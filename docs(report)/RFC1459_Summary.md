# RFC 1459 프로토콜 구현 요약

이 프로젝트에서 구현할 IRC 프로토콜의 핵심 기능들을 정리하는 문서입니다.

## 1. 구현 목표 명령어 (Command)
- [ ] NICK <nickname> : 닉네임 설정
- [ ] JOIN <channel> : 채널 입장
- [ ] PART <channel> : 채널 퇴장
- [ ] PRIVMSG <receiver> <message> : 메시지 전송 (개인/채널)
- [ ] QUIT <message> : 서버 연결 종료

## 2. 응답 코드 (Reply Codes)
- 001 RPL_WELCOME : 환영 메시지
- 403 ERR_NOSUCHCHANNEL : 존재하지 않는 채널
- 433 ERR_NICKNAMEINUSE : 이미 사용 중인 닉네임

## 3. 참고 사항
- RFC 1459 원문: https://tools.ietf.org/html/rfc1459
- 모든 메시지는 CR-LF (\r\n)로 끝납니다.
