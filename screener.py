# -*- coding: utf-8 -*-
"""
Multi-Market Screener v2 — 일본/한국/미국 + 재무지표/MACD/사업내용/확장 시그널
================================================================================
python screener.py  →  site/{jp,kr,us}/index.html + 허브 생성
환경변수: OUTPUT_DIR(기본 site), HISTORY_MARKETS("jp,kr"/"us"/빈값)
"""
import gzip, io, json, os, re, sys, time, webbrowser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from tradingview_screener import Query, col

import i18n

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CONFIG = {
    "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "site"),
    "HISTORY_MARKETS": [m for m in os.environ.get("HISTORY_MARKETS", "").split(",") if m.strip()],
    "OPEN_BROWSER": os.environ.get("GITHUB_ACTIONS") != "true",
    # ── 단기 ──
    "RVOL_SPIKE": 2.5, "GAP_UP_PCT": 3.0, "NEAR_HIGH_RATIO": 0.98, "RSI_REBOUND": 32,
    # ── 중장기 ──
    "GC_MAX_SPREAD": 0.02, "RECLAIM_MAX": 0.03, "TREND_MAX_EXT": 0.20, "MACD_GC_MAX": 0.005,
    # ── 가치·펀더 ──
    "VAL_PER_MAX": 10, "VAL_PBR_MAX": 1.0, "DIV_MIN": 4.0, "QUAL_ROE": 15, "QUAL_EQR": 50,
    # ── 성장 ──
    "GROW_YOY": 20.0,      # 고성장: 최근 분기 매출 YoY
    "GROW_CAGR": 10.0,     # 고성장: 매출 5년 CAGR 동시 충족
    "ACCEL_YOY": 10.0,     # 이익가속: EPS YoY 하한
    "ACCEL_GAP": 1.5,      # 이익가속: EPS 성장이 매출 성장의 N배 이상
    "GARP_PSR": 2.0,       # 저평가성장: PSR 상한
    "GARP_YOY": 10.0,      # 저평가성장: 매출 YoY 하한
    "GARP_OPM": 5.0,       # 저평가성장: 영업이익률 하한
}

JST = ZoneInfo("Asia/Tokyo")
BASE = Path(__file__).resolve().parent

SCAN_COLUMNS = [
    "name", "description", "close", "change", "gap", "low", "high",
    "volume", "Value.Traded", "relative_volume_10d_calc",
    "SMA5", "SMA20", "SMA50", "SMA200", "price_52_week_high", "RSI",
    "Perf.W", "Perf.1M", "Perf.3M", "sector", "industry", "type", "subtype", "exchange",
    "market_cap_basic", "price_earnings_ttm", "price_book_fq",
    "earnings_per_share_basic_ttm", "return_on_equity", "dividends_yield_current",
    "total_assets", "total_liabilities_fy", "ebitda", "MACD.macd", "MACD.signal",
    # 성장 (요청: 분기·연간·TTM·5년)
    "total_revenue_yoy_growth_fq", "total_revenue_yoy_growth_fy",
    "total_revenue_yoy_growth_ttm", "total_revenue_qoq_growth_fq",
    "total_revenue_cagr_5y", "earnings_per_share_diluted_yoy_growth_fq",
    # 수익성·밸류
    "operating_margin_ttm", "return_on_invested_capital", "price_sales_ratio",
    "debt_to_equity",
    # 밸류·위치
    "price_earnings_growth_ttm", "Perf.YTD", "price_52_week_low", "Perf.Y",
]

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
    "jp": dict(tv_market="japan", exchanges=["TSE"],
               title_html="JP<span>スクリーナー</span>", page_title="JP Screener",
               market_label="도쿄증권거래소", nav_label="🇯🇵 일본",
               turn_div=1e8, turn_label="대금(억엔)", mcap_div=1e8, mcap_label="시총(억)",
               ebitda_div=1e8, ebitda_label="EBITDA(억)",
               min_options=[[0, "거래대금: 전체"], [0.1, "≥ 0.1억엔"], [0.5, "≥ 0.5억엔"], [1, "≥ 1억엔"],
                            [5, "≥ 5억엔"], [10, "≥ 10억엔"], [50, "≥ 50억엔"]],
               default_min=1, seg_label="시장구분", segments=["프라임", "스탠다드", "그로스"],
               us_price=False, data_credit=" / JPX"),
    "kr": dict(tv_market="korea", exchanges=["KRX"],
               title_html="KR<span>스크리너</span>", page_title="KR Screener",
               market_label="코스피·코스닥", nav_label="🇰🇷 한국",
               turn_div=1e8, turn_label="대금(억원)", mcap_div=1e8, mcap_label="시총(억)",
               ebitda_div=1e8, ebitda_label="EBITDA(억)",
               min_options=[[0, "거래대금: 전체"], [0.5, "≥ 0.5억원"], [1, "≥ 1억원"], [5, "≥ 5억원"],
                            [10, "≥ 10억원"], [50, "≥ 50억원"], [100, "≥ 100억원"]],
               default_min=1, seg_label="시장구분", segments=["코스피", "코스닥", "코넥스"],
               us_price=False, data_credit=" / KRX"),
    "us": dict(tv_market="america", exchanges=["NYSE", "NASDAQ", "AMEX"],
               title_html="US<span>스크리너</span>", page_title="US Screener",
               market_label="NYSE·나스닥·AMEX", nav_label="🇺🇸 미국",
               turn_div=1e6, turn_label="대금($M)", mcap_div=1e9, mcap_label="시총($B)",
               ebitda_div=1e6, ebitda_label="EBITDA($M)",
               min_options=[[0, "거래대금: 전체"], [0.1, "≥ $0.1M"], [0.5, "≥ $0.5M"], [1, "≥ $1M"],
                            [5, "≥ $5M"], [10, "≥ $10M"], [50, "≥ $50M"]],
               default_min=1, seg_label="거래소", segments=["NYSE", "NASDAQ", "AMEX"],
               us_price=True, data_credit=""),
}


