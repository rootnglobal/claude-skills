---
name: bbg-sync
version: 261013
description: >-
  블룸버그 PC의 로컬 인박스(C:\Bloomberg_Inbox\)에 떨어진 Bloomberg 산출물(blpapi 덤프 xlsx,
  RES 셀사이드 PDF, BI 리포트, 모델 export)을 데스크톱 앱 파일 브리지로 스캔해 구글 드라이브
  'Investment Research' 종목 폴더(xlsx→Model/, PDF→리서치/, IR성→IR/)로 인제스트하는 스킬.
  Layer 1(파일 생성)은 블룸버그 PC의 bbg_dump.py(xbbg/blpapi, Windows 작업 스케줄러)와 수동
  다운로드가 담당하고, 이 스킬은 Layer 2(집어가기)를 담당한다. "인박스 싱크", "블룸버그 싱크",
  "BBG 싱크", "Bloomberg_Inbox 정리", "블룸버그 덤프 올려줘", "BBG 파일 드라이브로" 등의 키워드,
  또는 ir-research-pipeline이 Bloomberg 자산 점검 단계에서 호출할 때 이 스킬을 사용할 것.
  종목 모드(특정 티커만)와 전체 모드(인박스 전량) 지원. 덤프 유니버스·주기·헬스체크 운영 질문
  ("BBG 덤프 종목", "덤프 주기", "watchlist.csv")에도 사용. RootN 리서처 전용.
  (v261013: 덤프 주 1회 + 실적 후 단건, Drive 자동동기화, 시트 Apps Script가 유니버스 관리)
---

# bbg-sync — Bloomberg_Inbox → Drive 인제스트

> **공통 규칙**: `_shared/common-rules.md` 적용 — fail-fast, ASCII 파일명, 드라이브 3점 검증.
> 아키텍처 전제: 클라우드 Claude는 Bloomberg 터미널·엑셀을 원격 조작할 수 없다. 자동화 경계선은
> **"블룸버그 PC의 지정 폴더에 파일이 떨어진 이후"**부터다. 파일을 떨어뜨리는 장치(Layer 1)는
> `scripts/bbg_dump.py` + 수동 다운로드이고, 이 스킬은 떨어진 파일을 집어가는 장치(Layer 2)다.

