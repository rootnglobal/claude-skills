---
name: api-key-registry
version: 261023
description: "RootN API 키·인증키 레지스트리(구글시트 'RootN API Keys') 조회·등록 스킬. API 키·서비스키·토큰이 필요하면 사용자에게 묻기 전에 먼저 조회하고, 401/Unauthorized/키 미설정 오류 때도 사용. 새 키를 받으면 등록을 제안. 트리거: API 키 어디 있어, 인증키 등록, 키 저장, 서비스키 필요, 키 관리, 토큰 찾아줘."
---

# api-key-registry

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다.

RootN의 모든 API 키·토큰의 단일 참조점(SSOT)은 구글시트 **'RootN API Keys'** 다.

- 찾는 법: Drive `search_files`로 `title = 'RootN API Keys'`(스프레드시트) 검색 → 파일 id 확보. 문서에 id를 적지 않는다.
- 컬럼: `service, key_name, key_value, account, issued, limits, used_by, notes`
- 원칙: 키가 필요한 모든 작업은 **레지스트리 조회 → 없으면 발급/요청 → 발급 즉시 등록** 순서.

## 1. 키 조회 (읽기)

1. 위에서 찾은 파일 id를 `mcp__Google_Drive__read_file_content` 로 읽는다 (마크다운 표로 반환됨).
   - 같은 제목이 여러 개면 수정시각 최신·소유자 본인 파일을 쓰고, 나머지는 보고만 한다(레지스트리 분열 점검).
2. `service`/`used_by`/`notes` 컬럼에서 필요한 서비스를 매칭한다. 부분일치 허용 (예: "공공데이터포털" ↔ "data.go.kr").
3. `key_value`가 `(값은 ... 참조)` 형태면 실제 값은 해당 위치(Drive 파일 등)에서 읽는다.
4. 레지스트리에 없으면: 사용자에게 키 요청 또는 발급 절차 안내. **발급받으면 즉시 2번 절차로 등록 제안.**

## 2. 키 등록·수정 (쓰기)

Drive MCP는 구글시트 셀 수정이 불가하다(파일 신규 생성만 가능). 절대 'RootN API Keys' 시트를 새 파일로 다시 만들지 말 것(레지스트리 분열 금지). 등록은 아래 경로를 우선순위 A→B→C로 사용:

- **A. 레지스트리 API에 POST (기본)**: RootN Registry API(Apps Script Web App)에 POST해서 행을 upsert한다.
  - 웹앱 URL·secret: Drive `Investment Research/_config/rootn_registry_api_v2.txt`(`url=`, `secret=`) 참조.
    - 폴백 없음: 구 `rootn_registry_api.txt`는 2026-10-23 secret 교체로 무효(`unauthorized`). v2 파일이 없으면 B로.
  - 요청: `POST {webapp_url}`, JSON body `{ "secret": "...", "action": "upsert", "rows": [ {service, key_name, key_value, account, issued, limits, used_by, notes} ] }` (rows 최대 20개, 셀 5000자). upsert는 service+key_name 일치 행이 있으면 갱신(빈 필드는 기존값 유지), 없으면 append.
  - 등록 확인: `{"secret":"...","action":"find","service":"...","key_name":"..."}` → 일치 행 메타(row·account·issued·used_by·has_value). key_value 는 돌려주지 않는다. 오류: `unauthorized`(secret 불일치) · `not configured` · `internal error`.
  - curl 사용 시: 응답이 302로 `script.googleusercontent.com/macros/echo?...`를 가리키는데, `curl -L`이 POST를 그대로 재전송해 405가 날 수 있다. Location 헤더를 직접 받아 그 URL로 **GET** 재요청할 것.
  - 웹앱이 403("You need access")을 내면: 조직 정책이 아니라 스크립트 소유자가 Apps Script 편집기에서 함수를 1회도 실행하지 않아 OAuth 동의(SpreadsheetApp 권한)가 안 된 경우가 흔하다 — `script.google.com/d/{script_id}/edit`에서 함수 1회 수동 실행 후 재시도(재배포 불필요).
  - 등록 후 read_file_content로 재확인.
- **B. Chrome 자동화 (폴백)**: A가 막히면(웹앱 접근 불가 등) Claude in Chrome이 연결돼 있을 때 시트 URL
  (1단계에서 찾은 id의 `/spreadsheets/d/{id}/edit`)를 열어 마지막 행 아래에 새 행을 직접 입력한다. 입력 후 read_file_content로 재확인.
- **C. 사용자 입력 요청 (최종 폴백)**: A, B 모두 안 되면 추가할 행을 탭 구분 한 줄로 정리해 사용자에게 전달하고 시트에 붙여넣도록 요청한다.

등록 시 채울 것: service(서비스명), key_name(키 종류), key_value(값 — 단 고민감 키는 값 대신 참조 위치), account(발급 계정), issued(YYYY-MM-DD), limits(한도), used_by(사용하는 스크립트·스킬·트리거), notes(활용신청 범위, 재발급 방법 등).

## 3. 보안 규칙

- 키 값을 대화·산출물에 불필요하게 반복 노출하지 말 것. 확인용으로는 앞 6자리 + "…" 만 표기.
- 고민감 키(쓰기 권한 PAT, 증권사 트레이딩 API, 결제 관련)는 시트에 **값을 쓰지 않고** Drive 개별 파일 참조로 등록 (예: GitHub PAT → `rootn_gh_pat.txt` 참조).
- 무료·공공데이터급 키(FRED, data.go.kr 등)는 값 직접 기재 허용.
- 키를 스크립트에 내장할 때는 기존 패턴을 따른다: env var → 스크립트 옆 키파일 → DEFAULT 상수 (liquidity_monitor.py의 FRED/DATAGO 참조 순서와 동일).

## 4. 현재 등록된 키 (2026-07 기준 스냅샷 — 항상 시트가 우선)

| service | 용도 | 위치 |
|---|---|---|
| FRED | 미국 거시 시계열 | 시트 + liquidity_monitor.py 내장 |
| data.go.kr | 금융위 파생상품시세(한국 옵션) | 시트 + datago_key.txt |
| Telegram | 유동성 모니터 발송 봇 | 시트 + 각 트리거 프롬프트 |
| GitHub PAT | claude-skills-2 트래커 state push (Actions 이전 후 revoke 예정) | 값은 Drive rootn_gh_pat.txt |
