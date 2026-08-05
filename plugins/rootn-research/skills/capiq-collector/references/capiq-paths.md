# capiq-paths.md — CapIQ 실측 경로·동작·entitlement·커버리지

> 파일럿: 1차 2026-07-22 KST (bbg PC), 2차 2026-07-22 KST (메인 PC desktop-1u1d5ea).
> Claude in Chrome(Browser 1)으로 조작. 아래는 2차 세션 갱신 반영본.

## 0. 환경 / 로그인
- URL capitaliq.spglobal.com → /web/client?auth=inherit 세션 상속 로그인(Chrome 기 로그인 전제, 별도 입력 없음).
- 제품: S&P Capital IQ Pro. 계정 표시명 "Young Hwa Mo".
- **다운로드 위치(메인 PC)**: `C:\Users\user\Desktop\Claude (drive 연동)\다운로드`.
  Chrome이 OS 저장창 없이 이 폴더로 스트리밍 저장. device bridge로 컨테이너 마운트(`mnt/다운로드`).
- 쿠키 배너: "모두 거부"(ref로 클릭).

### ★ 렌더러 대응 — 핵심 우회법(2차 신규 확정)
- CIQ Pro SPA가 무거워 **CDP 스크린샷(Page.captureScreenshot)이 30초 타임아웃으로 거의 항상 실패**.
  프리즈 시 섹션 URL 재navigate로 리셋해도 스크린샷은 계속 실패할 수 있음.
- **해결: 스크린샷 대신 `read_page`(접근성 트리)를 1차 도구로 사용.** transcript 표·estimates 필터·
  버튼이 모두 ref로 잡힘 → `computer left_click {ref}` 로 조작. iframe 표도 read_page엔 노출됨
  (get_page_text/find는 여전히 iframe 표 텍스트 약함, read_page는 OK).
- **다운로드 성공 검증도 스크린샷 불필요**: `device_bash`로 `ls mnt/다운로드/ | grep -i <종목>` (또는 `ls -lat | head`).
  device_list_dir 전량 덤프보다 device_bash grep이 토큰 효율 높음.
- 다운로드는 한 건씩(클릭 → 5초 대기 → 폴더 grep 확인 → 다음). 배치 금지.

## 1. 검색 → tearsheet / MI KEY
- **상단 Search는 자동화 입력 불가**(§9 참조). MI KEY는 `references/capiq-mikey-registry.md` 캐시로 해석 —
  미스면 사용자가 CapIQ URL(`id=`) 1회 제공 → 캐시 append(이후 입력 0).
- tearsheet /company/profile?id=<MI_KEY>.
- Kioxia: TSE:285A, MI KEY 14356784, SPCIQ 605626628. Sansan: TSE:4443, MI KEY 5184024, SPCIQ 78816020.
  (전체 캐시는 registry 파일이 SSOT.)
- 좌측 페이지 메뉴가 직접 URL 링크로 노출(read_page): transcripts / detailedEstimates(ID 대문자) / profile / investmentresearch.

## 2. Transcripts(2년) — 동작 재확정
- URL /web/client#company/transcripts?id=<MI_KEY>. 기본 필터 Date Range=Last 2 Years, Type=All(그대로 OK).
- **각 이벤트 행에 최대 6개 제공자 버전**(2차 신규 확정):
  S&P Global: ENG / ENG-TRANSL / JPN, SCRIPTS Asia: JPN / ENG-TRANSL / ENG. 각 PDF/WORD/MP3.
  - `read_page filter=interactive`는 행 요약만(SCRIPTS Asia JPN+ENG-TRANSL 정도) → **해당 gridcell ref를
    `read_page ref_id=<cell> filter=all`로 읽으면 6버전 라벨이 모두 보임.** 원하는 라벨의 WORD ref 클릭.
  - 어닝콜 표준: **SCRIPTS Asia: ENG-TRANSL WORD**(기존 업로드분과 일관). 스페셜콜은 ENG 단일본 WORD.
