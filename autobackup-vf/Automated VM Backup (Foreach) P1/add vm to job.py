import http.client
import ssl
import urllib.parse
import json
import base64
import time
from datetime import datetime, timedelta

def log_step(workflow_logs, vdc_name, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "vdc_name": vdc_name,
        "step": step_name,
        "status": status,
        "details": details
    })

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    VEEAM_URL = inputs.get("vem_url")
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    vdc_name = inputs.get("VDC_name")
    print("Connected to Veeam Enterprise Manager!(For 'Add VM to Job' Script)")
    token = inputs['Token']
    headers["X-RestSvcSessionId"] = token
    
    parsed_url1 = urllib.parse.urlparse(VEEAM_URL)
    conn = http.client.HTTPSConnection(parsed_url1.hostname, parsed_url1.port, context=ssl._create_unverified_context(),timeout=10)
    
    # Step 1: Retrieve Hierarchy Roots
    try:
        conn.request("GET", "/api/hierarchyRoots", headers=headers)
        response = conn.getresponse()

        if response.status != 200:
            error_msg = f"Failed to retrieve hierarchy roots: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, vdc_name, "Retrieve Hierarchy Roots", "failure", error_msg)
            conn.close()
            raise Exception(error_msg)

        hierarchy_roots = json.loads(response.read().decode())
        log_step(workflow_logs, vdc_name, "Retrieve Hierarchy Roots", "success", "Hierarchy roots retrieved successfully")
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Retrieve Hierarchy Roots", "failure", str(e))
        raise e
    finally:
        conn.close()

    # Step 2: Find the Hierarchy Root ID for "portal-cloud.com"
    hierarchy_root_id = None
    for root in hierarchy_roots["Refs"]:
        if root["Name"] == "portal-dr.focus-multicloud.com":
            hierarchy_root_id = root["UID"]
            break

    if not hierarchy_root_id:
        error_msg = "Hierarchy Root ID for 'portal-cloud.com' not found!"
        log_step(workflow_logs, vdc_name, "Find Hierarchy Root ID", "failure", error_msg)
        raise Exception(error_msg)

    log_step(workflow_logs, vdc_name, "Find Hierarchy Root ID", "success", f"Hierarchy Root ID found: {hierarchy_root_id}")

    # Step 3: Read the backup job ID
    backup_job_id = inputs.get("job_id")
    if not backup_job_id:
        error_msg = "Backup job ID not provided!"
        log_step(workflow_logs, vdc_name, "Read Backup Job ID", "failure", error_msg)
        raise Exception(error_msg)
    
    log_step(workflow_logs, vdc_name, "Read Backup Job ID", "success", f"Backup job ID: {backup_job_id}")

    # Load VM list
    vm_list = inputs.get("filtered_vms")
    if not vm_list:
        log_step(workflow_logs, vdc_name, "Load VM List", "success", "No VMs to add to the job")
        return {"workflow_logs": workflow_logs}

    # Step 4: Add each VM to the backup job
    added_vms = []
    failed_vms = []
    for vm in vm_list:
        hierarchy_obj_ref = f"urn:vCloud:Vm:{hierarchy_root_id.split(':')[-1]}.{vm['id']}"
        payload = {"HierarchyObjRef": hierarchy_obj_ref, "HierarchyObjName": vm['name']}
        json_payload = json.dumps(payload)
        endpoint = f"/api/jobs/{backup_job_id}/includes"

        conn = http.client.HTTPSConnection(parsed_url1.hostname, parsed_url1.port, context=ssl._create_unverified_context(),timeout=10)
        try:
            conn.request("POST", endpoint, body=json_payload, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode()

            if response.status == 202:
                added_vms.append(vm['name'])
                print(f"VM {vm['name']} added with status: {response.status}")
            else:
                failed_vms.append(vm['name'])
                print(f"Failed to add VM {vm['name']} - Status: {response.status}, Response: {response_data}")
            time.sleep(1)
        except Exception as e:
            failed_vms.append(vm['name'])
            print(f"Error adding VM {vm['name']}: {str(e)}")
        finally:
            conn.close()

    # Log the results of adding VMs
    log_details = {"total_vms_processed": len(vm_list), "vms_added": added_vms, "vms_failed": failed_vms}
    status = "success" if not failed_vms else "partial_success"
    log_step(workflow_logs, vdc_name, "Add VMs to Job", status, log_details)

    return {"workflow_logs": workflow_logs}