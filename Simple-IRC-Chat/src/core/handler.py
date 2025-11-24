"""
클라이언트 접속을 처리하는 핸들러 모듈입니다.
각 클라이언트마다 스레드로 실행되며, 메시지 수신 및 응답을 처리합니다.
"""

import threading
from src.core.parser import parse_message

class ClientHandler(threading.Thread):
    def __init__(self, client_socket, addr, channel_manager):
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.channel_manager = channel_manager
        self.nickname = None
        self.running = True

    def run(self):
        """스레드 실행 메인 루프"""
        print(f"[Handler] Connected by {self.addr}")
        try:
            while self.running:
                # 데이터 수신 (최대 1024 바이트)
                data = self.client_socket.recv(1024)
                if not data:
                    break
                
                # 디코딩 및 파싱
                text = data.decode('utf-8')
                parsed = parse_message(text)
                
                if parsed:
                    self.process_command(parsed)
                    
        except Exception as e:
            print(f"[Handler] Error: {e}")
        finally:
            self.close_connection()

    def process_command(self, parsed_data):
        """파싱된 명령어를 처리하는 분기문"""
        cmd = parsed_data['command']
        params = parsed_data['params']
        
        print(f"[Handler] Received Command: {cmd}, Params: {params}")
        
        if cmd == 'NICK':
            # 닉네임 설정 로직
            pass
        elif cmd == 'JOIN':
            # 채널 입장 로직
            pass
        elif cmd == 'PRIVMSG':
            # 메시지 전송 로직
            pass
        elif cmd == 'QUIT':
            self.running = False

    def close_connection(self):
        """연결 종료 처리"""
        print(f"[Handler] Closing connection for {self.addr}")
        self.client_socket.close()
