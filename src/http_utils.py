import json
import urllib.parse
import mimetypes
import os

CRLF = "\r\n"

def parse_http_request(sock):
    """
    HTTP 요청을 파싱하여 method, path, version, headers, body를 반환합니다.
    """
    try:
        buffer = b""
        # 1. 헤더 읽기 (이중 CRLF가 나올 때까지)
        while b"\r\n\r\n" not in buffer:
            chunk = sock.recv(4096)
            if not chunk:
                return None, None, None, None, None
            buffer += chunk

        header_bytes, body_start = buffer.split(b"\r\n\r\n", 1)
        header_text = header_bytes.decode("iso-8859-1")
        lines = header_text.split(CRLF)

        if not lines:
            return None, None, None, None, None

        method, path, version = lines[0].split()[:3]
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()

        # 2. 바디 읽기 (Content-Length 만큼 정확히 읽기)
        content_length = int(headers.get("content-length", 0))
        body = body_start
        while len(body) < content_length:
            more = sock.recv(4096)
            if not more:
                break
            body += more

        # 바디가 더 많이 읽혔을 경우 잘라내기 (Pipelining 대비)
        return method, path, version, headers, body[:content_length]

    except Exception as e:
        print(f"[Parser Error] {e}")
        return None, None, None, None, None

def parse_multipart_data(body_bytes, boundary):
    """
    바이너리 안전한 멀티파트 파서
    """
    parts = {}
    # 바디 내의 구분자는 '--' + boundary 형태임
    boundary_bytes = b"--" + boundary.encode('utf-8')

    # boundary로 데이터 분리
    chunks = body_bytes.split(boundary_bytes)

    for chunk in chunks:
        # 빈 청크나 끝부분(--) 스킵
        if not chunk or chunk == b"--\r\n" or chunk == b"--":
            continue

        # 청크 구조: \r\n헤더\r\n\r\n내용\r\n
        # 1. 헤더와 바디 구분자(\r\n\r\n) 찾기
        sep_idx = chunk.find(b"\r\n\r\n")
        if sep_idx == -1: continue

        header_part = chunk[:sep_idx]
        body_part = chunk[sep_idx+4:] # \r\n\r\n 뒤가 진짜 데이터

        # 2. 멀티파트 프로토콜 상 데이터 뒤에 붙는 \r\n 제거
        # (주의: 이미지 데이터 자체가 \r\n으로 끝날 수도 있으므로 무조건 제거가 아니라 프로토콜 패딩만 제거해야 함)
        if body_part.endswith(b"\r\n"):
            body_part = body_part[:-2]

        # 3. 헤더에서 파일명 추출
        try:
            header_text = header_part.decode('utf-8', errors='ignore')
            if 'filename="' in header_text:
                # filename="이미지.png" 파싱
                p1 = header_text.find('filename="') + 10
                p2 = header_text.find('"', p1)
                if p1 > 9 and p2 > p1:
                    filename = header_text[p1:p2]
                    parts['file'] = (filename, body_part)
        except:
            pass

    return parts

def parse_query(path):
    parsed = urllib.parse.urlparse(path)
    query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items() if v}
    return parsed.path, query

def send_response(sock, status, reason, body, content_type="text/plain", headers=None):
    if headers is None: headers = {}

    # body가 str이면 인코딩, bytes면 그대로 둠 (이미지 전송 시 중요)
    if isinstance(body, str):
        body = body.encode("utf-8")

    headers_out = {
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Connection": "close",
        **headers
    }

    header_str = f"HTTP/1.1 {status} {reason}\r\n" + \
                 "".join([f"{k}: {v}\r\n" for k, v in headers_out.items()]) + "\r\n"

    # 헤더와 바디(바이너리 포함) 합쳐서 전송
    try:
        sock.sendall(header_str.encode("utf-8") + body)
    except:
        pass

def send_json(sock, status, payload):
    send_response(sock, status, "OK", json.dumps(payload), content_type="application/json")

def send_file(sock, filepath):
    if os.path.exists(filepath):
        mime, _ = mimetypes.guess_type(filepath)
        mime = mime or "application/octet-stream"

        with open(filepath, "rb") as f:
            data = f.read()

        send_response(sock, 200, "OK", data, content_type=mime)
    else:
        send_response(sock, 404, "Not Found", "File not found")