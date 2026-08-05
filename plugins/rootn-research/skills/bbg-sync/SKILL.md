---
name: bbg-sync
version: 260724
description: >-
  블룸버그 PC의 로컬 인박스(C:\Bloomberg_Inbox\)에 떨어진 Bloomberg 산출물(blpapi 덤프 xlsx,
  RES 셀사이드 PDF, BI 리포트, 모델 export)을 데스크톱 앱 파일 브리지로 스캔해 구글 드라이브
  'Investment Research' 종목 폴더(xlsx→Model/, PDF→리서치/, IR성→IR/)로 인제스트하는 스킬.
  Layer 1(파일 생성)은 블룸버그 PC의 bbg_dump.py(xbbg/blpapi, Windows 작업 스케줄러)와 수동
  다운로드가 담당하고, 이 스킬은 Layer 2(집어가기)를 담당한다. "인박스 싱크", "블룸버그 싱크",
  "BBG 싱크", "Bloomberg_Inbox 정리", "블룸버그 덤프 올려줘", "BBG 파일 드라이브로" 등의 키워드,
  또는 ir-research-pipeline이 Bloomberg 자산 점검 단계에서 호출할 때 이 스킬을 사용할 것.
  종목 모드(특정 티커만)와 전체 모드(인박스 전량) 지원. RootN 리서처 전용. (v260721, 설계 v260715 재구현)
---

# bbg-sync — Bloomberg_Inbox → Drive 인제스트

> **공통 규칙**: `_shared/common-rules.md` 적용 — fail-fast, ASCII 파일명, 드라이브 3점 검증.
> 아키텍처 전제: 클라우드 Claude는 Bloomberg 터미널·엑셀을 원격 조작할 수 없다. 자동화 경계선은
> **"블룸버그 PC의 지정 폴더에 파일이 떨어진 이후"**부터다. 파일을 떨어뜨리는 장치(Layer 1)는
> `scripts/bbg_dump.py` + 수동 다운로드이고, 이 스킬은 떨어진 파일을 집어가는 장치(Layer 2)다.

## 0. 전제 조건

1. **데스크톱 앱 브리지 연결** — `mcp__remote-devices__*` 도구가 살아 있고, 신뢰 폴더에
   `Bloomberg_Inbox/`가 마운트되어 있어야 한다. 오프라인이면 "브리지 오프라인 — skip"으로
   보고하고 종료(재시도 금지).
2. **브리지 기기 판별**: 두 PC(메인/블룸버그)의 데스크톱 앱이 동시에 켜져 있을 수 있다.
   마운트 폴더 목록에서 `Bloomberg_Inbox/` 존재 여부로 블룸버그 PC를 판별한다.
3. 브리지 마운트는 **삭제 불가**(rm 금지) — 처리 완료 파일은 `_uploaded/`로 `mv`한다.

## 1. 인박스 표준 구조 (블룸버그 PC)

```
C:\Bloomberg_Inbox\
├── dumps\        bbg_dump.py 산출물: [티커]_bbg_[YYYYMMDD].xlsx
├── _uploaded\    인제스트 완료분 (이 스킬이 mv)
├── _unsorted\    티커 파싱 실패분 (이 스킬이 mv 후 개별 보고)
└── (루트)        수동 다운로드: RES PDF·BI·모델 export, 파일명 앞에 티커 (예: 6758JT_UBS_initiation.pdf)
```

## 2. 워크플로우

### 2-1. 스캔
- 브리지로 `Bloomberg_Inbox/` 루트와 `dumps/`를 목록화. `_uploaded/`, `_unsorted/`는 제외.
- **종목 모드**(파이프라인 호출·티커 지정): 해당 티커 파일만 필터.
- **전체 모드**("인박스 싱크" 명령): 전량 처리.

### 2-2. 티커 파싱
- 파일명 선두 토큰에서 티커 추출. 허용 패턴: `005930KS`, `6758JT`, `AAPL`, `417840` 등
  (`_` 또는 공백 전까지). 실패 시 `_unsorted/`로 mv하고 개별 보고(파일명·사유).
- 티커 → Drive 종목 폴더 매핑: `Investment Research/[영문명 (코드)]/`. 폴더가 없으면
  종목 모드에선 생성, 전체 모드에선 생성 여부를 파일 목록과 함께 일괄 확인 후 진행.

### 2-3. Drive 매핑 규칙
| 파일 | 목적지 |
|---|---|
| `*_bbg_*.xlsx` (덤프), 모델 export xlsx | `Model/` |
| 셀사이드·BI PDF | `리서치/` |
| 회사 IR성 문서(설명회·공시류) | `IR/` |
| 판단 애매 | `리서치/`에 넣고 보고에 "분류 확인 요망" 표기 |

