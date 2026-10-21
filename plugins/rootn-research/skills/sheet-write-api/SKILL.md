---
name: sheet-write-api
version: 261021
description: "임의의 Claude 세션이 화이트리스트된 구글 시트에 secret 인증만으로 안전하게 write 하는 범용 시트 write API 스킬(독립형 Apps Script 웹앱 SheetWriteAPI_v1.gs 를 curl doPost 로 호출). actions=ping/read/append/overwrite. \"시트에 써줘/추가해줘\", \"구글시트 append\", \"시트 값 덮어써\", \"범용 시트 API\", \"sheet write API\", 시트 id·탭과 함께 write/append/overwrite 맥락에서 사용. 단 jp_model_portfolio 거래는 jp-port-trade(2FA), 모델포트 셀 정정은 build B 로 — 이 API 로 하지 말 것. creds 는 Drive rootn_sheet_write_api.txt/registry. RootN 리서처 전용."
---

# sheet-write-api — 범용 시트 write API

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다.

## 시스템 개요 (이 스킬이 SSOT — 매 세션 재설명 불필요)

- 정체: **독립형** Apps Script 웹앱(`SheetWriteAPI_v1.gs`, SSOT rootnglobal/claude-skills-2 → skills/sheet-write-api/assets/). 모델포트 Code.gs·jp_model_portfolio 와 무관, clasp 별도 프로젝트. MCP 커넥터 아님 — curl `doPost` 로 호출.
- 목적: 어느 Claude 세션이든 **화이트리스트된** 구글 시트에 secret 만으로 read/append/overwrite.
- 안전 2중 가드(무거운 2FA 폴링 없음):
  1. **화이트리스트가 로그·백업을 성역화** — API 가 overwrite 불가, append/read 만. 파생 시트(홀딩스·NAV·작업시트)만 자유 overwrite(실수 용인, 복구는 로그→재계산·build F 백업).
  2. **모든 write 감사** — 대상 시트의 `_SWAPI_audit` 탭에 시각·source·action·range·old→new·reason·secret여부·결과 기록.
- SECRET 은 응답·산출물·로그에 **절대 출력 금지**.

## 클로드 실행 절차

1. **접속정보**: Drive 에서 `rootn_sheet_write_api.txt` 검색·읽기 → `url=`, `secret=` 파싱. 없으면 API 미설치 — 사용자에게 데스크톱 1회 설치(INSTALL 체크리스트) 안내 후 중단. (레지스트리 'RootN API Keys' service="범용 시트 write API" 경유도 가능.)

2. **호출** (cloud bash 에서 curl, `-L` 필수 — Apps Script 302 리다이렉트):
   ```bash
   curl -sL -X POST "$URL" -H 'Content-Type: application/json' -d '<json>'
   ```
   공통 필드: `secret`(필수), `source`(권장 — 호출 주체, 감사에 남음).
   - **ping**: `{"secret":"…","action":"ping"}` → `{ok,version,whitelist:[{name,allowOverwrite,sheets,protectedTabs}]}`
   - **read**: `{"secret":"…","action":"read","id":"<sheetId>","tab":"<탭>","range":"A1:D20"}` (range 생략=전체) → `{ok,values}`
   - **append**(성역 탭에도 허용): `{"secret":"…","action":"append","id":"…","tab":"…","values":[["…","…"]],"reason":"…","source":"…"}` (values 2D) → `{ok,appendedRange,rows}`
   - **overwrite**(파생 탭만): `{"secret":"…","action":"overwrite","id":"…","tab":"…","range":"B2:C3","values":[[…]],"reason":"필수","source":"…"}` (range 셀수=values 차원) → `{ok,overwroteRange}`

3. **결과 해석**: `auth`=secret 불일치(creds 최신 확인) · `sanctuary tab … blocked`=로그/백업 성역(append 로 대체) · `allowOverwrite=false`=read/append 전용 등록 · `not whitelisted`/`tab not allowed`=데스크톱 `swapi_addSheet(...)` 필요 · `range … != values dims`=차원 맞출 것.

4. **write 전 확인**: overwrite 는 파괴적 — id·tab·range 를 사용자 의도와 대조, 애매하면 먼저 read 로 현재값 확인 후 진행. `reason` 은 항상 의미있게(감사 추적).

5. **fail-fast**: curl 2회 실패 시 중단, 원인 후보 보고(URL 만료→재배포/swapi_setup, 익명 액세스 미설정=HTML 로그인 응답, secret 불일치). 같은 호출 3회 반복 금지.

## 경계 — 이 API 로 하지 말 것

- jp_model_portfolio 거래 입력 → `jp-port-trade`(텔레 토큰 2FA).
- 모델포트 셀 정정 → build B(수정기능, 2FA·이력). raw overwrite 로 성역(로그) 금지.
- 화이트리스트 밖 시트 → 데스크톱 명시 등록 후에만. 와일드카드 전체허용 없음.

## 보안 규칙

- secret 을 대화·산출물에 출력하지 않는다. creds 는 Drive `rootn_sheet_write_api.txt` + 'RootN API Keys' 레지스트리에만. 코드·repo·파일에 secret 저장 금지.
- 로그·백업·감사 탭은 성역 — overwrite 시도 자체를 하지 말 것.

## 서버 코드·설치

- 서버는 **독립 clasp 프로젝트**(모델포트 clasp 밖). canonical 사본 = SSOT assets 의 `SheetWriteAPI_v1.gs`·`appsscript.json`. ⚠ 2026-10-21 기준 repo·Drive 어디에도 사본이 없다 — 데스크톱 clasp 프로젝트에서 `skills/sheet-write-api/assets/`로 반입 필요(반입 전까지 서버 수정은 clasp 원본에서). 설치·화이트리스트 구성은 `INSTALL_SheetWriteAPI_v1.md`(데스크톱 1회): swapi_setup() → 웹앱 배포(익명) → swapi_addSheet(id,name,allowOverwrite,sheetsCsv,protectedCsv) → registry 등록.
