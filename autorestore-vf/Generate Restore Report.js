var categoryPath = "/Reports";
function pad(number) {
    return number < 10 ? '0' + number : number;
}
var today = new Date();
today.setHours(today.getHours() + 1); // Add one hour
var formattedDate = today.toISOString().split('T')[0] + '_' + 
                    pad(today.getHours()) + ':' + 
                    pad(today.getMinutes());
var reportFileName = "restore_workflow_report_"+formattedDate+".md";

var type_restore = restore_type;
var selected_vms = selected_vms;
var vms_without_restore_points_list = vms_without_restore_points; // VMs without restore points
// Get or create the resource category
var resourceCategory = Server.getResourceElementCategoryWithPath(categoryPath);
if (!resourceCategory) {
    throw "Error: Resource Category not found at " + categoryPath + "!";
}

// Create a VM-to-VDC mapping
var vmToVdc = {};
if (Array.isArray(selected_vms)) {
    for (var i = 0; i < selected_vms.length; i++) {
        var vm = selected_vms[i];
        vmToVdc[vm.name] = vm.VDC; // Use "name" and "VDC" to match input
    }
} else {
    System.log("Warning: selected_vms is not an array, checking for wrapped array: " + JSON.stringify(selected_vms));
    if (selected_vms && selected_vms.selected_vms && Array.isArray(selected_vms.selected_vms)) {
        for (var i = 0; i < selected_vms.selected_vms.length; i++) {
            var vm = selected_vms.selected_vms[i];
            vmToVdc[vm.name] = vm.VDC;
        }
    } else {
        System.log("Error: No valid selected_vms array found: " + JSON.stringify(selected_vms));
    }
}

// Generate report from workflow_logs
var reportLines = [];
reportLines.push("# Automated VM Restore Workflow Report");
var date = new Date();
date.setHours(date.getHours() + 1); // Adjust for CET
reportLines.push("**Generated on:** " + date.toISOString());
reportLines.push("");

// Group logs by VDC using VM-to-VDC mapping
var vdcLogs = {};
var totalVmsProcessed = 0;
for (var i in workflow_logs) {
    var log = workflow_logs[i];
    var vmName = null;
    var vdcName = "N/A";
    // Check if context matches a VM name from selected_vms
    for (var j = 0; j < selected_vms.length; j++) {
        if (selected_vms[j].name === log.context) {
            vmName = log.context;
            vdcName = selected_vms[j].VDC;
            
            break;
        }
    }
    // If no VM match, context might be a VDC name (for VDC-level logs)
    if (!vmName && log.context !== "All VMs" && log.context !== "All VDCs") {
        vdcName = log.context;
    }
    if (!vdcLogs[vdcName]) {
        vdcLogs[vdcName] = [];
    }
    vdcLogs[vdcName].push(log);
    // Count total VMs processed only for VM-specific restore steps
    if ((log.step === "Start Restore" || log.step === "Start Instant Recovery") && vmName && vdcName !== "N/A") {
        totalVmsProcessed++;
    }
}

// Summary section
reportLines.push("## Summary");
reportLines.push("- **Restore Type:** " + type_restore);
reportLines.push("- **VDCs Processed:** " + Object.keys(vdcLogs).filter(function(vdc) { return vdc !== "N/A"; }).length);
reportLines.push("- **Total VMs Processed:** " + totalVmsProcessed);
reportLines.push("- **VMs Without Restore Points:** " + vms_without_restore_points_list.length);

// Detailed report by VDC
reportLines.push("## Detailed Report by VDC");
for (var vdcName in vdcLogs) {
    if (vdcName === "N/A") continue; // Skip global steps
    reportLines.push("### VDC: " + vdcName);
    reportLines.push("#### Restore Operations:");

    var vdcLogEntries = vdcLogs[vdcName];
    for (var j = 0; j < vdcLogEntries.length; j++) {
        var log = vdcLogEntries[j];
        var vmName = null;
        // Check if context matches a VM name from selected_vms
        for (var k = 0; k < selected_vms.length; k++) {
            if (selected_vms[k].name === log.context) {
                vmName = log.context;
                break;
            }
        }
        if (vmName && ((log.step === "Perform Restore" && type_restore === "Full VM Restore") || 
                       (log.step === "Perform Instant Recovery" && type_restore === "Instant Recovery"))) {
            reportLines.push("- **VM:** " + vmName);
            reportLines.push("  - **Step:** " + log.step);
            reportLines.push("  - **Timestamp:** " + log.timestamp);
            reportLines.push("  - **Status:** " + log.status);
            reportLines.push("  - **Details:** " + log.details);
            reportLines.push("");
        }
    }

    // List VMs without restore points for this VDC
    var vdcVmsWithoutPoints = [];
    for (var m = 0; m < vms_without_restore_points_list.length; m++) {
        if (vms_without_restore_points_list[m].vdc === vdcName) {
            vdcVmsWithoutPoints.push(vms_without_restore_points_list[m].vm_name + " on " + vms_without_restore_points_list[m].vdc + " with id " + vms_without_restore_points_list[m].vm_id);
        }
    }
    if (vdcVmsWithoutPoints.length > 0) {
        reportLines.push("#### VMs Without Restore Points:");
        for (var n = 0; n < vdcVmsWithoutPoints.length; n++) {
            reportLines.push("- " + vdcVmsWithoutPoints[n]);
        }
        reportLines.push("");
    }
}

// Store the report in a resource element
var reportContent = reportLines.join("\n");
System.log(reportContent);
var report = reportContent;
// Create a new resource element for the report
var reportResourceElement = null;
reportResourceElement = Server.createResourceElement(resourceCategory, reportFileName, mime);
var mime = new MimeAttachment();
mime.name = reportFileName;
mime.mimeType = "text/markdown";
mime.content = report;
try {
    reportResourceElement.setContentFromMimeAttachment(mime);
    System.log("Restore report successfully written to resource element: " + reportFileName);
} catch (e) {
    throw "Failed to write restore report to resource element: " + e;
}
