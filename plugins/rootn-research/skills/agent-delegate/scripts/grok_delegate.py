#!/usr/bin/env python3
"""grok_delegate.py - one xAI API (Grok) call for agent-delegate, with cost logging and caps.

Roles (user decision 2026-11-24): (1) fallback when Claude/Codex limits are exhausted,
(2) X mention check with the server-side x_search tool - at most once per task.
- key: env XAI_API_KEY only (never printed or logged)
- every successful call appends one line (no prompt text) to the usage log
  (env GROK_USAGE_LOG, default ~/.rootn/grok_usage.jsonl)
- monthly cap: refuses when this month's logged cost >= env GROK_MONTHLY_CAP_USD (default 100)
- x_search: requires --task and refuses if the log already has an x_search call for that task
stdout: one-line JSON summary. exit 0 ok / 1 error / 2 timeout / 4 monthly cap / 5 x_search cap
Python 3.10, stdlib only.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.x.ai/v1/responses"
# USD per 1M tokens (<200k context), docs.x.ai pricing checked 2026-11-24; used only when the
# response has no cost_in_usd_ticks
PRICE = {"grok-4.5": (2.00, 0.30, 6.00), "grok-4.3": (1.25, 0.20, 2.50)}
TICKS_PER_USD = 1e10
GUARD = ("[delegate rules] Use only the material in this prompt (attached files are inlined). "
         "Do not guess names or numbers; if something is not in the material, write 'not in material'.\n\n")
GUARD_X = ("[delegate rules] Use x_search results and the material in this prompt only. Cite post URLs and dates "
           "for every claim; separate company statements, expert views and rumors. Do not guess.\n\n")


def summary(**kw):
    print(json.dumps(kw, ensure_ascii=False))


def log_path():
    return os.environ.get("GROK_USAGE_LOG") or os.path.join(os.path.expanduser("~"), ".rootn", "grok_usage.jsonl")


def read_log():
    rows = []
    p = log_path()
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def extract_text(resp):
    out = []
    for item in resp.get("output") or []:
        if isinstance(item, dict) and item.get("type") == "message":
            for c in item.get("content") or []:
                if isinstance(c, dict) and c.get("type") in ("output_text", "text") and c.get("text"):
                    out.append(c["text"])
    if not out and isinstance(resp.get("output_text"), str):
        out.append(resp["output_text"])
    return "\n".join(out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", help="prompt file (default: stdin)")
    ap.add_argument("--out", required=True, help="output md path")
    ap.add_argument("--task", default="", help="task id (required with --x-search)")
    ap.add_argument("--role", choices=["fallback", "x-check"], default="fallback")
    ap.add_argument("--model", default="grok-4.3")
    ap.add_argument("--x-search", action="store_true", help="enable server-side x_search tool")
    ap.add_argument("--x-from", default="", help="x_search from_date YYYY-MM-DD (unverified param)")
    ap.add_argument("--attach", nargs="*", default=[], help="text files inlined into the prompt")
    ap.add_argument("--no-guard", action="store_true", help="do not prepend the material-only rule")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    key = os.environ.get("XAI_API_KEY")
    if not key:
        summary(agent="grok", status="error", reason="XAI_API_KEY not set")
        return 1
    if a.prompt_file:
        with open(a.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        summary(agent="grok", status="error", reason="empty prompt")
        return 1

    for p in a.attach:
        with open(p, encoding="utf-8", errors="replace") as f:
            prompt += "\n\n===== BEGIN FILE %s =====\n%s\n===== END FILE %s =====" % (
                os.path.basename(p), f.read(), os.path.basename(p))
    if not a.no_guard:
        prompt = (GUARD_X if a.x_search else GUARD) + prompt

    rows = read_log()
    month = datetime.date.today().strftime("%Y-%m")
    spent = sum(float(r.get("cost_usd") or 0) for r in rows if str(r.get("ts", "")).startswith(month))
    cap = float(os.environ.get("GROK_MONTHLY_CAP_USD") or 100)
    if spent >= cap:
        summary(agent="grok", status="monthly_cap", month_usd=round(spent, 4), cap_usd=cap)
        return 4
    if a.x_search:
        if not a.task:
            summary(agent="grok", status="error", reason="--task is required with --x-search")
            return 1
        if any(r.get("task") == a.task and r.get("x_search") for r in rows):
            summary(agent="grok", status="x_search_cap", task=a.task, reason="x_search already used for this task")
            return 5

    body = {"model": a.model, "input": [{"role": "user", "content": prompt}]}
    if a.x_search:
        tool = {"type": "x_search"}
        if a.x_from:
            tool["from_date"] = a.x_from
        body["tools"] = [tool]
    req = urllib.request.Request(API, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        summary(agent="grok", status="error", http=e.code, reason=detail)
        return 1
    except (TimeoutError, OSError) as e:
        if "timed out" in str(e).lower():
            summary(agent="grok", status="timeout", seconds=a.timeout)
            return 2
        summary(agent="grok", status="error", reason=str(e)[:300])
        return 1
    sec = round(time.time() - t0, 1)

    u = resp.get("usage") or {}
    tin = int(u.get("input_tokens") or 0)
    tout = int(u.get("output_tokens") or 0)
    cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
    ticks = u.get("cost_in_usd_ticks", resp.get("cost_in_usd_ticks"))
    if ticks is not None:
        cost, src = float(ticks) / TICKS_PER_USD, "ticks"
    else:
        p_in, p_cache, p_out = PRICE.get(a.model, PRICE["grok-4.5"])
        cost, src = ((tin - cached) * p_in + cached * p_cache + tout * p_out) / 1e6, "estimate_tokens_only"
    tools_used = u.get("num_server_side_tools_used") or u.get("server_side_tool_usage_details")

    text = extract_text(resp)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "task": a.task, "role": a.role,
           "model": resp.get("model") or a.model, "x_search": bool(a.x_search), "seconds": sec,
           "input_tokens": tin, "cached_tokens": cached, "output_tokens": tout,
           "cost_usd": round(cost, 6), "cost_source": src, "server_tools": tools_used}
    lp = log_path()
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    with open(lp, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not text:
        summary(agent="grok", status="error", reason="empty response text", cost_usd=rec["cost_usd"])
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    head = "<!-- agent: grok (%s, %s) | task: %s | %s | %ss | cost $%.4f (%s)%s -->\n\n" % (
        rec["model"], a.role, a.task, rec["ts"], sec, cost, src, " | x_search" if a.x_search else "")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(head + text + "\n")
    summary(agent="grok", status="ok", out=a.out, model=rec["model"], seconds=sec, input_tokens=tin,
            output_tokens=tout, cost_usd=rec["cost_usd"], cost_source=src,
            month_usd=round(spent + cost, 4), cap_usd=cap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
