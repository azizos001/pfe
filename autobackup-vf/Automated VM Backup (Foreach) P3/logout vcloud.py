import http.client
import urllib.parse
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

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    vCloud_token = inputs.get("vCloud_token")
    url = inputs.get("vCloud_ip")
    vdc_name = inputs.get("VDC_name")
    
    log_step(workflow_logs, vdc_name, "Authenticate with vCloud Director (Logout)", "success", "Using provided vCD token")
    
    headers = {
        "Accept": "application/json;version=39.0",
        "Authorization": f"Bearer {vCloud_token}"
    }
    
    logout_url = f"https://{url}/cloudapi/1.0.0/sessions/current"
    parsed_url = urllib.parse.urlparse(logout_url)
    
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(), timeout=10)
    try:
        conn.request("DELETE", parsed_url.path, headers=headers)
        response = conn.getresponse()
        
        if response.status != 204:  # 204 No Content is expected for a successful logout
            error_msg = f"Failed to logout: {response.status} {response.reason}"
            log_step(workflow_logs, vdc_name, "Logout from vCloud Director", "failure", error_msg)
            raise Exception(error_msg)
        
        log_step(workflow_logs, vdc_name, "Logout from vCloud Director", "success", "Successfully logged out from vCloud Director")
    
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Logout from vCloud Director", "failure", f"Error during logout: {str(e)}")
        raise e
    finally:
        conn.close()
    
    return {"workflow_logs": workflow_logs}