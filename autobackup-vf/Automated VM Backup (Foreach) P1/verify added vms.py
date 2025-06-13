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
    vdc_name = inputs.get("VDC_name")
    job_id = inputs.get("job_id")
    filtered_vms_input = inputs.get("filtered_vms")  # Intended VMs to add
    token = inputs.get("Token")
    VEEAM_URL = inputs.get("vem_url")
    
    try:
        # Parse filtered_vms (intended VMs)
        filtered_vms = json.loads(filtered_vms_input) if isinstance(filtered_vms_input, str) else filtered_vms_input
        intended_count = len(filtered_vms)
        print("intended_count",intended_count)
        # Set up headers for API request
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-RestSvcSessionId": token
        }
        
        # Fetch actual VMs from Veeam API
        parsed_url = urllib.parse.urlparse(VEEAM_URL)
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
        try:
            api_url = f"/api/jobs/{job_id}/includes"
            conn.request("GET", api_url, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode()
            
            if response.status not in [200, 201]:
                raise Exception(f"Failed to fetch VMs from job {job_id}. Status: {response.status}, Response: {response_data}")
            
            actual_vms_data = json.loads(response_data)
            actual_vms = actual_vms_data.get("ObjectInJobs")
            actual_count = len(actual_vms)
            log_step(workflow_logs, vdc_name, "Fetch VMs in Job", "success",
                     f"Fetched {actual_count} VMs from job {job_id} via API")
        except Exception as e:
            log_step(workflow_logs, vdc_name, "Fetch VMs in Job", "failure", str(e))
            raise e
        finally:
            conn.close()
        
        # Log the initial counts
        log_step(workflow_logs, vdc_name, "Verify Added VMs - Initial Check", "success",
                 f"Intended to add {intended_count} VMs to job {job_id}, found {actual_count} VMs in job")
        
        # Step 1: Check for missing VMs (intended but not added)
        intended_vm_ids = {vm.get("id").split(":")[-1] : vm.get("name") for vm in filtered_vms }
        actual_vm_ids = {vm.get("HierarchyObjRef").split(":")[-1]: vm.get("Name", "Unknown VM") for vm in actual_vms if vm.get("ObjectInJobId")}
        print("intended_vm_ids",intended_vm_ids)
        print("actual_vm_ids",actual_vm_ids)
        missing_vms = []
        for vm_id, vm_name in intended_vm_ids.items():
            if vm_id not in actual_vm_ids:
                missing_vms.append({"ObjectInJobId": vm_id, "Name": vm_name})
        
        # Step 2: Check for duplicates in actual VMs
        vm_id_counts = {}
        duplicate_vms = []
        
        for vm in actual_vms:
            vm_id = vm.get("HierarchyObjRef").split(":")[-1]
            if not vm_id:
                continue
            vm_id_counts[vm_id] = vm_id_counts.get(vm_id, 0) + 1
            if vm_id_counts[vm_id] > 1:
                duplicate_vms.append({"ObjectInJobId": vm_id, "Name": vm.get("Name", "Unknown VM")})
        
        # Prepare log details
        log_details = {
            "intended_vms_count": intended_count,
            "actual_vms_count": actual_count,
            "missing_vms": missing_vms,  # VMs that were intended but not added
            "duplicate_vms": duplicate_vms  # VMs that appear more than once in the job
        }
        
        # Determine status
        status = "success"
        if missing_vms:
            status = "partial_success"
        if duplicate_vms:
            status = "partial_success" if status == "success" else "failure"
        # Log the verification results
        log_step(workflow_logs, vdc_name, "Verify Added VMs", status, log_details)
        # Print summary for debugging
        print(f"Verification Summary for Job {job_id} in VDC {vdc_name}:")
        print(f" - Intended VMs: {intended_count}, Actual VMs in Job: {actual_count}")
        if missing_vms:
            print(f" - Missing VMs: {len(missing_vms)}")
            for vm in missing_vms:
                print(f"   - {vm['Name']} (ID: {vm['ObjectInJobId']})")
        if duplicate_vms:
            print(f" - Duplicate VMs: {len(duplicate_vms)}")
            for vm in duplicate_vms:
                print(f"   - {vm['Name']} (ID: {vm['ObjectInJobId']})")
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Verify Added VMs", "failure", str(e))
        raise e
    return {"workflow_logs": workflow_logs}