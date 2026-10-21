---
name: ir-webform
version: 261021b
description: "한·일·중·미 상장사 IR 문의 웹폼을 찾아 Claude in Chrome으로 IR 미팅 요청을 작성·제출하는 스킬(확인 화면 대조 후 기본 제출). 공개 IR 이메일이 없고 웹폼만 있으면 되묻지 말고 바로 실행. 트리거: 웹폼, 폼 작성, 문의 양식, 컨택 폼, contact form, IR 문의, 투자자 문의."
---

# IR 웹폼 자동 작성 스킬

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 SSOT repo(claude-skills-2)의 SKILL.md를 수정한다(설치본·업로드본 수정 금지; repo 접근 불가 세션이면 수정 지시 txt를 Drive `Skill/` 폴더에 남긴다). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


## 개요

이 스킬은 한국/일본/중국/미국 상장사의 IR 문의 웹폼을 Claude in Chrome으로 자동으로 찾아 채워준다.
직접 이메일 주소를 찾지 못한 경우나 회사가 웹폼 기반 문의만 지원하는 경우에 사용한다.

**공개된 IR 이메일이 없고 회사가 웹 문의 폼만 운영하는 경우, 사용자에게 "웹폼으로 진행할까요?"라고 되묻지 말고 곧바로 이 스킬을 실행해 웹폼을 채운다.** IR 미팅 요청 웹폼은 **기본 제출**한다(submit-by-default): 확인 화면(確認)이 있으면 그 내용을 입력값과 대조한 뒤 送信하고, 없으면 전 필드 스크린샷 재검증 후 제출한다(공통 규칙 §2의 IR outreach 웹폼 예외). 사용자가 "작성만"을 지시했으면 제출하지 않는다.

---

## 발신자 고정 정보

웹폼 필드(이름/연락처/이메일/소속)는 Drive `Investment Research/_config/sender.txt`의 값을 읽어 사용한다.
파일을 읽지 못하면 사용자에게 값을 직접 요청한다 — **개인 연락처를 이 문서에 하드코딩하지 않는다** (공통 규칙 §8).

---

## 워크플로우

### Step 0: 진입 판단 (되묻지 않기)

다음 조건 중 하나라도 해당하면 **사용자에게 추가 확인 질문을 하지 말고 곧바로 Step 1로 진행**한다:

- 공개된 IR 이메일 주소를 찾지 못한 경우
- 회사가 이메일 없이 웹 문의 폼만 운영하는 경우

즉, "공개 이메일이 없는데 웹폼으로 진행할까요?" 같은 확인 질문은 생략한다. 폼을 찾는 즉시 작성에 들어간다.
(작성에 이어 제출까지 기본 진행한다 — 확인 화면 대조 후 送信. 개요 참조.)

### Step 1: IR 문의 웹폼 URL 찾기

사용자가 URL을 직접 제공했으면 바로 Step 2로 이동.
그렇지 않으면 아래 순서로 폼 URL을 찾는다:

1. **웹 검색**: `"{회사명} IR 문의 contact form investor relations"` 검색
2. **회사 공식 홈페이지**: `/ir`, `/investor-relations`, `/contact`, `/inquiry` 경로 탐색
3. **Claude in Chrome으로 직접 탐색**: 홈페이지에서 IR/Contact 메뉴를 따라 이동

국가별 일반적인 경로:
- 한국: `/ir` 또는 고객 서비스 > 문의하기
- 일본: `/ir/contact`, `/ir/inquiry`, `/ir/meeting`
- 미국: `/investor-relations/contact`, `/ir/contact-us`
- 중국: `/ir/contact`, `/investor-relations`

### Step 1.5: 침묵기간(quiet period) 체크

IR 캘린더(IR 일정·決算発表予定日·earnings date)에서 **다음 결산발표일**을 확인한다. 오늘이 **분기말 다음 날 ~ 발표일** 사이면 본문 말미(맺음말 앞)에 아래 '선택 문장'의 침묵기간 문장을 1개 넣는다(`MM/DD` = 발표일). 발표일을 못 찾으면 넣지 않고 보고에 "발표일 미확인" 1줄.

