---
name: ir-tracker
version: 260721
description: "Gmail에서 IR 미팅 요청 발송 메일을 검색하여, 구글 시트(IR 미팅/콜 관리)의 '요청/진행사항' 탭을 자동으로 업데이트하는 스킬. 발송 이력, 답변 여부, 답변 내용 요약, 담당자 정보를 Gmail 스레드에서 추출하여 시트에 반영한다. 'IR 시트 업데이트', 'IR 트래커', 'IR 미팅 관리 시트', 'IR 현황 업데이트', 'IR 진행상황 정리', 'Gmail IR 메일 정리', 'IR 파이프라인 업데이트', 'IR 시트 동기화', 'IR 발송 내역 정리' 등의 키워드가 나오면 이 스킬을 사용할 것. IR 미팅 요청 메일을 보낸 뒤 시트를 최신 상태로 맞추고 싶을 때, 또는 정기적으로 IR 진행 상황을 시트에 반영하고 싶을 때 사용한다."
---

# IR 미팅/콜 관리 시트 자동 업데이트 스킬

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.

 
## 개요
 
RootNGlobal/Root & Global이 IR 미팅 요청을 위해 발송한 이메일과 그에 대한 답장을 Gmail에서 검색하여, 구글 시트 "IR 미팅/콜 관리"의 **요청/진행사항** 탭을 자동으로 업데이트한다.
 
이 스킬의 핵심 가치는 수동으로 Gmail과 시트를 왔다갔다하며 업데이트하는 번거로움을 없애는 것이다. Gmail이 "진실의 원천(source of truth)"이고, 시트는 그 요약 대시보드 역할을 한다.
 
## 대상 구글 시트
 
- **시트 URL**: `https://docs.google.com/spreadsheets/d/199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w/edit?gid=0#gid=0`
- **시트 ID**: `199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w`
- **탭 1**: `요청/진행사항` (gid=0) — IR 요청 진행 관리 메인 탭
- **탭 2**: `연락처 리스트` (gid=331223742) — IR 담당자 연락처 DB
 
### 시트 컬럼 구조 (요청/진행사항 탭)
 
| 컬럼 | 내용 | 예시 |
|------|------|------|
| A: 회사 | 회사명 (순수 회사명만, 티커 제외) | 에스엠, CATL, Naura Tech |
| B: 티커 | 종목코드 | 7309 JP, 300496, 002028 CH, TAL US |
| C: 요청사항 | 탐방/콜 등 | 탐방, 콜 |
| D: 요청 중요도 | 상/중/하 | 상 |
| E: 컨택일자 | 최초 연락일 | Y, Y/26-01-21 |
| F: 답변여부 | 답변 받았는지 | Y, 빈값 |
| G: 다시연락할일자 | 팔로업 예정일 | N/A, 날짜 |
| H: 다시연락한일자 | 실제 팔로업일 | Y/26-02-19 |
| I: 미팅일자 | 확정된 미팅 일정 | 2026.03.15 (11:00 am) |
| J: 기타 진행현황 | 자유 텍스트 메모 | 통역 섭외 완료, 답변 받음 |
| K: 담당자 | IR 담당자 이름 | 유수진 |
| L: 담당부서/직함 | 부서/직함 | IR, IR Director |
| M: 연락처 | 이메일/전화 | stock@gigavis.com |
| N: 통역가 연락처 | 통역사 정보 | |
| O: 주소 | 미팅 장소/링크 | 서울시 성동구... |
| P: 출입방법 | 방문 안내 | 1층 안내데스크에서... |
 
### 시트 컬럼 구조 (연락처 리스트 탭, gid=331223742)
 
| 컬럼 | 내용 | 예시 |
|------|------|------|
| A: 섹터 | 산업 분류 | 반도체, 2차전지, 엔터, IP |
| B: 회사명 | 회사명 | 매커스, SKC, 에스엠 |
| C: 담당자 | 이름 + 직함 | 이경준 부장, IR팀, 유수진 선임 |
| D: 연락처1 | 전화/이메일 | 02-3490-9514, sujin.you@smtown.com |
| E: 연락처2 | 보조 연락처 | 010-2006-7569 |
| F: 주소 | 회사 주소 | 서울시 강남구 테헤란로 626 |
| G: 비고 | 참고사항 | 탐방가능, *연락가능 수신처 |
 
## 워크플로우
 
### Step 1: Gmail에서 IR 발송 메일 검색
 
