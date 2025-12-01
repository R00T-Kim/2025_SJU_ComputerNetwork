# ==============================================================================
# Team Information
# ------------------------------------------------------------------------------
# 21011659 김근호 (Backend Core Developer)
# 21011582 한현준 (Data & Channel Manager)
# 21011673 한상민 (Frontend & Integration Developer)
# 21011650 이규민 (QA & Documentation Specialist)
# ==============================================================================

import json
import socket
import threading
import os
import time
import traceback
import urllib.parse

try:
    from src.channel_manager import ChannelManager
    from src.http_utils import parse_http_request, parse_query, parse_multipart_data, send_json, send_response, send_file
except ImportError:
    from channel_manager import ChannelManager
    from http_utils import parse_http_request, parse_query, parse_multipart_data, send_json, send_response, send_file

HOST = "::"  # IPv6/IPv4 모두 수용 (dual-stack 시도)
PORT = 8080
# 업로드 경로는 프로젝트 루트 기준으로 고정해 CWD에 영향을 받지 않도록 함
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

channel_manager = ChannelManager()

def handle_client(conn, addr):
    try:
        parsed = parse_http_request(conn)
        if not parsed or parsed[0] is None:
            return

        method, path, version, headers, body = parsed
        path_only, query = parse_query(path)

        # print(f"[REQ] {method} {path_only}") # 디버깅용

        if method == "OPTIONS":
            send_response(conn, 200, "OK", "")
            return

        if method == "GET" and path_only.startswith("/uploads/"):
            raw_name = path_only.replace("/uploads/", "")
            filename = urllib.parse.unquote(raw_name)
            filepath = os.path.join(UPLOAD_DIR, filename)
            # 경로 조작 방지
            if ".." in filename or filename.startswith("/"):
                send_response(conn, 403, "Forbidden", "Invalid path")
            else:
                send_file(conn, filepath)
            return

        if method == "GET" and path_only == "/channels":
            channels = channel_manager.list_channels(query.get("nick"))
            send_json(conn, 200, {"channels": channels})

        elif method == "GET" and path_only == "/users":
            users = channel_manager.get_all_users()
            send_json(conn, 200, {"users": users})

        elif method == "POST" and path_only == "/join":
            data = json.loads(body.decode("utf-8"))
            members, event = channel_manager.join_channel(data.get("channel"), data.get("nick"))
            send_json(conn, 200, {"status": "joined", "members": members, "event_id": event["id"]})

        elif method == "POST" and path_only == "/leave":
            data = json.loads(body.decode("utf-8"))
            nick = data.get("nick")
            channel = data.get("channel")
            if channel:
                ok = channel_manager.part_channel(channel, nick, reason="leaving")
            else:
                ok = channel_manager.leave_all(nick, reason="leaving")
            if ok:
                send_json(conn, 200, {"status": "left"})
            else:
                send_response(conn, 400, "Bad Request", "Not in channel")

        elif method == "POST" and path_only == "/message":
            data = json.loads(body.decode("utf-8"))
            event = channel_manager.post_message(
                data.get("channel"),
                data.get("nick"),
                data.get("text"),
                data.get("msg_type", "text"),
                data.get("file_name")
            )
            if event:
                send_json(conn, 200, {"status": "sent", "event_id": event["id"]})
            else:
                send_response(conn, 400, "Bad Request", "Join channel first")

        elif method == "POST" and path_only == "/presence":
            data = json.loads(body.decode("utf-8"))
            channel_manager.set_focus(data.get("nick"), data.get("active", False))
            send_json(conn, 200, {"status": "ok"})

        elif method == "GET" and path_only == "/events":
            events, latest = channel_manager.wait_events(
                query.get("channel"), int(query.get("since", 0)), query.get("nick")
            )
            send_json(conn, 200, {"events": events, "latest": latest})

        elif method == "POST" and path_only == "/upload":
            ctype = headers.get("content-type", "")
            if "boundary=" in ctype:
                # [중요 수정] boundary 파싱 시 뒤에 붙은 ; charset 등 제거
                boundary = ctype.split("boundary=")[1].split(";")[0].strip()

                parts = parse_multipart_data(body, boundary)

                if 'file' in parts:
                    fname, fcontent = parts['file']
                    fname = os.path.basename(fname)
                    # 파일명 안전하게 변경 (timestamp_prefix_originalname)
                    safe_name = f"{int(time.time() * 1000)}_{fname.replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR, safe_name)

                    with open(filepath, "wb") as f:
                        f.write(fcontent)

                    # 업로드 성공 로그
                    print(f"[UPLOAD] Saved {len(fcontent)} bytes to {filepath}")

                    req_host = headers.get("host", f"localhost:{PORT}")
                    url = f"http://{req_host}/uploads/{safe_name}"
                    send_json(conn, 200, {"url": url, "filename": fname, "saved_as": safe_name})
                else:
                    print("[UPLOAD FAIL] No file part found")
                    send_response(conn, 400, "Bad Request", "No file found")
            else:
                send_response(conn, 400, "Bad Request", "Not multipart")

        else:
            send_response(conn, 404, "Not Found", "Unknown Endpoint")

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        try:
            send_response(conn, 500, "Internal Error", str(e))
        except: pass
    finally:
        try: conn.close()
        except: pass

def start_server():
    server_sock = None
    last_error = None

    # IPv6 우선, 실패 시 IPv4로 fallback
    families = [socket.AF_INET6, socket.AF_INET] if ":" in HOST else [socket.AF_INET]

    for family in families:
        try:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                try:
                    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # dual-stack 허용
                except OSError:
                    pass
                bind_addr = (HOST, PORT, 0, 0)
            else:
                bind_addr = ("0.0.0.0" if HOST == "::" else HOST, PORT)

            s.bind(bind_addr)
            server_sock = s
            break
        except OSError as e:
            last_error = e
            continue

    if server_sock is None:
        print(f"[ERROR] Failed to bind on {HOST}:{PORT} ({last_error})")
        return

    server_sock.listen(128)
    print(f"[HTTP] Server running on {HOST}:{PORT} (family={server_sock.family})")

    try:
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        server_sock.close()

if __name__ == "__main__":
    start_server()