def fetch_tv(mkey, retries=3):
    mc = MARKETS[mkey]
    last = None
    for i in range(retries):
        try:
            n, df = (Query().set_markets(mc["tv_market"]).select(*SCAN_COLUMNS)
                     .where(col("type") == "stock", col("exchange").isin(mc["exchanges"]))
                     .limit(12000).get_scanner_data())
            if mkey == "us":
                df = df[~df["subtype"].isin(["preferred", "unit"])].copy()
            print(f"  [{mkey}] TradingView {len(df)}종목 (matched {n})")
            return df
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  [{mkey}] 재시도 {i+1}/{retries} ... ({e})")
            time.sleep(3)
    raise RuntimeError(f"[{mkey}] TradingView 수집 실패: {last}")


def master_jp():
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    seg = {"プライム（内国株式）": "프라임", "スタンダード（内国株式）": "스탠다드",
           "グロース（内国株式）": "그로스", "プライム（外国株式）": "프라임",
           "スタンダード（外国株式）": "스탠다드", "グロース（外国株式）": "그로스"}
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        j = pd.read_excel(io.BytesIO(r.content), dtype={"コード": str}).rename(
            columns={"コード": "code", "銘柄名": "m_name", "市場・商品区分": "seg_raw", "33業種区分": "m_sector"})
        j["m_segment"] = j["seg_raw"].map(seg)
        j = j[j["m_segment"].notna()]
        j["m_biz"] = None
        print(f"  [jp] JPX 종목일람 {len(j)}종목")
        return j[["code", "m_name", "m_segment", "m_sector", "m_biz"]]
    except Exception as e:  # noqa: BLE001
        print(f"  [jp] JPX 일람 실패 → TV 정보 대체 ({e})")
        return None


def master_kr():
    try:
        import FinanceDataReader as fdr
        krx = fdr.StockListing("KRX")[["Code", "Name", "Market"]].rename(
            columns={"Code": "code", "Name": "m_name", "Market": "mkt"})
        krx["m_segment"] = krx["mkt"].map(
            lambda v: "코스피" if str(v).startswith("KOSPI")
            else "코스닥" if str(v).startswith("KOSDAQ")
            else "코넥스" if str(v).startswith("KONEX") else "기타")
        krx["m_sector"] = None
        try:
            desc = fdr.StockListing("KRX-DESC")[["Code", "Products", "Industry"]].rename(columns={"Code": "code"})
            krx = krx.merge(desc, on="code", how="left")
            krx["m_biz"] = krx["Products"].fillna(krx["Industry"])
        except Exception:
            krx["m_biz"] = None
        print(f"  [kr] KRX 종목일람 {len(krx)}종목")
        return krx[["code", "m_name", "m_segment", "m_sector", "m_biz"]]
    except Exception as e:  # noqa: BLE001
        print(f"  [kr] KRX 일람 실패 → TV 정보 대체 ({e})")
        return None



# ─────────────────── 한국 실시간 시세 (네이버) ───────────────────
NAVER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Referer": "https://m.stock.naver.com/",
    "Accept": "application/json",
}

# 네이버는 엔드포인트 경로를 종종 바꾸므로 후보를 순서대로 시도한다.
NAVER_LIST_ENDPOINTS = [
    "https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize={size}",
    "https://api.stock.naver.com/stock/exchange/{market}/marketValue?page={page}&pageSize={size}",
    "https://m.stock.naver.com/api/stocks/exchange/{market}/marketValue?page={page}&pageSize={size}",
]
NAVER_POLLING = "https://polling.finance.naver.com/api/realtime/domestic/stock/{codes}"


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_items(payload):
    """응답 구조가 달라도 종목 리스트를 찾아 표준화."""
    if isinstance(payload, dict):
        for key in ("stocks", "datas", "result", "items", "list"):
            v = payload.get(key)
            if isinstance(v, list):
                payload = v
                break
            if isinstance(v, dict):
                for k2 in ("stocks", "datas", "areas", "list"):
                    if isinstance(v.get(k2), list):
                        payload = v[k2]
                        break
    if not isinstance(payload, list):
        return []
    out = []
    for it in payload:
        if not isinstance(it, dict):
            continue
        code = it.get("itemCode") or it.get("cd") or it.get("code")
        close = _num(it.get("closePrice") or it.get("nv") or it.get("now"))
        if not code or close is None:
            continue
        out.append({
            "code": str(code).zfill(6),
            "nv_close": close,
            "nv_change": _num(it.get("fluctuationsRatio") or it.get("cr")) or 0.0,
            "nv_volume": _num(it.get("accumulatedTradingVolume") or it.get("aq") or it.get("volume")) or 0.0,
        })
    return out


def _try_list_endpoint(tpl, timeout):
    rows, size = [], 100
    for market in ("KOSPI", "KOSDAQ"):
        for page in range(1, 40):
            r = requests.get(tpl.format(market=market, page=page, size=size),
                             headers=NAVER_HEADERS, timeout=timeout)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            items = _parse_items(r.json())
            if not items:
                break
            rows += items
            if len(items) < size:
                break
    return rows


