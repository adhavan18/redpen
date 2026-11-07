# QC 1: research and factual accuracy
Lesson: HTTP Requests and Responses (v1), generated 2026-11-07 14:58

- claims checked: 26 (supported 25, partial 0, unsupported 1, contradicted 0); accuracy 96%
- verifier quotes found verbatim in sources: 25/26
- code examples run: 1/1 print what the lesson claims
- live http probes: 6/6 confirmed
- copied passages (12+ words): 1
- sources cited: 8 (1 tier A)

## Claims

| verdict | claim | evidence |
|---|---|---|
| unsupported | HTTP request method names are strictly case-sensitive. | : "" (quote not verified) |
| supported | The GET method is used to retrieve data from a server without modifying the target resource. | S6: "The HTTP GET method is used to retrieve data from the server without modifying it." |
| supported | GET sends parameters appended directly to the URL as query parameters. | S6: "In this method, data is sent through the URL as query parameters" |
| supported | GET is defined as a safe method that is intended to be read-only with no effect on server state. | S8: "The methods GET, HEAD, OPTIONS, TRACE, and QUERY are defined as safe. In other words, safe methods are intended to be read-only." |
| supported | GET requests can be bookmarked and stored in browser history because data is included in the URL. | S6: "GET requests can be bookmarked and stored in browser history." |
| supported | Sending sensitive parameters in the address bar via GET compromises security. | S6: "Output: Data passed in GET method is clearly visible in the address bar, which can compromise the security." |
| supported | A successful GET response returns a representation of the target resource. | S1: "GET: the target resource" |
| supported | The POST method is used to send data from the client to the server to create or update resources. | S6: "POST is used to send data to the server for creating or updating resources." |
| supported | POST transfers data inside the request body rather than in the URL. | S6: "Data is sent through the request body." |
| supported | POST is classified as an unsafe method because it may modify server state or produce side effects. | S8: "In contrast, the methods POST, PUT, DELETE, CONNECT, and PATCH are not safe. They may modify the state of the server or have other effects s" |
| supported | All valid HTTP status codes fall in the range of 100 to 599 inclusive. | S1: "All valid status codes are within the range of 100 to 599, inclusive." |
| supported | The first digit of an HTTP status code defines the response category. | S1: "The first digit of the status code defines the class of response. The last two digits do not have any categorization role." |
| supported | Unrecognized status codes must be treated as equivalent to the base status code of their class based on the first digit. | S1: "However, a client MUST understand the class of any status code, as indicated by the first digit, and treat an unrecognized status code as be" |
| supported | 1xx status codes indicate that the request was received and processing is continuing. | S7: "These codes indicate that the server has received the request and is continuing to process it." |
| supported | 2xx status codes confirm that the client's request was successfully received, understood, and accepted. | S1: "The 2xx (Successful) class of status code indicates that the client's request was successfully received, understood, and accepted." |
| supported | 3xx status codes indicate that further action must be taken by the client to complete the request. | S1: "Further action needs to be taken in order to complete the request" |
| supported | 4xx status codes indicate that the request cannot be fulfilled due to bad syntax or client-side issues. | S13: "he 4xx class indicates that the request contains bad syntax or cannot be fulfilled due to an error on the client's side." |
| supported | 5xx status codes indicate that the server failed to fulfill an apparently valid request due to an internal server issue. | S8: "5XX server error
The server failed to fulfill an apparently valid request." |
| supported | Server implementations in practice are not technically restricted from altering state during a GET request. | S8: "Despite the prescribed safety of GET requests, in practice their handling by the server is not technically limited in any way." |
| supported | A server handler can modify a database during a GET request if poorly implemented. | S8: "It is perfectly possible to write a web application in which (for example) a database insert or other non-idempotent action is triggered by " |
| supported | Both GET and POST transmit data in plain text unless encrypted with TLS/HTTPS. | S9: "- Lack of security: Data is transmitted in plain text, making it vulnerable to attacks like man-in-the-middle." |
| supported | HTTP status codes are extensible. | S1: "HTTP status codes are extensible." |
| supported | Clients must understand the category indicated by the first digit of an HTTP status code. | S1: "However, a client MUST understand the class of any status code, as indicated by the first digit" |
| supported | An unrecognized code like 471 must be treated as equivalent to 400 Bad Request. | S1: "For example, if a client receives an unrecognized status code of 471,
 it can see from the first digit that there was something wrong with i" |