- 다운로드 파일명(CIQ 자동): `<Company>_<EventType>_<YYYY-MM-DD>_<Language>.docx`
  (ENG-TRANSL·ENG → `_English.docx`, JPN → `_Japanese.docx`).
  ※ 같은 표시일 이벤트라도 소스 기준일로 파일명이 갈릴 수 있음
    (예: Sansan 스페셜콜 표시 2025-10-30 2건 → 파일명 `2025-10-30` / `2025-10-29`, 충돌 없음).

### 2차 수집 실적
- Kioxia 285A 어닝콜 2025-05-15 ENG-TRANSL WORD 재수집 성공: 243,993 B (1차 미생성분 복구).
  (기존 IR/transcripts에 5건 이미 존재·중복 없음: Investor Day 2026-06-02, EC 2026-05-15/02-12/2025-11-13/08-08.)
- Sansan 4443 transcript 전건(7): 어닝콜 ENG-TRANSL WORD 5건(2026-07-14 365KB, 2026-04-10 352KB,
  2026-01-15 360KB, 2025-10-10 145KB, 2025-07-15 399KB) + 스페셜콜 ENG WORD 2건
  (2025-10-30 136KB, 2025-10-29 128KB). 중소형인데 영문번역 커버 양호(설계 '중소형 공백' 재확인·해소).

## 3. 셀사이드(Investment & Market Research) — 미변경(1차 기록 유효)
- URL /company/investmentresearch?id=<MI_KEY>&type=1. 기본 Date Range=Last 30 Days → Filters에서 Last 2 Years → Apply.
- 행 클릭=REPORT DETAILS 모달(다운로드 아님). Wright 등 "Synopsis View only"=전문 미권한.
- Kioxia entitlement: Quant IP, Wright, S&P Global Ratings, Third Bridge, Aequitas (전통 증권사 주식리서치 원문 없음).
- 2차에서는 미착수(우선순위/시간). 전문 권한 문서만 문서별 모달 확인 후 다운로드.

## 4. Estimates — Detailed Estimates export(2026 한정) + Estimate Highlights(forward 해법)
- URL /company/detailedEstimates?ID=<MI_KEY> (**ID 대문자**). 하위: Estimate Highlights/Consensus/Detailed/
  Recent Changes/Guidance/Surprise/Trends/Revisions.
- **Export 동작 확정(2차, 렌더러 안정 시 성공)**: 우상단 `Export` 버튼 → `Export to Excel as Data`.
  다운로드 파일명 `SPGlobal_<CompanyName(일문 포함)>_DetailedEstimates_<DD-Mon-YYYY>.xlsx` (~19–31KB).
  ※ 파일명에 일본어 회사명 포함 → **업로드 시 ASCII로 개명** 필요.
