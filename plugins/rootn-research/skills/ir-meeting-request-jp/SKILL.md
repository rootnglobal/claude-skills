---
name: ir-meeting-request-jp
version: 260721
description: "일본 상장사에 IR(투자자관계) 미팅을 요청하는 영문+일문 병기 이메일을 자동으로 작성하고 Gmail 임시보관함에 저장하는 스킬. 일본 회사명이나 4자리 종목코드(예: 7203, 6758)를 입력하면 IR 담당자 이메일을 웹에서 검색하고, 정해진 템플릿에 맞춰 미팅 요청 이메일 초안을 Gmail에 저장한다. '일본 IR 미팅 요청', '일본 회사 미팅', 'JP IR meeting', '일본 기업탐방', 일본 4자리 종목코드(예: 7203T, 6758T)와 함께 IR/미팅 요청 맥락이 나오면 이 스킬을 사용할 것. 여러 회사를 한꺼번에 요청하는 경우에도 각각에 대해 이 스킬의 워크플로우를 반복 적용할 것."
---

# 일본 상장사 IR 미팅 요청 이메일 자동 작성 스킬

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.

 
## 개요
 
이 스킬은 RootNGlobal Investors가 일본 상장사 IR 담당자에게 미팅을 요청하는 이메일을 자동으로 작성하고 Gmail 임시보관함에 저장한다. 이메일은 영어와 일본어를 병기하여, 영문 IR 담당자와 일본어만 사용하는 담당자 모두 읽을 수 있도록 한다.
 
## 워크플로우
 
### Step 1: 회사 식별 및 IR 연락처 찾기
 
사용자가 일본 회사명(한국어, 영어, 일본어 모두 가능) 또는 4자리 종목코드를 제공하면, 먼저 해당 회사의 정식 영문명과 일본어명을 확인한 뒤 IR 담당 이메일을 검색한다.
 
**회사명 확인:**
- 종목코드가 주어진 경우: 웹 검색으로 해당 종목코드의 회사명(영문 + 일본어)을 확인
- 한국어 회사명이 주어진 경우: 정식 영문명과 일본어명을 웹 검색으로 확인
- 사용자가 "T"를 붙이는 경우(예: 7203T)는 도쿄증권거래소 종목을 의미하며, 숫자 부분만 종목코드로 사용
 
**IR 이메일 검색 전략** (순서대로 시도, 앞 단계에서 찾으면 이후 단계는 건너뛴다):
 
1. **웹 검색**: `"{회사명 영문} IR contact email"` 또는 `"{회사명 일본어} IR お問い合わせ メール"` 로 검색
2. **회사 공식 홈페이지**: IR 페이지를 WebFetch로 확인. 일본 기업의 IR 페이지는 보통 다음 경로에 있다:
   - `/ir/`, `/investor/`, `/en/ir/` (영문 IR 페이지)
   - `/ir/contact/`, `/ir/inquiry/` (IR 문의 페이지)
3. **JPX(일본거래소그룹)**: `www.jpx.co.jp` 에서 해당 종목의 기업정보 확인
4. **株探(Kabutan)**: `kabutan.jp/stock/?code={종목코드}` — 기업 개요에 연락처가 있을 수 있다
5. **EDINET/TDnet (최후 수단)**: 위 1~4에서 찾지 못한 경우, EDINET(금융청 전자공시)에서 유가증권보고서(有価証券報告書)를 검색한다. 보고서의 "企業の概況" 섹션에 IR 담당 연락처가 기재되어 있는 경우가 있다.
   - 검색 방법: `"site:disclosure.edinet-fsa.go.jp {회사명}"` 또는 `"{회사명} 有価証券報告書 IR 連絡先"` 로 웹 검색
 
**이메일을 끝까지 찾지 못한 경우:**
- 대표 이메일(info@, contact@ 등)이나 IR 문의 폼 URL을 대안으로 제시하되, IR 전담 이메일이 아님을 명확히 알린다.
- 어떤 이메일도 찾지 못하면 사용자에게 직접 이메일 주소를 요청한다.
- 찾은 이메일의 출처를 항상 함께 보고한다.
 
### Step 2: 이메일 작성
 
아래 템플릿을 사용하여 이메일을 작성한다. `{Company Name (English)}` 과 `{会社名}` 부분만 실제 회사명으로 교체한다. 나머지 문구는 그대로 유지한다 — 이것은 RootNGlobal의 표준 일본 IR 요청 양식이므로 임의로 변경하지 않는 것이 중요하다.
 
**제목:** `IRミーティングのご依頼 / IR Meeting Request – RootNGlobal Investors`
 
