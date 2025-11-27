import json
import socket
import threading
import os
import traceback

try:
    from src.channel_manager import ChannelManager
    from src.http_utils import parse_http_request, parse_query, parse_multipart_data, send_json, send_response, send_file
except ImportError:
    from channel_manager import ChannelManager
    from http_utils import parse_http_request, parse_query, parse_multipart_data, send_json, send_response, send_file

HOST = "0.0.0.0"
PORT = 8080
UPLOAD_DIR = "uploads"

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
            filename = path_only.replace("/uploads/", "")
            filepath = os.path.join(UPLOAD_DIR, filename)
            # 경로 조작 방지
            if ".." in filename or filename.startswith("/"):
                send_response(conn, 403, "Forbidden", "Invalid path")
            else:
                send_file(conn, filepath)
            return

        if method == "GET" and path_only == "/channels":
            channels = channel_manager.list_channels()
            send_json(conn, 200, {"channels": channels})

        elif method == "GET" and path_only == "/users":
            users = channel_manager.get_all_users()
            send_json(conn, 200, {"users": users})

        elif method == "POST" and path_only == "/join":
            data = json.loads(body.decode("utf-8"))
            members, event = channel_manager.join_channel(data.get("channel"), data.get("nick"))
            send_json(conn, 200, {"status": "joined", "members": members, "event_id": event["id"]})

        elif method == "POST" and path_only == "/message":
            data = json.loads(body.decode("utf-8"))
            event = channel_manager.post_message(
                data.get("channel"), data.get("nick"), data.get("text"), data.get("msg_type", "text")
            )
            if event:
                send_json(conn, 200, {"status": "sent", "event_id": event["id"]})
            else:
                send_response(conn, 400, "Bad Request", "Join channel first")

        elif method == "GET" and path_only == "/events":
            events, latest = channel_manager.wait_events(
                query.get("channel"), int(query.get("since", 0))
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
                    # 파일명 안전하게 변경
                    safe_name = f"{int(os.path.getmtime(UPLOAD_DIR))}_{fname.replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR, safe_name)

                    with open(filepath, "wb") as f:
                        f.write(fcontent)

                    # 업로드 성공 로그
                    print(f"[UPLOAD] Saved {len(fcontent)} bytes to {safe_name}")

                    url = f"http://localhost:{PORT}/uploads/{safe_name}"
                    send_json(conn, 200, {"url": url})
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
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind((HOST, PORT))
    except OSError:
        print(f"[ERROR] Port {PORT} is use. Change PORT.")
        return

    server_sock.listen(20)
    print(f"[HTTP] Server running on {HOST}:{PORT}")

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