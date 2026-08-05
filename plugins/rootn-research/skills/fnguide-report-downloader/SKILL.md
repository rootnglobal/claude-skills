---
name: fnguide-report-downloader
version: 260721
description: "에프엔가이드(FnGuide) 증권사 애널리스트 리포트 다운로더 - 종목명 또는 종목코드를 입력하면 에프엔가이드 www.fnguide.com/Research/SearchReport 페이지에 접속하여 최근 2년간의 증권사 애널리스트 리포트 PDF를 모두 다운로드하는 스킬입니다. 사용자가 '에프엔가이드', 'FnGuide', '애널리스트 리포트', '컨센서스 리포트', '증권사 리포트', '종목 리포트 수집', '리서치 리포트 다운로드', '리포트 모아줘', '리서치 보고서' 등을 언급하면 이 스킬을 사용하세요. 종목코드(6자리 숫자, 예: 005930)와 종목명(예: 삼성전자) 모두 지원합니다. 에프엔가이드 유료 계정이 필요하며, Chrome에서 로그인된 상태여야 합니다."
---

# 에프엔가이드 애널리스트 리포트 다운로더

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


종목명 또는 종목코드를 받아 에프엔가이드 FnResearch에서 최근 2년간의 증권사 애널리스트 리포트 PDF를 일괄 다운로드하는 워크플로우.

이 스킬은 Claude in Chrome을 통해 `www.fnguide.com/Research/SearchReport` 페이지를 자동화한다.

> ⚠️ **핵심**: 올바른 URL은 `www.fnguide.com/Research/SearchReport` (FnResearch)이며, `comp.fnguide.com`이 아니다.

---

## 사전 요구사항

- **Chrome 브라우저**가 열려 있어야 함
- **에프엔가이드** 유료 계정으로 `www.fnguide.com`에 로그인된 상태
- Claude in Chrome 도구들(navigate, javascript_tool, computer, read_network_requests)에 대한 접근 권한

---

## 전체 워크플로우

### Step 1: 브라우저 연결 및 종목 확인

1. `list_connected_browsers`로 연결된 브라우저 목록 확인
2. 사용자에게 어느 브라우저를 사용할지 AskUserQuestion으로 확인
3. `select_browser`로 해당 브라우저 선택
4. `tabs_context_mcp`로 탭 ID 확인

종목명/종목코드 판별:
- 6자리 숫자 → 종목코드. WebSearch로 종목명 확인
- 한글 회사명 → WebSearch로 종목코드 확인

### Step 2: FnResearch 페이지 접속

```
URL: https://www.fnguide.com/Research/SearchReport
```

1. `navigate`로 위 URL 접속
2. 2~3초 대기
3. 로그인 확인: 로그인 메뉴가 보이면 로그인 안 된 상태 → 사용자에게 로그인 요청

### Step 3: 종목 검색

```javascript
// 검색창에 종목명 입력 (React controlled input이므로 nativeInputValueSetter 사용)
const input = document.querySelector('input[placeholder*="종목"]');
const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
nativeInputValueSetter.call(input, '종목명');
input.dispatchEvent(new Event('input', { bubbles: true }));
```

2초 대기 후 자동완성 드롭다운에서 해당 종목 클릭:
```javascript
// 자동완성에서 해당 종목 클릭 (computer 도구로 직접 클릭하거나 JS로)
// 자동완성 목록: 종목명/종목코드 섹션에서 종목명 클릭
```

또는 `computer` 도구로 자동완성 목록에서 직접 클릭한다.

2초 대기 후 검색 결과 확인: "종목: [종목명]에 대한 검색결과 N개" 메시지 확인.

### Step 4: 필터 설정

**기간 설정 (기본: 2년 — 공통 규칙 §6. 드롭다운에 '2년'이 없으므로 '직접입력'으로 시작일=오늘-2년을 지정한다. 직접입력 UI가 실패하면 '1년'으로 폴백하고 결과 보고에 '1년치만 수집'을 명시)**:
```javascript
// 기간 드롭다운 열기
const periodBtn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '3개월');
periodBtn.click();
// 1초 대기 후 1년 선택
const yearOpt = [...document.querySelectorAll('li')].find(el => el.textContent.trim() === '1년');
yearOpt.click();
```

2초 대기 후 결과 건수 확인.

**페이지당 개수 설정 (60개씩)**:
```javascript
// 개수 드롭다운 열기
const viewBtn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('15개씩 보기'));
viewBtn.click();
// 1초 대기 후 60개 선택
const opt60 = [...document.querySelectorAll('li')].find(el => el.textContent.trim() === '60개씩 보기');
opt60.click();
```

