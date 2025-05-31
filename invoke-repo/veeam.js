//prepare request
//Do not edit 
var inParamtersValues = [];
var request = restOperation.createRequest(inParamtersValues, content);
//set the request content type
request.contentType = "application\/json";
System.log("Request: " + request);

//Customize the request here
//request.setHeader("headerName", "headerValue");

//execute request
//Do not edit 
var response = request.execute();
//prepare output parameters
System.log("Response: " + response);
statusCode = response.statusCode;
statusCodeAttribute = statusCode;
System.log("Status code: " + statusCode);
contentLength = response.contentLength;
headers = response.getAllHeaders();
contentAsString = response.contentAsString;

var accessToken = headers["X-RestSvcSessionId"];
if (accessToken) {
    System.log("Retrieved Token");
} else {
    System.log("Error: No token found in response headers");
}