Gmail MCP `search_threads` 도구를 사용하여 IR 미팅 요청 메일을 검색한다.
 
**검색 쿼리** (두 가지를 병렬로 실행):
```
1. subject:"IR 미팅 요청" in:sent
2. subject:"IR Meeting Request" in:sent
```
 
두 검색 결과를 합쳐서 중복(같은 threadId) 제거한다.
 
**각 메일에서 추출할 정보:**
- `threadId` — 답장 확인용
- `headers.To` — 수신자 이메일 (= IR 연락처)
- `headers.Date` — 발송 일자 (= 컨택일자)
- `headers.Subject` — 제목에서 회사명 유추 가능
- `snippet` / `body` — 본문에서 회사명 추출
 
**회사명 추출 방법:**
- 한국어 템플릿: `"안녕하십니까, {회사명} IR 담당자님"` 패턴에서 추출
- 중국어 템플릿: `"尊敬的{회사명}投资者关系团队"` 패턴에서 추출
- 영문 템플릿: `"Dear {회사명} IR Team"` 패턴에서 추출
- 팔로업 메일: `"就我们于...发出的投资者关系会议请求进行跟进"` 등의 패턴에서도 앞부분의 회사명 추출
 
**팔로업(follow-up) 메일 처리:**
같은 회사에 대해 최초 IR 요청 메일과 팔로업 메일이 별도 스레드로 존재할 수 있다. 팔로업 메일의 발송 날짜는 `다시연락한일자(H)` 컬럼에 기록해야 하므로, 같은 회사에 대한 여러 스레드를 시간순으로 정리하는 것이 중요하다. 가장 이른 날짜가 `컨택일자(E)`, 이후 날짜가 `다시연락한일자(H)`에 해당한다.
 
### Step 2: 각 스레드의 답장 상태 확인
 
각 고유 threadId에 대해 Gmail MCP `get_thread`를 호출하여 전체 대화를 확인한다.
 
**판단 기준:**
- 스레드에 `from:` 이 IR 수신자(To에 해당하는 이메일 도메인)인 메시지가 있으면 → **답변 있음 (Y)**
- 아무 답장도 없으면 → **답변 없음 (빈값 유지)**
- 답장이 있으면 해당 답장에서 추가 정보 추출:
  - 답변자의 이름, 직함 (서명 블록에서)
  - 미팅 일정 관련 언급 여부
  - 핵심 진행 상황 요약 (1줄)
 
**주의:** 우리 쪽(rootnwm.com·rootnglobal.com 도메인 전체 — 발신 주소는 common-rules §8 / `_config/sender.txt` 참조)이 보낸 메시지는 "답변"으로 카운트하지 않는다. 상대방 IR팀이 보낸 메시지만 답변으로 인정한다.
 
### Step 3: 현재 시트 데이터 읽기

**헤더 검증(필수, 편집 전):** 시트 1행(헤더)을 읽어 위 '시트 컬럼 구조'와 컬럼명·순서가
일치하는지 확인한다. 불일치하면 셀 편집을 시작하지 말고 실제 헤더를 사용자에게 보고한다
(컬럼 이동·추가 가능성 — 잘못된 열에 쓰는 사고 방지).
 
Chrome 브라우저로 구글 시트에 접속하여 현재 데이터를 읽는다.
 
**방법: gviz JSON API (가장 안정적, 셀 내 줄바꿈에도 안전)**
 
