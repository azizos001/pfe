var categoryPath = "/Reports";
var logFileName = "backup_workflow_logs.json";
const today = new Date();
const formattedDate = today.toISOString().split('T')[0];
var reportFileName = formattedDate + "_backup_workflow_report.md";

// Step 1: Read the logs from the resource element
var resourceCategory = Server.getResourceElementCategoryWithPath(categoryPath);
if (!resourceCategory) {
    throw "Error: Resource Category not found!";
}

var logResourceElement = null;
for (var i in resourceCategory.resourceElements) {
    if (resourceCategory.resourceElements[i].name == logFileName) {
        logResourceElement = resourceCategory.resourceElements[i];
        break;
    }
}

if (!logResourceElement) {
    throw "Error: Log file 'backup_workflow_logs.json' not found!";
}

var logs = [];
var mimeAttachment = logResourceElement.getContentAsMimeAttachment();
if (mimeAttachment && mimeAttachment.content) {
    try {
        logs = JSON.parse(mimeAttachment.content);
    } catch (e) {
        throw "Error parsing log data: " + e;
    }
}

// Step 1.5: Filter logs for today
var todayStr = new Date().toISOString().substring(0, 10); // e.g., "2025-05-02"
var todayLogs = logs.filter(function(log) {
    if (!log.timestamp) return false;
    var logDate = log.timestamp.substring(0, 10);
    return logDate === todayStr;
});

// Step 2: Analyze the filtered logs and generate the report
var reportLines = [];
reportLines.push("# Automated VM Backup Workflow Report");
var date = new Date();
date.setHours(date.getHours() + 1);
reportLines.push("**Generated on:** " + date.toISOString());
reportLines.push("");

// Group logs by VDC and count totalSteps
var vdcLogs = {};
var totalSteps = 0; // Count only non-"N/A" steps
for (var i in todayLogs) {
    var log = todayLogs[i];
    var vdcName = log["vdc_name"];
    if (vdcName !== "N/A") {
        totalSteps++;
    }
    if (!vdcLogs[vdcName]) {
        vdcLogs[vdcName] = [];
    }
    vdcLogs[vdcName].push(log);
}

var successfulSteps = 0;
var vdcCount = 0;
var totalVmsBackedUp = 0;

reportLines.push("## Summary");

// Count VDCs and new VMs added
for (var vdcName in vdcLogs) {
    if (vdcName === "N/A") continue;
    vdcCount++;
    var vdcLogEntries = vdcLogs[vdcName];
    for (var j in vdcLogEntries) {
        var log = vdcLogEntries[j];
        if (log.step === "Add VMs to Job" && log.status === "success") {
            var details = log.details;
            if (typeof details === "object" && details.vms_added && Array.isArray(details.vms_added)) {
                totalVmsBackedUp += details.vms_added.length;
            }
        }
    }
}

// Detailed report by VDC
reportLines.push("## Detailed Report by VDC");
for (var vdcName in vdcLogs) {
    if (vdcName === "N/A") {
        continue; // Skip steps not associated with a specific VDC
    }
    reportLines.push("### VDC: " + vdcName);
    reportLines.push("#### Steps:");

    var vdcLogEntries = vdcLogs[vdcName];
    for (var j in vdcLogEntries) {
        var log = vdcLogEntries[j];
        var status = log["status"];
        if (status === "success") {
            successfulSteps++;
        } else if (status === "partial_success") {
            successfulSteps += 0.5; // Count as half a success for partial successes
        }

        reportLines.push("- **Step:** " + log["step"]);
        reportLines.push("  - **Timestamp:** " + log["timestamp"]);
        reportLines.push("  - **Status:** " + status);

        var details = log["details"];
        if (typeof details === "object") {
            for (var key in details) {
                reportLines.push("  - **" + key + ":** " + JSON.stringify(details[key]));
            }
        } else {
            reportLines.push("  - **Details:** " + details);
        }
        reportLines.push("");
    }
}

// Update summary with additional metrics
var successRate = (totalSteps > 0) ? (successfulSteps / totalSteps * 100) : 0;
reportLines.splice(4, 0, "- **Success Rate:** " + successRate.toFixed(2) + "%");
reportLines.splice(5, 0, "- **VDCs Processed:** " + vdcCount);
reportLines.splice(6, 0, "- **VMs Backed Up:** " + totalVmsBackedUp);

// Step 3: Store the report in a resource element
var reportContent = reportLines.join("\n");
var reportResourceElement = null;
for (var i in resourceCategory.resourceElements) {
    if (resourceCategory.resourceElements[i].name == reportFileName) {
        reportResourceElement = resourceCategory.resourceElements[i];
        break;
    }
}

if (!reportResourceElement) {
    reportResourceElement = Server.createResourceElement(resourceCategory, reportFileName, mime);
}

var mime = new MimeAttachment();
mime.name = reportFileName;
mime.mimeType = "text/markdown";
mime.content = reportContent;
reportResourceElement.setContentFromMimeAttachment(mime);

report = reportContent;
outputString = report;
outputString = reportFileName;
