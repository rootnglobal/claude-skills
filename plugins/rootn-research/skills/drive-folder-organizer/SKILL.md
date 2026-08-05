---
name: drive-folder-organizer
version: 260721
description: "구글 드라이브 'Investment Research' 종목 폴더를 표준 구조로 자동 정리하는 스킬. 종목 폴더 안에 평평하게 쌓인 파일들을 IR/ 와 리서치/ 하위폴더로 분류하고, 중복 파일('(1)', '사본' 등)을 제거하고, 폴더명을 '[종목명] (티커)' 규칙으로 통일한다. 사용자가 '폴더 정리', '드라이브 정리', '종목 폴더 정리', '리서치 폴더 정리', 'IR 폴더 분류', '하위폴더 분리', '중복 파일 제거', '파일 분류해줘', '폴더 구조 정리', 'Investment Research 정리' 등을 언급하면 이 스킬을 사용할 것. 종목명/티커와 함께 '정리'·'분류'·'중복'·'하위폴더' 맥락이 나오면 적극 사용한다."
---

# 드라이브 종목 폴더 정리 스킬 (Drive Folder Organizer)

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


구글 드라이브 `Investment Research` 아래 종목 폴더를 표준 구조로 정리하는 워크플로우.
한 폴더에 평평하게 쌓인 IR 자료·증권사 리포트를 `IR/`·`리서치/` 하위폴더로 분류하고,
중복을 제거하며, 폴더명을 `[종목명] (티커)` 규칙으로 맞춘다.

## 표준 폴더 구조

```
Investment Research/
└── [종목명] (티커)/          ← 예: RF머트리얼즈 (327260)
    ├── IR/                   ← 사업·반기·분기보고서, 공시, IR 발표자료, 링크 노트
    └── 리서치/               ← 증권사 애널리스트 리포트
```

## 분류 규칙

| 파일 유형 | 대상 폴더 | 판별 키워드(파일명) |
|---|---|---|
| 사업보고서 / 반기보고서 / 분기보고서 | `IR/` | "사업보고서", "반기보고서", "분기보고서", "10-K", "10-Q", "Annual", "Quarterly" |
| 공시·IR 발표·실적발표·기업설명회 | `IR/` | "IR", "실적", "발표", "공시", "Earnings", "Presentation", "결산설명" |
| 증권사 애널리스트 리포트 | `리서치/` | 증권사명 — 한국("하나증권", "메리츠", "신한", "키움", "신영" 등) + 해외("Goldman", "Morgan Stanley", "JPMorgan", "UBS", "Citi", "Jefferies", "CLSA", "Nomura", "野村", "Daiwa", "大和", "Mizuho", "みずほ", "SMBC", "CICC", "中金", "中信"), "Shared Research", "FISCO", "리포트", "탐방노트", "Review", "Initiation" |
| 분류 애매 | 사용자에게 확인 | — |

중복 판정: 동일 파일명에 `(1)`, `(2)`, ` - 사본`, `사본`, `copy` 등이 붙은 파일, 또는
이름·크기·내용이 동일한 파일. 가장 정식 이름(접미사 없는 쪽)을 남기고 나머지를 제거.

**보존 예외**: 종목 폴더 안의 `Model/`, `AI리서치/`, `리서치/_생태계/` 하위폴더(및 내용물)는
분류·이동·중복 제거 대상에서 제외하고 그대로 둔다.

---

## Step 0. 사전 확인 (사용자에게 1회 질문)

작업 시작 전 AskUserQuestion으로 다음을 확인한다:
1. **정리 방식**: (a) 하위폴더 분리 + 중복 제거 (b) 중복만 제거 (c) 분리 + 폴더명 변경까지
2. **폴더명 변경 여부**: `[종목명] (티커)` 규칙 적용 여부

> 파일을 휴지통으로 옮기는 단계는 되돌리기 어려우므로 **반드시 명시적 동의**를 받는다.

---

## Step 1. 대상 폴더 탐색 (Google Drive MCP)

```
search_files: title contains '[종목명]' and mimeType = 'application/vnd.google-apps.folder'
→ 폴더 id 확보
search_files: parentId = '[폴더 id]'   (pageSize 100)
→ 폴더 내 전체 파일 목록(id, title, mimeType) 확보
```

결과가 커서 토큰 한도를 넘으면 저장된 파일을 `jq`로 파싱:
```
jq -r '.files[] | [.id, .mimeType, .title] | @tsv' <saved.txt>
```

목록을 분류 규칙에 따라 `IR/`·`리서치/`·`중복(제거)`·`애매`로 라벨링한다.

---

## Step 2. 하위폴더 생성 (Google Drive MCP — 안정적)

이동/삭제 기능은 Drive MCP에 없지만 **폴더 생성과 복사는 가능**하다.

