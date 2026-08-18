# -*- coding: utf-8 -*-
"""
Multi-Market Screener — 일본 / 한국 / 미국 전 종목 데일리 스크리닝 대시보드
==========================================================================
실행하면 site/ 아래에 jp/ kr/ us/ 3개 시장 페이지 + 허브(index)가 생성됩니다.

  python screener.py                 # 3개 시장 전부 생성
환경변수:
  OUTPUT_DIR        출력 폴더 (기본 site)
  HISTORY_MARKETS   스냅샷 저장할 시장 (예: "jp,kr" / "us" / 비우면 저장 안 함)
"""

import io
import json
import os
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from tradingview_screener import Query, col

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ═════════════════════════ 공통 설정 ═════════════════════════
CONFIG = {
    "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "site"),
    "HISTORY_MARKETS": [m for m in os.environ.get("HISTORY_MARKETS", "").split(",") if m.strip()],
    "OPEN_BROWSER": os.environ.get("GITHUB_ACTIONS") != "true",

    # 시그널 임계값 (전 시장 공통)
    "RVOL_SPIKE": 2.5,
    "GAP_UP_PCT": 3.0,
    "NEAR_HIGH_RATIO": 0.98,
    "GC_MAX_SPREAD": 0.02,
    "RECLAIM_MAX": 0.03,
    "TREND_MAX_EXT": 0.20,
}

JST = ZoneInfo("Asia/Tokyo")
BASE = Path(__file__).resolve().parent

SCAN_COLUMNS = [
    "name", "description", "close", "change", "gap", "low", "high",
    "volume", "Value.Traded", "relative_volume_10d_calc",
    "SMA5", "SMA20", "SMA50", "SMA200",
    "price_52_week_high", "RSI",
    "Perf.W", "Perf.1M", "Perf.3M",
    "sector", "type", "subtype", "exchange",
]

# 트레이딩뷰 섹터 → 한글 (한국·미국 페이지용)
SECTOR_KO = {
    "Commercial Services": "상업서비스", "Communications": "통신",
    "Consumer Durables": "내구소비재", "Consumer Non-Durables": "필수소비재",
    "Consumer Services": "소비자서비스", "Distribution Services": "유통",
    "Electronic Technology": "전자·반도체", "Energy Minerals": "에너지",
    "Finance": "금융", "Government": "공공", "Health Services": "의료서비스",
    "Health Technology": "제약·바이오", "Industrial Services": "산업서비스",
    "Miscellaneous": "기타", "Non-Energy Minerals": "소재·금속",
    "Process Industries": "화학·공정", "Producer Manufacturing": "기계·제조",
    "Retail Trade": "소매", "Technology Services": "IT서비스·SW",
    "Transportation": "운송", "Utilities": "유틸리티",
}

MARKETS = {
    "jp": dict(
        tv_market="japan", exchanges=["TSE"],
        title_html="JP<span>スクリーナー</span>", page_title="JP Screener",
        market_label="도쿄증권거래소", nav_label="🇯🇵 일본",
        turn_div=1e8, turn_label="대금(억엔)",
        min_options=[[0, "거래대금: 전체"], [0.1, "≥ 0.1억엔"], [0.5, "≥ 0.5억엔"], [1, "≥ 1억엔"],
                     [5, "≥ 5억엔"], [10, "≥ 10억엔"], [50, "≥ 50억엔"]],
        default_min=1, seg_label="시장구분", segments=["프라임", "스탠다드", "그로스"],
        us_price=False, data_credit=" / JPX",
    ),
    "kr": dict(
        tv_market="korea", exchanges=["KRX"],
        title_html="KR<span>스크리너</span>", page_title="KR Screener",
        market_label="코스피·코스닥", nav_label="🇰🇷 한국",
        turn_div=1e8, turn_label="대금(억원)",
        min_options=[[0, "거래대금: 전체"], [0.5, "≥ 0.5억원"], [1, "≥ 1억원"], [5, "≥ 5억원"],
                     [10, "≥ 10억원"], [50, "≥ 50억원"], [100, "≥ 100억원"]],
        default_min=1, seg_label="시장구분", segments=["코스피", "코스닥", "코넥스"],
        us_price=False, data_credit=" / KRX",
    ),
    "us": dict(
        tv_market="america", exchanges=["NYSE", "NASDAQ", "AMEX"],
        title_html="US<span>스크리너</span>", page_title="US Screener",
        market_label="NYSE·나스닥·AMEX", nav_label="🇺🇸 미국",
        turn_div=1e6, turn_label="대금($M)",
        min_options=[[0, "거래대금: 전체"], [0.1, "≥ $0.1M"], [0.5, "≥ $0.5M"], [1, "≥ $1M"],
                     [5, "≥ $5M"], [10, "≥ $10M"], [50, "≥ $50M"]],
        default_min=1, seg_label="거래소", segments=["NYSE", "NASDAQ", "AMEX"],
        us_price=True, data_credit="",
    ),
}