- 표 구성: Consensus Estimates(Mean/Median/High/Low/StdDev/#Est/Actual, 회계·통화) + Broker Estimates(브로커별).
  Kioxia 브로커 Arete/China Renaissance/Daiwa/Morningstar(+Not Entitled**), IFRS.
  Sansan 브로커 Ichiyoshi/Tokai Tokyo(+Not Entitled**), Japanese GAAP.
- **★ 미해결: Period Range 향후연도 확장이 export에 반영 안 됨.**
  From/To 연도는 커스텀 위젯 `select.snl-listbox-multi`(id `section_1_control_28`/`_29`).
  - `form_input`으로 <select>.value=2029 설정돼도(“previous 2026→2029” 응답) Apply/Export는 무시하고 **2026-2026으로 리셋**.
  - 오버레이 옵션 클릭도 <select>.value 미변경. 결과 export는 현재/직전 회계연도(FY2026) 상세만 담고
    forward FY2027–2029 컬럼이 통째로 없음(브로커별 200행 모두 2026 기준).
  - **정밀 확정(3차 시도)**: JS로 `<select>` value에 native setter+`change` 이벤트 주입 → **Apply 시 라이브 표는
    forward(FQ1 2027·FY2027)까지 넓어짐**. 그러나 **Export는 여전히 2026-2026을 서버에서 받아** 무시(파일 byte 동일).
    즉 export는 커스텀 위젯의 커밋 상태를 읽고, 자동화로는 그 커밋을 못 바꿈. → **Detailed Estimates export로 forward 확장 불가.**
- **★ forward 컨센서스 해법 = `Estimate Highlights` 하위탭**(URL /company/estimateHighlights?ID=<MI_KEY>):
  이 페이지는 **FY+1~FY+3(예: FY2027/2028/2029)을 기본 노출**(Target Price 블록 + EPS-by-FY + Multiples NTM/차년FY).
  - 단 **이 페이지의 `Export to Excel as Data`는 파일 미생성**(2회). + 렌더러 프리즈 잦고 find/read가
    "page still loading"으로 막힘(지속 폴링) → **JS가 유일하게 동작**.
  - **채택 방법 = JS 스크랩**: `document.body.innerText`(‘Target Price’ 이후 슬라이스) 또는 `table tr` 순회로
    표를 긁어 컨테이너에서 xlsx 생성(신뢰도=화면 스크랩/반). 2차 실적: Sansan EPS FY27 0.45E/FY28 0.61E/FY29 0.79E,
    TP mean 12.66·8명; Kioxia TP mean 716.52·16명·Outperform·LT growth 43.17% + Multiples(NTM/2027FY),
    단 Kioxia EPS 표는 "No data matches your settings"로 미표시(통화/설정 이슈, 추후 설정 조정 필요).
  - Detailed Estimates export(2026 브로커별 상세)와 Estimate Highlights 스크랩(forward)은 **상보적** — 둘 다 보관.

## 5. 컨테이너/로컬 → Google Drive 업로드 — ★해결(방법 확정)
- **함정**: Chrome 기본 다운로드 폴더 `...\Claude (drive 연동)\다운로드`는 리서치 계정
  Drive로 **싱크되지 않음**(새/기존 파일 모두 title 검색 불검출; 타 계정 싱크 또는 미러 대상 아님 추정).
  연결 폴더에 `drive_uploader.py`/`credentials.json`/`token.json` 없어 방법 D도 즉시 불가.
- **해결(2차 확정)**: 실제 Drive for Desktop 미러 = `C:\Users\user\Desktop\Drive` (device mount `mnt/Drive`).
  이 폴더에 넣은 파일은 **~30초 내** 리서치 계정 Drive에 반영(title 검색 검출, size 일치 확인).
- **표준 업로드 절차(무-base64, create_file 금지 준수)**:
  1) CIQ 다운로드분을 `device_bash`로 `mnt/Drive/_capiq_intake_<date>/`에 `cp`
     (xlsx는 일본어 파일명 → **ASCII로 개명**해서 cp: `Kioxia_285A_capiq_DetailedEstimates_YYYYMMDD.xlsx` 등).
  2) ~30초 대기 후 Google Drive MCP `search_files title=`로 각 파일 fileId 확보(싱크 반영 검증 = 업로드 검증).
  3) `copy_file(fileId, parentId=캐논폴더, **title=원하는 이름**)`로 캐논 위치에 배치.
     ★ **title 반드시 지정** — 생략 시 "Copy of ..." 접두사가 붙어 기존 clean 파일과 불일치·중복 유발.
  4) intake 원본은 아카이브로 두거나 사용자 확인 후 정리.
- **캐논 folderId(2차 확정/신설)**:
  - Investment Research = 1o2kvIP7Aj2Ezcv13zPhZgnjc-VpM2jvr
  - Kioxia (285A) = 1u0q2dH6SK10RZSmTHCfpiOIwnhDyG9TU
    · IR/transcripts = 153iqxzw4kdM-PqXyhIDelzbcm23BYbCp (기존)
    · 리서치 = 1Ir53EB1IzOnheAsCT3xFoLh5xncOTY73 (신설) > consensus = 1lcFFWQCEzLjiUSHD4fU94gCxGMlTc0pI
  - Sansan = 1yzi5uB3udhVvCHatcQz9X7-oomp1YDul
    · IR = 11tfO9CUJpyaAxIeR6t-ZDbkwS_N7-Ka2 > transcripts = 1wHr4RQfEQiwPcyu0XYvnqbYFDUuaZVCR (신설)
    · 리서치 = 1LwgrrzwI5SgFwFg7-EJeHd3g8ouLjKsk > consensus = 19bB6lOXaLSuAXh64N3ufofL4Jnmsy4oy (신설)
    · Sell-side = 1LaYVAsCKh7HVPONhv5O1jyhrOhYpScLi (기존)

