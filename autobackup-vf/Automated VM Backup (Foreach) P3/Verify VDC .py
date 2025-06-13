import json
import http.client
import urllib.parse
import ssl

def fetch_all_pages(base_url, headers):
    page = 1
    page_size = 30
    all_items = []
    while True:
        url = f"{base_url}?page={page}&pageSize={page_size}"
        parsed_url = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed_url.hostname, context=ssl._create_unverified_context(), timeout=10)
        try:
            conn.request("GET", parsed_url.path + "?" + parsed_url.query, headers=headers)
            response = conn.getresponse()
            
            if response.status != 200:
                error_msg = f"Failed to fetch data: {response.status} {response.reason}"
                raise Exception(error_msg)
            
            data = json.loads(response.read().decode())
            items = data.get("values", [])
            all_items.extend(items)
            total_items = data.get("resultTotal", len(all_items))
            if len(all_items) >= total_items or not items:
                break
            page += 1
        except Exception as e:
            raise e
        finally:
            conn.close()
    return all_items
def handler(context, inputs):
    vCloud_token = inputs.get("vCloud_token")
    url = inputs.get("vCloud_ip")
    vdc_names = inputs.get("vdc_names")  # List of VDC names to verify
    
    if not vCloud_token:
        error_msg = "No vCD token provided"
        raise Exception(error_msg)
    
    if not vdc_names:
        error_msg = "No VDC names provided for verification"
        raise Exception(error_msg)
    
    headers = {"Accept": "application/json;version=39.0", "Authorization": f"Bearer {vCloud_token}"}
    vdc_url = f"https://{url}/cloudapi/1.0.0/vdcs"
    
    # Fetch all VDCs from vCloud
    vdcs = fetch_all_pages(vdc_url, headers)
    existing_vdc_names = {vdc["name"].lower() for vdc in vdcs if "name" in vdc}
    
    # Verify which input VDC names exist
    valid_vdc_names = [name.lower() for name in vdc_names if name.lower() in existing_vdc_names]
    print("vdc names =",valid_vdc_names)
    return {
        "vdc_list": valid_vdc_names
    }
