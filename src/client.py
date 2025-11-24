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
        
        # 1. 상단: 접속 정보
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(self.top_frame, text="Nick:").pack(side='left')
        self.nick_entry = tk.Entry(self.top_frame, width=10)
        self.nick_entry.pack(side='left', padx=5)
        self.nick_entry.insert(0, "Guest")

        self.connect_btn = tk.Button(self.top_frame, text="Connect", command=self.connect_server)
        self.connect_btn.pack(side='left')

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
        """GUI에 텍스트 추가 (Thread-Safe하게 작성하려면 queue 사용 권장되나 간단히 처리)"""
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, msg + "\n")
        self.chat_log.see(tk.END) # 스크롤 자동 내림
        self.chat_log.config(state='disabled')

    def connect_server(self):
        if self.is_connected: return
        
        nickname = self.nick_entry.get()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            self.is_connected = True
            
            # RFC 1459 접속 시도
            self.socket.send(f"NICK {nickname}\r\n".encode('utf-8'))
            self.socket.send(f"USER {nickname} 0 * :RealName\r\n".encode('utf-8'))
            
            self.log(f"[System] Connected to {HOST}:{PORT}")
            self.connect_btn.config(state='disabled')
            
            # 수신 스레드 시작 (핵심!)
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def receive_loop(self):
        """서버로부터 메시지를 계속 받아서 화면에 뿌림"""
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data: break # 연결 끊김
                
                # 들어온 메시지 디코딩 (여러 줄일 수 있음)
                messages = data.decode('utf-8').split('\r\n')
                for msg in messages:
                    if msg: self.log(msg)
                    
            except:
                break
        
        self.is_connected = False
        self.log("[System] Disconnected.")

    def send_message(self, event=None):
        if not self.is_connected: return
        
        msg = self.msg_entry.get()
        if msg:
            # 예: 채팅방 메시지 전송 (RFC: PRIVMSG #channel :message)
            # 여기서는 편의상 입력한 그대로 서버에 보냄 (테스트용)
            try:
                # 실제 구현 시: self.socket.send(f"PRIVMSG #General :{msg}\r\n".encode())
                self.socket.send(f"{msg}\r\n".encode('utf-8')) 
                self.msg_entry.delete(0, tk.END)
            except:
                self.log("[Error] Failed to send.")

if __name__ == "__main__":
    root = tk.Tk()
    app = IRCClientGUI(root)
    root.mainloop()