**본문:**
```
{会社名} IR担当者様
 
拝啓 時下ますますご清栄のこととお慶び申し上げます。
 
私どもRootNGlobal Investorsは、長期的なバリュー投資を志向するロングオンリーの株式運用会社でございます（会社紹介：http://www.rootnglobal.com/eng/sub1_1.jsp）。
 
現在、{会社名}様の主要事業の現況および中長期的な成長戦略について、より深い理解を得た上で投資検討を進めたく、IRミーティングをお願いしたくご連絡差し上げました。
 
ミーティングの形式（対面またはオンライン）および日程につきましては、貴社のご都合に合わせて柔軟に調整させていただきます。ご都合のよろしい日時をいくつかご提案いただけましたら、速やかにご返信いたします。
 
事前にご質問票や追加資料が必要でございましたら、お気軽にお申し付けください。
お忙しい中ご検討いただき、誠にありがとうございます。ご返信をお待ちしております。
 
敬具
RootNGlobal Investors
 
---
 
Dear IR Team of {Company Name (English)},
 
We are RootNGlobal Investors, a long-only equity asset manager focused on long-term value investing (about us: http://www.rootnglobal.com/eng/sub1_1.jsp).
 
We are currently conducting investment research on {Company Name (English)} and would greatly appreciate the opportunity to have an IR meeting to gain a deeper understanding of your business operations and mid-to-long-term growth strategy.
 
We are flexible regarding the meeting format (in-person or online) and scheduling. If you could kindly suggest a few available dates and times, we will promptly confirm.
 
Should you require a questionnaire or any additional materials in advance, please do not hesitate to let us know.
 
Thank you very much for your time and consideration. We look forward to hearing from you.
 
Best regards,
RootNGlobal Investors
```
 
### Step 3: Gmail 임시보관함에 저장
 
`gmail_create_draft` 도구를 사용하여 다음과 같이 저장한다:
 
- **to**: Step 1에서 찾은 IR 담당 이메일 주소
- **cc**: common-rules §8의 CC 표준(= Drive `_config/sender.txt`의 `cc` 값, 항상 고정) — 개인 주소를 문서에 직접 기재하지 않는다
- **subject**: `IRミーティングのご依頼 / IR Meeting Request – RootNGlobal Investors`
- **body**: Step 2에서 작성한 본문
 
### Step 4: 결과 보고
 
완료 후 사용자에게 다음을 보고한다:
- 회사의 정식 영문명 / 일본어명
- 수신인 이메일 주소와 출처
- CC 수신인
- Gmail 임시보관함 링크
- 발송 전 확인 요청 안내

---

## IR 미팅 확정 답장 가이드라인

상대방이 가능한 일정을 제안해오면, 사용자가 일정을 확정해달라고 요청할 때 아래 사항을 반드시 포함한다.

### 필수 포함 내용

1. **질문지 사전 발송 안내**: 미팅 1-2일 전에 질문 목록을 미리 공유할 예정임을 알린다.
   > "We typically prepare a list of questions and share them with you 1-2 days prior to the meeting."

2. **통역 필요 여부 확인**: 상대방 이메일에 통역(interpreter) 언급이 없는 경우, 우리 쪽에서 준비해야 하는지 질문한다.
   > "Could you also let us know whether an interpreter will be needed, so we can prepare accordingly?"
   
   단, 상대방이 이미 통역 관련 언급을 했거나(예: "speakers will be Japanese speakers, please arrange interpreter on your side"), 우리 쪽에서 준비한다고 이미 확정된 경우에는 생략하고 그에 맞게 대응한다.

3. **미팅 링크**: 상대방 이메일에 Zoom/Teams 등 미팅 링크나 "링크를 보내겠다"는 언급이 없는 경우, 우리 쪽에서 Google Meet 링크를 보내도 괜찮은지 제안한다.
   > "If it is convenient, we can send a Google Meet link from our side — please let us know if that works for you."
   
   단, 상대방이 이미 "Zoom meeting을 arrange하겠다" 등 언급한 경우에는 생략한다.

### 답장 언어 규칙

상대방이 보내온 이메일의 언어에 맞춰 답장을 작성한다.

- **일본어로 온 메일**: 일본어 + 영어 병기로 답장 (일본어 먼저, 구분선 후 영어)
- **영어로 온 메일**: 영어로만 답장
- **한국어로 온 메일**: 한국어로만 답장 (해당 없는 경우가 대부분)

일본어 병기 시 경어(丁寧語/敬語)를 사용하고, 상대방 담당자명(예: 小林様)을 첫 줄에 명시한다.
상대방 이메일에 CC가 있었다면 답장 CC에도 동일하게 포함한다.

### CC 기본값
확정 답장에도 동일하게 CC(common-rules §8 = `_config/sender.txt`의 `cc`)를 포함.

---
 
## 여러 회사를 한꺼번에 처리하는 경우
 
사용자가 여러 회사를 한꺼번에 요청하면, 각 회사에 대해 Step 1~4를 반복한다. 가능하면 IR 연락처 검색을 병렬로 진행하여 시간을 절약한다.
 
## 주의사항
 
- 이메일 본문 템플릿은 회사명 외에는 절대 변경하지 않는다. 이것은 RootNGlobal의 공식 일본 IR 요청 양식이다.
- 일본 기업의 IR 이메일은 보통 ir@, investor-relations@, kabushiki@ 등의 형태이다. 개인 이메일이 아닌 공식 IR용 이메일을 우선한다.
- 영문 회사명은 회사 공식 영문 표기를 사용한다 (예: "Toyota Motor Corporation", "Sony Group Corporation").
- 일본어 회사명은 정식 상호를 사용한다 (예: "トヨタ自動車株式会社" → "トヨタ自動車" 로 株式会社는 생략 가능).
- 종목코드에 "T" 접미사가 붙어있으면 도쿄증권거래소 종목이며, 숫자 부분만 사용한다.