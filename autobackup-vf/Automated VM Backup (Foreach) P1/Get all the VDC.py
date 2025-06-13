import json
import http.client
import urllib.parse
import base64
import ssl
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
            
            # Log progress
            log_step(workflow_logs, vdc_name, step_name, "success", f"Fetched {len(items)} items on page {page}, total so far: {len(all_items)}")
            
            # Check if there are more pages
            total_items = data.get("resultTotal", len(all_items))
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
    workflow_logs = []
    vCloud_token = inputs.get("vCloud_token")
    url = inputs.get("vCloud_ip")
    if not vCloud_token:
        error_msg = "No vCD token provided"
        log_step(workflow_logs, "N/A", "Authenticate with vCloud Director (Get VMs)", "failure", error_msg)
        raise Exception(error_msg)
    
    log_step(workflow_logs, "N/A", "Authenticate with vCloud Director (Get VMs)", "success", "Using provided vCD token")
    
    headers = {"Accept": "application/json;version=39.0", "Authorization": f"Bearer {vCloud_token}"}
    vdc_url = f"https://{url}/cloudapi/1.0.0/vdcs"
    
    # Fetch all VDCs dynamically
    vdcs = fetch_all_pages(vdc_url, headers, "N/A", "Get All VDCs", workflow_logs)
    
    vdc_list = [vdc["name"] for vdc in vdcs if "name" in vdc]
    log_step(workflow_logs, "N/A", "Get All VDCs", "success", f"Retrieved {len(vdc_list)} VDCs: {vdc_list}")
    
    return {"workflow_logs": workflow_logs,"vdc_list": vdc_list}