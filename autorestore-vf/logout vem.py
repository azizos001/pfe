import http.client
import ssl
import urllib.parse
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

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
    VEEAM_URL = inputs.get("veeam_url")
    vdc_name = "All VMs"
    login_response_xml = inputs.get("contentAsString")
    token = inputs.get("Token")
    
    print("Connected to Veeam Enterprise Manager!(For Logout Script)")
    
    # Parse XML to extract SessionId
    try:
        root = ET.fromstring(login_response_xml)
        session_id = root.find(".//{http://www.veeam.com/ent/v1.0}SessionId")
        if session_id is None or not session_id.text:
            error_msg = "SessionId not found in login response XML"
            log_step(workflow_logs, vdc_name, "Parse Login Response", "failure", error_msg)
        session_id = session_id.text
        log_step(workflow_logs, vdc_name, "Parse Login Response", "success", f"Extracted SessionId: {session_id}")
    except ET.ParseError as e:
        error_msg = f"Failed to parse XML: {str(e)}"
        log_step(workflow_logs, vdc_name, "Parse Login Response", "failure", error_msg)
        raise Exception(error_msg)
    
    log_step(workflow_logs, vdc_name, "Authenticate with Veeam Enterprise Manager (Logout)", "success", "Using extracted SessionId")
    
    headers = {"Accept": "application/json", "X-RestSvcSessionId": token}
    logout_url = f"{VEEAM_URL}/logonSessions/{session_id}"
    parsed_url = urllib.parse.urlparse(logout_url)
    
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context(),timeout=10)
    try:
        conn.request("DELETE", parsed_url.path, headers=headers)
        response = conn.getresponse()
        
        if response.status != 204:  # 204 No Content is expected for a successful logout
            error_msg = f"Failed to logout: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, vdc_name, "Logout from Veeam Enterprise Manager", "failure", error_msg)
        
        log_step(workflow_logs, vdc_name, "Logout from Veeam Enterprise Manager", "success", "Successfully logged out from Veeam Enterprise Manager")
    
    except Exception as e:
        log_step(workflow_logs, vdc_name, "Logout from Veeam Enterprise Manager", "failure", str(e))
        raise e
    finally:
        conn.close()
    
    return {"workflow_logs": workflow_logs}