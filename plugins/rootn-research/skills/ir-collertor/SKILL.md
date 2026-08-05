---
name: ir-collertor
version: 260721
description: "IR 자료 수집 스킬 - 주식 종목명 또는 티커를 입력하면 최근 2년간의 IR(Investor Relations) 자료를 공식 IR 페이지와 공시 사이트(DART, SEC EDGAR, EDINET, CNINFO)에서 검색하여 수집하고, 구글 드라이브의 'Investment Research' 폴더 아래에 [종목명]/IR 구조로 정리해주는 스킬입니다. 이 스킬은 종목 리서치, IR 자료 수집, 투자자료 정리, 기업 공시 자료 모음, 어닝콜 자료, 사업보고서, Annual Report, Quarterly Report, 10-K, 10-Q, 유가증권보고서, 반기보고서, 분기보고서, 결산설명회 자료 등의 수집에 사용하세요. 한국(DART/KRX), 미국(SEC EDGAR), 일본(EDINET/TDnet), 중국(CNINFO/SSE/SZSE) 종목을 지원합니다. 사용자가 '티커', '종목', 'IR', '투자자료', '공시', '어닝콜', '실적발표' 등을 언급하면 이 스킬을 사용하세요."
---

# IR 자료 수집 스킬 (IR Collector)

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.

 
종목명 또는 티커를 받아 최근 2년간의 IR 자료를 검색·수집하고 구글 드라이브에 정리하는 워크플로우.
 
## 핵심 원칙
 
한국 금융 사이트(DART, KIND, IR페이지 등)와 해외 공시 사이트(SEC EDGAR 등)는
WebFetch로 직접 접근이 차단되는 경우가 많다. 따라서 **반드시 Claude in Chrome 브라우저를
주요 접근 수단으로 사용**하고, WebSearch는 URL/링크 발견용으로만 활용한다.
 
---
 
## Step 1: 종목 정보 확인
 
WebSearch로 종목 기본 정보를 파악한다:
 
1. **정식 회사명** (한글/영문 모두)
2. **티커/종목코드**
3. **상장 시장** (KRX, NYSE, NASDAQ, TSE, SSE, SZSE 등)
4. **국가** → 검색 전략 결정
 
국가 판별:
- 한국명 또는 6자리 숫자 → KRX (한국)
- 영문 1~5자 대문자 → NYSE/NASDAQ (미국)
- 4자리 숫자 → TSE (일본)
- 그 외 → 사용자에게 확인
 
---
 
## Step 2: IR 자료 검색 (3단계 전략)
 
### 2-1. WebSearch로 링크 수집
 
WebSearch를 **병렬로 여러 쿼리** 실행하여 최대한 많은 자료 링크를 한 번에 수집한다:
 
```
병렬 검색 쿼리 (한국 종목 예시):
1. "[회사명] investor relations PDF 실적"
2. "[회사명] [종목코드] site:dart.fss.or.kr 사업보고서"
3. "[회사명] [종목코드] site:kind.krx.co.kr"
4. "[회사명] 어닝콜 실적발표 프레젠테이션 PDF"
5. "[회사명] [종목코드] 증권사 리포트 PDF"
 
미국 종목 예시:
1. "[company] investor relations SEC filings"
2. "[ticker] site:sec.gov 10-K 10-Q"
3. "[company] earnings presentation PDF"
4. "[company] annual report investor day"
```
 
검색 결과에서 수집할 것:
- 공시 문서의 KIND/DART 직접 링크 (acptno 포함)
- IR 페이지 URL
- 증권사 리포트 PDF 직접 링크
- SEC EDGAR 파일링 링크
 
### 2-2. Claude in Chrome으로 공시 사이트 접근
 
WebSearch에서 찾은 공시 링크가 부족하면, Chrome 브라우저로 공시 사이트에 직접 접속한다.
 
**한국 (DART):**
```
Chrome navigate → https://dart.fss.or.kr/dsab001/main.do
1. 회사명 검색창에 종목명 입력
2. 검색 실행
3. read_page로 공시 목록 확인
4. 사업보고서, 반기보고서, 분기보고서 등 링크 수집
```
 
