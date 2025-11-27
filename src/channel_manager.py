import threading
import time

class ChannelManager:
    def __init__(self):
        self.channels = {}  # channel -> set(nick)
        self.channel_events = {}  # channel -> list of event dicts
        self.last_event_id = 0
        self.cond = threading.Condition()

    def list_channels(self):
        with self.cond:
            return sorted(self.channels.keys())

    def get_all_users(self):
        """현재 접속 중인 모든 유저 목록 (중복 제거)"""
        with self.cond:
            users = set()
            for members in self.channels.values():
                users.update(members)
            return sorted(list(users))

    def join_channel(self, channel, nick):
        with self.cond:
            members = self.channels.setdefault(channel, set())
            members.add(nick)
            # 입장 시스템 메시지
            event = self._record_event_locked(channel, "join", nick)
            return list(members), event

    def part_channel(self, channel, nick, reason="leaving"):
        with self.cond:
            if channel not in self.channels or nick not in self.channels[channel]:
                return False
            self.channels[channel].remove(nick)
            self._record_event_locked(channel, "part", nick, text=reason)
            if not self.channels[channel]:
                del self.channels[channel]
            return True

    # [핵심 수정] msg_type 인자가 추가되었습니다!
    def post_message(self, channel, nick, text, msg_type="text"):
        """msg_type: 'text' or 'image'"""
        with self.cond:
            if channel not in self.channels or nick not in self.channels[channel]:
                return None
            return self._record_event_locked(channel, "message", nick, text=text, msg_type=msg_type)

    def wait_events(self, channel, since_id, timeout=10):
        deadline = time.time() + timeout
        with self.cond:
            def _collect():
                return [e for e in self.channel_events.get(channel, []) if e["id"] > since_id], self.last_event_id

            events, latest = _collect()
            while not events:
                remaining = deadline - time.time()
                if remaining <= 0: break
                self.cond.wait(timeout=remaining)
                events, latest = _collect()
            return events, latest

    # [핵심 수정] 내부 함수도 msg_type을 저장하도록 변경
    def _record_event_locked(self, channel, event_type, nick, text=None, msg_type="text"):
        self.last_event_id += 1
        event = {
            "id": self.last_event_id,
            "type": event_type,
            "channel": channel,
            "nick": nick,
            "timestamp": time.time(),
            "msg_type": msg_type  # text or image
        }
        if text is not None:
            event["text"] = text
        self.channel_events.setdefault(channel, []).append(event)
        self.cond.notify_all()
        return event