#!/usr/bin/env bash
# skills_sync.sh — cloud-side authenticated git for the RootN skills SSOT.
# Runs in ANY Claude cloud session (desktop / phone / Bloomberg / headless).
# The PAT is NEVER hardcoded: it is read from an env var the caller exports
# after fetching it from Google Drive (rootn_gh_pat.txt).
#
# Usage:
#   GH_PAT=xxxx ./skills_sync.sh pull            # fetch latest master into WORK
#   GH_PAT=xxxx ./skills_sync.sh push "msg"      # commit all + push to master
#   GH_PAT=xxxx ./skills_sync.sh status          # show local vs remote
#
set -euo pipefail

REPO_HOST="github.com/rootnglobal/claude-skills-2.git"
BRANCH="master"
WORK="${SKILLS_WORK:-/tmp/claude-skills}"
ACTION="${1:-pull}"

: "${GH_PAT:?GH_PAT env var required (read it from Drive rootn_gh_pat.txt first)}"
AUTH_URL="https://${GH_PAT}@${REPO_HOST}"
CLEAN_URL="https://${REPO_HOST}"

# quiet helper so the token never lands in logs
scrub_remote() { git -C "$WORK" remote set-url origin "$CLEAN_URL" 2>/dev/null || true; }

ensure_clone() {
  if [ ! -d "$WORK/.git" ]; then
    git clone --quiet "$AUTH_URL" "$WORK"
    scrub_remote
  fi
}

case "$ACTION" in
  pull)
    ensure_clone
    git -C "$WORK" remote set-url origin "$AUTH_URL"
    git -C "$WORK" fetch --quiet origin "$BRANCH"
    git -C "$WORK" reset --hard "origin/$BRANCH"
    scrub_remote
    echo "PULLED -> $(git -C "$WORK" log --oneline -1)"
    ;;
  push)
    ensure_clone
    MSG="${2:?commit message required for push}"
    git -C "$WORK" add -A
    if git -C "$WORK" diff --cached --quiet; then
      echo "NOCHANGE -> nothing to commit"
    else
      # 커밋 이메일은 env SKILLS_GIT_EMAIL(없으면 컨테이너 git 기본값). 주소를 스크립트에 적지 않는다.
      git -C "$WORK" ${SKILLS_GIT_EMAIL:+-c user.email="$SKILLS_GIT_EMAIL"} \
                     -c user.name="RootN Research" commit --quiet -m "$MSG"
      git -C "$WORK" remote set-url origin "$AUTH_URL"
      git -C "$WORK" push --quiet origin "$BRANCH"
      scrub_remote
      echo "PUSHED -> $(git -C "$WORK" log --oneline -1)"
    fi
    ;;
  status)
    ensure_clone
    git -C "$WORK" remote set-url origin "$AUTH_URL"
    git -C "$WORK" fetch --quiet origin "$BRANCH"
    scrub_remote
    echo "local : $(git -C "$WORK" log --oneline -1 2>/dev/null || echo none)"
    echo "remote: $(git -C "$WORK" log --oneline -1 "origin/$BRANCH")"
    ;;
  *)
    echo "unknown action: $ACTION (use pull|push|status)" >&2; exit 2;;
esac
