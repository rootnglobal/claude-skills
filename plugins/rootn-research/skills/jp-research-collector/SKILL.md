---
name: jp-research-collector
version: 261021
description: "일본 주식 종목 리서치 자료 자동 수집 스킬. 종목명 또는 4자리 종목코드를 입력하면 Kabutan(株探), Minkabu(みんかぶ), 株予報Pro(IFIS)에서 컨센서스·애널리스트 정보를 스크래핑하고, 회사사계보 온라인(四季報オンライン)에서 독자예상·기사를 수집하고, 공식 IR 페이지에서 결산설명자료 PDF를 curl로 다운로드하고, Shared Research Full Report와 IR Agents 취재노트(IR 1:1 인터뷰 Q&A), Kabu Berry·湘南投資勉強会 개인투자자 IR Q&A를 수집하여 로컬 폴더에 종목명_티커_YYMM 구조로 정리하는 스킬입니다. '일본 종목 리서치', '일본주 자료 수집', '日本株リサーチ', 'JP 리서치', '일본 IR 자료', '일본 결산설명회', '일본 애널리스트', '일본 컨센서스', 'Kabutan', 'Minkabu', '株探', 'Shared Research', 'ログミー', '四季報', '사계보', 'Toyo Keizai', 'IR Agents', '취재노트', 'Kabu Berry', '湘南投資勉強会', '일본 어닝콜', '일본 실적발표 자료', '일본 종목 분석 자료 모으기', '일본 주식 리포트 수집' 등의 키워드가 나오면 이 스킬을 사용하세요. 일본 4자리 종목코드(예: 6758, 7203)나 일본 회사명(예: 소니, 토요타)이 언급되면서 리서치·자료·리포트·IR 등의 맥락이 있으면 이 스킬을 적극 활용하세요."
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
5. **四季報オンライン (Toyo Keizai, ★구독 중)** — 전 상장사 커버. 독자예상·기자 코멘트·대주주.
   셀사이드 커버리지 0인 중소형주에서는 사실상 유일한 제3자 예상 (Step 2-5)
6. **Shared Research** — 로그인 필요하지만 기관급 리포트 (커버리지 약 250개사)
7. **CapIQ transcripts·셀사이드·estimates** — Chrome에 CapIQ 로그인 상태일 때. transcript 1차 소스,
   Shared Research 공백(250개사 외) 보완, BEst 덤프 없을 때 컨센 1차 소스 (`capiq-collector` 호출)
8. **IR Agents 취재노트** — 前애널리스트가 상장사 IR과 1:1 취재한 Q&A 노트. 중소형·저커버리지
   종목에서 IR 콜 대체재로 가치 높음. 무료 공개분 + (구독 시) 유료회원분 (Step 4-4)
9. **ログミーFinance** — 커버리지 제한적, 중소형주는 대부분 없음 (CapIQ transcript 없을 때 fallback)
10. **Kabu Berry Lab · 湘南投資勉強会** — 개인투자자 IR 세미나 Q&A·영상. 중소형주 위주, 무료 (Step 4-5)
11. **FISCO·Bridge Salon** — 무료 리포트가 거의 없음/얕음, 수율 낮음 (선택사항)
12. **カブヨミ (kabuyomi.jp)** — 有報(EDINET) AI 요약·17期 재무·32지표. 무료 범위만, 보조 (Step 2-6)

> **컨센서스 소스 위계 (§5-3 설계)**: BEst 덤프(1차, bbg-sync 인제스트분) > CapIQ estimates
> export(검증·차선) > Kabuyoho/Minkabu(보조·fallback) > **四季報 독자예상(구독 중 — 커버리지 0
> 중소형에서는 1차 소스로 승격, 신뢰도 중)**.
> **Kabutan actual은 항상 수집**한다. 월차(月次) 데이터는 회사 IR·Kabutan 유지.
>
> **취재·Q&A 소스 위계**: CapIQ transcript(원문) > 공식 IR 質疑応答 PDF > IR Agents 취재노트
> (회사 검수로 뉘앙스 완화 가능성, 대신 수치 신뢰도 높음) > ログミー(공식 설명회 전문) >
> Kabu Berry·湘南(회사가 비용 내는 공개 IR 행사 — 홍보 성격 감안, "신뢰도 중" 표기).
 
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