### 2-4. 업로드·정리
1. 브리지에서 파일을 클라우드 작업 폴더로 스테이징.
2. Drive 업로드 — 공통 규칙 3점 검증(중복 시 `_v2` 새 파일명, id·수정시각·용량 확인, 내용 재확인).
3. 성공분은 인박스에서 `_uploaded/`로 mv (동명 파일 존재 시 `_YYYYMMDD` 접미).
4. 실패분은 원위치 유지 + 개별 보고.

### 2-5. 덤프 무결성 체크 (dumps/*.xlsx)
- 시트 존재 확인: Meta / Consensus / Guidance / Recs / Revisions / Actuals_Q / Px / Macro.
- `_error` 로그 시트가 있으면 해당 티커를 보고에 별도 섹션으로 띄운다.
- Consensus 시트가 비어 있으면 "BEst 덤프 실패 — B안(확장 템플릿) 확인 필요" flagging.
- **Guidance 시트가 비어 있는 것은 실패 아님**: CEst 미제공 종목(예: 4443)은 정상. avail=Y인데 값이
  전무한 경우도 종목 특성이므로 flagging하지 않는다(Consensus까지 비면 그때 덤프 실패로 판단).

### 2-6. watchlist 소스·갱신 (Google Sheet → watchlist.csv, 일 1회 diff)
- **소스 오브 트루스 = Google Sheet**(RootN JP 모델포트, id `1cEYe8SgSXRO5DlGp8zRMiHaTBx6znUrcdE2yBrl5JcA`):
  **`타깃` 탭(≈`모델포트 1`) + `watchlist` 탭의 합집합(중복 제거)**. 두 탭 gid는 시트에서 확인.
- **동작(브리지가 BBG PC에 연결된 세션에서만)**: 두 탭 읽기 → 각 종목을 `ticker,name,sector_pack`로 변환
  (ticker는 BBG 형식 `NNNN JT Equity`/`NNNNNN KS Equity`/`AAPL US Equity`; sector_pack 배정) →
  현재 `C:\Bloomberg_Inbox\watchlist.csv`와 **diff** → 추가/삭제/섹터변경을 `C:\Bloomberg_Inbox\_watchlist_log.md`에
  날짜와 함께 append + 사용자 보고 → 새 watchlist.csv 저장.
- **주기·제약**: 일 1회면 충분(모델포트 변동 드묾), **12:00 덤프 이전**에 갱신돼야 그날 반영.
  - **bbg_dump.py는 시트를 못 읽는다**(사설 시트 인증 불가) → 이 갱신은 **반드시 Claude 세션**이 수행(Windows 스케줄러 아님).
  - 자동화: BBG PC 브리지 세션에서 예약 작업(create_trigger) 평일 11:45. ★헤드리스 실행 시 **BBG 데스크톱 앱이 켜져 연결**돼
    있어야 브리지·Google 커넥터가 살아있음 — 불안정하면 수동/리마인더로 대체하고 보고에 명시(fail-fast).

## 3. Layer 1 참고 (이 스킬이 실행하지 않는 것)

- `scripts/bbg_dump.py` — 블룸버그 PC **Windows 네이티브 Python**에서 실행 (Linux VM 불가:
  blpapi가 localhost:8194 터미널 연결 필요). Windows 작업 스케줄러 평일 12:00 1회
  (터미널 로그인 9~10시 이후에 돌아야 데이터 수신 — 그 이전 시각은 빈 덤프).
  입력 `watchlist.csv`, 출력 `dumps/[티커]_bbg_[YYYYMMDD].xlsx`. 셋업 절차는
  `references/bloomberg-pc-setup.md`.
- **B안 fallback**: blpapi 설치·접속 불가 시 기존 _Q/_A 템플릿에 BEst 시트를 추가한
  확장 템플릿(수동 refresh+저장)으로 전환. 이 경우에도 인제스트 경로는 동일.
- Desktop API 데이터는 **사내 이용 범위만** (외부 공유·재배포 금지) — 산출물 공유 시 주의 문구.

## 4. 일본 팩 (덤프에 포함되는 일본 특화 시트 — bbg_dump.py 담당)

