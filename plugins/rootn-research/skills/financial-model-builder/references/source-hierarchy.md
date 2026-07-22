# Source Hierarchy & Citation Rules

모든 숫자는 출처가 있어야 하고, 출처마다 신뢰 등급(tier)이 있다. 이 등급이 충돌을 해결하고, AI 환각이 모델에 스며드는 것을 막는다.

## Tier 정의

| tier | 출처 | 모델 사용 |
|------|------|-----------|
| 1 | 회사 공시·IR (사업보고서, 분기보고서, 실적발표 IR deck, 10-K/Q, 유가증권보고서) | 하드 넘버 ✅ — 최우선 |
| 2 | Bloomberg actual (캐시된 BDH 실적값), 거래소·통관 통계 | 하드 넘버 ✅ |
| 3 | Sell-side estimate (증권사 리포트의 추정·가정) | 추정/가정 셀에만, 출처 명시 ⚠️ |
| 4 | 뉴스·웹서치 | 보조·정성 ⚠️, 항상 1차 출처로 역추적 |
| 5 | Gemini·GPT 리서치 | 가설 전용 🚫 (하드 넘버 금지) |

## 핵심 규칙

1. **하드 넘버(historicals, segment actual, 실제 마진)는 tier 1~2에서만.** sell-side 추정을 actual 자리에 넣지 않는다.
2. **추정/forecast 셀**은 tier 3까지 허용하되 `source`에 어느 증권사·날짜인지 명시한다.
3. **tier 5(Gemini/GPT)는 절대 숫자 셀에 들어가지 않는다.** 가설(Qualitative) 탭에만 기록한다. 단, AI가 1차 소스를 직접 인용했고 그 1차 소스를 확인했다면, 그 1차 소스를 출처로 하여 tier 1~2로 승격한다 (AI는 출처가 아님).
4. **충돌 시 낮은 tier 숫자 우선.** 공시 ≠ Bloomberg 면 공시를 쓰고 차이를 Assumptions에 메모한다.
5. **출처 없는 셀은 0개여야 한다.** build_model.py와 검증 단계가 이를 체크한다.

## 인용 형식

`inputs.json`의 모든 수치 항목은 다음을 갖는다:
- `value`: 숫자
- `source`: 사람이 읽는 출처 문자열 (예: "2025 4Q IR p.12", "Mitsui MS 2026-05-13 p.4", "DART 분기보고서 2026.03 주석27")
- `tier`: 1~5

build_model.py는 이 정보를 Assumptions & Sources 탭에 그대로 적고, 해당 데이터 셀에 코멘트로 붙인다. 그래서 모델의 어떤 숫자든 클릭하면 출처를 즉시 알 수 있다.
