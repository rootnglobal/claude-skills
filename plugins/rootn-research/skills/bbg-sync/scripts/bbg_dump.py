#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bbg_dump.py — Bloomberg 터미널 PC용 일일 데이터 덤프 (Layer 1, A안)

실행 환경: 블룸버그 PC의 **Windows 네이티브 Python 3.8~3.12** (Linux VM 불가).
전제: Bloomberg 터미널 로그인 상태 (blpapi는 localhost:8194 무인증 로컬 접속).
설치: pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/
     pip install xbbg pandas openpyxl "pyarrow>=22.0"
주의: xbbg 1.x(rust)는 polars DataFrame을 반환 → to_pd()로 pandas 정규화 (pyarrow>=22.0 필수).
스케줄(v261013): 작업 스케줄러는 기존 그대로 평일 07:50 매일 호출. 스크립트가 스스로 판단해
  **주 1회 전체 배치**만 실행 — 월요일(=직전 금요일 종가 기준) 또는 마지막 성공 배치 후 7일 이상이면
  실행(공휴일·PC 꺼짐 다음 날 자동 캐치업), 아니면 즉시 종료. 강제 실행은 --force.
  schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN "bbg_dump" /ST 07:50 ^
    /TR "py -3 C:\\Bloomberg_Inbox\\bbg_dump.py"
모드:  (인자 없음) 주간 배치(due일 때만) / --force 즉시 배치 / "7203 JT Equity" 단건(워처·수동)
       --prune [--dry-run] 덤프 보관정리(티커별 최신 + 월말 + 최근 14일만 남김, 5.5KB 빈 덤프 삭제)
입력:  C:\\Bloomberg_Inbox\\watchlist.csv   (컬럼: ticker,name,sector_pack — 시트 Apps Script가 자동 갱신)
       C:\\Bloomberg_Inbox\\macro_map.csv   (컬럼: sector_pack,bbg_ticker,label)
출력:  C:\\Bloomberg_Inbox\\dumps\\[티커]_bbg_[YYYYMMDD].xlsx  ('내 컴퓨터' 동기화로 Drive에 자동 업로드)
       시트: Meta / Consensus / Guidance / Recs / Revisions / Actuals_Q / Px / Macro
       C:\\Bloomberg_Inbox\\_bbg_status.json (배치 결과 — 시트 Apps Script bbgHealthCheck가 감시)
       C:\\Bloomberg_Inbox\\bbg_dump.log
실패:  티커 단위로 계속 진행, _error 시트에 기록. 단 터미널 미접속(probe 실패)이면 10분 간격 최대 3시간
       재시도 후 배치 중단(빈 파일 미생성). 데이터가 전무한 덤프(_error만)는 파일을 쓰지 않음.
       연속 3종목 무데이터면 재-probe → 실패 시 중단(다음 날 캐치업).
필드 한도: reference 요청당 400필드 / history 요청당 25필드 (공식 한도) — 청크 분할 처리.
주의: Desktop API 데이터는 사내 이용 범위만. 외부 재배포 금지.
FLDS 실측 결과 (2026-07-22, 285A/4443 JT):
  - 가이던스(会社計画)는 CEst 계열 확정: BE250/BE252 + 값 필드 7개(BE202/205/206/215/216/217/220).
    285A는 SALES·OPER_INCME·NETINCME_G만 값 존재, 4443은 전부 N.A.(CEst 미제공 종목).
  - Toyo Keizai: 4443 ANR 표시 목록에 없음 (단 'Entitled to 15 of 17' — 미열람 2개
    소스 가능성 잔존, 신뢰도 중). TOT_ANALYST_REC 해석 시 유의.
  - 수급: SHORT_INT(PR238)=N.A.(일본 미지원). 외국인 보유는 가용 —
    BS_PERCENT_OF_FOREIGN_OWNERSHIP(BS140), CURRENT_FOREIGN_OWNERSHIP(DY186) → Meta에 포함.
    信用残은 표준 필드 미확인(TODO: FLDS 'margin trading'/'shintori' 재검색).
