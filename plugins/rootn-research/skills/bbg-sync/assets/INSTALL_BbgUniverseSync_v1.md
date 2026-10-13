# BbgUniverseSync v1 설치 (데스크톱 1회, 약 3분)

jp_model_portfolio 시트 기준. 기존 Code.gs·OrdersAPI_v1.gs는 수정하지 않는다(별도 파일 추가).

1. 시트 → 확장 프로그램 > Apps Script → 파일 + → 스크립트 `BbgUniverseSync_v1` 생성 → `BbgUniverseSync_v1.gs` 전체 붙여넣기 → 저장
   (clasp 사용 시: 프로젝트 폴더에 파일 추가 후 `clasp push`)
2. 프로젝트 설정에서 시간대가 Asia/Seoul(또는 Asia/Tokyo)인지 확인
3. 편집기에서 `bbgSyncUniverse` 1회 실행 → 권한 승인(Drive). 로그에 "변경 없음 (63종목)" 또는 텔레 "유니버스 갱신" 알림이면 정상
4. `bbgSetupTriggers` 1회 실행 → 텔레 "🔧 BBG 트리거 설치" 수신 확인

## 확인 포인트
- 텔레 알림은 OrdersAPI의 `ord_tg()`를 재사용(없으면 Script Property `TG_TOKEN`/`TG_CHAT_ID`).
- `bbgHealthCheck`가 "watchlist N종목 ≠ Drive M종목" 경보를 보내면 Drive→BBG PC 역방향 동기화가 안 되는 것 →
  BBG PC에서 `C:\Bloomberg_Inbox\watchlist.csv`를 Drive 파일로 교체(Drive for desktop 설정의 '내 컴퓨터' 폴더 동기화 상태 확인).
- 덤프 제외가 필요하면 `BBG.EXCLUDE`에 티커 추가(예: ETF 3종).
