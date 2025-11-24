"""
서버 로그를 출력하는 유틸리티 모듈입니다.
print() 함수 대신 이 모듈의 함수를 사용하여 로그 형식을 통일합니다.
"""

import datetime

def log(message, level="INFO"):
    """
    로그 메시지를 출력합니다.
    
    Args:
        message (str): 출력할 메시지
        level (str): 로그 레벨 (INFO, WARN, ERROR, DEBUG 등)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def error(message):
    """에러 로그 전용 함수"""
    log(message, "ERROR")

def info(message):
    """일반 정보 로그 전용 함수"""
    log(message, "INFO")

# 테스트 코드
if __name__ == "__main__":
    info("서버가 시작되었습니다.")
    error("연결 오류 발생!")
