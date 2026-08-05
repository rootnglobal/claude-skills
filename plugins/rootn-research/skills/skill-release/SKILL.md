---
name: skill-release
version: 260805b
description: "RootN 커스텀 스킬의 SSOT(Git repo) 관리·검증·배포 스킬. 스킬을 수정/추가한 뒤 '스킬 릴리즈', '스킬 배포', '스킬 검증', '스킬 싱크', 'SSOT 체크', '스킬 버전 올려줘', '스킬 diff' 등의 키워드가 나오면 이 스킬을 사용할 것. 스킬 수정 작업을 마쳤을 때 이 스킬을 후속으로 제안한다. push 가능 여부는 세션마다 다르므로 추정하지 말고 '테스트 브랜치 빈 커밋 push' 1회로 먼저 판별한다."
---

# Skill Release — RootN 스킬 SSOT 관리·배포

## 저장소 구조 (SSOT = 이 Git repo 하나)

```
claude-skills/                  ← Git repo 루트 (Cowork 로컬)
├── _shared/
│   └── common-rules.md         ← 공통 규칙 canonical (복제 금지, 참조만)
├── _meta/
│   ├── check_skills.py         ← 검증기
│   ├── uploaded_manifest.json  ← 마지막 배포 시점의 claude.ai 업로드본 해시
│   └── CHANGELOG.md            ← 릴리즈 로그 (날짜·스킬·변경 요약)
└── skills/
    ├── ir-collertor/SKILL.md
    ├── investment-note/SKILL.md
    └── ... (스킬별 폴더, references/·scripts/·assets/ 포함)
```

원칙:
- **수정은 반드시 repo에서만 한다.** claude.ai 업로드본·다른 사본을 직접 고치지 않는다.
- 스킬을 고치면 그 SKILL.md frontmatter의 `version: YYMMDD`를 그날 날짜로 올린다.
- 공통 규칙 문구는 `_shared/common-rules.md`에서만 수정한다.
- 원격 SSOT: `https://github.com/rootnglobal/claude-skills-2.git` (branch `master`) — 이 원격이 단일 진실원이고,
  편집·pull·push는 **클라우드 작업본(`/tmp/claude-skills`)에서** 한다.
  - 동기화는 `skills-sync` 스킬(내부 `skills_sync.sh`)로 처리한다: Google Drive의 fine-grained PAT 파일
    (`rootn_gh_pat.txt`, Contents R/W·이 repo 한정·무기한)을 읽어 클라우드 컨테이너에서 clone/pull/push.
    데스크톱·핸드폰·블룸버그·헤드리스 어디서든 동일하게 동작한다.
  - **device_bash(기기 마운트)로 로컬 `.git`을 갱신하지 말 것** — 네트워크가 없고 덮어쓰기·삭제가 막혀 실패한다
    (구 방식의 'push 후 로컬 git pull' 단계는 폐기). 데스크톱 로컬 사본이 꼭 필요하면 사용자가 네이티브 터미널에서 pull한다.
  - 토큰은 Drive에만 두고 스킬·repo·로그에 남기지 않는다(출력 시 `github_pat_...` 마스킹).

## 0. 편집 전 SSOT 대조 (생략 금지 — 사고 1순위)

**세션 컨테이너에 설치된 스킬 사본(`/root/.claude/skills/<이름>/SKILL.md`, 플러그인 동기화본)은 SSOT보다 구버전일 수 있다.**
이 사본을 base로 고쳐서 push하면 그 사이 SSOT에 들어간 블록이 조용히 삭제된다.

```
bash <skills-sync>/skills_sync.sh pull        # 또는 clone → /tmp/claude-skills
diff /root/.claude/skills/<이름>/SKILL.md /tmp/claude-skills/skills/<이름>/SKILL.md
```

- diff가 비어 있지 않으면 **반드시 SSOT 파일을 base로 다시 편집한다.** 캐시본 편집분을 덮어쓰지 않는다.
- 260805 실측 사례: 캐시본 `peer-momentum-screener` v260721 vs SSOT v260721b — SSOT에만 있던
  「BEst 덤프 최우선」 블록이 캐시본에 없어, 캐시본을 그대로 올렸으면 삭제될 뻔했다(push 직전 diff로 포착).
- push가 막힌 세션에서 편집했다면 결과물은 **전체 파일 + `git diff` 패치 두 형태로** 내보낸다.
  패치가 0바이트로 나오면 이미 로컬 커밋된 상태이므로 `git diff HEAD~1 HEAD`를 쓴다.

## 0-1. 환경별 릴리즈 경로 (push 가능 여부가 환경마다 다름)

**push 가능 여부는 "클라우드냐 로컬이냐"로 갈리지 않는다. 세션마다 다르다. 추정하지 말고 테스트하라.**

