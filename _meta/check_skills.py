#!/usr/bin/env python3
"""
RootN 스킬 SSOT 검증기.
사용법:
  python3 check_skills.py --root <SSOT repo의 skills/ 경로>          # 정합성 검사
  python3 check_skills.py --root <경로> --manifest uploaded_manifest_260710.json  # 배포 diff
검사 항목:
  1) frontmatter version: YYMMDD 존재
  2) 깨진 상대 참조 (references/, scripts/, assets/ 파일 존재 여부)
  3) 알려진 drift 마커 (구버전 문구)
  4) 스킬 간 파라미터 일치 (CC 주소, 핵심질문 개수, 수집 기간)
  5) manifest 비교 → 재업로드 필요한 스킬 목록
종료코드: 문제 있으면 1.
"""
import argparse, hashlib, json, os, re, sys

DRIFT_MARKERS = {
    # 구버전임을 뜻하는 문구: (스킬, 패턴, 설명)
    ("ir-collertor", r"최근 1년", "수집 기간은 2년으로 통일됨 (26-07-08 결정)"),
    ("ir-collertor", r"명시적 허가 필요", "다운로드는 기본 자동 진행으로 변경됨"),
    ("fnguide-report-downloader", r"최근 1년", "수집 기간은 2년으로 통일됨"),
    ("ir-research-pipeline", r"핵심질문 10개", "ir-question-prep 기준(Top 4~5)으로 통일"),
    ("ir-research-pipeline", r"최근 1년", "수집 기간은 2년으로 통일됨"),
}
# 스킬 문서에 이 문구가 '있어야' 최신 (없으면 경고)
REQUIRED_MARKERS = {
    ("*", r"common-rules\.md", "공통 규칙 참조가 없음 — SSOT 전환 후 각 스킬은 _shared/common-rules.md를 참조해야 함"),
}
CC_ALLOWED = set()  # 자사 개인주소 하드코딩 금지 → _config/sender.txt 참조
SELF_DOMAINS = ("rootnwm.com", "rootnglobal.com")

def frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---", txt, re.S)
    return m.group(1) if m else ""

def check(root, manifest_path=None):
    problems, warnings = [], []
    skills = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and not d.startswith("_"))
    for s in skills:
        sk = os.path.join(root, s, "SKILL.md")
        if not os.path.exists(sk):
            problems.append(f"[{s}] SKILL.md 없음"); continue
        txt = open(sk, encoding="utf-8", errors="replace").read()
        fm = frontmatter(txt)
        # 1) version
        if not re.search(r"^version:\s*\d{6}", fm, re.M):
            problems.append(f"[{s}] frontmatter에 version: YYMMDD 없음")
        # 2) 상대 참조
        for ref in re.findall(r"(?:references|scripts|assets)/[\w\-.가-힣]+\.\w+", txt):
            if not os.path.exists(os.path.join(root, s, ref)):
                # 다른 스킬/퍼블릭 스킬 경로 언급일 수 있음 → 절대경로 힌트 없으면 문제로
                if "/mnt/skills" not in txt[max(0, txt.find(ref)-80):txt.find(ref)]:
                    problems.append(f"[{s}] 깨진 참조: {ref} (폴더에 파일 없음, 외부 경로면 절대경로로 명시할 것)")
        # 3) drift 마커
        for skill, pat, why in DRIFT_MARKERS:
            if skill == s and re.search(pat, txt):
                problems.append(f"[{s}] 구버전 문구 '{pat}' — {why}")
        for skill, pat, why in REQUIRED_MARKERS:
            if (skill == "*" or skill == s) and not re.search(pat, txt):
                warnings.append(f"[{s}] {why}")
        # 4) 자사 개인주소 하드코딩 금지 (→ _config/sender.txt 참조)
        for cc in re.findall(r"[\w.\-]+@[\w.\-]+", txt):
            dom = cc.split("@")[1] if "@" in cc else ""
            if any(d in dom for d in SELF_DOMAINS):
                warnings.append(f"[{s}] 자사 개인주소 하드코딩: {cc} — _config/sender.txt 참조로 이동")
    # 5) manifest 비교
    if manifest_path:
        man = json.load(open(manifest_path))
        redeploy = []
        for s in skills:
            if s not in man["skills"]:
                continue  # NEW로만 표기
            cur = {}
            sdir = os.path.join(root, s)
            for dp, _, fs in os.walk(sdir):
                for f in sorted(fs):
                    rel = os.path.relpath(os.path.join(dp, f), sdir)
                    cur[rel] = hashlib.sha256(open(os.path.join(dp, f), "rb").read()).hexdigest()[:16]
            up = {k: v["sha256_16"] for k, v in man["skills"].get(s, {}).get("files", {}).items()}
            if cur != up:
                redeploy.append(s)
        new = [s for s in skills if s not in man["skills"]]
        removed = [s for s in man["skills"] if s not in skills]
        print("\n== 배포 diff (claude.ai 재업로드 필요) ==")
        for s in redeploy: print(f"  UPDATE : {s}")
        for s in new:      print(f"  NEW    : {s}")
        for s in removed:  print(f"  REMOVED(업로드본에만 존재): {s}")
        if not (redeploy or new or removed): print("  (동기화 상태)")
    print("\n== 문제 ==" if problems else "\n== 문제 없음 ==")
    for p in problems: print("  ✗", p)
    if warnings:
        print("== 경고 ==")
        for w in warnings: print("  △", w)
    return 1 if problems else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--manifest")
    a = ap.parse_args()
    sys.exit(check(a.root, a.manifest))