**한국 (KIND):**
```
Chrome navigate → https://kind.krx.co.kr
1. 종목명으로 검색
2. 공시 목록에서 정기보고서, IR자료 링크 수집
```
 
**미국 (SEC EDGAR):**
```
Chrome navigate → https://efts.sec.gov/LATEST/search-index?q="[company]"&dateRange=custom&startdt=[1년전]&enddt=[오늘]&forms=10-K,10-Q,8-K
또는 → https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=[company]&type=10-K&dateb=&owner=include&count=40
```
 
**일본 (EDINET/TDnet):**
```
Chrome navigate → https://disclosure2.edinet-fsa.go.jp
또는 TDnet → https://www.release.tdnet.info/inbs/I_main_00.html
```
 
### 2-3. 공식 IR 페이지 접근
 
WebSearch에서 찾은 공식 IR 페이지 URL로 Chrome 접속:
```
Chrome navigate → [회사 IR 페이지 URL]
read_page로 자료 목록 확인
PDF/PPT/Excel 다운로드 링크 수집
```

### 2-4. 라이브러리 전수 체크리스트 (필수)

**핵심 원칙: 절대 "최근 분기 실적자료 몇 개"나 "이미 세션에서 확보한 URL"만으로 끝내지 않는다.** 반드시 공식 IR 라이브러리 인덱스 페이지를 직접 열어 **전체 자산을 열거한 뒤**, 이미 가진 것만 스킵한다. 열거를 건너뛰고 바로 다운로드로 넘어가는 것은 이 스킬의 실패 모드다.

종목마다 아래 항목을 **있는지/없는지 명시적으로 확인**한다. 없으면 `없음(확인)`으로 기록한다 — 빈칸이나 무언(無言) 금지.

| # | 항목 | 범위 |
|---|------|------|
| 1 | 결산설명자료 | 전 분기 2년 |
| 2 | 결산단신 / Earnings Release | 전 분기 2년 |
| 3 | 어닝콜 Transcript | 있으면 전량 |
| 4 | **★ 데이터북 / Financial Data (Excel·XLSX·CSV) ★** | 전 분기 2년 — **반드시 별도 탐색** |
| 5 | 유가증권보고서 / 반기보고서 또는 10-K / 10-Q | 최근 2년 |
| 6 | 통합보고서 / Annual Report | 최근 2년 |
| 7 | Factsheet / Investor Presentation / IR Day | 있으면 전량 |
| 8 | ESG / Sustainability 데이터 | 별도 xlsx·CSV 있으면 수집 |

**4번(데이터북)은 실적자료 목록과 다른 페이지에 있는 것이 정상이다.** 실적자료 PDF 목록에 없다고 "데이터북 없음"으로 넘어가지 말고 별도로 찾는다. (검증 사례: Recruit는 분기별 `Recruit_YYYYMMQx_financialdata_{en,ja}.xlsx`를 제공)

**경로 주의:**
- 회사가 광고하는 `/ir/library/` 가 404이고 실제 인덱스가 `/ir/financials/` 등 다른 경로에 있는 경우가 흔하다. **404가 떠도 "라이브러리 없음"으로 포기하지 말고 실경로를 찾는다.** (sitemap, IR 톱페이지 글로벌 내비게이션, `site:{도메인} 決算/financial data` 검색으로 역추적)
- **일본 종목은 EN 라이브러리와 JP 라이브러리가 서로 다른 자산을 가질 수 있다. 반드시 둘 다 확인한다.** 한쪽에만 있는 Excel·Transcript가 흔하다.

이 체크리스트 결과(수집 / 미확보 / 없음(확인))를 **Step 5 결과 보고 표에 그대로 반영**한다.

---
 
## Step 3: 자료 다운로드
 
수집한 링크들에 대해 다운로드를 시도한다. 로컬 저장 경로: `/sessions/[session-id]/ir-downloads/[종목명]/`
 
### 다운로드 우선순위
 
