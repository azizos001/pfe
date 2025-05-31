import json
import http.client
import urllib.parse
import base64
import ssl

def handler(context, inputs):
    veeam_url = "https://172.16.106.100:9398/api"
    user = ".\Stage-Pfe"
    passw = "dbfk9rdtECT+Om"
    #encode credentials for basic auth
    credentials = f"{user}:{passw}"
    encode_credentials = base64.b64encode(credentials.encode()).decode()
    #session URL
    parsed_url = urllib.parse.urlparse(veeam_url)
    session_url = f"{veeam_url}/sessionMngr/?=latest"
    parsed_url2 = urllib.parse.urlparse(session_url)
    
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context())
    #request headers
    headers = {
        "Authorization" : f"Basic {encode_credentials}",
        "Accept" : "application/json"
    }
    #send auth request
    conn.request("POST", parsed_url2.path + "?" + parsed_url2.query, headers=headers)
    response = conn.getresponse()
    print("response code=", response.status)
    if response.status == 201 :
        print("connected to veeam entreprise manager")
        token = response.getheader("X-RestSvcSessionId")
        print(f"token= {token}")
    else:
        print(f"Authentication failed: {response.status}")
        print(response.read().decode())
    #close conn
    conn.close()

    