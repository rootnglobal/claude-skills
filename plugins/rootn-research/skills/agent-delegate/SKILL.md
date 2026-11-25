---
name: agent-delegate
version: 261125b
description: "데스크톱 Claude Code가 하위 작업을 Codex(독립 검증·리뷰, read-only)나 Grok xAI API(한도 소진 시 폴백·X 언급 확인)에 헤드리스로 맡기고 결과를 md 파일로 회수해 종합하는 절차. 트리거: Codex로 검증해줘, 교차 검증, 다른 에이전트에 맡겨, Grok으로 X 언급 확인, 한도 소진 폴백, 멀티에이전트 위임."
---

# agent-delegate — 하위 작업 위임·회수

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, 신뢰도 표기, 스크립트 출력 규약(§14). 태스크 완료 후 스킬 피드백 루프(§12)를 한 번 점검한다.

업무 데스크톱 Claude Code(허브)가 작업 중 필요한 때만 다른 에이전트에 하위 작업을 맡기고 결과를 파일로 회수한다. 호출은 `scripts/codex_delegate.py`·`scripts/grok_delegate.py`(Python 3.10, 표준 라이브러리)로 한다. 두 스크립트 모두 stdout에 요약 JSON 1줄을 출력하고 결과 본문은 `--out` 파일에 쓴다.

## 1. 역할

| 에이전트 | 역할 | 쓰지 않는 경우 |
|---|---|---|
| Claude(허브) | 조율·최종 판단·종합 | — |
| Codex(`codex exec`, ChatGPT 구독) | 독립 검증(숫자 재계산·논리·누락), 리서치용 스크립트 리뷰. read-only | 스킬 repo 코드 리뷰 — 기존 Codex PR 리뷰 흐름(codex/ 브랜치 → PR → 자동 리뷰)을 그대로 쓴다 |
| Grok(xAI API) | ① Claude·Codex 한도 소진 시 폴백 ② X 언급 확인(`x_search`) | 그 밖의 용도(사용자 결정 2026-11-24). Grok 구독 웹 화면 자동화는 하지 않는다 |

Gemini는 보류 상태라 위임 대상이 아니다.

## 2. 넘길 수 있는 자료

- 기본값: 두 에이전트 모두 **인증정보와 고객 개인정보만 빼고** 리서치 자료(공개 자료, 리서치 초안·노트, 계산·수치)를 넘긴다.
  - 빼는 것 ① 인증정보: 비밀번호·API 키·토큰·쿠키·secret이 든 설정값 ② 고객 데이터: 고객 이름·연락처·계좌 등 개인을 알아볼 수 있는 정보.
  - 유료 구독 원문(셀사이드·CapIQ·Bloomberg)은 이용 조건 때문에 통째로 넘기지 않고, 필요한 발췌·수치만 넘긴다.
- `grok_delegate.py`는 프롬프트·첨부에서 키·토큰·비밀번호 패턴이 보이면 호출하지 않고 exit 6(`secret_detected`, 패턴 이름·파일·줄 번호만 출력)으로 끝난다. 해당 줄을 지우거나 가린 뒤 다시 호출한다. 이름 같은 개인정보는 패턴으로 잡히지 않으므로 넘기기 전에 Claude가 뺀다.
- 인증정보·고객 개인정보를 빼면 성립하지 않는 작업은 위임하지 않고 "검증 보류"로 보고한다.
- 데이터 등급 규칙이 _config에 따로 정해져 있으면 그쪽이 우선한다.

## 3. 공통 호출 규칙

- **자기완결 프롬프트**: 하위 에이전트는 대화 맥락을 모른다. 목적·판정 기준·출력 형식(항목별 OK/이상/자료 없음 + 근거 위치)을 프롬프트에 적고, 근거 파일은 `--attach`로 넘긴다(스크립트가 본문에 끼워 넣는다).
- **근거 직접 제공·웹 검색 금지**: 스크립트가 "주어진 자료만 사용, 없으면 'not in material'" 규칙을 앞에 붙인다(`--no-guard`로 끌 수 있으나 기본 유지). Codex 호출 토큰의 절반가량이 자체 웹 검색에서 나왔다(2026-11-24 측정).
- **질문 묶기**: Codex는 호출마다 고정 입력 약 2.3~2.5만 토큰이 든다. 검증 질문은 한 프롬프트에 번호를 붙여 묶고 1회에 보낸다.
- **출력 위치**: `<작업 폴더>/_delegate/<YYMMDD>_<task>_<agent>.md`. 파일 첫 줄에 에이전트·모델·소요시간·토큰/비용 주석이 붙는다.
- **타임아웃**: Codex 기본 900초, Grok 120초. 실패(`status` ≠ ok)면 1회만 재시도하고, 다시 실패하면 건너뛰고 보고한다.
- **작업당 호출 상한**: Codex 2회(재시도 포함), Grok 폴백 2회, Grok `x_search` 1회.