260805 실측: 같은 날 같은 repo에 대해 **클라우드 Cowork 세션 A는 403, 클라우드 Cowork 세션 B는 push 성공**.
차이는 실행 위치가 아니라 **그 세션에 git 프록시 강제가 걸려 있는지**였다. 정적 표로 규칙화하면 틀린다.

### push 가능 여부 판별 — 항상 이 순서로

1. **환경 신호 확인**(참고용, 확정 아님)
   ```
   pwd; hostname; env | grep -iE 'CCR_(AGENT|TEST)_GITPROXY|https_proxy'
   ```
   - `pwd`가 **`/home/claude`**, hostname `vm`, `https_proxy=http://127.0.0.1:<port>` + `CCR_TEST_GITPROXY=1`
     → **클라우드 실행 + 프록시 강제**. push 막힐 가능성 높음.
   - `pwd`가 **`/sessions/<이름>`**(폴더는 `/sessions/<이름>/mnt/…`에 마운트)
     → **사용자 컴퓨터의 로컬 리눅스 VM**. 프록시 없음 → push 됨.
   - ⚠️ **세션이 자기 실행 위치를 잘못 보고하는 경우가 있다**(260805: 로컬 VM 세션이 스스로를 "클라우드 샌드박스"라고
     서술했으나 경로는 `/sessions/…`였고 push는 성공). **자기 진술이 아니라 `pwd`를 믿을 것.**
2. **확정 판별 — 테스트 브랜치에 빈 커밋 1회 push** (유일하게 믿을 수 있는 방법)
   ```
   git checkout -b test/push-check && git commit -q --allow-empty -m "push check"
   git push origin test/push-check && git push origin --delete test/push-check
   ```
   > **반드시 테스트 브랜치로.** master에 push하면 공개 배포 Action이 트리거된다.
3. 성공 → 그대로 릴리즈 진행. 403 → **재시도하지 말고** 아래 이관 경로로 전환.

### 403일 때의 이관 경로

| 대안 | push | 비고 |
|---|---|---|
| **Cowork를 "내 컴퓨터에서 실행"으로 새로 열기** | 됨 (260805 실측) | 데스크톱 앱 새 작업 시작 시 우측 상단 "Run this task" → On your computer. `pwd`가 `/sessions/…`면 제대로 잡힌 것 |
| 클라우드 Cowork 세션을 새로 열기 | 될 수도 있음 | 260805 실측 2회 모두 403. 기대치 낮음 |
| **claude.ai/code (웹)** | 가능 | repo 선택 단계가 authorized set을 채운다 → 프롬프트 → PR |
| **네이티브 CLI (로컬 터미널)** | 가능 | 프록시 없음. 헤드리스(`claude -p`) 자동화도 가능 |

- 403의 정체: git 프록시가 **세션 시작 시 확정되는 authorized repository set**에 든 repo에만 쓰기를 허용한다.
  오류 원문: `access denied by the git proxy: <repo> is not in this session's authorized repository set`.
  **읽기(clone/fetch/ls-remote)는 통과한다** — "읽기 허용, 쓰기는 명시 승인분만"의 유출 방지 설계.
  그래서 **403 세션에서도 PR 검증·SSOT 대조는 그대로 할 수 있다.**
- **PAT 문제가 아니다.** 같은 PAT로 읽기는 성공한다. 차단은 GitHub 도달 전 네트워크 계층에서 일어나며,
  그래서 **GitHub App 권한을 넓혀도 해결되지 않는다**(260805 실측: scope 확대 후 재시도해도 동일 403).
- `device_bash`(기기 브리지)는 **네트워크가 없어** 어느 세션에서도 push 경로가 아니다.
- 프록시를 우회하는 다른 전송(예: GitHub REST API를 curl로 호출)은 **쓰지 않는다.** 샌드박스 보안 통제 우회다.
- **읽기(fetch/ls-remote)는 Cowork에서도 된다.** PR 검증은 Cowork에서 직접 할 수 있다:
  `git fetch <url> refs/pull/<N>/head:refs/remotes/chk/prN` 후 `git diff origin/master...chk/prN`.

### claude.ai/code로 넘길 때 사용자에게 줄 것
1. 대상 repo·브랜치(`rootnglobal/claude-skills-2`, base `master`)
2. **변경 내용을 문장으로 서술한 프롬프트**(패치 첨부보다 이 방식이 안정적)
3. 첫 지시로 "먼저 master를 pull해 현재 파일을 읽고, 기존 블록을 지우지 말고 해당 부분만 정밀 수정하라"를 넣을 것

## 워크플로우

### 1. 검증 (수정 후 항상)
```
python3 _meta/check_skills.py --root skills/
```
문제(✗)가 0이 될 때까지 고친다. 검사 항목: version 헤더, 깨진 참조,
알려진 구버전 문구(drift 마커), 비표준 CC/발신 주소, 공통 규칙 참조 유무.

