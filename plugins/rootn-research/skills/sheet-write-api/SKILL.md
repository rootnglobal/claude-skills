---
name: sheet-write-api
version: 261023b
description: "화이트리스트된 구글 시트에 secret 인증으로 write하는 범용 시트 API 스킬(Apps Script 웹앱 SheetWriteAPI v2를 curl doPost 호출, ping/read/append/overwrite, 시트×탭×액션 화이트리스트). jp_model_portfolio 거래는 jp-port-trade, 모델포트 셀 정정은 build B로 — 이 API를 쓰지 않는다. 트리거: 시트에 써줘/추가해줘, 구글시트 append, 시트 값 덮어써, sheet write API."
---

# sheet-write-api — 범용 시트 write API

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다.

## 시스템 개요 (이 스킬이 SSOT — 매 세션 재설명 불필요)

- 정체: **독립형** Apps Script 웹앱 'RootN SheetWriteAPI v2'(업무 계정, 2026-10-23 재구축 — SSOT rootnglobal/claude-skills-2 → `_apps/sheet_write_api/`(비공개)). 요청·응답 형식은 v1과 같다. 모델포트 Code.gs·jp_model_portfolio 와 무관, clasp 별도 프로젝트. MCP 커넥터 아님 — curl `doPost` 로 호출.
- 목적: 어느 Claude 세션이든 **화이트리스트된** 구글 시트에 secret 만으로 read/append/overwrite.
- 안전 가드(무거운 2FA 폴링 없음):
  1. **시트×탭×액션 화이트리스트** — 시트마다 허용 탭과 액션(read/append/overwrite)을 따로 등록. 기본은 read 만, append/overwrite 는 명시한 탭만(로그·백업 탭은 append 만, 파생 탭만 overwrite). 탭 와일드카드 없음.
  2. **모든 write 감사** — 대상 시트의 숨김 탭 `_SWAPI_audit`에 시각·source·action·tab·range·크기·reason·overwrite 이전값·결과 기록(감사 탭 자체는 쓰기 불가).
  3. **입력 가드** — `=`로 시작하는 값(수식)은 허용 등록된 시트만, range 는 시트 접두 없는 A1 표기만, 요청·행수·셀수 상한.
- SECRET 은 응답·산출물·로그에 **절대 출력 금지**.

## 클로드 실행 절차

1. **접속정보**: Drive `Investment Research/_config/rootn_sheet_write_api_v2.txt` 검색·읽기 → `url=`, `secret=` 파싱(레지스트리 'RootN API Keys' service="범용 시트 write API", key_name="v2 url·secret" 이 이 파일을 가리킨다).
   - 폴백(1회성): v2 파일이 없을 때만 구 `rootn_sheet_write_api.txt`(v1, 개인 계정 배포 — 비활성화 예정). 둘 다 없으면 중단하고 사용자에게 보고.

2. **호출** (cloud bash 에서 curl, `-L` 필수 — Apps Script 302 리다이렉트):
   ```bash
   curl -sL -X POST "$URL" -H 'Content-Type: application/json' -d '<json>'
   ```
   공통 필드: `secret`(필수), `source`(권장 — 호출 주체, 감사에 남음).
   - **ping**: `{"secret":"…","action":"ping"}` → `{ok,version,whitelist:[{name,actions,tabs,tabsByAction,allowOverwrite,sheets,protectedTabs}]}` (시트 id 는 싣지 않음)
   - **read**: `{"secret":"…","action":"read","id":"<sheetId>","tab":"<탭>","range":"A1:D20"}` (range 생략=전체) → `{ok,values}`
   - **append**(append 허용 탭만): `{"secret":"…","action":"append","id":"…","tab":"…","values":[["…","…"]],"reason":"…","source":"…"}` (values 2D) → `{ok,appendedRange,rows}`
   - **overwrite**(overwrite 허용 탭만, `reason` 필수): `{"secret":"…","action":"overwrite","id":"…","tab":"…","range":"B2:C3","values":[[…]],"reason":"필수","source":"…"}` (range 셀수=values 차원) → `{ok,overwroteRange}`

3. **결과 해석**: `auth`=secret 불일치(creds 최신 확인) · `not configured`=서버 setup 전 · `not whitelisted`=시트 미등록 · `action not allowed: …`=그 시트에 해당 액션 미등록 · `tab not allowed`=탭 미등록 또는 그 액션이 허용되지 않은 탭(로그·백업 탭 overwrite → append 로 대체) · `tab not found` · `range … != values dims`=차원 맞출 것 · `formula not allowed` · `reason required for overwrite` · `bad range`=시트 접두 없이 A1 만 · `blocked sheet (jp_model_portfolio)`. 등록·권한 변경은 데스크톱 편집기 `swapi_addSheet(...)` 몫 — API 로는 못 바꾼다.

4. **write 전 확인**: overwrite 는 파괴적 — id·tab·range 를 사용자 의도와 대조, 애매하면 먼저 read 로 현재값 확인 후 진행. `reason` 은 항상 의미있게(감사 추적).

5. **fail-fast**: curl 2회 실패 시 중단, 원인 후보 보고(HTML 403 '액세스 거부됨'=웹앱 권한 미승인 → 편집기 `swapi_selfTest`, `not configured`=setup 전, `auth`=secret 불일치). 같은 호출 3회 반복 금지.

## 경계 — 이 API 로 하지 말 것

- jp_model_portfolio 거래 입력 → `jp-port-trade`(텔레 토큰 2FA).
- 모델포트 셀 정정 → build B(수정기능, 2FA·이력). raw overwrite 로 성역(로그) 금지.
- 화이트리스트 밖 시트·탭·액션 → 데스크톱 명시 등록 후에만. 와일드카드 전체허용 없음.
- jp_model_portfolio 읽기(예: GitHub Actions 타깃 탭) → 모델포트 자체 읽기 전용 export 웹앱(`_apps/jp_model_portfolio`, `exportApi_`). SWAPI v2 는 jp_model_portfolio 를 등록·호출 모두 거부한다.

## 보안 규칙

- secret 을 대화·산출물에 출력하지 않는다. creds 는 Drive `_config/rootn_sheet_write_api_v2.txt`(+ 레지스트리 참조 행)에만. 서버는 secret 의 SHA-256 만 보관. 코드·repo·파일에 secret 저장 금지.
- 로그·백업·감사 탭은 성역 — overwrite 시도 자체를 하지 말 것(서버도 overwrite 미허용으로 등록).

## 서버 코드·설치

- 서버는 **독립 clasp 프로젝트** 'RootN SheetWriteAPI v2'(업무 계정, 모델포트 clasp 밖). 소스 = SSOT `_apps/sheet_write_api/`(`Code.js`·`appsscript.json`, 공개 배포 밖). 설치·로테이션·화이트리스트 형식은 `_apps/README.md` 'sheet_write_api/' 절.
- 화이트리스트(Script Property `SWAPI_WHITELIST`) 등록: 데스크톱 편집기 `swapi_addSheet('<시트id>','이름','탭1,탭2','read,append')`(actions 생략=read 만), 확인 `swapi_selfTest`, 삭제 `swapi_removeSheet`. 탭별로 액션을 나누려면 스크립트 속성 JSON 의 `tabsByAction`.
- 2026-10-23 라이브 검증 16/16(ping·read·append·overwrite·read-back + 화이트리스트 밖 시트·탭·액션, 틀린 secret, 수식, reason 누락, 차원 불일치, 시트 접두 range 거부).
