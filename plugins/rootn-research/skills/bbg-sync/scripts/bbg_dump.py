#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bbg_dump.py — Bloomberg 터미널 PC용 일일 데이터 덤프 (Layer 1, A안)

실행 환경: 블룸버그 PC의 **Windows 네이티브 Python 3.8~3.12** (Linux VM 불가).
전제: Bloomberg 터미널 로그인 상태 (blpapi는 localhost:8194 무인증 로컬 접속).
설치: pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/
     pip install xbbg pandas openpyxl

스케줄: Windows 작업 스케줄러 평일 07:50
  schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN "bbg_dump" /ST 07:50 ^
    /TR "py -3 C:\\Bloomberg_Inbox\\bbg_dump.py"

입력:  C:\\Bloomberg_Inbox\\watchlist.csv   (컬럼: ticker,name,sector_pack)
       C:\\Bloomberg_Inbox\\macro_map.csv   (컬럼: sector_pack,bbg_ticker,label)
출력:  C:\\Bloomberg_Inbox\\dumps\\[티커]_bbg_[YYYYMMDD].xlsx
       시트: Meta / Consensus / Guidance / Recs / Revisions / Actuals_Q / Px / Macro
실패:  티커 단위로 계속 진행, _error 시트에 기록 (전체 중단 금지)

필드 한도: reference 요청당 400필드 / history 요청당 25필드 (공식 한도) — 청크 분할 처리.
주의: Desktop API 데이터는 사내 이용 범위만. 외부 재배포 금지.

TODO(터미널 FLDS로 확정 필요 — Phase 2):
  - GUIDANCE_FIELDS: 일본 会社計画 매출/OP/NP 가이던스 mnemonic (예: BEST_GUIDANCE 계열)
  - TOT_ANALYST_REC: Toyo Keizai contributor 포함 여부 확인
  - 수급 필드(외국인 보유·信用残·공매도) blpapi 가용성
"""

import csv
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

INBOX = Path(r"C:\Bloomberg_Inbox")
DUMPS = INBOX / "dumps"
TODAY = date.today().strftime("%Y%m%d")

# ---- 필드 정의 -------------------------------------------------------------
META_FLDS = ["NAME", "GICS_SECTOR_NAME", "CRNCY", "CUR_MKT_CAP", "EQY_SH_OUT",
             "EXPECTED_REPORT_DT", "LATEST_ANNOUNCEMENT_DT"]

# BEst 컨센서스: FY1~FY3 + 분기
CONS_FLDS = ["BEST_SALES", "BEST_OPP", "BEST_NET_INCOME", "BEST_EPS",
             "BEST_SALES_HI", "BEST_SALES_LO", "BEST_EPS_HI", "BEST_EPS_LO",
             "BEST_ANALYST_RATING", "TOT_ANALYST_REC", "BEST_TARGET_PRICE"]
CONS_PERIODS = ["1FY", "2FY", "3FY", "1FQ", "2FQ"]

# TODO: 터미널 FLDS로 확정 (Phase 2)
GUIDANCE_FLDS = ["TODO_GUIDANCE_SALES", "TODO_GUIDANCE_OP", "TODO_GUIDANCE_NP"]

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


def dump_ticker(blp, tkr, sector_pack, macro_rows):
    """한 종목 덤프 → dict[str, DataFrame]. 실패 시트는 _error에 기록."""
    out, errors = {}, []

    def try_sheet(name, fn):
        try:
            out[name] = fn()
        except Exception as e:  # noqa: BLE001 — 티커 단위 계속 진행
            errors.append({"sheet": name, "error": repr(e)})

    try_sheet("Meta", lambda: blp.bdp(tkr, META_FLDS).T)

    def consensus():
        rows = []
        for p in CONS_PERIODS:
            for fl in chunks(CONS_FLDS, CHUNK_REF):
                df = blp.bdp(tkr, fl, BEST_FPERIOD_OVERRIDE=p)
                if not df.empty:
                    r = df.iloc[0].to_dict()
                    r["period"] = p
                    rows.append(r)
        return pd.DataFrame(rows)
    try_sheet("Consensus", consensus)

    try_sheet("Guidance", lambda: blp.bdp(tkr, [f for f in GUIDANCE_FLDS
                                                if not f.startswith("TODO_")] or ["NAME"]).T)
    try_sheet("Recs", lambda: blp.bds(tkr, RECS_FLDS[0]))

    def revisions():
        start = (date.today() - timedelta(weeks=REV_WEEKS)).strftime("%Y-%m-%d")
        frames = []
        for p in ("1FY", "2FY"):
            df = blp.bdh(tkr, REV_FLDS, start_date=start, Per="W",
                         BEST_FPERIOD_OVERRIDE=p)
            if not df.empty:
                df.columns = [f"{c[1]}_{p}" for c in df.columns]
                frames.append(df)
        return pd.concat(frames, axis=1) if frames else pd.DataFrame()
    try_sheet("Revisions", revisions)

    def actuals():
        start = (date.today() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
        return blp.bdh(tkr, ACTUALS_FLDS, start_date=start, Per="Q")
    try_sheet("Actuals_Q", actuals)

    try_sheet("Px", lambda: blp.bdh(
        tkr, PX_FLDS,
        start_date=(date.today() - timedelta(days=PX_DAYS)).strftime("%Y-%m-%d")))

    def macro():
        rows = [r for r in macro_rows if r.get("sector_pack") == sector_pack]
        if not rows:
            return pd.DataFrame()
        start = (date.today() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
        frames = []
        for fl in chunks([r["bbg_ticker"] for r in rows], CHUNK_HIST):
            df = blp.bdh(fl, ["PX_LAST"], start_date=start, Per="M")
            frames.append(df)
        return pd.concat(frames, axis=1) if frames else pd.DataFrame()
    try_sheet("Macro", macro)

    if errors:
        out["_error"] = pd.DataFrame(errors)
    return out


def main():
    from xbbg import blp  # import 지연: blpapi 미설치 시 명확한 에러

    DUMPS.mkdir(parents=True, exist_ok=True)
    watch = load_csv(INBOX / "watchlist.csv")
    macro_rows = load_csv(INBOX / "macro_map.csv") if (INBOX / "macro_map.csv").exists() else []

    for row in watch:
        tkr = row["ticker"].strip()
        if not tkr:
            continue
        safe = tkr.replace(" ", "").replace("/", "")
        dest = DUMPS / f"{safe}_bbg_{TODAY}.xlsx"
        try:
            sheets = dump_ticker(blp, tkr, row.get("sector_pack", ""), macro_rows)
            with pd.ExcelWriter(dest, engine="openpyxl") as xw:
                for name, df in sheets.items():
                    df.to_excel(xw, sheet_name=name[:31])
            print(f"[OK] {tkr} -> {dest.name}"
                  + (" (with _error)" if "_error" in sheets else ""))
        except Exception:  # noqa: BLE001
            print(f"[FAIL] {tkr}")
            traceback.print_exc()
            # 전체 중단 금지 — 다음 티커 계속


if __name__ == "__main__":
    sys.exit(main())