def _try_polling(codes, timeout, batch=80):
    rows = []
    for i in range(0, len(codes), batch):
        chunk = ",".join(codes[i:i + batch])
        r = requests.get(NAVER_POLLING.format(codes=chunk), headers=NAVER_HEADERS, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        rows += _parse_items(r.json())
        time.sleep(0.05)
    return rows


def fetch_naver_kr(codes=None, timeout=12):
    """여러 엔드포인트를 순차 시도. 전부 실패하면 None(→ TradingView 값 사용)."""
    for tpl in NAVER_LIST_ENDPOINTS:
        try:
            rows = _try_list_endpoint(tpl, timeout)
            df = pd.DataFrame(rows).drop_duplicates(subset="code") if rows else pd.DataFrame()
            if len(df) >= 1000:
                print(f"  [kr] 네이버 취득: 고유 {len(df)}종목 "
                      f"(원본 {len(rows)}행 — 중복·ETF 포함)")
                return df
            print(f"  [kr] 후보 응답 부족(고유 {len(df)}종목) — 다음 엔드포인트 시도")
        except Exception as e:  # noqa: BLE001
            print(f"  [kr] 후보 실패({type(e).__name__}: {str(e)[:50]}) — 다음 엔드포인트 시도")
    if codes:
        try:
            rows = _try_polling(list(codes), timeout)
            df = pd.DataFrame(rows).drop_duplicates(subset="code") if rows else pd.DataFrame()
            if len(df) >= 1000:
                print(f"  [kr] 네이버 취득: 고유 {len(df)}종목 (polling)")
                return df
            print(f"  [kr] polling 응답 부족(고유 {len(df)}종목)")
        except Exception as e:  # noqa: BLE001
            print(f"  [kr] polling 실패({type(e).__name__}: {str(e)[:60]})")
    print("  [kr] 네이버 취득 실패 → TradingView 값 사용")
    return None


def apply_realtime_kr(df):
    """네이버 실시간 시세를 TradingView 데이터프레임에 덮어쓴다.
    이동평균·재무지표는 TradingView 값을 유지(하루 단위라 지연 영향 없음)."""
    nv = fetch_naver_kr(codes=df['code'].astype(str).tolist())
    if nv is None:
        return df, "TradingView"
    d = df.merge(nv, on="code", how="left")
    hit = d["nv_close"].notna()
    if hit.sum() < len(d) * 0.5:
        print(f"  [kr] 매칭률 낮음({hit.sum()}/{len(d)}) → TradingView 값 사용")
        return df, "TradingView"
    prev = d["close"] / (1 + d["change"] / 100)          # 전일 종가 역산
    d.loc[hit, "close"] = d.loc[hit, "nv_close"]
    d.loc[hit, "change"] = d.loc[hit, "nv_change"]
    d.loc[hit, "volume"] = d.loc[hit, "nv_volume"]
    d.loc[hit, "Value.Traded"] = d.loc[hit, "nv_close"] * d.loc[hit, "nv_volume"]
    # 갱신된 가격 기준으로 당일 고저 근사치 보정 (돌파 판정용)
    d.loc[hit, "high"] = d.loc[hit, ["high", "close"]].max(axis=1)
    d.loc[hit, "low"] = d.loc[hit, ["low", "close"]].min(axis=1)
    d = d.drop(columns=["nv_close", "nv_change", "nv_volume"])
    print(f"  [kr] 실시간 반영 {int(hit.sum())}/{len(d)}종목 "
          f"({hit.sum() / len(d) * 100:.1f}%) — 미매칭은 TradingView 값 유지")
    return d, "Naver"




# ─────────────────── 대표지수 시세 ───────────────────
# 소스: 일본=야후재팬(15분지연/실시간) · 한국=네이버(실시간) · 미국·환율=야후USA(15분지연)
YJ_URL = "https://finance.yahoo.co.jp/quote/{code}"
YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d"
NAVER_IDX = [
    "https://m.stock.naver.com/api/index/{code}/basic",
    "https://api.stock.naver.com/index/{code}/basic",
    "https://polling.finance.naver.com/api/realtime/domestic/index/{code}",
]
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}

# (그룹, 소스, 코드, 한국어, 일본어, TradingView심볼)
INDEX_LIST = [
    ("jp", "yj", "998407.O", "닛케이225",   "日経225",      "TVC:NI225"),
    ("jp", "yj", "998405.T", "TOPIX",       "TOPIX",        "TVC:TOPIX"),
    ("jp", "yj", "2516.T",   "그로스250*",  "グロース250*", "TSE:2516"),
    ("jp", "yj", "1591.T",   "JPX400*",     "JPX400*",      "TSE:1591"),
    ("kr", "nv", "KOSPI",    "코스피",      "KOSPI",        "KRX:KOSPI"),
    ("kr", "nv", "KOSDAQ",   "코스닥",      "KOSDAQ",       "KRX:KOSDAQ"),
    ("kr", "nv", "KPI200",   "코스피200",   "KOSPI200",     "KRX:KOSPI200"),
    ("us", "yf", "^DJI",     "다우",        "NYダウ",       "TVC:DJI"),
    ("us", "yf", "^IXIC",    "나스닥",      "NASDAQ",       "TVC:IXIC"),
    ("us", "yf", "^GSPC",    "S&P500",      "S&P500",       "TVC:SPX"),
    ("us", "yf", "^SOX",     "SOX반도체",   "SOX半導体",    "TVC:SOX"),
    ("us", "yf", "^RUT",     "러셀2000",    "ラッセル2000", "TVC:RUT"),
    ("us", "yf", "^VIX",     "VIX",         "VIX",          "TVC:VIX"),
    ("fx", "yf", "DX-Y.NYB", "달러인덱스",  "ドル指数",     "TVC:DXY"),
    ("fx", "yf", "JPY=X",    "USD/JPY",     "ドル円",       "FX:USDJPY"),
    ("fx", "yf", "KRW=X",    "USD/KRW",     "ドルウォン",   "FX:USDKRW"),
]


def _f(v):
    try:
        return float(str(v).replace(",", "").replace("−", "-").replace("+", "").strip())
    except (TypeError, ValueError):
        return None


def _idx_yahoo_jp(code, timeout=10):
    """야후재팬 지수·ETF 페이지에서 현재가와 전일비%를 추출."""
    r = requests.get(YJ_URL.format(code=code), headers=UA, timeout=timeout)
    if r.status_code != 200:
        return None
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    m = re.search(r"([\d,]+(?:\.\d+)?) 前日比 ([+\-−][\d,.]+) \( ?([+\-−][\d.]+) ?%", t)
    if not m:
        return None
    price, chg = _f(m.group(1)), _f(m.group(3))
    if price is None or chg is None:
        return None
    return price, chg


