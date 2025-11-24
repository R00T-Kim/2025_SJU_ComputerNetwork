"""
HTTP-based RPS Arena server (raw sockets).
Team Info: <fill team name / members / roles>
"""
import argparse
import json
import socket
import threading
import time
import atexit

from RPS.http_utils import parse_http_request, parse_query, send_json, send_response, reason_phrase
from RPS.state import GameState

HOST = "0.0.0.0"
PORT = 9090

state = GameState()


def _parse_json(body):
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        raise ValueError("invalid json")


def _require_user(token):
    user = state.auth(token)
    if not user:
        raise PermissionError("invalid token")
    return user


def handle_client(conn, addr):
    try:
        method, path, version, headers, body = parse_http_request(conn)
        path_only, query = parse_query(path)
        # Routes
        if method == "POST" and path_only == "/account/create":
            payload = _parse_json(body)
            ok, token, user = state.create_account(payload.get("username", ""), payload.get("password", ""))
            if not ok:
                send_json(conn, 400, {"error": token})
            else:
                send_json(conn, 201, {"token": token, "user": user})

        elif method == "POST" and path_only == "/account/login":
            payload = _parse_json(body)
            ok, token, user = state.login(payload.get("username", ""), payload.get("password", ""))
            if not ok:
                send_json(conn, 400, {"error": token})
            else:
                send_json(conn, 200, {"token": token, "user": user})

        elif method == "GET" and path_only == "/lobby/state":
            token = query.get("token", "")
            user = _require_user(token)
            resp = state.lobby_state(user)
            send_json(conn, 200, resp)

        elif method == "POST" and path_only == "/lobby/chat":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            text = payload.get("text", "").strip()
            if not text:
                return _bad_request(conn, "text required")
            msg = state.add_lobby_chat(user, text)
            send_json(conn, 201, {"message": msg})

        elif method == "GET" and path_only == "/lobby/chat":
            since = int(query.get("since", "0") or 0)
            msgs, latest = state.lobby_chat_since(since)
            send_json(conn, 200, {"messages": msgs, "latest": latest})

        elif method == "POST" and path_only == "/arena/create":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            ok, msg, arena = state.create_arena(user, payload.get("name", ""))
            if not ok:
                return _bad_request(conn, msg)
            send_json(conn, 201, {"arena": arena.to_summary(state.users), "role": user.role})

        elif method == "POST" and path_only == "/arena/join":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            try:
                arena_id = int(payload.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            role = payload.get("role", "spectator")
            ok, msg, arena = state.join_arena(user, arena_id, role)
            if not ok:
                return _bad_request(conn, msg)
            send_json(conn, 200, {"arena": arena.to_summary(state.users), "role": user.role})

        elif method == "POST" and path_only == "/arena/leave":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            try:
                arena_id = int(payload.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            state.leave_arena(user, arena_id, reason="left")
            send_json(conn, 200, {"status": "left"})

        elif method == "POST" and path_only == "/arena/move":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            try:
                arena_id = int(payload.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            move = payload.get("move", "")
            ok, msg = state.submit_move(user, arena_id, move)
            if not ok:
                return _bad_request(conn, msg)
            send_json(conn, 200, {"status": "submitted"})

        elif method == "GET" and path_only == "/arena/state":
            token = query.get("token", "")
            user = _require_user(token)
            try:
                arena_id = int(query.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            data = state.get_arena_state(arena_id)
            if not data:
                send_response(conn, 404, "Not Found", "arena not found")
            else:
                send_json(conn, 200, data)

        elif method == "GET" and path_only == "/arena/chat":
            try:
                arena_id = int(query.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            since = int(query.get("since", "0") or 0)
            msgs, latest = state.arena_chat_since(arena_id, since)
            send_json(conn, 200, {"messages": msgs, "latest": latest})

        elif method == "POST" and path_only == "/arena/chat":
            payload = _parse_json(body)
            user = _require_user(payload.get("token", ""))
            try:
                arena_id = int(payload.get("arena_id"))
            except Exception:
                return _bad_request(conn, "arena_id required")
            text = payload.get("text", "").strip()
            if not text:
                return _bad_request(conn, "text required")
            msg = state.add_arena_chat(user, arena_id, text)
            send_json(conn, 201, {"message": msg})

        else:
            send_response(conn, 404, "Not Found", "not found")
    except PermissionError as pe:
        send_response(conn, 401, "Unauthorized", json.dumps({"error": str(pe)}), content_type="application/json")
    except ValueError as ve:
        _bad_request(conn, str(ve))
    except Exception as e:
        send_response(conn, 500, "Internal Server Error", f"error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _bad_request(conn, msg):
    send_response(conn, 400, "Bad Request", json.dumps({"error": msg}), content_type="application/json")


def start_server(host: str = HOST, port: int = PORT):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(32)
    print(f"[RPS] Server listening on {host}:{port}")

    def _cleanup():
        state.save_users()
        try:
            server_sock.close()
        except Exception:
            pass

    atexit.register(_cleanup)

    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[RPS] Server shutting down...")
    finally:
        _cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP RPS Arena server (raw sockets)")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    start_server(args.host, args.port)
