---
name: jp-research-collector
version: 260722
description: "일본 주식 종목 리서치 자료 자동 수집 스킬. 종목명 또는 4자리 종목코드를 입력하면 Kabutan(株探), Minkabu(みんかぶ), 株予報Pro(IFIS)에서 컨센서스·애널리스트 정보를 스크래핑하고, 공식 IR 페이지에서 결산설명자료 PDF를 curl로 다운로드하고, Shared Research에서 Full Report를 다운로드하여 로컬 폴더에 종목명_티커_YYMM 구조로 정리하는 스킬입니다. '일본 종목 리서치', '일본주 자료 수집', '日本株リサーチ', 'JP 리서치', '일본 IR 자료', '일본 결산설명회', '일본 애널리스트', '일본 컨센서스', 'Kabutan', 'Minkabu', '株探', 'Shared Research', 'ログミー', '일본 어닝콜', '일본 실적발표 자료', '일본 종목 분석 자료 모으기', '일본 주식 리포트 수집' 등의 키워드가 나오면 이 스킬을 사용하세요. 일본 4자리 종목코드(예: 6758, 7203)나 일본 회사명(예: 소니, 토요타)이 언급되면서 리서치·자료·리포트·IR 등의 맥락이 있으면 이 스킬을 적극 활용하세요."
---

# 일본 주식 리서치 자료 자동 수집 (JP Research Collector)

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.

 
일본 상장 종목의 리서치 자료를 여러 소스에서 자동으로 수집하여 로컬 폴더에 정리하는 워크플로우.
 
## 핵심 원칙
 
일본 금융 사이트들은 WebFetch로 직접 접근이 차단되는 경우가 많다. **Claude in Chrome 브라우저를 주요 접근 수단으로 사용**하고, WebSearch는 URL 발견과 보조 검색에만 활용한다. 각 사이트마다 로그인 여부, 동적 로딩, PDF 다운로드 방식이 다르므로, 사이트별로 정해진 접근 전략을 따른다.
 
수집 기간은 **최근 2년**이며, 가능한 한 많은 자료를 다운로드하되, 로그인·CAPTCHA 등으로 접근 불가한 자료는 링크만 수집하여 사용자에게 안내한다.

### 수집 우선순위 (효율성 기반)

실전 테스트 결과, 아래 순서로 자료 수집 효율이 높다:

1. **Kabutan 재무 데이터** — `get_page_text`로 100% 수집 가능, 가장 풍부한 재무 데이터
2. **Kabuyoho 컨센서스** — `get_page_text`로 100% 수집 가능
3. **Minkabu 컨센서스** — `get_page_text`로 100% 수집 가능
4. **공식 IR 페이지 PDF** — `curl`로 직접 다운로드 가능 (irpocket.com, eir-parts.net 호스팅)  ★가장 중요한 PDF 소스
5. **Shared Research** — 로그인 필요하지만 기관급 리포트 (커버리지 약 250개사)
6. **CapIQ transcripts·셀사이드·estimates** — Chrome에 CapIQ 로그인 상태일 때. transcript 1차 소스,
   Shared Research 공백(250개사 외) 보완, BEst 덤프 없을 때 컨센 1차 소스 (`capiq-collector` 호출)
7. **ログミーFinance** — 커버리지 제한적, 중소형주는 대부분 없음 (CapIQ transcript 없을 때 fallback)
8. **FISCO** — 무료 리포트가 거의 없음, 수율 매우 낮음 (선택사항)

> **컨센서스 소스 위계 (§5-3 설계)**: BEst 덤프(1차, bbg-sync 인제스트분) > CapIQ estimates
> export(검증·차선) > Kabuyoho/Minkabu(보조·fallback) > Toyo Keizai(커버리지 0 중소형, 신뢰도 중).
> **Kabutan actual은 항상 수집**한다. 월차(月次) 데이터는 회사 IR·Kabutan 유지.
 
---
 
## Step 0: 사전 준비
 
### 저장 폴더 확인
 
사용자의 workspace 폴더(Cowork에서 마운트된 폴더, 또는 `/sessions/.../mnt/outputs/`)에 접근할 수 있는지 확인한다.
 
