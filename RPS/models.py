import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Set


def nick_from(username: str, user_id: int) -> str:
    return f"{username}#{user_id:03d}"


@dataclass
class User:
    username: str
    password: str
    user_id: int
    wins: int = 0
    losses: int = 0
    total_games: int = 0
    arena_id: Optional[int] = None
    role: Optional[str] = None  # "player1","player2","spectator", or None

    @property
    def nickname(self) -> str:
        return nick_from(self.username, self.user_id)

    @property
    def winrate(self) -> float:
        return (self.wins / self.total_games) * 100 if self.total_games else 0.0

    def to_dict(self):
        data = asdict(self)
        data["nickname"] = self.nickname
        data["winrate"] = round(self.winrate, 2)
        return data


@dataclass
class Arena:
    arena_id: int
    name: str
    creator_id: int
    player1: Optional[int] = None
    player2: Optional[int] = None
    spectators: Set[int] = None
    attacker: int = 0  # 0 none, 1 p1, 2 p2
    move_p1: Optional[str] = None
    move_p2: Optional[str] = None
    phase_deadline: float = None
    finished: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        if self.spectators is None:
            self.spectators = set()
        if self.phase_deadline is None:
            self.phase_deadline = time.time() + 15

    def reset_phase(self):
        self.move_p1 = None
        self.move_p2 = None
        self.phase_deadline = time.time() + 15

    def to_summary(self, users: Dict[int, User]):
        return {
            "arena_id": self.arena_id,
            "name": self.name,
            "creator": users[self.creator_id].nickname if self.creator_id in users else "unknown",
            "player1": users[self.player1].nickname if self.player1 in users else None,
            "player2": users[self.player2].nickname if self.player2 in users else None,
            "spectators": [users[uid].nickname for uid in self.spectators if uid in users],
            "attacker": self.attacker,
            "phase_deadline": self.phase_deadline,
            "finished": self.finished,
        }
