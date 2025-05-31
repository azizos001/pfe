// Input parameters (in production, use vRO input parameters or Configuration Elements)
var veeamUsername = user;
var veeamPassword = pass;

// Prepare the request body (form-urlencoded)
var body = "grant_type=password&username=" + encodeURIComponent(veeamUsername) + "&password=" + encodeURIComponent(veeamPassword);

// Prepare request
var inParametersValues = [];
var request = restOperation.createRequest(inParametersValues, body);

// Set the request content type and headers
request.contentType = "application/x-www-form-urlencoded";
request.setHeader("Accept", "application/json");
request.setHeader("x-api-version", "1.1-rev2");

//System.log("Request URL: " + request.fullUrl);

// Execute request
var response = request.execute();

// Prepare output parameters
System.log("Response: " + response);
statusCode = response.statusCode;
statusCodeAttribute = statusCode;
System.log("Status code: " + statusCode);
contentLength = response.contentLength;
headers = response.getAllHeaders();
contentAsString = response.contentAsString;
//System.log("Content as string: " + contentAsString);

// Parse and extract the access token (if successful)
var accessToken = null;
if (statusCode == 200 && contentAsString) {
    try {
        var jsonResponse = JSON.parse(contentAsString);
        accessToken = jsonResponse.access_token;
        System.log("Retrieved Token");
    } catch (e) {
        System.log("Error parsing JSON response: " + e);
    }
} else {
    System.log("Failed to retrieve token. Status code: " + statusCode);
}