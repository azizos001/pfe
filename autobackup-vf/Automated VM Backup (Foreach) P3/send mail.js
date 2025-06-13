// vRO Scriptable Task: sendEmailNotification
// Sends a simple, professional email notification with a summary of the Automated VM Backup Workflow
// including VDC names and configurable steps (e.g., "Add VMs to Job", "Verify Added VMs"),
// with separate tables for each VDC and VDC names as headings, and attaches the full report file
// Inputs:
// - reportContent: string - Markdown report from the generate_report step
// - resourceCategoryPath: string - Path to resource category (e.g., "/Reports")
// - reportFileName: string - Name of the report file (e.g., "2025-05-18_backup_workflow_report.md")
// - smtpHost: string - SMTP host (e.g., "smtp.gmail.com")
// - smtpPort: number - SMTP port (e.g., 587)
// - username: string - SMTP username (e.g., "user@domain.com")
// - password: SecureString - SMTP password
// - fromName: string - Sender's name (e.g., "Veeam Automation")
// - fromAddress: string - Sender's email (e.g., "automation@domain.com")
// - toAddressList: Array/string - Recipient email addresses (e.g., ["admin@domain.com"])
// - subject: string - Email subject (e.g., "VM Backup Workflow Report")
// - useSsl: boolean - Use SSL for SMTP
// - useStartTls: boolean - Use STARTTLS for SMTP
// - ccList: Array/string - Optional CC recipients
// - bccList: Array/string - Optional BCC recipients
// - companyLogoUrl: string - URL to company logo image (e.g., "https://yourcompany.com/logo.png")
// - companyName: string - Company name for branding (e.g., "Your Company")
// - companyWebsite: string - Company website URL for footer (e.g., "https://yourcompany.com")

// Function to convert array to comma-separated string
function convertToComaSeparatedList(arrayList) {
    if (!arrayList || (Array.isArray(arrayList) && arrayList.length === 0)) {
        return null;
    }
    if (!Array.isArray(arrayList)) {
        arrayList = [arrayList];
    }
    return arrayList.join(",");
}

// Custom function to pad numbers with leading zeros
function pad(number) {
    return (number < 10 ? "0" : "") + number;
}

// Function to clean and format details
function cleanDetails(detail) {
    // Remove leading/trailing whitespace, "Details:**", and markdown syntax (**)
    return detail.replace(/^Details:\*\*/i, '').replace(/^\*\*|\*\*$/g, '').trim();
}

