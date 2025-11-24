# src/core/channel_manager.py
import threading

from src.utils.logger import get_logger

logger = get_logger("ChannelManager")

class ChannelManager:
    def __init__(self):
        # 채널 이름 -> 사용자 리스트 (혹은 Set) 매핑
        self.channels = {}
        # [추가] 닉네임 -> ClientHandler 매핑 (전체 유저 관리용)
        self.all_users = {}
        self.lock = threading.Lock() # 스레드 동기화를 위한 락

    def add_client(self, client_handler):
            """서버 접속 시 전체 목록에 추가"""
            with self.lock:
                self.all_users[client_handler.nickname] = client_handler

    def change_nickname(self, client_handler, new_nickname):
        """닉네임 변경 반영 (성공 시 True, 중복 시 False 반환)"""
        with self.lock:
            if new_nickname in self.all_users:
                return False # 이미 존재함

            # 기존 닉네임 삭제 후 새 닉네임 등록
            old_nick = client_handler.nickname
            if old_nick in self.all_users:
                del self.all_users[old_nick]

            self.all_users[new_nickname] = client_handler
            return True

    def get_client_by_nick(self, nickname):
        """닉네임으로 클라이언트 핸들러 찾기 (귓속말용)"""
        with self.lock:
            return self.all_users.get(nickname)

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
        # 2. [추가] 전체 유저 목록에서 제거
        with self.lock:
            if client_handler.nickname in self.all_users:
                del self.all_users[client_handler.nickname]
            logger.info(f"User {client_handler.nickname} removed from registry.")

    def get_users_in_channel(self, channel_name):
        with self.lock:
            if channel_name in self.channels:
                return list(self.channels[channel_name])
        return []