BEst 덤프(`*_bbg_*.xlsx`, 공통규칙 §2 위치)가 없고 Chrome에 CapIQ 로그인 상태면,
`capiq-collector` §2-4 절차로 Estimates(Consensus Detail·Revisions·Segment)를 **Excel
export**로 받는다 → `리서치/consensus/`. Kabuyoho/Minkabu 평균값보다 깊은
(애널리스트 수·high/low/mean·revisions·세그먼트 추정) 데이터를 확보할 수 있다.
CapIQ 미가용이면 기존 2-1~2-2(Kabuyoho/Minkabu)가 컨센 소스가 된다.

### 2-5. 四季報オンライン (shikiho.toyokeizai.net) — 독자예상·기자 코멘트 (★구독 중)

회사사계보 온라인. **전 상장사 커버**이므로 Kabuyoho/Minkabu에 애널리스트가 0명인
중소형주에서 특히 중요하다. 東洋経済 기자의 독자 업적예상(회사계획과 별도)과
정성 코멘트 2건(업황·재료)이 핵심.

```
로그인: https://id.toyokeizai.net/sol/  (Chrome)
종목 페이지: https://shikiho.toyokeizai.net/stocks/{종목코드}
```

> **계정 정보**: Drive `Investment Research/_config/toyokeizai_account.txt` 참조.
> **계정·비밀번호를 이 문서에 직접 기재하지 않는다.** 동시 로그인 제한이 있을 수
> 있으므로 로그인 실패 시 1회만 재시도하고 사용자에게 알린다.

수집할 정보 (`shikiho_{종목코드}.txt`로 저장):
- **四季報 독자예상** (최신호): 매출·영업익·순이익·EPS 예상 (당기·내기) — 회사계획과의 괴리 방향 명기
- **기자 코멘트 2건** (【】헤드라인 포함): 업황 판단·서프라이즈 재료
- 대주주 상위·외국인 지분율·특정주 비율
- 前号比 예상 수정 방향 (상향/하향 화살표), 会社比 강기/약기 마크
- 종목 관련 四季報オンライン 기사(속보·해설)가 있으면 제목·날짜·요지

수집 방법: Chrome `get_page_text` 우선. 로그인 상태에서만 전체 데이터가 보이므로,
값이 비어 있으면 로그인 세션을 먼저 확인한다. Chrome 미가용 세션(순수 클라우드)에서는
curl 로그인이 잘 안 되므로 **skip하고 "四季報 미수집(Chrome 미가용)"으로 flagging**한다.

### 2-6. カブヨミ (kabuyomi.jp) — 有報 AI 요약·장기 재무 (보조, 선택)

EDINET 유가증권보고서를 AI로 요약·가공해 보여주는 무료 중심 사이트.
`https://kabuyomi.jp/stock/{종목코드}`. 무료 범위: AI 요약(사업리스크·전년 변화·
동업비교), 주요 수치, 세그먼트 구성(예: 지역별 매출 비중), 図解 BS/PL.
유료(월 980엔): 10년 차트·전년 差分 등 — **구독하지 않고 무료 범위만 쓴다**.

- 시도 순서: curl 1회 → 403이면 Chrome `get_page_text` → 실패 시 즉시 skip
- 유용한 경우: 有報 원문을 읽기 전 사업구조·리스크 조감, 세그먼트 비중 빠른 확인
- **AI 가공물이므로 "신뢰도 중" 표기**, 수치는 반드시 Kabutan·有報 원문과 교차 확인
- 저장: 핵심 요지만 `kabuyomi_{종목코드}.txt` (다른 소스와 중복되는 수치는 생략)

**「この会社をnoteで読む」 섹션 (★반드시 확인):** kabuyomi 종목 페이지 하단에 해당
종목을 다룬 note.com 개별주 분석글 링크가 붙는다 (예: 밸류에이션 위화감 지적,
경쟁사 비교, 수요처 분석 등 심층글). 처리:
1. 링크 전부 수집 → 제목·작성자·날짜를 `kabuyomi_{종목코드}.txt`에 목록화
2. 투자 판단에 유용해 보이는 글(실적 드라이버·경쟁 구도·bull/bear 논점을 다루는 것)은
   열어서 무료 범위를 `get_page_text`로 수집 → `note_{작성자}_{YYYY-MM}.txt`