## 4. Codex — 독립 검증

```
python -X utf8 scripts/codex_delegate.py --task <id> --prompt-file <prompt.md> --attach <근거1.md> <근거2.md> --out <작업폴더>/_delegate/<YYMMDD>_<id>_codex.md
```

- 스크립트가 빈 임시 폴더에서 `codex exec --sandbox read-only --skip-git-repo-check --ignore-user-config --ignore-rules --ephemeral -c web_search=disabled --json -o <file> -`를 실행한다. repo 폴더를 열지 않아 AGENTS.md·파일 탐색이 없다. 첨부는 파일 복사가 아니라 본문에 넣는다(read-only 샌드박스가 파일 읽기를 막은 사례, 2026-11-24).
- exit 3(`status: limit`) = 구독 한도 소진. 계정 전환은 하지 않는다. §2 조건을 지키는 작업이면 Grok 폴백(§5-1), 아니면 검증 보류로 보고한다.
- 결과 판정은 Claude가 한다. Codex 지적은 근거 위치를 원자료에서 직접 확인한 뒤에만 반영한다.

## 5. Grok — xAI API

키는 환경변수 `XAI_API_KEY`에서만 읽는다(값 출력·로깅 금지). 성공한 호출마다 사용 로그(`GROK_USAGE_LOG`, 기본 `~/.rootn/grok_usage.jsonl`)에 시각·task·모델·토큰·비용(USD, 응답의 `cost_in_usd_ticks` 기준)을 1줄 남긴다. 프롬프트 본문은 남기지 않는다. 이번 달 로그 합계가 월 상한(`GROK_MONTHLY_CAP_USD`, 기본 100)에 닿으면 스크립트가 호출을 거부한다(exit 4). 호출 전에 프롬프트·첨부의 인증정보 패턴(키 접두어·봇 토큰·개인키·`password=` 형태)을 검사해 보이면 보내지 않는다(exit 6, §2).

### 5-1. 폴백 (Claude·Codex 한도 소진 시)

```
python -X utf8 scripts/grok_delegate.py --role fallback --task <id> --model grok-4.3 --prompt-file <prompt.md> --attach <근거.md> --out <작업폴더>/_delegate/<YYMMDD>_<id>_grok.md
```

- 기본 모델은 grok-4.3(저가). 추론이 긴 검증만 `--model grok-4.5`.
- 결과 md와 보고에 "폴백(Grok)"을 표시한다. 폴백 결과는 한도가 돌아오면 Claude가 다시 확인할 항목으로 남긴다.

### 5-2. X 언급 확인 (`x_search`, 작업당 1회)

```
python -X utf8 scripts/grok_delegate.py --role x-check --x-search --task <id> --model grok-4.3 --prompt-file <prompt.md> --out <작업폴더>/_delegate/<YYMMDD>_<id>_grok_x.md
```

- `--task`가 필수이고, 같은 task로 `x_search`를 이미 썼으면 스크립트가 거부한다(exit 5). 질문(종목명·코드·기간·찾을 주제)을 한 프롬프트에 모두 넣는다.
- 비용은 가져온 게시물 수에 비례한다(2026-11 단가 약 $5/1천 건, 실측 1회 약 $0.09). 결과 보고에 그 호출의 비용(`cost_usd`)을 적는다.
- 결과는 회사 공식 발언 / 전문가 의견 / 커뮤니티 추측으로 나누고, 각 항목에 게시물 URL·날짜를 붙인다. 사실이 아니라 해석·가설로 다루고, 숫자는 공시·IR 원자료로 확인하기 전에는 결론에 쓰지 않는다.
- `--x-from YYYY-MM-DD`(`x_search` from_date)는 아직 검증하지 않은 파라미터다. 처음 쓸 때 오류가 나면 빼고 기간은 프롬프트에 적는다.

## 6. 종합·보고

- 종합본에서 결과마다 출처 에이전트를 표기한다(예: `[Codex 검증]`, `[Grok X 2026-11-20]`, `[폴백(Grok)]`).
- 에이전트끼리 결론이 다르면 원자료로 판정하고, 판정 근거를 1줄 남긴다.
- 보고에 넣을 것: 에이전트별 호출 수·status·소요시간, Codex 토큰, Grok 비용과 이번 달 누계(`month_usd`), 실패·보류 항목과 사유, 결과 md 경로.
