# src/core/parser.py

class IRCParser:
    @staticmethod
    def parse(message: str):
        """
        RFC 1459 스타일의 메시지를 파싱합니다.
        형식: [PREFIX] COMMAND [PARAMS...]
        예시: "PRIVMSG #General :Hello World" -> cmd="PRIVMSG", params=["#General", "Hello World"]
        """
        message = message.strip()
        if not message:
            return None, []

        parts = message.split(" ")
        command = parts[0].upper()
        params = []

        # 파라미터 파싱 로직 (콜론 ':' 뒤에는 띄어쓰기 포함된 하나의 문자열로 취급)
        if len(parts) > 1:
            raw_params = parts[1:]
            for index, param in enumerate(raw_params):
                if param.startswith(":"):
                    # 콜론으로 시작하면 그 뒤는 전부 하나의 파라미터 (메시지 본문 등)
                    params.append(" ".join(raw_params[index:])[1:])
                    break
                else:
                    params.append(param)

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