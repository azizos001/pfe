import http.client
import ssl
import urllib.parse
import json
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
    vdc_name = inputs.get("VDC_name")
    token = inputs.get("Token")
    job_id = inputs.get("job_id")
    missing_vms = inputs.get("missingVMs")  # Input containing list of VMs deleted from vCloud

    print("Connected to Veeam Enterprise Manager!(to remove vCloud deleted VMs)")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-RestSvcSessionId": token
    }
    parsed_url = urllib.parse.urlparse(VEEAM_URL)
    # Parse missing_vms if it's a JSON string
    if isinstance(missing_vms, str):
        try:
            missing_vms = json.loads(missing_vms)
        except json.JSONDecodeError as e:
            log_step(workflow_logs, vdc_name, "Parse missingVMs", "failure", f"Error parsing missingVMs: {str(e)}")
            raise Exception(f"Error parsing missingVMs: {str(e)}")
    
    if not missing_vms or not isinstance(missing_vms, list):
        log_step(workflow_logs, vdc_name, "Check Missing VMs", "success", "No vCloud deleted VMs provided to delete")
        return {"workflow_logs": workflow_logs}
    
    log_step(workflow_logs, vdc_name, "Check Missing VMs", "success", f"Found {len(missing_vms)} vCloud deleted VMs to remove")
    # Fetch current VMs in the job to get ObjectInJobId
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        job_vm_url = f"/api/jobs/{job_id}/includes"
        conn.request("GET", job_vm_url, headers=headers)
        response = conn.getresponse()
        
        if response.status != 200:
            error_msg = f"Failed to fetch VMs from job {job_id}: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, vdc_name, "Fetch Job VMs", "failure", error_msg)
            raise Exception(error_msg)
        
        job_vms_data = json.loads(response.read().decode())
        job_vms = {vm["HierarchyObjRef"].split(".")[-1]: vm for vm in job_vms_data.get("ObjectInJobs")}
        log_step(workflow_logs, vdc_name, "Fetch Job VMs", "success", f"Retrieved {len(job_vms)} VMs from job {job_id}")
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Fetch Job VMs", "failure", str(e))
        raise e
    finally:
        conn.close()
    # Delete vCloud deleted VMs from the job
    removed_vms = []
    failed_vms = []
    
    for missing_vm in missing_vms:
        vm_id = missing_vm.get("id")  # Extract full urn
        job_vm = job_vms.get(vm_id)
        if not job_vm:
            failed_vms.append(missing_vm["name"])
            print(f"VM {missing_vm['name']} (ID: {vm_id}) not found in job, skipping deletion")
            continue
        
        delete_url = f"/api/jobs/{job_id}/includes/{job_vm['ObjectInJobId']}"
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
        try:
            conn.request("DELETE", delete_url, headers=headers)
            delete_response = conn.getresponse() 
            if delete_response.status == 202:
                removed_vms.append(missing_vm["name"])
                print(f"Removing VM {missing_vm['name']} (ID: {vm_id}) - Status: {delete_response.status}")
            else:
                failed_vms.append(missing_vm["name"])
                print(f"Failed to remove VM {missing_vm['name']} (ID: {vm_id}) - Status: {delete_response.status}, Response: {delete_response.read().decode()}")
        except Exception as e:
            failed_vms.append(missing_vm["name"])
            print(f"Error removing VM {missing_vm['name']} (ID: {vm_id}): {str(e)}")
        finally:
            conn.close()
    log_details = {
        "total_vms_processed": len(missing_vms),
        "vms_removed": removed_vms,
        "vms_failed": failed_vms
    }
    status = "success" if not failed_vms else "partial_success"
    log_step(workflow_logs, vdc_name, "Remove vCloud Deleted VMs", status, log_details)
    return {"workflow_logs": workflow_logs}