### Step 2: 폼 언어 및 필드 파악

`mcp__Claude_in_Chrome__navigate`로 해당 URL에 접근한 뒤 `get_page_text`로 페이지 내용을 확인해 다음을 파악한다:

- 폼이 존재하는가? (없으면 사용자에게 알리고 종료)
- 어떤 언어로 작성되어 있는가? (한국어 / 영어 / 일본어 / 중국어)
- 어떤 필드가 있는가? (이름, 이메일, 연락처, 회사명, 문의 유형, 제목, 내용 등)
- 문의 유형 드롭다운이 있는가? → "IR" 또는 "투자자" 관련 옵션 선택. **개인/기관 구분이 있으면(예: 個人投資家 vs アナリスト・機関投資家) RootN은 기관투자자이므로 '아날리스트·기관투자자' 계열을 선택한다.**

**임베디드(cross-origin) 마케팅 폼 처리 — 핵심 우회법**: IR 폼이 Pardot/SATORI 등 마케팅 플랫폼 iframe(예: `go.{회사도메인}` 같은 별도 서브도메인/도메인)으로 삽입된 경우, 부모 페이지에서는 필드가 cross-origin이라 `form_input`·`javascript_tool`로 접근되지 않고 `read_page`/`find`도 필드를 온전히 못 잡으며 native `<select>` 옵션은 좌표 스크린샷으로도 안 보인다. 이때는:
1. 부모 DOM에서 `document.querySelectorAll('iframe')`의 `.src`로 폼 iframe URL을 확인한다.
2. 그 **`src` URL을 새 탭(또는 같은 탭)에서 직접 열어** top-level로 렌더한다 — 그러면 same-origin이 되어 JS로 필드 조작이 가능하다.
3. `javascript_tool`로 `input,textarea,select`를 열거하고 `label[for=id]`로 라벨을 매핑해 각 필드의 name/id를 파악한다(필드 name이 `<siteid>_<fieldid>pi_...` 형태로 난독화되어 있어 라벨 매핑이 필수).
4. 값 설정 후 **반드시 `input`·`change`·`blur` 이벤트를 dispatch**해야 마케팅 플랫폼 검증이 입력을 인식한다(값만 대입하면 검증 실패로 제출이 막힌다).
5. 제출도 이 top-level 폼에서 (사용자가) 하면 동일 엔드포인트로 전송되므로 임베드 페이지로 되돌아갈 필요가 없다.

### Step 3: 발신자 정보 필드 채우기

`mcp__Claude_in_Chrome__form_input` 또는 `find` + `computer(left_click)` + `computer(type)` 조합으로 각 필드를 채운다. (cross-origin 임베드 폼은 Step 2의 top-level 우회 후 `javascript_tool`로 채운다.)

필드 매핑:

| 한국어 | 영어 | 일본어 | 중국어 | 입력값 |
|--------|------|--------|--------|-------|
| 이름/성명 | Name | お名前/氏名 | 姓名 | sender.txt `name_kr` (한국폼) / `name_en` (기타). 姓/名 분리 폼이면 `name_en`을 성(family)/명(given)으로 나눠 입력 |
| 이메일 | Email | メールアドレス | 电子邮件 | sender.txt `email` |
| 연락처/전화 | Phone/Tel | 電話番号 | 电话 | sender.txt `phone`. 해외 회사 폼은 국가코드 포함(+82 형식, 앞자리 0 제거) |
| 회사명 | Company | 会社名 | 公司名称 | sender.txt `company` |
| 부서 | Department | 部署名 | 部门 | `Research` (선택 필드면 채우고, 없으면 생략) |
| 문의 유형 | Inquiry Type | お問い合わせ種別 | 询问类型 | IR/기관투자자 관련 옵션 선택 |

