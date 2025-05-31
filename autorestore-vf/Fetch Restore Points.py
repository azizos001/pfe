import http.client
import ssl
import urllib.parse
import json
import base64
from datetime import datetime, timedelta

def log_step(workflow_logs, context, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "context": context if context else "All VMs",
        "step": step_name,
        "status": status,
        "details": details
    })

def make_api_request(conn, method, url, headers, body=None):
    parsed_url = urllib.parse.urlparse(url)
    conn.request(method, parsed_url.path + ("?" + parsed_url.query if parsed_url.query else ""), body=body, headers=headers)
    response = conn.getresponse()
    return response

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    veeam_url = inputs.get("veeam_url")
    selected_vms = inputs.get("selected_vms")
    selected_date = inputs.get("RP_Date")
    token = inputs.get("Token")
    vms_without_restore_points_list = []
    log_step(workflow_logs, "All VMs", "Authenticate Veeam", "success", "Authenticated successfully")

    headers = {
        "Accept": "application/json",
        "X-RestSvcSessionId": token,
        "Content-Type": "application/json"
    } 

    # Fetch backups
    backups_url = f"{veeam_url}/backups"
    conn = http.client.HTTPSConnection(urllib.parse.urlparse(backups_url).hostname, urllib.parse.urlparse(backups_url).port, context=ssl._create_unverified_context(),timeout=10)
    try:
        response = make_api_request(conn, "GET", backups_url, headers)
        if response.status != 200:
            error_msg = f"Failed to fetch backups: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, "All VMs", "Fetch Backups", "failure", error_msg)
            raise Exception(error_msg)
        backups_data = json.loads(response.read().decode())
        backups = backups_data.get("Refs")
        log_step(workflow_logs, "All VMs", "Fetch Backups", "success", f"Retrieved {len(backups)} backups")
    finally:
        conn.close()

    # Fetch all backup jobs
    jobs_url = f"{veeam_url}/jobs"
    conn = http.client.HTTPSConnection(urllib.parse.urlparse(jobs_url).hostname, urllib.parse.urlparse(jobs_url).port , context=ssl._create_unverified_context(),timeout=10)
    try:
        response = make_api_request(conn, "GET", jobs_url, headers)
        if response.status != 200:
            error_msg = f"Failed to fetch backup jobs: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, "All VMs", "Fetch Backup Jobs", "failure", error_msg)
            raise Exception(error_msg)
        jobs_data = json.loads(response.read().decode())
        jobs = jobs_data.get("Refs")
        log_step(workflow_logs, "All VMs", "Fetch Backup Jobs", "success", f"Retrieved {len(jobs)} backup jobs")
    finally:
        conn.close()

    # Map VMs to backups
    vm_backup_map = {}
    vm_vdc_map = {vm["id"]: vm["VDC"] for vm in selected_vms}  # Map VM ID to VDC
    for vm in selected_vms:
        vm_name = vm["name"]
        vm_id = vm["id"]
        vdc_name = vm["VDC"]
        matched = False
        for backup in backups:
            backup_name = backup["Name"]
            if " - " not in backup_name:
                continue
            job_name, vm_part = backup_name.split(" - ", 1)
            vm_base_name = vm_part.rsplit("-", 1)[0].strip() if "-" in vm_part else vm_part.strip()
            if vm_base_name.lower() != vm_name.lower():
                continue

            # Find the job ID by matching the job name
            job_id = None
            for job in jobs:
                if job["Name"] == job_name:
                    job_id = job["UID"]
                    break

            if not job_id:
                log_step(workflow_logs, vm_name, "Match VM to Backup", "warning", f"No job found for job name {job_name} in backup {backup_name}")
                continue

            # Fetch job includes to confirm VM ID
            job_vms_url = f"{veeam_url}/jobs/{job_id}/includes"
            conn = http.client.HTTPSConnection(urllib.parse.urlparse(job_vms_url).hostname, urllib.parse.urlparse(job_vms_url).port , context=ssl._create_unverified_context(),timeout=10)
            try:
                response = make_api_request(conn, "GET", job_vms_url, headers)
                if response.status != 200:
                    error_msg = f"Failed to fetch job VMs for {job_id}: {response.status} - {response.read().decode()}"
                    log_step(workflow_logs, vm_name, "Match VM to Backup", "warning", error_msg)
                    continue
                job_data = json.loads(response.read().decode())
                job_vms = job_data.get("ObjectInJobs")
                for job_vm in job_vms:
                    job_vm_id = job_vm["HierarchyObjRef"].split(".")[-1]
                    if job_vm_id == vm_id:
                        vm_backup_map[vm_id] = {
                            "full_name": vm_part,
                            "vm_name": vm_name,
                            "vm_id": vm_id
                        }
                        log_step(workflow_logs, vm_name, "Match VM to Backup", "success", f"Matched {vm_name} to backup {backup_name}")
                        matched = True
                        break
                if matched:
                    break
            finally:
                conn.close()
        if not matched:
            log_step(workflow_logs, vm_name, "Match VM to Backup", "warning", f"No backup found for {vm_name}")
            vms_without_restore_points_list.append({
                "vm_name": vm_name,
                "vm_id": vm_id,
                "vdc": vdc_name
            })
    # Fetch restore points
    restore_url = f"{veeam_url}/vmRestorePoints"
    conn = http.client.HTTPSConnection(urllib.parse.urlparse(restore_url).hostname, urllib.parse.urlparse(restore_url).port , context=ssl._create_unverified_context(),timeout=10)
    try:
        response = make_api_request(conn, "GET", restore_url, headers)
        if response.status != 200:
            error_msg = f"Failed to fetch restore points: {response.status} - {response.read().decode()}"
            log_step(workflow_logs, "All VMs", "Fetch Restore Points", "failure", error_msg)
            raise Exception(error_msg)
        restore_data = json.loads(response.read().decode())
        vm_restore_points = restore_data.get("Refs")
        log_step(workflow_logs, "All VMs", "Fetch Restore Points", "success", f"Retrieved {len(vm_restore_points)} restore points")
    finally:
        conn.close()

    # Filter and select restore points
    restore_points = []
    for vm_id, vm_info in vm_backup_map.items():
        full_name = vm_info["full_name"]
        vdc_name = vm_vdc_map.get(vm_id)
        matching_points = sorted(
            [rp for rp in vm_restore_points if rp["Name"].startswith(full_name + "@")],
            key=lambda x: x["Name"].split("@")[1],
            reverse=True
        )
        if not matching_points:
            log_step(workflow_logs, vm_name, "Filter Restore Points", "warning", f"No restore points for {full_name}")
            # Add VM to the list of VMs without restore points
            vms_without_restore_points_list.append({
                "vm_name": vm_info["vm_name"],
                "vm_id": vm_id,
                "vdc": vdc_name
            })
            continue

        # Default to no restore point selected
        restore_point = None
        log_msg = f"No restore points found for {full_name}"
        
        if selected_date:
            try:
                target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                daily_points = [
                    rp for rp in matching_points
                    if datetime.strptime(rp["Name"].split("@")[1].split(" ")[0], "%Y-%m-%d").date() == target_date
                ]
                if daily_points:
                    restore_point = daily_points[0]
                    log_msg = f"Selected restore point for {full_name} on {target_date}"
                else:
                    log_msg = f"No restore points for {full_name} on {target_date}"
                    log_step(workflow_logs, vm_name, "Select Restore Point", "warning", log_msg)
                    # Add VM to the list of VMs without restore points
                    vms_without_restore_points_list.append({
                        "vm_name": vm_info["vm_name"],
                        "vm_id": vm_id,
                        "vdc": vdc_name
                    })
                    continue
            except ValueError:
                log_msg = f"Invalid date {selected_date} for {full_name}"
                log_step(workflow_logs, vm_name, "Select Restore Point", "warning", log_msg)
                # Add VM to the list of VMs without restore points
                vms_without_restore_points_list.append({
                    "vm_name": vm_info["vm_name"],
                    "vm_id": vm_id,
                    "vdc": vdc_name
                })
                continue
        else:
            # If no selected_date is provided, use the latest restore point
            restore_point = matching_points[0]
            log_msg = f"Using latest restore point for {full_name}"

        # Only append if a restore point was selected
        if restore_point:
            restore_points.append({
                "vm_name": vm_info["vm_name"],
                "vm_id": vm_id,
                "restore_point_id": restore_point["UID"],
                "creation_time": restore_point["Name"].split("@")[1],
                "vdc": vdc_name
            })
            log_step(workflow_logs, vm_name, "Select Restore Point", "success", log_msg)

    print("restore_points = ", restore_points)
    # Add warning log if some VMs have no restore points
    total_vms = len(selected_vms)      
    vms_with_restore_points = len(restore_points)
    vms_without_restore_points = total_vms - vms_with_restore_points
    if vms_without_restore_points > 0:
        vm_names_without_restore = [vm["vm_name"] for vm in vms_without_restore_points_list]
        log_step(
            workflow_logs,
            "All VMs",
            "Finalize Restore Points",
            "warning",
            f"{vms_without_restore_points} out of {total_vms} VMs had no restore points: {', '.join(vm_names_without_restore)}"
        )
    print("VMs without restore points = ", vms_without_restore_points)
    print("VMs without restore points details = ", vms_without_restore_points_list)

    # Update the return statement to include the list
    log_step(workflow_logs, "All VMs", "Finalize Restore Points", "success", f"Processed {len(restore_points)} restore points")
    return {
        "restore_points": restore_points,
        "workflow_logs": workflow_logs,
        "vms_without_restore_points": vms_without_restore_points_list
    }