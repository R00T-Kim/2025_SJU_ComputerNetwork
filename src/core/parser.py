"""
클라이언트로부터 수신한 메시지를 파싱하는 모듈입니다.
IRC 프로토콜 명령어(NICK, JOIN, PRIVMSG 등)를 해석하여 반환합니다.
"""

def parse_message(data):
    """
    수신된 데이터를 파싱하여 명령어와 파라미터로 분리합니다.
    
    Args:
        data (str): 소켓에서 수신한 원시 문자열 (예: "JOIN #general\r\n")
        
    Returns:
        dict: {'command': 'JOIN', 'params': ['#general']}
    """
    if not data:
        return None

    parts = data.strip().split(' ')
    command = parts[0].upper()
    params = parts[1:]
    
    return {
        'command': command,
        'params': params
    }

if __name__ == "__main__":
    # 테스트
    msg = "PRIVMSG #room :Hello World"
    print(parse_message(msg))

