# Data Room Convention & AI Research Input Rules

## Drive 구조

```
Investment Research/                         (루트, folderId 고정 — search_files로 'Investment Research' 검색)
└── [종목명 (티커)]/                          예: "롯데에너지머티리얼즈 (020150)"
    ├── Model/        Bloomberg 템플릿 + 산출 모델·메모
    ├── 리서치/        sell-side PDF
    ├── IR/           IR 자료
    └── AI리서치/      (선택) Gemini/GPT 텍스트·링크
```

## 데이터룸 찾기
1. `search_files` 로 `mimeType = folder and title contains '[종목명]'` 또는 티커로 회사 폴더를 찾는다.
2. 그 폴더의 자식에서 `Model`, `리서치`, `IR`, `AI리서치` 하위 폴더의 folderId를 얻는다 (`parentId = '<회사folderId>'`).
3. `Model/` 에서 `title contains '_Q' and mimeType=xlsx` → 분기 템플릿, `_A` → 연간 템플릿.

## 파일 읽기
- xlsx 템플릿: `download_file_content` 로 base64 받아 로컬 저장 후 openpyxl로 파싱. (대용량이면 결과가 파일로 저장됨 — 그 경로에서 base64 추출.)
- PDF (IR·sell-side): PDF 도구 또는 `read_file_content` 로 텍스트 추출.
- 결과가 토큰 한도를 넘으면 디스크 파일로 저장되니 grep/jq로 필요한 부분만 추출한다.

## 산출물 저장
- `create_file`/`copy_file` 로 `Model/` 폴더에 업로드.
- 파일명: `[티커]_[종목명]_Model_v[YYMMDD].xlsx`, 메모는 `..._Memo_v[YYMMDD].md`.
- 기존 버전은 덮어쓰지 말고 버전 태그로 누적.

## AI 리서치(Gemini/GPT) 입력 규칙
Gemini/GPT 공유 링크는 로그인·JS 렌더링 때문에 자동 fetch가 자주 실패한다. 그리고 사용자가 직접 .txt를 만드는 건 번거롭다. 그래서 **스킬이 빈 구글 Doc을 미리 만들어 주고, 사용자는 거기에 그냥 복붙**하게 한다.

### 스킬이 할 일 (회사 작업 시작 시)
1. `AI리서치/` 폴더가 없으면 만든다 (`create_file`, mimeType `application/vnd.google-apps.folder`, parent=회사 폴더).
2. 빈 구글 Doc을 만든다: `create_file`로 `mimeType='application/vnd.google-apps.document'`, `title='YYYYMMDD_[종목명]_AI리서치'` (또는 주제별로 `YYYYMMDD_[주제]`), parentId=AI리서치 folderId. **본문/형식 제약 없이** 빈 문서면 된다.
3. 사용자에게 그 Doc 링크(`viewUrl`)를 주고 "여기에 GPT/Gemini 내용을 그대로 붙여넣으세요. 형식·파일 변환 필요 없습니다"라고 안내한다.
4. 이후 그 Doc을 `read_file_content`로 읽어 반영한다. (여러 주제면 Doc을 여러 개 만들어도 됨. 사용자가 이미 만든 Doc/txt가 있으면 그것도 읽는다.)

### 반영 규칙 (변하지 않음)
- AI Doc 내용은 전부 `inputs.json`의 `qualitative` 섹션(가설)으로만. **tier 5, 숫자 셀 금지.**
- 단, AI가 1차 소스(공시·IR·뉴스)를 인용했고 그 원문이 확인되면, 그 원문을 출처로 하여 tier 1~3으로 승격(AI 자체는 출처가 아니라 가설).

## 지역별 노트
- **한국 (DART)**: 사업보고서 'II.사업의 내용'에 부문별 매출·생산능력·가동률·수주잔고. 분기보고서 주석에 부문정보. `ir-collertor`·`fnguide-report-downloader` 활용.
- **미국 (SEC EDGAR)**: 10-K/10-Q의 Segment Reporting 주석(ASC 280)에 reportable segment 매출·영업이익, geographic breakdown. MD&A에 backlog.
- **일본 (EDINET/TDnet)**: 有価証券報告書·決算短信의 セグメント情報. `jp-research-collector` 활용. 수주잔고=受注残高.
- **중국 (CNINFO)**: 연보·중보의 分行业/分产品/分地区 매출표.
