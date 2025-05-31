import http.client
import ssl
import urllib.parse
from datetime import datetime, timedelta

def log_step(workflow_logs, vdc_name, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "context": vdc_name,
        "step": step_name,
        "status": status,
        "details": details
    })

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    vdc_name = "All VMs"
    VEEAM_URL = inputs.get("VBR_url")
    token = inputs.get("Token_VBR")
    log_step(workflow_logs, vdc_name, "Authenticate with Veeam VBR (Logout)", "success", "Using provided Veeam VBR token")
    print("Authenticate with Veeam VBR (Logout)")
    headers = {
        "x-api-version": "1.1-rev2",
        "Authorization": f"Bearer {token}"
    }
    
    logout_endpoint = "/api/oauth2/logout"
    logout_url = f"{VEEAM_URL}{logout_endpoint}"
    parsed_url = urllib.parse.urlparse(logout_url)
    
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("POST", parsed_url.path, headers=headers)
        response = conn.getresponse()
        
        if response.status != 200:  # 200 OK is expected for a successful logout
            error_msg = f"Failed to logout: {response.status} {response.reason}"
            log_step(workflow_logs, vdc_name, "Logout from Veeam", "failure", error_msg)
        
        log_step(workflow_logs, vdc_name, "Logout from Veeam", "success", "Successfully logged out from Veeam Backup & Replication")
    
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Logout from Veeam", "failure", f"Error during logout: {str(e)}")
        raise e
    finally:
        conn.close()
    
    return {"workflow_logs": workflow_logs}