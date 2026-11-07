# HTTP Requests and Responses

**Learning objective:** Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.

*Time: 44 minutes. Audience: first-year computer science undergraduates*

## What Happens When You Submit a Web Form?
*3 min*

Imagine typing your username into a web page or clicking a link to read an article. Behind the scenes, your browser relies on HTTP (Hypertext Transfer Protocol) to communicate with web servers [S6][S9]. But how does the server know whether you are trying to fetch a page or submit account credentials? And how does it report whether your request succeeded or failed? HTTP uses specific request methods to declare intended actions and status codes to report outcomes clearly [S6][S7][S11]. Understanding these mechanisms is essential for developing web applications and designing REST APIs [S7][S11].

## HTTP Request Methods: GET vs POST
*7 min*

An HTTP request specifies a method (sometimes called an HTTP verb) to classify the desired action to be performed on a target server resource [S8][S12]. Method names are strictly case-sensitive [S8].

### The GET Method
The GET method is primarily used to retrieve or fetch data from a server without modifying the target resource [S6][S9].
- **Data Transmission**: GET sends parameters appended directly to the URL as query parameters [S6].
- **Safety**: GET is defined as a safe method, meaning it is intended to be read-only and have no intended effect on server state [S8].
- **Browser Behavior**: Because data is included in the URL, GET requests can be bookmarked and stored in browser history [S6]. However, sending sensitive parameters (like passwords) in the address bar can compromise security [S6].
- **Response Content**: A successful GET response returns a representation of the target resource [S1][S11].

### The POST Method
The POST method is used to send data from the client to the server for creating or updating resources or processing data [S6][S9].
- **Data Transmission**: POST transfers data inside the request body rather than in the URL [S6].
- **Safety**: POST is classified as an unsafe method because it may modify server state or produce side effects (such as updating database records or sending emails) [S8].
- **Use Cases**: POST is suitable for submitting web forms, uploading files, or transmitting sensitive or large datasets [S6].
- **Response Content**: A successful POST response returns content representing the status of, or results obtained from, the action [S1][S11].

| Feature | GET Method | POST Method |
| --- | --- | --- |
| **Primary Purpose** | Retrieve / fetch data [S6][S9] | Submit / create / update data [S6][S9] |
| **Data Location** | Appended to URL query string [S6] | Sent inside request body [S6] |
| **Safety Class** | Safe (read-only, no server state modification) [S8] | Unsafe (may modify server state) [S8] |
| **Bookmarks & History** | Can be bookmarked and saved in history [S6] | Cannot be bookmarked directly [S6] |

