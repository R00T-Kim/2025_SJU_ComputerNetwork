# src/core/parser.py

class IRCParser:
    @staticmethod
    def parse(message: str):
        """
        RFC 1459 스타일의 메시지를 파싱합니다.
        형식: [PREFIX] COMMAND [PARAMS...]
        """
        message = message.strip()
        if not message:
            return None, []

        prefix = ""
        if message.startswith(":"):
            # prefix가 있는 경우 (예: :nick!user@host COMMAND ...)
            # 첫 번째 공백을 찾아서 prefix 분리
            parts = message.split(" ", 1)
            if len(parts) < 2:
                return None, [] # 유효하지 않은 메시지
            prefix = parts[0][1:] # 맨 앞 ':' 제거
            message = parts[1].strip()

        # Trailing Parameter 분리 ( " :" 로 시작하는 부분)
        trailing = None
        if " :" in message:
            message, trailing = message.split(" :", 1)
        
        # 나머지 파라미터들은 공백으로 구분 (연속된 공백 무시)
        args = message.split()
        if not args:
            return None, []
            
        command = args[0].upper()
        params = args[1:]
        
        if trailing is not None:
            params.append(trailing)

        return command, params

    @staticmethod
    def build_msg(command, *params):
        """
        서버 -> 클라이언트로 보낼 때 사용
        예: build_msg("PRIVMSG", "#General", "Hello!") -> "PRIVMSG #General :Hello!\r\n"
        """
        msg = command
        if params:
            for i, p in enumerate(params):
                if i == len(params) - 1 and " " in p:
                    msg += f" :{p}" # 마지막 파라미터에 공백이 있으면 콜론 추가
                else:
                    msg += f" {p}"
        return msg + "\r\n"