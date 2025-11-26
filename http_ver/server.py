"""
HTTP-based chat server using raw sockets (no frameworks).
Team Info: <fill team name / members / roles>
"""
import json
import socket
import threading

from http_ver.channel_manager import ChannelManager
from http_ver.http_utils import parse_http_request, parse_query, send_json, send_response

HOST = "0.0.0.0"
PORT = 8080

channel_manager = ChannelManager()


def handle_client(conn, addr):
    try:
        method, path, version, headers, body = parse_http_request(conn)
        path_only, query = parse_query(path)

        if method == "GET" and path_only == "/channels":
            channels = channel_manager.list_channels()
            send_json(conn, 200, {"channels": channels})

        if method == "OPTIONS":
            send_response(conn, 200, "OK", "")
            return
        
        elif method == "POST" and path_only == "/join":
            payload = _parse_json(body)
            nick = payload.get("nick")
            channel = payload.get("channel")
            if not nick or not channel:
                return _bad_request(conn, "nick and channel are required")
            members, event = channel_manager.join_channel(channel, nick)
            send_json(conn, 200, {"status": "joined", "channel": channel, "nick": nick, "members": members, "event_id": event["id"]})

        elif method == "POST" and path_only == "/part":
            payload = _parse_json(body)
            nick = payload.get("nick")
            channel = payload.get("channel")
            if not nick or not channel:
                return _bad_request(conn, "nick and channel are required")
            ok = channel_manager.part_channel(channel, nick, reason=payload.get("reason", "leaving"))
            if not ok:
                return _bad_request(conn, "not in channel")
            send_json(conn, 200, {"status": "parted", "channel": channel, "nick": nick})

        elif method == "POST" and path_only == "/message":
            payload = _parse_json(body)
            nick = payload.get("nick")
            channel = payload.get("channel")
            text = payload.get("text", "")
            if not nick or not channel or not text.strip():
                return _bad_request(conn, "nick, channel, text are required")
            event = channel_manager.post_message(channel, nick, text.strip())
            if not event:
                return _bad_request(conn, "join the channel first")
            send_json(conn, 200, {"status": "sent", "event_id": event["id"]})

        elif method == "GET" and path_only == "/events":
            channel = query.get("channel")
            if not channel:
                return _bad_request(conn, "channel is required")
            since = 0
            if "since" in query:
                try:
                    since = int(query.get("since", "0"))
                except ValueError:
                    return _bad_request(conn, "since must be an integer")
            events, latest = channel_manager.wait_events(channel, since)
            send_json(conn, 200, {"events": events, "latest": latest})

        else:
            send_response(conn, 404, "Not Found", "Not Found")
    except ValueError as ve:
        _bad_request(conn, str(ve))
    except Exception as e:
        send_response(conn, 500, "Internal Server Error", f"error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _parse_json(body_bytes):
    if not body_bytes:
        return {}
    try:
        return json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JSON")


def _bad_request(conn, msg):
    send_response(conn, 400, "Bad Request", json.dumps({"error": msg}), content_type="application/json")


def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(16)
    print(f"[HTTP] Chat server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server_sock.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[HTTP] Server shutting down...")
    finally:
        server_sock.close()


if __name__ == "__main__":
    start_server()
