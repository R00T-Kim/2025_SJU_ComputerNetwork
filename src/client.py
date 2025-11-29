"""
HTTP chat client using raw sockets.
Team Info: <fill team name / members / roles>
"""
import argparse
import json
import socket
import threading
import time
import urllib.parse


def http_request(host, port, method, path, body_dict=None):
    body_bytes = b""
    headers = {
        "Host": f"{host}:{port}",
        "Connection": "close",
    }
    if body_dict is not None:
        body_bytes = json.dumps(body_dict).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
    else:
        headers["Content-Length"] = "0"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        request_lines = [f"{method} {path} HTTP/1.1"]
        for k, v in headers.items():
            request_lines.append(f"{k}: {v}")
        request_lines.extend(["", ""])
        request_head = "\r\n".join(request_lines).encode("utf-8")
        sock.sendall(request_head + body_bytes)

        status, resp_headers, resp_body = _read_http_response(sock)
        return status, resp_headers, resp_body


def _read_http_response(sock):
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk

    if b"\r\n\r\n" not in buffer:
        raise RuntimeError("Malformed HTTP response")

    header_bytes, body = buffer.split(b"\r\n\r\n", 1)
    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split("\r\n")
    status_line = lines[0]
    parts = status_line.split(" ", 2)
    if len(parts) < 2:
        raise RuntimeError("Bad status line")
    status = int(parts[1])
    headers = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    content_length = int(headers.get("content-length", "0") or 0)
    while len(body) < content_length:
        more = sock.recv(4096)
        if not more:
            break
        body += more
    return status, headers, body[:content_length]


def poll_events(host, port, channel, since_ref, running_flag):
    while running_flag["running"]:
        path = f"/events?channel={urllib.parse.quote(channel)}&since={since_ref['value']}"
        try:
            status, _, body = http_request(host, port, "GET", path)
            if status == 200 and body:
                data = json.loads(body.decode("utf-8"))
                events = data.get("events", [])
                latest = data.get("latest", since_ref["value"])
                if events:
                    since_ref["value"] = max(e.get("id", since_ref["value"]) for e in events)
                    for event in events:
                        _print_event(event)
                else:
                    since_ref["value"] = max(since_ref["value"], latest)
            else:
                time.sleep(1)
        except Exception as e:
            print(f"[poll] error: {e}")
            time.sleep(2)


def _print_event(event):
    etype = event.get("type")
    nick = event.get("nick")
    channel = event.get("channel")
    if etype == "message":
        text = event.get("text", "")
        print(f"[{channel}] <{nick}> {text}")
    elif etype == "join":
        print(f"[{channel}] {nick} joined")
    elif etype == "part":
        print(f"[{channel}] {nick} left")


def main():
    parser = argparse.ArgumentParser(description="HTTP chat client (raw sockets)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--channel", default="# 일반")
    parser.add_argument("--nick", default="Guest")
    args = parser.parse_args()

    # Join channel first
    status, _, body = http_request(args.host, args.port, "POST", "/join", {"nick": args.nick, "channel": args.channel})
    if status != 200:
        print(f"Join failed ({status}): {body.decode('utf-8', errors='ignore')}")
        return
    print(f"Joined {args.channel} as {args.nick}")

    running_flag = {"running": True}
    since_ref = {"value": 0}
    poll_thread = threading.Thread(target=poll_events, args=(args.host, args.port, args.channel, since_ref, running_flag), daemon=True)
    poll_thread.start()

    try:
        while True:
            msg = input("> ")
            if msg.strip() in ("/quit", "/exit"):
                break
            if msg.strip().startswith("/part"):
                http_request(args.host, args.port, "POST", "/part", {"nick": args.nick, "channel": args.channel})
                print(f"Left {args.channel}")
                break
            if not msg.strip():
                continue
            status, _, resp_body = http_request(
                args.host,
                args.port,
                "POST",
                "/message",
                {"nick": args.nick, "channel": args.channel, "text": msg},
            )
            if status != 200:
                print(f"[send error] {status}: {resp_body.decode('utf-8', errors='ignore')}")
    except KeyboardInterrupt:
        pass
    finally:
        running_flag["running"] = False
        http_request(args.host, args.port, "POST", "/part", {"nick": args.nick, "channel": args.channel, "reason": "client exit"})
        time.sleep(0.2)
        print("bye")


if __name__ == "__main__":
    main()