> 이 검증기는 CI 게이트와 **동일한 스크립트**다. 여기서 통과하면 배포 Action도 이 단계에서는 통과한다.
> Cowork에서 push를 못 하더라도 이 검증만은 반드시 로컬에서 돌려두고 넘긴다.

### 2. 커밋 → master
```
git add -A && git commit -m "skill: <스킬명> <변경 요약> (vYYMMDD)"
```
CHANGELOG.md에 한 줄 추가. push 불가 환경이면 0-1의 경로로 넘긴다.

### 3. 배포는 자동 (master push 시 GitHub Action)
`.github/workflows/repackage-marketplace.yml` — **master에 들어가면 사람이 할 일은 없다.**

```
master push
  → check_skills.py 게이트
  → 마켓플레이스 트리 빌드 (skills/ → plugins/rootn-research/skills/, _shared/ 복사)
  → plugin.json version = 1.YYMMDD.<run_number> 자동 주입
  → 검증: 매니페스트 JSON 파싱 / 스킬 10개 이상 / _shared 존재 / 자사 이메일 0건
  → 공개 repo rootnglobal/claude-skills 에 단일커밋 강제푸시(히스토리 0)
```

실패하는 지점은 사실상 둘뿐이다:
- `check_skills.py` ✗ → 1단계를 안 돌린 것
- **자사 도메인 이메일 잔존**(워크플로 정규식이 자사 두 도메인 주소를 grep) → 공개 배포 중단.
  스킬 본문에 담당자 메일을 직접 쓰지 말 것. **이 규칙을 설명하는 문서 자체도 예시 주소를 적으면 게이트에 걸린다.**

배포 확인(누구나, 인증 불필요):
```
git clone --depth 1 https://github.com/rootnglobal/claude-skills /tmp/pubchk
cat /tmp/pubchk/plugins/rootn-research/.claude-plugin/plugin.json   # version=1.YYMMDD.run
git -C /tmp/pubchk log -1 --format='%ci %s'                          # "publish from ...@<sha>"
```

### 4. 사용자 단말 반영 (유일한 수동 단계)
데스크톱 앱에서 플러그인 업데이트를 눌러야 새 버전이 세션에 로드된다.
`version` 값이 올라가야 앱이 업데이트를 감지하므로(260804 확인), Action의 version 주입이 빠지면 버튼이 비활성화된다.
반영 전 세션은 **구버전 스킬로 동작**한다 — 0단계의 캐시 drift가 여기서 생긴다.

### 5. (legacy) manifest 갱신 — zip 수동 업로드 방식을 쓸 때만
```
python3 - <<'PY'
import hashlib, json, os
root='skills'; man={'snapshot_date':'<오늘>','environment':'claude.ai uploaded skills','skills':{}}
for s in sorted(os.listdir(root)):
    d=os.path.join(root,s)
    if not os.path.isdir(d): continue
    files={}
    for dp,_,fs in os.walk(d):
        for f in sorted(fs):
            p=os.path.join(dp,f)
            files[os.path.relpath(p,d)]={'sha256_16':hashlib.sha256(open(p,'rb').read()).hexdigest()[:16],'bytes':os.path.getsize(p)}
    man['skills'][s]={'files':files}
json.dump(man,open('_meta/uploaded_manifest.json','w'),ensure_ascii=False,indent=1)
print('manifest updated')
PY
git add _meta/uploaded_manifest.json && git commit -m "meta: manifest sync"
```

## 새 스킬 추가 시
1. `skills/<이름>/SKILL.md` 생성 — frontmatter에 `name`, `version: YYMMDD`, `description`.
2. 워크플로우 첫 스텝에 `_shared/common-rules.md` 참조 한 줄.
3. check_skills.py 통과 → 커밋 → 업로드 → manifest 갱신.

## Self-review
- [ ] **편집 base가 SSOT인가?** (컨테이너 캐시본을 base로 쓰지 않았는가 — 0단계 diff 수행)
- [ ] version을 올렸는가? (내용을 고치고 version을 안 올리면 diff는 잡지만 이력이 안 남는다)
- [ ] check_skills.py 문제 0인가?
- [ ] 자사 이메일 0건인가? (공개 배포 게이트)
- [ ] push 가능 여부를 **테스트 브랜치 1회 push로 판별**했는가? (환경으로 추정하지 않았는가) 불가면 패치·프롬프트를 내보냈는가?
- [ ] master 반영 후 공개 repo의 plugin.json version이 올라갔는지 확인했는가?
- [ ] CHANGELOG에 한 줄 남겼는가?

## 상시 규칙
- 파괴적 작업 없음(로컬 파일·Git만). 단 데스크톱 앱의 플러그인 업데이트는 사용자가 직접 누른다.
- Fail-fast: 검증 스크립트 오류가 환경 문제(권한 등)면 2회 내 포기하고 사유 보고.