먼저 시트 URL로 navigate한 뒤, 같은 탭에서 javascript_tool로 fetch를 실행한다:
```javascript
// JSON 형식이 CSV보다 안정적 (셀 내 줄바꿈 처리 가능)
(async () => {
  const sheetId = '199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w';
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?tqx=out:json&gid=0&tq=SELECT A,B,C,D,E,F,G,H,I,J,K,L,M WHERE A IS NOT NULL`;
  const resp = await fetch(url);
  const text = await resp.text();
  const json = JSON.parse(text.replace(/^[^(]*\(/, '').replace(/\);?\s*$/, ''));
  const rows = json.table.rows;
  return rows.map(r => {
    const vals = r.c.map(c => c ? (c.v || '') : '');
    return vals.join(' | ');
  }).join('\n');
})();
```
 
이 방식의 장점:
- CSV와 달리 셀 내 줄바꿈이 있어도 파싱이 깨지지 않음
- SQL-like 쿼리로 필요한 컬럼만 선택 가능
- 구글 시트 페이지에서 실행하면 인증 문제 없음
 
**주의: 시트 페이지에 먼저 navigate한 후에 javascript_tool로 fetch해야 한다.** 다른 페이지에서 실행하면 CORS 에러 발생.
 
### Step 4: 업데이트 대상 결정
 
Gmail 데이터와 시트 데이터를 비교하여 업데이트가 필요한 항목을 결정한다.
 
**매칭 로직 (중요 — 다국어 회사명 매칭):**
 
IR 메일은 한국어, 중국어, 영어로 발송되므로, Gmail에서 추출한 회사명과 시트의 회사명이 다른 언어일 수 있다. 실전에서 흔한 불일치 예시:
 
| Gmail (메일 본문) | 시트 A열 | 매칭 단서 |
|---|---|---|
| 思源电气 (중문) | 사윈전기 (002028 CH) | 티커 002028, 도메인 sieyuan.com |
| 蓝色光标 (중문) | bluefocus (300058 ch) | 도메인 bluefocus.com |
| 好未来 (중문) | TAL EDU (TAL US) | 도메인 tal.com |
| VeriSilicon (영문) | 신위안마이크로 (VeriSilicon, 688521 SH) | 시트 A열에 영문명 포함 |
 
매칭 전략 (순서대로 시도):
1. **시트 A열에 영문명이 괄호 안에 포함** → 영문 부분 매칭 (예: "VeriSilicon" ↔ "신위안마이크로 (VeriSilicon, 688521 SH)")
2. **Gmail의 To 이메일 도메인** ↔ **시트 M열 연락처의 도메인** (예: sieyuan.com ↔ webmaster@sieyuan.com)
3. **티커/종목코드** 매칭 — Gmail 제목이나 본문에서 종목코드가 나오면 시트 B열과 비교
4. **WebSearch로 교차 확인** — 중문 회사명의 영문명/한글명을 검색하여 시트와 매칭
 
**매칭이 불확실하면 반드시 사용자에게 확인을 요청한다. 자동으로 "새 회사"라고 판단하지 않는다.**
 
**업데이트 규칙:**
 
0. **회사명(A)·티커(B) 정리 (항상 실행):**
   현재 A열에 티커가 혼재된 경우가 많다. 업데이트 시 이를 분리 정리한다.
 
   분리 패턴:
   - `"Shimano (7309 JP)"` → A: `Shimano`, B: `7309 JP`
   - `"Tsugami (6101 JP)"` → A: `Tsugami`, B: `6101 JP`
   - `"Thundersoft (300496)"` → A: `Thundersoft`, B: `300496`
   - `"COL Group, 300364.SZ"` → A: `COL Group`, B: `300364.SZ`
   - `"사원전기 (002028 CH)"` → A: `사원전기`, B: `002028 CH`
   - `"Naura Tech (2371 CH)"` → A: `Naura Tech`, B: `2371 CH`
   - `"신위안마이크로 (VeriSilicon, 688521 SH)"` → A: `신위안마이크로 (VeriSilicon)`, B: `688521 SH`
   - `"에프에스티 (036810 KQ)"` → A: `에프에스티`, B: `036810 KQ`
   - `"Marubeni (TYO: 8002)"` → A: `Marubeni`, B: `TYO: 8002`
 
   규칙 요약:
   - 괄호 안에 숫자가 포함된 종목코드/거래소가 있으면 → B열로 분리
   - 괄호 안에 영문 별명만 있으면 (예: VeriSilicon) → A열에 유지 (영문명은 회사 식별에 유용)
   - 쉼표 뒤에 종목코드가 있으면 (예: `COL Group, 300364.SZ`) → 쉼표 기준으로 분리
   - **이미 B열에 값이 있으면 덮어쓰지 않는다**
   - **A열 수정 시에는 기존 A열 값으로 매칭하던 다른 셀과의 연관성에 주의한다**
 
1. **시트에 이미 있는 회사:**
   - `컨택일자(E)`: 비어있거나 "Y"만 있으면 → 실제 날짜로 업데이트 (Y/YY-MM-DD 형식)
   - `답변여부(F)`: Gmail 스레드에서 답장 확인 → Y 또는 빈값
   - `연락처(M)`: 비어있으면 → Gmail의 To 이메일로 채우기
   - `담당자(K)`, `담당부서/직함(L)`: 답장에서 서명 블록 정보 추출 가능하면 채우기
   - `기타 진행현황(J)`: 답변 내용 1줄 요약 추가 (기존 내용에 덧붙이기)
   - `다시연락한일자(H)`: 팔로업 메일이 있으면 해당 날짜 기록 (Y/YY-MM-DD 형식)
 
2. **시트에 없는 새 회사:**
   - 사용자에게 새 행 추가 여부를 확인한 후 추가
   - 최소 정보: 회사명(A), 티커(B, 가능하면), 컨택일자(E), 연락처(M)
 
**절대 덮어쓰지 않는 필드:**
- `요청사항(C)`, `요청 중요도(D)` — 사용자가 수동 설정하는 필드
- `미팅일자(I)` — 이미 값이 있으면 건드리지 않음
- `통역가 연락처(N)`, `주소(O)`, `출입방법(P)` — 수동 관리 필드
- 이미 값이 있는 `컨택일자(E)`, `답변여부(F)` — 기존 정보를 덮어쓰지 않음
 
### Step 5: Chrome `computer` 도구로 시트 업데이트
 
Google Sheets는 Canvas 기반 렌더링이라 DOM 조작이 불가능하다. 따라서 **`computer` 도구의 실제 마우스/키보드 입력**이 유일하게 신뢰할 수 있는 편집 방법이다.
 
**시트 접속:**
```
navigate → https://docs.google.com/spreadsheets/d/199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w/edit?gid=0#gid=0
```
 
**셀 편집 절차 (Name Box 패턴 — 가장 안정적):**
 
각 셀에 대해 이 3단계를 반복한다:
 
1. **Name Box 클릭** — 좌측 상단의 셀 주소 표시 영역 (좌표 약 (42, 119) 부근, 스크린샷으로 정확한 위치 확인)
2. **셀 주소 타이핑** — 예: `E5`, `K23` (영문+숫자이므로 입력 문제 없음)
3. **Enter → 값 타이핑 → Enter**
 
```
computer: left_click (42, 119)   ← Name Box 클릭
computer: type "H18"              ← 목표 셀 주소 입력
computer: key "Return"            ← 셀로 이동
computer: type "Y/26-03-09"      ← 값 입력
computer: key "Return"            ← 값 확정
```
 
**한글 입력 주의사항:**
Google Sheets에서 `computer` 도구의 `type` 액션으로 한글을 입력하면 IME 조합 문제로 빈 셀로 남는 경우가 있다. 한글 텍스트를 입력해야 할 때는 다음 클립보드 우회 방법을 사용한다:
 
```javascript
// Step 1: javascript_tool로 클립보드에 한글 텍스트 설정
(async () => {
  await navigator.clipboard.writeText('기가비스');
  return 'done';
})();
 
