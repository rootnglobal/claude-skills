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
pip install xbbg pandas openpyxl
```

blpapi는 localhost:8194로 터미널에 무인증 접속한다 (터미널 로그인 상태 필요).

## 4. mnemonic TODO 확정 (터미널 FLDS)

- 일본 가이던스(会社計画) 필드: 터미널에서 `FLDS` 실행 → guidance 검색 → bbg_dump.py의
  `GUIDANCE_FLDS` TODO 교체
- `TOT_ANALYST_REC`의 Toyo Keizai contributor 포함 여부 확인
- 수급 필드(외국인·信用残·공매도) 가용성 확인 → 가용 시 필드 추가
- `macro_map.csv` 섹터별 선행지표 티커 채우기 (공작기계 수주, 기계수주, SEMI billings, 방일객수, TANKAN 등)

## 5. 수동 1회 실행·검증

```
py -3 C:\Bloomberg_Inbox\bbg_dump.py
```

- `dumps\`에 `[티커]_bbg_[YYYYMMDD].xlsx` 생성 확인
- `_error` 시트가 있는 티커는 사유 확인 (필드 미가용·티커 오타·entitlement)

## 6. 작업 스케줄러 등록 (평일 07:50)

```
schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN "bbg_dump" /ST 07:50 /TR "py -3 C:\Bloomberg_Inbox\bbg_dump.py"
```

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