def _idx_naver(code, timeout=10):
    """네이버 지수 API (실시간). 후보 엔드포인트 순차 시도."""
    for tpl in NAVER_IDX:
        try:
            r = requests.get(tpl.format(code=code),
                             headers={**UA, "Referer": "https://m.stock.naver.com/",
                                      "Accept": "application/json"}, timeout=timeout)
            if r.status_code != 200:
                continue
            j = r.json()
            if isinstance(j, dict) and "datas" in j and j["datas"]:
                j = j["datas"][0]
            if isinstance(j, list) and j:
                j = j[0]
            if not isinstance(j, dict):
                continue
            price = _f(j.get("closePrice") or j.get("nv") or j.get("now"))
            chg = _f(j.get("fluctuationsRatio") or j.get("cr"))
            if price is not None and chg is not None:
                return price, chg
        except Exception:
            continue
    return None


def _idx_yahoo_us(sym, timeout=10):
    """야후USA 차트 API. 전일종가는 일봉 배열에서 직접 계산(meta 값은 부정확)."""
    r = requests.get(YF_CHART.format(sym=sym), headers=UA, timeout=timeout)
    res = (r.json().get("chart") or {}).get("result")
    if not res:
        return None
    m = res[0]["meta"]
    closes = [c for c in (res[0]["indicators"]["quote"][0].get("close") or []) if c]
    if len(closes) < 2:
        return None
    price = m.get("regularMarketPrice") or closes[-1]
    prev = closes[-2] if abs(closes[-1] - price) < 1e-9 else closes[-2]
    if not prev:
        return None
    return float(price), round((float(price) / float(prev) - 1) * 100, 2)


def fetch_indices():
    """지수 스트립 데이터. 항목별로 실패해도 나머지는 그대로 표시."""
    out, fails = [], []
    for grp, src, code, ko, ja, tv in INDEX_LIST:
        got = None
        try:
            if src == "yj":
                got = _idx_yahoo_jp(code)
            elif src == "nv":
                got = _idx_naver(code) or (_idx_yahoo_us({"KOSPI": "^KS11", "KOSDAQ": "^KQ11",
                                                          "KPI200": "^KS200"}.get(code, code)))
            else:
                got = _idx_yahoo_us(code)
        except Exception:
            got = None
        if not got:
            fails.append(ko)
            continue
        price, chg = got
        out.append([ko, ja, round(price, 2), round(chg, 2), tv, grp])
    print(f"  [지수] {len(out)}/{len(INDEX_LIST)}개 취득" + (f" (실패: {', '.join(fails)})" if fails else ""))
    return out



# ─────────────── 유입배: 5일 매매대금 ÷ 60일 매매대금 ───────────────
INFLOW_SHORT, INFLOW_LONG = 5, 60
INFLOW_MIN = 20          # 이 일수 이상이면 근사치라도 계산
INFLOW_TH = 1.3          # '지속유입' 임계
INFLOW_STREAK = 3        # 연속 충족 일수


def compute_inflow(mkey):
    """(유입배 dict, 지속유입 dict, 사용일수). 데이터 부족 시 빈 dict."""
    import glob
    files = sorted(glob.glob(str(BASE / "history" / mkey / "*.csv.gz")))[-(INFLOW_LONG + INFLOW_STREAK):]
    if len(files) < INFLOW_MIN:
        print(f"  [{mkey}] 유입배: 스냅샷 {len(files)}일 (최소 {INFLOW_MIN}일 필요) → 축적 대기")
        return {}, {}, len(files)

    series, kept, prev_close = {}, 0, None
    for f in files:
        try:
            d = pd.read_csv(f, compression="gzip", dtype={"code": str})
        except Exception:
            continue
        if not {"code", "Value.Traded"} <= set(d.columns):
            continue
        d = d.dropna(subset=["code"]).drop_duplicates(subset="code")
        if prev_close is not None and "close" in d.columns:          # 휴장일 제거
            cur = d.set_index("code")["close"]
            common = cur.index.intersection(prev_close.index)
            if len(common) > 100 and (cur.loc[common] == prev_close.loc[common]).mean() > 0.97:
                continue
        if "close" in d.columns:
            prev_close = d.set_index("code")["close"]
        for c, v in zip(d["code"].astype(str), d["Value.Traded"].fillna(0).astype(float)):
            series.setdefault(c, {})[kept] = v
        kept += 1

    if kept < INFLOW_MIN:
        return {}, {}, kept

    def ratio_at(vals, end):
        lo = max(0, end - INFLOW_LONG + 1)
        long_v = [vals[i] for i in range(lo, end + 1) if i in vals]
        short_v = [vals[i] for i in range(max(0, end - INFLOW_SHORT + 1), end + 1) if i in vals]
        if len(long_v) < INFLOW_MIN or not short_v:
            return None
        la = sum(long_v) / len(long_v)
        return (sum(short_v) / len(short_v) / la) if la > 0 else None

    inflow, streak = {}, {}
    for c, vals in series.items():
        r = ratio_at(vals, kept - 1)
        if r is None:
            continue
        inflow[c] = round(r, 2)
        streak[c] = all((lambda x: x is not None and x >= INFLOW_TH)(ratio_at(vals, kept - 1 - b))
                        for b in range(INFLOW_STREAK))
    print(f"  [{mkey}] 유입배: {len(inflow)}종목 ({kept}일 기준"
          f"{'·근사치' if kept < INFLOW_LONG else ''}) / 지속유입 {sum(streak.values())}종목")
    return inflow, streak, kept


# ─────────────────── TDnet 적시공시 (일본) ───────────────────
KW_PATTERNS = [  # 비트 순서 = i18n.kw_labels 순서
    r"上方修正", r"下方修正", r"増配|復配", r"減配|無配", r"自己株式|自社株",
    r"株式分割", r"決算短信|決算説明", r"業績予想", r"配当予想",
    r"業務提携|資本提携", r"公開買付|TOB", r"月次",
]
KW_STRONG = (1 << 0) | (1 << 2) | (1 << 4) | (1 << 5) | (1 << 10)  # 상방·증배·자사주·분할·TOB
DIS_CAP_PLAIN = 700   # 키워드 미해당 공시 최대 보존 건수
TDNET_DAYS = 5        # 조회 영업일 수 (오늘 포함)