// Function to extract summary metrics, VDC names, and specified steps from markdown and generate HTML
function markdownToHtml(markdown, companyName, companyLogoUrl, companyWebsite) {
    if (!markdown) {
        return "<html><body><p>No report content provided for today.</p></body></html>";
    }

    // Collect data first
    var lines = markdown.split("\n");
    var summarySection = false;
    var vdcSection = false;
    var inStepSection = false;
    var successRate = "N/A";
    var vdcProcessed = "N/A";
    var vmsBackedUp = "N/A";
    var vdcNames = [];
    var currentVdc = null;
    var stepsByVdc = {}; // Object to store steps for each VDC

    // Define the steps to include in the table (you can modify this list)
    var stepsToInclude = ["Check Resource Element" ,"Get All VMs", "Compare VMs" ,"Detect Missing VMs", "Find PVDC Compute Policy" ,"Search Job ID" ,"Create Backup Job", "Add VMs to Job" , "Verify Added VMs" , "Verify VMs"];

    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();

        // Extract summary metrics
        if (line.indexOf("## Summary") === 0) {
            summarySection = true;
            continue;
        }
        if (summarySection && line.indexOf("## ") === 0) {
            summarySection = false;
            continue;
        }
        if (summarySection && line.indexOf("- ") === 0) {
            var match = line.substring(2).match(/\*\*(.*?):\*\* (.*)/);
            if (match) {
                var key = match[1];
                var value = match[2];
                if (key === "Success Rate") successRate = value;
                if (key === "VDCs Processed") vdcProcessed = value;
                if (key === "VMs Backed Up") vmsBackedUp = value;
            }
        }

        // Extract VDC names and steps
        if (line.indexOf("### VDC: ") === 0) {
            currentVdc = line.substring(9).trim();
            vdcNames.push(currentVdc);
            vdcSection = true;
            inStepSection = false;
            if (!stepsByVdc[currentVdc]) {
                stepsByVdc[currentVdc] = [];
            }
            continue;
        }
        if (vdcSection && line.indexOf("#### Steps:") === 0) {
            inStepSection = true;
            continue;
        }
        if (inStepSection && line.indexOf("- **Step:** ") === 0) {
            var step = line.replace("- **Step:** ", "").trim();
            // Check if the step is in the list of steps to include
            var isIncludedStep = false;
            for (var j = 0; j < stepsToInclude.length; j++) {
                if (step === stepsToInclude[j]) {
                    isIncludedStep = true;
                    break;
                }
            }
            if (!isIncludedStep) {
                while (i + 1 < lines.length && lines[i + 1].trim().indexOf("  - ") === 0) {
                    i++; // Skip sub-lines
                }
                continue;
            }
            var timestampLine = "";
            var statusLine = "";
            var detailsLines = []; // Array to collect all detail lines
            if (i + 1 < lines.length) timestampLine = lines[++i].trim();
            if (i + 1 < lines.length) statusLine = lines[++i].trim();

            // Collect all subsequent detail lines (any line starting with "- **")
            while (i + 1 < lines.length && lines[i + 1].trim().indexOf("- **") === 0) {
                i++;
                detailsLines.push(cleanDetails(lines[i].trim().replace("- **", "").trim()));
            }

            if (timestampLine.indexOf("- **Timestamp:**") !== 0 || statusLine.indexOf("- **Status:**") !== 0) {
                continue;
            }

            var timestamp = escapeHtml(timestampLine.replace("- **Timestamp:**", "").trim());
            var status = escapeHtml(statusLine.replace("- **Status:**", "").trim());
            var statusLower = status.toLowerCase();
            var statusClass = statusLower === "success" ? "status-success" : "status-failure";
            var statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
            var details = detailsLines.length > 0 ? detailsLines.join("<br>") : "N/A"; // Join with line breaks

            stepsByVdc[currentVdc].push({
                step: step,
                timestamp: timestamp,
                status: statusLabel,
                statusClass: statusClass,
                details: details
            });
        }
    }

    // Start HTML with basic styling
    var html = "<html><head><style>" +
        "body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; }" +
        ".container { max-width: 1000px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }" +
        ".header { background: linear-gradient(to right, #005b96, #03396c); padding: 20px; text-align: center; color: #ffffff; }" +
        ".header img { max-width: 120px; }" +
        ".content { padding: 20px; }" +
        "h1 { color: #03396c; font-size: 24px; margin-bottom: 10px; }" +
        "h2 { color: #03396c; font-size: 20px; margin-top: 20px; }" +
        "h3 { color: #03396c; font-size: 18px; margin-top: 15px; }" +
        "p { color: #333333; line-height: 1.6; }" +
        ".summary-box { background-color: #e8f0fe; padding: 15px; border-radius: 6px; margin-bottom: 20px; }" +
        "table { width: 100%; border-collapse: collapse; margin: 10px 0; border: 1px solid #e0e0e0; }" +
        "th, td { padding: 12px; text-align: left; border: 1px solid #e0e0e0; }" +
        "th { background-color: #f8f9fa; font-weight: bold; }" +
        ".status-success { color: #28a745; font-weight: bold; }" +
        ".status-failure { color: #dc3545; font-weight: bold; }" +
        ".footer { background-color: #f4f6f8; padding: 15px; text-align: center; font-size: 12px; color: #666666; }" +
        ".footer a { color: #005b96; text-decoration: none; }" +
        "</style></head><body>" +
        "<div class=\"container\">" +
        "<div class=\"header\">" +
        (companyLogoUrl ? "<img src=\"" + escapeHtml(companyLogoUrl) + "\" alt=\"" + escapeHtml(companyName) + " Logo\" />" : "<h1>" + escapeHtml(companyName || 'Company') + "</h1>") +
        "</div>" +
        "<div class=\"content\">" +
        "<h1>Automated VM Backup Workflow Report</h1>";

    // Add date and greeting
    var date = new Date();
    var formattedDate = date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) + " " + pad(date.getHours()+1) + ":" + pad(date.getMinutes());
    html += "<p><strong>Generated on:</strong> " + formattedDate + "</p>" +
        "<p>Dear IT Team, below is a summary of today's VM Backup Workflow runs, followed by key steps for each VDC. The full report is attached for details.</p>";

    // Add summary box (before the tables)
    html += "<div class=\"summary-box\">" +
        "<h2>Summary</h2>" +
        "<p><strong>Success Rate:</strong> " + escapeHtml(successRate) + "</p>" +
        "<p><strong>VDCs Processed:</strong> " + escapeHtml(vdcProcessed) + "</p>" +
        "<p><strong>VMs Backed Up:</strong> " + escapeHtml(vmsBackedUp) + "</p>" +
        "<p><strong>VDCs:</strong> " + (vdcNames.length > 0 ? escapeHtml(vdcNames.join(", ")) : "None") + "</p>" +
        "</div>";

    // Add "Key Steps" heading and VDC tables
    if (Object.keys(stepsByVdc).length > 0) {
        html += "<h2>Key Steps</h2>";
        for (var vdc in stepsByVdc) {
            if (stepsByVdc[vdc].length > 0) {
                html += "<h3>" + escapeHtml(vdc) + "</h3>" +
                    "<table style=\"border: 1px solid #e0e0e0;\">" +
                    "<tr style=\"background-color: #f8f9fa;\"><th style=\"border: 1px solid #e0e0e0; padding: 12px;\">Step</th><th style=\"border: 1px solid #e0e0e0; padding: 12px;\">Timestamp</th><th style=\"border: 1px solid #e0e0e0; padding: 12px;\">Status</th><th style=\"border: 1px solid #e0e0e0; padding: 12px;\">Details</th></tr>";
                for (var k = 0; k < stepsByVdc[vdc].length; k++) {
                    var stepData = stepsByVdc[vdc][k];
                    html += "<tr style=\"border: 1px solid #e0e0e0;\">" +
                        "<td style=\"border: 1px solid #e0e0e0; padding: 12px;\">" + escapeHtml(stepData.step) + "</td>" +
                        "<td style=\"border: 1px solid #e0e0e0; padding: 12px;\">" + escapeHtml(stepData.timestamp) + "</td>" +
                        "<td style=\"border: 1px solid #e0e0e0; padding: 12px;\" class=\"" + escapeHtml(stepData.statusClass) + "\">" + escapeHtml(stepData.status) + "</td>" +
                        "<td style=\"border: 1px solid #e0e0e0; padding: 12px;\">" + stepData.details + "</td>" +
                        "</tr>";
                }
                html += "</table>";
            }
        }
    }

    // Close HTML
    html += "</div><div class=\"footer\">© " + new Date().getFullYear() + " " +
        (companyName ? escapeHtml(companyName) : "Your Company") +
        ". Visit us at <a href=\"" + escapeHtml(companyWebsite || "#") + "\">" +
        escapeHtml(companyWebsite || "our website") + "</a>.</div></div></body></html>";

    return html;
}

