# src/client.py
import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading
from src.core.parser import IRCParser

# --- 설정 ---
HOST = '127.0.0.1'
PORT = 6667

class IRCClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Team Project IRC Client")
        self.socket = None
        self.is_connected = False
        self.current_channel = None
        self.nickname = "Guest"
        
        # 1. 상단: 접속 정보
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(self.top_frame, text="Host:").pack(side='left')
        self.host_entry = tk.Entry(self.top_frame, width=15)
        self.host_entry.pack(side='left', padx=2)
        self.host_entry.insert(0, "127.0.0.1")

        tk.Label(self.top_frame, text="Port:").pack(side='left')
        self.port_entry = tk.Entry(self.top_frame, width=6)
        self.port_entry.pack(side='left', padx=2)
        self.port_entry.insert(0, "6667")
        
        tk.Label(self.top_frame, text="Nick:").pack(side='left', padx=5)
        self.nick_entry = tk.Entry(self.top_frame, width=10)
        self.nick_entry.pack(side='left', padx=2)
        self.nick_entry.insert(0, "Guest")

        self.connect_btn = tk.Button(self.top_frame, text="Connect", command=self.connect_server)
        self.connect_btn.pack(side='left', padx=5)

        # 2. 중단: 채팅 로그 (ScrolledText)
        self.chat_log = scrolledtext.ScrolledText(root, state='disabled', height=15)
        self.chat_log.pack(fill='both', expand=True, padx=5, pady=5)

        # 3. 하단: 메시지 입력
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(fill='x', padx=5, pady=5)

        self.msg_entry = tk.Entry(self.bottom_frame)
        self.msg_entry.pack(side='left', fill='x', expand=True)
        self.msg_entry.bind("<Return>", self.send_message) # 엔터키 전송

        self.send_btn = tk.Button(self.bottom_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side='right', padx=5)

    def log(self, msg):
        """GUI에 텍스트 추가"""
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, msg + "\n")
        self.chat_log.see(tk.END)
        self.chat_log.config(state='disabled')

    def connect_server(self):
        if self.is_connected: return
        
        host = self.host_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.nickname = self.nick_entry.get()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.is_connected = True
            
            # RFC 1459 접속 시도
            self.socket.send(f"NICK {self.nickname}\r\n".encode('utf-8'))
            self.socket.send(f"USER {self.nickname} 0 * :RealName\r\n".encode('utf-8'))
            
            self.log(f"[System] Connected to {host}:{port}")
            self.connect_btn.config(state='disabled')
            
            # 수신 스레드 시작
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def receive_loop(self):
        """서버로부터 메시지를 계속 받아서 화면에 뿌림"""
        buffer = ""
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data: break
                
                buffer += data.decode('utf-8')
                
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    if not line: continue
                    
                    # IRCParser를 사용한 구조화된 파싱
                    command, params = IRCParser.parse(line)
                    
                    # Prefix 파싱 (예: :nick!user@host COMMAND ...)
                    prefix = ""
                    if line.startswith(":"):
                        parts = line.split(" ", 1)
                        prefix = parts[0][1:] # : 제거
                        if "!" in prefix: prefix = prefix.split("!")[0] # user@host 제거

                    if command == "PRIVMSG":
                        if len(params) >= 2:
                            target = params[0]
                            msg = params[1]
                            self.log(f"[{target}] <{prefix}> {msg}")
                            
                    elif command == "JOIN":
                        channel = params[0] if params else "???"
                        self.log(f"[System] {prefix} joined {channel}")
                        
                    elif command == "PART":
                        channel = params[0] if params else "???"
                        reason = params[1] if len(params) > 1 else ""
                        self.log(f"[System] {prefix} left {channel} ({reason})")
                        
                    elif command == "QUIT":
                        reason = params[0] if params else ""
                        self.log(f"[System] {prefix} quit ({reason})")
                        
                    elif command == "NICK":
                        new_nick = params[0] if params else "???"
                        self.log(f"[System] {prefix} changed nickname to {new_nick}")
                        if prefix == self.nickname:
                            self.nickname = new_nick # 내 닉네임 업데이트

                    elif command == "PING":
                        if params:
                            self.socket.send(f"PONG {params[0]}\r\n".encode('utf-8'))
                        else:
                            self.socket.send("PONG\r\n".encode('utf-8'))

                    elif command == "353": # RPL_NAMREPLY
                        # params: [me, =, #channel, :nick1 nick2 ...]
                        if len(params) >= 4:
                            channel = params[2]
                            users = params[3]
                            self.log(f"[Users in {channel}] {users}")
                    
                    elif command == "366": # RPL_ENDOFNAMES
                        pass # 무시

                    elif command == "001": # Welcome
                        self.log(f"[Server] {params[-1] if params else 'Welcome'}")

                    else:
                        # 기타 메시지는 그대로 출력
                        self.log(line)
                    
            except Exception as e:
                self.log(f"[Error] {e}")
                break
        
        self.is_connected = False
        self.log("[System] Disconnected.")
        self.connect_btn.config(state='normal')

    def send_message(self, event=None):
        if not self.is_connected: return
        
        msg = self.msg_entry.get()
        if not msg: return

        try:
            if msg.startswith("/"):
                # 명령어 모드
                cmd_line = msg[1:]
                parts = cmd_line.split(" ", 1)
                cmd = parts[0].upper()
                param = parts[1] if len(parts) > 1 else ""
                
                if cmd == "JOIN":
                    self.socket.send(f"JOIN {param}\r\n".encode('utf-8'))
                    self.current_channel = param.split(" ")[0]
                elif cmd == "PART":
                    self.socket.send(f"PART {param}\r\n".encode('utf-8'))
                    if self.current_channel == param:
                        self.current_channel = None
                elif cmd == "NICK":
                    self.socket.send(f"NICK {param}\r\n".encode('utf-8'))
                elif cmd == "NAMES":
                    self.socket.send(f"NAMES {param}\r\n".encode('utf-8'))
                else:
                    self.socket.send(f"{cmd_line}\r\n".encode('utf-8'))
            else:
                # 일반 대화 모드
                if self.current_channel:
                    # 내가 보낸 메시지도 화면에 표시 (서버가 에코해주지 않는 구조라면)
                    self.socket.send(f"PRIVMSG {self.current_channel} :{msg}\r\n".encode('utf-8'))
                    self.log(f"[{self.current_channel}] <{self.nickname}> {msg}")
                else:
                    self.log("[System] Join a channel first! (/join #channel)")
            
            self.msg_entry.delete(0, tk.END)
        except Exception as e:
            self.log(f"[Error] {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = IRCClientGUI(root)
    root.mainloop()