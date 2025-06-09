import json
import http.client
import urllib.parse
import ssl
from urllib.parse import urlencode

def handler(context, inputs):
    # Veeam B&R Server Details
    user = ".\\stage_pfe"
    print(user)
    passw = "xxxxxxxxx"
    print(passw)
    url = "172.16.205.206:9419"
    endpoint = "/api/oauth2/token"

    # Compose full URL
    sessions_url = f"https://{url}{endpoint}"
    parsed_url = urllib.parse.urlparse(sessions_url)

    # Establish HTTPS connection
    conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, context=ssl._create_unverified_context())

    # Headers and payload
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-api-version": "1.1-rev2"
    }
    payload = urlencode({
        "grant_type": "password",
        "username": user,
        "password": passw
    })

    # Send request
    conn.request("POST", parsed_url.path, body=payload, headers=headers)
    response = conn.getresponse()
    body = response.read().decode()
    conn.close()

    if response.status == 200:
        token = json.loads(body).get("access_token")
        print("Authentication successful. Access Token acquired.")
        print("VBR Token =",token)
    else:
        print(f"Authentication failed: {response.status} {response.reason}")