# ─────────────────────── 데이터 수집 ───────────────────────
def fetch_tv(mkey: str, retries: int = 3) -> pd.DataFrame:
    mc = MARKETS[mkey]
    last_err = None
    for i in range(retries):
        try:
            n, df = (Query().set_markets(mc["tv_market"]).select(*SCAN_COLUMNS)
                     .where(col("type") == "stock",
                            col("exchange").isin(mc["exchanges"]))
                     .limit(12000).get_scanner_data())
            if mkey == "us":  # 우선주·SPAC유닛 제외
                df = df[~df["subtype"].isin(["preferred", "unit"])].copy()
            print(f"  [{mkey}] TradingView {len(df)}종목 (matched {n})")
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  [{mkey}] 재시도 {i + 1}/{retries} ... ({e})")
            time.sleep(3)
    raise RuntimeError(f"[{mkey}] TradingView 수집 실패: {last_err}")


def master_jp() -> pd.DataFrame | None:
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    seg_map = {"プライム（内国株式）": "프라임", "スタンダード（内国株式）": "스탠다드",
               "グロース（内国株式）": "그로스", "プライム（外国株式）": "프라임",
               "スタンダード（外国株式）": "스탠다드", "グロース（外国株式）": "그로스"}
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        jpx = pd.read_excel(io.BytesIO(r.content), dtype={"コード": str})
        jpx = jpx.rename(columns={"コード": "code", "銘柄名": "m_name", "市場・商品区分": "seg_raw",
                                  "33業種区分": "m_sector"})[["code", "m_name", "seg_raw", "m_sector"]]
        jpx["m_segment"] = jpx["seg_raw"].map(seg_map)
        jpx = jpx[jpx["m_segment"].notna()]
        print(f"  [jp] JPX 종목일람 {len(jpx)}종목")
        return jpx[["code", "m_name", "m_segment", "m_sector"]]
    except Exception as e:  # noqa: BLE001
        print(f"  [jp] JPX 일람 실패 → TV 정보 대체 ({e})")
        return None


def master_kr() -> pd.DataFrame | None:
    try:
        import FinanceDataReader as fdr
        krx = fdr.StockListing("KRX")[["Code", "Name", "Market"]].rename(
            columns={"Code": "code", "Name": "m_name", "Market": "mkt_raw"})
        krx["m_segment"] = krx["mkt_raw"].map(
            lambda v: "코스피" if str(v).startswith("KOSPI")
            else "코스닥" if str(v).startswith("KOSDAQ")
            else "코넥스" if str(v).startswith("KONEX") else "기타")
        krx["m_sector"] = None  # 업종은 TV 섹터(한글화) 사용
        print(f"  [kr] KRX 종목일람 {len(krx)}종목")
        return krx[["code", "m_name", "m_segment", "m_sector"]]
    except Exception as e:  # noqa: BLE001
        print(f"  [kr] KRX 일람 실패 → TV 정보 대체 ({e})")
        return None


# ─────────────────────── 시그널 계산 ───────────────────────
SIG_KEYS = ["sig_spike", "sig_x5", "sig_x20", "sig_high", "sig_gap",
            "sig_gc", "sig_reclaim", "sig_trend"]


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    c = CONFIG
    close, low = df["close"], df["low"]
    s5, s20, s200 = df["SMA5"], df["SMA20"], df["SMA200"]
    df["sig_spike"] = df["relative_volume_10d_calc"] >= c["RVOL_SPIKE"]
    df["sig_x5"] = (low <= s5) & (s5 <= close) & (df["change"] > 0)
    df["sig_x20"] = (low <= s20) & (s20 <= close) & (df["change"] > 0)
    df["sig_high"] = close >= df["price_52_week_high"] * c["NEAR_HIGH_RATIO"]
    df["sig_gap"] = df["gap"] >= c["GAP_UP_PCT"]
    valid = s200.notna() & (s200 > 0)
    df["sig_gc"] = valid & (s20 > s200) & ((s20 / s200 - 1) <= c["GC_MAX_SPREAD"])
    df["sig_reclaim"] = valid & (close > s200) & ((low <= s200) | ((close / s200 - 1) <= c["RECLAIM_MAX"]))
    df["sig_trend"] = valid & (close > s5) & (s5 > s20) & (s20 > s200) & ((close / s200 - 1) <= c["TREND_MAX_EXT"])
    df["ext200"] = ((close / s200 - 1) * 100).where(valid)
    return df


def build_rows(df: pd.DataFrame, turn_div: float) -> list:
    d = df.rename(columns={"Value.Traded": "val", "Perf.W": "pw", "Perf.1M": "p1", "Perf.3M": "p3"})
    sig = pd.Series(0, index=d.index)
    for i, k in enumerate(SIG_KEYS):
        sig = sig | (d[k].fillna(False).astype(int) * (1 << i))
    out = pd.DataFrame({
        "c0": d["code"], "c1": d["disp_name"], "c2": d["sector_final"], "c3": d["segment_final"],
        "c4": d["close"].round(2), "c5": d["change"].round(2),
        "c6": d["SMA5"].round(2), "c7": d["SMA20"].round(2), "c8": d["SMA200"].round(2),
        "c9": d["ext200"].round(1), "c10": d["volume"],
        "c11": d["relative_volume_10d_calc"].round(2), "c12": (d["val"] / turn_div).round(2),
        "c13": d["RSI"].round(1), "c14": d["pw"].round(1), "c15": d["p1"].round(1),
        "c16": d["p3"].round(1), "c17": d["gap"].round(2), "c18": sig, "c19": d["ticker"],
    })
    out = out.astype(object).where(pd.notna(out), None)
    rows = out.values.tolist()
    for row in rows:
        if row[10] is not None:
            row[10] = int(row[10])
        row[18] = int(row[18])
    return rows


