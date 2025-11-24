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
                # 성공 메시지 (JOIN 메시지는 채널의 다른 사용자에게도 브로드캐스트 해야 함)
                join_msg = f":{self.nickname} JOIN {channel}"
                self.channel_manager.broadcast(channel, join_msg, sender=None) # sender=None -> 모두에게 전송

        elif command == "PART":
            if params:
                channel = params[0]
                reason = params[1] if len(params) > 1 else "Leaving"
                # PART 메시지 브로드캐스트
                part_msg = f":{self.nickname} PART {channel} :{reason}"
                self.channel_manager.broadcast(channel, part_msg, sender=None)
                self.channel_manager.leave_channel(channel, self)

        elif command == "NAMES":
            if params:
                channel = params[0]
                users = self.channel_manager.get_users_in_channel(channel)
                if users:
                    # RPL_NAMREPLY (353) & RPL_ENDOFNAMES (366)
                    user_list = " ".join([u.nickname for u in users])
                    self.send_message(f":server 353 {self.nickname} = {channel} :{user_list}")
                    self.send_message(f":server 366 {self.nickname} {channel} :End of /NAMES list")

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
            else:
                self.send_message("PONG")
        
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