# OrdersAPI v1 설치 체크리스트 (데스크톱 1회, 약 7분)

jp_model_portfolio 시트 기준. 기존 Code.gs는 수정하지 않는다(별도 파일 추가).

## 설치

1. **시트 → 확장 프로그램 > Apps Script → 파일 + → 스크립트** `OrdersAPI_v1` 생성 → `OrdersAPI_v1.gs` 내용 전체 붙여넣기 → 저장
2. **doPost 충돌 확인**: 편집기 전체 검색(Ctrl+Shift+F)으로 `doPost` 검색.
   - 기존 Code.gs에 doPost가 **없으면** 그대로 진행 (대시보드는 doGet만 씀 → 충돌 없을 가능성 높음)
   - **있으면**: 새 파일의 `doPost`를 `doPost_ord`로 개명하고, 기존 doPost 최상단에
     `if (e && e.postData) { try { var b=JSON.parse(e.postData.contents); if (b && b.secret) return doPost_ord(e); } catch(err){} }` 추가
3. **배포 > 배포 관리 > 연필(수정) > 액세스: "모든 사용자"** 로 재배포 (버전: 새 버전)
   - 기존 대시보드 doGet도 같은 배포를 쓰므로, 대시보드 URL 노출이 걱정되면 배포를 2개로 분리해도 됨(선택)
4. 편집기에서 함수 선택 → **`ord_setup` 실행** → 권한 승인
   - 효과: 1분 텔레 폴링 트리거 + SECRET 생성 + Drive에 `rootn_jp_port_orders_api.txt` 자동 생성(URL+시크릿) + 텔레 설치완료 알림
5. **확정 파이프라인 연결(권장)**: Code.gs의 `onOpen()`에서 `addItem('★거래 확정', 'XXXX')`의 함수명 확인 →
   편집기 콘솔에서 `ord_setConfirmFn('XXXX')` 1회 실행
   - 이걸 해야 폰 주문이 로그·알림·TWAP대기까지 원샷 처리됨. 미지정 시 행만 기록되고 "확정 대기"로 남음(fail-safe)
   - 주의: 해당 확정 함수가 UI 다이얼로그(현금부족 시 선택창)를 띄우는 경우 트리거 컨텍스트에서 실패할 수 있음 →
     실패 시 자동으로 "확정 대기 + 텔레 경고"로 떨어지므로 안전. 완전 자동화를 원하면 Code.gs 확정 함수에
     headless 분기(UI 불가 시 자동조정 선택)를 추가해야 함 — Code.gs 원본을 클로드에게 주면 패치 만들어 줌
6. **리허설**: 텔레그램 봇 챗에 `주문 6981 +0.1` → 미리보기+토큰 수신 → `취소` 입력(실제 기록 안 함).
   E열 %표기가 이상하면(0.5%가 아니라 50% 등) 클로드에게 보고

## 검증 (설치 직후 1회)

- [ ] 텔레 `상태` → 응답 오는지 (폴링 트리거 작동)
- [ ] `주문 6981 +0.1` → 토큰 수신 → `확인 <토큰>` → 거래입력 행 생성 + E열 0.10% 표기 확인 → 행 삭제(미확정이면 로그에 안 남음) 또는 그대로 두고 ★거래 확정
- [ ] Drive에 `rootn_jp_port_orders_api.txt` 생성 확인
- [ ] (클로드 경로) 아무 클로드 세션에서 "모델포트 주문 테스트 ping" 요청 → 클로드가 curl ping 성공하는지

## API 키 레지스트리 등록 (RootN API Keys 시트에 행 추가 — 폰 Sheets 앱으로 가능)

```
service: JP모델포트 주문API
key_name: webapp url + secret
key_value: (값은 Drive rootn_jp_port_orders_api.txt 참조)
account: (리서치 계정 — 레지스트리 참조)
issued: 2026-08-04
limits: 주문 준비/조회만 가능, 확정은 텔레 토큰 필수
used_by: jp-port-trade 스킬, OrdersAPI_v1.gs
notes: 웹앱 재배포 시 URL 변경 → ord_setup 재실행하면 Drive 파일 자동 갱신
```

## 보안 설계 요약

- 웹앱 액세스 "모든 사용자"지만: SECRET 없이는 어떤 액션도 불가, SECRET이 있어도 **주문 준비/조회만** 가능.
- 실제 거래 기록은 등록된 텔레그램 챗의 **사용자 본인**이 `확인 <토큰>` 회신해야만 실행
  (봇 자신의 메시지는 getUpdates에 안 잡히므로 클로드/외부가 확인을 위조할 수 없음 = 진짜 out-of-band 2FA).
- 토큰 6자리, 10분 만료, 1회용. |Δ| 상한 3%p(Script Property `ORD_MAX_DELTA`로 조정).