> **Optional video:** [Hyper Text Transfer Protocol Crash Course - HTTP 1.0, 1.1, HTTP/2, HTTP/3](https://www.youtube.com/watch?v=0OrmKCB0UrQ&t=439s) by Hussein Nasser, 7:19-8:07 (0.8 min). Explains how clients specify HTTP methods like GET and POST when issuing web requests.

## HTTP Response Status Code Categories
*7 min*

When a server processes an HTTP request, it returns a three-digit integer status code describing the result and the semantics of the response [S1]. All valid status codes fall in the range of 100 to 599 inclusive [S1]. The first digit defines the response category, while the last two digits have no categorization role [S1].

Clients MUST understand the general class of any status code based on its first digit [S1][S8]. If a client receives an unrecognized status code (such as 471), it must treat it as equivalent to the base status code of that class (e.g., 400 Bad Request) [S1][S8].

### Status Code Categories

- **1xx (Informational)**: Indicates that the request was received and processing is continuing [S1][S7][S8]. Example: 100 Continue [S7][S11].
- **2xx (Successful)**: Confirms that the client's request was successfully received, understood, and accepted by the server [S1][S7][S8]. For example, `200 OK` indicates that the request has succeeded [S1].
- **3xx (Redirection)**: Indicates that further action must be taken by the client to complete the request [S1][S7][S8].
- **4xx (Client Error)**: Indicates that the request cannot be fulfilled due to bad syntax or an issue originating on the client side [S1][S8][S13]. Examples include invalid syntax or unauthorized access attempts [S1][S13].
- **5xx (Server Error)**: Indicates that the server failed to fulfill an apparently valid request due to an internal server issue [S1][S8][S13].

| Category | Category Name | Meaning / Cause |
| --- | --- | --- |
| **1xx** | Informational | Request received, continuing process [S1][S7][S8] |
| **2xx** | Successful | Request successfully received, understood, and accepted [S1][S7] |
| **3xx** | Redirection | Further action required to complete request [S1][S7][S8] |
| **4xx** | Client Error | Request contains bad syntax or client-side error [S1][S8][S13] |
| **5xx** | Server Error | Server failed to fulfill an apparently valid request [S1][S8] |

> **Optional video:** [HTTP Crash Course & Exploration](https://www.youtube.com/watch?v=iYM2zFP3Zn0&t=571s) by Traversy Media, 9:31-10:19 (0.8 min). Overview of HTTP response status code ranges including 200, 300, and 400 series.

## Executing GET and POST Requests in Python
*6 min*

Let's observe how GET and POST requests are issued programmatically and inspect their response status codes using Python's standard library `urllib.request`.

```python
import urllib.request
import urllib.parse
import json

# 1. Executing a GET request
url_get = "https://httpbin.org/get?user=alice&city=boston"
req_get = urllib.request.Request(url_get, method="GET")

with urllib.request.urlopen(req_get) as response:
    status_code = response.getcode()
    body = json.loads(response.read().decode())
    print(f"GET Status Code: {status_code}")
    print(f"GET Query Arguments: {body['args']}")

# 2. Executing a POST request
url_post = "https://httpbin.org/post"
data = urllib.parse.urlencode({"username": "bob", "role": "admin"}).encode("utf-8")
req_post = urllib.request.Request(url_post, data=data, method="POST")

with urllib.request.urlopen(req_post) as response:
    status_code = response.getcode()
    body = json.loads(response.read().decode())
    print(f"POST Status Code: {status_code}")
    print(f"POST Form Data: {body['form']}")
```

```output
GET Status Code: 200
GET Query Arguments: {'city': 'boston', 'user': 'alice'}
POST Status Code: 200
POST Form Data: {'role': 'admin', 'username': 'bob'}
```

Notice that the GET request appends data directly to the URL (`?user=alice&city=boston`) [S6]. In contrast, the POST request encodes the payload into bytes and sends it inside the HTTP request body [S6]. Both requests return a status code of 200, which belongs to the 2xx (Successful) category [S1][S7].

## Common Misconceptions About HTTP Methods and Status Codes
*5 min*

### Misconception 1: GET requests can never alter server state, and POST requests are inherently encrypted.
**Why it is tempting**: HTTP standards define GET as a safe, read-only method [S8]. Furthermore, POST parameters are hidden from the browser address bar [S6].
**What is actually true**: While the HTTP specification prescribes GET as safe, server implementation in practice is not technically restricted [S8]. A buggy server handler could modify a database during a GET request [S8]. Additionally, hiding parameters in a POST body does not encrypt them; both GET and POST transmit data in plain text unless encrypted with TLS/HTTPS [S9].

### Misconception 2: If a client receives an unassigned or custom status code, the application must crash.
**Why it is tempting**: Developers often expect applications to crash if a response code is not explicitly defined in a standard enum.
**What is actually true**: HTTP status codes are extensible [S1]. Clients are not required to understand every individual status code, but MUST understand the category indicated by the first digit [S1][S8]. For instance, an unrecognized code like `471` must be treated as equivalent to `400` (Bad Request) [S1][S8].

### Misconception 3: A 5xx status code means the client sent invalid request data.
**Why it is tempting**: When an HTTP request fails, developers frequently assume their request body or URL syntax was formatted incorrectly.
**What is actually true**: Bad request syntax or client-side issues yield 4xx (Client Error) codes [S1][S8][S13]. A 5xx status code indicates a server-side error where the server failed to fulfill an apparently valid request [S1][S8].

## Hands-on Request Analysis and Status Code Classification
*9 min*

Complete the following exercise independently or in pairs.

### Step 1: Request Method Selection
For each of the following scenarios, decide whether `GET` or `POST` is appropriate and justify your choice based on data placement and method safety [S6][S8]:
1. Fetching a public user profile page (`/users/view?id=42`).
2. Submitting a new account registration form containing a user's email and password.

### Step 2: Status Code Classification
Categorize each scenario outcome below into **2xx (Successful)**, **4xx (Client Error)**, or **5xx (Server Error)** [S1][S7][S8]:
1. A client attempts to fetch a page, but supplies an invalid authentication header.
2. A client sends a valid POST request, but the server's internal database connection drops unexpectedly.
3. A web crawler issues a valid GET request and receives the full HTML content of an article.
4. A client receives an unrecognized status code `429` from an API endpoint.

### Self-Check & Answers
- **Step 1.1**: `GET`, because fetching a profile page is a read-only retrieval operation that does not modify server state [S6][S8].
- **Step 1.2**: `POST`, because submitting account credentials sends sensitive data that should be placed in the request body and creates/modifies user state [S6][S8].
- **Step 2.1**: **4xx (Client Error)** — the client provided invalid request headers [S1][S13].
- **Step 2.2**: **5xx (Server Error)** — an apparently valid request failed due to a server-side failure [S1][S8].
- **Step 2.3**: **2xx (Successful)** — the request was successfully received, understood, and accepted [S1][S7].
- **Step 2.4**: **4xx (Client Error)** — an unrecognized 4xx code (429) must be interpreted as equivalent to 400 (Client Error) based on its first digit [S1][S8].

## Key Takeaways
*2 min*

- **GET vs. POST Methods**: GET retrieves data via URL parameters and is defined as a safe, read-only method; POST submits data inside the request body to create or update resources and may modify server state [S6][S8][S9].
- **Status Code Structure**: Status codes are three-digit integers where the first digit determines the response category [S1].
- **2xx Category**: Indicates that the request was successfully received, understood, and accepted (e.g., 200 OK) [S1][S7].
- **4xx Category**: Indicates client-side errors such as bad syntax or unauthorized requests [S1][S8][S13].
- **5xx Category**: Indicates server-side errors where the server fails to fulfill an apparently valid request [S1][S8].
- **Extensibility Rule**: Clients must understand the status class (first digit) and map unrecognized codes to the base `x00` code of that class [S1][S8].

## Knowledge check
*5 min*

**1. Which of the following correctly describes a structural distinction between HTTP GET and POST requests?**

- A) GET transfers data within the request body, whereas POST appends parameters to the URL.
- B) GET requests cannot be bookmarked by browsers, whereas POST requests are stored in browser history.
- C) GET sends parameters as part of the URL query string, whereas POST transfers parameters inside the request body.
- D) GET is an unsafe method intended to modify server state, whereas POST is strictly read-only.

