from datetime import datetime, timedelta

def log_step(workflow_logs, vdc_name, step_name, status, details):
    workflow_logs.append({
        "timestamp": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "context": vdc_name if vdc_name else "All VDCs",
        "step": step_name,
        "status": status,
        "details": details
    })

def handler(context, inputs):
    workflow_logs = inputs.get("workflow_logs")
    vms_list = inputs.get("vms_list")
    vms_list_user = inputs.get("vms_list_user")


    vm_lookup = {(vm["name"], vm["VDC"]): vm for vm in vms_list}
    vm_list_selected = []

    for selected_vm in vms_list_user:
        selected_name, selected_vdc = selected_vm.split(" on ", 1)
        key = (selected_name, selected_vdc)
        vm_list_selected.append(vm_lookup[key])  # assume always valid

    #One log per VDC
    unique_vdcs = {vm["VDC"] for vm in vm_list_selected}
    for vdc in sorted(unique_vdcs):
        log_step(workflow_logs, vdc, "Select VMs", "success", f"VMs selected in VDC: {vdc}")

    #Final summary log
    log_step(workflow_logs, None, "Select VMs", "success", f"Selected {len(vm_list_selected)} out of {len(vms_list_user)} VMs")
    print("VM list selected = ",vm_list_selected)
    return {"selected_vms": vm_list_selected, "workflow_logs": workflow_logs}
