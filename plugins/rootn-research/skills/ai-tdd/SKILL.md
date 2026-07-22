---
name: ai-tdd
version: 260721
description: |
  AI 코딩 설계-주도 개발(Design-Driven Development) 스킬 v2.0.
  파일 기반 맥락 외부화 + TDD + Git 마일스톤 + 표준 로깅의 통합 워크플로우.
  
  7-파일 프레임워크(1prd → 2design → 3todo → 4logging → 5test → 6gitops → 7buglog)를
  프로젝트 루트에 생성하고, 설계 → 구현 → 테스트 → 커밋의 사이클을 반복 실행합니다.
  
  핵심 원칙: 프롬프트 창에는 명령만, 맥락은 .md 파일에 담는다.
  AI의 휘발성 기억을 파일로 외부화하여 세션 간 맥락을 완벽히 보존합니다.
  
  트리거 조건: "TDD로 개발해줘", "설계-주도 개발", "7-파일 프레임워크",
  "AI TDD", "프로젝트 설계해줘", "PRD 작성해줘", "설계 문서 만들어줘",
  "TDD 사이클", "테스트 먼저", "설계부터 시작", "프로젝트 세팅해줘",
  "새 프로젝트 시작", "AI 코딩 워크플로우", "맥락 외부화",
  "design-driven", "DDD 방식으로", "7파일", "설계 계약서"
---

# AI 코딩 설계-주도 개발 (Design-Driven Development) v2.0

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다 — fail-fast, 자동진행/사전확인, ASCII 파일명, 드라이브 3점 검증, 신뢰도 표기, 수집기간 기본 2년. 그리고 **태스크 완료 후 스킬 피드백 루프(§12)**: 최종 산출물 전달 직후(태스크 단위 1회) 새로 확인된 소스·URL·우회법, 반복된 실패 패턴, 사용자가 수동으로 고친 부분을 점검한다. 개선점이 있으면 업로드본 SKILL.md를 즉석 수정하고 동일 diff를 SSOT repo(claude-skills)에 반영한다 (repo 미접근 환경이면 diff를 출력해 "다음 Cowork 세션에서 repo 반영 필요"로 flagging). 없으면 "스킬 업데이트 없음" 한 줄로 종료한다.


## Overview

이 스킬은 AI 코딩의 근본적 한계(맥락 소실, 구조 침식, 테스트 부재, 롤백 불가)를 해결하는
**파일 기반 설계-주도 개발 워크플로우**입니다.

7개의 .md 파일이 AI의 외부 기억 장치 역할을 하며, TDD + Git 마일스톤으로 안전망을 구축합니다.

### 핵심 원칙

- **프롬프트 3줄 원칙**: 프롬프트에는 명령만, 맥락은 .md 파일에 담는다
- **코드 전 설계**: 2design.md 확정 전 코드 작성 절대 금지
- **테스트 통과 = 커밋**: 테스트 실패 상태에서는 절대 커밋하지 않는다
- **1 TODO = 1 커밋**: 한 커밋에 여러 기능을 넣지 않는다
- **표준 로깅 강제**: console.log/print 금지, 반드시 로거 모듈만 사용

---

## File Structure

```
ai-tdd/
├── SKILL.md              # 이 파일 (실행 지침)
├── AI_TDD_Guide_v2.md    # 전체 방법론 레퍼런스 (참조용)
├── 1prd.md               # 요구사항 정의 템플릿
├── 2design.md            # 아키텍처 및 상세 설계 템플릿
├── 3todo.md              # 작업 분해 체크리스트 템플릿
├── 4logging.md           # 표준 로깅 모듈 명세 템플릿
├── 5test.md              # 테스트 케이스 템플릿
├── 6gitops.md            # Git 버전 관리 규칙 템플릿
└── 7buglog.md            # 버그 추적 및 학습 기록 템플릿
```

---

## Workflow

### 분석 유형 판별

**Option A: 새 프로젝트 시작 (Full Pipeline)**
→ "새 프로젝트 시작해줘", "처음부터 설계해줘"
→ Phase 0~7 전체 실행