**입력 순서·재검증**: 자유서술(문의 본문·Inquiry/message) textarea는 **맨 마지막에** 입력하고, 입력 직후 **전 필드를 스크린샷으로 1회 재검증**한다. 긴 textarea는 `form_input`이 타임아웃될 수 있고, 이때 확장 재연결로 폼이 초기화되면 앞서 채운 값이 날아간다 — 재검증에서 빈 필드가 보이면 다시 채운다.

### Step 4: 제목 및 내용 작성

`{회사명}` 부분만 실제 회사명으로 교체하여 아래 국가별 템플릿을 그대로 사용한다. 이름·서명은 sender.txt `name_kr`(한국 템플릿)·`name_en`(그 외)으로 채운다.

**언어 규칙**: 본문은 **대상 회사 언어 + 영어** 병기(일본 = 일본어 + 영어, 중국 = 중국어 + 영어). 한국은 국문 단독, 미국은 영어 단독. 폼에 글자수/바이트 제한이 있으면 영어 파트를 삭제한다(아래 '국가별 콘텐츠 템플릿' 상단 전역 규칙).

**형식·일정 제약 반영(중요)**: 사용자가 미팅 형식(온라인/대면)이나 일정(특정 월·요일·시간대)을 **명시**했으면, 템플릿의 '형식·일정 유연' 문장만 그 제약으로 **정밀 교체**하고 나머지 문구는 유지한다. 예: 온라인 전용 + 10월 오후 13:30~16:30 → 해당 문장을 "온라인(화상)만 희망 / 10월 평일 오후 13:30~16:30 후보 요청"으로 바꾼다. **일본↔한국은 동일 시간대(UTC+9)라 KST/JST 변환 불필요**(그 사실을 본문에 '일본시간, 한국시간과 동일'로 명기하면 오해가 없다). 미국·중국 등 시차가 있는 국가는 상대국 현지시간으로 환산해 병기한다.

**제목(Subject) 병기 원칙:** 비영어권 회사(일본·중국 등)의 제목은 본문과 마찬가지로 **대상 회사의 언어 / 영어** 병기로 작성한다(예: 일본어 `IRミーティングのご依頼 / IR Meeting Request (...)`). 발신·수신이 같은 언어권인 한국(국문 단독) 및 영어권인 미국(영어 단독)은 단일 언어 제목을 그대로 사용한다.

---

## 국가별 콘텐츠 템플릿

**전역 규칙 — 글자수/바이트 제한 폼**
- 폼에 글자수/바이트 제한이 있어 병기 전문이 안 들어가면, 영문 병기를 생략하고 **대상국 언어(현지어) 단독**으로 작성한다.
- 주의: 일부 일본 폼 벤더(req.qubo.jp 등)는 "N文字 이하" 표기지만 실제로는 UTF-8 바이트에 가깝게 카운트한다 → 일본어는 3바이트/자라 빨리 초과한다. 현지어 단독 + 핵심만으로 **~950바이트 이내**를 타깃으로 한다(아래 일본 압축본). 입력 전 `len(text.encode('utf-8'))`로 확인.

**선택 문장 (해당 시에만 본문 맺음말 앞에 삽입, 병기 본문이면 언어별로 각각)**

| 조건 | 일본어 | 한국어 | 영어 | 중국어 |
|---|---|---|---|---|
| 침묵기간(Step 1.5) | 決算発表（MM/DD）以降の日程でご調整いただけますと幸いです。 | 결산 발표(MM/DD) 이후 일정으로 조율해 주시면 감사하겠습니다. | We would be glad to schedule the meeting after your earnings announcement on MM/DD. | 会议时间可安排在贵司业绩公告（MM/DD）之后。 |
| CC 불가 폼 | ご返信の際は {sender.txt cc} もCCに加えていただけますと幸いです。 | 회신 시 {sender.txt cc}도 참조(CC)로 넣어 주시면 감사하겠습니다. | When replying, please also copy {sender.txt cc}. | 回复时烦请同时抄送 {sender.txt cc}。 |

