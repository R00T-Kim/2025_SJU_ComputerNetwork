"""
IRC 클라이언트 메인 실행 파일입니다.
현재는 CLI 기반으로 텍스트 입력을 받아 서버로 전송합니다.

[확장 계획]
추후 GUI 모드를 지원하기 위해 'tkinter' 등을 사용할 수 있습니다.
--gui 옵션을 주어 실행하거나, 별도의 ClientGUI 클래스로 분리할 예정입니다.
"""

import socket
import threading
import sys

HOST = '127.0.0.1'
PORT = 6667

def receive_messages(sock):
    """서버로부터 메시지를 수신하여 출력하는 스레드 함수"""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("서버와의 연결이 끊어졌습니다.")
                break
            print(data.decode('utf-8'))
        except:
            print("연결 종료")
            break

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((HOST, PORT))
        print(f"Connected to server {HOST}:{PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 수신 스레드 시작
    recv_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    recv_thread.daemon = True
    recv_thread.start()

    print("명령어를 입력하세요 (예: NICK myname, JOIN #test)")
    
    # 송신 루프 (메인 스레드)
    try:
        while True:
            msg = input()
            if msg.upper() == '/QUIT':
                client_socket.sendall("QUIT :Bye\r\n".encode('utf-8'))
                break
            
            # 메시지 전송 (CR-LF 추가)
            client_socket.sendall((msg + "\r\n").encode('utf-8'))
            
    except KeyboardInterrupt:
        print("종료합니다.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    # 추후 sys.argv를 확인하여 GUI 모드 실행 가능
    start_client()