> **현행 운영 (v261013)** — 브리지 없이도 도는 구조:
> - **Layer 0 (유니버스)**: 시트 Apps Script `assets/BbgUniverseSync_v1.gs`가 매일 06시 `타깃 ∪ Watchlist`를
>   Drive `내 컴퓨터 (1)/Bloomberg_Inbox/watchlist.csv`(folder id `1S_6f3qBxEoMz2hBRl-U62ljf50fgXbKf`)에 기록 →
>   Drive for desktop이 BBG PC `C:\Bloomberg_Inbox\`로 동기화. 설치는 `assets/INSTALL_BbgUniverseSync_v1.md`.
> - **Layer 1 (덤프)**: `bbg_dump.py`가 **주 1회(월 07:50, 직전 금요일 종가 기준)** 전체 배치 + 놓치면 다음 평일 캐치업.
>   실적 발표 D+2~5 종목은 Apps Script가 `requests/*.req`를 넣어 워처가 단건 덤프. 노트 작업 시 온디맨드 단건.
> - **Drive 반영**: `C:\Bloomberg_Inbox` 전체가 '내 컴퓨터' 동기화 대상이라 덤프는 **자동으로 Drive
>   `Bloomberg_Inbox/dumps/`에 올라간다** → 소비 스킬은 이 위치를 1차로 본다(§6). 이 스킬의 Model/ 인제스트(§2)는
>   PDF·수동 다운로드 정리나 종목 폴더 사본이 필요할 때만 쓴다.
> - **감시**: 배치 결과는 `_bbg_status.json`·`bbg_dump.log`(Drive에서 읽힘) → Apps Script `bbgHealthCheck`(매일 12시)가
>   실패·9일+ 지연·watchlist 미반영을 텔레 알림. 상태 질문엔 이 두 파일을 Drive에서 읽어 답한다.

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

### 2-6. watchlist 소스·갱신 (시트 Apps Script가 자동 — Claude 세션 불필요)
- **소스 오브 트루스 = Google Sheet**(RootN JP 모델포트, id `1cEYe8SgSXRO5DlGp8zRMiHaTBx6znUrcdE2yBrl5JcA`):
  **`타깃` 탭 + `Watchlist` 탭의 합집합(중복 제거, 타깃 순서 우선)**. 청산 종목은 두 탭에서 빠지면 자동 제외.
- **동작**: `BbgUniverseSync_v1.gs`의 `bbgSyncUniverse()`가 매일 06시 Drive의 watchlist.csv를 `setContent`로 갱신
  (변경 있을 때만, 기존 name·sector_pack 보존, 신규는 `jp_review` → 텔레로 추가/제외/미지정 보고).
  Drive 리비전이 이력. 구 `watchlist_sync.py`(PC 서비스계정 방식)는 **폐기**.
- **수동 보정**: sector_pack은 macro_map 매핑용(실데이터 영향은 `jp_machinery` 등 macro_map에 티커가 있는 팩만).
  바꾸려면 Drive watchlist.csv 해당 행의 3번째 열만 고치면 다음 동기화에서 보존된다. 덤프 제외는 `BBG.EXCLUDE`.
- **동기화 실패 감지**: PC가 읽은 종목 수(`_bbg_status.json`의 `watchlist_n`) ≠ Drive 행 수면 `bbgHealthCheck`가 경보 →
  BBG PC에서 파일 수동 교체.
- **Claude 세션에서 즉시 반영이 필요할 때**(시트 대량 변경 직후 등): Drive 커넥터는 내용 덮어쓰기 불가 → 기존 파일을
  `watchlist_YYYYMMDD_bak.csv`로 rename 후 새 `watchlist.csv` 생성(같은 폴더). 다음 Apps Script 실행이 새 파일을 이어서 관리.

## 3. Layer 1 참고 (이 스킬이 실행하지 않는 것)

- `scripts/bbg_dump.py` — 블룸버그 PC **Windows 네이티브 Python**에서 실행 (Linux VM 불가:
  blpapi가 localhost:8194 터미널 연결 필요). 작업 스케줄러는 **평일 07:50 매일 호출**하되 스크립트가
  주 1회만 배치(월요일 또는 마지막 성공 후 7일+ 캐치업), 그 외 즉시 종료. 터미널 미접속이면 10분 간격 최대 3시간
  probe 후 중단(빈 파일 미생성), 데이터 전무 덤프는 쓰지 않음. 모드: 무인자(주간) / `--force` / 단건 티커 /
  `--prune [--dry-run]`(티커별 최신+월말+최근 14일만 보존). 결과 `_bbg_status.json`·`bbg_dump.log`.
  입력 `watchlist.csv`, 출력 `dumps/[티커]_bbg_[YYYYMMDD].xlsx`. 셋업 절차는
  `references/bloomberg-pc-setup.md`. **배포 경로**: SSOT 수정 → Drive `Bloomberg_Inbox/bbg_dump.py`로 올리면
  (rename 백업 후 새 파일 생성) PC에 동기화된다.
- `bbg_request_watcher.py`(PC, 1분 폴링): `requests/*.req` 첫 줄 티커로 단건 덤프 → `requests/done/`.
  성공 후 `bbg_drive_upload.py`를 부르지만 자격증명 미설정이라 실패 로그만 남음(무해 — Drive 반영은 동기화가 담당).
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
> peer-momentum-screener·ir-research-pipeline)은 **최신 `*_bbg_*.xlsx`**를 컨센·가이던스·리비전·주가
> **1차 소스**로 사용한다(공통규칙 §2 훅). **찾는 법**: Drive 검색 `title contains '{코드}JTEquity_bbg_'`
> (한국 `{코드}KSEquity_bbg_`) → 파일명 날짜가 가장 최근인 것. 위치는 보통 `Bloomberg_Inbox/dumps/`(자동 동기화),
> 예전 인제스트분은 `[종목]/Model/`. 주 1회 갱신이므로 **파일명 날짜를 데이터 기준일로 명시**하고, 7일 넘게 지났거나
> 실적 발표 이후라면 BBG PC에 단건 요청(`requests/{코드}_JT_Equity.req`, 첫 줄 `{코드} JT Equity`)을 제안한다. 시트 스키마:

- **Meta**(전치): NAME·GICS_SECTOR·CRNCY·CUR_MKT_CAP·EQY_SH_OUT·실적발표예정일 + 외국인보유(BS140·DY186).
- **Consensus**(long: ticker/field/value/period): BEST_SALES·OPP·NET_INCOME·EPS(+HI/LO)·BEST_ANALYST_RATING·
  TOT_ANALYST_REC·BEST_TARGET_PRICE × period 1FY/2FY/3FY/1FQ/2FQ → forward 컨센·목표가·투자의견.
- **Guidance**(전치): CEST_* 회사계획(매출·OP·경상·순익·EPS). CEst 미제공 종목은 빔(정상).
- **Recs**: 브로커별 의견·TP·날짜(BEST_ANALYST_RECS_BULK).
- **Revisions**: BEST_EPS/SALES 주간 2년(1FY·2FY) → revision momentum·growth delta 입력값.
- **Actuals_Q**: 분기 실적 3년(매출·OP·순익·EPS). **Px**: 일간 종가·거래량 500일. **Macro**: 섹터 선행지표(macro_map 매핑분).
- ★ **레벨값 QC**: BEst/CEst 절대치는 종목별 이상치 점검 후 사용(§4a; 285A처럼 벤더 데이터 오류 가능). 방향성·리비전·비율은 그대로 사용 가능.
