var categoryPath = "/Reports";
function pad(number) {
  return number < 10 ? '0' + number : number;
}
var date = new Date();
date.setHours(date.getHours() + 1); // Add 1 hour
var logFileName = "restore_workflow_logs_" +
  date.toISOString().split("T")[0] + "_" +
  pad(date.getHours()) + "_" +
  pad(date.getMinutes()) +
  ".json";
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
  System.log("Error: Resource Element '" + logFileName + "' not found in the category '" + categoryPath + "'. Creating a new one...");
  resourceElement = Server.createResourceElement(resourceCategory, logFileName, mime);
}

// Read existing logs
var log = [];
var mimeAttachment = resourceElement.getContentAsMimeAttachment();
if (mimeAttachment && mimeAttachment.content) {
  try {
    var logs = JSON.parse(mimeAttachment.content);
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
