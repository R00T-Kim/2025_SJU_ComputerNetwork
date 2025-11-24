# src/core/channel_manager.py
from src.utils.logger import get_logger

logger = get_logger("ChannelManager")

class ChannelManager:
    def __init__(self):
        # 채널 이름 -> 사용자 리스트 (혹은 Set) 매핑
        self.channels = {} 
        # 사용자 정보 저장 (필요 시 확장)
        self.users = {}

    def create_channel(self, channel_name):
        if channel_name not in self.channels:
            self.channels[channel_name] = set()
            logger.info(f"Channel {channel_name} created.")

    def join_channel(self, channel_name, client_handler):
        if channel_name not in self.channels:
            self.create_channel(channel_name)
        self.channels[channel_name].add(client_handler)
        logger.info(f"{client_handler.nickname} joined {channel_name}")

    def leave_channel(self, channel_name, client_handler):
        if channel_name in self.channels:
            if client_handler in self.channels[channel_name]:
                self.channels[channel_name].remove(client_handler)
                logger.info(f"{client_handler.nickname} left {channel_name}")
                if not self.channels[channel_name]:
                    del self.channels[channel_name]
                    logger.info(f"Channel {channel_name} deleted (empty).")

    def broadcast(self, channel_name, message, sender=None):
        if channel_name in self.channels:
            for client in self.channels[channel_name]:
                if client != sender:
                    try:
                        client.send_message(message)
                    except Exception as e:
                        logger.error(f"Error sending to {client.nickname}: {e}")

    def remove_user(self, client_handler):
        """사용자가 접속을 끊었을 때 모든 채널에서 제거"""
        for channel in list(self.channels.keys()):
            self.leave_channel(channel, client_handler)