**Option B: 기존 프로젝트 구현 이어하기 (Resume)**
→ "이어서 작업해줘", "세션 복구"
→ Phase R(복구) → 구현 루프

**Option C: 버그 수정 (Bugfix)**
→ "버그 발생", "에러 수정해줘"
→ Phase B(버그 수정 워크플로우)

---

### Phase 0: 프로젝트 초기화

7개 템플릿 파일을 이 스킬 폴더에서 프로젝트 루트로 복사한다.

```bash
# 스킬 폴더에서 프로젝트 루트로 템플릿 복사
cp /mnt/skills/user/ai-tdd/1prd.md ./
cp /mnt/skills/user/ai-tdd/2design.md ./
cp /mnt/skills/user/ai-tdd/3todo.md ./
cp /mnt/skills/user/ai-tdd/4logging.md ./
cp /mnt/skills/user/ai-tdd/5test.md ./
cp /mnt/skills/user/ai-tdd/6gitops.md ./
cp /mnt/skills/user/ai-tdd/7buglog.md ./
```

---

### Phase 1: 요구사항 정의 (1prd.md)

사용자에게 질문하여 `1prd.md` 템플릿의 모든 항목을 채운다.

**실행 방법:**
1. `1prd.md`를 읽는다
2. 각 항목(프로젝트 개요, 핵심 기능, 기술 스택, 제약 조건, 성공 기준)에 대해 
   사용자에게 **한 번에 하나씩** 질문한다
3. 답변을 받아 `1prd.md`에 기록한다
4. 모든 항목이 채워질 때까지 반복한다

**금지 사항:**
- 이 단계에서 코드를 작성하지 않는다
- 한 번에 여러 질문을 하지 않는다

---

### Phase 2: 설계 대화 (2design.md)

`1prd.md`를 기반으로 아키텍처와 상세 설계를 확정한다.

**실행 순서:**
1. `1prd.md`를 읽고 아키텍처를 **3가지** 제안한다 (장단점, 트레이드오프 포함)
2. 사용자가 선택하면 모듈 구조를 확정한다
   - 각 모듈의 책임
   - 공개 인터페이스 (함수명, 인자 타입, 반환 타입)
   - 모듈 간 의존 관계
3. 위험 요소를 **5가지** 찾아 대응 방안과 함께 기록한다
4. 모든 내용을 `2design.md`에 기록한다

**금지 사항:**
- 이 단계에서 코드를 작성하지 않는다
- 아키텍처를 1가지만 제시하지 않는다

---

### Phase 3: 로깅 표준 정의 (4logging.md)

`4logging.md` 템플릿을 기반으로 로깅 표준을 확정한다.

**필수 정의 항목:**
- 5개 로그 레벨 (DEBUG, INFO, WARN, ERROR, FATAL)
- 표준 로그 포맷: `[YYYY-MM-DD HH:mm:ss.SSS] [LEVEL] [MODULE] [FUNCTION] MESSAGE {context}`
- 모듈별 로깅 규칙 (어떤 이벤트를 어떤 레벨로)
- 민감 정보 마스킹 규칙

---

### Phase 4: 작업 분해 (3todo.md)

`2design.md`를 기반으로 `3todo.md`를 작성한다.

**규칙:**
- 각 항목은 **단일 함수 단위**로 분해한다
- Phase별로 그룹핑한다 (Phase 1~5 → v0.1.0~v1.0.0)
- 로깅 모듈 구현은 항상 Phase 1 첫 번째 항목이다

---

### Phase 5: 테스트 설계 (5test.md)

각 기능에 대해 4가지 범주의 테스트 케이스를 설계한다.

**필수 4가지 범주:**
1. 정상 경로 (Happy Path)
2. 경계값 (Boundary)
3. 에러 케이스 (Error)
4. 상태 전이 (State)

---

### Phase 6: Git 초기화 (6gitops.md)

`6gitops.md` 규칙을 확정하고 Git을 초기화한다.

```bash
git init
git add .
git commit -m "chore: 프로젝트 초기화 - 7-파일 프레임워크 세팅"
git tag v0.0.0
```

