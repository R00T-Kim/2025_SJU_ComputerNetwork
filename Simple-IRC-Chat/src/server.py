"""
IRC 서버 메인 실행 파일입니다.
소켓을 열고 클라이언트의 접속을 대기하며, 접속 시 핸들러 스레드를 생성합니다.

실행 방법:
    python server.py
"""

import socket
import sys
import os

# src 폴더를 파이썬 경로에 추가하여 모듈 임포트 가능하게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

from src.core.channel_manager import ChannelManager
from src.core.handler import ClientHandler
from src.utils.logger import info, error

HOST = '127.0.0.1'  # 로컬호스트
PORT = 6667         # IRC 기본 포트

def start_server():
    # 채널 관리자 생성
    channel_manager = ChannelManager()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 포트 재사용 옵션 설정
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        info(f"Server started on {HOST}:{PORT}")
        
        while True:
            # 클라이언트 접속 대기
            client_socket, addr = server_socket.accept()
            info(f"New connection from {addr}")
            
            # 클라이언트 핸들러 스레드 시작
            handler = ClientHandler(client_socket, addr, channel_manager)
            handler.start()
            
    except KeyboardInterrupt:
        info("서버를 종료합니다.")
    except Exception as e:
        error(f"서버 에러 발생: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