a. BEst vs 会社計画(가이던스) 갭 + 과거 3년 보수성 계수. **가이던스는 CEst 계열**(Guidance 시트,
   BE250/252+값7). CEst 미제공 종목은 Guidance 빈 것이 정상.
   ★ **QC — 285A 벤더 데이터 레벨 신뢰 보류(덤프 실측 2026-07-24, 신뢰도 낮음)**: 갭이 매출만이 아니라
   **체계적**임. 가이던스(CEST) SALES ¥1.75조·NETINCME_G ¥0.87조 vs BEst SALES 1FY ¥9.55조(2FY 12.40·3FY 14.31)·
   NET_INCOME 1FY ¥5.26조 — 매출 5.5x·순익 ~6x. BEst는 **내부 정합**(연차 성장궤적 매끈, 함의주식수 ~573M 일정).
   Kioxia 실제 매출규모(~¥1.7조)는 **가이던스와 부합** → BEst 레벨이 ~5.5–6x 부풀려진 것으로 보이고,
   가이던스 OPER_INCME ¥1.30조(→OP마진 74%)도 비현실 → **285A(신규 상장)의 BEst·CEst 레벨 절대치는 그대로 쓰지 말 것**
   (스크립트 필드매핑은 정상 — 벤더 데이터 품질 이슈). 조치: 285A 레벨은 터미널 EEB/EE·회사 결산자료로 재확인,
   BEst는 방향성·리비전(상대)에만 사용. 다른 종목도 갭을 보수성 계수로 쓰기 전 EEB/EE 대조 후 사용.
b. Revisions momentum (BEst EPS/Sales FY1·FY2 주간 시계열) — growth delta 입력값
c. Toyo Keizai 추정 (커버리지 0 중소형의 유일 제3자 추정, 신뢰도 중). **`TOT_ANALYST_REC`에 Toyo Keizai가
   빠져 있을 수 있음**(실측 4443 ANR 목록 미표시, 'Entitled to 15 of 17') → ANR 수치 해석 시 유의.
d. 섹터 선행지표 팩 (공작기계 수주·기계수주·장비 billings·방일객수·TANKAN — macro_map.csv 매핑)
e. 수급 — **외국인 보유 확정 가용**(Meta의 BS_PERCENT_OF_FOREIGN_OWNERSHIP·CURRENT_FOREIGN_OWNERSHIP).
   **SHORT_INT은 일본 N.A.**(제외). **信用残은 표준 필드 미확인(TODO)** — 확정 시 추가.
f. 결산발표 캘린더

월차(月次) 데이터는 회사 IR·Kabutan 유지 (덤프 대상 아님).

## 5. 결과 보고 형식

| # | 파일 | 티커 | 분류 | Drive 경로 | 상태 |
|---|---|---|---|---|---|

+ `_unsorted` 목록(개별 사유), 덤프 무결성 이슈, 브리지 오프라인 여부.

## 6. 덤프 소비자 계약 (다른 스킬이 bbg 덤프를 읽는 법)

> 종목 재무·컨센을 다루는 분석 스킬(investment-note·financial-model-builder·comparative-investment-note·
> peer-momentum-screener·ir-research-pipeline)은 Drive `[종목]/Model/`의 **최신 `*_bbg_*.xlsx`**를
> 컨센·가이던스·리비전·주가 **1차 소스**로 사용한다(공통규칙에도 훅). 시트 스키마:

- **Meta**(전치): NAME·GICS_SECTOR·CRNCY·CUR_MKT_CAP·EQY_SH_OUT·실적발표예정일 + 외국인보유(BS140·DY186).
- **Consensus**(long: ticker/field/value/period): BEST_SALES·OPP·NET_INCOME·EPS(+HI/LO)·BEST_ANALYST_RATING·
  TOT_ANALYST_REC·BEST_TARGET_PRICE × period 1FY/2FY/3FY/1FQ/2FQ → forward 컨센·목표가·투자의견.
- **Guidance**(전치): CEST_* 회사계획(매출·OP·경상·순익·EPS). CEst 미제공 종목은 빔(정상).
- **Recs**: 브로커별 의견·TP·날짜(BEST_ANALYST_RECS_BULK).
- **Revisions**: BEST_EPS/SALES 주간 2년(1FY·2FY) → revision momentum·growth delta 입력값.
- **Actuals_Q**: 분기 실적 3년(매출·OP·순익·EPS). **Px**: 일간 종가·거래량 500일. **Macro**: 섹터 선행지표(macro_map 매핑분).
- ★ **레벨값 QC**: BEst/CEst 절대치는 종목별 이상치 점검 후 사용(§4a; 285A처럼 벤더 데이터 오류 가능). 방향성·리비전·비율은 그대로 사용 가능.
