#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bbg_dump.py — Bloomberg 터미널 PC용 일일 데이터 덤프 (Layer 1, A안)

실행 환경: 블룸버그 PC의 **Windows 네이티브 Python 3.8~3.12** (Linux VM 불가).
전제: Bloomberg 터미널 로그인 상태 (blpapi는 localhost:8194 무인증 로컬 접속).
설치: pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/
     pip install xbbg pandas openpyxl "pyarrow>=22.0"
주의: xbbg 1.x(rust)는 polars DataFrame을 반환 → to_pd()로 pandas 정규화 (pyarrow>=22.0 필수).
스케줄: Windows 작업 스케줄러 평일 12:00 (터미널 로그인 9~10시 이후에 실행돼야 데이터 수신)
  schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN "bbg_dump" /ST 12:00 ^
    /TR "py -3 C:\\Bloomberg_Inbox\\bbg_dump.py"
입력:  C:\\Bloomberg_Inbox\\watchlist.csv   (컬럼: ticker,name,sector_pack)
       C:\\Bloomberg_Inbox\\macro_map.csv   (컬럼: sector_pack,bbg_ticker,label)
출력:  C:\\Bloomberg_Inbox\\dumps\\[티커]_bbg_[YYYYMMDD].xlsx
       시트: Meta / Consensus / Guidance / Recs / Revisions / Actuals_Q / Px / Macro
실패:  티커 단위로 계속 진행, _error 시트에 기록 (전체 중단 금지)
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
            if not sheets:
                print(f"[EMPTY] {tkr} — no data, skip write")
                continue
            with pd.ExcelWriter(dest, engine="openpyxl") as xw:
                for name, df in sheets.items():
                    to_pd(df).to_excel(xw, sheet_name=name[:31])
            print(f"[OK] {tkr} -> {dest.name}"
                  + (" (with _error)" if "_error" in sheets else ""))
        except Exception:  # noqa: BLE001
            print(f"[FAIL] {tkr}")
            traceback.print_exc()
            # 전체 중단 금지 — 다음 티커 계속
if __name__ == "__main__":
    sys.exit(main())