사용자가 특정 경로를 지정한 경우(예: `C:\Users\user\Desktop\Claude`) 해당 경로가 마운트되어 있는지 확인하고, 안 되어 있으면 `request_cowork_directory` 도구로 폴더 마운트를 요청한다.

**기본 저장 전략**: 먼저 `/sessions/.../mnt/outputs/`에서 작업하고, 완료 후 사용자 지정 경로로 일괄 복사한다. 이렇게 하면 중간에 문제가 생겨도 작업물이 보존된다.
 
### 폴더 생성
 
저장 경로에 다음 형식의 폴더를 생성한다:
 
```
{종목명}_{종목코드}_{YYMM}/
```
 
예: `ソニーグループ_6758_2603/` (2026년 3월 수집)
 
이 폴더 안에 수집한 모든 파일을 저장한다. 여러 종목 수집 시 마지막에 `전체_수집_요약_{YYMM}.txt`도 루트에 생성한다.
 
---
 
## Step 1: 종목 정보 확인
 
WebSearch로 기본 정보를 파악한다:
 
1. **정식 회사명** (일본어 및 영문)
2. **종목코드** (4자리 숫자)
3. **상장 시장** (東証プライム / スタンダード / グロース 등)
4. **섹터/업종**
5. **공식 IR 페이지 URL**
 
종목코드가 4자리 숫자이면 일본 주식으로 판별한다. 사용자가 한국어 회사명(예: "소니", "토요타")을 입력한 경우, 일본어 정식명과 종목코드를 매칭한다.
 
---
 
## Step 2: 컨센서스 · 애널리스트 정보 스크래핑
 
아래 3개 사이트에서 컨센서스 정보를 수집한다. 각 사이트의 페이지를 Chrome으로 열고, 페이지 내용을 읽어서 주요 데이터를 텍스트 파일로 정리한다.

> **효율 팁 (실전 검증, TOWA 6315)**: Kabutan(`stock/finance?code=`)·Kabuyoho(`sp/reportAnalyst?bcode=`)는 클라우드 `curl -sL -A "Mozilla/5.0"`로 200 응답하는 경우가 많다. **먼저 curl로 HTML을 받아 파싱하면 브라우저 탭 없이 훨씬 빠르다** — 재무 테이블은 `pandas.read_html`, 컨센 텍스트는 태그 제거로 추출. 403/차단이면 그때 Chrome으로 폴백한다. **Minkabu(`/analyst_consensus`)는 curl 403이 잦아 Chrome이 필요**하다.
 
### 2-1. 株予報Pro (kabuyoho.jp) — 컨센서스 예상
 
IFIS(아이피스)가 운영하는 애널리스트 컨센서스 데이터 소스. Yahoo Finance Japan의 애널리스트 리포트 서비스가 2022년에 종료된 이후, 일본 주식의 컨센서스 정보를 가장 체계적으로 제공한다.
 
```
Chrome navigate → https://kabuyoho.jp/sp/reportAnalyst?bcode={종목코드}
```
 
수집할 정보:
- 애널리스트 수, 레이팅 분포 (강력매수/매수/중립/매도)
- 목표주가 평균·최고·최저
- EPS/매출 컨센서스 예상 (현재 기·다음 기)
- 컨센서스 변동 추이
 
`read_page` 또는 `get_page_text`로 페이지 내용을 읽고, 주요 데이터를 `consensus_kabuyoho.txt`로 저장한다.
 
### 2-2. Minkabu (minkabu.jp) — 애널리스트 컨센서스
 
```
Chrome navigate → https://minkabu.jp/stock/{종목코드}/analyst_consensus
```
 
수집할 정보:
- 증권사별 목표주가, 레이팅
- 컨센서스 평균 목표주가
- 개인 투자자 예상 vs 프로 예상 비교
 
`consensus_minkabu.txt`로 저장한다.
 
### 2-3. Kabutan (kabutan.jp) — 재무 데이터 (★ 가장 풍부한 데이터)
 