"""
import csv
import json
import re
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
INBOX = Path(r"C:\Bloomberg_Inbox")
DUMPS = INBOX / "dumps"
TODAY = date.today().strftime("%Y%m%d")
STATUS = INBOX / "_bbg_status.json"
LOG = INBOX / "bbg_dump.log"
# ---- 배치 주기·가드 ---------------------------------------------------------
BATCH_WEEKDAY = 0            # 0=월요일: 직전 금요일 종가·주말 컨센 반영분을 주 1회 스냅샷
CATCHUP_DAYS = 7             # 마지막 성공 배치 후 7일 이상이면 요일 무관 실행(캐치업)
PROBE_TICKER = "1306 JT Equity"
PROBE_WAIT_SEC = 600         # 터미널 미접속 시 재시도 간격
PROBE_WINDOW_SEC = 3 * 3600  # 재시도 총 허용 시간
MAX_CONSEC_EMPTY = 3         # 연속 무데이터 종목 수 → 재-probe
EMPTY_FILE_BYTES = 8000      # 이보다 작은 덤프 = _error만 있는 빈 파일(정리 대상)
PRUNE_RECENT_DAYS = 14
# ---- 필드 정의 -------------------------------------------------------------
META_FLDS = ["NAME", "GICS_SECTOR_NAME", "CRNCY", "CUR_MKT_CAP", "EQY_SH_OUT",
             "EXPECTED_REPORT_DT", "LATEST_ANNOUNCEMENT_DT",
             # 수급(FLDS 실측 가용분): 외국인 보유. SHORT_INT는 일본 N.A.라 제외.
             "BS_PERCENT_OF_FOREIGN_OWNERSHIP", "CURRENT_FOREIGN_OWNERSHIP"]
# BEst 컨센서스: FY1~FY3 + 분기
CONS_FLDS = ["BEST_SALES", "BEST_OPP", "BEST_NET_INCOME", "BEST_EPS",
             "BEST_SALES_HI", "BEST_SALES_LO", "BEST_EPS_HI", "BEST_EPS_LO",
             "BEST_ANALYST_RATING", "TOT_ANALYST_REC", "BEST_TARGET_PRICE"]
CONS_PERIODS = ["1FY", "2FY", "3FY", "1FQ", "2FQ"]
# 가이던스(会社計画): CEst 계열 전체 확정 (FLDS 실측 2026-07-22, 285A/4443).
# 종목·회계기준에 따라 일부만 값이 있음(N.A.는 자동으로 비어서 나옴 — 정상).
# CEst 미제공 종목(예: 4443)은 Guidance 시트가 빈 것이 정상.
GUIDANCE_FLDS = ["CEST_CUR_GUIDANCE_AVAIL",          # BE250 가이던스 존재 여부(Y/N)
                 "CEST_LAST_CO_GUIDANCE_UPDATE_DT",  # BE252 최종 수정일
                 "CEST_SALES",                       # BE202 매출
                 "CEST_OPER_INCME",                  # BE215 영업이익
                 "CEST_CUR_PROFIT",                  # BE216 경상이익
                 "CEST_NET_INCOME",                  # BE205 순이익
                 "CEST_NETINCME_G",                  # BE217 순이익(GAAP)
                 "CEST_EPS",                         # BE206 EPS
                 "CEST_EPS_GAAP"]                    # BE220 EPS(GAAP)
RECS_FLDS = ["BEST_ANALYST_RECS_BULK"]  # bulk: 브로커별 의견·TP·날짜
# Revisions: 주간 시계열 (history)
REV_FLDS = ["BEST_EPS", "BEST_SALES"]           # overrides: BEST_FPERIOD_OVERRIDE 1FY/2FY
REV_WEEKS = 104                                  # 2년
ACTUALS_FLDS = ["SALES_REV_TURN", "IS_OPER_INC", "NET_INCOME", "IS_EPS"]
PX_FLDS = ["PX_LAST", "PX_VOLUME"]
PX_DAYS = 500
CHUNK_REF = 400   # reference 요청당 필드 한도
CHUNK_HIST = 25   # history 요청당 필드 한도
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))
def to_pd(df):
    """xbbg 1.x(rust)는 polars DataFrame을 반환 — pandas로 정규화 (구버전 pandas는 그대로 통과).
    polars→pandas 변환에는 pyarrow>=22.0 필요 (pip install pyarrow)."""
    if df is None:
        return pd.DataFrame()
    if not isinstance(df, pd.DataFrame) and hasattr(df, "to_pandas"):
        df = df.to_pandas()
    return df
def dump_ticker(blp, tkr, sector_pack, macro_rows):
    """한 종목 덤프 → dict[str, DataFrame]. 실패 시트는 _error에 기록."""
    out, errors = {}, []
    def try_sheet(name, fn):
        try:
            out[name] = fn()
        except Exception as e:  # noqa: BLE001 — 티커 단위 계속 진행
            errors.append({"sheet": name, "error": repr(e)})
    try_sheet("Meta", lambda: to_pd(blp.bdp(tkr, META_FLDS)).T)
    def consensus():
        frames = []
        for p in CONS_PERIODS:
            for fl in chunks(CONS_FLDS, CHUNK_REF):
                df = to_pd(blp.bdp(tkr, fl, BEST_FPERIOD_OVERRIDE=p))
                if not df.empty:
                    # 구 xbbg: wide(1행, 필드=컬럼) / 신 xbbg: long(ticker,field,value 행)
                    # — 어느 쪽이든 통째로 보존하고 period만 붙인다 (iloc[0] 금지: long이면 첫 필드만 남음)
                    df = df.copy()
                    df["period"] = p
                    frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    try_sheet("Consensus", consensus)
    try_sheet("Guidance", lambda: to_pd(blp.bdp(tkr, [f for f in GUIDANCE_FLDS
                                                if not f.startswith("TODO_")] or ["NAME"])).T)
    try_sheet("Recs", lambda: to_pd(blp.bds(tkr, RECS_FLDS[0])))
    def revisions():
        start = (date.today() - timedelta(weeks=REV_WEEKS)).strftime("%Y-%m-%d")
        frames = []
        for p in ("1FY", "2FY"):
            df = to_pd(blp.bdh(tkr, REV_FLDS, start_date=start, Per="W",
                               BEST_FPERIOD_OVERRIDE=p))
            if not df.empty:
                # 구 xbbg: MultiIndex(티커,필드) / 신 xbbg(polars): 평평한 컬럼명
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [f"{c[1]}_{p}" for c in df.columns]
                else:
                    df.columns = [f"{c}_{p}" for c in df.columns]
                frames.append(df)
        return pd.concat(frames, axis=1) if frames else pd.DataFrame()
    try_sheet("Revisions", revisions)
    def actuals():
        start = (date.today() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
        return to_pd(blp.bdh(tkr, ACTUALS_FLDS, start_date=start, Per="Q"))
    try_sheet("Actuals_Q", actuals)
    try_sheet("Px", lambda: to_pd(blp.bdh(
        tkr, PX_FLDS,
        start_date=(date.today() - timedelta(days=PX_DAYS)).strftime("%Y-%m-%d"))))
    def macro():
        rows = [r for r in macro_rows if r.get("sector_pack") == sector_pack]
        if not rows:
            return pd.DataFrame()
        start = (date.today() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
        frames = []
        tickers = [r["bbg_ticker"] for r in rows
                   if r.get("bbg_ticker", "").strip().upper() != "TODO"]
        if not tickers:
            return pd.DataFrame()
        for fl in chunks(tickers, CHUNK_HIST):
            df = to_pd(blp.bdh(fl, ["PX_LAST"], start_date=start, Per="M"))
            frames.append(df)
        return pd.concat(frames, axis=1) if frames else pd.DataFrame()
    try_sheet("Macro", macro)
    if errors:
        out["_error"] = pd.DataFrame(errors)
    return out
def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        if LOG.exists() and LOG.stat().st_size > 1_000_000:   # 1MB 넘으면 최근 3000줄만 유지
            tail = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-3000:]
            LOG.write_text("\n".join(tail) + "\n", encoding="utf-8")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass
def load_status():
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
def save_status(st):
    try:
        STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log(f"[WARN] status 저장 실패: {e!r}")
def batch_due(st, today=None):
    """주간 배치 실행 여부: 오늘 이미 성공했으면 X / 월요일이면 O / 마지막 성공 후 7일 이상이면 O(캐치업)."""
    today = today or date.today()
    last = st.get("last_full_batch")
    if last == today.isoformat():
        return False
    if today.weekday() == BATCH_WEEKDAY:
        return True
    if not last:
        return True
    try:
        return (today - date.fromisoformat(last)).days >= CATCHUP_DAYS
    except ValueError:
        return True
def probe(blp):
    try:
        return not to_pd(blp.bdp(PROBE_TICKER, ["PX_LAST"])).empty
    except Exception:  # noqa: BLE001
        return False
def wait_for_terminal(blp):
    t0 = time.time()
    while True:
        if probe(blp):
            return True
        if time.time() - t0 + PROBE_WAIT_SEC > PROBE_WINDOW_SEC:
            return False
        log(f"[WAIT] 터미널 미접속 — {PROBE_WAIT_SEC // 60}분 후 재시도")
        time.sleep(PROBE_WAIT_SEC)
def is_empty_dump(sheets):
    """_error 외에 실제 데이터가 하나도 없으면 True (터미널 끊김·무효 티커)."""
    return all(name == "_error" or to_pd(df).empty for name, df in sheets.items())
def write_dump(blp, tkr, sector_pack, macro_rows):
    """한 종목 덤프 → 저장. 반환: 'ok' | 'ok_err' | 'empty' | 'fail'."""
    safe = tkr.replace(" ", "").replace("/", "")
    dest = DUMPS / f"{safe}_bbg_{TODAY}.xlsx"
    try:
        sheets = dump_ticker(blp, tkr, sector_pack, macro_rows)
        if not sheets or is_empty_dump(sheets):
            errs = sheets.get("_error") if sheets else None
            first = (to_pd(errs).iloc[0]["error"][:120] if errs is not None and not to_pd(errs).empty else "")
            log(f"[EMPTY] {tkr} — 데이터 없음, 파일 미생성 {first}")
            return "empty"
        with pd.ExcelWriter(dest, engine="openpyxl") as xw:
            for name, df in sheets.items():
                to_pd(df).to_excel(xw, sheet_name=name[:31])
        log(f"[OK] {tkr} -> {dest.name}" + (" (with _error)" if "_error" in sheets else ""))
        return "ok_err" if "_error" in sheets else "ok"
    except Exception:  # noqa: BLE001 — 전체 중단 금지
        log(f"[FAIL] {tkr}\n{traceback.format_exc()}")
        return "fail"
def resolve_sector_pack(tkr):
    """단건 모드: watchlist.csv → sector_pack_map.csv 순으로 sector_pack 조회. 없으면 ''(Macro만 빔)."""
    code = tkr.split()[0] if tkr else ""
    for fname in ("watchlist.csv", "sector_pack_map.csv"):
        p = INBOX / fname
        if not p.exists():
            continue
        try:
            for r in load_csv(p):
                t = (r.get("ticker") or "").strip()
                if t and t.split()[0] == code:
                    return (r.get("sector_pack") or "").strip()
        except Exception:  # noqa: BLE001
            pass
    return ""
def prune(dry_run=True, today=None):
    """dumps/ 보관정리: 티커별 최신 1개 + 월말(그 달 마지막) 1개 + 최근 14일 보존, 빈 덤프(<8KB)는 삭제."""
    today = today or date.today()
    pat = re.compile(r"^(.+)_bbg_(\d{8})\.xlsx$")
    by_tkr = {}
    for p in DUMPS.glob("*_bbg_*.xlsx"):
        m = pat.match(p.name)
        if m:
            by_tkr.setdefault(m.group(1), []).append((m.group(2), p))
    keep, drop = set(), []
    for tkr, items in by_tkr.items():
        good = [(d, p) for d, p in items if p.stat().st_size >= EMPTY_FILE_BYTES]
        if good:
            keep.add(max(good)[1])
            month_last = {}
            for d, p in good:
                if d > month_last.get(d[:6], ("",))[0]:
                    month_last[d[:6]] = (d, p)
            keep.update(p for _, p in month_last.values())
            cutoff = (today - timedelta(days=PRUNE_RECENT_DAYS)).strftime("%Y%m%d")
            keep.update(p for d, p in good if d >= cutoff)
        drop += [p for _, p in items if p not in keep]
    log(f"[PRUNE] {'dry-run ' if dry_run else ''}보존 {len(keep)} / 삭제 {len(drop)}")
    if not dry_run:
        for p in drop:
            try:
                p.unlink()
            except Exception as e:  # noqa: BLE001
                log(f"[PRUNE-ERR] {p.name} {e!r}")
    return keep, drop
def main():
    args = [a for a in sys.argv[1:] if a.strip()]
    flags = {a.strip().lower() for a in args if a.strip().startswith("--")}
    tkr_arg = " ".join(a for a in args if not a.strip().startswith("--")).strip()
    DUMPS.mkdir(parents=True, exist_ok=True)
    if "--prune" in flags:
        prune(dry_run="--dry-run" in flags)
        return 0
    if not tkr_arg and "--force" not in flags:
        st = load_status()
        if not batch_due(st):
            print(f"[SKIP] 주간 배치 대상일 아님 (마지막 성공 {st.get('last_full_batch')})")
            return 0
    from xbbg import blp  # import 지연: blpapi 미설치 시 명확한 에러
    macro_rows = load_csv(INBOX / "macro_map.csv") if (INBOX / "macro_map.csv").exists() else []
    if tkr_arg:   # 단건 모드 (bbg_request_watcher.py·dump_one.bat)
        log(f"[MODE] 단건 {tkr_arg}")
        r = write_dump(blp, tkr_arg, resolve_sector_pack(tkr_arg), macro_rows)
        return 0 if r in ("ok", "ok_err") else 1
    watch = [r for r in load_csv(INBOX / "watchlist.csv") if (r.get("ticker") or "").strip()]
    st = load_status()
    st.update(last_attempt=datetime.now().isoformat(timespec="seconds"),
              watchlist_n=len(watch),
              watchlist_mtime=datetime.fromtimestamp((INBOX / "watchlist.csv").stat().st_mtime)
              .isoformat(timespec="seconds"))
    log(f"[MODE] 주간 배치 {len(watch)}종목")
    if not wait_for_terminal(blp):
        st.update(result="terminal_down", ok=0, empty=[], failed=[])
        save_status(st)
        log("[ABORT] 터미널 미접속 3시간 — 배치 중단, 다음 평일 캐치업")
        return 2
    counts, empty, failed, consec, aborted = {"ok": 0, "ok_err": 0}, [], [], 0, False
    for i, row in enumerate(watch):
        tkr = row["ticker"].strip()
        r = write_dump(blp, tkr, row.get("sector_pack", ""), macro_rows)
        if r in counts:
            counts[r] += 1
            consec = 0
            continue
        (empty if r == "empty" else failed).append(tkr)
        consec += 1
        if consec >= MAX_CONSEC_EMPTY:
            if wait_for_terminal(blp):
                consec = 0
            else:
                aborted = True
                failed += [w["ticker"].strip() for w in watch[i + 1:]]
                log("[ABORT] 배치 도중 터미널 끊김 — 중단, 다음 평일 캐치업")
                break
    st.update(result="aborted" if aborted else "ok", ok=counts["ok"] + counts["ok_err"],
              ok_with_error_sheet=counts["ok_err"], empty=empty, failed=failed,
              finished=datetime.now().isoformat(timespec="seconds"))
    if not aborted:
        st["last_full_batch"] = date.today().isoformat()
    save_status(st)
    log(f"[DONE] ok {st['ok']} / empty {len(empty)} / fail {len(failed)}" + (" (aborted)" if aborted else ""))
    return 0 if not aborted else 2
if __name__ == "__main__":
    sys.exit(main())