## 6. 셀사이드(Investment & Market Research) — 2차 실측
- URL /company/investmentresearch?id=<MI_KEY>&type=1. Date Range 기본이 Last 2 Years로 잡혀 있기도 함(확인).
- 목록은 JS `table tr` 순회로 안정적으로 스크랩 가능(read_page는 파일명 라벨 약함).
- **다운로드 게이트(재확인)**: 행의 `pdf` 링크 클릭 = 다운로드 아님(Report Details 모달). 체크박스 선택도
  자동화(클릭·JS)로 등록 안 됨 → PDF 미생성. **자동 원문 다운로드 불가**, 사용자 수동 필요. Wright 등 Synopsis-only.
- **커버리지 실측**: Kioxia = 전통 증권사 equity 리서치 **없음**(Quant IP 월간 특허·Wright·S&P Ratings 신용·
  Third Bridge 전문가네트워크·Aequitas placement·Smart Insider만). Sansan = **실제 equity 리서치 있음**
  (Ichiyoshi Research/Hiroshi Naya 英日, Tokai Tokyo Intelligence Lab; 총 86건). → 목록 인벤토리 md로 대체 산출.

## 7. Drive 삭제/정리 — 도구 한계(중요)
- **Google Drive MCP에 삭제/휴지통/이동/이름변경 API 없음**(copy_file·create_file·search만).
- **device_bash는 마운트 파일 rm 불가**, mv도 다른 마운트로 옮기면 원본 remove 단계에서 "Operation not permitted".
  → 컨테이너/브리지로는 Drive·미러 파일 **삭제 불가**.
- 결론: 중복/오생성 파일 삭제는 **Drive 웹 UI(브라우저)만** 가능(단 CIQ 아닌 Drive라도 가상화 리스트·줌으로 오삭제 위험).
  안전책: 애초에 copy_file에 title 지정해 "Copy of" 중복을 만들지 말 것(§5). 생기면 사용자에게 수동 휴지통 목록으로 인계.

## 8. 함정 요약
- 스크린샷 신뢰 금지 → read_page/ device_bash 검증. Estimate Highlights 등 폴링 페이지는 JS만 동작.
- Detailed Estimates export는 forward 확장 불가 → forward는 Estimate Highlights JS 스크랩(§4).
- Chrome 기본 다운로드폴더 ≠ Drive 미러(§5). 실제 미러 `C:\Users\user\Desktop\Drive` 사용.
- `copy_file`는 title 미지정 시 "Copy of" 접두사 → 반드시 title 지정(§5). 삭제 도구 없음(§7).
- 프리즈 시 섹션 URL 재navigate.

## 9. 신규 수집 섹션 — route·방법 (3차 실측, Kioxia 14356784 / Sansan 5184024)
- **섹션 맵**(좌측 네비): Profile(Corporate Profile·Stock·Corporate Structure·Officers·Analyst Coverage·
  Compensation·Advisers·Products & Services·Competitors·Valuation/Peer Comps) · Financials · Estimates ·
  Investment & Market Research · News/Events/Filings · Transactions · Business Relationships & Supply Chain ·
  Investments · Sustainability · Ownership · Corporate Issuance · Report Builder.
- **route 규칙**: Profile 계열은 `<a href>`로 노출(id 소문자), 그 외 그룹은 라우터 onClick(href 없음) →
  네비로 route 추출 안 됨, 직접 URL 필요. `#company/<route>?ID=`(대문자) 또는 `?id=`(소문자) 혼용.
