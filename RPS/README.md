# RPS Arena (HTTP 기반 묵찌빠 결투장)

raw TCP 소켓 위에 직접 구현한 HTTP/1.1(JSON) 프로토콜로 동작하는 PvP 묵찌빠 결투 서비스입니다. 로그인/회원가입, 로비 채팅, 아레나 생성·입장·관전, 15초 타이머 기반 묵찌빠 라운드 진행, 전적 저장을 포함합니다. 클라이언트는 주기적 폴링(1s)으로 상태를 갱신합니다.

## 주요 기능
- 계정 시스템: username 중복 허용, 서버가 ID 000~999 순차 부여 → nickname `username#id`. 로그인/회원가입 지원.
- 로비: 전체 채팅, 아레나 목록 조회, 아레나 생성.
- 아레나: Player1/Player2 슬롯, 관전자 무제한, 로비→입장 알림, 아레나 채팅.
- 게임 규칙: 묵찌빠. 초기 라운드 승자가 공격자, 공격자 상태에서 동점 시 즉시 승리. 15초 내 미제출자는 패배, 모두 미제출 시 라운드 재시작.
- 전적 기록: wins/losses/total_games 저장, 서버 종료 시 `rps_users.json`에 영속화.

## 실행 방법
- 서버: `python -m RPS.server --host 0.0.0.0 --port 9090` (또는 `make run-rps-server`)
- 클라이언트: `python -m RPS.client --host 127.0.0.1 --port 9090` (또는 `make run-rps-client`)

## 클라이언트 사용법 (터미널)
- 시작: `l` → 로그인, `c` → 계정 생성.
- 로비 명령:  
  - `/create <arena_name>` → 생성 직후 자동 입장.  
  - `/join <arena_id> <player|spectator>` → 예: `/join 1 player`  
  - `/chat <msg>` → 로비 채팅.  
  - `/quit` → 클라이언트 종료.
- 아레나 명령:  
  - `/move <rock|paper|scissor>` (플레이어만)  
  - `/chat <msg>` → 아레나 채팅  
  - `/leave` → 아레나 나가고 로비로 복귀

## HTTP API 요약 (JSON)
- `POST /account/create {username,password}` → {token,user} (ID 부여)
- `POST /account/login {username,password}` → {token,user}
- `GET /lobby/state?token=...` → {user, arenas[]}
- `GET /lobby/chat?since=ID` / `POST /lobby/chat {token,text}`
- `POST /arena/create {token,name}` → {arena,role}
- `POST /arena/join {token,arena_id,role}` → {arena,role} (`full player` 오류 처리)
- `POST /arena/leave {token,arena_id}`
- `POST /arena/move {token,arena_id,move=rock|paper|scissor}`
- `GET /arena/state?token=...&arena_id=...` → 현재 페이즈, 공격자, 제출 여부, 종료/승자
- `GET /arena/chat?arena_id=...&since=ID` / `POST /arena/chat {token,arena_id,text}`

## 프로토콜/네트워킹
- raw `socket(AF_INET, SOCK_STREAM)` + 직접 작성한 HTTP/1.1 파서(`RPS/http_utils.py`), 프레임워크 미사용.
- 클라이언트는 1초 간격 폴링으로 상태/채팅을 갱신 (WebSocket/롱폴 없음).

## 데이터/구조
- 모델: `RPS/models.py` (User, Arena), 상태/로직: `RPS/state.py`, HTTP 핸들러: `RPS/server.py`, 터미널 클라이언트: `RPS/client.py`.
- 사용자 전적은 `rps_users.json`에 저장/로드. 아레나 정보는 메모리 관리(종료 시 삭제).

## 제출용 메모
- 팀 정보/역할을 각 소스 상단 주석과 `docs/Team_Info.txt`에 채워주세요.
- UI는 터미널 기반; HTML/브라우저 UI를 쓰려면 위 API를 폴링하는 페이지를 별도로 만들면 됩니다.
