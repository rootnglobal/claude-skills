---
name: skills-sync
version: 261021
description: >-
  RootN claude-skills SSOT(private repo rootnglobal/claude-skills-2)를 어느 환경(순수
  클라우드·핸드폰·블룸버그 PC·데스크톱)에서도 GitHub와 동기화하는 스킬. Google Drive에 저장된
  GitHub PAT 파일(rootn_gh_pat.txt)을 읽어 클라우드 컨테이너에서 repo를 pull/push한다.
  "스킬 pull", "스킬 동기화", "claude-skills 당겨줘/올려줘", "skills sync", "SSOT 동기화",
  "스킬 최신으로", "스킬 GitHub에 올려줘" 등의 맥락에서 사용할 것. RootN 리서처 전용.
---

# skills-sync — 클라우드 인증 git 동기화

> **공통 규칙**: 작업 시작 전 `_shared/common-rules.md`(로컬 실행 시 스킬 폴더 기준 `../_shared/common-rules.md`)를 읽고 전 구간에 적용한다.

## 핵심 원리
- 단일 진실원(SSOT)은 **GitHub private repo** `rootnglobal/claude-skills-2` (branch: master).
- 모든 네트워크 git 작업은 **클라우드 컨테이너(Bash)**에서 수행한다. device_bash는 네트워크가 없고,
  기기 마운트는 **덮어쓰기·삭제 불가(생성만 가능)**이므로 데스크톱 로컬 폴더의 in-place `git`
  (reset/fetch/pull) 은 **절대 시도하지 말 것** — 반드시 실패하고 lock 잔해만 남긴다.
- 인증은 Google Drive에 저장된 fine-grained PAT(`rootn_gh_pat.txt`, Contents read/write, 무기한)로 한다.
  Drive에 있으므로 데스크톱·핸드폰·블룸버그·헤드리스 어디서든 같은 방식으로 읽힌다.

## 절차

### 1) Drive에서 PAT 읽기
- Google Drive MCP로 `title contains 'rootn_gh_pat'` 검색 → 파일 id 확보.
- 파일 내용(텍스트)을 읽어 토큰 문자열을 얻는다. (`read_file_content` / `download_file_content`)
- 토큰을 로그·응답에 절대 출력하지 말 것. 아래처럼 파일로만 넘긴다.

### 2) 동기화 스크립트 준비
아래 스크립트를 `/tmp/skills_sync.sh`에 쓰고 `chmod +x` 한다. (scripts/skills_sync.sh 와 동일)
Drive에서 읽은 토큰은 `/tmp/.gh_pat`에 `umask 077`로 저장한 뒤 env로 넘긴다.

```bash
umask 077; printf '%s' '<DRIVE에서_읽은_토큰>' > /tmp/.gh_pat
export GH_PAT="$(cat /tmp/.gh_pat)"
/tmp/skills_sync.sh status   # 로컬 vs 원격 비교
/tmp/skills_sync.sh pull     # 최신 master 받기 (WORK=/tmp/claude-skills)
/tmp/skills_sync.sh push "커밋 메시지"   # 수정분 커밋+push
```
출력에서 토큰이 새지 않도록 항상 `sed -E 's/github_pat[_][A-Za-z0-9_]+/***/g'` 로 필터링해 보여준다.

### 3) 작업 위치
- pull 결과 작업본은 클라우드의 `/tmp/claude-skills` 이다. 스킬 편집·검증·빌드는 여기서 한다.
- master push가 곧 배포다(CI가 marketplace로 발행). claude.ai 업로드본은 만들지 않는다.
- **push 전 반드시** repo `CLAUDE.md`의 검증(`python3 _meta/check_skills.py --root skills/` ✗ 0개, `_ops/` 수정 시 `py_compile`, 식별자 grep 0건)을 작업본에서 통과시킨다. 실패하면 push하지 않는다.
- 편집 후 GitHub 반영은 `push` 액션으로 한다. force-push·히스토리 재작성 금지.

### 4) 데스크톱 로컬 폴더가 꼭 필요할 때만
데스크톱 사용자가 로컬 폴더 자체를 최신으로 원하면, 클라우드에서 만든 파일을
`device_commit_files`로 **개별 파일 생성/덮어쓰기**해 전달하거나(마운트는 device_commit_files
경로로는 덮어쓰기 가능), 사용자가 자기 Windows 터미널에서 네이티브로 `git pull` 하도록 안내한다.
device_bash로 로컬 `.git`을 갱신하려 하지 말 것.

## 주의
- repo 이름 주의: 원격은 `claude-skills-2`(private SSOT). `claude-skills`는 CI가 만드는 public 배포본이라 직접 push 금지.
- 실패 시 fail-fast: 소스당 1~2회만. 같은 동작 3회 반복 금지.