| supported | Bad request syntax or client-side issues yield 4xx Client Error codes. | S13: "he 4xx class indicates that the request contains bad syntax or cannot be fulfilled due to an error on the client's side." |
| supported | A 5xx status code indicates a server-side error where the server failed to fulfill an apparently valid request. | S8: "5XX server error
The server failed to fulfill an apparently valid request." |

## Code execution

- s4 (python): **pass** - output matches the lesson

## Live probes

- GET https://jsonplaceholder.typicode.com/posts/1 -> 200 (expected 200-299): confirmed
- GET https://jsonplaceholder.typicode.com/posts?userId=1 -> 200 (expected 200-299): confirmed
- POST https://jsonplaceholder.typicode.com/posts -> 201 (expected 201-201): confirmed
- POST https://httpbin.org/post -> 200 (expected 200-299): confirmed
- GET https://httpbin.org/redirect/1 -> 302 (expected 300-399): confirmed
- GET https://jsonplaceholder.typicode.com/posts/999999 -> 404 (expected 400-499): confirmed

## Sources

| id | tier | cited | source |
|---|---|---|---|
| S1 | A | 35 | [HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) |
| S2 | A | 0 | [HTTP response status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) |
| S3 | A | 0 | [HTTP: Hypertext Transfer Protocol](https://developer.mozilla.org/en-US/docs/Web/HTTP) |
| S4 | A | 0 | [HTTP](https://openlibrary.org/works/OL16026044W) |
| S5 | A | 0 | [Computer networking](https://openlibrary.org/works/OL56272W) |
| S6 | B | 22 | [Difference between HTTP GET and POST Methods - GeeksforGeeks](https://www.geeksforgeeks.org/php/difference-between-http-get-and-post-methods/) |
| S7 | B | 13 | [HTTP Status Codes - GeeksforGeeks](https://www.geeksforgeeks.org/computer-networks/what-are-http-status-codes/) |
| S8 | B | 34 | [HTTP - Wikipedia](https://en.wikipedia.org/wiki/HTTP) |
| S9 | B | 7 | [Hypertext Transfer Protocol - HTTP - GeeksforGeeks](https://www.geeksforgeeks.org/html/what-is-http/) |
| S10 | B | 0 | [HTTP Request and Response Cycle in Express.js - GeeksforGeeks](https://www.geeksforgeeks.org/web-tech/request-and-response-cycle-in-express-js/) |
| S11 | C | 5 | [HTTP Status Codes — Complete Reference for RFC 9110](https://www.jpkc.com/db/en/cheatsheets/networking/http-status/) |
| S12 | C | 1 | [HTTP Methods Explained: GET, POST, PUT, PATCH & DELETE | DevWithTools](https://devwithtools.org/blog/http-methods-explained) |
| S13 | C | 7 | [Complete reference table of all HTTP response status codes (1xx–5xx) w](https://gist.github.com/rjoydip/3e30666e42b8de5b48141bc3573ed963) |
| S14 | C | 0 | [content/files/en-us/web/http/reference/status/index.md at main · mdn/c](https://github.com/mdn/content/blob/main/files/en-us/web/http/reference/status/index.md?plain=1) |

## Findings

### F1 [medium] copied text (open)
where: s2; found by: check

1 passage(s) of 12+ words match a source word for word

evidence: "post method is used to send data from the client to the server for creating or updating resources"

suggested fix: paraphrase these passages and keep the citation

### F2 [medium] unsupported claim (open)
where: s2; found by: llm

"HTTP request method names are strictly case-sensitive." is not backed by any research source.

evidence: None of the provided evidence mentions whether HTTP request method names are case-sensitive.

suggested fix: HTTP request method names are generally written in uppercase.

## Checks that could not run

- google-grounded check skipped: google-grounded check failed after retries: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more informatio
