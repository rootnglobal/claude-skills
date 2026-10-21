---
name: ir-webform
version: 261021
description: "한국/일본/중국/미국 상장사의 IR 문의 웹폼을 자동으로 찾아 Claude in Chrome으로 내용을 채워주는 스킬. 회사명이나 URL을 입력하면 IR/투자자 관계 문의 페이지를 찾아 양식을 작성하고 사용자가 확인 후 제출할 수 있도록 한다. '웹폼', '폼 작성', '문의 양식', '컨택 폼', 'contact form', 'IR 문의', '투자자 문의' 등의 키워드와 함께 회사명이 언급되면 이 스킬을 사용할 것. 이메일 주소를 찾지 못한 경우나 회사 웹폼을 통해 IR 미팅 요청을 하려는 경우에도 적극적으로 사용할 것. 공개된 IR 이메일이 없고 회사가 웹 문의 폼만 운영하는 경우에는 사용자에게 '웹폼으로 진행할까요?'라고 되묻지 말고 곧바로 이 스킬을 실행해 웹폼을 채울 것."
---

# IR 웹폼 자동 작성 스킬

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


## 개요

이 스킬은 한국/일본/중국/미국 상장사의 IR 문의 웹폼을 Claude in Chrome으로 자동으로 찾아 채워준다.
직접 이메일 주소를 찾지 못한 경우나 회사가 웹폼 기반 문의만 지원하는 경우에 사용한다.

**공개된 IR 이메일이 없고 회사가 웹 문의 폼만 운영하는 경우, 사용자에게 "웹폼으로 진행할까요?"라고 되묻지 말고 곧바로 이 스킬을 실행해 웹폼을 채운다.** 단, 제출(submit) 버튼은 끝까지 누르지 않으며, 작성 후 제출은 사용자가 직접 확인하고 누르도록 한다. 스킬은 절대 자동으로 제출하지 않는다.

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
(되묻지 않는 것은 '작성'까지이며, **제출(submit)은 끝까지 사용자 몫**이라는 원칙은 그대로 유지된다.)

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

### Step 4: 제목 및 내용 작성

`{회사명}` 부분만 실제 회사명으로 교체하여 아래 국가별 템플릿을 그대로 사용한다.

**형식·일정 제약 반영(중요)**: 사용자가 미팅 형식(온라인/대면)이나 일정(특정 월·요일·시간대)을 **명시**했으면, 템플릿의 '형식·일정 유연' 문장만 그 제약으로 **정밀 교체**하고 나머지 문구는 유지한다. 예: 온라인 전용 + 10월 오후 13:30~16:30 → 해당 문장을 "온라인(화상)만 희망 / 10월 평일 오후 13:30~16:30 후보 요청"으로 바꾼다. **일본↔한국은 동일 시간대(UTC+9)라 KST/JST 변환 불필요**(그 사실을 본문에 '일본시간, 한국시간과 동일'로 명기하면 오해가 없다). 미국·중국 등 시차가 있는 국가는 상대국 현지시간으로 환산해 병기한다.

**제목(Subject) 병기 원칙:** 비영어권 회사(일본·중국 등)의 제목은 본문과 마찬가지로 **대상 회사의 언어 / 영어** 병기로 작성한다(예: 일본어 `IRミーティングのご依頼 / IR Meeting Request (...)`). 발신·수신이 같은 언어권인 한국(국문 단독) 및 영어권인 미국(영어 단독)은 단일 언어 제목을 그대로 사용한다.

---

## 국가별 콘텐츠 템플릿

### 한국 (Korean)

**제목:** `IR 미팅 요청의 건 (RootNGlobal Investors)`

**내용:**
```
안녕하십니까, {회사명} IR 담당자님.

RootNGlobal Investors는 장기 가치 투자를 지향하는 상장 주식 롱온리 자산운용사(당사 소개: http://www.rootnglobal.com/kor/sub1_1.jsp)로, 현재 {회사명}의 주요 사업 현황과 중장기 성장 전략에 대한 보다 심도 있는 이해를 바탕으로 투자 검토를 진행하고자 IR 미팅을 요청드리고자 합니다.

미팅 방식(대면 또는 비대면) 및 일정은 귀사의 편의에 맞추어 유연하게 조율하고자 합니다. 가능하신 일시를 몇 가지 제안해 주시면 확인 후 신속히 회신드리겠습니다.

아울러 사전에 전달드려야 할 질의서나 추가 자료가 필요하시면 편히 말씀 부탁드립니다.
바쁘신 와중에도 검토해 주셔서 감사드리며, 회신을 기다리겠습니다.
감사합니다.

RootNGlobal Investors
모영화 드림
```

### 일본 (Japanese/English bilingual)

**제목:** `IRミーティングのご依頼 / IR Meeting Request (RootNGlobal Investors)`