3. **유료 note 기사**(유료 라인 이후 잠김)는 무료 도입부로 논지를 파악하고, 가치 있어
   보이면 **결과 보고에 제목·작성자·가격·링크를 "note 유료 기사 구매 검토"로 표기**
   — 사용자가 승인하면 구매 진행(결제는 항상 사전 확인). 개인 작성 글이므로
   "신뢰도 낮음~중" 표기.

---
 
## Step 3: 공식 IR 페이지 PDF 다운로드 (★ 핵심 단계)
 
### 3-1. 공식 IR 페이지에서 결산설명자료 PDF 수집

**이 단계가 PDF 자료 수집의 핵심이다.** 대부분의 일본 상장사는 공식 IR 페이지에서 결산설명자료를 PDF로 제공하며, PDF 호스팅은 주로 `irpocket.com` 또는 `eir-parts.net`을 사용한다.

> **네트워크 전제 (매 세션 첫 1회만 확인)**: 클라우드 컨테이너의 egress 정책은 조직·계정마다 다르다.
> `curl -s -o /dev/null -w '%{http_code}' https://pdf.irpocket.com/` 로 1회 판별하고, `000`(CONNECT 403)이면
> **클라우드 curl·WebFetch 경로를 전부 포기하고 Chrome 단독으로 진행**한다. 같은 세션에서 재시도 금지.
> (2026-09 RootN 환경 실측: kabutan / kabuyoho / minkabu / 회사 IR 도메인 / pdf.irpocket.com / tdnet / edinet
> 전부 차단. 데스크톱 로컬 VM도 연결 폴더가 없으면 device_bash 사용 불가 → Chrome이 유일 경로.)

**공식 IR 페이지 찾기:**

```
WebSearch → "{회사명} 決算説明会資料 site:{공식도메인}"
WebSearch → "{회사명} IR 決算説明 投資家情報"
```

일반적인 IR 페이지 URL 패턴:
- `https://www.{company}.co.jp/ir/briefing/` — 결산설명회 자료
- `https://www.{company}.co.jp/ir/library/` — IR 라이브러리
- `https://www.{company}.co.jp/ir/result/` — 결산단신

**★결산설명회 페이지가 IR 라이브러리 하위에 없을 때 (흔함)**

회사에 따라 결산설명회 자료가 `library` 계열이 아니라 전혀 다른 경로에 있다.
(실측: NIPPON EXPRESS HD 9147 = `/ja/ir/event/data-room/`. IR資料室에는 決算短信·有報·統合報告書만 있고
설명회 자료는 "IRイベント" 하위에 들어 있었다.)
**IR 라이브러리 목록만 보고 "결산설명자료 없음"이라고 단정하지 말 것.** 아래 2단계로 찾는다.

1) **앵커 텍스트 스캔** — IR 톱·library·event 3개 페이지를 페이지 컨텍스트에서 `fetch`해 DOM 파싱하고,
   링크 텍스트에 설명회 계열 키워드가 있는 것만 뽑는다. 네비게이션만 보면 안 보이는 링크가 잡힌다.

```javascript
const urls = ['/ja/ir/', '/ja/ir/library/', '/ja/ir/event/'].map(p => location.origin + p);
const res = [];
for (const u of urls) {
  const h = await (await fetch(u)).text();
  const d = new DOMParser().parseFromString(h, 'text/html');
  [...d.querySelectorAll('a[href]')].forEach(a => {
    const t = a.textContent.replace(/\s+/g, ' ').trim();
    if (/説明|プレゼン|ファクト|補足|データ|決算/i.test(t))
      res.push(new URL(a.getAttribute('href'), u).href + ' | ' + t.slice(0, 60));
  });
}
JSON.stringify([...new Set(res)].slice(0, 60));
```

2) **후보 URL 일괄 HEAD 판별** — 1)로도 안 나오면 흔한 경로를 한 번에 때려본다 (탭 이동 없이 status만 확인).

```javascript
const base = location.origin + '/ja/ir/';
const cands = ['library/presentation/','library/briefing/','library/settlement/','event/data-room/',
               'finance/presentation/','library/financial/','library/factbook/','event/presentation/'];
const r = [];
for (const c of cands) { try { r.push(c + ' -> ' + (await fetch(base + c)).status); } catch(e) { r.push(c + ' -> ERR'); } }
JSON.stringify(r);
```

**PDF 링크 일괄 추출 (JavaScript 활용):**

