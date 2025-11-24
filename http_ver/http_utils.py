import json
import urllib.parse

CRLF = "\r\n"


def parse_http_request(sock):
    """
    Very small HTTP/1.1 request parser for a single request per connection.
    Returns (method, path, version, headers, body_bytes).
    """
    buffer = b""
    # Read until header terminator
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk

    if b"\r\n\r\n" not in buffer:
        raise ValueError("Incomplete HTTP headers")

    header_bytes, body = buffer.split(b"\r\n\r\n", 1)
    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split(CRLF)
    if not lines or len(lines[0].split()) < 3:
        raise ValueError("Invalid request line")

    method, path, version = lines[0].split()[:3]
    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or 0)
    while len(body) < content_length:
        more = sock.recv(4096)
        if not more:
            break
        body += more

    return method, path, version, headers, body[:content_length]


def send_response(sock, status, reason, body, content_type="text/plain", headers=None):
    if headers is None:
        headers = {}
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers_out = {
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = [
        f"HTTP/1.1 {status} {reason}",
        *[f"{k}: {v}" for k, v in headers_out.items()],
        "",
        "",
    ]
    response_head = CRLF.join(header_lines).encode("utf-8")
    sock.sendall(response_head + body)


def send_json(sock, status, payload):
    body = json.dumps(payload)
    send_response(sock, status, _reason_phrase(status), body, content_type="application/json")


def parse_query(path):
    parsed = urllib.parse.urlparse(path)
    query = urllib.parse.parse_qs(parsed.query)
    # Flatten query values (take first)
    simple_query = {k: v[0] for k, v in query.items() if v}
    return parsed.path, simple_query


def _reason_phrase(status):
    phrases = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }
    return phrases.get(status, "OK")
