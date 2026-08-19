# -*- coding: utf-8 -*-
"""
profiles.py — 회사별 서술형 사업 소개 수집기
=============================================
야후 파이낸스에서 longBusinessSummary(영문)를 시총 상위부터 배치로 수집해
profiles/{market}.json.gz 캐시에 누적한다. 매 종가판 실행마다 PROFILE_BATCH개씩
채워지므로 2~4주면 전 종목이 완성되고, 이후에는 오래된 항목만 갱신한다.

환경변수:
  HISTORY_MARKETS  이번 실행에서 수집할 시장 ("jp,kr" / "us")
  PROFILE_BATCH    시장당 이번에 수집할 개수 (기본 250)
"""
import gzip
import json
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")
BATCH = int(os.environ.get("PROFILE_BATCH", "250"))
MARKETS = [m for m in os.environ.get("HISTORY_MARKETS", "").split(",") if m.strip()]
STALE_DAYS = 180          # 이 일수보다 오래된 항목은 재수집 대상
MAX_CONSEC_FAIL = 25      # 연속 실패(레이트리밋 추정) 시 이번 배치 중단
SLEEP = 0.45   # 야후 + 현지 소스 2회 요청이므로 조금 여유롭게


# ─────────── 현지어 사업 소개 (일본: 야후재팬 特色 / 한국: 네이버 기업개요) ───────────
import re

WEB_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "ja,en;q=0.8",
}