def _tdnet_day(yyyymmdd, retries=3):
    url = f"https://webapi.yanoshin.jp/webapi/tdnet/list/{yyyymmdd}.json?limit=3000"
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
            r.raise_for_status()
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    else:
        raise RuntimeError(f"TDnet {yyyymmdd} 재시도 실패: {last}")
    out = []
    for it in (r.json() or {}).get("items", []):
        if not isinstance(it, dict):
            continue
        # API 응답 구조 변경 대응: {"Tdnet": {...}} 와 {...} 두 형태 모두 처리
        td = it.get("Tdnet") if isinstance(it.get("Tdnet"), dict) else it
        code = str(td.get("company_code") or "")[:4]
        title = str(td.get("title") or "").strip()
        if not code or not title:
            continue
        bits = 0
        for i, pat in enumerate(KW_PATTERNS):
            if re.search(pat, title):
                bits |= 1 << i
        raw_pub = str(td.get("pubdate") or "")            # "YYYY-MM-DD HH:MM:SS"
        pub = raw_pub[5:16].replace("-", "/")             # 화면 표시용 "MM/DD HH:MM"
        out.append([pub, code, str(td.get("company_name") or ""), bits, title,
                    str(td.get("document_url") or ""), raw_pub])
    return out


def fetch_tdnet(universe_codes):
    """오늘 + 직전 영업일 공시. 실패 시 None(탭 숨김이 아닌 빈 목록으로 처리)."""
    from datetime import timedelta
    now = datetime.now(JST)
    days, d = [], now
    while len(days) < TDNET_DAYS:
        if d.weekday() < 5:
            days.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    items = []
    for day in days:
        try:
            items += _tdnet_day(day)
        except Exception as e:  # noqa: BLE001
            print(f"  [jp] TDnet {day} 실패: {type(e).__name__}: {str(e)[:60]}")
    uni = set(universe_codes)
    items = [x for x in items if x[1] in uni]
    items.sort(key=lambda x: x[6], reverse=True)
    tagged = [x for x in items if x[3]]
    plain = [x for x in items if not x[3]][:DIS_CAP_PLAIN]
    merged = sorted(tagged + plain, key=lambda x: x[6], reverse=True)
    merged = [x[:6] for x in merged]          # 화면 전송 시 원본 시각 컬럼 제거
    dmap = {}
    for x in tagged:
        dmap[x[1]] = dmap.get(x[1], 0) | x[3]
    latest = merged[0][0] if merged else "-"
    print(f"  [jp] TDnet 공시 {len(merged)}건 (키워드 {len(tagged)} / 일반 {len(plain)}) 최신 {latest}")
    return {"items": merged, "map": dmap, "strong": KW_STRONG}


def load_profiles(mkey):
    p = BASE / "profiles" / f"{mkey}.json.gz"
    if not p.exists():
        return None
    try:
        return json.loads(gzip.decompress(p.read_bytes()).decode("utf-8"))
    except Exception:
        return None


# 시그널 가중치 — 성과분석 데이터가 쌓이면 실제 초과수익 기준으로 재조정할 것.
# 지금은 근거 없는 차등을 두지 않고 균등(1.0)에서 출발한다.
SIG_WEIGHT = {
    "sig_spike": 1.0, "sig_x5": 1.0, "sig_x20": 1.0, "sig_high": 1.0,
    "sig_gap": 1.0, "sig_oversold": 1.0,
    "sig_gc": 1.0, "sig_reclaim": 1.0, "sig_trend": 1.0, "sig_macd": 1.0,
    "sig_value": 1.0, "sig_div": 1.0, "sig_qual": 1.0,
    "sig_growth": 1.0, "sig_accel": 1.0, "sig_garp": 1.0,
    "sig_inflow": 1.0,
}

SIG_KEYS = ["sig_spike", "sig_x5", "sig_x20", "sig_high", "sig_gap", "sig_oversold",
            "sig_gc", "sig_reclaim", "sig_trend", "sig_macd",
            "sig_value", "sig_div", "sig_qual",
            "sig_growth", "sig_accel", "sig_garp", "sig_inflow"]