Kabutan의 finance 페이지는 `get_page_text`로 한 번에 방대한 재무 데이터를 추출할 수 있다. 기본 페이지를 거치지 않고 **직접 finance 페이지로 이동**하는 것이 효율적이다.
 
```
Chrome navigate → https://kabutan.jp/stock/finance?code={종목코드}
```
 
`get_page_text`로 추출 가능한 데이터:
- **통기 실적** (최근 4~5년): 매출, 영업익, 경상익, 순이익, EPS, 배당
- **업적수정 이력**: 초기예상 → 수정 → 실적 (상향/하향 방향 포함)
- **수익성 지표**: 영업이익률, ROE, ROA, 총자산회전율
- **캐시플로우**: 영업CF, 투자CF, 재무CF, FreeCF, 현금잔고
- **분기별 실적** (최근 8분기): 3개월 단위 매출·이익·마진
- **3분기 누적**: 통기 진척률 확인 가능
- **재무 상태(BS)**: BPS, 자기자본비율, 총자산, 유이자부채배율
- **과거최고 실적**: 항목별 최고치와 해당 결산기
 
추출한 데이터를 `financials_kabutan.txt`에 구조화하여 저장한다. **특기사항**(상향수정 횟수, 과거최고 여부, 특이 분기 등)도 파일 하단에 코멘트로 추가한다.

> **팁**: Kabutan 페이지의 JavaScript 경고("JavaScriptが無効になっています")는 무시해도 된다. `get_page_text`로 데이터 테이블 내용은 정상 추출된다.

### 2-4. CapIQ estimates export — BEst 덤프 없을 때 컨센 1차 소스

Drive `Model/`에 BEst 덤프(`*_bbg_*.xlsx`)가 없고 Chrome에 CapIQ 로그인 상태면,
`capiq-collector` §2-4 절차로 Estimates(Consensus Detail·Revisions·Segment)를 **Excel
export**로 받는다 → `리서치/consensus/`. Kabuyoho/Minkabu 평균값보다 깊은
(애널리스트 수·high/low/mean·revisions·세그먼트 추정) 데이터를 확보할 수 있다.
CapIQ 미가용이면 기존 2-1~2-2(Kabuyoho/Minkabu)가 컨센 소스가 된다.
 
---
 
## Step 3: 공식 IR 페이지 PDF 다운로드 (★ 핵심 단계)
 
### 3-1. 공식 IR 페이지에서 결산설명자료 PDF 수집

**이 단계가 PDF 자료 수집의 핵심이다.** 대부분의 일본 상장사는 공식 IR 페이지에서 결산설명자료를 PDF로 제공하며, PDF 호스팅은 주로 `irpocket.com` 또는 `eir-parts.net`을 사용한다. 이 PDF들은 `curl`로 직접 다운로드 가능하다.

**공식 IR 페이지 찾기:**

```
WebSearch → "{회사명} 決算説明会資料 site:{공식도메인}"
WebSearch → "{회사명} IR 決算説明 投資家情報"
```

일반적인 IR 페이지 URL 패턴:
- `https://www.{company}.co.jp/ir/briefing/` — 결산설명회 자료
- `https://www.{company}.co.jp/ir/library/` — IR 라이브러리
- `https://www.{company}.co.jp/ir/result/` — 결산단신

**PDF 링크 일괄 추출 (JavaScript 활용):**

Chrome으로 IR 페이지에 접속한 후, `javascript_tool`로 모든 PDF 링크를 한 번에 추출한다:

```javascript
const links = document.querySelectorAll('a[href$=".pdf"]');
const results = [];
links.forEach(l => {
  const parent = l.closest('li') || l.closest('tr') || l.parentElement;
  const text = parent ? parent.textContent.trim().substring(0, 120) : l.textContent.trim();
  results.push({ href: l.href, text: text });
});
JSON.stringify(results);
```

eir-parts.net 호스팅인 경우 (Nomura Micro Science 등):
```javascript
const links = document.querySelectorAll('a[href*="eir-parts.net"]');
const urls = [];
links.forEach(l => urls.push(l.href));
JSON.stringify([...new Set(urls)]);
```

