---
name: financial-model-builder
version: 260721b
description: 주식 종목의 financial model을 Bloomberg Excel 템플릿 위에 만들고, IR 자료·sell-side 리포트·뉴스·웹서치·Gemini/GPT 리서치를 통합해 지역·제품·고객 segment별 매출/이익 breakdown, 수출입·수주잔고 등 선행지표, 그리고 성장의 원천(매출성장 vs mix개선 vs 마진개선, GP/OP)과 그 가속(growth delta)·지속성을 숫자로 분해하는 스킬. "재무모델 만들어줘", "financial model", "실적 모델", "segment 매출 분해", "growth 분해", "성장 지속성 분석", "밸류에이션 모델", "어닝 모델", "수주잔고 모델", 종목명·티커와 함께 모델/추정/분해 맥락이 나오면 이 스킬을 적극 사용할 것. 한국(DART)·미국(SEC)·일본(EDINET)·중국(CNINFO) 상장사를 모두 지원하며, 자료는 구글 드라이브의 'Investment Research/[종목명 (티커)]/' 데이터룸(Model·리서치·IR 폴더)에서 읽고 결과도 그 Model 폴더에 저장한다.
---

# Financial Model Builder

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


## 이 스킬이 답하려는 질문

최종 목적은 단 하나다: **"이 회사의 실적 성장(growth)의 delta가 커질 것인가, 그리고 그게 지속 가능한가?"** 를 숫자로 보여주는 것.

그러려면 모델이 네 가지를 분해해서 보여줘야 한다.

1. **어디서 버는가** — 지역·제품·고객 segment별 매출/이익 구조
2. **성장이 어디서 나오는가** — 물량(volume)인가, 단가(price)인가, mix 개선인가, 마진(GP/OP) 개선인가
3. **가속하는가** — 성장률 자체가 빨라지는가 (성장의 2차 미분 = growth delta)
4. **지속되는가** — 후행지표(P&L)와 선행지표(수주잔고·수출입·capex·book-to-bill)가 같은 방향을 가리키는가

숫자를 채우는 것보다 **이 분해를 만드는 것**이 핵심이다. 단순히 Bloomberg 값을 옮기는 작업이 아니다.

## 절대 원칙: 소스 위계 (Source Hierarchy)

리서치 모델이 망가지는 1순위 원인은 출처가 섞이는 것이다. 모든 숫자는 출처 우선순위를 따른다:

> 회사 공시·IR > Bloomberg actual > sell-side estimate > 뉴스/웹 > Gemini·GPT

**컨센서스(추정치)의 위계는 별도로**: BEst 덤프(`Model/*_bbg_*.xlsx`의 Consensus/Revisions
시트, `bbg-sync` 인제스트분) > CapIQ estimates export(`리서치/consensus/`, 검증·차선) >
개별 sell-side 리포트 수치 > 무료 소스(FnGuide/Kabuyoho/Minkabu). 위계가 다른 컨센 숫자가
충돌하면 높은 위계를 쓰고 차이를 Assumptions에 메모한다.

- **하드 넘버(모델에 들어가는 실제 숫자)는 1~2차 소스(공시·IR·Bloomberg)에서만** 가져온다.
- **Gemini/GPT 내용은 "가설/정성 색깔"로만** 쓴다. 그 안에서 1차 소스를 인용한 경우에만 숫자로 승격한다. AI 환각 숫자가 모델에 들어가는 것을 막는 가장 중요한 장치다.
- **모든 셀에 출처 태그를 단다** (Assumptions & Sources 탭의 source 컬럼 + 셀 코멘트). 출처 없는 숫자는 모델에 들어가지 않는다.

자세한 규칙: `references/source-hierarchy.md` 를 읽을 것.

## 데이터룸 구조 (Google Drive)

자료는 이 구조에서 읽고, 결과도 여기 `Model/` 에 저장한다. (기존 `ir-collertor` 스킬과 동일한 컨벤션)

```
Investment Research/
└── [종목명 (티커)]/              예: 롯데에너지머티리얼즈 (020150)
    ├── Model/                    Bloomberg 템플릿 (_Q.xlsx 분기, _A.xlsx 연간) + 산출 모델
    ├── 리서치/                    sell-side PDF
    ├── IR/                       IR 자료 (실적발표, 사업보고서, 분기보고서)
    └── AI리서치/ (선택)           Gemini/GPT에서 붙여넣은 .md/.txt + 링크
```