`{sender.txt cc}`는 `_config/sender.txt`의 `cc` 값으로 런타임에 채운다(문서에 주소를 적지 않는다).

### 한국 (Korean)

**제목:** `IR 미팅 요청의 건 (RootNGlobal Investors)`

**내용:**
```
안녕하십니까, {회사명} IR 담당자님.

RootNGlobal Investors는 10년 이상 글로벌 주식 운용 트랙레코드를 보유한 상장 주식 롱온리 자산운용사로, 2~3년 이상 장기 보유를 지향하는 가치 투자를 하고 있습니다(당사 소개: http://www.rootnglobal.com/kor/sub1_1.jsp). 현재 {회사명}의 주요 사업 현황과 중장기 성장 전략에 대한 보다 심도 있는 이해를 바탕으로 투자 검토를 진행하고자 IR 미팅을 요청드리고자 합니다.

미팅 방식(대면 또는 비대면) 및 일정은 귀사의 편의에 맞추어 유연하게 조율하고자 합니다. 가능하신 일시를 몇 가지 제안해 주시면 확인 후 신속히 회신드리겠습니다. 온라인 미팅이 어려우시면 질문지를 이메일로 보내 서면으로 답변 받는 형식도 괜찮습니다.

아울러 사전에 전달드려야 할 질의서나 추가 자료가 필요하시면 편히 말씀 부탁드립니다.
바쁘신 와중에도 검토해 주셔서 감사드리며, 회신을 기다리겠습니다.
감사합니다.

RootNGlobal Investors
{sender.txt name_kr} 드림
```

### 일본 (Japanese/English bilingual)

**제목:** `IRミーティングのご依頼 / IR Meeting Request (RootNGlobal Investors)`

**내용:**
```
{会社名} IRご担当者様

RootNGlobal Investorsの{sender.txt name_kr}（{sender.txt name_en}）と申します。

弊社は10年以上のグローバル株式運用実績を持つ上場株式ロングオンリーの資産運用会社で、2～3年以上の長期保有を前提とした価値投資を志向しております（会社紹介: http://www.rootnglobal.com/eng/sub1_1.jsp）。最近、日本株ファンドを立ち上げ、日本企業への投資検討を進めております。この度、{会社名}様の主要事業の現状および中長期的な成長戦略についてより深く理解させていただきたく、IRミーティングのご機会をいただけないでしょうか。

ミーティングはオンライン（60分程度）を希望しております。日程は貴社のご都合に合わせて柔軟に調整いたします。ご都合のよい候補日時をいくつかご提示いただけますと幸いです。オンラインでのご対応が難しい場合は、質問書をメールでお送りし、ご回答をいただく形でも差し支えございません。

また、事前に質問書やその他資料が必要でしたら、遠慮なくお申し付けください。
ご多忙のところ恐れ入りますが、ご検討いただけますと幸甚です。

---

Dear IR Team at {Company Name},

My name is {sender.txt name_en} from RootNGlobal Investors, a long-only equity asset manager with a global equity track record of over 10 years, investing for the long term with a typical holding period of 2-3 years or more (http://www.rootnglobal.com/eng/sub1_1.jsp). We recently launched a Japan equity fund and are reviewing Japanese companies.

We would like to request an IR meeting to gain deeper insight into {Company Name}'s key business operations and medium-to-long-term growth strategy. We would prefer an online call of about 60 minutes and are flexible on timing — please suggest a few available slots at your convenience. If a live meeting is difficult, we're also happy to send a questionnaire by email and receive written answers.

If you require a written questionnaire or any materials in advance, please let us know.

Best regards,
{sender.txt name_en} | RootNGlobal Investors | {_config/sender.txt의 email}
```

