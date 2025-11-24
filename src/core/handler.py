# src/core/handler.py
import threading
import socket
from src.core.parser import IRCParser
from src.utils.logger import get_logger

logger = get_logger("Handler")

class ClientHandler(threading.Thread):
    def __init__(self, sock, addr, channel_manager):
        super().__init__()
        self.sock = sock
        self.addr = addr
        self.channel_manager = channel_manager
        self.nickname = f"Guest{addr[1]}" # 임시 닉네임
        self.running = True

    def run(self):
        logger.info(f"Connected: {self.addr}")
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                buffer += data.decode('utf-8')
                
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    if not line: continue
                    
                    command, params = IRCParser.parse(line)
                    self.handle_command(command, params)
                    
            except ConnectionResetError:
                break
            except Exception as e:
                logger.error(f"Error handling client {self.addr}: {e}")
                break
        
        self.cleanup()

    def handle_command(self, command, params):
        logger.debug(f"Received: {command} {params}")
        
        if command == "NICK":
            if params:
                old_nick = self.nickname
                self.nickname = params[0]
                logger.info(f"Nick change: {old_nick} -> {self.nickname}")
                # 클라이언트에게 환영 메시지 예시 (RFC 호환)
                self.send_message(f":server 001 {self.nickname} :Welcome to the IRC Network {self.nickname}")

        elif command == "USER":
            # USER 명령 처리 (여기서는 로그만 출력)
            pass

        elif command == "JOIN":
            if params:
                channel = params[0]
                self.channel_manager.join_channel(channel, self)
                # 성공 메시지
                self.send_message(f":{self.nickname} JOIN {channel}")

        elif command == "PRIVMSG":
            if len(params) >= 2:
                target = params[0]
                msg = params[1]
                # 채널 메시지인 경우
                if target.startswith("#"):
                    formatted_msg = f":{self.nickname} PRIVMSG {target} :{msg}"
                    self.channel_manager.broadcast(target, formatted_msg, sender=self)
                else:
                    # 1:1 DM 등 구현 예정
                    pass
        elif command == "PING":
            if params:
                self.send_message(f"PONG {params[0]}")
        
        elif command == "QUIT":
            self.running = False

    def send_message(self, msg):
        try:
            self.sock.send(f"{msg}\r\n".encode('utf-8'))
        except Exception as e:
            logger.error(f"Send error: {e}")

    def cleanup(self):
        logger.info(f"Disconnected: {self.addr}")
        self.channel_manager.remove_user(self)
        try:
            self.sock.close()
        except:
            pass