**curl로 PDF 다운로드 (Bash):**

```bash
cd /sessions/.../mnt/outputs/{종목폴더}/
curl -sL -o "ir_presentation_YYYY-MM_설명.pdf" "{PDF_URL}"
file ir_presentation_YYYY-MM_설명.pdf  # PDF 유효성 확인
```

주요 PDF 호스팅 도메인 (curl 다운로드 가능 확인됨):
- `pdf.irpocket.com` — 오르가노 등 다수 기업 사용
- `ssl4.eir-parts.net` — 노무라마이크로 등 사용
- `finance-frontend-pc-dist.west.edge.storage-yahoo.jp` — Yahoo Finance 경유 공시

**수집 대상 자료 (최근 2년):**
- 결산설명회자료 (決算説明会資料) — 매 반기/통기마다
- 결산보충자료 (決算補足資料) — 매 분기
- 질의응답 요약 (質疑応答要旨) — 있으면 반드시 수집 (투자 인사이트 풍부)
- 결산단신 (決算短信) — 최신 1~2개만
- **Supplemental Financial Data (Excel) — 매 분기.** 결산설명 라이브러리(`/ir/library/`, `/ir/briefing/`) 하위가 아니라 **IR 톱페이지(`/ir.html`)의 IR News 피드나 `presentation.html`에 `[XLS]` 아이콘으로 걸려 있는 경우가 많다.** 라이브러리 목록만 보고 "Excel 없음"이라 단정하지 말고, 톱페이지 뉴스 피드·presentation 페이지의 첨부 아이콘까지 확인한다. (검증 사례: Sansan은 분기별 `Supplemental Financial Data for Qx FYxxxx.xlsx`를 톱페이지 피드로 제공)

**XLS/CSV 링크 추출 (위 PDF 추출과 별도로 톱페이지·presentation 페이지에서 반드시 1회 실행):**

```javascript
const links = document.querySelectorAll('a[href$=".xlsx"], a[href$=".xls"], a[href$=".csv"], a[href$=".zip"]');
const results = [];
links.forEach(l => {
  const parent = l.closest('li') || l.closest('tr') || l.parentElement;
  results.push({ href: l.href, text: parent ? parent.textContent.trim().substring(0, 120) : l.textContent.trim() });
});
JSON.stringify(results);
```

아이콘이 이미지·의사요소로 렌더되어 확장자가 href에 없을 수 있다. 위 셀렉터가 0건이면 `a[href*="xls"], a[href*="excel"], a[href*="supplement"]` 로 한 번 더 훑고, 그래도 0건이면 "Excel 없음"으로 기록한다.

**파일명 규칙:**
```
ir_presentation_YYYY-MM_FYxxxx_설명.pdf
ir_qa_YYYY-MM_FYxxxx_질의응답.pdf
ir_supplement_YYYY-MM_FYxxxx_보충자료.pdf
ir_tanshin_YYYY-MM_FYxxxx.pdf
ir_supplemental_data_YYYY-MM_FYxxxxQx.xlsx
```

### 3-2. CapIQ transcripts — transcript 1차 소스 (Chrome 가용 시)

Chrome에 CapIQ 로그인 상태면 `capiq-collector` §2-2 절차로 earnings call transcripts
최근 2년치(Q&A 포함)를 다운로드한다 → `IR/transcripts/`. ログミー가 커버하지 못하는
중소형·B2B 종목도 CapIQ에는 있는 경우가 많다.
- CapIQ에 없으면: §3-1의 질의응답 PDF(質疑応答) → §3-3 ログミー 순으로 fallback.
- 이미 확보한 분기는 재수집하지 않는다.

### 3-3. ログミーFinance (finance.logmi.jp) — 결산설명회 서면 기록 (CapIQ 없을 때 fallback)
 
> **실전 결과**: ログミーFinance 커버리지는 대형주·인기주에 편중되어 있다. 중소형주·B2B 기업은 최근 2년 transcript가 없는 경우가 대부분이다. **공식 IR PDF 확보를 우선하고, 시간이 남으면 시도**한다.

