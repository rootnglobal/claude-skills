---
name: ir-meeting-reply
version: 261127b
description: "IR 담당자가 보낸 미팅 일정 제안·확정·링크·통역 관련 메일에 답장 초안(Gmail 임시보관함)을 만드는 스킬. 사용자가 회사명과 일시만 주면 스레드를 찾아 수신자·참조·담당자명·요일·종료시각·통역 문의·미팅 링크 문구를 알아서 채운다. 일본 기업=일본어+영어, 한국=한국어, 영어 메일=영어. 트리거: IR 답장, IR 메일 답장 적어줘, ○○에 답장 12/8 9:30, 일정 회신, 미팅 확정 답장, 이 시간으로 답해줘."
---

# IR 미팅 회신 초안 스킬

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 `../_shared/common-rules.md`)를 읽고 적용한다 — fail-fast, 자동진행/사전확인, §8 발신자·CC(`_config/sender.txt`), §12 스킬 피드백 루프. 메일은 **초안까지만** 만든다. 발송은 사용자가 한다.

요청 메일(첫 연락)은 `ir-meeting-request`·`ir-meeting-request-jp` 몫이다. 이 스킬은 **상대가 답장을 보낸 뒤의 회신**만 다룬다. 질문지 파일 작성은 `ir-question-prep`, IR 시트 반영은 `ir-tracker` 몫이다.

## 입력

- 필수: 회사명(약칭·오타 허용) + 일시(예: `12/8 9:30`, `12/14 14:30~15:30`).
- 선택: 추가 지시(통역 확정, 링크 방식, 자료 요청 등). 없으면 아래 기본값으로 진행하고 묻지 않는다.
- 시각은 상대국 현지시간으로 본다(일본 JST = 한국 KST). 그 외 시간대 회사면 1회만 확인한다.
- 여러 회사를 한 번에 주면 회사별로 Step 1~6을 반복한다.
- 사용자가 일시를 정하지 않았는데 상대가 후보 슬롯을 여러 개 줬으면 → 후보를 한 줄씩 나열한 **선택용 초안**을 만든다(Step 3). 사용자가 남길 줄만 두고 지운 뒤 바로 보낸다.
- 상대가 **일정 예약 링크**(TimeRex·msetsu·Calendly 등)로 고르라고 하면 → 답장 초안을 만들지 않는다. 링크, 스피커, 상대의 미결 질문(언어·통역 등)을 사용자에게 알리고 멈춘다. 사용자가 예약한 뒤 "답장해줘"라고 하면 그때 회신을 쓴다.

## Step 1. 스레드 찾기

1. Gmail `search_threads`(view `THREAD_VIEW_SUMMARY`): `({영문명} OR {현지어 사명} OR {도메인}) newer_than:120d`. 사명이 오타·약칭이면 철자 변형과 현지어 표기를 OR로 묶는다(예: 영문 철자 2종 + 가타카나).
2. 대상 = 상대 회사 도메인에서 온 **가장 최근 수신 메시지**가 있는 IR 스레드. 우리 쪽 메시지가 이미 마지막이면 답장 완료로 보고 1줄로 알리고 멈춘다.
3. 후보가 둘 이상이고 구분이 안 될 때만 묻는다(식별 질문).
4. `get_thread`로 읽는다. 결과가 파일로 떨어질 만큼 크면 메시지별로 인용 이력(`From:`, `差出人:`, `On ... wrote:`, `20xx년 ... 작성:`) 앞부분만 잘라 읽는다.

## Step 2. 상대 메일에서 뽑을 것

| 항목 | 쓰임 |
|---|---|
| 담당자 성(姓)·회사 정식명 | 첫 줄 `{会社名}\n{姓}様`, 영어 경칭 |
| 제안 슬롯(날짜·시간 범위·소요시간) | 사용자 일시 검증 |
| 미팅 링크 언급 | ④ 링크 블록 분기 |
| 통역 언급 | ③ 통역 블록 분기 |
| 우리 쪽 참석자·직함·인원·긴급연락처 문의 | ⑤ 참석자 블록 |
| 일정 예약 링크(TimeRex·msetsu·Calendly 등) | 초안 없이 사용자에게 알림 |
| 질문지(質問シート·質問票) 제출 기한 | 회신에 기한 확인 1줄 + Step 5b 리마인더 예약 |
| 그 밖의 질문·요청(자료 등) | 답변하거나 사용자에게 플래그 |
| To·Cc | 수신자 설정 |