1. **Chrome 브라우저 다운로드** (가장 신뢰도 높음)
   - Chrome에서 PDF/PPT/Excel 링크를 직접 navigate하여 다운로드
   - 다운로드된 파일은 `~/Downloads/` 디렉토리에서 확인 후 작업 폴더로 이동
 
2. **same-origin `fetch → blob`** (공통 규칙 §9 — curl/wget보다 우선)
   - 페이지 컨텍스트에서 javascript_tool로 fetch 후 blob 저장. curl/wget은 차단이 잦아 보조로만.
   <!-- TODO(260710): collection-mechanics 참고문서(로컬 최신본에만 존재) 원문 미확보 — 공통 규칙 §9로 갈음. 원문 확보 시 references 폴더에 추가. -->
   - 주의: 이 방법은 WebFetch와 같은 제한이 적용될 수 있음
   - 직접 PDF 링크(예: 증권사 리포트 PDF)에 대해서만 시도
 
3. **다운로드 불가 시 → 링크 수집**
   - 로그인 필요, CAPTCHA, 동적 페이지 등으로 다운로드 불가한 경우
   - `ir_links.txt` 파일에 링크와 설명을 정리
 
### 파일명 규칙
```
[YYYY-MM-DD]_[자료유형]_[설명].[확장자]
예: 2025-03-20_사업보고서_2024년_결산.pdf
예: 2025-10-01_애널리스트리포트_메리츠증권.pdf
예: 2025-08-14_반기보고서_2025년_상반기.pdf
```
 
### 수집 대상 자료 유형 (우선순위)
1. 사업보고서 / Annual Report / 10-K
2. 분기/반기 보고서 / 10-Q
3. 실적발표 프레젠테이션 (Earnings Presentation)
4. 어닝콜 스크립트/녹취록
5. IR Day / 기업설명회(NDR) 자료
6. 주주총회 자료 (Proxy Statement)
7. Factsheet / Databook
8. 증권사 애널리스트 리포트 (PDF 직접 링크가 있는 경우)
 
---

### 3-4. 비PDF 파일 형식 확인 (중요)

PDF 외에도 다음 형식의 파일들을 반드시 확인하고 함께 수집한다:

**공식 IR 페이지 확인 대상:**
- CSV / ZIP (재무제표 데이터, 예: `財務諸表CSV_FY202403.zip`)
- Excel (.xlsx, .xls) — 결산 보충 데이터
- PowerPoint (.pptx, .ppt) — 설명회 자료

**IRBank (일본 종목, `f.irbank.net/files/[종목코드]/`):**
- 연간/분기 재무 CSV 파일 (fy-data-all.csv, fy-balance-sheet.csv 등)
- 다운로드: `curl -L "https://f.irbank.net/files/[종목코드]/fy-data-all.csv" -o fy-data-all.csv`
- rate-limit(429) 오류 발생 시 해당 파일은 건너뛰고 계속 진행

**EDINET (일본 종목):**
- XBRL/ZIP 형식 공시 패키지 — API 구독 키 필요, 없으면 수집 불가로 기록

**원칙:** IR 페이지를 탐색할 때 PDF 목록뿐 아니라 비PDF 다운로드 링크도 함께 확인할 것.

**★ 데이터북 Excel은 별도로 찾는다 (최다 누락 항목) ★**

데이터북 / Financial Data 성격의 Excel은 **실적자료(결산설명자료·Earnings Release)와 별도 URL·별도 페이지에 걸려 있는 경우가 많다.** 실적자료 PDF 목록을 훑었다고 해서 데이터북을 확인한 것이 아니다. §2-4 체크리스트 4번은 반드시 **독립된 탐색 액션**으로 수행한다.

전형적인 배치 위치 (전부 확인):
- IR 톱페이지(`/ir.html`)의 IR News / 최신 릴리스 피드 — `[XLS]` 아이콘으로 인라인 첨부
- `presentation.html` / 결산자료 페이지의 첨부 아이콘
- `/ir/financials/`, `/ir/data/`, `/ir/library/` 등 별도 재무데이터 인덱스
- EN 페이지와 JP 페이지 각각 (일본 종목은 한쪽에만 있는 경우 흔함)

