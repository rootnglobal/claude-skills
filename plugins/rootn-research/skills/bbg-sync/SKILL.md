---
name: bbg-sync
version: 260721b
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

## 3. Layer 1 참고 (이 스킬이 실행하지 않는 것)

- `scripts/bbg_dump.py` — 블룸버그 PC **Windows 네이티브 Python**에서 실행 (Linux VM 불가:
  blpapi가 localhost:8194 터미널 연결 필요). Windows 작업 스케줄러 평일 07:50 1회.
  입력 `watchlist.csv`, 출력 `dumps/[티커]_bbg_[YYYYMMDD].xlsx`. 셋업 절차는
  `references/bloomberg-pc-setup.md`.
- **B안 fallback**: blpapi 설치·접속 불가 시 기존 _Q/_A 템플릿에 BEst 시트를 추가한
  확장 템플릿(수동 refresh+저장)으로 전환. 이 경우에도 인제스트 경로는 동일.
- Desktop API 데이터는 **사내 이용 범위만** (외부 공유·재배포 금지) — 산출물 공유 시 주의 문구.

## 4. 일본 팩 (덤프에 포함되는 일본 특화 시트 — bbg_dump.py 담당)

a. BEst vs 会社計画(가이던스) 갭 + 과거 3년 보수성 계수
b. Revisions momentum (BEst EPS/Sales FY1·FY2 주간 시계열) — growth delta 입력값
c. Toyo Keizai 추정 (커버리지 0 중소형의 유일 제3자 추정, 신뢰도 중)
d. 섹터 선행지표 팩 (공작기계 수주·기계수주·장비 billings·방일객수·TANKAN — macro_map.csv 매핑)
e. 수급 (외국인·信用残·공매도 — blpapi 가용성 확인 후)
f. 결산발표 캘린더

월차(月次) 데이터는 회사 IR·Kabutan 유지 (덤프 대상 아님).

## 5. 결과 보고 형식

| # | 파일 | 티커 | 분류 | Drive 경로 | 상태 |
|---|---|---|---|---|---|

+ `_unsorted` 목록(개별 사유), 덤프 무결성 이슈, 브리지 오프라인 여부.
