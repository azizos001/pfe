import http.client
import urllib.parse
import base64
import ssl
import json
import re
from datetime import datetime, timedelta

def log_step(workflow_logs, vdc_name, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "vdc_name": vdc_name,
        "step": step_name,
        "status": status,
        "details": details
    })

def fetch_all_pages(base_url, headers, vdc_name, step_name, workflow_logs):
    page = 1
    page_size = 30
    all_items = []
    
    while True:
        url = f"{base_url}?page={page}&pageSize={page_size}"
        parsed_url = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed_url.hostname, context=ssl._create_unverified_context(),timeout=10)
        try:
            conn.request("GET", parsed_url.path + "?" + parsed_url.query, headers=headers)
            response = conn.getresponse()
            
            if response.status != 200:
                error_msg = f"Failed to fetch data: {response.status} {response.reason}"
                log_step(workflow_logs, vdc_name, step_name, "failure", error_msg)
                raise Exception(error_msg)
            
            data = json.loads(response.read().decode())
            items = data.get("values", [])
            all_items.extend(items)
            
            log_step(workflow_logs, vdc_name, step_name, "success", f"Fetched {len(items)} items on page {page}, total so far: {len(all_items)}")
            
            total_items = data.get("resultTotal")
            if len(all_items) >= total_items or not items:
                break
                
            page += 1
        except Exception as e:
            log_step(workflow_logs, vdc_name, step_name, "failure", f"Error fetching page {page}: {str(e)}")
            raise e
        finally:
            conn.close()
    
    return all_items

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    vcd_token = inputs.get("vCloud_token")
    url = inputs.get("vCloud_ip")
    vdc_name = inputs.get("VDC_name")
    if not vcd_token:
        error_msg = "No vCD token provided"
        log_step(workflow_logs, vdc_name, "Authenticate with vCloud Director (Get VMs)", "failure", error_msg)
        raise Exception(error_msg)
    
    log_step(workflow_logs, "N/A", "Authenticate with vCloud Director (Get VMs)", "success", "Using provided vCD token")
    
    headers = {"Accept": "application/json;version=39.0", "Authorization": f"Bearer {vcd_token}"}
    
    # Step 1: Fetch all compute policies and match by name pattern
    pvdcCP_id = None
    PVDC_Name = None
    compute_policies_url = f"https://{url}/cloudapi/2.0.0/vdcComputePolicies"
    compute_policies = fetch_all_pages(compute_policies_url, headers, vdc_name, "Fetch Compute Policies", workflow_logs)
    pattern = f"^{re.escape(vdc_name)}.*defaultpolicy$"
    for policy in compute_policies:
        policy_id = policy.get("id")
        policy_name = policy.get("description")
        if policy_name is None:
            continue
        if re.match(pattern, policy_name.lower()):
            pvdcCP_id = policy_id
            PVDC_Name = policy_name
            log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "success", f"Matched compute policy '{policy_name}' (ID: {pvdcCP_id}) by name pattern")
            break
    # Step 2: If no match, check VDCs for each policy ending with defaultpolicy
    if not pvdcCP_id:
        for policy in compute_policies:
            policy_id = policy.get("id")
            policy_name = policy.get("description")
            if policy_name is None:
                continue
            if not policy_name.lower().endswith("defaultpolicy"):
                continue
            compute_policy_vdcs_url = f"https://{url}/cloudapi/2.0.0/vdcComputePolicies/{policy_id}/vdcs"
            parsed_url = urllib.parse.urlparse(compute_policy_vdcs_url)
            conn = http.client.HTTPSConnection(parsed_url.hostname, context=ssl._create_unverified_context(),timeout=10)
            try:
                conn.request("GET", compute_policy_vdcs_url, headers=headers)
                response = conn.getresponse()
                
                if response.status == 200:
                    vdcs_data = json.loads(response.read().decode())
                    for vdc in vdcs_data:
                        vdc_name_from_api = vdc.get("name").lower()
                        if vdc_name_from_api == vdc_name:
                            pvdcCP_id = policy_id
                            PVDC_Name = policy_name
                            log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "success", f"Matched compute policy '{policy_name}' (ID: {pvdcCP_id}) via VDC association")
                            break
                    if pvdcCP_id:
                        break
                else:
                    log_step(workflow_logs, vdc_name, "Fetch VDCs for Compute Policy", "failure", f"Failed to get VDCs for policy {policy_name}: {response.status} {response.reason}")
            except Exception as e:
                log_step(workflow_logs, vdc_name, "Fetch VDCs for Compute Policy", "failure", f"Error fetching VDCs for policy {policy_name}: {str(e)}")
            finally:
                conn.close()
    if not pvdcCP_id:
        error_msg = f"No compute policy ending with 'defaultpolicy' found for VDC {vdc_name}"
        log_step(workflow_logs, vdc_name, "Find PVDC Compute Policy", "failure", error_msg)
        raise Exception(error_msg)
    # Step 3: Fetch VMs for the matched compute policy dynamically
    encoded_pvdcCP_id = urllib.parse.quote(pvdcCP_id)
    vms_url = f"https://{url}/cloudapi/1.0.0/vdcComputePolicies/{encoded_pvdcCP_id}/vms"
    vms = fetch_all_pages(vms_url, headers, vdc_name, "Fetch All VMs", workflow_logs)
    if vms:
        vm_list = [{"name": vm["name"], "id": vm["id"]} for vm in vms]
        log_step(workflow_logs, vdc_name, "Get All VMs", "success", f"Retrieved {len(vm_list)} VMs for VDC {vdc_name}")
    else:
        vm_list = []
        log_step(workflow_logs, vdc_name, "Get All VMs", "success", "No VMs found in VDC")
    return {"workflow_logs": workflow_logs, "vms_list": vm_list, "PVDC_name": PVDC_Name,"VDC_name":vdc_name}