```
WebSearch → "{회사명} site:finance.logmi.jp 決算説明会"
```
 
최근 2년치 결산설명회 기사가 있으면:
1. 각 기사의 URL을 수집
2. Chrome으로 열어 `get_page_text`로 전체 텍스트를 추출
3. `transcript_YYYY_Q{n}.txt` 형식으로 저장

> **주의**: `get_page_text`가 타임아웃(45초)되면 `read_page`를 대신 사용한다.
 
---
 
## Step 4: 리서치 리포트 수집
 
### 4-1. Shared Research (sharedresearch.jp) — 기관급 분석 리포트
 
Shared Research는 약 250개 일본 상장사에 대한 독립적인 기업 분석 리포트를 제공한다. 기관투자자급 품질이며, 무료 계정으로 열람·PDF 다운로드 가능하다.

**커버리지 확인:**
```
WebSearch → "{회사명} site:sharedresearch.jp"
```
결과에 `sharedresearch.jp/ja/companies/{종목코드}` URL이 있으면 커버리지에 포함.

**로그인 절차 (★ React 사이트이므로 특별한 처리 필요):**

1. Chrome에서 `https://sharedresearch.jp/ja/login` 으로 이동
2. `form_input`으로 이메일·비밀번호 입력
3. **반드시 React 호환 방식으로 값 설정** (일반 form_input만으로는 React state가 업데이트되지 않을 수 있음):

```javascript
const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value').set;
const emailInput = document.querySelector('input[placeholder="Eメール"]');
const pwInput = document.querySelector('input[type="password"]');

nativeInputValueSetter.call(emailInput, '{이메일}');
emailInput.dispatchEvent(new Event('input', { bubbles: true }));
emailInput.dispatchEvent(new Event('change', { bubbles: true }));

nativeInputValueSetter.call(pwInput, '{비밀번호}');
pwInput.dispatchEvent(new Event('input', { bubbles: true }));
pwInput.dispatchEvent(new Event('change', { bubbles: true }));

document.querySelector('button[type="submit"]').click();
```

4. 로그인 성공 시 `https://sharedresearch.jp/en/dashboard`로 리다이렉트됨
5. 실패 시 "メールアドレス／パスワードが無効" 에러 표시 → 사용자에게 비밀번호 확인 요청

**리포트 다운로드:**

1. `https://sharedresearch.jp/en/companies/{종목코드}` 로 이동
2. 페이지 우측 하단의 초록색 **"Download"** 버튼 클릭
3. "Your PDF is now ready and downloading" 확인 모달이 뜨면 성공
4. PDF는 **사용자의 브라우저 다운로드 폴더**에 저장됨 (sandbox가 아님)
5. 커버리지에 없는 종목은 skip

> **계정 정보**: Drive `Investment Research/_config/sender.txt` 참조(Shared Research 계정). **계정·비밀번호를 이 문서에 직접 기재하지 않는다.**
> 로그인 실패 시 사용자에게 비밀번호 변경 여부 확인 요청
 
### 4-2. CapIQ Aftermarket Research — Shared Research 공백 보완 (Chrome 가용 시)

Shared Research 커버리지(약 250개사) 밖 종목이거나 리포트가 오래됐으면, Chrome에 CapIQ
로그인 상태에서 `capiq-collector` §2-3 절차로 Aftermarket Research 브로커 PDF
(entitlement 범위)를 수집한다 → `리서치/`. 잠긴 리포트는 제목·브로커·날짜만 기록.

### 4-3. FISCO (fisco.jp) — 기업조사 리포트 (선택사항, 수율 낮음)

> **실전 결과**: FISCO 무료 리포트는 FISCO가 IR 컨설팅 계약을 맺은 기업에만 존재한다. 일반 상장사의 무료 리포트를 찾기 매우 어렵다. **시간이 남을 때만 간단히 검색**하고, 없으면 빠르게 skip한다.
 
```
WebSearch → "{회사명} FISCO 企業調査レポート PDF"
```
 
결과에서 직접 PDF 링크가 있으면 다운로드, 없으면 즉시 다음으로 넘어간다.
 
---
 