```
create_file: title='IR',   contentMimeType='application/vnd.google-apps.folder', parentId='[폴더 id]'
create_file: title='리서치', contentMimeType='application/vnd.google-apps.folder', parentId='[폴더 id]'
→ 각 하위폴더 id 확보
```

---

## Step 3. 파일 분류 — "복사 후 원본 휴지통" 방식

Drive MCP에는 move/update/delete 도구가 없다. 따라서:

### 3-1. 하위폴더로 복사 (Google Drive MCP)
중복으로 판정한 파일은 **복사하지 않는다.** 나머지 각 파일에 대해:
```
copy_file: fileId='[원본 id]', parentId='[대상 하위폴더 id]', title='[원본과 동일한 정식 파일명]'
```
- 여러 파일은 한 메시지에서 병렬 호출로 처리하면 빠르다.
- 복사가 모두 성공했는지 응답으로 확인한다(파일 누락 시 원본 삭제 금지).

### 3-2. 원본 일괄 휴지통 이동 (Claude in Chrome)
복사 검증 후, 최상단에 남은 원본 + 중복 파일을 휴지통으로 옮긴다.
```
1. list_connected_browsers → AskUserQuestion으로 브라우저 선택 → select_browser
2. navigate → https://drive.google.com/drive/folders/[폴더 id]
3. 목록 보기(리스트 뷰)에서 폴더(상단)는 제외하고 파일만 선택:
   - 첫 파일 left_click → 마지막 파일 shift+left_click (연속 범위)
   - 선택에서 빠진 파일은 ctrl+left_click 으로 추가
   - 상단 "N개 선택됨" 카운트로 파일 수가 정확한지 확인
4. 툴바 휴지통 아이콘 클릭 → "휴지통으로 이동" 확인 버튼 클릭
```
> ⚠️ Ctrl+A는 하위폴더(IR/리서치)까지 선택하므로 쓰지 말 것. 파일만 범위 선택한다.
> 휴지통 이동은 30일간 복구 가능하므로 안전하지만, 실행 전 화면을 스크린샷으로 검증한다.

---

## Step 4. 폴더명 변경 (Claude in Chrome) — 선택 시

```
1. 폴더 안에서 상단 breadcrumb의 '[현재 폴더명] ▾' 드롭다운 클릭
2. 메뉴에서 '이름 바꾸기' 클릭
3. ctrl+a 로 기존 이름 전체 선택 → 새 이름 타이핑 → '확인'
```
- 새 이름 규칙: `[정식 종목명] (티커)`  예) `RF머트리얼즈 (327260)`
- 폴더명에 오타가 있던 경우(예: '머터리얼즈'→'머트리얼즈') 정식 표기로 교정한다.
- 폴더명은 한국어 또는 영어만 사용(일본어 표기 금지).

---

## Step 5. 검증 (Google Drive MCP)

```
search_files: parentId='[IR 폴더 id]'     → IR 파일 수·목록 확인
search_files: parentId='[리서치 폴더 id]'  → 리서치 파일 수·목록 확인
search_files: parentId='[종목 폴더 id]'    → 최상단에 하위폴더 2개만 남았는지 확인
get_file_metadata: [종목 폴더 id]          → 변경된 폴더명 확인
```

원본 수 = (IR 복사본 수) + (리서치 복사본 수) + (중복 제거 수) 가 맞는지 대조한다.

---

## Step 6. 결과 보고

```
## 폴더 정리 결과: [종목명] ([티커])
- 폴더명: [변경 전] → [변경 후]
- IR/: N개 (목록)
- 리서치/: M개 (목록)
- 제거(휴지통): K개 (중복/원본)
- 드라이브 링크: [종목 폴더 URL]
```

---

## 주의사항 / 트러블슈팅

- **휴지통 이동 = 명시적 허가 필수.** 사용자 동의 없이 삭제/이동하지 않는다.
- **복사 검증 우선.** copy_file 응답을 모두 확인하기 전에는 원본을 삭제하지 않는다(데이터 손실 방지).
- **DART/공시 PDF 직접 다운로드는 자동화 차단됨.** 새 IR 자료를 추가할 때 DART의 `pdf.do`는
  XHR/fetch에 빈 응답(Content-Length 0)을 주므로 프로그램 다운로드가 안 된다. 이 경우
  뷰어 링크(`/dsaf001/main.do?rcpNo=...`)를 `IR/`에 링크 노트(Google 문서)로 정리해 제공한다.
- **Drive MCP에는 이동/이름변경/삭제 도구가 없다.** 생성·복사는 MCP, 이동(휴지통)·이름변경은 Chrome UI로 처리.
- **선택 시 폴더 오선택 주의.** 리스트 뷰에서 폴더는 상단에 모이므로 파일만 범위 선택.
- **종목 폴더가 여러 개 검색될 때** 사용자에게 정확한 폴더를 확인한다.
