import http.client
import ssl
import urllib.parse
import json
import base64
from datetime import datetime, timedelta

def log_step(workflow_logs, context, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "context": context if context else "All VMs",
        "step": step_name,
        "status": status,
        "details": details
    })

def make_api_request(conn, method, url, headers, body=None):
    parsed_url = urllib.parse.urlparse(url)
    conn.request(method, parsed_url.path + ("?" + parsed_url.query if parsed_url.query else ""), body=body, headers=headers)
    response = conn.getresponse()
    return response

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    veeam_url = inputs.get("veeam_url")
    restore_points = inputs.get("restore_points")
    token = inputs.get("Token")
    restore_options = {
        "PowerOnAfterRestore": inputs.get("PowerOn", False),
        "VmNewNameSuffix": None,
        "HierarchyRootName": "portal-dr.focus-multicloud.com"
    }
    headers = {
        "Accept": "application/json",
        "X-RestSvcSessionId": token,
        "Content-Type": "application/json"
    }
    log_step(workflow_logs, "All VMs", "Authenticate Veeam", "success", "Authenticated successfully")
    # Fetch HierarchyRootUid from HierarchyRootName
    hierarchy_root_id = None
    if restore_options["HierarchyRootName"]:
        hierarchy_url = f"{veeam_url}/hierarchyRoots"
        conn = http.client.HTTPSConnection(urllib.parse.urlparse(hierarchy_url).hostname, urllib.parse.urlparse(hierarchy_url).port, context=ssl._create_unverified_context(),timeout=10)
        try:
            response = make_api_request(conn, "GET", hierarchy_url, headers)
            if response.status == 200:
                hierarchy_data = json.loads(response.read().decode())
                hierarchy_roots = hierarchy_data.get("Refs")
                for root in hierarchy_roots:
                    if root["Name"].lower() == restore_options["HierarchyRootName"].lower():
                        hierarchy_root_id = root["UID"]
                        log_step(workflow_logs, "All VMs", "Fetch HierarchyRoot", "success", f"Found HierarchyRoot ID: {hierarchy_root_id} for {restore_options['HierarchyRootName']}")
                        break
                if not hierarchy_root_id:
                    log_step(workflow_logs, "All VMs", "Fetch HierarchyRoot", "warning", f"No HierarchyRoot found for name: {restore_options['HierarchyRootName']}")
            else:
                error_msg = f"Failed to fetch hierarchyRoots: {response.status} - {response.read().decode()}"
                log_step(workflow_logs, "All VMs", "Fetch HierarchyRoot", "failure", error_msg)
                raise Exception(error_msg)
        finally:
            conn.close()

    # Perform restore for each VM
    restore_results = []
    for rp in restore_points:
        vm_name = rp["vm_name"]
        restore_point_id = rp["restore_point_id"]
        log_step(workflow_logs, vm_name, "Start Restore", "info", f"Starting restore for {vm_name} (Restore Point ID: {restore_point_id})")

        # Construct nested payload
        payload = {
            "VmRestoreSpec": {
                "PowerOnAfterRestore": restore_options["PowerOnAfterRestore"],
                "VmRestoreParameters": {
                    "VmRestorePointUid": restore_point_id
                }
            }
        }

        # Add VmNewName with suffix if provided
        if restore_options["VmNewNameSuffix"]:
            payload["VmRestoreSpec"]["VmRestoreParameters"]["VmNewName"] = vm_name

        # Add HierarchyRootUid if found
        if hierarchy_root_id:
            payload["VmRestoreSpec"]["HierarchyRootUid"] = hierarchy_root_id

        json_payload = json.dumps(payload)

        # Send restore request
        restore_url = f"{veeam_url}/vmRestorePoints/{restore_point_id}?action=restore"
        conn = http.client.HTTPSConnection(urllib.parse.urlparse(restore_url).hostname, urllib.parse.urlparse(restore_url).port , context=ssl._create_unverified_context(),timeout=10)
        try:
            response = make_api_request(conn, "POST", restore_url, headers, json_payload)
            if response.status == 202:
                response_data = json.loads(response.read().decode())
                task_id = response_data.get("TaskId")
                restore_results.append({
                    "vm_name": vm_name,
                    "vm_id": rp["vm_id"],
                    "restore_point_id": restore_point_id,
                    "task_id": task_id,
                    "status": "Started",
                    "creation_time": rp["creation_time"]
                })
                log_step(workflow_logs, vm_name, "Perform Restore", "success", f"Restore started for {vm_name}. Task ID: {task_id}")
            else:
                error_msg = f"Failed to start restore for {vm_name}: {response.status} - {response.read().decode()}"
                log_step(workflow_logs, vm_name, "Perform Restore", "failure", error_msg)
                restore_results.append({
                    "vm_name": vm_name,
                    "vm_id": rp["vm_id"],
                    "restore_point_id": restore_point_id,
                    "task_id": None,
                    "status": f"Failed: {response.status}",
                    "creation_time": rp["creation_time"]
                })
        finally:
            conn.close()
    print("Restore Results = ",restore_results)
    log_step(workflow_logs, "All VMs", "Finalize Restore", "success", f"Processed {len(restore_results)} restore operations")
    return {"Restore_Results": json.dumps({"restore_results": restore_results}, indent=4), "workflow_logs": workflow_logs}