// Step 2: computer 도구로 Ctrl+V 붙여넣기
computer: key "ctrl+v"
```
 
**업데이트 순서:**
- 기존 행 업데이트를 먼저 처리하고, 새 행 추가를 나중에 한다
- 각 셀 업데이트 후 다음 셀로 넘어가기 전에 Name Box를 다시 클릭하여 위치를 확실히 리셋한다
- 5개 이상의 셀을 업데이트할 때는 중간에 스크린샷으로 진행 상황을 확인한다
 
### Step 6: 연락처 리스트 탭 동기화
 
요청/진행사항 탭에서 새로운 IR 연락처 정보(담당자, 이메일, 전화번호 등)가 확인되면, **연락처 리스트** 탭(gid=331223742)에도 해당 회사가 있는지 확인하고, 없으면 새 행으로 추가한다.
 
**탭 이동 방법:**
```javascript
// javascript_tool로 연락처 리스트 탭 클릭
const tabs = document.querySelectorAll('.docs-sheet-tab');
for (const tab of tabs) {
  if (tab.textContent.includes('연락처')) {
    tab.click();
    break;
  }
}
```
또는 직접 navigate:
```
navigate → https://docs.google.com/spreadsheets/d/199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w/edit?gid=331223742#gid=331223742
```
 
**연락처 리스트 탭 데이터 읽기:**
```javascript
(async () => {
  const sheetId = '199m_xcnD9oRwwUTiBYxPPBv_TOutjzD_Uxy1Hemhr2w';
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?tqx=out:json&gid=331223742&tq=SELECT A,B,C,D,E WHERE B IS NOT NULL`;
  const resp = await fetch(url);
  const text = await resp.text();
  const json = JSON.parse(text.replace(/^[^(]*\(/, '').replace(/\);?\s*$/, ''));
  return json.table.rows.map(r => r.c.map(c => c ? (c.v || '') : '').join(' | ')).join('\n');
})();
```
 
**동기화 규칙:**
- 연락처 리스트 탭의 B열(회사명)에 해당 회사가 이미 있으면 → 건너뛰기 (기존 정보 우선)
- 없으면 → 마지막 행 아래에 새 행 추가:
  - A(섹터): Gmail 메일이나 회사 정보에서 유추 가능하면 기입, 불확실하면 빈값
  - B(회사명): 요청/진행사항 탭의 A열 회사명과 동일하게
  - C(담당자): Gmail 답장의 서명 블록에서 추출한 이름+직함 (예: "Effy Xu IR Director")
  - D(연락처1): IR 이메일 주소 (Gmail의 To 주소)
  - E(연락처2): 답장에서 추가 연락처가 있으면 기입
- **연락처 리스트 탭을 편집할 때도 요청/진행사항 탭과 동일한 Name Box 패턴 + 한글 클립보드 방식을 사용한다.**
- 연락처 리스트 탭 업데이트 후 요청/진행사항 탭으로 돌아온다.
 
### Step 7: 결과 보고
 
업데이트 완료 후 사용자에게 변경 사항을 요약 보고한다.
 
```
## IR 시트 업데이트 결과
 
### 업데이트된 항목
| 회사 | 변경 필드 | 이전 값 | 새 값 |
|------|-----------|---------|-------|
| VeriSilicon | 담당자(K) | (빈값) | Effy Xu |
| VeriSilicon | 담당부서(L) | (빈값) | IR Director |
 
### 새로 추가된 항목 (요청/진행사항 탭)
| 회사 | 티커 | 컨택일자 | 연락처 |
|------|------|----------|--------|
| 기가비스 | 420770 | Y/26-03-18 | stock@gigavis.com |
 
### 회사명·티커 정리
| 행 | 이전 A열 | 새 A열 | 새 B열(티커) |
|----|----------|--------|-------------|
| 9 | Shimano (7309 JP) | Shimano | 7309 JP |
| 11 | Tsugami (6101 JP) | Tsugami | 6101 JP |
 
### 연락처 리스트 탭에 추가된 항목
| 회사명 | 담당자 | 연락처1 |
|--------|--------|---------|
| VeriSilicon | Effy Xu IR Director | ir@verisilicon.com |
 
### 수동 확인 필요
(매칭 불확실한 항목 등)
```
 
## 실행 시 주의사항
 
- **시트 편집 전 반드시 현재 데이터를 먼저 읽는다.** 다른 사람이 편집 중일 수 있으므로 최신 상태를 기준으로 작업한다.
- **기존 값이 있는 셀은 함부로 덮어쓰지 않는다.** Gmail에서 새로 알게 된 정보만 추가/업데이트한다.
- **대량 업데이트 전에 사용자에게 변경 예정 사항을 먼저 보여주고 확인을 받는다.** "이렇게 업데이트할 예정입니다. 진행할까요?" 형태로 확인.
- **컨택일자 형식**: 기존 시트의 형식을 따른다. `Y` (연락함 표시만), `Y/YY-MM-DD` (연락함 + 날짜) 두 가지가 혼용된다. Gmail에서 날짜를 알 수 있으면 `Y/YY-MM-DD` 형식으로 기록한다.
- **회사명 매칭이 애매한 경우** (한글명 vs 중문명 vs 영문명): 반드시 사용자에게 확인한다. 자동 매칭하지 않는다. Step 4의 매칭 전략을 참고.
- **한글 셀 입력 시** 반드시 클립보드 방식(javascript_tool + Ctrl+V)을 사용한다. `type` 액션으로 직접 한글을 타이핑하면 Google Sheets에서 인식하지 못한다.
 
## 도구 의존성
 
이 스킬은 다음 도구들을 사용한다:
- Gmail MCP `search_threads` — IR 메일 검색
- Gmail MCP `get_thread` — 스레드 전체 읽기 (답장 확인)
- Claude in Chrome `computer` — 구글 시트 셀 편집 (Name Box 패턴으로 마우스/키보드 입력)
- Claude in Chrome `javascript_tool` — 구글 시트 데이터 읽기 (gviz JSON API), 한글 클립보드 설정
- Claude in Chrome `navigate` — 구글 시트 페이지 접속