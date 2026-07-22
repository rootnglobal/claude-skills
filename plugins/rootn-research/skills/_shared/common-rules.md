# RootN 스킬 공통 규칙 (canonical — 이 파일이 유일한 원본)

> 각 스킬 SKILL.md에는 이 규칙을 복제하지 않는다. 워크플로우 첫 스텝에
> "`_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를
> 읽고 전 구간에 적용한다" 한 줄만 둔다. 문구 수정은 반드시 이 파일에서만 한다.

## 1. Fail-fast, never stall
- 소스당 시도 1~2회. 로그인·2FA·CAPTCHA·robots 차단·무응답이면 즉시 포기하고 다음 소스로.
- 같은 동작 3회 반복 금지. 우회를 "조금만 더" 시도하며 머무르지 않는다.
- 실패분은 뭉뚱그리지 않고 개별 보고: 항목·소스·날짜·사유·링크. ("n건 실패" 금지)

## 2. 자동 진행 vs 사전 확인
- 자료 수집·다운로드·드라이브 업로드·폴더 생성은 묻지 않고 바로 진행한다.
- **기본 업로드 정책**: 클로드가 수집하거나 생성한 최종 산출물(수집 자료·노트·모델·문서 등)은 기본적으로 해당 종목/테마 Drive 폴더에도 업로드한다(§9 방법 D로 올리고 §4로 검증). 폴더 구조는 `Investment Research/[종목명 (티커)]/{IR/, 리서치/, Model/}`; 대상이 모호하면 기존 폴더 우선, 없으면 사용자에게 확인. 임시·중간 파일은 업로드 제외.
- 되돌릴 수 없는 작업은 반드시 사전 확인: 드라이브 파일 이동/휴지통, 이메일 발송, 웹폼 제출.
  (이메일은 임시보관함 저장까지, 웹폼은 작성까지가 스킬의 몫이다.)

## 3. 파일명·폴더명
- 산출물 파일명은 ASCII (NFC/NFD 이슈 회피). 한글/일문 표시명이 필요하면 Drive 표시명에서만.
- 드라이브 폴더명: `[종목명 (티커)]` — 한국어 또는 영어만, 일본어 표기 금지.
- 로컬 수집 폴더도 영문/로마자 기본 (예: `sony_6758_2607/`).
- 멀티바이트 기호(×→↑↓÷)가 든 파일은 bash heredoc('EOF')으로 생성하거나 ASCII 대체(x, ->).

## 4. 드라이브 업로드 3점 검증
1. 덮어쓰기 대신 새 파일명(`_v2` 등 suffix).
2. 링크 공유 전 방금 올린 파일의 id·수정시각·용량을 확인.
3. 업로드 후 내용·언어를 재확인.
> `drive_uploader.py`(방법 D)는 업로드 후 size·md5Checksum·수정시각을 자동 대조해 무손실을 확정한다.

## 5. 데이터·출처
- 신뢰 가능한 소스의 숫자는 최대한 끌어온다. 저신뢰 수치도 버리지 않고 "신뢰도 낮음" 표기 후 활용.
- 신뢰도 태그: 별(공시·감사) / 반(실적콜·리포트 2차인용) / 세모(뉴스·추정 = "신뢰도 낮음").
- 읽지 못한 자료는 파일명·위치·실패 사유와 함께 명시적으로 flagging.
- 모든 수치·주장에 출처. 모르면 "확인 필요" — 지어내지 않는다.

## 6. 수집 기간 기본값
- IR·리서치·뉴스 수집은 **최근 2년** (사용자가 달리 지정하지 않는 한).

## 7. 예시 작성 규칙
- 스킬 문서·템플릿의 예시에는 generic placeholder만 사용한다. 실존 종목명·수치 하드코딩 금지.

## 8. 발신자·CC 표준 (아웃리치 계열)
- 자사 발신 계정·CC·서명은 Drive `_config/sender.txt`에서 읽는다(개인 주소를 문서에 직접 기재하지 않는다).
- `_config/sender.txt` 항목: `email`(발신), `cc`(IR 미팅요청·질문지 발송 공통 CC), `name`/`company`(서명).
- 자사 도메인(답변 판정 시 '우리 쪽'): rootnwm.com, rootnglobal.com 전체

## 9. 다운로드/업로드 기술 표준 (collector 계열)
- 런타임에 Chrome download path 확인 (`request_cowork_directory`).
- binary download는 same-origin `fetch → blob` (curl/wget 아님).
- **Drive 업로드는 방법 D(`drive_uploader.py`, Drive API resumable+md5)를 최우선**으로 쓴다. Cowork에 연결된 폴더에 `drive_uploader.py`+`credentials.json`+`token.json` 이 있으면 브라우저 없이 무인 동작. 실행: `py|python3 drive_uploader.py --folder <ID> [--name-suffix _v2] <파일들>` (셋업: ir-collertor `scripts/SETUP_Drive_API_uploader.md`).
  - 커넥터 `create_file` 은 소용량(≲50KB)만 인라인 base64로 쓰고 반드시 fileSize 대조. `file_upload`(Chrome)는 Google Drive가 HTML `<input type=file>` 을 안 열어 **부적합**.
