# Bloomberg FA Template 구조

사용자의 템플릿은 Bloomberg "Financial Analysis (FA)" 표준 export다. 파일명 컨벤션: `[티커]_[종목명]_Q.xlsx`(분기), `_A.xlsx`(연간).

## 시트 구성 (관측된 구조)
- **IS Index Row** — Income Statement 라인아이템 ↔ Bloomberg 필드 mnemonic 사전. 산업별(Industrial / Bank / Insurance / Financial / Utility / REIT) × (Adjusted / GAAP) 변형을 모두 나열. 회사 산업에 맞는 컬럼만 유효.
- **BS Index Row** — Balance Sheet 라인아이템 ↔ mnemonic 사전.
- **CF (Cash Flow)** — 현금흐름 라인아이템.
- **표준 IS/BS/CF 데이터 시트** — 회사 실적값 (기간 컬럼). add-in 비활성 export면 셀이 `#NAME?`, 캐시값은 `data_only=True`로 읽힘.
- **Segments** — segment별 데이터. 헤더에 Ticker, Name, Acc Standard, Currency, **Type(예: Product)**, **Group By(Segment)**, Period(Quarterly), Level. 기간 컬럼은 분기(예: FQ2 2021 … FQ2 2029)로 과거+forward 플레이스홀더 포함. BICS_LEVEL_1/2/3 등 segment key field 사용.

## 주요 mnemonic (Industrial 기준)
| 라인 | mnemonic |
|------|----------|
| Revenue | SALES_REV_TURN |
| Cost of sales | IS_COGS_TO_FE_AND_PP_AND_G |
| Sales & Services Revenue | IS_S&SR_GAAP |
| Gross Profit | GROSS_PROFIT |
| Operating Income | IS_OPER_INC |
| Net Income | NET_INCOME |
| EPS (dil, cont ops) | IS_DIL_EPS_CONT_OPS |

산업이 Bank/Insurance/Utility/REIT면 해당 컬럼의 mnemonic을 쓴다 (NET_INT_INC, IS_TOT_NET_PREM_EARN, IS_REV_FROM_ELECT, IS_RENT_INC 등). IS Index Row 시트에서 회사 산업 컬럼을 확인할 것.

## 다루는 법
1. `scripts/inspect_template.py` 로 시트·기간 컬럼·Segments 블록·캐시값을 JSON 덤프.
2. **원본 템플릿을 직접 수정하지 않는다.** Bloomberg BDH 수식이 깨진다. 대신 historicals 캐시값을 읽어 **새 모델 워크북**에 옮기고 분석 탭을 추가한다.
3. Segments 탭은 Bloomberg가 주는 product/geographic segment의 출발점. 그러나 Bloomberg segment는 거칠다 — 고객별·세부 제품별·물량/단가는 IR·sell-side로 보강해야 한다.
4. `#NAME?` 또는 빈 캐시값이면 → 공시·IR에서 actual 보완 (tier 1).

## inspect_template.py 출력
```
{ "sheets": [...], "period_columns": {...}, "segments": {"type","group_by","members","periods"},
  "is_lines": [{row,label,mnemonic,values}], "cached_values_present": bool }
```

## 3-statement 보존 원칙 (중요)
모델은 sell/buy-side 스타일로 **IS·BS·CF·Ratios를 베이스**로 깐다. Bloomberg 템플릿에 값이 있는 라인아이템은 **하나도 빼지 말고 그대로** `inputs.statements`로 옮긴다.

1. `inspect_template.py` 출력의 `statements_raw`(income_statement/balance_sheet/cash_flow/ratios)를 받아 시작점으로 쓴다. 이건 best-effort 추출이므로 라벨·값·기간 정렬을 검증한다.
2. 각 라인 = `{label, values, [key], [fmt], [bold], [indent], source, tier}`. values는 `meta.periods`에 정렬.
3. **분석 연결용 key 6개는 반드시 태깅**: Revenue, COGS, GrossProfit, OpEx, OperatingProfit, NetIncome. 나머지 라인은 key 없이 그대로 보존.
4. `fmt`: 비율행은 `"pct"`, 배수행(PER/PBR/EV·EBITDA)은 `"x"`. 섹션 소계는 `bold:true`, 하위 항목은 `indent:1~2`.
5. build_model.py가 IS 하단에 GM%·OPM%·YoY·growth-delta 파생행을 자동 추가하고, Segment/Bridge/Dashboard가 이 key들을 참조한다. **Bloomberg 숫자 자체는 절대 수정·삭제하지 않는다.**
