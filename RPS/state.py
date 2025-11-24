import json
import os
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

from RPS.models import Arena, User, nick_from


DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rps_users.json")


class GameState:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.username_to_id: Dict[str, list] = {}
        self.next_user_id: int = 0

        self.sessions: Dict[str, int] = {}

        self.arenas: Dict[int, Arena] = {}
        self.next_arena_id: int = 1

        self.lobby_chat: List[dict] = []
        self.arena_chats: Dict[int, List[dict]] = {}
        self.chat_seq: int = 0

        self.lock = threading.Lock()

        self._load_users()

    # --------------- Persistence -----------------
    def _load_users(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.next_user_id = data.get("next_user_id", 0)
            for item in data.get("users", []):
                user = User(
                    username=item["username"],
                    password=item["password"],
                    user_id=item["user_id"],
                    wins=item.get("wins", 0),
                    losses=item.get("losses", 0),
                    total_games=item.get("total_games", 0),
                )
                self.users[user.user_id] = user
                self.username_to_id.setdefault(user.username, []).append(user.user_id)
        except Exception:
            # Ignore load errors; start fresh
            self.users = {}
            self.username_to_id = {}
            self.next_user_id = 0

    def save_users(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "next_user_id": self.next_user_id,
                        "users": [
                            {
                                "username": u.username,
                                "password": u.password,
                                "user_id": u.user_id,
                                "wins": u.wins,
                                "losses": u.losses,
                                "total_games": u.total_games,
                            }
                            for u in self.users.values()
                        ],
                    },
                    f,
                )
        except Exception:
            pass

    # --------------- Accounts -----------------
    def create_account(self, username: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        username = username.strip()
        if not username or not password:
            return False, "username and password required", None
        with self.lock:
            if self.next_user_id >= 1000:
                return False, "no more ids", None
            # Username can duplicate; IDs are unique
            user_id = self.next_user_id
            self.next_user_id += 1
            user = User(username=username, password=password, user_id=user_id)
            self.users[user_id] = user
            self.username_to_id.setdefault(username, []).append(user_id)
            token = self._new_session(user_id)
            self._chat_lobby_system(f"{user.nickname} joined the arena service.")
            return True, token, user.to_dict()

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        with self.lock:
            ids = self.username_to_id.get(username, [])
            if not ids:
                return False, "Incorrect Username", None
            for uid in ids:
                user = self.users.get(uid)
                if user and user.password == password:
                    token = self._new_session(uid)
                    return True, token, user.to_dict()
            return False, "Incorrect Password", None

    def _new_session(self, user_id: int) -> str:
        token = uuid.uuid4().hex
        self.sessions[token] = user_id
        return token

    def auth(self, token: str) -> Optional[User]:
        if not token:
            return None
        uid = self.sessions.get(token)
        if uid is None:
            return None
        return self.users.get(uid)

    # --------------- Lobby -----------------
    def lobby_state(self, user: User):
        with self.lock:
            arenas = [a.to_summary(self.users) for a in self.arenas.values()]
            return {
                "user": user.to_dict(),
                "arenas": arenas,
            }

    def lobby_chat_since(self, since_id: int = 0):
        with self.lock:
            msgs = [m for m in self.lobby_chat if m["id"] > since_id]
            latest = self.chat_seq
            return msgs, latest

    def add_lobby_chat(self, user: User, text: str):
        with self.lock:
            self.chat_seq += 1
            msg = {
                "id": self.chat_seq,
                "nick": user.nickname,
                "text": text,
                "ts": time.time(),
            }
            self.lobby_chat.append(msg)
            return msg

    def _chat_lobby_system(self, text: str):
        self.chat_seq += 1
        msg = {
            "id": self.chat_seq,
            "nick": "SYSTEM",
            "text": text,
            "ts": time.time(),
        }
        self.lobby_chat.append(msg)
        return msg

    # --------------- Arena lifecycle -----------------
    def create_arena(self, user: User, name: str) -> Tuple[bool, str, Optional[Arena]]:
        name = name.strip()
        if not name:
            return False, "arena name required", None
        with self.lock:
            arena_id = self.next_arena_id
            self.next_arena_id += 1
            arena = Arena(arena_id=arena_id, name=name, creator_id=user.user_id, player1=user.user_id)
            self.arenas[arena_id] = arena
            user.arena_id = arena_id
            user.role = "player1"
            self._chat_lobby_system(f"{user.nickname} created Arena [{name}]")
            return True, "created", arena

    def join_arena(self, user: User, arena_id: int, role: str) -> Tuple[bool, str, Optional[Arena]]:
        with self.lock:
            arena = self.arenas.get(arena_id)
            if not arena:
                return False, "arena not found", None
            # If user already in an arena, prevent double join
            if user.arena_id and user.arena_id != arena_id:
                return False, "already in another arena", None
            if role == "player":
                if arena.player1 is None:
                    arena.player1 = user.user_id
                    slot = "player1"
                elif arena.player2 is None:
                    arena.player2 = user.user_id
                    slot = "player2"
                else:
                    return False, "full player", None
                user.arena_id = arena_id
                user.role = slot
            else:
                arena.spectators.add(user.user_id)
                user.arena_id = arena_id
                user.role = "spectator"
            self._chat_lobby_system(f"{user.nickname} has entered Arena [{arena.name}]")
            return True, "joined", arena

    def leave_arena(self, user: User, arena_id: int, reason: str = "left"):
        with self.lock:
            arena = self.arenas.get(arena_id)
            if not arena:
                user.arena_id = None
                user.role = None
                return
            other_slot = None
            leaving_slot = None
            if arena.player1 == user.user_id:
                leaving_slot = 1
                other_slot = 2 if arena.player2 else None
                arena.player1 = None
                arena.move_p1 = None
            elif arena.player2 == user.user_id:
                leaving_slot = 2
                other_slot = 1 if arena.player1 else None
                arena.player2 = None
                arena.move_p2 = None
            elif user.user_id in arena.spectators:
                arena.spectators.discard(user.user_id)

            user.arena_id = None
            user.role = None
            self._chat_lobby_system(f"{user.nickname} returned from Arena [{arena.name}] ({reason})")
            # If the user was a player and the other exists, award win to remaining player.
            if other_slot and leaving_slot:
                self._finish_arena(arena, winner_slot=other_slot, reason="opponent left", loser_id=user.user_id)
                return
            # If no players remain, delete arena
            if arena.player1 is None and arena.player2 is None:
                self.arenas.pop(arena_id, None)

    # --------------- Chat (arena) -----------------
    def arena_chat_since(self, arena_id: int, since_id: int = 0):
        with self.lock:
            msgs = [m for m in self.arena_chats.get(arena_id, []) if m["id"] > since_id]
            latest = self.chat_seq
            return msgs, latest

    def add_arena_chat(self, user: User, arena_id: int, text: str):
        with self.lock:
            self.chat_seq += 1
            msg = {
                "id": self.chat_seq,
                "nick": user.nickname,
                "text": text,
                "ts": time.time(),
            }
            self.arena_chats.setdefault(arena_id, []).append(msg)
            return msg

    # --------------- Game play -----------------
    def submit_move(self, user: User, arena_id: int, move: str) -> Tuple[bool, str]:
        move = move.lower()
        if move not in ("rock", "paper", "scissor"):
            return False, "invalid move"
        with self.lock:
            arena = self.arenas.get(arena_id)
            if not arena or arena.finished:
                return False, "arena not found or finished"
            if user.user_id not in (arena.player1, arena.player2):
                return False, "not a player"
            if arena.player1 == user.user_id:
                arena.move_p1 = move
            elif arena.player2 == user.user_id:
                arena.move_p2 = move
            self._maybe_resolve(arena)
            return True, "accepted"

    def get_arena_state(self, arena_id: int):
        with self.lock:
            arena = self.arenas.get(arena_id)
            if not arena:
                return None
            self._maybe_resolve(arena)
            return {
                "arena": arena.to_summary(self.users),
                "phase_deadline": arena.phase_deadline,
                "moves": {
                    "p1": bool(arena.move_p1),
                    "p2": bool(arena.move_p2),
                },
                "attacker": arena.attacker,
                "finished": arena.finished,
                "winner": self.users[arena.winner].nickname if arena.winner in self.users else None,
            }

    # --------------- Internal game logic -----------------
    def _result(self, m1: str, m2: str) -> int:
        if m1 == m2:
            return 0
        wins = {("rock", "scissor"), ("scissor", "paper"), ("paper", "rock")}
        return 1 if (m1, m2) in wins else 2

    def _maybe_resolve(self, arena: Arena):
        now = time.time()
        # Timeout handling
        if not arena.finished and now > arena.phase_deadline:
            if arena.move_p1 and not arena.move_p2:
                self._finish_arena(arena, winner_slot=1, reason="timeout")
                return
            if arena.move_p2 and not arena.move_p1:
                self._finish_arena(arena, winner_slot=2, reason="timeout")
                return
            if not arena.move_p1 and not arena.move_p2:
                arena.reset_phase()
                return

        if arena.finished:
            return

        # Both moves present?
        if arena.move_p1 and arena.move_p2:
            res = self._result(arena.move_p1, arena.move_p2)
            if arena.attacker == 0:
                if res == 0:
                    arena.reset_phase()
                    return
                arena.attacker = res  # winner becomes attacker
                arena.reset_phase()
                return
            else:
                if res == 0:
                    # tie while attacker set => attacker wins
                    self._finish_arena(arena, winner_slot=arena.attacker, reason="tie as attacker")
                    return
                else:
                    arena.attacker = res  # new attacker
                    arena.reset_phase()
                    return

    def _finish_arena(self, arena: Arena, winner_slot: int, reason: str, loser_id: int = None):
        arena.finished = True
        arena.winner = arena.player1 if winner_slot == 1 else arena.player2
        p1 = self.users.get(arena.player1) if arena.player1 is not None else None
        p2 = self.users.get(arena.player2) if arena.player2 is not None else None
        # Handle loser that already left
        if loser_id and loser_id not in (arena.player1, arena.player2):
            loser = self.users.get(loser_id)
        else:
            loser = None
        if p1 and p2:
            p1.total_games += 1
            p2.total_games += 1
            if winner_slot == 1:
                p1.wins += 1
                p2.losses += 1
            else:
                p2.wins += 1
                p1.losses += 1
        elif p1 and winner_slot == 1 and loser:
            p1.total_games += 1
            p1.wins += 1
            loser.total_games += 1
            loser.losses += 1
        elif p2 and winner_slot == 2 and loser:
            p2.total_games += 1
            p2.wins += 1
            loser.total_games += 1
            loser.losses += 1
        # Release players back to lobby and announce
        affected = []
        if p1:
            p1.arena_id = None
            p1.role = None
            affected.append(p1.nickname)
        if p2:
            p2.arena_id = None
            p2.role = None
            affected.append(p2.nickname)

        # Notify lobby
        for nick in affected:
            self._chat_lobby_system(f"{nick} has returned from Arena [{arena.name}] ({reason})")

        # spectators also released
        for uid in list(arena.spectators):
            user = self.users.get(uid)
            if user:
                user.arena_id = None
                user.role = None
        # Remove arena
        self.arenas.pop(arena.arena_id, None)
        # Persist user stats
        self.save_users()