def compute_signals(df):
    c = CONFIG
    d = df
    if "sig_inflow" not in d:
        d["sig_inflow"] = False
    close, low = d["close"], d["low"]
    s5, s20, s200 = d["SMA5"], d["SMA20"], d["SMA200"]
    macd, macds = d["MACD.macd"], d["MACD.signal"]
    per, pbr = d["price_earnings_ttm"], d["price_book_fq"]
    roe, divy = d["return_on_equity"], d["dividends_yield_current"]
    assets, liab = d["total_assets"], d["total_liabilities_fy"]

    d["eqr"] = ((assets - liab) / assets * 100).where(assets.notna() & liab.notna() & (assets > 0))
    d["macd_h"] = macd - macds
    # 단기
    d["sig_spike"] = d["relative_volume_10d_calc"] >= c["RVOL_SPIKE"]
    d["sig_x5"] = (low <= s5) & (s5 <= close) & (d["change"] > 0)
    d["sig_x20"] = (low <= s20) & (s20 <= close) & (d["change"] > 0)
    d["sig_high"] = close >= d["price_52_week_high"] * c["NEAR_HIGH_RATIO"]
    d["sig_gap"] = d["gap"] >= c["GAP_UP_PCT"]
    d["sig_oversold"] = (d["RSI"] <= c["RSI_REBOUND"]) & (d["change"] > 0)
    # 중장기
    valid = s200.notna() & (s200 > 0)
    d["sig_gc"] = valid & (s20 > s200) & ((s20 / s200 - 1) <= c["GC_MAX_SPREAD"])
    d["sig_reclaim"] = valid & (close > s200) & ((low <= s200) | ((close / s200 - 1) <= c["RECLAIM_MAX"]))
    d["sig_trend"] = valid & (close > s5) & (s5 > s20) & (s20 > s200) & ((close / s200 - 1) <= c["TREND_MAX_EXT"])
    d["sig_macd"] = (macd > macds) & (d["macd_h"] <= c["MACD_GC_MAX"] * close) & (close > 0)
    # 가치·펀더
    d["sig_value"] = (per > 0) & (per <= c["VAL_PER_MAX"]) & (pbr > 0) & (pbr <= c["VAL_PBR_MAX"])
    d["sig_div"] = divy >= c["DIV_MIN"]
    d["sig_qual"] = (roe >= c["QUAL_ROE"]) & (d["eqr"] >= c["QUAL_EQR"])
    # 성장
    rev_q = d["total_revenue_yoy_growth_fq"]
    eps_q = d["earnings_per_share_diluted_yoy_growth_fq"]
    cagr = d["total_revenue_cagr_5y"]
    opm = d["operating_margin_ttm"]
    psr = d["price_sales_ratio"]
    d["sig_growth"] = (rev_q >= c["GROW_YOY"]) & (cagr >= c["GROW_CAGR"])
    d["sig_accel"] = (eps_q >= c["ACCEL_YOY"]) & (rev_q > 0) & (eps_q >= rev_q * c["ACCEL_GAP"])
    d["sig_garp"] = ((psr > 0) & (psr <= c["GARP_PSR"]) & (rev_q >= c["GARP_YOY"])
                     & (opm >= c["GARP_OPM"]))
    d["ext200"] = ((close / s200 - 1) * 100).where(valid)
    # 52주 밴드 내 위치: 저가=0%, 고가=100%
    hi, lo = d["price_52_week_high"], d["price_52_week_low"]
    rng = hi - lo
    d["pos52"] = ((close - lo) / rng * 100).where(rng > 0)
    return d


def build_rows(df, mc):
    df = df.copy()
    df["score"] = 0.0
    for k, w in SIG_WEIGHT.items():
        if k in df:
            df["score"] = df["score"] + df[k].fillna(False).astype(int) * w
    d = df.rename(columns={"Value.Traded": "val", "Perf.W": "pw", "Perf.1M": "p1", "Perf.3M": "p3"})
    sig = pd.Series(0, index=d.index)
    for i, k in enumerate(SIG_KEYS):
        sig = sig | (d[k].fillna(False).astype(int) * (1 << i))
    out = pd.DataFrame({
        "c0": d["code"], "c1": d["disp_name"], "c2": d["sector_final"], "c3": d["segment_final"],
        "c4": d["close"].round(4), "c5": d["change"].round(2),
        "c6": d["SMA5"].round(2), "c7": d["SMA20"].round(2), "c8": d["SMA200"].round(2),
        "c9": d["ext200"].round(2), "c10": d["volume"],
        "c11": d["relative_volume_10d_calc"].round(2), "c12": (d["val"] / mc["turn_div"]).round(2),
        "c13": d["RSI"].round(1), "c14": d["pw"].round(2), "c15": d["p1"].round(2),
        "c16": d["p3"].round(2), "c17": d["gap"].round(2), "c18": sig, "c19": d["ticker"],
        "c20": (d["market_cap_basic"] / mc["mcap_div"]).round(1),
        "c21": d["price_earnings_ttm"].round(1), "c22": d["price_book_fq"].round(2),
        "c23": d["earnings_per_share_basic_ttm"].round(2), "c24": d["return_on_equity"].round(2),
        "c25": d["dividends_yield_current"].round(2), "c26": d["eqr"].round(2),
        "c27": (d["ebitda"] / mc["ebitda_div"]).round(1), "c28": d["macd_h"].round(2),
        "c29": d["biz"].fillna(""),
        "c30": d["total_revenue_yoy_growth_fq"].round(1),
        "c31": d["total_revenue_yoy_growth_fy"].round(1),
        "c32": d["total_revenue_yoy_growth_ttm"].round(1),
        "c33": d["total_revenue_qoq_growth_fq"].round(1),
        "c34": d["total_revenue_cagr_5y"].round(1),
        "c35": d["earnings_per_share_diluted_yoy_growth_fq"].round(1),
        "c36": d["operating_margin_ttm"].round(1),
        "c37": d["return_on_invested_capital"].round(1),
        "c38": d["price_sales_ratio"].round(2),
        "c39": d["debt_to_equity"].round(2),
        "c40": d["price_earnings_growth_ttm"].round(2),
        "c41": d["Perf.YTD"].round(1),
        "c42": d["price_52_week_high"].round(2),
        "c43": d["price_52_week_low"].round(2),
        "c44": d["pos52"].round(0),
        "c45": d["Perf.Y"].round(1),
        "c46": d["inflow"].round(2) if "inflow" in d else None,
        "c47": d["score"].round(1),
    })
    out = out.astype(object).where(pd.notna(out), None)
    rows = out.values.tolist()
    for row in rows:
        if row[10] is not None:
            row[10] = int(row[10])
        row[18] = int(row[18])
    return rows


def nav_html(active, lang):
    """언어 유지한 채 시장 이동."""
    return "".join(
        f'<a href="../{k}/index.html" class="{"on" if k == active else ""}">'
        f'{i18n.MARKET_I18N[k][lang]["nav"]}</a>' for k in MARKETS)


def lang_nav(mkey, lang):
    other = "ja" if lang == "ko" else "ko"
    # ko는 /<mkey>/, ja는 /ja/<mkey>/
    href = f"../../{mkey}/index.html" if lang == "ja" else f"../ja/{mkey}/index.html"
    return f'<a href="{href}">{i18n.UI[other]["lang_name"]}</a>'


