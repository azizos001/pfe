import http.client
import urllib.parse
import ssl
from datetime import datetime, timedelta

def handler(context, inputs):
    vCloud_token = inputs.get("vCloud_token")
    url = inputs.get("vCloud_ip")
    vdc_name = inputs.get("VDC_name")
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
            raise Exception(error_msg)
    except Exception as e:
        raise e
    finally:
        conn.close()