Drive 폴더/파일 접근은 Google Drive MCP 도구(`search_files`, `get_file_metadata`, `download_file_content`, `read_file_content`)를 사용한다. 데이터룸을 찾고 자료를 정리하는 상세 규칙은 `references/data-room.md` 를 읽을 것.

## 워크플로우

### 0. 범위 확인 (필요 시)
종목명/티커가 모호하거나 모델 범위(과거만 vs 추정 포함, 분기 vs 연간)가 불명확하면 먼저 짧게 확인한다. 명확하면 바로 진행한다.

### 1. 데이터룸 찾기 + Bloomberg 템플릿·덤프 수집
- Drive에서 `Investment Research/[종목명 (티커)]/Model/` 의 `*_Q.xlsx`(분기)와 `*_A.xlsx`(연간)를 찾는다.
- **BEst 덤프도 함께 찾는다**: `Model/`의 `[티커]_bbg_[YYYYMMDD].xlsx`(`bbg-sync` 인제스트분,
  최신 날짜 1개). 있으면 Consensus(FY1~3+분기)·Guidance·Recs·Revisions 시트를 로드해
  컨센 비교·guidance 갭 분석의 1차 소스로 쓴다. 없고 데스크톱 브리지가 살아 있으면
  `bbg-sync` 종목 모드를 먼저 1회 시도한다(오프라인이면 skip 보고).
- 템플릿을 로컬로 내려받아 `scripts/inspect_template.py` 로 구조를 파악한다. 이 스크립트는 시트 목록, 표준 IS/BS/CF 라인아이템, **Segments 탭의 segment 종류·기간 컬럼**, 그리고 캐시된 실적값(있으면)을 JSON으로 덤프한다.
- **IS/BS/CF/Ratios 시트의 전 라인아이템(라벨+기간값)을 추출**해 `inputs.statements`로 옮긴다(값 있는 라인 모두 보존). 기간은 `meta.periods`에 정렬. Bloomberg 구조·mnemonic은 `references/bloomberg-template.md` 참고.

**중요**: Bloomberg 셀이 `#NAME?` 면 add-in이 비활성 상태로 export된 것이다. 이 경우 캐시값(`data_only=True`)을 우선 읽고, 비어 있으면 공시·IR에서 actual을 보완한다. 모델 historicals는 반드시 실제 값이어야 한다.

### 2. 자료 수집 (소스 위계 순서대로)
- **IR 폴더**: 실적발표 자료, 사업보고서/분기보고서에서 segment 매출·이익, 수주잔고, capex, 가동률, 물량/단가(ASP)를 추출한다. 한국이면 필요 시 `ir-collertor` 스킬로 최신 IR을 먼저 수집할 수 있다.
- **리서치 폴더**: sell-side PDF에서 segment 추정, mix 가정, 마진 전망, 수출입·통계 데이터를 추출한다. (이미 들어있는 PDF는 PDF 도구로 읽는다.)
  `리서치/consensus/`에 CapIQ estimates export(xlsx)가 있으면 BEst 덤프 검증·보완용으로 로드한다(둘 다 없으면 무료 소스 fallback).
- **AI리서치 폴더**: 작업 시작 시 `AI리서치/` 폴더에 **빈 구글 Doc**(`YYYYMMDD_[종목명]_AI리서치`)을 만들어 사용자에게 링크를 주고, 거기에 Gemini/GPT 내용을 형식 제약 없이 복붙하게 한다(.txt 만들 필요 없음). 그 Doc을 읽어 가설 후보로만 반영. 1차 소스 인용 확인 시에만 숫자 채택. 상세는 `references/data-room.md`.
- **웹서치**: 수출입 통계, 산업 데이터, 최근 뉴스, 경쟁사 동향을 보완한다. 항상 1차 출처로 역추적한다.

### 3. 입력 정리 → inputs.json
수집한 내용을 `assets/inputs_schema.json` 스키마에 맞춰 `inputs.json` 으로 정리한다. 각 숫자에는 반드시 `source`(출처)와 `tier`(소스 위계 등급)를 붙인다. 스키마는 segment build, revenue bridge 드라이버(volume/price/mix/fx), margin bridge, leading indicators, assumptions, qualitative(가설) 섹션을 포함한다.

### 4. 모델 빌드
`scripts/build_model.py --inputs inputs.json --out <model.xlsx>` 를 실행한다. **출력은 sell/buy-side 모델처럼 정통 3-statement를 베이스로 깔고 그 위에 분석을 얹는 구조**다:

베이스 (반드시 Bloomberg 데이터 보존):
- **Income Statement / Balance Sheet / Cash Flow / Ratios** — Bloomberg 템플릿(또는 공시)에 값이 있는 라인아이템을 **하나도 빼지 말고 전부** `inputs.statements`에 옮겨 그대로 렌더. IS 하단에 GM%/OPM%/YoY/growth-delta 파생행을 자동 추가.

그 위에 add 하는 분석:
- **Quarterly** — 분기 컬럼 + FY 컬럼(=SUM 분기, 라이브 링크). 분기 OPM·연간 IS와 FY tie-out 자동. (`inputs.quarterly` 채우면 생성)
- **Dashboard** — growth delta 한눈에 (매출·YoY·가속·OPM, 3-statement 참조)
- **Segment build** — 지역×제품×고객 매출·이익 매트릭스
- **Revenue bridge** — segment 기여도(±%p), volume/price 분해 (라이브 수식)
- **Margin bridge** — ΔGP·ΔOP를 매출효과/마진(GM%)효과/opex 레버리지로 분해
- **Leading indicators** — 수주잔고·book-to-bill·수출입·capex·가동률
- **Peer benchmark** (선택) — `inputs.json`의 `peers` 채우면 자동 생성
- **Assumptions & Sources** — 모든 입력의 출처·tier + 가설(tier5)

**원칙: Bloomberg에 있는 IS/BS/CF/Ratios 숫자는 절대 삭제·요약하지 않는다.** 분석 탭은 이 라인들을 `key`(Revenue/COGS/GrossProfit/OpEx/OperatingProfit/NetIncome)로 참조한다. 분석에 필요한 6개 key는 반드시 태깅하고, 나머지 라인은 그대로 보존한다.

**정통 sell/buy-side 스타일 3원칙(참고 모델 기준, `references/model-structure.md`):** ① 분기+연간 둘 다(Quarterly 시트의 FY=SUM 분기 라이브 링크) ② bottom-up 셀 링크(Segment 합계→IS Revenue tie-out, Quarterly FY→연간 IS tie-out) ③ 자세한 breakdown(제품·지역·고객·물량/ASP·선행지표·peer). 값 복붙이 아니라 셀 참조·라이브 수식으로 연결한다.

bridge와 growth-delta는 **하드코딩이 아니라 Excel 수식**으로 깐다. 감사 가능하고, 사용자가 가정을 바꾸면 즉시 재계산되도록. 분석 정의(수식)는 `references/analytics-framework.md` 참고.

### 5. 1페이지 메모
`assets/memo_template.md` 를 채워 투자 논리 요약 메모를 만든다: 성장의 원천 한 줄, 지속성 판단(후행 vs 선행), 핵심 리스크, 다음 확인 포인트. 모델의 결론을 빠르게 전달하는 용도.

### 6. 저장 + 검증
- 모델과 메모를 Drive `Model/` 폴더에 저장한다 (파일명: `[티커]_[종목명]_Model_v[YYMMDD].xlsx`).
- **검증**: segment 합계 = 전사 매출 일치, bridge 합계 = 실제 ΔRevenue 일치, 출처 없는 셀 0개. 불일치는 메모에 명시한다.

## 산출물 요약
1. **Excel 모델** — 위 7개 탭, 라이브 수식, 셀별 출처
2. **1페이지 메모** — growth delta + 지속성 결론

## 참고 파일
- `references/source-hierarchy.md` — 소스 위계·인용 규칙 (반드시 숙지)
- `references/bloomberg-template.md` — Bloomberg FA 템플릿 구조·mnemonic·Segments 탭
- `references/analytics-framework.md` — growth delta·bridge 수식 정의
- `references/data-room.md` — Drive 데이터룸 컨벤션·AI 리서치 입력 규칙
- `references/model-structure.md` — 정통 sell/buy-side 분기+연간·bottom-up 링크 구조 (참고 모델 패턴)
- `assets/inputs_schema.json` — 모델 입력 스키마
- `assets/memo_template.md` — 1페이지 메모 템플릿

## 멀티 지역
한국(DART), 미국(SEC EDGAR), 일본(EDINET), 중국(CNINFO) 모두 지원. 지역별 공시 소스·segment 공개 관행 차이는 `references/data-room.md` 의 "지역별 노트" 참고. 일본 종목은 `jp-research-collector`, 한국 종목은 `ir-collertor`·`fnguide-report-downloader` 스킬의 산출물을 입력으로 재사용할 수 있다.