## Step 3. 일시 확정 — 계산은 코드로

- 요일은 반드시 코드로 계산한다(예: `python3 -c "import datetime as d;print(d.date(2026,12,8).strftime('%a'))"`). 연도는 오늘 기준 가장 가까운 미래.
- 종료시각: 시작만 주어지면 시작+60분(상대가 다른 소요시간을 정했으면 그 길이). 상대가 정확한 슬롯(예: 14:30–15:30)을 줬으면 그대로 쓴다.
- 사용자가 고른 시각이 제안 슬롯 밖이면 초안은 만들되 보고에 ⚠ 1줄.
- **선택용 초안**(사용자가 일시를 안 정함): 일본어·영어 양쪽에 후보를 한 줄씩 나열한다 — `・{M}月{D}日（{曜}）{HH:MM}－{HH:MM}（日本時間）` / `- {Weekday}, {Month} {D}, {HH:MM}-{HH:MM} (JST)`.
  - 시간 범위로 준 후보는 시작 시각부터 60분으로 잡는다.
  - 줄을 지워도 문장이 성립하게 앞 문장은 단수형으로 쓴다: `日程は、下記でお願いできれば幸いです。` / `We would like to schedule the meeting for the following slot:`
  - 본문에 안내 문구나 표시를 넣지 않는다. 보고에서 "양쪽 언어에서 한 줄만 남기고 보내라"고 알린다.
  - 후보가 Google Calendar 일정이나 확정 대기 중인 다른 IR 일정(메일상 합의, 캘린더 미등록 포함)과 겹치거나 붙어 있으면 보고에 표시한다.
- 상대가 제안한 슬롯을 고른 경우 "어려우면 다른 시간도 가능" 같은 **대안 문장은 넣지 않는다**. 사용자가 대안을 명시하면 그때만 넣는다.

## Step 4. 본문 구성 — 짧게, IR 담당자가 한 번에 읽히게

순서: ① 감사 1줄 → ② 일정 1줄 → ③ 통역(조건부) → ④ 링크(조건부) → ⑤ 참석자 블록·상대 질문 답변(물었을 때) → ⑥ 자료 요청(기본) → ⑦ 마무리·서명.

원칙:
- 상대가 이미 정한 항목은 확인만 한다.
- 조건을 길게 늘어놓거나 우리 방식을 강요하지 않는다.
- AI 번역 도구는 언급하지 않는다.

### ③ 통역 블록 분기

- **상대가 통역을 언급하지 않음** → 아래 표준 블록을 그대로 쓴다.
- **상대가 우리 방식을 안 뒤에도 통역을 요청함 / 통역 수배를 명시적으로 요청함** → 표준 블록 대신 1줄: `通訳は弊社にて手配いたします。` / `We will arrange an interpreter on our side.`
- **상대가 일본어 진행을 희망하거나 "그 외 언어면 통역을 준비해 달라"고 일반 조건으로만 말함**(우리 방식을 아직 설명하지 않음) → 바로 통역을 수락하지 말고 아래 **재확인 블록**으로 다시 묻는다. 우리 방식이면 회사는 일본어만 쓰면 된다는 점을 알리고, 그래도 필요하면 우리가 섭외한다고 쓴다. 참석자 블록의 통역 줄은 `通訳者 1名（必要な場合、弊社手配）` / `One interpreter, if needed (arranged by us)`로 쓴다.

재확인 블록(일본어):

```
通訳について、改めてご確認させていただけますでしょうか。
当日は弊社より英語で質問いたしますが、以下の形式で進めますと、貴社では日本語のみでご対応いただけます。
・追加質問も含め、全てのご質問を事前に日本語の質問票でお送りします。
・ご回答は日本語でいただいて問題ございません。
・必要に応じて、チャットにて日本語でもやり取りいたします。
この形式でも通訳が必要な場合は、弊社にて手配いたしますので、お知らせいただけますと幸いです。
```

재확인 블록(영어):

