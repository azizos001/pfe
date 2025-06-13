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
    VEEAM_URL = inputs.get("vbr_url")
    jobs_endpoint = "/api/v1/jobs"
    repositories_endpoint = "/api/v1/backupInfrastructure/repositories"
    
    # Use provided token
    token = inputs.get("Token_VBR")
    if not token:
        error_msg = "No token provided in inputs"
        log_step(workflow_logs, vdc_name, "Token Validation", "failure", error_msg)
    
    # Retrieve backup repositories
    headers = {
        "x-api-version": "1.1-rev2",
        "Authorization": f"Bearer {token}"
    }
    repositories_url = f"{VEEAM_URL}{repositories_endpoint}"
    parsed_repos_url = urllib.parse.urlparse(repositories_url)
    
    conn = http.client.HTTPSConnection(parsed_repos_url.hostname, parsed_repos_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("GET", parsed_repos_url.path, headers=headers)
        repos_response = conn.getresponse()
        repos_body = repos_response.read().decode()
        
        if repos_response.status != 200:
            error_msg = f"Failed to retrieve backup repositories: {repos_response.status} - {repos_body}"
            log_step(workflow_logs, vdc_name, "Retrieve Backup Repositories", "failure", error_msg)
        
        repositories = json.loads(repos_body).get("data")
        if not repositories:
            error_msg = "No backup repositories found"
            log_step(workflow_logs, vdc_name, "Retrieve Backup Repositories", "failure", error_msg)
        
        repository_name_input = inputs.get("repository_name")
        selected_repo = next((repo for repo in repositories if repo["name"] == repository_name_input), None)
        if not selected_repo:
            error_msg = f"Repository {repository_name_input} not found"
            log_step(workflow_logs, vdc_name, "Retrieve Backup Repositories", "failure", error_msg)
        backup_repository_id = selected_repo["id"]
        repository_name = selected_repo["name"]
        log_step(workflow_logs, vdc_name, "Retrieve Backup Repositories", "success", f"Selected repository: {repository_name} (ID: {backup_repository_id})")
        
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Retrieve Backup Repositories", "failure", str(e))
        raise e
    finally:
        conn.close()
    
    # Prepare VM entries
    vms = inputs.get("filtered_vms")
    includes = []
    added_vms = []
    for vm in vms:
        includes.append({
            "type": "VirtualMachine",
            "platform": "CloudDirector",
            "hostName": "portal-dr.focus-multicloud.com",
            "name": vm["name"],
            "objectId": vm["id"]
        })
        added_vms.append(vm["name"])
    
    if not includes:
        error_msg = "No VMs provided in 'filtered_vms'"
        log_step(workflow_logs, vdc_name, "VM Validation", "failure", error_msg)
        raise Exception(error_msg)
    
    # Job creation payload
    new_job_name = f"{vdc_name}_Standard"
    payload = {
        "name": new_job_name,
        "description": f"Standard Backup Job for {vdc_name}",
        "type": "CloudDirectorBackup",
        "isHighPriority": False,
        "virtualMachines": {
            "includes": includes,
            "excludes": {}
        },
        "storage": {
            "backupRepositoryId": backup_repository_id, 
            "backupProxies": {
                "autoSelect": True
            },
            "retentionPolicy": {
                "type": "Days",
                "quantity": 7
            }
        },
        "schedule": {
            "runAutomatically": True,
            "daily": {
                "isEnabled": True,
                "dailyKind": "Everyday",
                "localTime": "22:00"
            },
            "retry": {
                "isEnabled": True
            }
        }
    }
    
    # Job creation request
    jobs_headers = {
        "x-api-version": "1.1-rev2",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    jobs_url = f"{VEEAM_URL}{jobs_endpoint}"
    parsed_jobs_url = urllib.parse.urlparse(jobs_url)
    
    conn = http.client.HTTPSConnection(parsed_jobs_url.hostname, parsed_jobs_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("POST", parsed_jobs_url.path, body=json.dumps(payload), headers=jobs_headers)
        jobs_response = conn.getresponse()
        jobs_body = jobs_response.read().decode()
        
        if jobs_response.status == 201:
            log_step(workflow_logs, vdc_name, "Create Backup Job", "success", f"Backup job created: {new_job_name}")
            # Log VM addition with same status as job creation
            log_details = {"total_vms_processed": len(vms), "vms_added": added_vms, "vms_failed": []}
            log_step(workflow_logs, vdc_name, "Add VMs to Job", "success", log_details)
        else:
            error_msg = f"Failed to create backup job: {jobs_response.status} - {jobs_body}"
            log_step(workflow_logs, vdc_name, "Create Backup Job", "failure", error_msg)
            # Log VM addition with same status as job creation
            log_details = {"total_vms_processed": len(vms), "vms_added": [], "vms_failed": added_vms}
            log_step(workflow_logs, vdc_name, "Add VMs to Job", "failure", log_details)
            raise Exception(error_msg)
        
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Create Backup Job", "failure", str(e))
        # Log VM addition with same status as job creation
        log_details = {"total_vms_processed": len(vms), "vms_added": [], "vms_failed": added_vms}
        log_step(workflow_logs, vdc_name, "Add VMs to Job", "failure", str(e))
        raise e
    finally:
        conn.close()
    
    return {"workflow_logs": workflow_logs}

    