- **확정 route**: profile(id) · estimateHighlights(ID) · detailedEstimates(ID) · transcripts(id) ·
  investmentresearch(id,&type=1) · peerAnalyticsMain(id) · PublicOwnershipDetailed(ID) ·
  PublicOwnershipSummaryHistory/OwnershipSummary/OwnershipHistory · corporateStructure(Id) · analystCoverage(ID) ·
  products · competitors · incomeStatement(ID)=**CreditStats Direct** · corporateCompensation(Id).
- **★ CapIQ export 신뢰도(실측)**: Detailed Estimates=파일 O. **Estimate Highlights·Peer Comps="Export to Excel as Data"
  클릭해도 브라우저 다운로드 X**(서버 큐 추정). → 신규 섹션은 **JS 스크랩** 우선.
- **Ownership Detailed 수집법(✓검증)**: `PublicOwnershipDetailed?ID=`. 데이터가 실제 `<table>`.
  프로즌(이름) 테이블 index 1 + 스크롤(지표) 테이블 index 4를 **row index로 조인**.
  지표 컬럼 순서: [0]shares [1]%O/S [2]MktValue($M) [3]Chg(shares) [4]Chg% [5]FilingDate ... [14]Country [15]Style [17]HolderType.
  → 컨테이너서 xlsx. Sansan 실측: 창업자 Terada 32.5%·Ichigo(액티비스트) 11.6%·Wellington·Greenoaks(VC/PE)·Vanguard·Nomura·BlackRock.
- **Estimate Highlights 수집법(✓검증, §4)**: innerText('Target Price' 이후 슬라이스) 스크랩 → forward FY+1~+3.
- **Peer Comps(✗)**: `peerAnalyticsMain?id=` — 데이터가 커스텀 그리드(비-`<table>`), export도 미다운로드 → 자동 수집 비신뢰(수동).
- **Financials(✗)**: incomeStatement가 CreditStats Direct(iframe), Kioxia 데이터·export 미노출 → Bloomberg BEst·EDINET로 대체.
- **★ Search 위젯 → MI KEY 자동해석(✗ 심층조사 결론, 4차)**: 상단 Search·검색결과 모두 자동화 거부.
  - UI 입력: `computer type`·JS native setter 모두 값 주입 즉시 리셋(`input.value`가 동일 tick에 ''로 복귀) → typeahead XHR 미발생.
  - 백엔드: omni-search는 **gRPC-web**(`/apisv3/spg-search/*` 전 경로가 GET에 `application/grpc` 반환). REST/JSON 검색 엔드포인트 부재
    (`spg-webplatform-core/*/search`류는 SPA HTML fallback). gRPC 메서드 경로·protobuf 스키마 미상 → 자동 재현 불가.
  - 소스 확보 불가: top-search MFE(`cdn.spgi.spglobal.com/spg/search/top-search/...`) JS는 **CORS로 fetch 본문 판독 차단**(전부 ERR).
  - 앱 함수: `topSearch`는 module-federation 로더(검색 아님), `omniSearchRequestor`는 Dojo declare 난독화(호출 메서드 미노출).
  - 티커 라우트: `#company/profile?referenceIdentifier=TSE:1812` **미해석**(빈 프로필).
  - **결론**: 순수 zero-input 해석기 불가 → **`references/capiq-mikey-registry.md` 캐시**로 대체.
    신규 종목만 사용자가 CapIQ URL(`id=` 포함) 1회 제공 → 캐시 append → 이후 입력 0. (수집기 §2-1 프로토콜)
  - 미래 후보(미검증): Screener 그리드 API·Report Builder 엔티티 피커(REST 여지) — 필요 시 조사.
- **route 추가 확정(4차, Sansan 5184024 좌측 네비 `<a href>` 실측)**: corporateStructure(Id) · analystCoverage(ID) ·
  committeeMembership · professionals · products. → analystCoverage·corporateStructure는 route 확정, `<table>` 스크랩 유력.
- **미검증(table 스크랩 가능성 높음, 요청 시 확인)**: keyDevelopments · Business Relationships/Supply Chain ·
  Transactions · Corporate Issuance. 실행 시 `<table>` 유무 확인 후 스크랩(없으면 스킵·기록).
