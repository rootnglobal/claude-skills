# Target Model Structure — 정통 sell/buy-side 스타일

기관 sell-side 모델(예: 카지노 섹터 Sands/Galaxy/Melco/MGM 모델)을 참고한 목표 구조. 핵심 특징 3가지를 반드시 구현한다.

## 1. 분기 + 연간 둘 다
- **연간 3-statement**: Income Statement / Balance Sheet / Cash Flow / Ratios (각 시트, 전 라인 보존).
- **Quarterly 시트**: 분기 컬럼 + 각 연도 끝에 **FY 컬럼 = SUM(그 해 분기)** 를 라이브 수식으로. 분기↔연간이 한 시트에서 묶인다.
- 참고 모델 패턴: 별도 "Quarterly" 시트 + 연간 "earnings (F)/BS (F)/CF (F)". 분기 Q4는 흔히 `=FY - SUM(Q1:Q3)`로 역산, FY는 `=SUM(분기)`로 정산.

## 2. Bottom-up 링크 (셀끼리 연결)
- 제품/지역/자산(property)별 driver 시트 → 집계(Financials) → 연결 3-statement 로 **링크**(`=Financials!F19` 처럼). 값 복붙이 아니라 셀 참조.
- 본 스킬에서는: **Segment build** 합계가 IS Revenue와 tie-out 되도록 연결하고, Quarterly FY가 연간 IS와 tie-out 되도록 연결한다. 모든 파생값(마진·YoY·bridge)은 statement 셀을 참조하는 **라이브 수식**.

## 3. 자세한 breakdown
- 제품×지역×고객 segment, 분기별 segment, 물량/단가(ASP), 선행지표(수주잔고·수출입·capex·가동률), peer까지.
- 참고 모델은 property별로 VIP/Mass/슬롯, win rate, 테이블 수까지 분해 → 같은 깊이를 segment 데이터가 있는 만큼 재현한다.

## 입력 매핑 (inputs.json)
- 연간 3-statement → `statements.{income_statement,balance_sheet,cash_flow,ratios}.lines` (Bloomberg 값 전부 보존, key 6개 태깅).
- 분기 → `quarterly.{quarters, fy_groups, lines}` (line type=flow/stock/ratio).
- breakdown → `segments`, `leading_indicators`, `peers`.
build_model.py가 이를 받아 분기 FY합산·tie-out·bridge를 라이브 수식으로 깐다.

## tie-out 체크 (검증)
- Quarterly: "FY Rev vs 연간 IS (tie-out)" ≈ 0
- Segment build: "vs IS Revenue (tie-out)" ≈ 0
- Margin bridge: 효과 합 = 실제 ΔGP/ΔOP
빌드 후 LibreOffice 재계산(또는 Excel)으로 이 값들이 0 근처인지 확인한다.
