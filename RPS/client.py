"""
HTTP RPS Arena client (terminal, raw sockets).
Team Info: <fill team name / members / roles>
"""
import argparse
import json
import socket
import threading
import time


CRLF = "\r\n"


def http_request(host, port, method, path, body_dict=None):
    body_bytes = b""
    headers = {"Host": f"{host}:{port}", "Connection": "close"}
    if body_dict is not None:
        body_bytes = json.dumps(body_dict).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body_bytes))
    else:
        headers["Content-Length"] = "0"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        lines = [f"{method} {path} HTTP/1.1"] + [f"{k}: {v}" for k, v in headers.items()] + ["", ""]
        sock.sendall(CRLF.join(lines).encode("utf-8") + body_bytes)
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
        raise RuntimeError("bad response")
    header_bytes, body = buffer.split(b"\r\n\r\n", 1)
    lines = header_bytes.decode("iso-8859-1").split("\r\n")
    status_line = lines[0].split()
    if len(status_line) < 2:
        raise RuntimeError("bad status line")
    status = int(status_line[1])
    headers = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    cl = int(headers.get("content-length", "0") or 0)
    while len(body) < cl:
        more = sock.recv(4096)
        if not more:
            break
        body += more
    return status, headers, body[:cl]


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.token = None
        self.user = None
        self.arena_id = None
        self.role = None

        self.lobby_chat_since = 0
        self.arena_chat_since = 0
        self.poll_stop = threading.Event()
        self.last_arenas_repr = None

    # --------------- Auth flows -----------------
    def create_account(self):
        username = input("New username: ").strip()
        password = input("New password: ").strip()
        status, _, body = http_request(self.host, self.port, "POST", "/account/create", {"username": username, "password": password})
        if status in (200, 201):
            data = json.loads(body.decode("utf-8"))
            self.token = data["token"]
            self.user = data["user"]
            print(f"Account created. Logged in as {self.user['nickname']}")
        else:
            print(f"Create failed: {body.decode('utf-8', errors='ignore')}")

    def login(self):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        status, _, body = http_request(self.host, self.port, "POST", "/account/login", {"username": username, "password": password})
        if status == 200:
            data = json.loads(body.decode("utf-8"))
            self.token = data["token"]
            self.user = data["user"]
            print(f"Welcome {self.user['nickname']} (winrate {self.user['winrate']}%)")
        else:
            print(f"Login failed: {body.decode('utf-8', errors='ignore')}")

    # --------------- Lobby -----------------
    def start_lobby(self):
        self.poll_stop.clear()
        threading.Thread(target=self._poll_lobby_state, daemon=True).start()
        threading.Thread(target=self._poll_lobby_chat, daemon=True).start()
        print("Lobby commands: /create <name>, /join <arena_id> <player|spectator>, /chat <msg>, /quit")
        while True:
            cmd = input("lobby> ").strip()
            if cmd.startswith("/create "):
                self._create_arena(cmd[len("/create "):])
            elif cmd.startswith("/join "):
                parts = cmd.split()
                if len(parts) >= 3:
                    arena_id = parts[1]
                    role = parts[2]
                    self._join_arena(arena_id, role)
                    if self.arena_id:
                        self._enter_arena_loop()
                else:
                    print("usage: /join <arena_id> <player|spectator>")
            elif cmd.startswith("/chat "):
                self._send_lobby_chat(cmd[len("/chat "):])
            elif cmd == "/quit":
                self.poll_stop.set()
                return
            else:
                print("commands: /create, /join, /chat, /quit")

    def _poll_lobby_state(self):
        while not self.poll_stop.is_set():
            try:
                status, _, body = http_request(self.host, self.port, "GET", f"/lobby/state?token={self.token}")
                if status == 200:
                    data = json.loads(body.decode("utf-8"))
                    arenas = data.get("arenas", [])
                    arenas_sorted = sorted(arenas, key=lambda x: x.get("arena_id", 0))
                    arenas_repr = json.dumps(arenas_sorted, sort_keys=True)
                    if arenas_repr != self.last_arenas_repr:
                        self.last_arenas_repr = arenas_repr
                        print("\n[Arenas]")
                        for a in arenas_sorted:
                            print(f"- #{a['arena_id']} {a['name']} (creator {a['creator']}) p1={a['player1']} p2={a['player2']}")
                        print("----")
                time.sleep(1)
            except Exception as e:
                print(f"[lobby poll err] {e}")
                time.sleep(2)

    def _poll_lobby_chat(self):
        while not self.poll_stop.is_set():
            try:
                status, _, body = http_request(self.host, self.port, "GET", f"/lobby/chat?since={self.lobby_chat_since}")
                if status == 200:
                    data = json.loads(body.decode("utf-8"))
                    msgs = data.get("messages", [])
                    if msgs:
                        self.lobby_chat_since = max(m["id"] for m in msgs)
                        for m in msgs:
                            print(f"[Lobby] {m['nick']} | {m['text']}")
                time.sleep(1)
            except Exception as e:
                print(f"[lobby chat err] {e}")
                time.sleep(2)

    def _create_arena(self, name: str):
        status, _, body = http_request(self.host, self.port, "POST", "/arena/create", {"token": self.token, "name": name})
        if status in (200, 201):
            data = json.loads(body.decode("utf-8"))
            arena = data["arena"]
            self.arena_id = arena["arena_id"]
            self.role = data.get("role", "player1")
            print(f"Created arena #{self.arena_id} {arena['name']} as {self.role}")
            self._enter_arena_loop()
        else:
            print(f"Create arena failed: {body.decode('utf-8', errors='ignore')}")

    def _join_arena(self, arena_id, role):
        try:
            aid = int(arena_id)
        except Exception:
            print("arena_id must be int")
            return
        status, _, body = http_request(self.host, self.port, "POST", "/arena/join", {"token": self.token, "arena_id": aid, "role": role})
        if status == 200:
            data = json.loads(body.decode("utf-8"))
            self.arena_id = aid
            self.role = data.get("role", role)
            print(f"Joined arena #{aid} as {self.role}")
        else:
            print(f"Join failed: {body.decode('utf-8', errors='ignore')}")

    def _send_lobby_chat(self, text: str):
        http_request(self.host, self.port, "POST", "/lobby/chat", {"token": self.token, "text": text})

    # --------------- Arena -----------------
    def _enter_arena_loop(self):
        self.poll_stop.set()
        self.poll_stop = threading.Event()
        threading.Thread(target=self._poll_arena_state, daemon=True).start()
        threading.Thread(target=self._poll_arena_chat, daemon=True).start()
        print("Arena commands: /move <rock|paper|scissor> (player only), /chat <msg>, /leave")
        while True:
            cmd = input(f"arena#{self.arena_id}> ").strip()
            if cmd.startswith("/move "):
                if self.role.startswith("player"):
                    move = cmd.split(" ", 1)[1]
                    self._send_move(move)
                else:
                    print("spectators cannot move")
            elif cmd.startswith("/chat "):
                self._send_arena_chat(cmd[len("/chat "):])
            elif cmd == "/leave":
                self._leave_arena()
                break
            else:
                print("commands: /move, /chat, /leave")
        # restart lobby polling
        self.poll_stop.set()
        self.poll_stop = threading.Event()
        threading.Thread(target=self._poll_lobby_state, daemon=True).start()
        threading.Thread(target=self._poll_lobby_chat, daemon=True).start()

    def _poll_arena_state(self):
        while not self.poll_stop.is_set():
            try:
                status, _, body = http_request(self.host, self.port, "GET", f"/arena/state?token={self.token}&arena_id={self.arena_id}")
                if status == 200:
                    data = json.loads(body.decode("utf-8"))
                    arena = data.get("arena", {})
                    finished = data.get("finished", False)
                    # print state only when changed
                    state_repr = json.dumps(data, sort_keys=True)
                    if getattr(self, "_last_arena_state", None) != state_repr:
                        self._last_arena_state = state_repr
                        print(f"\n[Arena #{arena.get('arena_id')}] {arena.get('name')} attacker={data.get('attacker')} moves(p1={data['moves']['p1']} p2={data['moves']['p2']}) deadline={int(data.get('phase_deadline',0))}")
                    if finished:
                        print(f"Game finished! Winner: {data.get('winner')}")
                        self.arena_id = None
                        self.role = None
                        self.poll_stop.set()
                        break
                time.sleep(1)
            except Exception as e:
                print(f"[arena state err] {e}")
                time.sleep(2)

    def _poll_arena_chat(self):
        while not self.poll_stop.is_set():
            try:
                status, _, body = http_request(self.host, self.port, "GET", f"/arena/chat?arena_id={self.arena_id}&since={self.arena_chat_since}")
                if status == 200:
                    data = json.loads(body.decode("utf-8"))
                    msgs = data.get("messages", [])
                    if msgs:
                        self.arena_chat_since = max(m["id"] for m in msgs)
                        for m in msgs:
                            print(f"[Arena Chat] {m['nick']} | {m['text']}")
                time.sleep(1)
            except Exception as e:
                print(f"[arena chat err] {e}")
                time.sleep(2)

    def _send_move(self, move: str):
        if not self.arena_id:
            print("not in arena")
            return
        status, _, body = http_request(self.host, self.port, "POST", "/arena/move", {"token": self.token, "arena_id": self.arena_id, "move": move})
        if status == 200:
            print("move submitted")
        else:
            print(f"move failed: {body.decode('utf-8', errors='ignore')}")

    def _send_arena_chat(self, text: str):
        http_request(self.host, self.port, "POST", "/arena/chat", {"token": self.token, "arena_id": self.arena_id, "text": text})

    def _leave_arena(self):
        if not self.arena_id:
            return
        http_request(self.host, self.port, "POST", "/arena/leave", {"token": self.token, "arena_id": self.arena_id})
        print("left arena; back to lobby")
        self.arena_id = None
        self.role = None


def main():
    parser = argparse.ArgumentParser(description="HTTP RPS Arena client (raw sockets)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()

    c = Client(args.host, args.port)
    while not c.token:
        choice = input("Type 'l' to login, 'c' to create account: ").strip().lower()
        if choice == "l":
            c.login()
        elif choice == "c":
            c.create_account()
    c.start_lobby()


if __name__ == "__main__":
    main()
