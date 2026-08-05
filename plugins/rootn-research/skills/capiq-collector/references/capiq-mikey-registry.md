# capiq-mikey-registry.md — 티커/회사명 → CapIQ MI KEY 캐시

> **목적**: CapIQ 상단 Search 위젯이 자동화 입력을 완전히 거부하고(값 주입 즉시 리셋),
> 백엔드 omni-search가 gRPC-web(`/apisv3/spg-search/*`)이라 자동 재현 불가하며,
> MFE 소스는 CORS로 못 읽고, 티커형 라우트(`referenceIdentifier=`)도 해석 실패한다
> (근거: capiq-paths.md §9). → **순수 zero-input ticker→MI KEY 해석기는 이 환경에서 구현 불가.**
> 대신 **한 종목당 최초 1회만** MI KEY를 확보해 여기 캐시하면, 이후 그 종목은 입력 0으로 수집된다.
> 이것이 "내 input 최소화" 요구의 견고한 해법이다.

## 신규 종목 MI KEY 확보 프로토콜 (수집기 워크플로우 §2-1에서 호출 — 비차단)
1. **레지스트리 조회 먼저**: 아래 표에 티커/회사명이 있으면 그 MI KEY로 바로 진행(입력 0).
2. **미스여도 멈추지 않는다**(공통규칙 §2 ask-async): 해석되는 종목부터 먼저 다 수집하고,
   미해석분은 **한 목록으로 모아** 결과 보고에 함께 요청 — "해당 종목을 CapIQ에서 연 뒤 주소창 URL을 달라"
   (또는 MI KEY 숫자). URL 예: `.../web/client#company/profile?id=<MIKEY>` → **`id=` 뒤 숫자가 MI KEY**.
   - 사용자는 CapIQ 검색이 정상 동작(사람 입력 허용)하므로 종목을 열어 URL 복사만 하면 된다.
   - 응답이 없으면 그 종목만 스킵·개별 보고하고 나머지·다른 태스크를 계속한다. 하나로 전체를 대기시키지 않는다.
3. **확보 즉시 아래 표에 append**(티커·회사명·MI KEY·SPCIQ·확보일). SSOT push로 영구화.
4. 이후 동일 종목은 1로 해결 → **재입력 불필요**.

> ※ 향후 자동화 후보(미검증, 필요 시 조사): Screener 그리드 API(거래소:티커 필터→ID 반환 가능성),
>   Report Builder 엔티티 피커. 둘 다 REST/JSON일 여지가 있어 omni-search gRPC보다 재현 가능성 높음.
>   현 시점 미구현 — 레지스트리 캐시가 1차 해법.

## 캐시 (확정)
| 티커 | 회사명 | MI KEY | SPCIQ ID | 확보일 |
|---|---|---|---|---|
| TSE:285A | Kioxia Holdings | 14356784 | 605626628 | 2026-07-22 |
| TSE:4443 | Sansan | 5184024 | 78816020 | 2026-07-22 |

## 대기 (MI KEY 미확보 — 사용자 URL/키 1회 필요)
> 티커는 식별 확인 필요분 포함. 일본 건설 테스트 대상.
| 요청 티커/명 | 추정 티커 | MI KEY | 상태 |
|---|---|---|---|
| Taisei | TSE:1801 | — | 대기 |
| Kandenko | TSE:1942 | — | 대기 |
| Kumagai Gumi | TSE:1861 | — | 대기 |
| Penta-Ocean | TSE:1893 | — | 대기 |
| Taikisha | TSE:1979 | — | 대기 |
| Kajima | TSE:1812 | — | 대기 |
| Kraftia | (식별확인) | — | 대기 |
| Dandan | (식별확인) | — | 대기 |
