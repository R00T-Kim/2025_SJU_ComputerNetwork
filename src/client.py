# src/client.py
import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading

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

        nickname = self.nick_entry.get()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.is_connected = True
            
            # RFC 1459 접속 시도
            self.socket.send(f"NICK {nickname}\r\n".encode('utf-8'))
            self.socket.send(f"USER {nickname} 0 * :RealName\r\n".encode('utf-8'))
            
            self.log(f"[System] Connected to {host}:{port}")
            self.connect_btn.config(state='disabled')
            
            # 수신 스레드 시작
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def receive_loop(self):
        """서버로부터 메시지를 계속 받아서 화면에 뿌림"""
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data: break
                
                messages = data.decode('utf-8').split('\r\n')
                for msg in messages:
                    if not msg: continue
                    
                    # 간단한 파싱 (PRIVMSG 포맷팅)
                    if " PRIVMSG " in msg:
                        try:
                            # :sender PRIVMSG #target :message
                            parts = msg.split(" PRIVMSG ", 1)
                            sender_info = parts[0] # :nick OR :nick!user@host
                            rest = parts[1]
                            
                            sender = sender_info[1:] if sender_info.startswith(":") else sender_info
                            if "!" in sender: sender = sender.split("!")[0]
                            
                            target, content = rest.split(" :", 1)
                            self.log(f"[{target}] <{sender}> {content}")
                        except:
                            self.log(msg)
                    elif " PING " in msg:
                         # PING 응답 (자동 PONG)
                         try:
                             check = msg.split(" PING ", 1)[1]
                             self.socket.send(f"PONG {check}\r\n".encode('utf-8'))
                         except:
                             pass
                    else:
                        self.log(msg)
                    
            except:
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
                else:
                    # 기타 명령어는 그대로 전송
                    self.socket.send(f"{cmd_line}\r\n".encode('utf-8'))
            else:
                # 일반 대화 모드
                if self.current_channel:
                    self.socket.send(f"PRIVMSG {self.current_channel} :{msg}\r\n".encode('utf-8'))
                    self.log(f"[{self.current_channel}] <Me> {msg}")
                else:
                    self.log("[System] Join a channel first! (/join #channel)")
            
            self.msg_entry.delete(0, tk.END)
        except Exception as e:
            self.log(f"[Error] {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = IRCClientGUI(root)
    root.mainloop()