# Analytics Framework — Growth Delta & Bridges

목적: 성장의 **원천**과 **가속**과 **지속성**을 숫자로. 아래 정의를 build_model.py가 Excel 수식으로 깐다.

## 1. Growth & Growth Delta (가속)
- 기간 t 매출 성장률(YoY): `g_t = Rev_t / Rev_{t-4} - 1` (분기) 또는 `Rev_t/Rev_{t-1}-1` (연간).
- **Growth delta (2차 미분, 가속)**: `Δg_t = g_t - g_{t-1}`. 양수면 가속, 음수면 감속.
- Dashboard에 g_t 선과 Δg_t 막대를 같이 둔다. "delta가 커지는가"가 핵심 질문이므로 Δg의 추세가 최상단.

## 2. Revenue Bridge (성장의 원천 분해)
ΔRevenue(YoY) 를 네 효과로 분해. segment i 별로:
- **Volume effect** = (Q_t - Q_{t-1}) × P_{t-1}
- **Price effect** = (P_t - P_{t-1}) × Q_{t-1}   (단, 동일 통화·물량 기준)
- **Mix effect** = segment 구성비 변화 효과 = Σ_i (w_t,i - w_{t-1,i}) × (P_{t-1,i} - P̄_{t-1}) × Q_total ... 실무적으론 잔차로 처리
- **FX effect** = 환율 변동 효과 (해외 매출 × Δ환율)
- 잔차(Residual) = 실제 ΔRev - (위 합). 0에 수렴해야 함. 큰 잔차는 데이터 부족 신호 → 메모에 표기.

물량(Q)·단가(P)가 없으면(흔함): segment 매출만으로 **organic vs mix**만 분해한다.
- Organic = Σ_i Rev_{t-1,i} × g_i (각 segment 자체 성장)
- Mix/구성 = 잔차. 이때 Price/Volume은 "blended"로 라벨.

## 3. Margin Bridge (마진 개선 원천)
ΔGP 분해:
- **Volume/Growth effect** = ΔRev × GM_{t-1}  (작년 마진으로 매출 늘어난 효과)
- **Margin effect** = Rev_t × (GM_t - GM_{t-1})  (마진율 자체 개선)
GM 개선은 다시 (a) mix 개선 (b) 단가-원가 스프레드 (c) 규모의 경제로 정성 분해.

ΔOP 분해:
- GP 효과 + **Opex leverage** = -(Opex_t - Opex_{t-1}). Opex가 매출보다 느리게 늘면 OP마진 개선.
- `OP% = OP/Rev`, `Δ(OP%)` 를 GP마진 기여분과 opex 레버리지 기여분으로 나눔.

## 4. Sustainability (지속성)
후행(P&L)과 선행지표를 나란히:
- **수주잔고(backlog)** YoY, **book-to-bill** = 수주/매출 (>1이면 잔고 증가→미래 매출 우호)
- **수출입 통관 데이터** (월별 물량·금액) — 분기 매출의 선행
- **Capex / 증설 가동 시점** — 미래 capacity
- **가동률(utilization)** — 추가 물량 여력
- **재고/채널 재고** — 수요 둔화 조기 신호

판정 로직(Dashboard에 표기):
- 매출 가속(Δg>0) + 선행지표 동반 상승 → **지속 가능 (green)**
- 매출 가속하나 선행지표 둔화 → **지속성 경고 (red)**: 일시적 가능성
- 매출 감속이나 선행지표 반등 → **저점 통과 후보 (amber)**

## 5. Quality of growth 체크
- 성장이 단가(P)·mix·마진에서 오면 질 높음 (수익성 동반).
- 순수 물량(Q)·저가 밀어내기면 질 낮음 (마진 희석). Revenue bridge × Margin bridge를 교차해서 본다.