**일본 압축본 (글자수/바이트 제한 폼 전용, 일본어 단독, ~950바이트 이내)**
```
{会社名} IRご担当者様

RootNGlobal Investors（上場株式ロングオンリー運用、グローバル株式運用10年超、2～3年以上の長期保有）の{sender.txt name_en}と申します。日本株ファンドの立ち上げに伴い、貴社の事業と中長期戦略をより深く理解させていただきたく、オンライン（60分程度）でのIRミーティングをお願いできませんでしょうか。難しい場合は、質問書へのメールでのご回答でも差し支えございません。候補日時をご提示いただけますと幸いです。
会社紹介: http://www.rootnglobal.com/eng/sub1_1.jsp
```

### 미국 (English)

**제목:** `IR Meeting Request – RootNGlobal Investors`

**내용:**
```
Dear IR Team at {Company Name},

My name is {sender.txt name_en} from RootNGlobal Investors, a long-only equity asset manager with a global equity track record of over 10 years, investing for the long term with a typical holding period of 2-3 years or more (http://www.rootnglobal.com/eng/sub1_1.jsp).

We are currently conducting investment due diligence on {Company Name} and would like to request an IR meeting to better understand your key business operations and medium-to-long-term growth strategy.

We would prefer an online call of about 60 minutes and are flexible on timing — please suggest a few available slots at your earliest convenience. If a live meeting is difficult, we're also happy to send a questionnaire by email and receive written answers. If you require a written questionnaire or any materials in advance, please let us know.

Thank you for your time and consideration.

Best regards,
{sender.txt name_en}
RootNGlobal Investors
{_config/sender.txt의 email}
```

### 중국 (Chinese/English bilingual)

**제목:** `IR会议请求 / IR Meeting Request (RootNGlobal Investors)`

**내용:**
```
尊敬的{公司名称}投资者关系团队：

您好，我是RootNGlobal Investors的{sender.txt name_en}（{sender.txt name_kr}）。

我司是一家拥有逾10年全球股票投资业绩的上市股票多头（long-only）资产管理公司，坚持2～3年以上长期持有的价值投资理念（公司介绍：http://www.rootnglobal.com/eng/sub1_1.jsp）。为了更深入了解{公司名称}的核心业务现状及中长期增长战略，希望申请一次IR会议。

会议形式希望为线上会议（约60分钟），时间可根据贵司便利灵活安排，烦请提供几个可行的时间段。如线上会议不便，我们也可以将问题清单以邮件发送、由贵司书面回复。如需事先提交问卷或其他材料，请随时告知。

感谢您百忙之中的关注，期待您的回复。

---

Dear IR Team at {Company Name},

My name is {sender.txt name_en} from RootNGlobal Investors, a long-only equity asset manager with a global equity track record of over 10 years, investing for the long term with a typical holding period of 2-3 years or more (http://www.rootnglobal.com/eng/sub1_1.jsp).

We would like to request an IR meeting to gain deeper insight into {Company Name}'s key business operations and medium-to-long-term growth strategy. We would prefer an online call of about 60 minutes and are flexible on timing. Please suggest a few available time slots at your convenience. If a live meeting is difficult, we're also happy to send a questionnaire by email and receive written answers.

Best regards,
{sender.txt name_en} | RootNGlobal Investors | {_config/sender.txt의 email}
```

---

## Step 5: 제출 및 사용자에게 보고

1. **제출**: 확인 화면(確認)이 있으면 표시된 내용을 입력값과 대조한 뒤 送信한다. 확인 화면이 없으면 Step 3의 전 필드 재검증 후 제출한다. 완료 페이지 URL·문구(예: 「お問い合わせを承りました」)로 성공을 검증한다.
2. **자동응답 확인**: 제출 후 Gmail에서 대상 회사 도메인의 자동응답(受付完了 등)을 검색한다. 자동응답에 IR 이메일 주소가 노출되면 follow-up용으로 보고한다.
3. 사용자에게 다음을 보고한다:

```
✅ 웹폼 제출 완료

- 회사: {회사명}
- 폼 URL: {URL} → 완료 페이지: {URL/문구}
- 이름: {sender.txt name_kr} / {sender.txt name_en}
- 이메일: {_config/sender.txt의 email}
- 문의 유형: IR 관련 선택됨
- 제목: {작성한 제목}
- 자동응답: {수신 여부} / 노출된 IR 주소: {주소 또는 없음}
```