**내용:**
```
{会社名} IRご担当者様

RootNGlobal Investorsの모영화（Mo Younghwa）と申します。

弊社は長期的な価値投資を志向する上場株式ロングオンリーの資産運用会社です（会社紹介: http://www.rootnglobal.com/kor/sub1_1.jsp）。この度、{会社名}様の主要事業の現状および中長期的な成長戦略についてより深くご理解するため、IRミーティングのご機会をいただけないでしょうか。

ミーティングの形式（対面・オンライン）および日程は、貴社のご都合に合わせて柔軟に調整いたします。ご都合のよい候補日時をいくつかご提示いただけますと幸いです。

また、事前に質問書やその他資料が必要でしたら、遠慮なくお申し付けください。
ご多忙のところ恐れ入りますが、ご検討いただけますと幸甚です。

---

Dear IR Team at {Company Name},

My name is Younghwa Mo from RootNGlobal Investors, a long-only equity asset manager focused on long-term value investing (http://www.rootnglobal.com/kor/sub1_1.jsp).

We would like to request an IR meeting to gain deeper insight into {Company Name}'s key business operations and medium-to-long-term growth strategy. We are flexible on format (in-person or virtual) and timing — please suggest a few available slots at your convenience.

If you require a written questionnaire or any materials in advance, please let us know.

Best regards,
Younghwa Mo | RootNGlobal Investors | {_config/sender.txt의 email}
```

### 미국 (English)

**제목:** `IR Meeting Request – RootNGlobal Investors`

**내용:**
```
Dear IR Team at {Company Name},

My name is Younghwa Mo from RootNGlobal Investors, a long-only equity asset manager focused on long-term value investing (http://www.rootnglobal.com/kor/sub1_1.jsp).

We are currently conducting investment due diligence on {Company Name} and would like to request an IR meeting to better understand your key business operations and medium-to-long-term growth strategy.

We are flexible on format (in-person or virtual) and timing — please suggest a few available slots at your earliest convenience. If you require a written questionnaire or any materials in advance, please let us know.

Thank you for your time and consideration.

Best regards,
Younghwa Mo
RootNGlobal Investors
{_config/sender.txt의 email}
```

### 중국 (Chinese/English bilingual)

**제목:** `IR会议请求 / IR Meeting Request (RootNGlobal Investors)`

**내용:**
```
尊敬的{公司名称}投资者关系团队：

您好，我是RootNGlobal Investors的Mo Younghwa（모영화）。

贵司是一家专注于长期价值投资的股票多头资产管理公司（公司介绍：http://www.rootnglobal.com/kor/sub1_1.jsp）。为了更深入了解{公司名称}的核心业务现状及中长期增长战略，希望申请一次IR会议。

会议形式（线上或线下）及时间均可根据贵司便利灵活安排，烦请提供几个可行的时间段。如需事先提交问卷或其他材料，请随时告知。

感谢您百忙之中的关注，期待您的回复。

---

Dear IR Team at {Company Name},

My name is Younghwa Mo from RootNGlobal Investors, a long-only equity asset manager focused on long-term value investing (http://www.rootnglobal.com/kor/sub1_1.jsp).

We would like to request an IR meeting to gain deeper insight into {Company Name}'s key business operations and medium-to-long-term growth strategy. We are flexible on format (in-person or virtual) and timing. Please suggest a few available time slots at your convenience.

Best regards,
Younghwa Mo | RootNGlobal Investors | {_config/sender.txt의 email}
```

---

## Step 5: 작성 완료 후 사용자에게 보고

폼 작성이 완료되면 **절대 제출하지 않고** 사용자에게 다음을 보고한다:

```
✅ 웹폼 작성 완료

- 회사: {회사명}
- 폼 URL: {URL}
- 이름: 모영화 / Mo Younghwa
- 이메일: {_config/sender.txt의 email}
- 문의 유형: IR 관련 선택됨
- 제목: {작성한 제목}

브라우저에서 내용을 확인하신 후 직접 제출해 주세요.
```

남겨둔 항목(개인정보 동의 체크박스 미체크, 제출 버튼)과 웹폼 CC 불가 사실을 함께 1줄로 명시한다.

---

## 주의사항

- **제출(submit) 버튼은 절대 클릭하지 않는다.** 사용자가 직접 검토 후 제출한다.
- **개인정보 동의(プライバシーポリシー同意/개인정보 수집 동의) 체크박스는 스킬이 체크하지 않는다.** 약관·동의 수락은 사용자 몫이며, 제출과 함께 사용자가 직접 체크하도록 남겨두고 보고에 명시한다.
- **쿠키/트래킹 동의 팝업은 가장 privacy-preserving 옵션(거부)을 선택**한 뒤 폼 작성을 진행한다.
- **웹폼에는 CC 개념이 없다.** 회신은 입력한 발신 이메일로만 오므로, `_config/sender.txt`의 CC 수신인은 웹폼 경로에서 반영할 수 없다 — 결과 보고에 1줄 명시한다. CC가 필수면 이메일 채널이 필요함을 알린다.
- 폼을 찾지 못하거나 로그인이 필요한 경우 사용자에게 알리고 대안(이메일 주소, 전화번호)을 제시한다.
- CAPTCHA가 있으면 사용자에게 직접 처리를 요청한다.
- 첨부파일 필드는 건드리지 않는다.
- 여러 회사를 한꺼번에 요청한 경우 회사별로 Step 1~5를 순서대로 반복한다.