---

### Phase 7: 구현 루프 (반복)

**RED → GREEN → REFACTOR → COMMIT 사이클을 반복한다.**

```
1. 3todo.md에서 다음 미완료 항목 확인
2. 5test.md에서 해당 항목의 테스트 먼저 작성 (RED — 실패 확인)
3. 최소한의 코드로 테스트 통과 + 4logging.md 표준 로깅 적용 (GREEN)
4. 2design.md 규칙 준수하며 리팩토링 (REFACTOR)
5. 전체 테스트 통과 확인
6. 6gitops.md 규칙에 따라 커밋
7. 3todo.md에 체크 표시
8. Phase 내 모든 항목 완료 시 태그 (v0.X.0)
9. 1번으로 돌아간다
```

**필수 체크:**
- [ ] 테스트가 RED 상태에서 시작했는가?
- [ ] console.log/print를 사용하지 않았는가?
- [ ] 2design.md의 인터페이스 정의를 따랐는가?
- [ ] 전체 테스트(기존 + 신규)가 통과했는가?
- [ ] 커밋 메시지가 6gitops.md 규칙을 따랐는가?

---

### Phase R: 세션 복구 (대화 끊김 후)

```
1. 1prd.md, 2design.md, 3todo.md를 순서대로 읽고 현재 상황 요약
2. 4logging.md, 6gitops.md 규칙 확인
3. git log --oneline -10으로 최근 커밋 확인
4. 3todo.md에서 미완료 항목 파악
5. Phase 7 구현 루프로 진입
```

---

### Phase B: 버그 수정 워크플로우

```
1. fix/BUG-NNN 브랜치 생성
2. [ERROR] 로그 분석으로 원인 파악
3. 5test.md 회귀 섹션에 재현 테스트 추가
4. 최소 범위로 수정 (다른 파일 건드리지 않음)
5. 전체 테스트 통과 확인
6. 7buglog.md에 기록 (증상, 근본 원인, 수정, 재발 방지)
7. 커밋 → dev에 머지 → fix 브랜치 삭제
```

**패턴 승격 규칙:** 같은 패턴의 버그가 3회 이상 반복되면 `2design.md`의 규칙으로 승격한다.

---

## Critical Rules

1. **설계 선행**: 2design.md 확정 전 코드 작성 절대 금지
2. **로깅 선행**: 로깅 모듈이 Phase 1에서 가장 먼저 구현되어야 한다
3. **테스트 먼저**: 항상 RED에서 시작. 테스트 없는 구현 금지
4. **표준 로거 강제**: console.log, print 사용 시 즉시 수정
5. **커밋 = 안전 지점**: 테스트 실패 상태 커밋 금지
6. **1 TODO = 1 커밋**: 여러 기능을 한 커밋에 넣지 않는다
7. **파일에 기록**: 합의 사항, 설계 변경, 버그 기록은 반드시 해당 .md 파일에 반영
8. **인터페이스 준수**: 2design.md의 모듈 인터페이스를 임의로 변경하지 않는다
9. **범위 제한**: 요청받은 파일만 수정. 다른 파일을 임의로 건드리지 않는다
10. **한글 소통**: 모든 문서와 커밋 메시지는 한글 (기술 용어 영문 병기)

---

## Anti-Patterns (금지 패턴)

- ❌ "전체 앱을 한 번에 만들어줘" → 모듈 단위로 쪼개서 요청
- ❌ PRD에서 바로 TODO로 직행 → 반드시 2design.md를 거친다
- ❌ console.log 방치 → 4logging.md 표준 로거만 사용
- ❌ 커밋 없이 다음 기능으로 → 테스트 통과 즉시 커밋
- ❌ 여러 기능을 한 커밋에 → 1 TODO = 1 커밋
- ❌ 버그 수정 후 기록 생략 → 반드시 7buglog.md에 기록

---

## Reference

상세 방법론은 `AI_TDD_Guide_v2.md`를 참조한다.
각 Phase의 템플릿 구조와 빈칸 항목은 해당 번호의 .md 파일을 참조한다.