체크한 동의(제출 필수 개인정보 처리 동의)·체크하지 않은 동의(마케팅·뉴스레터), 침묵기간 문장·CC 요청 문장 삽입 여부를 1줄로 명시한다. 제출하지 못했으면(챌린지 CAPTCHA·통신인증 반복 실패 등) 사유와 남은 단계를 적고 사용자 수동 제출로 넘긴다.

---

## 주의사항

- **제출은 기본 진행한다**(IR 미팅 요청 웹폼 한정, 공통 규칙 §2 예외). 확인 화면 대조 후 送信하며, 사용자가 "작성만"을 지시한 경우에만 제출하지 않는다.
- **동의 체크박스**: 제출에 필수인 개인정보 처리 동의(プライバシーポリシー同意/개인정보 수집 동의)는 체크한다. 마케팅·뉴스레터 수신 동의는 체크하지 않는다. 체크 내역은 보고에 명시한다.
- **쿠키/트래킹 동의 팝업은 가장 privacy-preserving 옵션(거부)을 선택**한 뒤 폼 작성을 진행한다.
- **웹폼에는 CC 개념이 없다.** 회신은 입력한 발신 이메일로만 오므로, 본문 말미에 '선택 문장'의 CC 요청 문장(대상 언어별)을 넣고, 결과 보고에 1줄 명시한다.
- 폼을 찾지 못하거나 로그인이 필요한 경우 사용자에게 알리고 대안(이메일 주소, 전화번호)을 제시한다.
- **reCAPTCHA/CAPTCHA**: invisible이면 그대로 통과한다. 이미지·퍼즐 챌린지가 뜨면 풀지 않고 즉시 중단해 사용자 처리로 넘긴다(공통 규칙 §1).
- 첨부파일 필드는 건드리지 않는다.
- 여러 회사를 한꺼번에 요청한 경우 회사별로 Step 1~5를 순서대로 반복한다.

## 일본 폼 특이사항 (현장 확인)

- **동의 게이트**: 일부 일본 IR 폼은 입력 화면 앞에 프라이버시 정책 동의 페이지(예: `/ir/inquiry.html` → "同意して問合わせる" → `/contact/contact.php?id=N`)를 둔다. 이 동의는 폼 접근을 위한 필수 이동 단계이므로 통과해 진입한다.
- **필수 都道府県/住所 (해외 발신 대응)**: 일본 국내 폼의 `都道府県`(현) 드롭다운은 해외 옵션이 없이 필수(※)인 경우가 많다. 임의로 가짜 지역을 넣지 말고 사용자에게 flag한 뒤, 사용자가 "아무거나 선택"을 승인하면 임의 현(예: 대상사 본사 소재 현)을 선택하고 `住所`에는 실제 해외 주소(sender.txt `address_en`, 예: "..., Seoul, Republic of Korea")를 명기한다. TEL 3분할은 국내 형식(예: 010 / XXXX / XXXX)으로 넣고 국가코드(+82)는 본문 서명에 병기한다.
- **확인 단계 토큰 오류**: 확인(確認) 버튼 클릭 시 이메일 필드 옆에 "通信認証に失敗しました"(통신 인증 실패)가 뜰 수 있다(토큰/세션 이슈로 추정). 입력값은 대개 유지되므로, 재렌더된 폼에서 확인을 **1회** 재시도한다(fail-fast: 2회 초과 금지). 반복 실패면 봇 차단 가능성으로 보고 사용자에게 수동 제출을 넘긴다.
- **제출 흐름**: 일반적으로 `contact.php`(입력) → `confirm.php`(확인, 送信/修正) → `commit.php`(접수 완료, "お問い合わせを承りました"). 기본 제출 — 확인 화면 내용을 입력값과 대조한 뒤 送信하고, 완료 페이지 URL·문구로 성공을 검증한다.