href에 확장자가 없고 아이콘이 이미지·의사요소로 렌더되는 경우가 있으므로, `a[href$=".xlsx"]` 가 0건이면 `a[href*="xls"], a[href*="excel"], a[href*="financialdata"], a[href*="supplement"]` 로 한 번 더 훑는다. 그래도 0건일 때만 `없음(확인)`으로 기록한다.

검증 사례: Recruit는 분기별 `Recruit_YYYYMMQx_financialdata_{en,ja}.xlsx`, Sansan은 `Supplemental Financial Data for Qx FYxxxx.xlsx` 를 실적 PDF와 다른 경로로 제공.

---
 
## Step 4: 구글 드라이브 폴더 생성 및 업로드
 
### 4-1. 폴더 구조 생성 (Chrome 사용)
 
Chrome으로 `drive.google.com`에 접속하여 폴더를 만든다.
 
**폴더 생성 방법 (Google Drive UI):**
1. `drive.google.com/drive/u/0/my-drive`로 navigate
2. screenshot으로 현재 상태 확인
3. `+ 신규` 버튼 클릭 (좌측 상단, 좌표로 클릭)
4. 첫 번째 클릭에서는 메뉴가 안 보일 수 있음 → **두 번 클릭** 필요
5. 드롭다운 메뉴에서 `새 폴더` 클릭
6. 폴더명 입력 후 `만들기` 클릭
 
**생성할 폴더 구조:**
```
내 드라이브/
└── Investment Research/          ← 없으면 생성
    └── [종목명] ([종목코드])/      ← 예: 삼성전자 (005930)
        └── IR/                    ← 자료 저장 위치
```
 
> ⚠️ **폴더명 규칙 (중요)**: 구글 드라이브 폴더명은 반드시 **영어 또는 한국어**로 작성한다. 일본어(히라가나/가타카나/한자) 폴더명은 사용 금지.
> - ✅ 올바른 예: `Nomura Micro Science (6254)` 또는 `노무라마이크로사이언스 (6254)`
> - ❌ 잘못된 예: `野村マイクロ・サイエンス (6254)` (일본어 사용 금지)
> - 일본 종목이라도 영문 공식명 또는 한국어 표기를 사용할 것

각 폴더를 생성한 뒤 더블클릭으로 진입하여 하위 폴더를 만든다.
 
### 4-2. 파일 업로드
 
Google Drive의 네이티브 파일 선택 대화상자는 자동화가 제한적이다. 아래 우선순위로 시도한다.
 
**방법 D: Drive API 업로더 `drive_uploader.py` (신규·최우선 권장)**
```
전제: 사용자 로컬(또는 Cowork에 연결된 폴더)에 drive_uploader.py + credentials.json + token.json
      이 있어야 한다. 최초 1회 OAuth 인가(py drive_uploader.py --auth-only)로 token.json 생성 후
      재사용하면 브라우저 없이 동작. 셋업 절차: scripts/SETUP_Drive_API_uploader.md (스크립트 scripts/drive_uploader.py 동봉).
1. 대상 Drive 폴더 ID 확보(폴더 URL의 /folders/ 뒤 문자열).
2. 실행: py drive_uploader.py --folder <FOLDER_ID> [--name-suffix _v2] <파일들...>
   (클라우드/헤드리스는 python3 로 실행. token.json 있으면 무인 동작.)
3. 출력의 size [OK] md5 [OK] 로 3점 검증. FAIL이면 --name-suffix 로 재업로드.
- 장점: 대용량(수 MB) OK, base64 인라인 한계·네이티브 피커 문제 없음, md5 무손실 검증.
- 참고: Drive 커넥터 create_file 은 소용량(≲50KB)만 인라인 base64로 가능하며 fileSize 대조 필수.
```
 
