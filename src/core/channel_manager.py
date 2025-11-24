# src/core/channel_manager.py
from src.utils.logger import get_logger
import threading

logger = get_logger("ChannelManager")

class ChannelManager:
    def __init__(self):
        # 채널 이름 -> 사용자 리스트 (혹은 Set) 매핑
        self.channels = {} 
        self.lock = threading.Lock() # 스레드 동기화를 위한 락

    def create_channel(self, channel_name):
        with self.lock:
            if channel_name not in self.channels:
                self.channels[channel_name] = set()
                logger.info(f"Channel {channel_name} created.")

    def join_channel(self, channel_name, client_handler):
        with self.lock:
            if channel_name not in self.channels:
                self.channels[channel_name] = set()
                logger.info(f"Channel {channel_name} created (auto).")
            self.channels[channel_name].add(client_handler)
        logger.info(f"{client_handler.nickname} joined {channel_name}")

    def leave_channel(self, channel_name, client_handler):
        with self.lock:
            if channel_name in self.channels:
                if client_handler in self.channels[channel_name]:
                    self.channels[channel_name].remove(client_handler)
                    logger.info(f"{client_handler.nickname} left {channel_name}")
                    if not self.channels[channel_name]:
                        del self.channels[channel_name]
                        logger.info(f"Channel {channel_name} deleted (empty).")

    def broadcast(self, channel_name, message, sender=None):
        # 락을 걸고 타겟 클라이언트 목록을 복사해둠 (보내는 동안 락 잡고 있으면 느려질 수 있음)
        targets = []
        with self.lock:
            if channel_name in self.channels:
                targets = list(self.channels[channel_name])
        
        for client in targets:
            if client != sender:
                try:
                    client.send_message(message)
                except Exception as e:
                    logger.error(f"Error sending to {client.nickname}: {e}")

    def remove_user(self, client_handler):
        """사용자가 접속을 끊었을 때 모든 채널에서 제거하고 QUIT 메시지 전송"""
        # 1. 사용자가 속한 채널 찾기
        user_channels = []
        with self.lock:
            for ch_name, users in self.channels.items():
                if client_handler in users:
                    user_channels.append(ch_name)
        
        # 2. 각 채널에 QUIT 메시지 전송 및 제거
        quit_msg = f":{client_handler.nickname} QUIT :Connection closed"
        for ch in user_channels:
            self.broadcast(ch, quit_msg, sender=client_handler)
            self.leave_channel(ch, client_handler)

    def get_users_in_channel(self, channel_name):
        with self.lock:
            if channel_name in self.channels:
                return list(self.channels[channel_name])
        return []