**2. A web application form requires users to enter a new password. Why should the web developer configure the form to use POST instead of GET?**

- A) POST places sensitive form data inside the request body rather than displaying it in the browser URL bar.
- B) GET requests are restricted from sending text strings to web servers.
- C) GET automatically encrypts parameters, whereas POST sends plain text without TLS.
- D) POST is a safe method that guarantees no state changes occur on the backend server.

**3. An API client submits a valid request to an API endpoint. While processing the request, the server's internal database service crashes. Which status code category should the server return?**

- A) 3xx (Redirection)
- B) 5xx (Server Error)
- C) 4xx (Client Error)
- D) 2xx (Successful)

**4. A client sends an HTTP request containing malformed JSON syntax in its request payload. How should the server categorize its response status code?**

- A) 5xx class because any execution failure must be classified as a server error.
- B) 4xx class because the request contains bad syntax or a client-side error.
- C) 2xx class because the network packet was successfully delivered.
- D) 1xx class to request informational header updates from the client.

**5. A client receives an unrecognized HTTP status code of 471 from a server. According to the HTTP specification, how must the client handle this response?**

- A) Treat the response as equivalent to status code 400 (Bad Request).
- B) Crash the application because the status code is unregistered.
- C) Ignore the status code and assume the request succeeded with 200 OK.
- D) Treat the response as equivalent to status code 500 (Internal Server Error).

### Answers

1. **C**: GET parameters are appended directly to the URL as query parameters, whereas POST transfers parameters inside the HTTP request body [S6].
2. **A**: GET displays parameters directly in the browser address bar, which can compromise security. POST sends data inside the request body [S6].
3. **B**: 5xx status codes indicate that the server failed to fulfill an apparently valid request due to an internal server error [S1][S8].
4. **B**: 4xx status codes indicate client errors, including bad syntax or requests that cannot be fulfilled [S1][S8][S13].
5. **A**: Clients MUST understand the class of any status code based on its first digit and treat an unrecognized status code as equivalent to the x00 status code of that class (e.g., 471 becomes 400) [S1][S8].

## References

- **[S1]** HTTP Semantics. <https://www.rfc-editor.org/rfc/rfc9110.html> (tier A: IETF RFC (the standard itself))
- **[S6]** Difference between HTTP GET and POST Methods - GeeksforGeeks. <https://www.geeksforgeeks.org/php/difference-between-http-get-and-post-methods/> (tier B: tutorial site (uneven quality))
- **[S7]** HTTP Status Codes - GeeksforGeeks. <https://www.geeksforgeeks.org/computer-networks/what-are-http-status-codes/> (tier B: tutorial site (uneven quality))
- **[S8]** HTTP - Wikipedia. <https://en.wikipedia.org/wiki/HTTP> (tier B: encyclopedia (secondary, check citations))
- **[S9]** Hypertext Transfer Protocol - HTTP - GeeksforGeeks. <https://www.geeksforgeeks.org/html/what-is-http/> (tier B: tutorial site (uneven quality))
- **[S11]** HTTP Status Codes — Complete Reference for RFC 9110. <https://www.jpkc.com/db/en/cheatsheets/networking/http-status/> (tier C: unclassified site)
- **[S12]** HTTP Methods Explained: GET, POST, PUT, PATCH & DELETE | DevWithTools. <https://devwithtools.org/blog/http-methods-explained> (tier C: unclassified site)
- **[S13]** Complete reference table of all HTTP response status codes (1xx–5xx) with descriptions and MDN links — sourced from MDN Web Docs. Covers Informational, Successful, Redirection, Client Error, and Server Error classes with per-section context notes.. <https://gist.github.com/rjoydip/3e30666e42b8de5b48141bc3573ed963> (tier C: unclassified site)

**Videos**

- Hyper Text Transfer Protocol Crash Course - HTTP 1.0, 1.1, HTTP/2, HTTP/3 by Hussein Nasser <https://www.youtube.com/watch?v=0OrmKCB0UrQ&t=439s> (7:19-8:07)
- HTTP Crash Course & Exploration by Traversy Media <https://www.youtube.com/watch?v=iYM2zFP3Zn0&t=571s> (9:31-10:19)

**Further reading**

- HTTP, David Gourley, Brian Totty, Linda Mui (1997) <https://openlibrary.org/works/OL16026044W>
- Computer networking, James F. Kurose, Keith W. Ross (1900) <https://openlibrary.org/works/OL56272W>