```
Regarding the interpreter, may we kindly confirm once more? We will ask our questions in English, but with the following format, your side can respond entirely in Japanese:
- We will send all questions, including follow-up questions, in advance as a written questionnaire in Japanese.
- You are welcome to answer in Japanese.
- If needed, we will also communicate in Japanese via the meeting chat.
If an interpreter would still be needed in this format, please let us know and we will arrange one on our side.
```
- **상대가 통역 불필요라고 함** → 생략하거나 `通訳の件、承知いたしました。` 1줄.
- **사용자가 통역을 확정함**(예: "통역 붙일 거야") → 그 지시를 따른다.
- 통역이 이미 정해졌는지 헷갈리면 Gmail 스레드 → 'IR 미팅/콜 관리' 시트 '요청/진행사항' 탭(통역가 연락처·기타 진행현황 열, 시트 ID는 `_config/sheet_ids.txt`의 `ir_tracker`) → 사용자 질문 순으로 확인한다(ir-question-prep §8-1과 같은 순서).
- 통역을 우리가 섭외하기로 정해지면 당일 질문은 통역 경유 한국어다 — 그 뒤 회신에는 '英語で質問' 류 문구를 다시 쓰지 않는다(질문지 언어는 `ir-question-prep` §0).

표준 블록(일본어):

```
また、通訳の要否についてお伺いできればと存じます。
差し支えなければ、以下の形式で通訳なしで進めることも可能です。
・追加質問も含め、全てのご質問を事前に日本語の質問票でお送りします。
・当日は英語で質問いたしますが、ご回答は日本語でいただいて問題ございません。
・必要に応じて、チャットにて日本語でもやり取りいたします。

他社様とも、この形式で効率よく進められた例がございます。もちろん、通訳がいた方がよろしい場合は弊社にて手配いたしますので、ご都合のよい方をお知らせいただけますと幸いです。
```

표준 블록(영어):

```
We would also like to ask about the need for an interpreter. If convenient for you, we could proceed without one in the following format:
- We will send all questions, including follow-up questions, in advance as a written questionnaire in Japanese.
- We will ask questions in English, and you are welcome to answer in Japanese.
- If needed, we will also communicate in Japanese via the meeting chat.

In some of our meetings with other companies, this format has worked efficiently. Of course, if you would prefer to have an interpreter, we will gladly arrange one on our side. Please let us know whichever you prefer.
```

쓰지 않는 표현(사용자 교정 이력):
- "통역 없이 하고 싶다·선호한다"로 시작하는 문장
- "다른 회사와도 이 방식으로 하고 있다"처럼 늘 그렇게 하는 듯한 표현. 쓸 수 있는 건 "효율적으로 진행한 사례가 있다"까지다.
- "회사 방침상 필요하면"처럼 통역 선택에 조건을 다는 표현
- AI 실시간 번역 도구의 이름을 대거나 강조하는 표현
- 숫자만 영어로 전달되면 충분하다는 표현(상대에게 영어 부담을 상기시킴)

### ④ 링크 블록 분기

툴 이름은 상대가 쓴 표현을 따른다.

- **상대가 Zoom/Teams 등을 보내겠다고 함** → `Zoomのご案内をお待ちしております。` / `We look forward to receiving the Zoom invitation.`
- **상대가 자사 툴로 설정하겠다고 제안함** → 수락: `Teamsでのご設定をお願いできますと幸いです。` / `We would appreciate it if you could set up the Teams meeting.`
- **상대가 우리에게 설정을 요청함** → `弊社にてGoogle Meetのリンクをお送りいたします。` / `We will send you a Google Meet link.`
- **링크 언급이 없음** → `ミーティングのリンクは、弊社にてGoogle Meetをご用意できます。貴社で別のツールをご設定いただける場合は、そちらを使用いたします。` / `Regarding the meeting link, we can set up a Google Meet. If you would prefer to set up another platform, we will be happy to use that instead.`

### ⑤ 참석자·긴급연락처 블록(상대가 물었을 때만)

- 값은 Drive `_config/ir_meeting_attendees.txt`에서 읽는다(`attendee_en`, `attendee_ja`, `title_en`, `title_ja`, `emergency_1`, `emergency_2`). 이름·전화번호를 SKILL.md에 쓰지 않는다. 파일을 못 읽으면 자리표시로 두고 보고에 플래그한다.
- 기본값: 사용자가 따로 말하지 않으면 참석자는 `attendee` 1명, 통역이 있으면 통역 +1명.
- 묻지 않은 항목(긴급연락처 등)은 넣지 않는다.
- 풀네임(フルネーム)을 물으면 `_config/sender.txt`의 `name_en`을 쓰고, `attendee_ja`의 가타카나를 괄호로 붙인다.

출석자 소속·이름을 물었을 때(일본어 / 영어):

```
【弊社出席者】
・{company}　{title_ja}（{title_en}）　{attendee_ja}
・通訳者 1名（弊社手配）
```

```
Attendees from our side:
- {attendee_en}, {title_en}, {company}
- One interpreter (arranged by us)
```

