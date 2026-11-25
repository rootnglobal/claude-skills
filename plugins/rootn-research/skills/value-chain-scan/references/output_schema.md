# 산출 스키마 (vcs_{코드}_YYMMDD.xlsx)

모든 시트 1행 헤더, 국문. 회사명은 영문 + 원어 병기.
시트 순서: Summary, Entities, Claims, Factors, Trackers, Data_* (선택), Events, Glossary, IR_Questions, Sources, Errors, BBG_Requests.

## Summary
스냅샷(기준일·주가·컨센·다음 이벤트) / Top 5 신규 요인(factor_id) / 흔들리는 주장(claim_id) / 추적 추천 Top 3 / 결론이 틀릴 가장 큰 이유 1줄.

## Entities
entity_id | entity_en | entity_local(원어) | country | ticker | exchange | role(customer / end-customer / competitor / supplier / landlord / vendor / end-market) | product_key | 관계 근거(source_id) | 근거등급 | 점유율·매출비중(출처·연도) | 비고
- 근거 C이고 영향이 없는 잠재 경쟁사 행은 넣지 않는다.

## Claims (경영진 주장 + 외부 분석 주장)
claim_id | 주장 요약 | 출처(문서·일자·페이지) | 반증 유형(D1~D10) | 지지 증거(source_id) | 반증 증거(source_id) | 판정(intact / under pressure / broken / unverifiable) | 근거등급 | 메모
- 외부 분석(다른 LLM·브로커) 주장은 `X01` 형식 ID, 판정은 확인 / 수정 / 미확인 / 보완.

## Factors (업·다운 요인)
factor_id | 방향(+/−) | 유형 코드(D·X·U) | 내용 | 연결 세그먼트(비중) | 근거(source_id 목록) | 근거등급 | 신규성(IR / 셀사이드 / 미인지 / 미인지(공개 자료)) | severity(Critical / High / Medium / Watch) | 확률(낮음·중간·높음 + 근거) | 매출 영향 범위 % | OP 영향 범위 % | EPS 영향(세율·주식수) | 지역 분리 영향(예: 국가A / 국가A 외) | 기간(12M / 24M) | time-to-impact | tail(Y/N) | 반증 조건 | 반대검증 결과(전→후·사유) | 다음 확인 시점 | 상태(new / confirmed / refuted / stale)

## Trackers
tracker_spec.md의 필드 그대로.

## Data_{주제} (선택)
리드-래그 근거 시트. 원자료(월별, 출처·조회일) → 분기 집계(SUMIFS) → YoY → lag 0/1/2 상관(CORREL)·전환점 일치율. 대용량이면 수식이 참조하는 범위만 두고 원자료 파일 위치를 적는다.

## Events
날짜 | 이벤트(자체·고객·경쟁사 실적, 정책 시행 등) | 긍정 신호(임계) | 부정 신호(임계) | 연결 factor_id / claim_id | 결과(refresh 때 기입)

## Glossary
product_key | ja | zh_cn | zh_tw | ko | en | 비고

## Sources
source_id | 제목 | 발행처 | URL | 게시일 | 이벤트일 | 언어 | 페이지·문단 | 접근일 | 근거등급 | 독립성 그룹
- 신규성 판정용으로만 쓴 셀사이드·내부 문서는 묶어서 1~2행으로 둔다.

## Errors
항목 | 소스 | URL | 날짜 | 사유(로그인·CAPTCHA·무응답·차단·없음·429/403) | 대안 경로

## IR_Questions
번호 | 질문 후보(경영진만 답할 수 있는 것, 한 문항 한 질문) | 연결 factor_id / claim_id | 기존 질문지 중복(Y/N)
- 기존 질문지와 중복되는 것은 넣지 않는다(중복 여부만 확인용으로 표시).

## BBG_Requests
종목 | 대상 엔티티 | 화면·필드(예: SPLC, transcript, 실적 예정일, 동종주 Px, Curncy 월평균) | 기간 | 용도

## 롤업 (vcs_rollup_YYMMDD.xlsx)
- Matrix: 종목 × (High 이상 요인 수, Critical, tail, 주요 요인 한 줄)
- CommonExposure: 공통 고객·end market·국가·투입재 → 걸린 종목들
- TopFactors: 전 종목 High 이상 요인
- TrackerRank: 추적 후보 통합 순위(공통성·severity·자동화 가능성)
- Progress: 종목·상태(완료/미완료)·사유·산출물 위치
- Changes: 이전 롤업 대비 변화

## 업로드 폴백 (공통 규칙 §9 경로를 쓸 수 없는 세션)
방법 D(drive_uploader)도, 커넥터 create_file 파일 참조(`sha256:<hex>:<절대경로>`)도 쓸 수 없을 때만 적용한다.
- (a) 보고서: 인라인 스타일을 뺀 HTML을 Drive create_file(contentMimeType=text/html)로 올려 Google Doc으로 변환한다.
- (b) xlsx: create_file로 빈 Google Sheet를 만들고, update_spreadsheet(addSheet)로 탭을 만든 뒤 update_values로 시트별 값·수식을 쓴다(USER_ENTERED). `=`로 시작하면 수식, 앞 apostrophe는 텍스트 — `+`·`-`로 시작하는 문자열과 `YYYY-MM` 문자열에는 apostrophe를 붙인다(안 붙이면 수식·날짜로 바뀌어 값이 틀어진다).
- (c) 수식 셀 2~3개를 get_spreadsheet로 읽어 원본 xlsx 계산값과 대조한다.
- (d) 대용량 원자료 탭은 수식이 참조하는 행만 올리고 탭 안에 '전체 원자료는 채팅 xlsx'라고 적는다.
- (e) 원본 .xlsx·.docx는 채팅 파일로도 함께 전달하고, Drive 원형 업로드는 미완료로 보고한다.
- 인라인 base64를 모델이 직접 전사하지 않는다(공통 규칙 §9 — 30KB 이상에서 전사 오류 실측).
