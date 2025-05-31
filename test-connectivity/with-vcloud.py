import json
import http.client
import urllib.parse
import base64
import ssl

def handler(context, inputs):
    #Vcloud Director Details
    user = "stage-pfe"
    passw = "k'HvD1bb:yekI%"
    url = "172.16.106.4"
    endpoint = "/cloudapi/1.0.0/sessions/provider"
    #encode cred in base64 for basic auth
    auth_string = f"{user}@system:{passw}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    #parse the url
    sessions_url = f"https://{url}{endpoint}"
    parsed_url = urllib.parse.urlparse(sessions_url)
    #establish https connection
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context())
    #prepare headers for auth
    headers = {
        "Accept": "application/*;version=39.0",
        "Authorization": f"Basic {encoded_auth}"
    }
    #send auth request
    conn.request("POST", parsed_url.path, headers=headers)
    response=conn.getresponse()
    #get session token
    if response.status == 200:
        vcd_token = response.getheader("X-VMWARE-VCLOUD-ACCESS-TOKEN")
        print("Authentication successful! to vCloud")
        print("Token= ",vcd_token)
    else:
        print("Authentication failed:", response.status, response.reason)
    conn.close()
    