## Step 5: 파일 다운로드 및 정리
 
### 다운로드 방법 (우선순위)
 
1. **Bash curl** (★최우선): `irpocket.com`, `eir-parts.net`, `storage-yahoo.jp` 호스팅 PDF는 curl로 직접 다운로드 가능. 가장 효율적이고 안정적.
   ```bash
   curl -sL -o "파일명.pdf" "PDF_URL"
   file 파일명.pdf  # 유효성 확인 (196 bytes 등 극소 파일은 실패)
   ```
2. **Chrome 브라우저 다운로드**: Shared Research 등 로그인 필요 사이트. 다운로드된 파일은 사용자의 로컬 Downloads 폴더에 저장됨 (sandbox 아님).
3. **텍스트 추출 저장**: Chrome `get_page_text`로 페이지 내용을 `.txt`로 저장. (Kabutan 재무, 컨센서스 등)
4. **링크 수집**: 위 방법 모두 불가 시 `수집불가_링크모음.txt`에 URL·설명·접근불가 사유를 정리.

> **중요**: curl로 다운받은 PDF는 반드시 `file` 명령으로 확인한다. 200 bytes 미만이면 HTML 리다이렉트 응답일 가능성이 높으므로 다른 URL을 시도한다.
 
### 파일명 규칙
 
```
[자료유형]_[YYYY-MM]_[FY정보]_[설명].[확장자]
```
 
실전 검증된 파일명 예시:
- `consensus_kabuyoho.txt` — 株予報Pro 컨센서스 데이터
- `consensus_minkabu.txt` — Minkabu 컨센서스 데이터
- `financials_kabutan.txt` — Kabutan 재무 데이터 (통기+분기+CF+BS)
- `ir_presentation_2025-11_FY2026_1H説明会.pdf` — 결산설명회자료
- `ir_presentation_2025-05_FY2025決算.pdf` — 통기 결산설명회자료
- `ir_qa_2025-05_FY2025質疑応答.pdf` — Q&A 요약
- `ir_supplement_2026-02_FY2026_3Q.pdf` — 분기 보충자료
- `ir_tanshin_2026-02_FY2026_3Q.pdf` — 결산단신
- `ir_individual_investor_presentation.pdf` — 개인투자자 설명자료
- `수집_요약.txt` — 개별 종목 수집 요약
- `수집불가_링크모음.txt` — 다운로드 불가 자료의 링크 목록
 
### 최종 폴더 구조 (실전 예시)
 
```
オルガノ_6368_2604/                   ← 13개 파일
├── consensus_kabuyoho.txt
├── consensus_minkabu.txt
├── financials_kabutan.txt
├── ir_presentation_2024-05_FY2024決算説明会.pdf
├── ir_presentation_2024-11_FY2025_1H説明会.pdf
├── ir_presentation_2025-05_FY2025決算説明会.pdf
├── ir_presentation_2025-11_FY2026_1H説明会.pdf
├── ir_qa_2024-11_FY2025_1H質疑応答.pdf
├── ir_qa_2025-05_FY2025質疑応答.pdf
├── ir_qa_2025-11_FY2026_1H質疑応答.pdf
├── ir_individual_investor_presentation.pdf
├── ir_tanshin_2025-05_FY2025.pdf
├── ir_tanshin_2025-10_FY2026_2Q.pdf
└── 수집_요약.txt

전체_수집_요약_2604.txt               ← 여러 종목 수집 시 루트에 생성
```
 
---
 
## Step 6: 결과 보고
 
작업 완료 후 사용자에게 간결하게 보고한다:
 
```
## 일본 종목 리서치 자료 수집 결과: {종목명} ({종목코드})
 
### 컨센서스 요약
- 애널리스트 수: N명
- 평균 목표주가: ¥XX,XXX
- 컨센서스 레이팅: 매수/중립/매도
 
### 수집 완료된 자료
| # | 파일명 | 소스 | 유형 | 기간 |
|---|--------|------|------|------|
| 1 | ... | ログミー | Transcript | 2025 Q3 |
 
### 다운로드 불가 (링크 제공)
| # | 자료명 | 소스 | 링크 | 사유 |
|---|--------|------|------|------|
 
### 저장 위치
{폴더 경로}
```
 
