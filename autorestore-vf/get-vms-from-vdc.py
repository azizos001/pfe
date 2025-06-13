import http.client
import ssl
import urllib.parse
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

def log_step(workflow_logs, context, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "context": context if context else "All VDCs",
        "step": step_name,
        "status": status,
        "details": details
    })

def make_api_request(conn, method, url, headers, body=None):
    parsed_url = urllib.parse.urlparse(url)
    conn.request(method, parsed_url.path + ("?" + parsed_url.query if parsed_url.query else ""), body=body, headers=headers)
    response = conn.getresponse()
    return response

def fetch_all_pages(base_url, headers, context, step_name, workflow_logs):
    page = 1
    page_size = 30
    all_items = []

    while True:
        url = f"{base_url}?page={page}&pageSize={page_size}"
        conn = http.client.HTTPSConnection(urllib.parse.urlparse(url).hostname, context=ssl._create_unverified_context(), timeout=10)
        try:
            response = make_api_request(conn, "GET", url, headers)
            if response.status != 200:
                error_msg = f"Failed to fetch data: {response.status} - {response.read().decode()}"
                log_step(workflow_logs, context, step_name, "failure", error_msg)
                raise Exception(error_msg)
            data = json.loads(response.read().decode())
            items = data.get("values")
            all_items.extend(items)
            log_step(workflow_logs, context, step_name, "success", f"Fetched {len(items)} items on page {page}, total so far: {len(all_items)}")
            total_items = data.get("resultTotal")
            if len(all_items) >= total_items or not items:
                break
            page += 1
        finally:
            conn.close()
    return all_items

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    workflow_logs = []
    vcd_url = inputs.get("vCloud_ip")
    vcd_token = inputs.get("vCloud_token")
    selected_vdcs = inputs.get("vdc_list")

    log_step(workflow_logs,"All VDCs", "Authenticate with vCloud Director", "success", "Using provided vCD token")
    headers = {
        "Accept": "application/json;version=39.0",
        "Authorization": f"Bearer {vcd_token}"
    }

    # Fetch all compute policies
    compute_policies_url = f"https://{vcd_url}/cloudapi/2.0.0/vdcComputePolicies"
    compute_policies = fetch_all_pages(compute_policies_url, headers,"All VDCs", "Fetch Compute Policies", workflow_logs)

    # Match compute policies for each VDC
    matched_vdcs = []
    for vdc_name in selected_vdcs:
        vdc_name_lower = vdc_name.lower()
        pvdcCP_id = None
        PVDC_Name = None

        # Step 1: Match by name pattern
        pattern = rf"^{re.escape(vdc_name_lower)}.*defaultpolicy$"
        for policy in compute_policies:
            policy_name = policy.get("description")
            if policy_name is None:
                continue
            if policy_name and re.match(pattern, policy_name.lower()):
                pvdcCP_id = policy.get("id")
                PVDC_Name = policy_name
                log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "success", f"Matched compute policy '{policy_name}' (ID: {pvdcCP_id}) by name pattern")
                break

        # Step 2: If no match, check VDCs for policies ending with 'defaultpolicy'
        if not pvdcCP_id:
            for policy in compute_policies:
                policy_name = policy.get("description")
                if policy_name is None:
                    continue
                policy_name = policy_name.lower()
                if policy_name and policy_name.endswith("defaultpolicy"):
                    policy_id = policy.get("id")
                    compute_policy_vdcs_url = f"https://{vcd_url}/cloudapi/2.0.0/vdcComputePolicies/{policy_id}/vdcs"
                    conn = http.client.HTTPSConnection(urllib.parse.urlparse(compute_policy_vdcs_url).hostname, context=ssl._create_unverified_context(), timeout=10)
                    try:
                        response = make_api_request(conn, "GET", compute_policy_vdcs_url, headers)
                        if response.status != 200:
                            log_step(workflow_logs, vdc_name, "Fetch VDCs for Compute Policy", "warning", f"Failed to get VDCs for policy {policy_name}: {response.status} - {response.read().decode()}")
                            continue
                        vdcs_data = json.loads(response.read().decode())
                        for vdc in vdcs_data:
                            vdc_name_from_api = vdc.get("name").lower()
                            if vdc_name_from_api == vdc_name_lower:
                                pvdcCP_id = policy_id
                                PVDC_Name = policy_name
                                log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "success", f"Matched compute policy '{policy_name}' (ID: {pvdcCP_id}) via VDC association")
                                break
                        if pvdcCP_id:
                            break
                    finally:
                        conn.close()

        if not pvdcCP_id:
            log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "warning", f"No compute policy found for VDC {vdc_name}")
            continue
        matched_vdcs.append({"id": pvdcCP_id, "name": vdc_name, "PVDC_name": PVDC_Name})
    if not matched_vdcs:
        log_step(workflow_logs,"All VDCs", "Match VDCs", "warning", f"No VDCs matched from input: {selected_vdcs}")
        return {"vms_list_user": [], "vms_list": [], "workflow_logs": workflow_logs}
    # Fetch VMs for each matched VDC
    vm_list = []
    for vdc in matched_vdcs:
        vms_url = f"https://{vcd_url}/cloudapi/1.0.0/vdcComputePolicies/{urllib.parse.quote(vdc['id'])}/vms"
        vms = fetch_all_pages(vms_url, headers, vdc["name"], "Fetch All VMs", workflow_logs)
        vm_list.extend({"name": vm["name"], "id": vm["id"], "VDC": vdc["name"]} for vm in vms)
    vms_list_user = [f"{vm['name']} on {vm['VDC']}" for vm in vm_list]
    log_step(workflow_logs, "All VDCs", "Fetch VMs", "success", f"Retrieved {len(vm_list)} VMs from {len(matched_vdcs)} VDCs")
    # Add summary of VMs per VDC
    vms_by_vdc = defaultdict(list)
    for vm in vm_list:
        vms_by_vdc[vm["VDC"]].append(vm)
    for vdc_name, vms in sorted(vms_by_vdc.items()):
        log_step(workflow_logs, vdc_name, "VM Summary", "success", f"Total VMs in VDC {vdc_name}: {len(vms)}")
        print(f"Total VMs in VDC {vdc_name}: {len(vms)}")
    return {"vms_list_user": vms_list_user, "vms_list": vm_list, "workflow_logs": workflow_logs}
