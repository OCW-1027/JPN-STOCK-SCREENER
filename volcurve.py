# -*- coding: utf-8 -*-
"""
volcurve.py — 장중 거래량 곡선 수집 (RVOL 시간보정용 재료)
============================================================
15분마다 도는 실행에서 '시장 전체 거래량 합계'만 한 줄 기록한다.
2~3주 쌓이면 "장 시작 후 N분 시점에 하루 거래량의 몇 %가 소화되는지"
실측 곡선이 나오고, 그때 RVOL을 정확히 시간보정할 수 있다.

- 종목별이 아니라 시장 합계만 저장 → 파일이 매우 작다 (하루 약 30줄)
- volcurve/{market}.csv 에 append, 90일 롤링 보관
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from tradingview_screener import Query, col

BASE = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")
KEEP_DAYS = 90
EXCH = {"jp": ["TSE"], "kr": ["KRX"], "us": ["NYSE", "NASDAQ", "AMEX"]}
TVM = {"jp": "japan", "kr": "korea", "us": "america"}
# 각 시장 정규장 (JST 기준, 분)
SESSION = {"jp": [(9 * 60, 11 * 60 + 30), (12 * 60 + 30, 15 * 60)],
           "kr": [(9 * 60, 15 * 60 + 30)],
           "us": [(22 * 60 + 30, 24 * 60 + 5 * 60)]}


def elapsed_minutes(mkey, now):
    """장 시작부터 경과한 정규장 분. 장외면 None."""
    t = now.hour * 60 + now.minute
    tt = t + 24 * 60 if (mkey == "us" and t < 6 * 60) else t
    total = el = 0
    inside = False
    for a, b in SESSION[mkey]:
        span = b - a
        if tt >= b:
            el += span
        elif tt > a:
            el += tt - a
            inside = True
        total += span
    return (el, total, inside or el > 0)


def snap(mkey):
    n, df = (Query().set_markets(TVM[mkey]).select("name", "volume", "Value.Traded")
             .where(col("type") == "stock", col("exchange").isin(EXCH[mkey]))
             .limit(12000).get_scanner_data())
    return len(df), float(df["volume"].fillna(0).sum()), float(df["Value.Traded"].fillna(0).sum())


def main():
    now = datetime.now(JST)
    out = BASE / "volcurve"
    out.mkdir(exist_ok=True)
    for mkey in ("jp", "kr", "us"):
        el, total, active = elapsed_minutes(mkey, now)
        if not active:
            continue
        try:
            cnt, vol, val = snap(mkey)
        except Exception as e:
            print(f"  [{mkey}] 수집 실패: {type(e).__name__}")
            continue
        f = out / f"{mkey}.csv"
        new = not f.exists()
        with f.open("a", encoding="utf-8") as fp:
            if new:
                fp.write("date,time,elapsed_min,session_min,stocks,volume,value\n")
            fp.write(f"{now:%Y-%m-%d},{now:%H:%M},{el},{total},{cnt},{vol:.0f},{val:.0f}\n")
        print(f"  [{mkey}] {now:%H:%M} 경과 {el}/{total}분 · 거래량 {vol/1e6:,.0f}백만주")

        # 90일 롤링
        try:
            d = pd.read_csv(f)
            cut = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
            d = d[d["date"] >= cut]
            d.to_csv(f, index=False)
        except Exception:
            pass


if __name__ == "__main__":
    main()