- EDINET은 API v2 + `Investment Research/_config/edinet_api.txt` 구독키.

## 10. Self-review 위치
- self-review 섹션은 마지막 워크플로우 스텝 바로 뒤에 둔다 (문서 말미 원칙 블록보다 앞).

## 11. 판정 근거의 검증 가능성 (분석·판정 계열 스킬 공통)
- **노출은 절대치 단독 금지**: 테마 노출은 자산/매출/이익 비중 %와 단위 민감도 %(가격변수 1단위당 순이익 영향)로 정규화해 제시하고, 절대치는 산출 근거로만 병기한다. 개수 기준 %(척수·건수·점포수)는 자산 크기(용량)·시장 구분·계약 부착을 모두 무시하므로 단독으로 판정하지 않는다.
- **계약구조 레이어 (스팟 vs 장기)**: 자산이 있어도 장기계약(COA·기간용선·CVC·장기공급 등)이 부착되어 있으면 시황 수혜는 0에 수렴한다. 회사 공시 익스포저(시황:안정 비율, 익스포저 자산수/일수)를 최우선으로 하고, 해외 종목은 현지어 IR 원문 검색을 포함한다. 미공시면 추정 후 "신뢰도 낮음" 표기.
- **노출 크기보다 구성**: 노출 %가 비슷해도 최대 이익원이 테마와 무관하거나 역행(드래그 자산)하면 판정이 갈린다. 이익 비중 상위 1~2개 사업이 테마의 순풍/무풍/역풍 중 어디인지 한 줄로 명기한다.
- **다축 테마는 축별 분리**: 테마가 복수의 가격축이면 노출표를 축별로 따로 만든다 — 같은 회사가 축에 따라 순위가 뒤집힌다. thesis(어느 가격에 베팅하는가)를 먼저 정의한다.
- **시황 방향 사전 검증**: 판정 근거로 시황 방향을 쓰기 전에 스크리닝 시점의 최신 스팟 데이터(주간 지수, 연속 상승/하락 주수, 컨센서스 리비전)를 검색·확인한다. '구조 전망'(공급 사이클, 수년)과 '현재 delta'(스팟 방향, 주·월)는 별도 축으로 분리 표기하고, 구조 프레임만으로 단정하지 않는다. 두 축이 상충하면 상충 사실 자체를 명시한다.
- **수치 최신성**: 노출의 분자(선대·캐파·점포수 등)는 M&A·연결범위 변경으로 급변한다. 셀사이드 수치를 쓰기 전 최신 공시 원문과 대조하고, 6개월 이상 지난 수치는 기준일을 명기한다.

## 12. 태스크 완료 후 스킬 피드백 루프
- 태스크의 최종 산출물을 전달한 직후(매 turn이 아니라 태스크 단위 1회), 이번 실행에서 사용한 스킬에 반영할 개선점이 있는지 검토한다.
- 검토 대상: 새로 확인된 소스·URL·기술적 우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분.
- 개선점이 있으면 업로드본 SKILL.md를 즉석 수정한다. 단 동일 diff를 SSOT repo(`claude-skills/`)에도 반영해야 하며, repo가 마운트되지 않은 환경이면 diff를 별도 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging한다.
- 개선점이 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.

## 13. 대용량 Drive 파일 처리 (커넥터 응답 폭증 대응)
- **토큰 초과로 파일 저장된 응답은 재시도 금지.** `read_file_content`/`search_files` 결과가 커서 파일로 떨어지면, 같은 호출을 다시 하지 말고 bash `python3`로 그 JSON의 `fileContent`(또는 결과 배열)를 슬라이스해 청크 단위로 읽는다. 예: `python3 -c "import json; d=json.load(open(P)); print(d['fileContent'][A:B])"`.
- **폴더구조·title 탐색은 `search_files`에 `excludeContentSnippets:true`.** 콘텐츠 스니펫이 응답을 폭증시켜 토큰 초과를 유발한다. 스니펫은 본문 검색(fullText)이 목적일 때만 켠다.
- **docx는 .docx 원형을 유지해 올린다**: `base64Content` + `contentMimeType`=`application/vnd.openxmlformats-officedocument.wordprocessingml.document` + `disableConversionToGoogleType:true`. (생략하면 Google Docs로 변환돼 서식이 깨진다.) 업로드 후 §4대로 id·수정시각·용량 3점 검증.
- **soffice로 렌더한 미리보기 이미지는 Windows outputs 경로로 Read한다.** `/sessions/...`(기기 마운트) 경로는 Read 툴로 못 읽으므로, device로 commit된 사용자 디스크 outputs 경로를 지정해 읽는다.
