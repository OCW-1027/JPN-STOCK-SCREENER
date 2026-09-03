# -*- coding: utf-8 -*-
"""
supply_us.py — 미국 수급 데이터 수집
=====================================
① FINRA 일별 공매도 거래량 (CNMSshvol) — 12,000+종목, 매일 갱신, 파일 1개로 전량.
   → 당일 거래량 중 공매도 비중(%). "오늘 얼마나 숏이 걸렸나"를 매일 볼 수 있다.
   미국에만 있는 데이터로, 일본·한국에는 대응물이 없다.

② 나스닥 Short Interest — 격주 공시 잔고 + Days to Cover.
   종목당 1회 호출이라 전 종목은 무리. 거래대금 상위 N개(기본 300)만 받는다.

출력: supply/us.json
  {code: {sv_pct, sv_pct_prev, sv_chg, si_shares, si_days}}
    sv_pct       당일 공매도 거래량 비중(%)
    sv_pct_prev  직전 영업일 비중(%)
    sv_chg       증감(%p)
    si_shares    Short Interest 잔고(주) — 상위 종목만
    si_days      Days to Cover — 상위 종목만

주의: ①의 sv_pct는 '잔고'가 아니라 '당일 거래 중 숏 비중'이다. 40~60%도 흔하며
      시장조성자의 헤지 물량이 상당수 포함되므로, 높다고 곧 하락 신호는 아니다.
      의미가 있는 건 절대 수준보다 '평소 대비 급변'(sv_chg)이다.
"""
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")
ET = ZoneInfo("America/New_York")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}
FINRA = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d}.txt"
NASDAQ = "https://api.nasdaq.com/api/quote/{sym}/short-interest?assetClass=stocks"

SI_TOP = int(os.environ.get("US_SI_TOP", "300"))    # Short Interest 수집 종목 수
SI_SLEEP = float(os.environ.get("US_SI_SLEEP", "0.3"))


def finra_day(d):
    """하루치 FINRA 파일 → {symbol: (short, total)}."""
    r = requests.get(FINRA.format(d=d), headers=UA, timeout=40)
    if r.status_code != 200 or len(r.content) < 10000:
        return None
    df = pd.read_csv(io.StringIO(r.text), sep="|")
    df = df[df["Symbol"].notna() & df["TotalVolume"].notna()]
    df = df[df["TotalVolume"] > 0]
    return dict(zip(df["Symbol"].astype(str),
                    zip(df["ShortVolume"].astype(float), df["TotalVolume"].astype(float))))


def fetch_finra():
    """최근 영업일 2개를 받아 당일 비중과 증감을 계산."""
    days, d = [], datetime.now(ET)
    while len(days) < 6:
        if d.weekday() < 5:
            days.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)

    got = []
    for day in days:
        m = finra_day(day)
        if m:
            got.append((day, m))
            print(f"  [FINRA] {day} {len(m)}종목")
        if len(got) == 2:
            break
    if not got:
        raise RuntimeError("FINRA 파일 없음")

    cur_day, cur = got[0]
    prev = got[1][1] if len(got) > 1 else {}
    out = {}
    for sym, (s, t) in cur.items():
        pct = round(s / t * 100, 1)
        p = prev.get(sym)
        pp = round(p[0] / p[1] * 100, 1) if p and p[1] else None
        out[sym] = {"sv_pct": pct, "sv_pct_prev": pp,
                    "sv_chg": round(pct - pp, 1) if pp is not None else None}
    return out, cur_day


def top_symbols(n):
    """거래대금 상위 n종목 (Short Interest 대상)."""
    from tradingview_screener import Query, col
    _, df = (Query().set_markets("america").select("name", "Value.Traded", "subtype")
             .where(col("type") == "stock",
                    col("exchange").isin(["NYSE", "NASDAQ", "AMEX"]))
             .limit(12000).get_scanner_data())
    df = df[~df["subtype"].isin(["preferred", "unit"])]
    df = df.sort_values("Value.Traded", ascending=False)
    return [str(x) for x in df["name"].tolist()[:n]]


def fetch_short_interest(syms):
    """나스닥 격주 공시 — 최신 1건만."""
    s = requests.Session()
    out, ok, fail, consec = {}, 0, 0, 0
    for i, sym in enumerate(syms, 1):
        try:
            r = s.get(NASDAQ.format(sym=sym),
                      headers={**UA, "Accept": "application/json"}, timeout=12)
            rows = (((r.json() or {}).get("data") or {})
                    .get("shortInterestTable") or {}).get("rows") or []
            if rows:
                row = rows[0]
                si = row.get("interest", "").replace(",", "")
                dtc = row.get("daysToCover")
                out[sym] = {"si_shares": int(si) if si.isdigit() else None,
                            "si_days": round(float(dtc), 2) if dtc else None}
                ok += 1
                consec = 0
            else:
                fail += 1
                consec += 1
        except Exception:
            fail += 1
            consec += 1
        if consec >= 30:
            print(f"  [나스닥] 연속 실패 {consec}회 — 중단")
            break
        if i % 100 == 0:
            print(f"    {i}/{len(syms)} (성공 {ok})")
        time.sleep(SI_SLEEP)
    print(f"  [나스닥] Short Interest {ok}종목 (실패 {fail})")
    return out


def main():
    print("=" * 60)
    print("미국 수급 데이터 수집", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    merged, meta = {}, {}

    try:
        sv, day = fetch_finra()
        meta["finra_asof"] = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        for k, v in sv.items():
            merged.setdefault(k, {}).update(v)
    except Exception as e:  # noqa: BLE001
        print(f"  [FINRA] 실패: {type(e).__name__}: {str(e)[:80]}")

    if SI_TOP > 0:
        try:
            syms = top_symbols(SI_TOP)
            si = fetch_short_interest(syms)
            meta["si_count"] = len(si)
            for k, v in si.items():
                merged.setdefault(k, {}).update(v)
        except Exception as e:  # noqa: BLE001
            print(f"  [나스닥] 실패: {type(e).__name__}: {str(e)[:80]}")

    if not merged:
        print("  수집 0건 — 기존 파일 유지")
        return
    meta["asof"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    out = BASE / "supply"
    out.mkdir(exist_ok=True)
    (out / "us.json").write_text(json.dumps({"meta": meta, "data": merged}, ensure_ascii=False),
                                 encoding="utf-8")
    print(f"  완료 → supply/us.json ({len(merged)}종목)")


if __name__ == "__main__":
    main()