def biz_text(row_sector, row_industry, krx_products, lang):
    """사업내용: 섹터 · 세부업종 (+ 한국은 KRX 주요제품)."""
    idx = 0 if lang == "ko" else 1
    parts = []
    for raw, table in ((row_sector, i18n.SECTOR), (row_industry, i18n.INDUSTRY)):
        if isinstance(raw, str) and raw.strip():
            parts.append(table.get(raw, (raw, raw))[idx])
    base = " · ".join(parts)
    if isinstance(krx_products, str) and krx_products.strip():
        kp = krx_products.strip()
        kp = kp[:120] + "…" if len(kp) > 120 else kp
        return f"{base} — {kp}" if base else kp
    return base


def build_market(mkey, template, out_dir, generated, indices=None):
    """시장 데이터를 1회 수집해 ko/ja 두 페이지를 생성."""
    mc = MARKETS[mkey]
    df = fetch_tv(mkey)
    master = master_jp() if mkey == "jp" else master_kr() if mkey == "kr" else None

    df["code"] = df["name"].astype(str)
    if master is not None:
        df = df.merge(master, on="code", how="left")
        df["disp_name"] = df["m_name"].fillna(df["description"])
        df["segment_final"] = df["m_segment"].fillna("기타")
        df["krx_products"] = df["m_biz"]
    else:
        df["disp_name"] = df["description"]
        df["segment_final"] = "—"
        df["krx_products"] = None
    if mkey == "us":
        df["segment_final"] = df["exchange"]

    src = "TradingView"
    if mkey == "kr":
        df, src = apply_realtime_kr(df)

    inflow, in_streak, in_days = compute_inflow(mkey)
    df["inflow"] = df["code"].map(inflow)
    df["sig_inflow"] = df["code"].map(in_streak).fillna(False).astype(bool)

    df = compute_signals(df)

    dis = fetch_tdnet(df["code"].tolist()) if mkey == "jp" else None
    profiles = load_profiles(mkey)
    if profiles is not None:
        page_dir_common = out_dir / mkey
        page_dir_common.mkdir(parents=True, exist_ok=True)
        (page_dir_common / "profiles.json").write_text(
            json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
        filled = sum(1 for v in profiles.values() if v.get("d"))
        print(f"  [{mkey}] 프로필 캐시 배포: {len(profiles)}건 (서술 {filled})")

    if mkey in CONFIG["HISTORY_MARKETS"]:
        hist = BASE / "history" / mkey
        hist.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(JST).strftime("%Y-%m-%d")
        df.to_csv(hist / f"{stamp}.csv.gz", index=False, encoding="utf-8")
        print(f"  [{mkey}] 스냅샷 저장: history/{mkey}/{stamp}.csv.gz")

    for lang in ("ko", "ja"):
        d = df.copy()
        L = i18n.UI[lang]
        ML = i18n.MARKET_I18N[mkey][lang]
        idx = 0 if lang == "ko" else 1

        # 업종 컬럼: 일본은 JPX 33업종(일본어) 유지, 한국어판은 그대로 두되 그 외는 번역
        if mkey == "jp" and "m_sector" in d:
            # JPX 33업종이 없는 종목은 TV 섹터의 '일본어' 명칭으로, 그것도 없으면 その他
            jp_fallback = d["sector"].map(
                lambda v: i18n.SECTOR.get(v, (None, None))[1] if pd.notna(v) else None)
            d["sector_final"] = d["m_sector"].fillna(jp_fallback).fillna("その他")
        else:
            d["sector_final"] = d["sector"].map(
                lambda v: i18n.SECTOR.get(v, (v, v))[idx] if pd.notna(v) and str(v).strip() else None)
            d["sector_final"] = d["sector_final"].fillna("기타" if lang == "ko" else "その他")

        misc = "その他" if (lang == "ja" or mkey == "jp") else "기타"
        vc = d["sector_final"].value_counts()
        rare = set(vc[vc < 3].index)
        if rare:
            d["sector_final"] = d["sector_final"].map(lambda v: misc if v in rare else v)

        if lang == "ja":
            d["segment_final"] = d["segment_final"].map(lambda v: i18n.SEG_JA.get(v, v))
            # 한국 종목명은 한글이라 일본어 독자가 읽을 수 없음 → 영문명으로 대체
            if mkey == "kr":
                d["disp_name"] = d["description"].fillna(d["disp_name"])

        kps = d["krx_products"] if lang == "ko" else [None] * len(d)
        d["biz"] = [biz_text(sec, ind, kp, lang) for sec, ind, kp
                    in zip(d["sector"], d["industry"], kps)]

        rows = build_rows(d, mc)
        cfg = dict(market=mkey, lang=lang, t=L,
                   turnLabel=ML["turn"], mcapLabel=ML["mcap"], ebitdaLabel=ML["ebitda"],
                   minOptions=i18n.min_options(mkey, lang), defaultMin=mc["default_min"],
                   segments=ML["segs"], allLabel=i18n.ALL_LABEL[lang],
                   usPrice=mc["us_price"])
        dis_payload = "null"
        if dis is not None:
            dis_payload = json.dumps({**dis, "kws": L["kw_labels"]},
                                     ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        prof_url = ""
        if profiles is not None:
            prof_url = "profiles.json" if lang == "ko" else f"../../{mkey}/profiles.json"
        # 대시보드는 별도 사이트(github.io/dashboard). 일본어판은 index_ja.html로 연결
        dash_url = ("https://ocw-1027.github.io/dashboard/"
                    if lang == "ko" else "https://ocw-1027.github.io/dashboard/index_ja.html")
        study_url = ("https://ocw-1027.github.io/investment-study/"
                     if lang == "ko" else "https://ocw-1027.github.io/investment-study/jp.html")
        extra_nav = (f'<a href="{study_url}" target="_blank" rel="noopener" '
                     f'class="study">{L["nav_study"]}</a>'
                     f'<a href="{dash_url}" target="_blank" rel="noopener" '
                     f'class="dash">{L["nav_dash"]}</a>'
                     + i18n.btc_link(lang) +
                     f'<a href="../ranking/index.html">{L["nav_rank"]}</a>'
                     f'<a href="../backtest/index.html">{L["nav_bt"]}</a>'
                     f'<a href="../brief/index.html">{"📋 브리프" if lang == "ko" else "📋 ブリーフ"}</a>')
        html = template
        for k, v in {
            "__HTML_LANG__": lang, "__PAGE_TITLE__": mc["page_title"],
            "__TITLE_HTML__": ML["title"], "__MARKET_LABEL__": ML["label"],
            "__GENERATED__": generated, "__COUNT__": f"{len(rows):,}",
            "__NAV__": nav_html(mkey, lang), "__LANGNAV__": lang_nav(mkey, lang),
            "__META_PRE__": L["meta_pre"], "__META_STOCKS__": L["meta_stocks"],
            "__META_UP__": L["meta_up"], "__META_DN__": L["meta_dn"],
            "__TAB_SHORT__": L["tab_short"], "__TAB_LONG__": L["tab_long"],
            "__TAB_FUND__": L["tab_fund"], "__TAB_ALL__": L["tab_all"],
            "__STRIP_LABEL__": L["strip_label"], "__SEARCH_PH__": L["search_ph"],
            "__PRESET_TECH__": L["preset_tech"], "__PRESET_FIN__": L["preset_fin"],
            "__PRESET_ALL__": L["preset_all"], "__HINT__": L["hint"],
            "__PRESET_GROWTH__": L["preset_growth"], "__TAB_GROWTH__": L["tab_growth"],
            "__PREV__": L["prev"], "__NEXT__": L["next"],
            "__WL_ALL__": L["wl_all"], "__WL_CLEAR__": L["wl_clear"],
            "__WL_DL__": L["wl_dl"], "__WL_HINT__": L["wl_hint"],
            "__TAB_DIS__": L["tab_dis"], "__DIS_NONE__": L["dis_none"],
            "__DIS_ALL__": L["dis_all"], "__EXTRA_NAV__": extra_nav,
            "__FOOT_TOGGLE__": L["foot_toggle"],
            "__FOOTER__": L["foot"].format(credit=(" / Naver(실시간)" if src == "Naver" else "") + mc["data_credit"]),
        }.items():
            html = html.replace(k, v)
        idx_l = 0 if lang == "ko" else 1
        cfg["help"] = {k: v[idx_l] for k, v in i18n.HELP.items()}
        cfg["helpSig"] = {k: v[idx_l] for k, v in i18n.HELP_SIG.items()}
        cfg["profilesUrl"] = prof_url
        cfg["bizLoading"] = L["biz_loading"]
        cfg["bizNone"] = L["biz_none"]
        idx_payload = json.dumps(
            [[(x[0] if lang == "ko" else x[1]), x[2], x[3], x[4], x[5]] for x in (indices or [])],
            ensure_ascii=False)
        html = html.replace("__INDICES__", idx_payload)
        html = html.replace("__BTC_CSS__", i18n.BTC_CSS).replace("__BTC_JS__", i18n.BTC_JS)
        html = html.replace("__DIS__", dis_payload)
        html = html.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
        html = html.replace("__DATA__", json.dumps(rows, ensure_ascii=False, separators=(",", ":")))

        page = (out_dir / mkey) if lang == "ko" else (out_dir / "ja" / mkey)
        page.mkdir(parents=True, exist_ok=True)
        (page / "index.html").write_text(html, encoding="utf-8")

    dm = mc["default_min"]
    rows = build_rows(df.assign(sector_final=df["sector"], biz=""), mc)
    n_s = sum(1 for r in rows if r[18] & 0b0000000000111111 and (r[12] or 0) >= dm)
    n_l = sum(1 for r in rows if r[18] & 0b0000001111000000 and (r[12] or 0) >= dm)
    n_f = sum(1 for r in rows if r[18] & 0b0001110000000000 and (r[12] or 0) >= dm)
    n_g = sum(1 for r in rows if r[18] & 0b1110000000000000 and (r[12] or 0) >= dm)
    print(f"  [{mkey}] 완료 — {len(rows)}종목 / 단기 {n_s} / 중장기 {n_l} / "
          f"펀더 {n_f} / 성장 {n_g} (ko+ja)")


HUB = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=jp/index.html"><title>Stock Screener</title></head>
<body style="background:#0f141c;color:#e9eef6;font-family:sans-serif;padding:40px">
<p>이동 중... / 移動中...</p>
<p>한국어: <a href="jp/index.html" style="color:#ffb224">일본</a> ·
<a href="kr/index.html" style="color:#ffb224">한국</a> ·
<a href="us/index.html" style="color:#ffb224">미국</a></p>
<p>日本語: <a href="ja/jp/index.html" style="color:#ffb224">日本</a> ·
<a href="ja/kr/index.html" style="color:#ffb224">韓国</a> ·
<a href="ja/us/index.html" style="color:#ffb224">米国</a></p></body></html>"""


def main():
    print("=" * 60)
    print("Multi-Market Screener v3 실행 (ko/ja)", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    template = (BASE / "template.html").read_text(encoding="utf-8")
    out_dir = Path(CONFIG["OUTPUT_DIR"])
    if not out_dir.is_absolute():
        out_dir = BASE / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(JST).strftime("%Y-%m-%d (%a) %H:%M JST")

    indices = fetch_indices()

    for mkey in MARKETS:
        try:
            build_market(mkey, template, out_dir, generated, indices=indices)
        except Exception as e:  # noqa: BLE001
            print(f"  [{mkey}] 페이지 생성 실패: {e}")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise

    (out_dir / "index.html").write_text(HUB, encoding="utf-8")
    print(f"\n완료 → {out_dir}")
    if CONFIG["OPEN_BROWSER"]:
        try:
            webbrowser.open((out_dir / "jp" / "index.html").as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    main()
