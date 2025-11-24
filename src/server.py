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
        logger.info(f"IRC Server started on {HOST}:{PORT}")
        
        channel_manager = ChannelManager()

        while True:
            client_sock, addr = server_sock.accept()
            handler = ClientHandler(client_sock, addr, channel_manager)
            handler.start()
            
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        server_sock.close()

if __name__ == "__main__":
    start_server()