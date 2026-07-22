---
name: skill-release
version: 260721
description: "RootN 커스텀 스킬의 SSOT(Git repo) 관리·검증·배포 스킬. 스킬을 수정/추가한 뒤 '스킬 릴리즈', '스킬 배포', '스킬 검증', '스킬 싱크', 'SSOT 체크', '스킬 버전 올려줘', '스킬 diff' 등의 키워드가 나오면 이 스킬을 사용할 것. 스킬 수정 작업을 마쳤을 때 이 스킬을 후속으로 제안한다."
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

## 워크플로우

### 1. 검증 (수정 후 항상)
```
python3 _meta/check_skills.py --root skills/
```
문제(✗)가 0이 될 때까지 고친다. 검사 항목: version 헤더, 깨진 참조,
알려진 구버전 문구(drift 마커), 비표준 CC/발신 주소, 공통 규칙 참조 유무.

### 2. 배포 diff
```
python3 _meta/check_skills.py --root skills/ --manifest _meta/uploaded_manifest.json
```
`UPDATE/NEW`로 표시된 스킬만 claude.ai에 재업로드하면 된다.

### 3. 커밋
```
git add -A && git commit -m "skill: <스킬명> <변경 요약> (vYYMMDD)"
```
CHANGELOG.md에 한 줄 추가.

### 4. claude.ai 업로드 (수동 단계)
claude.ai Settings > Capabilities > Skills 에서 diff에 나온 스킬의 zip을 교체 업로드한다.
zip 생성:
```
cd skills && for s in <스킬명들>; do (cd "$s" && zip -r "../${s}.zip" .); done
```
> 업로드는 브라우저 수동 작업이다. Claude in Chrome으로 자동화하지 않는다
> (파일 선택 다이얼로그·계정 설정 접근은 사전 확인 대상).

### 5. manifest 갱신 (배포 완료 직후 — 잊으면 diff가 계속 뜬다)
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
- [ ] version을 올렸는가? (내용을 고치고 version을 안 올리면 diff는 잡지만 이력이 안 남는다)
- [ ] check_skills.py 문제 0인가?
- [ ] 배포 후 manifest를 갱신했는가?
- [ ] CHANGELOG에 한 줄 남겼는가?

## 상시 규칙
- 파괴적 작업 없음(로컬 파일·Git만). 단 claude.ai 업로드본 교체는 사용자가 직접 한다.
- Fail-fast: 검증 스크립트 오류가 환경 문제(권한 등)면 2회 내 포기하고 사유 보고.