직함·인원·긴급연락처를 물었을 때(일본어 / 영어):

```
【対応者・役職】
{attendee_ja}／{title_ja}（{title_en}）
【参加人数】
{N}名（{attendee_en}、通訳者1名）
【緊急連絡先】
・{emergency_1}
・{emergency_2}
```

```
- Attendee / title: {attendee_en}, {title_en}
- Number of participants: {N} ({attendee_en} and one interpreter)
- Emergency contacts: {emergency_1} / {emergency_2}
```

통역이 없으면 통역 줄과 인원 +1을 뺀다. 통역 여부가 미정이면 통역 줄에 `（必要な場合、弊社手配）` / `if needed`를 붙인다.

### ⑥ 자료 요청 블록(기본)

- 일정 회신·확정 회신에 기본으로 1줄 넣는다. 위치는 링크·참석자 블록 뒤, 마무리 앞.
- 넣지 않는 경우: 이 스레드에서 우리가 이미 자료를 요청했음, 상대가 IR deck 등이 없다고 했음, 상대가 자료를 이미 보내왔음.

```
貴社IRページに掲載されていない資料（IRデッキ等）がございましたら、ミーティング前に共有いただけますと幸いです。
```

```
If there are any materials not available on your IR website (such as an IR deck), we would appreciate it if you could share them with us before the meeting.
```

한국 기업: `IR 페이지에 공개되지 않은 자료(IR deck 등)가 있으시면 미팅 전에 공유해 주시면 감사하겠습니다.`

### 선택 블록(사용자가 요청할 때만)

- 질문지 송부 시점: `質問票はミーティングの1～2日前までにお送りいたします。` / `We will send the questionnaire 1-2 days before the meeting.`

### 표준 골격 — 일본 기업(일본어 먼저, `---` 뒤 영어)

```
{会社正式名}
{担当者姓}様

ご返信いただき、誠にありがとうございます。

日程は、{M}月{D}日（{曜}）{HH:MM}－{HH:MM}（日本時間）でお願いできれば幸いです。

{③ 일본어}

{④ 일본어}

{⑥ 일본어}

引き続きよろしくお願い申し上げます。

{서명}

---

Dear {경칭},

Thank you very much for your reply.

We would like to schedule the meeting for {Weekday}, {Month} {D}, {HH:MM}-{HH:MM} (JST).

{③ English}

{④ English}

{⑥ English}

Best regards,
{서명}
```

- 시간 표기: 일본어는 전각 `：`·`－`, 영어는 `14:30-15:30`.
- 영어 경칭: 기본은 `{Surname}-san`. 상대가 영문 서명에 Mr./Ms.를 썼거나 스레드에서 이미 그렇게 불렀을 때만 그것을 쓴다(한자 이름만으로 성별을 추정하지 않는다).
- 서명: `_config/sender.txt`의 `company`(없으면 회사명). 이 스레드에서 우리 쪽이 개인 이름을 넣어 왔으면 같은 형식(`{name_en}` + 회사명)을 따른다.
- 첫 줄은 상대가 이미 쓴 우리 쪽 인사 형식과 맞춘다. 첫 회신이면 `いつもお世話になっております` 없이 `ご返信いただき…`로 시작한다.

### 언어 분기

- **일본 기업이 일본어로 보냄** → 일본어+영어(위 골격).
- **영어로만 보냄**(일본 기업 포함) → 영어 블록만. 상대가 일본어 진행이나 통역을 말했으면 ③ 분기를 적용한다.
- **한국 기업** → 한국어만. 통역 블록 없이 ①②④⑥⑦만 쓴다(⑥은 한국어 문구).
- **그 밖의 비영어권**(중국 등) → 같은 구조를 상대 언어+영어로 쓰되, 그 언어의 통역 블록 문구는 처음 쓸 때 사용자에게 1회 확인한다.

## Step 5. 초안 저장

- `create_draft` 설정:
  - `replyToMessageId` = 마지막 수신 메시지 id(인용 이력이 자동으로 붙는다)
  - `to` = 그 메시지 발신자
  - `cc` = 그 메시지 To·Cc 중 자사 발신 계정을 뺀 전원 + `_config/sender.txt`의 `cc`(중복 제거)
  - 제목 = `RE: ` + 원 제목(이미 RE:/Re:로 시작하면 그대로)