`수집_요약.txt` 파일에도 동일한 내용을 저장하여 나중에 참조할 수 있도록 한다.
 
---
 
## 주의사항
 
- 수집 기간: **최근 2년** (현재 날짜 기준)
- CAPTCHA/로봇 차단 시 무리하게 우회하지 않고 링크만 제공
- Shared Research는 사용자가 Chrome에서 로그인 상태여야 리포트 접근 가능
- FISCO는 무료 공개분만 수집 (유료 리포트는 링크만 안내)
- 여러 종목은 순차 처리 (종목별로 Step 0~6 반복)
- 일본어·한국어·영어가 혼용될 수 있으므로 검색어를 다양하게 시도
 
## 트러블슈팅 (실전 경험 기반)
 
- **WebFetch 차단됨**: 일본 금융 사이트 대부분이 해당. Chrome 브라우저로 직접 접속.
- **Chrome 연결 안 됨**: "Multiple Chrome extensions" 에러 시 사용자에게 Chrome 확장 프로그램 연결 확인 요청.
- **ログミー 기사가 안 나옴**: 중소형주·B2B 기업은 대부분 커버 안 됨. 공식 IR 페이지의 결산설명자료 PDF로 대체. **이것이 정상이다.**
- **Shared Research 로그인 실패**: React 사이트이므로 일반 `form_input`만으로는 불충분. `javascript_tool`로 `nativeInputValueSetter` + `dispatchEvent`를 사용해야 함. 그래도 실패하면 비밀번호 변경 가능성 → 사용자에게 확인 요청.
- **Shared Research에 종목 없음**: 커버리지가 약 250개사로 제한적. 없으면 skip.
- **PDF 다운로드 파일이 너무 작음** (200 bytes 이하): HTML 리다이렉트 응답. 올바른 URL이 아님. JavaScript로 실제 PDF URL을 다시 추출하거나, 다른 URL 패턴을 시도.
- **Kabutan `get_page_text` 타임아웃**: 페이지가 무거울 경우 `read_page`를 대신 사용.
- **ログミーFinance 페이지 로딩 타임아웃** (45초): `get_page_text` 대신 `read_page`(filter: "all", depth: 5)를 사용.
- **종목코드로 검색 안 됨**: 일본어 정식 회사명으로 재검색 시도. 예: "노무라마이크로" → "野村マイクロ・サイエンス"
- **FISCO 리포트 없음**: 정상. 대부분의 종목에 무료 FISCO 리포트는 없다. 빠르게 skip.
- **공식 IR 사이트 도메인 불명**: WebSearch로 `"{회사명} IR 投資家情報"` 검색하여 정확한 도메인 확인. 예: 노무라마이크로는 `nomura-nms.co.jp` (nomura-ms.co.jp가 아님).
- **여러 종목 처리 시 효율**: 동일 소스(Kabuyoho → Minkabu → Kabutan)를 전 종목에 순차 처리한 후, IR PDF 다운로드를 별도 배치로 처리하면 Chrome 탭 전환이 줄어들어 효율적.

## 검증된 IR 사이트 도메인 목록

| 회사명 | 종목코드 | IR 도메인 | 결산설명자료 URL |
|-------|---------|----------|---------------|
| オルガノ | 6368 | organo.co.jp | /ir/briefing/ |
| 野村マイクロ | 6254 | nomura-nms.co.jp | /ir/library/investment-briefing.html |
| 栗田工業 | 6370 | kurita.co.jp | /ir/ |
| 大気社 | 1979 | taikisha.co.jp | /ir/ |
| 高砂熱学 | 1969 | tte-net.com | /ir/ |
| ＴＯＷＡ | 6315 | towajapan.co.jp | /jp/ir/library/ (서버렌더 — HTML을 curl로 받아 PDF·데이터북 링크 직접 추출 가능. 데이터북 = `*_briefing.xlsx`, PDF·xlsx 모두 클라우드 curl 다운로드됨) |