import json
import http.client
import urllib.parse
import base64
import ssl
from datetime import datetime, timedelta
import time

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
    headers = {"Accept": "application/json", "X-RestSvcSessionId": inputs['Token']}
    print("Connected to Veeam Enterprise Manager!(For Search Job ID Script)")
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    job_id = None
    for attempt in range(max_retries):
        jobs_url = f"{VEEAM_URL}/jobs"
        parsed_url2 = urllib.parse.urlparse(jobs_url)
        conn = http.client.HTTPSConnection(parsed_url2.hostname, parsed_url2.port, context=ssl._create_unverified_context(), timeout=10)
        
        try:
            conn.request("GET", parsed_url2.path, headers=headers)
            response = conn.getresponse()
            
            if response.status != 200:
                error_msg = f"Failed to fetch backup jobs: {response.status} - {response.read().decode()}"
                log_step(workflow_logs, vdc_name, "Fetch Backup Jobs", "failure", f"Attempt {attempt + 1}/{max_retries}: {error_msg}")
                if attempt == max_retries - 1:
                    raise Exception(error_msg)
                time.sleep(retry_delay)
                continue
            
            jobs = json.loads(response.read().decode())
            log_step(workflow_logs, vdc_name, "Fetch Backup Jobs", "success", f"Attempt {attempt + 1}: Retrieved {len(jobs.get('Refs', []))} backup jobs")
            
            for job in jobs.get("Refs"):
                if job["Name"].lower() == f"{vdc_name}_standard":
                    job_id = job["UID"]
                    log_step(workflow_logs, vdc_name, "Search Job ID", "success", f"Matching job found: {job['Name']} (ID: {job_id})")
                    conn.close()
                    return {"workflow_logs": workflow_logs, "job_id": job_id}
            
            # If job ID not found, log and retry
            log_step(workflow_logs, vdc_name, "Search Job ID Attempts", "failure", f"Attempt {attempt + 1}/{max_retries}: No matching backup jobs found")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        except Exception as e:
            log_step(workflow_logs, vdc_name, "Fetch Backup Jobs", "failure", f"Attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(retry_delay)
        
        finally:
            conn.close()
    
    # If we reach here, all retries failed to find the job ID
    error_msg = f"Critical: Backup job '{vdc_name}_standard' not found after {max_retries} attempts. Expected job ID for VDC '{vdc_name}'."
    print(error_msg)
    log_step(workflow_logs, vdc_name, "Search Job ID", "failure", error_msg)
    return {"workflow_logs": workflow_logs, "job_id": None}