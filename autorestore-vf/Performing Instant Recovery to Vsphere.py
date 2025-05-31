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
    vbr_url = inputs.get("VBR_url")
    restore_points = inputs.get("restore_points")
    token = inputs.get("Token_VBR")
    log_step(workflow_logs, "All VMs", "Authenticate VBR", "success", "Authenticated successfully")
    # Update headers with session token
    headers = {
        "x-api-version": "1.1-rev2",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Process each restore point for instant recovery
    restore_results = []
    for lrp in restore_points:
        vm_name = lrp["vm_name"]
        restore_point_id = lrp["restore_point_id"]
        creation_time = lrp["creation_time"]
        log_step(workflow_logs, vm_name, "Start Instant Recovery", "info", f"Initiating instant recovery for {vm_name} from restore point {restore_point_id} (Created: {creation_time})")

        # Extract restore point ID
        object_restore_point_id = restore_point_id[25:] if restore_point_id.startswith("urn:veeam:VmRestorePoint:") else restore_point_id

        # Prepare request body for instant recovery
        restore_body = {
            "restorePointId": object_restore_point_id,
            "type": "OriginalLocation",
            "vmTagsRestoreEnabled": True,
            "secureRestore": {
                "antivirusScanEnabled": True,
                "virusDetectionAction": "DisableNetwork",
                "entireVolumeScanEnabled": True
            },
            "nicsEnabled": False,
            "PowerUp": True,
            "reason": "Instant Recovery to VMware vSphere"
        }

        # Send POST request to start instant recovery
        restore_url = f"{vbr_url}/api/v1/restore/instantRecovery/vSphere/vm"
        conn = http.client.HTTPSConnection(urllib.parse.urlparse(restore_url).hostname, urllib.parse.urlparse(restore_url).port, context=ssl._create_unverified_context())
        try:
            response = make_api_request(conn, "POST", restore_url, headers, json.dumps(restore_body))
            if response.status == 201:
                response_data = json.loads(response.read().decode())
                restore_results.append({
                    "vm_name": vm_name,
                    "restore_point_id": restore_point_id,
                    "status": "Success",
                    "creation_time": creation_time,
                    "response": response_data
                })
                log_step(workflow_logs, vm_name, "Perform Instant Recovery", "success", f"Successfully started instant recovery for {vm_name}")
            else:
                error_msg = f"Failed to start instant recovery for {vm_name}: {response.status} - {response.read().decode()}"
                log_step(workflow_logs, vm_name, "Perform Instant Recovery", "failure", error_msg)
                restore_results.append({
                    "vm_name": vm_name,
                    "restore_point_id": restore_point_id,
                    "status": f"Failed: {response.status}",
                    "creation_time": creation_time,
                    "response": None
                })
        finally:
            conn.close()
    print("Restore Results = ",restore_results)
    log_step(workflow_logs, "All VMs", "Finalize Instant Recovery", "success", f"Processed {len(restore_results)} instant recovery operations")
    return {"Restore_Results": json.dumps({"restore_results": restore_results}, indent=4), "workflow_logs": workflow_logs}