# ─────────────────────── 페이지 생성 ───────────────────────
def nav_html(active: str) -> str:
    return "".join(
        f'<a href="../{k}/index.html" class="{"on" if k == active else ""}">{m["nav_label"]}</a>'
        for k, m in MARKETS.items())


def build_market(mkey: str, template: str, out_dir: Path, generated: str) -> dict:
    mc = MARKETS[mkey]
    df = fetch_tv(mkey)
    master = master_jp() if mkey == "jp" else master_kr() if mkey == "kr" else None

    df["code"] = df["name"].astype(str)
    if master is not None:
        df = df.merge(master, on="code", how="left")
        df["disp_name"] = df["m_name"].fillna(df["description"])
        if mkey == "jp":
            df["sector_final"] = df["m_sector"].fillna("その他")
        else:
            df["sector_final"] = df["sector"].map(SECTOR_KO).fillna(df["sector"]).fillna("기타")
        df["segment_final"] = df["m_segment"].fillna("기타")
    else:
        df["disp_name"] = df["description"]
        df["sector_final"] = df["sector"].map(SECTOR_KO).fillna(df["sector"]).fillna("기타")
        df["segment_final"] = df["exchange"] if mkey == "us" else "—"
    if mkey == "us":
        df["segment_final"] = df["exchange"]

    df = compute_signals(df)

    if mkey in CONFIG["HISTORY_MARKETS"]:
        hist = BASE / "history" / mkey
        hist.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(JST).strftime("%Y-%m-%d")
        df.to_csv(hist / f"{stamp}.csv.gz", index=False, encoding="utf-8")
        print(f"  [{mkey}] 스냅샷 저장: history/{mkey}/{stamp}.csv.gz")

    rows = build_rows(df, mc["turn_div"])
    cfg = dict(market=mkey, turnLabel=mc["turn_label"], minOptions=mc["min_options"],
               defaultMin=mc["default_min"], segLabel=mc["seg_label"],
               segments=mc["segments"], usPrice=mc["us_price"])
    html = (template
            .replace("__PAGE_TITLE__", mc["page_title"])
            .replace("__TITLE_HTML__", mc["title_html"])
            .replace("__MARKET_LABEL__", mc["market_label"])
            .replace("__GENERATED__", generated)
            .replace("__COUNT__", f"{len(rows):,}")
            .replace("__NAV__", nav_html(mkey))
            .replace("__DATA_CREDIT__", mc["data_credit"])
            .replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
            .replace("__DATA__", json.dumps(rows, ensure_ascii=False, separators=(",", ":"))))
    page_dir = out_dir / mkey
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "index.html").write_text(html, encoding="utf-8")
    n_s = sum(1 for r in rows if r[18] & 0b00011111 and (r[12] or 0) >= mc["default_min"])
    n_l = sum(1 for r in rows if r[18] & 0b11100000 and (r[12] or 0) >= mc["default_min"])
    print(f"  [{mkey}] 완료 — {len(rows)}종목 / 단기 {n_s} / 중장기 {n_l}")
    return {"count": len(rows), "short": n_s, "long": n_l}


HUB = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=jp/index.html"><title>Stock Screener</title></head>
<body style="background:#0f141c;color:#e9eef6;font-family:sans-serif;padding:40px">
<p>이동 중... 자동으로 넘어가지 않으면 선택하세요:</p>
<p><a href="jp/index.html" style="color:#ffb224">🇯🇵 일본</a> ·
<a href="kr/index.html" style="color:#ffb224">🇰🇷 한국</a> ·
<a href="us/index.html" style="color:#ffb224">🇺🇸 미국</a></p></body></html>"""


def main():
    print("=" * 60)
    print("Multi-Market Screener 실행", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    template = (BASE / "template.html").read_text(encoding="utf-8")
    out_dir = Path(CONFIG["OUTPUT_DIR"])
    if not out_dir.is_absolute():
        out_dir = BASE / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(JST).strftime("%Y-%m-%d (%a) %H:%M JST")

    for mkey in MARKETS:
        try:
            build_market(mkey, template, out_dir, generated)
        except Exception as e:  # noqa: BLE001
            print(f"  [{mkey}] 페이지 생성 실패 — 이전 배포 유지 필요: {e}")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise  # CI에서는 실패로 처리해 옛 사이트를 덮어쓰지 않음

    (out_dir / "index.html").write_text(HUB, encoding="utf-8")
    print(f"\n완료 → {out_dir}")

    if CONFIG["OPEN_BROWSER"]:
        try:
            webbrowser.open((out_dir / "jp" / "index.html").as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    main()
