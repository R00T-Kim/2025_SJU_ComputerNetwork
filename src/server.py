# src/server.py
import socket
import threading
from src.core.handler import ClientHandler
from src.core.channel_manager import ChannelManager
from src.utils.logger import get_logger

logger = get_logger("Server")

HOST = '0.0.0.0'
PORT = 6667

def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind((HOST, PORT))
        server_sock.listen(5)
        server_sock.settimeout(1.0) # 1초마다 타임아웃 -> 인터럽트 감지 가능
        logger.info(f"IRC Server started on {HOST}:{PORT}")
        
        channel_manager = ChannelManager()

        while True:
            try:
                client_sock, addr = server_sock.accept()
                handler = ClientHandler(client_sock, addr, channel_manager)
                handler.daemon = True # 메인 스레드 종료 시 함께 종료
                handler.start()
            except socket.timeout:
                continue # 타임아웃 발생 시 루프 재진입 (종료 신호 확인용)
            except Exception as e:
                logger.error(f"Accept error: {e}")

    except KeyboardInterrupt:
        logger.info("\nServer stopping by user request (Ctrl+C)...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        server_sock.close()
        logger.info("Server socket closed.")

if __name__ == "__main__":
    start_server()