def _clean(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", t).strip()


def local_jp(code, timeout=12):
    """야후재팬 프로필의 【特色】【連結事業】 (출처: 회사사계보)."""
    import requests
    r = requests.get(f"https://finance.yahoo.co.jp/quote/{code}.T/profile",
                     headers=WEB_HEADERS, timeout=timeout)
    if r.status_code != 200:
        return ""
    txt = _clean(r.text)
    parts = []
    for key in ("特色", "連結事業"):
        m = re.search(r"【" + key + r"】(.{5,400}?)(?=【|企業情報|本社所在地|設立年月日|市場名|"
                      r"決算|従業員数|代表者名|上場年月日|業種分類|$)", txt)
        if m:
            seg = m.group(1).strip(" 　·・")
            if seg:
                parts.append(f"【{key}】{seg}")
    return " ".join(parts)[:600]


NAVER_PROFILE_ENDPOINTS = [
    "https://m.stock.naver.com/api/stock/{code}/integration",
    "https://api.stock.naver.com/stock/{code}/integration",
    "https://m.stock.naver.com/api/stock/{code}/basic",
]


def local_kr(code, timeout=12):
    """네이버 종목 개요(기업개요/사업 설명). 엔드포인트 후보를 순차 시도."""
    import requests
    for tpl in NAVER_PROFILE_ENDPOINTS:
        try:
            r = requests.get(tpl.format(code=code),
                             headers={**WEB_HEADERS, "Referer": "https://m.stock.naver.com/",
                                      "Accept": "application/json"}, timeout=timeout)
            if r.status_code != 200:
                continue
            j = r.json()
            for key in ("companySummary", "corporationSummary", "summary",
                        "companyOverview", "description", "industryDescription"):
                v = j.get(key) if isinstance(j, dict) else None
                if isinstance(v, str) and len(v.strip()) > 10:
                    return _clean(v)[:600]
            # 중첩 구조 탐색
            def walk(o, depth=0):
                if depth > 3:
                    return ""
                if isinstance(o, dict):
                    for k, v in o.items():
                        if isinstance(v, str) and "Summary" in k and len(v.strip()) > 10:
                            return _clean(v)[:600]
                        got = walk(v, depth + 1)
                        if got:
                            return got
                elif isinstance(o, list):
                    for v in o[:20]:
                        got = walk(v, depth + 1)
                        if got:
                            return got
                return ""
            got = walk(j)
            if got:
                return got
        except Exception:
            continue
    return ""


def local_desc(m, code):
    try:
        if m == "jp":
            return local_jp(code)
        if m == "kr":
            return local_kr(code)
    except Exception:
        return ""
    return ""


def load_cache(m):
    p = BASE / "profiles" / f"{m}.json.gz"
    if p.exists():
        try:
            return json.loads(gzip.decompress(p.read_bytes()).decode("utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(m, cache):
    p = BASE / "profiles" / f"{m}.json.gz"
    p.parent.mkdir(exist_ok=True)
    p.write_bytes(gzip.compress(json.dumps(cache, ensure_ascii=False).encode("utf-8")))


def universe(m):
    """시총순 코드 리스트 + 야후 심볼 매핑."""
    from tradingview_screener import Query, col
    exch = {"jp": ["TSE"], "kr": ["KRX"], "us": ["NYSE", "NASDAQ", "AMEX"]}[m]
    n, df = (Query().set_markets({"jp": "japan", "kr": "korea", "us": "america"}[m])
             .select("name", "market_cap_basic", "type", "subtype", "exchange")
             .where(col("type") == "stock", col("exchange").isin(exch))
             .limit(12000).get_scanner_data())
    if m == "us":
        df = df[~df["subtype"].isin(["preferred", "unit"])]
    df = df.sort_values("market_cap_basic", ascending=False)
    codes = df["name"].astype(str).tolist()

    if m == "jp":
        return codes, {c: f"{c}.T" for c in codes}
    if m == "us":
        return codes, {c: c.replace(".", "-").replace("/", "-") for c in codes}
    # kr: 코스피/코스닥 접미사
    import FinanceDataReader as fdr
    krx = fdr.StockListing("KRX")[["Code", "Market"]]
    sfx = {str(r.Code): (".KS" if str(r.Market).startswith("KOSPI") else ".KQ")
           for r in krx.itertuples()}
    return codes, {c: c + sfx.get(c, ".KS") for c in codes}


def run_market(m):
    import yfinance as yf
    cache = load_cache(m)
    today = datetime.now(JST).strftime("%Y-%m-%d")
    stale_cut = (datetime.now(JST) - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%d")

    codes, symmap = universe(m)
    missing = [c for c in codes if c not in cache]
    stale = [c for c in codes if c in cache and cache[c].get("t", "") < stale_cut]
    targets = (missing + stale)[:BATCH]
    print(f"  [{m}] 캐시 {len(cache)}건 / 미수집 {len(missing)} / 재수집 대상 {len(stale)} → 이번 {len(targets)}건")
    if not targets:
        return

    ok = fail = consec = 0
    n_local = 0
    for c in targets:
        try:
            info = yf.Ticker(symmap[c]).info
            d = (info.get("longBusinessSummary") or "").strip()
            loc = local_desc(m, c)          # 현지어 (jp=일본어 / kr=한국어)
            if loc:
                n_local += 1
            cache[c] = {"d": d, "l": loc, "t": today}
            ok += 1
            consec = 0
        except Exception:
            fail += 1
            consec += 1
            if consec >= MAX_CONSEC_FAIL:
                print(f"  [{m}] 연속 실패 {consec}회 — 레이트리밋 추정, 이번 배치 중단")
                break
        time.sleep(SLEEP)
    save_cache(m, cache)
    filled = sum(1 for v in cache.values() if v.get("d"))
    loc_n = sum(1 for v in cache.values() if v.get("l"))
    print(f"  [{m}] 결과: 성공 {ok} / 실패 {fail} (현지어 {n_local}건) · "
          f"캐시 총 {len(cache)}건 (영문 {filled} / 현지어 {loc_n})")


def main():
    print("=" * 60)
    print("회사 프로필 수집", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
          "| 대상:", ",".join(MARKETS) or "(없음)")
    print("=" * 60)
    for m in MARKETS:
        if m in ("jp", "kr", "us"):
            try:
                run_market(m)
            except Exception as e:  # noqa: BLE001
                print(f"  [{m}] 수집 실패(건너뜀): {type(e).__name__}: {str(e)[:100]}")


if __name__ == "__main__":
    main()
