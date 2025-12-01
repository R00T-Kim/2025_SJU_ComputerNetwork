# ==============================================================================
# Team Information
# ------------------------------------------------------------------------------
# 21011659 김근호 (Backend Core Developer)
# 21011582 한현준 (Data & Channel Manager)
# 21011673 한상민 (Frontend & Integration Developer)
# 21011650 이규민 (QA & Documentation Specialist)
# ==============================================================================

import threading
import time

# 유저 활동 기준(초) – 너무 짧게 깜빡이지 않도록 여유를 둠
ACTIVE_THRESHOLD = 15
# 활동이 완전히 끊긴 유저를 채널에서 제거하는 시간(초)
STALE_TIMEOUT = 20

class ChannelManager:
    def __init__(self):
        self.channels = {}  # channel -> set(nick)
        self.channel_events = {}  # channel -> list of event dicts
        self.last_event_id = 0
        self.last_read = {}  # channel -> {nick: last_read_event_id}
        self.last_seen = {}  # nick -> last activity timestamp
        self.focus_state = {}  # nick -> bool (True if page focused/visible)
        self.cond = threading.Condition()

    def list_channels(self, nick=None):
        with self.cond:
            self._cleanup_inactive_locked()
            channels = []
            for ch in sorted(self.channels.keys()):
                if ch.startswith('!dm_'):
                    if not nick:
                        continue
                    participants = ch.replace('!dm_', '').split('_')
                    if nick not in participants:
                        continue
                channels.append(ch)
            return channels

    def get_all_users(self):
        """현재 접속 중인 모든 유저 목록 (중복 제거)"""
        with self.cond:
            self._cleanup_inactive_locked()
            users = set()
            for members in self.channels.values():
                users.update(members)
            user_list = []
            now = time.time()
            for u in users:
                last = self.last_seen.get(u, 0)
                active = self.focus_state.get(u, False) or ((now - last) <= ACTIVE_THRESHOLD)
                user_list.append({"nick": u, "active": active})
            user_list.sort(key=lambda x: x["nick"])
            return user_list

    def join_channel(self, channel, nick):
        with self.cond:
            members = self.channels.setdefault(channel, set())
            members.add(nick)
            self.last_seen[nick] = time.time()
            self.last_read.setdefault(channel, {})[nick] = self.last_event_id
            self._cleanup_inactive_locked()
            # 입장 시스템 메시지
            event = self._record_event_locked(channel, "join", nick)
            return list(members), event

    def part_channel(self, channel, nick, reason="leaving"):
        with self.cond:
            if channel not in self.channels or nick not in self.channels[channel]:
                return False
            self.channels[channel].remove(nick)
            if channel in self.last_read and nick in self.last_read[channel]:
                del self.last_read[channel][nick]
            # 채널에서 나가면 last_seen은 일단 두지만 이후 cleanup에서 정리됨
            self._record_event_locked(channel, "part", nick, text=reason)
            if not self.channels[channel]:
                del self.channels[channel]
                if channel in self.last_read:
                    del self.last_read[channel]
            return True
    def leave_all(self, nick, reason="leaving"):
        with self.cond:
            changed = False
            for channel, members in list(self.channels.items()):
                if nick in members:
                    members.remove(nick)
                    changed = True
                    if channel in self.last_read and nick in self.last_read[channel]:
                        del self.last_read[channel][nick]
                    self._record_event_locked(channel, "part", nick, text=reason)
                    if not members:
                        del self.channels[channel]
                        if channel in self.last_read:
                            del self.last_read[channel]
            if nick in self.last_seen:
                del self.last_seen[nick]
            return changed

    # [핵심 수정] msg_type 인자가 추가되었습니다!
    def post_message(self, channel, nick, text, msg_type="text", file_name=None):
        """msg_type: 'text', 'image', or 'file'"""
        with self.cond:
            if channel not in self.channels or nick not in self.channels[channel]:
                return None
            self.last_seen[nick] = time.time()
            self.focus_state[nick] = True
            self._cleanup_inactive_locked()
            return self._record_event_locked(
                channel, "message", nick, text=text, msg_type=msg_type, file_name=file_name
            )

    def wait_events(self, channel, since_id, nick=None, timeout=10):
        deadline = time.time() + timeout
        with self.cond:
            def _collect():
                raw = [e for e in self.channel_events.get(channel, []) if e["id"] > since_id]
                return raw, self.last_event_id

            events, latest = _collect()
            while not events:
                remaining = deadline - time.time()
                if remaining <= 0: break
                self.cond.wait(timeout=remaining)
                events, latest = _collect()

            # 이 호출을 한 유저를 읽음 처리
            if nick:
                self.last_read.setdefault(channel, {})[nick] = latest
                self.last_seen[nick] = time.time()
                self.focus_state[nick] = True

            self._cleanup_inactive_locked()
            return events, latest

    # [핵심 수정] 내부 함수도 msg_type을 저장하도록 변경
    def _record_event_locked(self, channel, event_type, nick, text=None, msg_type="text", file_name=None):
        self.last_event_id += 1
        event = {
            "id": self.last_event_id,
            "type": event_type,
            "channel": channel,
            "nick": nick,
            "timestamp": time.time(),
            "msg_type": msg_type  # text, image, or file
        }
        if text is not None:
            event["text"] = text
        if file_name:
            event["file_name"] = file_name
        self.channel_events.setdefault(channel, []).append(event)
        self.cond.notify_all()
        return event

    def _cleanup_inactive_locked(self):
        """채널에서 완전히 떠난/오래 비활성인 유저 정리"""
        now = time.time()
        for channel, members in list(self.channels.items()):
            to_remove = []
            for m in list(members):
                last = self.last_seen.get(m, 0)
                if now - last > STALE_TIMEOUT:
                    to_remove.append(m)
            for m in to_remove:
                members.remove(m)
                if channel in self.last_read and m in self.last_read[channel]:
                    del self.last_read[channel][m]
            if not members:
                del self.channels[channel]
                if channel in self.last_read:
                    del self.last_read[channel]

        # last_seen/last_read 에서 채널에 속하지 않는 유저 정리
        active_members = {m for ms in self.channels.values() for m in ms}
        for nick in list(self.last_seen.keys()):
            if nick not in active_members:
                del self.last_seen[nick]
        for channel, readers in list(self.last_read.items()):
            to_del = [n for n in readers if n not in active_members]
            for n in to_del:
                del readers[n]
            if not readers:
                del self.last_read[channel]

    def set_focus(self, nick, is_active):
        with self.cond:
            self.last_seen[nick] = time.time()
            self.focus_state[nick] = bool(is_active)
            self._cleanup_inactive_locked()