2초 대기.

### Step 5: 전체 rptId 수집

**다운로드 함수 정의** (먼저 실행):
```javascript
window.downloadPdf = async function(rptId, filename) {
  const res = await fetch('/ResearchPdf/GetPdfFile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rptId: String(rptId) })
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 3000);
  return blob.size;
};
```

**rptId 수집 함수**:
```javascript
function collectPage() {
  const rows = [...document.querySelectorAll('tbody tr')];
  return rows.map(row => {
    const link = row.querySelector('a[href*="/Research/PdfViewer"]');
    if (!link) return null;
    const rptId = link.getAttribute('href').split('=')[1];
    const title = link.textContent.trim().replace(/[\\/:*?"<>|]/g,'_').substring(0, 60);
    return { rptId, filename: `${종목명}_${rptId}_${title}.pdf` };
  }).filter(Boolean);
}

window._rptList = collectPage();
```

**페이지 수 확인**: 총 건수가 60건 초과이면 2페이지 이상 존재.

**2페이지 이동 및 추가 수집**:
```javascript
// 페이지 버튼은 class="pcol" 인 button/a 요소
const page2 = [...document.querySelectorAll('button, a')]
  .find(el => el.textContent.trim() === '2' && (el.className||'').includes('pcol'));
page2.click();
// 2초 대기 후
window._rptList.push(...collectPage());
```

필요시 3페이지 이상도 동일하게 반복.

사용자에게 보고: "[종목명] 2년치 리포트 **[N]건** 수집 완료. 다운로드를 시작합니다."

### Step 6: 일괄 PDF 다운로드

```javascript
window._downloadCount = 0;
window._downloadErrors = [];

async function runAllDownloads() {
  for (const item of window._rptList) {
    try {
      await window.downloadPdf(item.rptId, item.filename);
      window._downloadCount++;
      await new Promise(r => setTimeout(r, 800)); // 0.8초 간격 (서버 부하 방지)
    } catch(e) {
      window._downloadErrors.push(`${item.rptId}: ${e.message}`);
    }
  }
  window._downloadDone = true;
}
runAllDownloads();
```

진행 확인 (10~15초마다):
```javascript
`진행: ${window._downloadCount}/${window._rptList.length}건, 오류: ${window._downloadErrors.length}건, 완료: ${window._downloadDone||false}`
```

완료 기준: `window._downloadDone === true`

### Step 7: 결과 보고

완료 후 사용자에게 보고:

```
## 에프엔가이드 리포트 다운로드 완료: [종목명] ([종목코드])

- 수집 기간: 최근 2년
- 총 다운로드: [N]건
- 오류: [M]건
- 저장 위치: 브라우저 기본 다운로드 폴더
- 파일명 형식: [종목명]_[rptId]_[제목].pdf
```

---

## PDF 다운로드 메커니즘 (핵심 정보)

- **PDF 뷰어 URL**: `https://www.fnguide.com/Research/PdfViewer?rptId={ID}`
- **PDF 다운로드 API**: `POST https://www.fnguide.com/ResearchPdf/GetPdfFile`
  - Body: `{ "rptId": "1102568" }` (JSON)
  - 응답: PDF blob
- **rptId 위치**: 각 리포트 행의 `a[href*="/Research/PdfViewer"]` 링크에서 추출
- 인증은 세션 쿠키로 자동 처리됨 (로그인 상태면 별도 인증 불필요)

---

## 여러 종목 처리

여러 종목을 요청하는 경우 Step 2~7을 종목별로 순차 반복한다.

---

## 기간 커스터마이즈

기간 드롭다운 옵션: **1개월**, **3개월** (기본), **6개월**, **1년**, **직접입력**

- 기간 미지정 → 기본값 2년 (직접입력)
- "최근 6개월" → 6개월 선택
- 특정 날짜 범위 → 직접입력 선택 후 날짜 입력

---

## 트러블슈팅

- **검색 결과 0건**: 종목명이 정확하지 않음 → 자동완성 목록에서 정확한 종목명/코드 확인
- **다운로드 실패**: 세션 만료 가능성 → `www.fnguide.com`에서 로그인 재확인
- **자동완성 안 뜸**: `nativeInputValueSetter` 대신 `computer` 도구로 직접 클릭하여 입력
- **페이지 버튼 못 찾음**: `class="pcol"` 대신 숫자 텍스트로 버튼 탐색
- **blob 크기 0**: 해당 rptId의 리포트가 접근 불가(권한 문제) → 건너뛰고 계속 진행