- 본문은 plain text `body`로 쓴다(마크다운 금지). `includeSignature`는 false(서명은 본문에 직접 쓴다).
- 수정 요청이 오면 → `update_draft`는 인용 이력을 날리므로 **새 초안을 만든 뒤 이전 초안을 `delete_draft`**한다(이번 세션에서 만든 초안만). `delete_draft`가 "Message not a draft"를 돌려주면 사용자가 이미 보낸 것이다 → 방금 만든 새 초안을 지우고 알린다.
- 자동 발송은 하지 않는다.

## Step 5b. 질문지 기한 리마인더 예약(상대가 기한을 정했을 때)

- 상대가 질문지·질문 시트 제출 기한을 정하면(예: 「質問シートは12/10（木）午前中までに」) 초안 저장과 함께 1회성 예약 작업을 만든다. 따로 묻지 않는다.
- 실행 시각: 기한 7일 전 같은 요일 09:00(KST). 그 시각이 이미 지났거나 24시간 안이면 다음 날 09:00으로 당기고 보고에 적는다. 사용자가 시점을 따로 말하면 그것을 따른다.
- 만들기 전에 `list_triggers`로 같은 회사·같은 기한의 리마인더가 이미 있는지 확인한다.
- `create_trigger`: `run_once_at` = `YYYY-MM-DDT09:00:00[Asia/Seoul]`, `initiation` = human_request, `notifications` = {}. 작업 이름 = `{영문 사명} ({코드}) IR 질문지 리마인더 (1회, 텔레그램)`.
- 프롬프트는 기존 "(1회, 텔레그램)" 리마인더 예약 작업과 같은 형식으로 쓴다. 텔레그램 자격증명은 'RootN API Keys' 시트에서 /tmp 파일로만 다루고, chat_id는 기존 작업과 같은 값을 쓰며, 텔레그램 1건 발송 외 다른 행동은 금지한다. 시트 id·chat_id는 SKILL.md에 쓰지 않고 기존 작업에서 가져온다.
- 메시지 본문(한국어):
  - 첫 줄 `⏰ {영문 사명} ({코드}) IR 질문지 — {MM/DD(요일) 오전}까지 발송`
  - 미팅 일시·링크 제공 주체·통역 유무
  - 조건(예: 추가 질문까지 전부 사전 송부, 일본어 답변)
  - 할 일: Claude에 "{영문 사명} IR 질문지 만들어줘"(ir-question-prep) → 검토 → 이 스레드에 회신으로 발송(CC 유지)
  - 스레드 링크
- 기한 없이 미팅만 확정됐으면 리마인더를 만들지 않는다(사용자가 원하면 미팅 7일 전으로).

## Step 6. 보고(짧게)

- 대상 스레드, To/Cc
- 일시(요일 포함)
- 넣은 블록과 그 근거(상대 메일의 어느 언급 때문인지)
- 판단한 부분(종료시각, 경칭, 슬롯 밖 여부)
- 초안 링크
- 예약한 리마인더(실행 일시·작업 이름) — 있을 때
- 상대가 답을 요구했는데 이번 답장에 반영하지 못한 항목이 있으면 1줄로 플래그한다.

## 후속 회신(상대가 확정 답장을 보낸 뒤)

상황별 최소 문구 — 감사 1줄 + 아래 해당 줄 + (아직 요청 안 했으면 ⑥ 자료 요청 1줄) + `当日はどうぞよろしくお願い申し上げます。`

- 일정 확정 + 링크 수신 → 링크 수신 감사.
- 통역 불필요 확인 → `通訳の件、承知いたしました。質問票は事前にお送りいたします。`
- 통역 필요 → `通訳は弊社にて手配いたします。`
- 질문지 기한 지정 → `質問シートは{M}月{D}日（{曜}）午前中までにお送りいたします。` + Step 5b 리마인더 예약
- 참석자 풀네임·직함 문의 → ⑤ 참석자 블록
- 우리에게 링크 설정 요청 → `Google Meetのリンクは、質問票とあわせてミーティングの1～2日前までにお送りいたします。`

미팅이 확정되면(상대가 승낙):
- Google Calendar 등록을 제안한다(같은 일정이 이미 있는지 먼저 확인).
- IR 시트 반영은 `ir-tracker`로 넘긴다.
- 질문지 첨부 발송 메일은 `ir-question-prep` 산출물을 쓴다.

## 피드백 루프

common-rules §12를 따른다. 사용자가 문구를 손본 부분은 이 파일의 "쓰지 않는 표현"이나 해당 블록에 반영하도록 수정 지시를 남긴다.