Chrome으로 IR 페이지에 접속한 후, `javascript_tool`로 모든 PDF 링크를 한 번에 추출한다.

> **★필수 전처리**: 일본 IR 페이지는 연도별 아코디언(`<details>`)으로 과거 자료를 접어두는 경우가 매우 많다.
> 접힌 상태에서는 링크가 DOM에 있어도 누락되기 쉬우므로, **추출 전 반드시 모두 펼친다**:
> `document.querySelectorAll('details').forEach(d => d.open = true);`
> 펼치기 전후로 추출 건수를 비교해 차이가 크면 아코디언이 원인이다. (실측: NXHD 9147은 펼치기 전 0건 → 펼친 후 111건)

```javascript
document.querySelectorAll('details').forEach(d => d.open = true);
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

### 3-1b. ★월차 매출·물량 KPI 페이지 (선행지표 — 반드시 확인)

결산설명 자료만 받고 끝내지 말 것. 상당수 일본 기업이 **월차(月次) 데이터를 IR 사이트에 상설 공개**하며,
이것이 growth delta 판정의 1차 선행지표가 된다. `peer-momentum-screener` / `jp-earnings-quality-screen`가
그대로 소비하는 입력이므로 수집 단계에서 확보해 둔다.

확인할 경로 (IR 톱의 "財務・業績" 또는 "月次" 계열 하위):
- `/ir/finance/monthly/` — 월차 매출고 (사업부문별 전년동월비). 통상 PDF 월 1건
- `/ir/finance/airfreight*`, `/ir/finance/marine*`, `/ir/finance/sky*` — 물류·해운의 취급물량
- 소매·외식이면 기존점 매출, 장비면 수주/BB비 — 업종별로 명칭이 다르므로 "月次""取扱実績""受注" 키워드로 탐색

처리:
1. 최근 24개월치 PDF를 §5의 JSZip 일괄 다운로드로 확보 (`monthly_YYYY_MM.pdf`)
2. **최신 1건만** pdf.js로 텍스트 추출해 `leading_indicators_*.txt`에 표로 정리
3. 요약에는 반드시 **YoY 수준이 아니라 YoY의 가속/감속(2차 미분)** 을 적는다.
   예) "日本発 항공 1Q +112% → 2Q +110% → 7·8월 +125% = 가속"
4. 회사가 "경영계획 KPI에 대응한다"고 주석을 단 지표는 ★표기 — 회사 스스로 책임지는 숫자다

> 실측(NXHD 9147): 월차에서 국내 육상(철도·소구화물·자동차)은 전부 마이너스인데 세그먼트 이익은 증익 계획
> → "국내 증익은 물량이 아니라 가격개정"이라는 결론이 월차 하나로 검증됐다. 이런 교차검증이 이 단계의 목적이다.

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
Bridge Salon(bridge-salon.jp)도 같은 방식으로 1회만 검색 — 리포트가 있으면 수집하되
깊이가 얕으므로 다른 소스가 확보됐으면 skip해도 된다.

### 4-4. IR Agents 취재노트 (ir-agents.com/media) — IR 1:1 인터뷰 Q&A ★중소형주 핵심 소스

前애널리스트·PM이 상장사 IR과 1:1 취재를 진행하고 문답식 Q&A(取材ノート)로 정리하는
서비스. capacity·share·마진·리드타임 등 IR 콜 수준의 디테일이 담기며, 결산 직후 같은
회사를 반복 취재해 분기 추적이 가능하다. 상당수 자료는 회사가 게시 전 검수하므로
공격적 뉘앙스는 완화될 수 있으나 수치 신뢰도는 높다.

```
취재노트 목록: https://ir-agents.com/media/category/取材ノート/
무료 공개분: https://ir-agents.com/media/tag/完全公開記事/
검색: WebSearch → "{회사명} site:ir-agents.com"
유료회원 안내: https://ir-agents.com/media/paid-membership-info/ (3개월 3,300엔, 가입 https://ir-agents.com/media/register/)
```

> **계정 정보**: Drive `Investment Research/_config/iragents_account.txt` 참조 (RootN
> 계정 보유, 2026-08 가입). **계정·비밀번호를 이 문서에 직접 기재하지 않는다.**
> 잠긴 기사가 있으면 Chrome으로 로그인 후 재시도한다.

절차:
1. 대상 종목의 취재노트 존재 여부를 검색으로 확인 (사이트 내 검색 또는 WebSearch)
2. **완전공개(무료) 기사**는 `get_page_text`로 전문 추출 → `iragents_note_YYYY-MM_{주제}.txt`
3. **유료회원 전용 기사**: Chrome으로 로그인(계정은 위 `_config` 파일) 후 전문 수집.
   로그인해도 잠겨 있으면(유료 플랜 미전환·업종 열람 제한 등) 제목·날짜·링크만
   `수집불가_링크모음.txt`에 기록하고, **결과 보고에 "IR Agents 열람 불가 N건 — 사유"
   형태로 반드시 표기**한다. 유료 전환·결제는 사용자 확인 필요.
4. 대상 종목 취재노트가 없으면: 취재 리퀘스트 가능(1회 최대 5개 기업) 사실을 결과
   보고에 언급한다. 리퀘스트 제출 자체는 웹폼 제출이므로 사전 확인 대상.

> **주의**: 경쟁 가능성이 있는 업종 독자는 열람이 제한될 수 있다. 계정 상태(무료/유료)는
> `_config` 파일의 plan 항목이 기준 — 유료 전환이 완료되면 그 파일만 갱신하면 된다.

### 4-5. Kabu Berry Lab · 湘南投資勉強会 — 개인투자자 IR 세미나 Q&A (무료)

기관 커버리지가 없는 중소형주의 경영진·IR Q&A를 무료로 볼 수 있는 소스.
회사가 비용을 내는 공개 IR 행사이므로 홍보 성격을 감안해 **"신뢰도 중"을 명기**하고
쓴다. Q&A 분량은 길고(행사당 질문 ~20개+) 구체적인 편.

```
Kabu Berry: https://kabuberry.com/ (행사 목록) + YouTube "KabuBerry Channel"
검색: WebSearch → "{회사명} Kabu Berry 質疑応答" / "{회사명} site:note.com KabuBerry"
湘南투자회: YouTube "湘南投資勉強会オンライン" + WebSearch → "{회사명} 湘南投資勉強会"
```

절차 (종목당 검색 1~2회로 fail-fast):
1. 대상 종목의 과거 등판 여부를 검색. 없으면 즉시 skip — **중소형주라도 없는 게 정상**
2. Q&A 전문이 note 등 텍스트로 공개된 경우 → `get_page_text` 추출 →
   `kabuberry_qa_YYYY-MM.txt` / `shonan_qa_YYYY-MM.txt` (참가 회사 IR note에 올라오는
   경우가 많음: 예 `note.com/{회사}_ir`)
3. 영상만 있는 경우 → 링크·행사일·제목만 `수집_요약.txt`에 기록 (영상 전사는 하지 않음)
 
---
 
## Step 5: 파일 다운로드 및 정리
 
### 다운로드 방법 (우선순위)
 
0. **경로 판별 (먼저)**: §3-1의 egress 1회 테스트 결과에 따라 갈린다.
   클라우드 curl이 살아 있으면 1번, `000`이면 **곧장 2번(JSZip)** 으로 간다.

1. **Bash curl** (egress 허용 환경에서만): `irpocket.com`, `eir-parts.net`, `storage-yahoo.jp` 호스팅 PDF를 직접 다운로드.
   ```bash
   curl -sL -o "파일명.pdf" "PDF_URL"
   file 파일명.pdf  # 유효성 확인 (196 bytes 등 극소 파일은 실패)
   ```

2. **★Chrome + JSZip 일괄 다운로드 (차단 환경의 표준 경로 — 실전 검증됨)**

   Chrome 페이지 컨텍스트에서 PDF를 `fetch`해 zip 1개로 묶어 **1회만** 다운로드한다.
   개별 파일을 연속 다운로드하면 Chrome이 중간에 차단하므로, 건수가 5건을 넘으면 무조건 이 방식을 쓴다.
   (실측: 38건/69MB, 20건/7.4MB 각각 1회 성공)

   ```javascript
   // 1) 라이브러리 로드 (cdnjs 허용 확인됨). 페이지를 navigate하면 날아가므로 그때마다 재로드.
   await new Promise((res, rej) => { const s = document.createElement('script');
     s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
     s.onload = res; s.onerror = () => rej('blocked'); document.head.appendChild(s); });

   // 2) window.__ITEMS = [{h: <url>, name: <ASCII 파일명>}, ...] 를 미리 만들어 둔다
   const zip = new JSZip(); const used = {}; const log = [];
   for (const it of window.__ITEMS) {
     let n = it.name;
     if (used[n]) { used[n]++; n = n.replace(/\.(pdf|xls|xlsx)$/, '_' + used[it.name] + '.$1'); } else used[n] = 1;
     try {
       const r = await fetch(it.h);
       if (!r.ok) { log.push('FAIL ' + r.status + ' ' + n); continue; }
       const b = await r.arrayBuffer();
       if (b.byteLength < 2000) { log.push('TOOSMALL ' + b.byteLength + ' ' + n); continue; }  // HTML 리다이렉트
       zip.file(n, b); log.push('OK ' + (b.byteLength / 1024 | 0) + 'KB ' + n);
     } catch (e) { log.push('ERR ' + n + ' ' + e.message); }
   }
   const blob = await zip.generateAsync({ type: 'blob' });
   const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
   a.download = '{영문사명}_{코드}_IR_{YYMMDD}.zip'; document.body.appendChild(a); a.click();
   JSON.stringify({ zipKB: blob.size / 1024 | 0, log });
   ```

   - **툴 출력이 잘려 log 뒷부분을 못 볼 수 있다.** 성공 여부는 `log.filter(x => !x.startsWith('OK'))` 로만
     따로 뽑아 확인하고, 전량 성공이면 실패 목록이 빈 배열로 나온다.
   - 파일명은 반드시 ASCII (`ir_qa_FY2026Q2.pdf` 등). 일본어 파일명은 zip 압축 해제 시 깨진다.
   - zip은 사용자의 **Chrome 다운로드 폴더**(Drive 연동 폴더인 경우가 많음)에 떨어진다.
     컨테이너에서는 확인할 수 없으므로 **결과 보고에 "압축 해제 필요"와 예상 파일명을 반드시 명시**한다.

3. **★pdf.js 텍스트 추출 → Blob 다운로드 (토큰 절약의 핵심)**

   質疑応答要旨·補足資料처럼 텍스트가 본체인 PDF는 브라우저에서 추출한다.
   **추출한 전문을 툴 출력으로 회수하지 말 것** — `javascript_tool` 출력은 일본어 기준 약 1,700자에서 잘리므로,
   3만 자짜리 자료를 끌어오려면 15회 이상 호출해야 해서 토큰이 폭증한다.

   ```javascript
   await new Promise((res, rej) => { const s = document.createElement('script');
     s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
     s.onload = res; s.onerror = rej; document.head.appendChild(s); });
   pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
   window.__ext = async (url) => {
     const d = await pdfjsLib.getDocument({ url }).promise; let o = '';
     for (let i = 1; i <= d.numPages; i++) {
       const tc = await (await d.getPage(i)).getTextContent();
       let last = null, line = ''; const lines = [];
       tc.items.forEach(it => { const y = Math.round(it.transform[5]);
         if (last !== null && Math.abs(y - last) > 3) { lines.push(line); line = ''; }
         line += it.str; last = y; });
       lines.push(line); o += '\n--- p' + i + ' ---\n' + lines.join('\n');
     }
     return o;
   };
   ```

   회수 규칙:
   - **전문** → `Blob` 다운로드로 사용자 폴더에 직접 떨군다 (`{코드}_QA_all.txt` 등). 컨텍스트를 거치지 않는다.
   - **툴 출력으로는 구조만** 가져온다 — 섹션 헤딩, `Q\d+` 문항 머리 40~60자, 핵심 수치 1줄.
     예: `[...c.matchAll(/Q\d+[．.](.{0,50})/g)].map(m => m[1])`
   - 표 형식 슬라이드는 페이지 단위로 키워드 필터링해 필요한 페이지만 본다
     (`if (/欧州/.test(body) && /事業利益/.test(body))`).

4. **텍스트 추출 저장**: Chrome `get_page_text`로 페이지 내용을 `.txt`로 저장. (Kabutan 재무, 컨센서스 등)

5. **링크 수집**: 위 방법 모두 불가 시 `수집불가_링크모음.txt`에 URL·설명·접근불가 사유를 정리.

> **중요**: curl로 다운받은 PDF는 반드시 `file` 명령으로 확인한다. 200 bytes 미만이면 HTML 리다이렉트 응답일 가능성이 높으므로 다른 URL을 시도한다. JSZip 경로에서는 위 코드의 `byteLength < 2000` 가드가 같은 역할을 한다.
 
### 파일명 규칙
 
```
[자료유형]_[YYYY-MM]_[FY정보]_[설명].[확장자]
```
 
실전 검증된 파일명 예시:
- `consensus_kabuyoho.txt` — 株予報Pro 컨센서스 데이터
- `consensus_minkabu.txt` — Minkabu 컨센서스 데이터
- `financials_kabutan.txt` — Kabutan 재무 데이터 (통기+분기+CF+BS)
- `shikiho_6758.txt` — 四季報 독자예상·기자 코멘트·대주주
- `iragents_note_2026-05_北米PDU.txt` — IR Agents 취재노트
- `kabuberry_qa_2026-02.txt` / `shonan_qa_2025-11.txt` — 개인투자자 IR 세미나 Q&A
- `ir_presentation_2025-11_FY2026_1H説明会.pdf` — 결산설명회자료
- `ir_presentation_2025-05_FY2025決算.pdf` — 통기 결산설명회자료
- `ir_qa_2025-05_FY2025質疑応答.pdf` — Q&A 요약
- `ir_supplement_2026-02_FY2026_3Q.pdf` — 분기 보충자료
- `ir_tanshin_2026-02_FY2026_3Q.pdf` — 결산단신
- `ir_individual_investor_presentation.pdf` — 개인투자자 설명자료
- `monthly_2026_08.pdf` — 월차 매출 리포트 (§3-1b)
- `leading_indicators_volume.txt` — 월별 취급물량·월차 매출 YoY 정리 (§3-1b)
- `segment_guidance_FY2026.txt` — 세그먼트별 가이던스 vs 전기 실적 + 환율 특수요인 분해
- `capital_allocation_*.txt` — 자본배분·주주환원 계획 (자사주·정책보유주 축소·자산매각)
- `qa_agenda_FY20XX-FY20YY.txt` — 질의응답 논점 지도 (전문은 Blob 다운로드본에 위임)
- `수집_요약.txt` — 개별 종목 수집 요약
- `수집불가_링크모음.txt` — 다운로드 불가 자료의 링크 목록

zip 및 브라우저 직접 다운로드분 (사용자 다운로드 폴더 — 컨테이너에서 확인 불가하므로 보고에 명시):
- `{영문사명}_{코드}_IR_{YYMMDD}.zip` — IR PDF·Excel 일괄
- `{영문사명}_{코드}_monthly_{YYYY}-{YYYY}.zip` — 월차 리포트 일괄
- `{코드}_QA_FY20XX-FY20YY_all.txt` / `{코드}_{분기}_supplement_raw.txt` — pdf.js 추출 전문
 
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
 
### 유료 소스 구독 검토 (해당 시)
- IR Agents 유료 취재노트 N건 존재 (3개월 3,300엔) — 링크 목록
- note 유료 기사 구매 검토 — 제목·작성자·가격·링크 (kabuyomi 경유 발견분)
 
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
- 유료 서비스 신규 구독·결제·취재 리퀘스트 제출은 자동 진행하지 않는다 — 필요성만 보고하고 사용자 확인 후 진행 (기존 구독분 로그인·수집은 자동 진행)
- 직접 IR 미팅 확보(1:1·그룹)는 이 스킬 범위 밖 — `ir-meeting-request-jp` 스킬 또는 みんせつ(기관 등록) 경로를 안내
 
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
- **四季報 데이터가 비어 보임**: 로그인 세션 만료 가능성. `id.toyokeizai.net/sol/`에서 재로그인 1회 시도, 실패 시 flagging 후 skip. 계정은 Drive `_config/toyokeizai_account.txt`.
- **IR Agents 기사가 잠김**: 유료회원 전용 또는 업종 열람 제한. 무리하게 우회하지 말고 제목·링크만 기록 후 구독 검토로 보고.
- **Kabu Berry·湘南 Q&A 텍스트를 못 찾음**: 행사 자체가 없거나 영상만 공개된 경우. 해당 회사 IR note(`note.com/{회사}_ir`)를 한 번 더 확인하고 없으면 링크만 기록.
- **공식 IR 사이트 도메인 불명**: WebSearch로 `"{회사명} IR 投資家情報"` 검색하여 정확한 도메인 확인. 예: 노무라마이크로는 `nomura-nms.co.jp` (nomura-ms.co.jp가 아님).
- **여러 종목 처리 시 효율**: 동일 소스(Kabuyoho → Minkabu → Kabutan)를 전 종목에 순차 처리한 후, IR PDF 다운로드를 별도 배치로 처리하면 Chrome 탭 전환이 줄어들어 효율적.
- **클라우드 curl·WebFetch가 전부 `000`**: 조직 egress 차단(CONNECT 403). `curl -sS "$HTTPS_PROXY/__agentproxy/status"` 로 확인 가능. 우회 시도 금지 — Chrome 단독으로 전환하고 요약의 '미수집' 절에 사유를 명시한다.
- **IR 라이브러리에 결산설명자료가 없음**: §3-1의 앵커 텍스트 스캔 + 후보 URL HEAD 판별 2단계를 쓸 것. "없음"으로 단정하기 전에 IR 톱·event 페이지까지 훑는다.
- **PDF 링크가 0건 추출됨**: `<details>` 아코디언이 접혀 있을 가능성이 가장 높다. `d.open = true` 후 재시도. 그래도 0건이면 JS 렌더링 페이지이므로 `fetch` + DOMParser가 아니라 **실제 navigate 후** 추출해야 한다.
- **Chrome 연속 다운로드가 중간에 멈춤**: 브라우저의 다중 다운로드 차단. §5-2 JSZip 1회 다운로드로 전환.
- **javascript_tool 출력이 중간에 잘림**: 일본어 기준 약 1,700자가 한계. 전문은 Blob 다운로드로 사용자 폴더에 떨구고, 툴 출력으로는 헤딩·문항 머리·핵심 수치만 정규식으로 뽑는다.
- **cdnjs 스크립트 로드 실패**: 해당 사이트 CSP가 외부 스크립트를 막는 경우. IR 사이트는 대체로 허용되므로, 막히면 CSP가 느슨한 다른 자사 페이지(월차 페이지 등)로 이동해 같은 작업을 수행한다.
- **지주회사 전환 종목의 과거 데이터 단절**: 티커가 바뀌었으면(예: 日本通運 9062 → NIPPON EXPRESS HD 9147, 2022.1 株式移転) 전환 전 공시는 구 법인명으로 EDINET에 있고, 결산기 변경이 겹치면 변칙 결산(예: 2021년 4~12월 9개월)이 섞인다. 회사가 접합해 공표하는 장기 재무 Excel이 있으면 그것을 1차 소스로 쓴다.

## 검증된 IR 사이트 도메인 목록

| 회사명 | 종목코드 | IR 도메인 | 결산설명자료 URL |
|-------|---------|----------|---------------|
| オルガノ | 6368 | organo.co.jp | /ir/briefing/ |
| 野村マイクロ | 6254 | nomura-nms.co.jp | /ir/library/investment-briefing.html |
| 栗田工業 | 6370 | kurita.co.jp | /ir/ |
| 大気社 | 1979 | taikisha.co.jp | /ir/ |
| 高砂熱学 | 1969 | tte-net.com | /ir/ |
| ＴＯＷＡ | 6315 | towajapan.co.jp | /jp/ir/library/ (서버렌더 — HTML을 curl로 받아 PDF·데이터북 링크 직접 추출 가능. 데이터북 = `*_briefing.xlsx`, PDF·xlsx 모두 클라우드 curl 다운로드됨) |
| NIPPON EXPRESS HD | 9147 | nipponexpress-holdings.com | **`/ja/ir/event/data-room/`** (★IR資料室 아님. `<details>` 아코디언 — 펼쳐야 링크 추출됨. PDF는 pdf.irpocket.com/C9147/… 난수 경로. 월차 `/ja/ir/finance/monthly/`, 물량 KPI `/ja/ir/finance/airfreight_nxhd/`·`/marine_nxhd/`, 장기 재무 Excel `/ja/ir/finance/xls/financial-data.xls`. 経営計画 `/ja/ir/management/plan/`, 자본정책 `/ja/ir/management/improvement/`. 統合報告書·有報·ファクトブック 4개 페이지는 JS 렌더링이라 fetch-DOM 파싱 실패 → 브라우저로 직접 열 것) |
