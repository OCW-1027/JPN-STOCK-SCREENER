# -*- coding: utf-8 -*-
"""
JP Market Screener — 일본 상장 전 종목 데일리 스크리닝 대시보드
================================================================
매일 장 마감 후 실행 → 전 종목 시세/지표 수집 → 시그널 계산 → dashboard.html 생성

데이터 소스:
  1) TradingView Screener API (tradingview-screener 라이브러리, 무료)
  2) JPX 공식 상장종목일람 data_j.xls (일본어 종목명 / 33업종 / 시장구분)

실행:  python screener.py
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

# ── Windows 콘솔 한글 깨짐 방지 ──────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ═════════════════════════ 설정 ═════════════════════════════
CONFIG = {
    "OUTPUT_HTML": "dashboard.html",   # OneDrive 폴더 경로로 바꾸면 폰에서도 열람 가능
    "SAVE_HISTORY_CSV": True,          # ./history/YYYY-MM-DD.csv 로 매일 스냅샷 저장 (추후 백테스트/스파크라인용)
    "OPEN_BROWSER": True,              # 생성 후 브라우저 자동 열기

    # ── 단기 시그널 임계값 ──
    "RVOL_SPIKE": 2.5,        # 거래량 급증: 10일 평균 대비 배수
    "GAP_UP_PCT": 3.0,        # 갭업 %
    "NEAR_HIGH_RATIO": 0.98,  # 52주 신고가 근접 (종가 >= 신고가의 98%)

    # ── 중장기 시그널 임계값 ──
    "GC_MAX_SPREAD": 0.02,    # 골든크로스 직후: 20MA가 200MA 위 2% 이내
    "RECLAIM_MAX": 0.03,      # 200일선 탈환: 200MA 위 3% 이내(또는 당일 상향 통과)
    "TREND_MAX_EXT": 0.20,    # 정배열 초입: 200MA 이격 20% 이내 (과열 제외)
}
# ════════════════════════════════════════════════════════════

# GitHub Actions 등에서 환경변수로 동작 오버라이드
if os.environ.get("OUTPUT_HTML"):
    CONFIG["OUTPUT_HTML"] = os.environ["OUTPUT_HTML"]
if os.environ.get("GITHUB_ACTIONS") == "true":
    CONFIG["OPEN_BROWSER"] = False

JST = ZoneInfo("Asia/Tokyo")
BASE = Path(__file__).resolve().parent

SCAN_COLUMNS = [
    "name", "description", "close", "change", "gap", "low", "high",
    "volume", "Value.Traded", "relative_volume_10d_calc",
    "SMA5", "SMA20", "SMA50", "SMA200",
    "price_52_week_high", "RSI",
    "Perf.W", "Perf.1M", "Perf.3M",
    "sector", "type", "exchange", "market_cap_basic",
]

JPX_XLS_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"

SEGMENT_MAP = {
    "プライム（内国株式）": "프라임",
    "スタンダード（内国株式）": "스탠다드",
    "グロース（内国株式）": "그로스",
    "プライム（外国株式）": "프라임",
    "スタンダード（外国株式）": "스탠다드",
    "グロース（外国株式）": "그로스",
}


# ─────────────────────── 데이터 수집 ───────────────────────
def fetch_tradingview(retries: int = 3) -> pd.DataFrame:
    """일본 전 종목 스냅샷 (도쿄증권거래소만)."""
    last_err = None
    for i in range(retries):
        try:
            n, df = (
                Query()
                .set_markets("japan")
                .select(*SCAN_COLUMNS)
                .where(col("type") == "stock")
                .limit(8000)
                .get_scanner_data()
            )
            df = df[df["exchange"] == "TSE"].copy()   # 나고야/후쿠오카/삿포로 중복 제거
            print(f"  TradingView: 전체 {n}건 중 도쿄증권거래소 {len(df)}종목")
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  재시도 {i + 1}/{retries} ... ({e})")
            time.sleep(3)
    raise RuntimeError(f"TradingView 데이터 수집 실패: {last_err}")


def fetch_jpx_master() -> pd.DataFrame | None:
    """JPX 공식 상장종목일람 — 일본어 종목명 / 33업종 / 시장구분."""
    try:
        r = requests.get(JPX_XLS_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        jpx = pd.read_excel(io.BytesIO(r.content), dtype={"コード": str})
        jpx = jpx.rename(columns={
            "コード": "code", "銘柄名": "name_jp",
            "市場・商品区分": "segment_raw", "33業種区分": "sector33",
        })[["code", "name_jp", "segment_raw", "sector33"]]
        jpx["segment"] = jpx["segment_raw"].map(SEGMENT_MAP)
        jpx = jpx[jpx["segment"].notna()]  # ETF/REIT/PRO Market 제외
        print(f"  JPX 종목일람: {len(jpx)}종목 (프라임/스탠다드/그로스)")
        return jpx
    except Exception as e:  # noqa: BLE001
        print(f"  JPX 종목일람 취득 실패 → TradingView 정보로 대체 ({e})")
        return None


# ─────────────────────── 시그널 계산 ───────────────────────
def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    c = CONFIG
    close, low = df["close"], df["low"]
    s5, s20, s200 = df["SMA5"], df["SMA20"], df["SMA200"]

    # 단기
    df["sig_spike"] = df["relative_volume_10d_calc"] >= c["RVOL_SPIKE"]
    df["sig_x5"] = (low <= s5) & (s5 <= close) & (df["change"] > 0)
    df["sig_x20"] = (low <= s20) & (s20 <= close) & (df["change"] > 0)
    df["sig_high"] = close >= df["price_52_week_high"] * c["NEAR_HIGH_RATIO"]
    df["sig_gap"] = df["gap"] >= c["GAP_UP_PCT"]

    # 중장기 (SMA200 미산출 신규상장주는 자동 제외)
    valid = s200.notna() & (s200 > 0)
    df["sig_gc"] = valid & (s20 > s200) & ((s20 / s200 - 1) <= c["GC_MAX_SPREAD"])
    df["sig_reclaim"] = valid & (close > s200) & (
        (low <= s200) | ((close / s200 - 1) <= c["RECLAIM_MAX"])
    )
    df["sig_trend"] = valid & (close > s5) & (s5 > s20) & (s20 > s200) & (
        (close / s200 - 1) <= c["TREND_MAX_EXT"]
    )

    df["ext200"] = ((close / s200 - 1) * 100).where(valid)  # 200일선 이격도 %
    return df


# ─────────────────────── 대시보드 생성 ───────────────────────
SIG_KEYS = ["sig_spike", "sig_x5", "sig_x20", "sig_high", "sig_gap",
            "sig_gc", "sig_reclaim", "sig_trend"]


def r(v, nd=1):
    """반올림 + NaN → None (JSON null)."""
    try:
        if v is None or pd.isna(v):
            return None
        return round(float(v), nd)
    except Exception:  # noqa: BLE001
        return None


def build_rows(df: pd.DataFrame) -> list:
    d = df.rename(columns={
        "Value.Traded": "val", "Perf.W": "pw", "Perf.1M": "p1", "Perf.3M": "p3",
    })
    sig = pd.Series(0, index=d.index)
    for i, k in enumerate(SIG_KEYS):
        sig = sig | (d[k].fillna(False).astype(int) * (1 << i))

    out = pd.DataFrame({
        "c0": d["code"], "c1": d["disp_name"], "c2": d["sector_final"], "c3": d["segment_final"],
        "c4": d["close"].round(1), "c5": d["change"].round(2),
        "c6": d["SMA5"].round(1), "c7": d["SMA20"].round(1), "c8": d["SMA200"].round(1),
        "c9": d["ext200"].round(1), "c10": d["volume"],
        "c11": d["relative_volume_10d_calc"].round(2), "c12": (d["val"] / 1e8).round(2),
        "c13": d["RSI"].round(1), "c14": d["pw"].round(1), "c15": d["p1"].round(1),
        "c16": d["p3"].round(1), "c17": d["gap"].round(2), "c18": sig,
    })
    out = out.astype(object).where(pd.notna(out), None)
    rows = out.values.tolist()
    for row in rows:
        if row[10] is not None:
            row[10] = int(row[10])
        row[18] = int(row[18])
    return rows


def main():
    print("=" * 60)
    print("JP Market Screener 실행", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)

    print("[1/4] TradingView 전 종목 수집 ...")
    df = fetch_tradingview()

    print("[2/4] JPX 종목일람 병합 ...")
    jpx = fetch_jpx_master()
    df["code"] = df["name"].astype(str)
    if jpx is not None:
        df = df.merge(jpx, on="code", how="left")
        df["disp_name"] = df["name_jp"].fillna(df["description"])
        df["sector_final"] = df["sector33"].fillna("その他")  # JPX 미수록(신규상장·특수종목)은 통합
        df["segment_final"] = df["segment"].fillna("기타")
        # JPX 일람에 없는 종목(ETF성/특수)은 제외하지 않고 '기타'로 유지
    else:
        df["disp_name"] = df["description"]
        df["sector_final"] = df["sector"].fillna("기타")
        df["segment_final"] = "—"
    df["name_final"] = df["code"]

    print("[3/4] 시그널 계산 ...")
    df = compute_signals(df)
    n_short = int(df[["sig_spike", "sig_x5", "sig_x20", "sig_high", "sig_gap"]].any(axis=1).sum())
    n_long = int(df[["sig_gc", "sig_reclaim", "sig_trend"]].any(axis=1).sum())
    print(f"  단기 시그널 {n_short}종목 / 중장기 시그널 {n_long}종목")

    if CONFIG["SAVE_HISTORY_CSV"]:
        hist_dir = BASE / "history"
        hist_dir.mkdir(exist_ok=True)
        stamp = datetime.now(JST).strftime("%Y-%m-%d")
        df.to_csv(hist_dir / f"{stamp}.csv.gz", index=False, encoding="utf-8")
        print(f"  스냅샷 저장: history/{stamp}.csv.gz")

    print("[4/4] 대시보드 생성 ...")
    rows = build_rows(df)
    generated = datetime.now(JST).strftime("%Y-%m-%d (%a) %H:%M JST")

    template = (BASE / "template.html").read_text(encoding="utf-8")
    html = (template
            .replace("__GENERATED__", generated)
            .replace("__COUNT__", str(len(rows)))
            .replace("__DATA__", json.dumps(rows, ensure_ascii=False, separators=(",", ":"))))

    out = Path(CONFIG["OUTPUT_HTML"])
    if not out.is_absolute():
        out = BASE / out
    out.write_text(html, encoding="utf-8")
    print(f"  완료 → {out}  ({out.stat().st_size / 1e6:.1f} MB)")

    if CONFIG["OPEN_BROWSER"]:
        try:
            webbrowser.open(out.as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    main()
