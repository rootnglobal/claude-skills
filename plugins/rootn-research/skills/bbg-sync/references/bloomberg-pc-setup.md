# 블룸버그 PC 셋업 가이드 (Phase 2 — 1회, 약 30~60분)

전제: Bloomberg 터미널 설치·로그인된 Windows PC. Claude 데스크톱 앱 설치(파일 브리지용).

## 1. 인박스 폴더 생성

```
C:\Bloomberg_Inbox\
├── dumps\
├── _uploaded\
└── _unsorted\
```

Claude 데스크톱 앱에서 `C:\Bloomberg_Inbox\`를 신뢰 폴더로 등록한다.

## 2. 파일 배치

`bbg_dump.py`, `watchlist.csv`, `macro_map.csv`를 `C:\Bloomberg_Inbox\`에 복사.
(브리지로 Claude가 직접 갱신할 수 있는 위치여야 한다 — 이후 watchlist 수정은 Claude가 수행 가능.)

- `watchlist.csv` 컬럼: `ticker,name,sector_pack`
  예: `005930 KS Equity,Samsung Electronics,semis` / `6758 JT Equity,Sony,jp_tech`
- `macro_map.csv` 컬럼: `sector_pack,bbg_ticker,label`
  예: `jp_machinery,JMTOYOY Index,공작기계 수주 YoY` (섹터 선행지표 매핑, TODO 채우기)

## 3. Python 환경 (Windows 네이티브 — Linux VM·WSL 불가)

Python 3.8~3.12 설치 후:

```
pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/
pip install xbbg pandas openpyxl "pyarrow>=22.0"
```

blpapi는 localhost:8194로 터미널에 무인증 접속한다 (터미널 로그인 상태 필요).

> **실측 주의(Phase 2)**: 최신 **xbbg 1.x(rust)는 polars DataFrame을 반환** → 스크립트의 `to_pd()`가
> pandas로 정규화하며, 이때 **pyarrow>=22.0 필수**(누락 시 변환 실패). 정상 완료 후에도
> `SessionConnectionDown`/`SessionTerminated` WARN·ERROR가 찍히는데 **덤프는 이미 저장된 뒤라 무해**
> (`[OK]` 줄이 먼저 출력되면 성공).

## 4. mnemonic 확정 결과 (터미널 FLDS 실측, 2026-07-22 · 285A/4443 JT)

- **가이던스(会社計画) = CEst 계열 확정** → `GUIDANCE_FLDS`에 반영 완료:
  `CEST_CUR_GUIDANCE_AVAIL`(BE250)·`CEST_LAST_CO_GUIDANCE_UPDATE_DT`(BE252) + 값 7개
  (BE202 SALES / BE215 OPER_INCME / BE216 CUR_PROFIT / BE205 NET_INCOME / BE217 NETINCME_G /
  BE206 EPS / BE220 EPS_GAAP). 종목·회계기준에 따라 가용 필드가 갈리므로 **7개 전부 넣고 가용분만 잡히게** 함.
  실측: 285A는 SALES·OPER_INCME·NETINCME_G 값 존재(업데이트 05/15), **4443은 avail=true지만 값 전무
  (CEst 미제공 종목 → Guidance 시트 빈 것이 정상, 실패 아님)**.
- **`TOT_ANALYST_REC` — Toyo Keizai 주의**: 4443 ANR 표시 목록에 Toyo Keizai 없음. 단 화면에
  'Entitled to 15 of 17' → 미열람 2개 소스에 포함됐을 여지 있어 **신뢰도 중**. ANR 해석 시 유의.
- **수급 확정**: 외국인 보유 **가용** → `BS_PERCENT_OF_FOREIGN_OWNERSHIP`(BS140)·
  `CURRENT_FOREIGN_OWNERSHIP`(DY186)를 Meta에 포함(실측 285A 68.47% / 4443 40.83%).
  **`SHORT_INT`(PR238)=일본 N.A.라 제외**. **信用残은 표준 필드 미확인 → TODO**(FLDS에서
  'margin trading'/'shintori' 재검색 필요).
- `macro_map.csv` 섹터별 선행지표 티커 채우기 (공작기계 수주, 기계수주, SEMI billings, 방일객수, TANKAN 등).
  `bbg_ticker`가 `TODO`인 행은 스크립트가 자동 스킵.

## 5. 수동 1회 실행·검증

```
py -3 C:\Bloomberg_Inbox\bbg_dump.py
```

- `dumps\`에 `[티커]_bbg_[YYYYMMDD].xlsx` 생성 확인
- `_error` 시트가 있는 티커는 사유 확인 (필드 미가용·티커 오타·entitlement)

## 6. 작업 스케줄러 등록 (평일 07:50 호출 · 주 1회 배치 — v261013)

> **현행**: 스케줄러는 평일 매일 07:50 호출, 스크립트가 스스로 주 1회(월요일, 놓치면 다음 평일 캐치업)만 배치한다.
> 터미널 미로그인이면 10분 간격 최대 3시간 재시도 후 중단(빈 파일 미생성) — 07:50 고정이어도 안전.
> (구 버전은 매일 배치였고, 2026-10-12 공휴일에 미로그인 상태로 종목당 ~13분 타임아웃·5.5KB 빈 파일이 남았음)

```
schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN "bbg_dump" /ST 07:50 /TR "py -3 C:\Bloomberg_Inbox\bbg_dump.py"
```

- 강제 즉시 배치: `py -3 C:\Bloomberg_Inbox\bbg_dump.py --force`
- 단건: `py -3 C:\Bloomberg_Inbox\bbg_dump.py "7203 JT Equity"` (워처·dump_one.bat이 사용)
- 보관 정리: `... bbg_dump.py --prune --dry-run` 확인 후 `--prune` (티커별 최신+월말+최근 14일 보존, 5.5KB 빈 덤프 삭제)
- `C:\Bloomberg_Inbox`는 Drive for desktop '내 컴퓨터' 동기화 대상 → 덤프·로그·상태파일이 Drive에 자동 반영되고,
  Drive에서 바뀐 `watchlist.csv`·`bbg_dump.py`·`requests/*.req`가 PC로 내려온다(역방향 동기화 필수).

## 7. B안 fallback (blpapi 불가 시)

기존 Bloomberg FA 템플릿(_Q.xlsx/_A.xlsx)에 BEst 시트(Consensus/Revisions)를 추가한
확장 템플릿을 만들어, 아침에 터미널 엑셀에서 열어 refresh 후 저장 → `dumps\`에 복사.
인제스트(bbg-sync Layer 2)는 동일하게 동작한다.

## 8. 수동 다운로드 컨벤션 (문서류)

RES 셀사이드 PDF·BI 리포트·모델 export는 `C:\Bloomberg_Inbox\` 루트에 저장하되
파일명 앞에 티커를 붙인다: `6758JT_UBS_initiation.pdf`, `005930KS_BI_memory_outlook.pdf`.

## 주의

- Desktop API 데이터는 **사내 이용 범위만** — 외부 공유·재배포 금지.
- 브리지 마운트는 삭제 불가 — 정리는 bbg-sync가 `_uploaded\`로 mv하는 방식으로만.
