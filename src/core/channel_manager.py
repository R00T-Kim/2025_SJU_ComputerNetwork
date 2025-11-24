"""
채널과 유저 정보를 관리하는 매니저 클래스입니다.
채널 생성, 삭제, 유저 입장/퇴장 등의 상태 관리를 담당합니다.
"""

class ChannelManager:
    def __init__(self):
        # { "채널명": [유저소켓1, 유저소켓2, ...] } 형태의 딕셔너리 예시
        self.channels = {}
        # { "유저소켓": "닉네임" } 형태의 딕셔너리 예시
        self.users = {}

    def create_channel(self, channel_name):
        """새로운 채널을 생성합니다."""
        if channel_name not in self.channels:
            self.channels[channel_name] = []
            print(f"[ChannelManager] Channel created: {channel_name}")
            return True
        return False

    def join_channel(self, channel_name, user_socket):
        """유저를 채널에 추가합니다."""
        # 로직 구현 필요
        pass

    def leave_channel(self, channel_name, user_socket):
        """유저를 채널에서 제거합니다."""
        # 로직 구현 필요
        pass

    def get_users_in_channel(self, channel_name):
        """특정 채널에 있는 유저 목록을 반환합니다."""
        return self.channels.get(channel_name, [])

# 싱글톤처럼 사용하거나 서버 인스턴스에서 하나만 생성해서 사용
