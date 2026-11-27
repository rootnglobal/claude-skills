# capiq-mikey-registry.md — 티커/회사명 → CapIQ MI KEY 캐시

> **목적**: CapIQ 상단 Search 위젯이 자동화 입력을 완전히 거부하고(값 주입 즉시 리셋),
> 백엔드 omni-search가 gRPC-web(`/apisv3/spg-search/*`)이라 자동 재현 불가하며,
> MFE 소스는 CORS로 못 읽고, 티커형 라우트(`referenceIdentifier=`)도 해석 실패한다
> (근거: capiq-paths.md §9). → **순수 zero-input ticker→MI KEY 해석기는 이 환경에서 구현 불가.**
> 대신 **한 종목당 최초 1회만** MI KEY를 확보해 여기 캐시하면, 이후 그 종목은 입력 0으로 수집된다.
> 이것이 "내 input 최소화" 요구의 견고한 해법이다.

## 신규 종목 MI KEY 확보 프로토콜 (수집기 워크플로우 §2-1에서 호출 — 비차단)
1. **레지스트리 조회 먼저**: 시트 `capiq_mikey_registry`(아래 캐시 위치)에 티커/회사명이 있으면 그 MI KEY로 바로 진행(입력 0).
2. **미스여도 멈추지 않는다**(공통규칙 §2 ask-async): 해석되는 종목부터 먼저 다 수집하고,
   미해석분은 **한 목록으로 모아** 결과 보고에 함께 요청 — "해당 종목을 CapIQ에서 연 뒤 주소창 URL을 달라"
   (또는 MI KEY 숫자). URL 예: `.../web/client#company/profile?id=<MIKEY>` → **`id=` 뒤 숫자가 MI KEY**.
   - 사용자는 CapIQ 검색이 정상 동작(사람 입력 허용)하므로 종목을 열어 URL 복사만 하면 된다.
   - 응답이 없으면 그 종목만 스킵·개별 보고하고 나머지·다른 태스크를 계속한다. 하나로 전체를 대기시키지 않는다.
3. **확보 즉시 Drive 시트 `capiq_mikey_registry`의 `cache` 탭에 append**(티커·회사명·MI KEY·SPCIQ·확보일, 아래 캐시 위치).
4. 이후 동일 종목은 1로 해결 → **재입력 불필요**.

> ※ 향후 자동화 후보(미검증, 필요 시 조사): Screener 그리드 API(거래소:티커 필터→ID 반환 가능성),
>   Report Builder 엔티티 피커. 둘 다 REST/JSON일 여지가 있어 omni-search gRPC보다 재현 가능성 높음.
>   현 시점 미구현 — 레지스트리 캐시가 1차 해법.

## 캐시 위치 — Drive 시트 (2026-11-27 이전)
- 캐시는 이 파일이 아니라 Drive `Investment Research/_config/` 의 Google 시트 **`capiq_mikey_registry`** 에 둔다(공개 배포본에 종목·키를 남기지 않고, 어느 세션에서나 바로 append하기 위해).
  - 찾기: ① Drive `Investment Research/_config/sheet_ids.txt`의 `capiq_mikey_registry` 키 값(시트 ID)을 쓴다(`read_file_content`, 다른 키처럼 `key=value` 한 줄).
    ② 파일이나 키가 없을 때만 폴백: Drive `search_files` → `title = 'capiq_mikey_registry' and mimeType = 'application/vnd.google-apps.spreadsheet'`. ID는 문서에 쓰지 않는다.
  - 탭 `cache`: `ticker | company | mi_key | spciq_id | acquired | note` (예: `TSE:XXXX | <회사명> | <MI KEY> | <SPCIQ> | YYYY-MM-DD |`).
  - 탭 `pending`: `requested | guessed_ticker | mi_key | status` — 사용자 URL을 기다리는 종목.
- 조회: Sheets `get_values`(`cache!A:F`)로 읽어 티커·회사명으로 매칭.
- append: Sheets `update_spreadsheet`의 `appendCells`(sheetId 0) 또는 마지막 행 다음 범위에 `update_values`. 숫자 ID·날짜는 앞에 `'`를 붙여 텍스트로 쓴다. 같은 티커가 이미 있으면 덮어쓰지 말고 note에 갱신 사유를 적는다. `pending` 탭에 있던 종목은 status를 `확보`로 바꾼다.
- Sheets 커넥터가 없는 세션: 확보한 키를 결과 보고에 한 줄로 남기고 append를 실패 항목으로 표시한다(SSOT repo에는 쓰지 않는다).
