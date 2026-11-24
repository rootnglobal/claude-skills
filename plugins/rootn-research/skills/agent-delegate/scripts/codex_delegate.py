#!/usr/bin/env python3
"""codex_delegate.py - run one headless Codex sub-task and collect the final answer as md.

Design (agent-delegate SKILL.md):
- empty temp work dir and --skip-git-repo-check: no repo/AGENTS.md loading
- --attach files are inlined into the prompt (the read-only sandbox may block file reads, 2026-11-24 test)
- read-only sandbox, user config/rules ignored, web search disabled, session not persisted
- evidence is given directly (prompt + attachments); one call per task with questions bundled
- final message via -o, token usage from --json events
stdout: one-line JSON summary. exit 0 ok / 1 error / 2 timeout / 3 usage limit
Python 3.10, stdlib only.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

GUARD = (
    "[delegate rules] Do not browse or search the web and do not explore files outside this folder. "
    "Do not run shell commands. Use only the material in this prompt (attached files are inlined below). "
    "If something cannot be verified from that material, write 'not in material'.\n\n"
)
LIMIT_RE = re.compile(r"usage limit|rate limit|quota|too many requests|\b429\b", re.I)


def inline_attachments(paths):
    parts = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            parts.append("\n\n===== BEGIN FILE %s =====\n%s\n===== END FILE %s =====" % (
                os.path.basename(p), f.read(), os.path.basename(p)))
    return "".join(parts)


def summary(**kw):
    print(json.dumps(kw, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", help="prompt file (default: stdin)")
    ap.add_argument("--attach", nargs="*", default=[], help="text files inlined into the prompt")
    ap.add_argument("--out", required=True, help="output md path")
    ap.add_argument("--task", default="", help="task label for the md header")
    ap.add_argument("--model", default="")
    ap.add_argument("--schema", default="", help="JSON schema file for --output-schema")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--no-guard", action="store_true", help="do not prepend the no-web/no-explore rule")
    a = ap.parse_args()

    exe = shutil.which("codex")
    if not exe:
        summary(agent="codex", status="error", reason="codex not on PATH")
        return 1
    if a.prompt_file:
        with open(a.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        summary(agent="codex", status="error", reason="empty prompt")
        return 1

    work = tempfile.mkdtemp(prefix="codex_delegate_")
    try:
        prompt += inline_attachments(a.attach)
        if not a.no_guard:
            prompt = GUARD + prompt
        last = os.path.join(work, "_last_message.md")
        cmd = [exe, "exec", "--sandbox", "read-only", "--skip-git-repo-check",
               "--ignore-user-config", "--ignore-rules", "--ephemeral",
               "-c", "web_search=disabled", "--json", "-o", last]
        if a.model:
            cmd += ["-m", a.model]
        if a.schema:
            cmd += ["--output-schema", os.path.abspath(a.schema)]
        cmd.append("-")
        t0 = time.time()
        try:
            r = subprocess.run(cmd, input=prompt, cwd=work, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=a.timeout)
        except subprocess.TimeoutExpired:
            summary(agent="codex", status="timeout", seconds=a.timeout)
            return 2
        sec = round(time.time() - t0, 1)
        usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
        for line in (r.stdout or "").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            u = ev.get("usage") if isinstance(ev, dict) else None
            if isinstance(u, dict):
                for k in usage:
                    usage[k] += int(u.get(k) or 0)
        text = ""
        if os.path.exists(last):
            with open(last, encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
        if r.returncode != 0 or not text:
            tail = ((r.stderr or "") + "\n" + (r.stdout or ""))[-2000:]
            status = "limit" if LIMIT_RE.search(tail) else "error"
            summary(agent="codex", status=status, exit=r.returncode, seconds=sec,
                    reason=tail.strip().splitlines()[-1][:300] if tail.strip() else "")
            return 3 if status == "limit" else 1
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        head = "<!-- agent: codex | task: %s | %s | %ss | tokens in %d (cached %d) / out %d -->\n\n" % (
            a.task, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), sec,
            usage["input_tokens"], usage["cached_input_tokens"], usage["output_tokens"])
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(head + text + "\n")
        summary(agent="codex", status="ok", out=a.out, seconds=sec, **usage)
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
