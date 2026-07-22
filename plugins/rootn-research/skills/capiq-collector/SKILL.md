---
name: capiq-collector
version: 260721b
description: >-
  S&P Capital IQ(www.capitaliq.spglobal.com)에서 Claude in Chrome으로 종목 자료를 수집하는 스킬.
  수집 대상: (1) earnings call transcripts 최근 2년(Q&A 포함) → Drive IR/transcripts/,
  (2) 셀사이드 리포트(Aftermarket Research, entitlement 범위) → 리서치/,
  (3) 컨센서스 상세(애널리스트 수, high/low/mean, revisions, 세그먼트 추정) Excel export → 리서치/consensus/,
  (4) Key Developments·comps (요청 시). Chrome에 CapIQ 로그인 상태 필수.
  "CapIQ", "Capital IQ", "캡아이큐", "CapIQ transcript", "어닝콜 transcript 수집", "CapIQ 컨센서스",
  "CapIQ 셀사이드", "transcript 받아줘" 등의 키워드, 또는 ir-research-pipeline·jp-research-collector가
  CapIQ 단계를 호출할 때 이 스킬을 사용할 것. 미국·중국 종목 셀사이드와 일본 중소형 transcript 공백
  보완에 특히 유용. RootN 리서처 전용. (v260721, 설계 v260715 재구현)
---

# capiq-collector — S&P Capital IQ 자료 수집

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`를 읽고 전 구간에 적용한다 — fail-fast,
> 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년.
> 태스크 완료 후 스킬 피드백 루프: 새로 확인된 CapIQ 경로·엘리먼트·우회법은
> `references/capiq-paths.md`에 즉시 기록하고 SSOT repo 반영을 flagging한다.

## 0. 전제 조건 (하나라도 미충족 시 즉시 중단·보고)

1. **Claude in Chrome 연결** — 브라우저 도구(`mcp__remote-devices__` 경유 Chrome MCP)가 살아 있어야 한다.
   모바일·헤드리스 세션이면 이 스킬은 실행 불가 → "메인 컴퓨터에서 실행 필요"로 보고하고 종료.
2. **CapIQ 로그인 상태** — www.capitaliq.spglobal.com 접속 시 로그인 화면·2FA가 나오면
   **자동 로그인 시도 금지**. 즉시 사용자에게 로그인 요청 후 중단. (fail-fast)
3. 대상 종목의 Drive 폴더(`Investment Research/[영문명 (코드)]/`)가 없으면 생성한다
   (drive-folder-organizer 규칙 준수).

## 1. 수집 대상과 우선순위

| 순위 | 데이터 | 방법 | Drive 목적지 |
|---|---|---|---|
| 1 | **Earnings call transcripts** (최근 2년, Q&A 포함) | 종목 페이지 → Documents/Transcripts → Word/PDF 다운로드 | `IR/transcripts/` |
| 2 | **셀사이드 리포트** (Aftermarket Research, entitlement 범위) | Research 탭 브로커 PDF. **미국·중국 종목 우선** | `리서치/` |
| 3 | **컨센서스 상세** (애널리스트 수, high/low/mean, revisions, 세그먼트 추정) | 표의 **Excel export 버튼** 우선 (스크래핑은 fallback) | `리서치/consensus/` |
| 4 | Key Developments 타임라인, comps | Excel export | `리서치/` (사용자 요청 시에만) |

역할 분담(스킬 세트 전체 기준): **숫자=Bloomberg BEst 1차(CapIQ는 검증/fallback)**,
**transcript·미중 셀사이드=CapIQ 1차**, 한국 셀사이드=FnGuide, 일본 무료 소스는 기존 스킬 유지.

## 2. 워크플로우

### 2-1. 종목 식별
- 티커·회사명으로 CapIQ 상단 검색. 동명이사 있으면 거래소·국가로 확정 (순수 식별 모호 시 사용자 확인 허용).
- 종목 페이지 도달 후 URL의 company id를 기록해 둔다 (이후 직행용, capiq-paths.md에 축적).

### 2-2. Transcripts (우선순위 1)
1. 좌측 메뉴 Documents → Transcripts (또는 News/Events → Transcripts).
2. 기간 필터 최근 2년. earnings call 유형 위주로 전량 열거 — **목록을 먼저 전부 세고 시작**한다
   (몇 건 중 몇 건 확보인지 보고에 필요).
3. 각 transcript를 Word(우선) 또는 PDF로 다운로드. 파일명:
   `[YYYY-MM-DD]_transcript_[Qn_FYyy].docx` (ASCII).
4. 다운로드 실패 항목은 개별 기록(항목·사유·링크).

### 2-3. 셀사이드 리포트 (우선순위 2)
1. Research 탭 → 대상 종목 필터, 기간 2년.
2. entitlement 범위 내 브로커 PDF 다운로드. 파일명: `[YYYY-MM-DD]_리서치_[브로커]_[제목요약].pdf`
   는 비ASCII 우려 시 `[YYYY-MM-DD]_research_[broker].pdf`.
3. entitlement 밖(잠김) 리포트는 제목·브로커·날짜만 목록으로 기록(수집 불가 사유 명시).

### 2-4. 컨센서스 상세 (우선순위 3)
1. Estimates 탭 → Consensus Detail / Estimates Revisions / Segment Estimates.
2. 각 표의 **Excel export 버튼**을 사용 (화면 스크래핑은 export 부재 시에만).
3. 파일명: `[티커]_capiq_consensus_[YYYYMMDD].xlsx` 등.

### 2-5. Drive 업로드
- 표준 구조 `Investment Research/[영문명 (코드)]/{IR/transcripts/, 리서치/, 리서치/consensus/}`.
- 공통 규칙의 3점 검증(새 파일명, id·수정시각·용량 확인, 내용·언어 재확인) 적용.
- 기존 자료와 중복이면 재업로드하지 않고 스킵 목록에 기록.

## 3. fail-fast 규칙 (엄격 적용)

- 세션 만료·2FA·CAPTCHA → **즉시 중단**, 사용자에게 재로그인 요청. 자동 재시도 금지.
- 커버리지 없음(transcript 0건 등) → "없음(확인)"으로 기록하고 다음 항목으로.
- 같은 클릭·같은 페이지 로드 3회 반복 금지. 소스당 시도 1~2회.
- 실패분은 항목·소스·날짜·사유·링크로 **개별** 보고 (모호한 "n건 실패" 금지).

## 4. 결과 보고 형식

| # | 자료 | 기간/건수 | 상태(수집/미확보/없음(확인)) | Drive 경로 |
|---|---|---|---|---|

+ 실패·잠김 항목 개별 목록, entitlement 관찰 사항.

## 5. 경로·entitlement 기록 (첫 실행 시 필수)

첫 실행에서 실측한 것들을 `references/capiq-paths.md`에 기록한다:
- 메뉴 경로·URL 패턴 (transcript 목록, research 필터, estimates export)
- Excel export 버튼 위치·동작 방식
- entitlement 범위 (열람 가능 브로커, Aftermarket 여부, 잠긴 항목 패턴)
- 일본 중소형 transcript 커버리지 하한 (설계 오픈 이슈 #2)

기록 후 SSOT repo(claude-skills) 반영 필요를 flagging한다.
