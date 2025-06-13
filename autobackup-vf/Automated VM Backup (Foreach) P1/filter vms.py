import http.client
import ssl
import urllib.parse
import json
import base64
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
    print("Connected to Veeam Enterprise Manager!(For Filter VMs Script)")
    token = inputs['Token']
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-RestSvcSessionId": token
    }
    
    backup_job_id = inputs.get("job_id")
    parsed_url = urllib.parse.urlparse(VEEAM_URL)
    
    # Get the list of all backup jobs
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("GET", "/api/jobs", headers=headers)
        response = conn.getresponse()
        jobs_data = response.read().decode()
        jobs = json.loads(jobs_data).get("Refs")
        
        log_step(workflow_logs, vdc_name, "Retrieve Backup Jobs", "success", f"Retrieved {len(jobs)} backup jobs")
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Retrieve Backup Jobs", "failure", str(e))
        raise e
    finally:
        conn.close()
    
    backed_up_vms = []
    for job in jobs:
        job_id = job["UID"]
        job_name = job.get("Name").lower()
        if job_id == backup_job_id or job_id == "urn:veeam:Job:cc66d047-3cbe-4ad1-ac9d-d1016c69908c" or job_name.endswith("_standard"):
            continue
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
        try:
            job_vm_url = f"/api/jobs/{job_id}/includes"
            conn.request("GET", job_vm_url, headers=headers)
            job_response = conn.getresponse()
            job_vms_data = job_response.read().decode()
            if job_response.status == 200:
                job_vms = json.loads(job_vms_data).get("ObjectInJobs")
                for vm in job_vms:
                    backed_up_vms.append(vm["HierarchyObjRef"].split(".")[1])
        except Exception as e:
            log_step(workflow_logs, vdc_name, "Retrieve VMs in Job " + job_id, "failure", str(e))
        finally:
            conn.close()
    print(f"Total VMs already backed up in other jobs: {len(backed_up_vms)}")
    log_step(workflow_logs, vdc_name, "Check Backed Up VMs", "success", f"Total VMs already backed up in other jobs: {len(backed_up_vms)}")
    vm_list = inputs.get("addedVMs")
    filtered_vms = []
    for vm in vm_list:
        if vm["id"] not in backed_up_vms:
            filtered_vms.append(vm)
    print(f"VMs to be added to the backup job: {len(filtered_vms)}")
    log_step(workflow_logs, vdc_name, "Filter VMs", "success", f"VMs to be added to the backup job: {len(filtered_vms)}")
    return {
        "workflow_logs": workflow_logs,
        "filtered_vms": filtered_vms
    }


































#####################################################################

import http.client
import ssl
import urllib.parse
import json
import base64
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
    print("Connected to Veeam Enterprise Manager!(For Filter VMs Script)")
    token = inputs['Token']
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-RestSvcSessionId": token
    }
    
    parsed_url = urllib.parse.urlparse(VEEAM_URL)
    
    # Get the list of all backup jobs
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("GET", "/api/jobs", headers=headers)
        response = conn.getresponse()
        jobs_data = response.read().decode()
        jobs = json.loads(jobs_data).get("Refs")
        
        log_step(workflow_logs, vdc_name, "Retrieve Backup Jobs", "success", f"Retrieved {len(jobs)} backup jobs")
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Retrieve Backup Jobs", "failure", str(e))
        raise e
    finally:
        conn.close()
    
    backed_up_vms = []
    for job in jobs:
        job_id = job["UID"]
        job_name = job.get("Name").lower()
        if job_id == "urn:veeam:Job:cc66d047-3cbe-4ad1-ac9d-d1016c69908c" or job_name.endswith("_standard"):
            continue
        
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
        try:
            job_vm_url = f"/api/jobs/{job_id}/includes"
            conn.request("GET", job_vm_url, headers=headers)
            job_response = conn.getresponse()
            job_vms_data = job_response.read().decode()
            
            if job_response.status == 200:
                job_vms = json.loads(job_vms_data).get("ObjectInJobs")
                for vm in job_vms:
                    backed_up_vms.append(vm["HierarchyObjRef"].split(".")[1])
        except Exception as e:
            log_step(workflow_logs, vdc_name, "Retrieve VMs in Job " + job_id, "failure", str(e))
        finally:
            conn.close()
    
    print(f"Total VMs already backed up in other jobs: {len(backed_up_vms)}")
    log_step(workflow_logs, vdc_name, "Check Backed Up VMs", "success", f"Total VMs already backed up in other jobs: {len(backed_up_vms)}")
    
    vm_list = inputs.get("oldContent")
    filtered_vms = []
    for vm in vm_list:
        if vm["id"] not in backed_up_vms:
            filtered_vms.append(vm)
    
    print(f"VMs to be added to the backup job: {len(filtered_vms)}")
    log_step(workflow_logs, vdc_name, "Filter VMs", "success", f"VMs to be added to the backup job: {len(filtered_vms)}")
    
    return {
        "workflow_logs": workflow_logs,
        "filtered_vms": filtered_vms
    }