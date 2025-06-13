var categoryPath = "/Reports";
var logFileName = "backup_workflow_logs.json";

// Get or create the resource category
var resourceCategory = Server.getResourceElementCategoryWithPath(categoryPath);
if (!resourceCategory) {
    throw "Error: Resource Category not found!";
}

// Search for the log file resource element
var resourceElement = null;
for (var i in resourceCategory.resourceElements) {
    if (resourceCategory.resourceElements[i].name == logFileName) {
        resourceElement = resourceCategory.resourceElements[i];
        break;
    }
}

// If the resource element doesn't exist, create it
if (!resourceElement) {
    System.log("Error : Resource Element "+logFileName+" not found in the category " + categoryPath+". Creating a new one...");
    //resourceElement = Server.createResourceElement(resourceCategory, logFileName, "application/json");
    resourceElement = Server.createResourceElement(resourceCategory,logFileName,mime);
}

// Read existing logs
var logs = [];
var mimeAttachment = resourceElement.getContentAsMimeAttachment();
if (mimeAttachment && mimeAttachment.content) {
    try {
        logs = JSON.parse(mimeAttachment.content);
    } catch (e) {
        System.log("Error parsing existing log data: " + e);
    }
}

// Append new logs from workflow_logs
if (workflow_logs && Array.isArray(workflow_logs)) {
    logs = logs.concat(workflow_logs);
} else {
    System.log("Warning: No new logs to append (workflow_logs is invalid)");
}

// Write the updated logs back to the resource element
var mime = new MimeAttachment();
mime.name = logFileName;
mime.mimeType = "application/json";
mime.content = JSON.stringify(logs, null, 4);
resourceElement.setContentFromMimeAttachment(mime);

System.log("Logs successfully written to resource element: " + logFileName);