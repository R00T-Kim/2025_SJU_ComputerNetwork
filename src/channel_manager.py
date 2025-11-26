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

    def join_channel(self, channel, nick):
        with self.cond:
            members = self.channels.setdefault(channel, set())
            members.add(nick)
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

    def post_message(self, channel, nick, text):
        with self.cond:
            if channel not in self.channels or nick not in self.channels[channel]:
                return None
            return self._record_event_locked(channel, "message", nick, text=text)

    def wait_events(self, channel, since_id, timeout=15):
        """
        Long polling: wait until there is an event newer than since_id for channel or timeout.
        Returns (events, latest_id).
        """
        deadline = time.time() + timeout
        with self.cond:
            def _collect():
                events = [e for e in self.channel_events.get(channel, []) if e["id"] > since_id]
                return events, self.last_event_id

            events, latest = _collect()
            while not events:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self.cond.wait(timeout=remaining)
                events, latest = _collect()
            return events, latest

    def _record_event_locked(self, channel, event_type, nick, text=None):
        self.last_event_id += 1
        event = {
            "id": self.last_event_id,
            "type": event_type,
            "channel": channel,
            "nick": nick,
            "timestamp": time.time(),
        }
        if text is not None:
            event["text"] = text
        self.channel_events.setdefault(channel, []).append(event)
        self.cond.notify_all()
        return event