// Ensure escapeHtml is defined
function escapeHtml(unsafe) {
    if (!unsafe) return "";
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

try {
    var message = new EmailMessage();
    // Validate and configure SMTP settings
    if (!smtpHost) {
        throw new Error("SMTP host is required");
    }
    message.smtpHost = smtpHost;
    if (!smtpPort || smtpPort <= 0) {
        throw new Error("SMTP port is required and must be a positive number");
    }
    message.smtpPort = smtpPort;
    message.username = username;
    message.password = password;
    if (fromName) {
        message.fromName = fromName;
    }
    if (!fromAddress) {
        throw new Error("From address is required");
    }
    message.fromAddress = fromAddress;
    message.useSsl = !!useSsl;
    message.useStartTls = !!useStartTls;
    // Build address lists
    message.toAddress = convertToComaSeparatedList(toAddressList);
    if (!message.toAddress) {
        throw new Error("At least one recipient is required");
    }
    message.ccAddress = convertToComaSeparatedList(ccList);
    message.bccAddress = convertToComaSeparatedList(bccList);
    // Set subject
    message.subject = "VM Backup Workflow Report - " + new Date().toISOString().split("T")[0];
    // Generate HTML content with summary metrics, VDC names, and steps
    var htmlContent = markdownToHtml(report, companyName, companyLogoUrl, companyWebsite);
    message.addMimePart(htmlContent, "text/html; charset=UTF-8");
    var resourceCategoryPath = "/Reports"
    // Attach the full report file
    var resourceCategory = Server.getResourceElementCategoryWithPath(resourceCategoryPath);
    if (!resourceCategory) {
        throw new Error("Resource Category not found at path: " + resourceCategoryPath);
    }
    var reportResourceElement = null;
    for (var i in resourceCategory.resourceElements) {
        if (resourceCategory.resourceElements[i].name === reportFileName) {
            reportResourceElement = resourceCategory.resourceElements[i];
            break;
        }
    }
    if (!reportResourceElement) {
        throw new Error("Report file '" + reportFileName + "' not found!");
    }
    var mimeAttachment = reportResourceElement.getContentAsMimeAttachment();
    if (mimeAttachment && mimeAttachment.content) {
        message.addMimePart(mimeAttachment, mimeAttachment.mimeType);
        System.log("Attached full report: " + reportFileName);
    } else {
        throw new Error("Failed to retrieve content of report file: " + reportFileName);
    }
    // Log and send
    System.log("Sending email to host: " + message.smtpHost + ":" + message.smtpPort +
               ", from: " + message.fromAddress + ", to: " + message.toAddress);
    message.sendMessage();
    System.log("Email sent successfully");
} catch (e) {
    System.error("Failed to send email: " + e);
    throw e;
}