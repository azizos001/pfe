var file_Name = PVDC_name + ".json";
var Categorypath = "/VDCS";
var vdc_name = PVDC_name;

// Function to log to workflow_logs
function logToWorkflowLogs(workflow_logs, stepName, status, details) {
    workflow_logs.push({
        "timestamp": new Date(new Date().getTime() + 60 * 60 * 1000).toISOString(),
        "vdc_name": VDC_name,
        "step": stepName,
        "status": status,
        "details": details
    });
}

// Main logic
try {
    var resourceCategory = Server.getResourceElementCategoryWithPath(Categorypath);
    if (!resourceCategory) {
        throw "Error: Resource Category not found!";
    }
    
    // Search for the specific resource element
    var resourceElement = null;
    var resources = resourceCategory.resourceElements;
    for (var i in resources) {
        if (resources[i].name == file_Name) {
            resourceElement = resources[i];
            break;
        }
    }
    
    if (!resourceElement) {
        System.log("Resource Element " + file_Name + " not found in the category " + Categorypath + ". Creating a new one...");
        resourceElement = Server.createResourceElement(resourceCategory, file_Name, mime);
        logToWorkflowLogs(workflow_logs, "Check Resource Element", "success", "Resource element not found, created new: " + file_Name);
    } else {
        logToWorkflowLogs(workflow_logs, "Check Resource Element", "success", "Resource element found: " + file_Name);
    }
    
    // Read existing content
    var oldContent = [];
    var mimeAttachment = resourceElement.getContentAsMimeAttachment();
    if (mimeAttachment && mimeAttachment.content) {
        var existingData = mimeAttachment.content;
        try {
            oldContent = JSON.parse(existingData);
            if (!Array.isArray(oldContent)) {
                oldContent = []; // Fallback if parsed data isn't an array
                logToWorkflowLogs(workflow_logs, "Read Existing VMs", "warning", "Parsed data is not an array, resetting to empty array");
            } else {
                logToWorkflowLogs(workflow_logs, "Read Existing VMs", "success", "Existing VMs read successfully, count: " + oldContent.length);
            }
        } catch (error) {
            logToWorkflowLogs(workflow_logs, "Read Existing VMs", "failure", "Error parsing existing JSON data: " + error);
            throw "Error parsing existing JSON data: " + error;
        }
    } else {
        logToWorkflowLogs(workflow_logs, "Read Existing VMs", "success", "No existing VMs found (first run)");
    }
    
    // Validate and parse vms_list if it's a JSON string
    var vms_list_array = [];
    if (typeof vms_list === "string") {
        try {
            vms_list_array = JSON.parse(vms_list);
            if (!Array.isArray(vms_list_array)) {
                throw new Error("Parsed vms_list is not an array");
            }
        } catch (error) {
            logToWorkflowLogs(workflow_logs, "Parse vms_list", "failure", "Error parsing vms_list as JSON: " + error);
            throw "Error parsing vms_list: " + error;
        }
    } else if (Array.isArray(vms_list)) {
        vms_list_array = vms_list;
    } else {
        logToWorkflowLogs(workflow_logs, "Parse vms_list", "failure", "vms_list is neither a string nor an array");
        throw "Invalid vms_list input";
    }
    logToWorkflowLogs(workflow_logs, "Parse vms_list", "success", "vms_list processed, count: " + vms_list_array.length);
    // Find new VMs
    var oldVms = oldContent.map(function(vm) { return vm.id; });
    var addedVMs = vms_list_array.filter(function(vm) { 
        return oldVms.indexOf(vm.id) == -1; 
    });
    var missingVMs = oldContent.filter(function(vm) { 
        var found = false;
        for (var i = 0; i < vms_list_array.length; i++) {
            if (vms_list_array[i].id === vm.id) {
                found = true;
                break;
            }
        }
        return !found;
    });
    if (addedVMs.length == 0 && missingVMs.length == 0) {
        switch_1 = 0;
        logToWorkflowLogs(workflow_logs, "Compare VMs", "success", "No new or missing VMs found , VMs match existing data in the Resource element");
    } else if (vms_list_array.length == addedVMs.length && missingVMs.length == 0) {
        switch_1 = 1;
        logToWorkflowLogs(workflow_logs, "Compare VMs", "success", "All VMs are new, count: " + addedVMs.length);
    } else if (addedVMs.length == 0 && missingVMs.length > 0) {
        switch_1 = -2;
        logToWorkflowLogs(workflow_logs, "Compare VMs", "warning", "Only Missing VMs found, count: " + missingVMs.length);
        logToWorkflowLogs(workflow_logs, "Detect Missing VMs", "info", "Missing VMs: " + JSON.stringify(missingVMs.map(function(vm) { return vm.name; })));
    } else {
        switch_1 = -1;
        logToWorkflowLogs(workflow_logs, "Compare VMs", "success", "New VMs found: " + addedVMs.length + ", Missing VMs found: " + missingVMs.length);
        if (missingVMs.length > 0) {
            logToWorkflowLogs(workflow_logs, "Detect Missing VMs", "info", "Missing VMs: " + JSON.stringify(missingVMs.map(function(vm) { return vm.name; })));
        }
    }
    // Update the resource element with the current VM list
    var mime = new MimeAttachment();
    mime.name = file_Name;
    mime.mimeType = "application/json";
    mime.content = JSON.stringify(vms_list_array, null, 4);
    resourceElement.setContentFromMimeAttachment(mime);
    logToWorkflowLogs(workflow_logs, "Update Resource Element", "success", "Resource element updated with current VM list, count: " + vms_list_array.length);
} catch (error) {
    logToWorkflowLogs(workflow_logs, "Compare and Store", "failure", "Error in Compare and Store: " + error);
    throw error;
}