**방법 A: Chrome 드래그 & 드롭 시뮬레이션** (⚠️ Google Drive에는 부적합)
```
Google Drive 웹은 업로드를 OS 네이티브 파일 피커로 처리하고, 자동화 가능한 <input type=file>을
DOM에 노출하지 않는다(신규 메뉴를 열고 DOM 조회해도 input[type=file] 0건). 따라서 file_upload
도구로는 Drive 업로드가 성립하지 않는다 → 방법 D를 사용한다.
(HTML file input을 실제로 노출하는 일반 웹앱에서만 file_upload 가 유효.)
```
 
**방법 B: ir_links.txt를 직접 생성** (파일 업로드 실패 시)
```
1. IR 폴더 안에서 신규 > Google 문서 생성
2. 수집한 링크 목록을 문서에 입력
3. 문서 제목을 "IR 자료 링크 모음 - [종목명]"으로 설정
```
 
**방법 C: 로컬 출력 + 안내** (최종 폴백)
```
1. ir_links.txt 파일을 /sessions/[session-id]/mnt/outputs/에 저장
2. 구글 드라이브 IR 폴더 URL을 사용자에게 전달
3. 사용자가 직접 파일을 드래그하여 업로드하도록 안내
```
 
---
 
## Step 5: 결과 보고
 
작업 완료 후 사용자에게 간결하게 보고:
 
```
## IR 자료 수집 결과: [종목명] ([티커])
 
### 라이브러리 전수 체크리스트 (§2-4)
| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1 | 결산설명자료 (2년) | 수집 / 미확보 / 없음(확인) | |
| 2 | 결산단신·Earnings Release | | |
| 3 | 어닝콜 Transcript | | |
| 4 | **데이터북 / Financial Data (Excel)** | | 별도 탐색 수행 여부 명시 |
| 5 | 유가증권보고서·반기보고서 / 10-K·10-Q | | |
| 6 | 통합보고서 / Annual Report | | |
| 7 | Factsheet / Investor Presentation / IR Day | | |
| 8 | ESG·Sustainability 데이터 | | |
> 8개 항목 전부 상태를 채운다. 빈칸 금지. `미확보`는 사유(로그인·404·차단 등)와 링크를 아래 표에 개별 기재.

### 수집 완료된 자료
| # | 자료명 | 유형 | 날짜 | 파일형식 |
|---|--------|------|------|----------|
| 1 | ... | ... | ... | PDF |
 
### 다운로드 불가 (링크 제공)
| # | 자료명 | 링크 | 사유 |
|---|--------|------|------|
| 1 | ... | [링크] | 로그인 필요 |
 
### 구글 드라이브 저장 위치
Investment Research > [종목명] ([티커]) > IR
[드라이브 폴더 직접 링크]
```
 
---
 
## 주의사항
 
- 검색 기간: **최근 2년** (현재 날짜 기준, 공통 규칙 §6)
- 파일 다운로드·드라이브 업로드는 묻지 않고 자동 진행한다(공통 규칙 §2). 되돌릴 수 없는 작업만 사전 확인.
- CAPTCHA/로봇 차단 시 무리하게 우회하지 않고 링크만 제공
- 구글 드라이브 접근 시 사용자가 Chrome에서 로그인 상태여야 함
- 여러 종목은 순차 처리 (종목별로 Step 1~5 반복)
 
## 트러블슈팅
 
- **WebFetch 차단됨**: Chrome 브라우저로 직접 접속. 대부분의 한국 금융 사이트(DART, KIND 등)는 WebFetch가 차단되므로 항상 Chrome 우선 사용
- **Chrome 연결 안 됨**: "Multiple Chrome extensions" 에러 시 사용자에게 Chrome 확장 프로그램 연결 확인 요청
- **구글 드라이브 신규 버튼 안 열림**: `+ 신규` 버튼을 **2번 연속 클릭** (첫 번째는 포커스, 두 번째에 메뉴 오픈)
- **파일 업로드 불가**: 방법 D(drive_uploader.py)를 최우선 시도. 그다음 방법 B(Google 문서)·C(로컬 저장 + 안내)로 전환
- **종목 국가 판별 불가**: 사용자에게 직접 확인