# -*- coding: utf-8 -*-
"""
brief.py — 운용 데스크 브리프
==============================
종가 스냅샷(history/{시장}/날짜.csv.gz)에서 오늘 볼 종목을 규칙으로 고르고,
종목별 근거 데이터(수치·시그널·기저율·TDnet 공시·사업 소개)를 한 묶음으로 만든다.

  python brief.py         → briefs/{시장}/날짜.json + briefs/picks.jsonl (+텔레그램)   [brief.yml]
  python brief.py page    → briefs/ 의 시장별 최신 JSON → site/brief/index.html, site/ja/brief/index.html (시장 탭)   [daily.yml]

LLM_MODE=off (기본) 는 모델 호출이 없어 비용 0. 페이지의 "분석 요청 복사" 로 필요한 종목만
Claude 채팅에 붙여 넣어 100점 평가를 받는다. 나중에 자동화하려면 LLM_MODE=api 로 바꾸면 된다.

환경변수: MARKET(jp|kr|us) · BRIEF_DATE(YYYY-MM-DD, 비우면 최신 스냅샷) · MAX_PICKS(20) · MIN_VAL / MIN_MCAP / MIN_PRICE (억엔·억원·$M 단위, 비우면 시장별 기본값)
          N_SHORT(8) · N_LONG(8) · N_NEWS(4) · MAX_PER_INDUSTRY(3) · COOLDOWN_DAYS(3)
          LLM_MODE(off|api) · ANTHROPIC_API_KEY · LLM_MODEL · LLM_MAX_SEARCH(3)
          TELEGRAM_TOKEN · TELEGRAM_CHAT_ID · BRIEF_URL · OUTPUT_DIR(site)
"""
import glob
import gzip
import html
import json
import os
import re
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
BRIEFS = BASE / "briefs"

CFG = {
    "MARKET": os.environ.get("MARKET", "jp"),
    "BRIEF_DATE": os.environ.get("BRIEF_DATE", "").strip(),
    "MAX_PICKS": int(os.environ.get("MAX_PICKS", "20")),
    "MIN_VAL": os.environ.get("MIN_VAL", "").strip(),         # 거래대금 하한 (억엔·억원·$M). 비우면 시장별 기본값
    "N_SHORT": int(os.environ.get("N_SHORT", "8")),
    "N_LONG": int(os.environ.get("N_LONG", "8")),
    "N_NEWS": int(os.environ.get("N_NEWS", "4")),
    "MAX_PER_INDUSTRY": int(os.environ.get("MAX_PER_INDUSTRY", "3")),
    "COOLDOWN_DAYS": int(os.environ.get("COOLDOWN_DAYS", "3")),
    "LLM_MODE": os.environ.get("LLM_MODE", "off").lower(),
    "LLM_MODEL": os.environ.get("LLM_MODEL", "claude-sonnet-5"),
    "LLM_MAX_SEARCH": int(os.environ.get("LLM_MAX_SEARCH", "3")),
    "BRIEF_URL": os.environ.get("BRIEF_URL", "https://stock-screener-ev3.pages.dev/brief/"),
    "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "site"),
}

MARKETS = {
    "jp": dict(div=1e8, unit_ko="억엔", unit_ja="億円", ccy="엔", ccy_ja="円", label_ko="🇯🇵 일본", label_ja="🇯🇵 日本"),
    "kr": dict(div=1e8, unit_ko="억원", unit_ja="億ウォン", ccy="원", ccy_ja="ウォン", label_ko="🇰🇷 한국", label_ja="🇰🇷 韓国"),
    "us": dict(div=1e6, unit_ko="$M", unit_ja="$M", ccy="$", ccy_ja="$", label_ko="🇺🇸 미국", label_ja="🇺🇸 米国"),
}

MIN_VAL_DEFAULT = {"jp": 3.0, "kr": 10.0, "us": 10.0}          # 거래대금 하한: 억엔 · 억원 · $M
MIN_MCAP_DEFAULT = {"jp": 100.0, "kr": 1000.0, "us": 500.0}    # 시총 하한:    억엔 · 억원 · $M
MIN_PRICE_DEFAULT = {"jp": 0.0, "kr": 0.0, "us": 5.0}          # 주가 하한 (미국 페니주 제외)


def _floor(env, table, m):
    v = os.environ.get(env, "").strip()
    return float(v) if v else table[m]


def min_val(m):
    return _floor("MIN_VAL", MIN_VAL_DEFAULT, m)


def min_mcap(m):
    return _floor("MIN_MCAP", MIN_MCAP_DEFAULT, m)


def min_price(m):
    return _floor("MIN_PRICE", MIN_PRICE_DEFAULT, m)


SIG_SHORT = ["sig_spike", "sig_x5", "sig_x20", "sig_high", "sig_gap", "sig_oversold"]
SIG_TREND = ["sig_gc", "sig_reclaim", "sig_trend", "sig_macd"]
SIG_FUND = ["sig_value", "sig_div", "sig_qual"]
SIG_GROWTH = ["sig_growth", "sig_accel", "sig_garp"]
SIG_ALL = SIG_SHORT + SIG_TREND + SIG_FUND + SIG_GROWTH + ["sig_inflow"]

# ── screener.py 와 같은 값을 쓰되, import 가 안 되는 환경(로컬 테스트)에서도 돌도록 폴백 ──
try:
    from screener import KW_PATTERNS, KW_STRONG  # noqa: F401
except Exception:
    KW_PATTERNS = [r"上方修正", r"下方修正", r"増配|復配", r"減配|無配", r"自己株式|自社株",
                   r"株式分割", r"決算短信|決算説明", r"業績予想", r"配当予想",
                   r"業務提携|資本提携", r"公開買付|TOB", r"月次"]
    KW_STRONG = (1 << 0) | (1 << 2) | (1 << 4) | (1 << 5) | (1 << 10)
try:
    import i18n
    SIG_NAME = i18n.SIGNAL_I18N
    KW_LABELS = {"ko": i18n.UI["ko"]["kw_labels"], "ja": i18n.UI["ja"]["kw_labels"]}
    INDUSTRY = getattr(i18n, "INDUSTRY", {})
except Exception:
    SIG_NAME = {k: (k, k) for k in SIG_ALL}
    KW_LABELS = {"ko": [p.split("|")[0] for p in KW_PATTERNS], "ja": [p.split("|")[0] for p in KW_PATTERNS]}
    INDUSTRY = {}


def sig_label(k, lang="ko"):
    v = SIG_NAME.get(k)
    return (v[0] if lang == "ko" else v[1]) if v else k


def ind_label(name, lang="ko"):
    v = INDUSTRY.get(name)
    return (v[0] if lang == "ko" else v[1]) if v else (name or "")


# ───────────────────────── 데이터 로드 ─────────────────────────
def snapshot_path(m, date=""):
    files = sorted(glob.glob(str(BASE / "history" / m / "*.csv.gz")))
    if date:
        p = BASE / "history" / m / f"{date}.csv.gz"
        return p if p.exists() else None
    return Path(files[-1]) if files else None


def load_snapshot(p):
    df = pd.read_csv(p, compression="gzip", dtype={"code": str, "name": str})
    df = df.dropna(subset=["code", "close"]).drop_duplicates(subset="code")
    for k in SIG_ALL:
        df[k] = df[k].fillna(False).astype(bool) if k in df else False
    df["score"] = df[SIG_ALL].sum(axis=1).astype(float)
    return df


def load_profiles(m):
    p = BASE / "profiles" / f"{m}.json.gz"
    if not p.exists():
        return {}
    try:
        return json.loads(gzip.decompress(p.read_bytes()).decode("utf-8"))
    except Exception:
        return {}


def load_baserates(m):
    """backtest.py 의 시그널별 승률·초과수익을 그대로 가져온다 (실패하면 빈 dict)."""
    try:
        import backtest
        res = backtest.analyze(m)
        return res.get("signals", {}), res.get("n_days", 0)
    except Exception as e:  # noqa: BLE001
        print(f"  기저율 생략: {type(e).__name__}: {str(e)[:80]}")
        return {}, 0


def read_picks():
    p = BRIEFS / "picks.jsonl"
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def recent_picks(days, today):
    """picks.jsonl 에서 오늘 이전 최근 N 브리프 날짜 안에 이미 뽑힌 코드 (재분석 쿨다운)."""
    if days <= 0:
        return set()
    rows = [r for r in read_picks() if r.get("market") == CFG["MARKET"] and r["date"] < today]
    dates = sorted({r["date"] for r in rows})[-days:]
    return {r["code"] for r in rows if r["date"] in dates}


# ───────────────────────── TDnet 공시 (일본) ─────────────────────────
def tdnet_day(yyyymmdd, retries=3):
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
        raise RuntimeError(f"TDnet {yyyymmdd}: {last}")
    out = []
    for it in (r.json() or {}).get("items", []):
        td = it.get("Tdnet") if isinstance(it, dict) and isinstance(it.get("Tdnet"), dict) else it
        if not isinstance(td, dict):
            continue
        code = str(td.get("company_code") or "")[:4]
        title = str(td.get("title") or "").strip()
        if not code or not title:
            continue
        bits = 0
        for i, pat in enumerate(KW_PATTERNS):
            if re.search(pat, title):
                bits |= 1 << i
        pub = str(td.get("pubdate") or "")
        out.append(dict(code=code, pub=pub[:16], title=title, url=str(td.get("document_url") or ""),
                        bits=bits, strong=bool(bits & KW_STRONG)))
    return out


def fetch_tdnet(codes, days=5):
    now, ds, d = datetime.now(JST), [], datetime.now(JST)
    while len(ds) < days:
        if d.weekday() < 5:
            ds.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    items = []
    for day in ds:
        try:
            items += tdnet_day(day)
        except Exception as e:  # noqa: BLE001
            print(f"  TDnet {day} 실패: {str(e)[:60]}")
    uni = set(codes)
    by = {}
    for it in sorted((x for x in items if x["code"] in uni), key=lambda x: x["pub"], reverse=True):
        by.setdefault(it["code"], []).append(it)
    print(f"  TDnet: {len(ds)}영업일 {sum(len(v) for v in by.values())}건 / {len(by)}종목")
    return by


# ───────────────────────── 후보 선정 (결정론) ─────────────────────────
NEWS_PRIORITY = {10: 5, 0: 4, 2: 3, 5: 2, 4: 1}   # TOB > 상방수정 > 증배 > 분할 > 자사주 (KW_PATTERNS 비트)
NEWS_NOISE = re.compile(r"処分|譲渡制限|報酬|消却")  # 자사주 '처분·보수·소각' 공시는 매수 공시가 아니므로 제외


def news_priority(x):
    if (x["bits"] >> 4) & 1 and not (x["bits"] & ~(1 << 4) & KW_STRONG) and NEWS_NOISE.search(x["title"]):
        return 0
    return max((v for b, v in NEWS_PRIORITY.items() if (x["bits"] >> b) & 1), default=0)


def select_candidates(df, tdnet, cooldown, mkey):
    c, m = CFG, MARKETS[mkey]
    d = df.copy()
    if "type" in d:
        d = d[d["type"].astype(str).str.lower() == "stock"]
    if "subtype" in d:
        d = d[~d["subtype"].astype(str).str.lower().str.contains("etf|reit|fund|trust|preferred", na=False)]
    ok = (d["Value.Traded"].fillna(0) >= min_val(mkey) * m["div"]) & (d["close"].fillna(0) >= min_price(mkey))
    if "market_cap_basic" in d:
        ok &= d["market_cap_basic"].fillna(0) >= min_mcap(mkey) * m["div"]
    liquid = d[ok].copy()
    liquid["inflow_s"] = liquid["inflow"].fillna(0) if "inflow" in liquid else 0
    liquid["rvol_s"] = liquid["relative_volume_10d_calc"].fillna(0)
    liquid["n_short"] = liquid[SIG_SHORT].sum(axis=1)          # 오늘 켜진 단기 트리거 수
    liquid["n_long"] = liquid[SIG_TREND + SIG_FUND + SIG_GROWTH].sum(axis=1)
    news_rank = {}
    if tdnet:
        cut = (datetime.now(JST) - timedelta(days=4)).strftime("%Y-%m-%d")
        for k, v in tdnet.items():
            for x in v:
                if x["pub"] >= cut and x["strong"]:
                    news_rank[k] = max(news_rank.get(k, 0), news_priority(x))
    liquid["news_rank"] = liquid["code"].map(news_rank).fillna(0)

    def top(mask, n, keys):
        return liquid[mask].sort_values(keys, ascending=[False] * len(keys)).head(n * 3)

    pools = [
        ("short", top((liquid["n_short"] >= 1) & (liquid["score"] >= 2), c["N_SHORT"],
                      ["n_short", "score", "rvol_s", "inflow_s"])),
        ("long", top((liquid["n_long"] >= 1) & (liquid["score"] >= 3), c["N_LONG"],
                     ["n_long", "score", "inflow_s", "Value.Traded"])),
        ("news", top((liquid["news_rank"] > 0) & (liquid["score"] >= 1), c["N_NEWS"],
                     ["news_rank", "score", "Value.Traded"])),
    ]
    picked, seen, per_ind, quota = [], set(), {}, {"short": c["N_SHORT"], "long": c["N_LONG"], "news": c["N_NEWS"]}
    for bucket, pool in pools:
        for _, r in pool.iterrows():
            if quota[bucket] <= 0 or len(picked) >= c["MAX_PICKS"]:
                break
            code = r["code"]
            if code in seen or (code in cooldown and bucket != "news"):
                continue
            ind = str(r.get("industry") or "")
            if per_ind.get(ind, 0) >= c["MAX_PER_INDUSTRY"]:
                continue
            seen.add(code)
            per_ind[ind] = per_ind.get(ind, 0) + 1
            quota[bucket] -= 1
            picked.append((bucket, r))
    stats = dict(total=int(len(df)), liquid=int(len(liquid)), candidates=len(picked),
                 short=sum(1 for b, _ in picked if b == "short"),
                 long=sum(1 for b, _ in picked if b == "long"),
                 news=sum(1 for b, _ in picked if b == "news"))
    return picked, stats


def _f(v, nd=2):
    try:
        if v is None or pd.isna(v):
            return None
        return round(float(v), nd)
    except Exception:
        return None


def pick_record(bucket, r, profiles, baserates, tdnet, mkey):
    m = MARKETS[mkey]
    code = r["code"]
    sigs = [k for k in SIG_ALL if bool(r.get(k, False))]
    base = {}
    for k in sigs:
        st = baserates.get(k) or {}
        base[k] = {h: st[h] for h in ("5", "20", "1") if isinstance(st.get(h), dict)}
    prof = profiles.get(code) or {}
    krx = str(r.get("krx_products") or "").strip() if mkey == "kr" else ""
    biz = (prof.get("l") or "").strip() or (krx if krx and krx != "nan" else "") or (prof.get("d") or "").strip()[:220]
    s200 = _f(r.get("SMA200"))
    close = _f(r.get("close"), 4)
    return dict(
        code=code, name=str(r.get("disp_name") or r.get("description") or code), ticker=str(r.get("ticker") or ""),
        bucket=bucket, score=_f(r.get("score"), 1), signals=sigs, baserate=base,
        sector=str(r.get("sector") or ""), industry=str(r.get("industry") or ""),
        segment=str(r.get("segment_final") or ""),
        close=close, chg=_f(r.get("change")), gap=_f(r.get("gap")),
        sma5=_f(r.get("SMA5")), sma20=_f(r.get("SMA20")), sma200=s200,
        ext200=_f(r.get("ext200")) if "ext200" in r else (_f((close / s200 - 1) * 100) if close and s200 else None),
        rsi=_f(r.get("RSI"), 1), macd_h=_f(r.get("macd_h")), rvol=_f(r.get("relative_volume_10d_calc")),
        pw=_f(r.get("Perf.W")), p1=_f(r.get("Perf.1M")), p3=_f(r.get("Perf.3M")), ytd=_f(r.get("Perf.YTD"), 1),
        pos52=_f(r.get("pos52"), 0), hi52=_f(r.get("price_52_week_high")), lo52=_f(r.get("price_52_week_low")),
        val=_f((r.get("Value.Traded") or 0) / m["div"], 1), mcap=_f((r.get("market_cap_basic") or 0) / m["div"], 0),
        per=_f(r.get("price_earnings_ttm"), 1), pbr=_f(r.get("price_book_fq")), eps=_f(r.get("earnings_per_share_basic_ttm")),
        roe=_f(r.get("return_on_equity"), 1), eqr=_f(r.get("eqr"), 1), div=_f(r.get("dividends_yield_current")),
        rev_q=_f(r.get("total_revenue_yoy_growth_fq"), 1), rev_ttm=_f(r.get("total_revenue_yoy_growth_ttm"), 1),
        cagr5=_f(r.get("total_revenue_cagr_5y"), 1), eps_q=_f(r.get("earnings_per_share_diluted_yoy_growth_fq"), 1),
        opm=_f(r.get("operating_margin_ttm"), 1), roic=_f(r.get("return_on_invested_capital"), 1),
        psr=_f(r.get("price_sales_ratio")), peg=_f(r.get("price_earnings_growth_ttm")), de=_f(r.get("debt_to_equity")),
        inflow=_f(r.get("inflow")), biz=biz,
        tdnet=[dict(pub=x["pub"], title=x["title"], url=x["url"], bits=x["bits"], strong=x["strong"])
               for x in (tdnet.get(code) or [])[:6]],
        llm=None,
    )


# ───────────────────────── 분석 요청 프롬프트 (채팅에 붙여 넣는 용도) ─────────────────────────
def _n(v, suf="", nd=None):
    if v is None:
        return "—"
    if nd is not None:
        return f"{v:,.{nd}f}{suf}"
    return f"{v:,.2f}".rstrip("0").rstrip(".") + suf


def _s(v, suf="%"):
    return "—" if v is None else f"{v:+,.2f}".rstrip("0").rstrip(".") + suf


def price(v, mkey, lang="ko"):
    if v is None:
        return "—"
    m = MARKETS[mkey]
    return f"${v:,.2f}" if mkey == "us" else f"{v:,.0f}" + (m["ccy"] if lang == "ko" else m["ccy_ja"])


def amt(v, mkey, lang="ko"):
    if v is None:
        return "—"
    m = MARKETS[mkey]
    return f"${v:,.1f}M" if mkey == "us" else f"{_n(v)}{m['unit_ko'] if lang == 'ko' else m['unit_ja']}"


def stock_block(p, date, lang="ko", mkey="jp"):
    m = MARKETS[mkey]
    unit = m["unit_ko"] if lang == "ko" else m["unit_ja"]
    sigs = ", ".join(sig_label(k, lang) for k in p["signals"]) or "—"
    br = []
    for k, hs in p["baserate"].items():
        h = "5" if "5" in hs else ("20" if "20" in hs else ("1" if "1" in hs else None))
        if h:
            st = hs[h]
            br.append(f"{sig_label(k, lang)} {h}일 승률 {st['win']}% 시장대비 {st['excess']:+}%p (n={st['n']})"
                      if lang == "ko" else
                      f"{sig_label(k, lang)} {h}日 勝率{st['win']}% 市場比{st['excess']:+}%p (n={st['n']})")
    dis = "; ".join(f"{x['pub'][5:]} {x['title'][:40]}" for x in p["tdnet"][:4]) or ("없음" if lang == "ko" else "なし")
    ind = ind_label(p["industry"], lang)
    if lang == "ko":
        return (f"■ {p['code']} {p['name']} ({p['ticker']}) | 업종 {ind} / {p['segment']} | 분류 {BUCKET_KO[p['bucket']]}\n"
                f"주가 {price(p['close'], mkey)} ({_s(p['chg'])}) | 5MA {_n(p['sma5'])} / 20MA {_n(p['sma20'])} / 200MA {_n(p['sma200'])} "
                f"(200MA 대비 {_s(p['ext200'])}) | RSI {_n(p['rsi'])} | MACD-H {_n(p['macd_h'])} | RVOL {_n(p['rvol'])} | 52주 위치 {_n(p['pos52'], '%')}\n"
                f"1주 {_s(p['pw'])} / 1개월 {_s(p['p1'])} / 3개월 {_s(p['p3'])} / YTD {_s(p['ytd'])} | 유입배 {_n(p['inflow'])}\n"
                f"거래대금 {amt(p['val'], mkey)} | 시총 {amt(p['mcap'], mkey)} | PER {_n(p['per'])} | PBR {_n(p['pbr'])} | ROE {_n(p['roe'], '%')} | "
                f"자기자본비율 {_n(p['eqr'], '%')} | 배당 {_n(p['div'], '%')} | D/E {_n(p['de'])}\n"
                f"매출 YoY 분기 {_n(p['rev_q'], '%')} / TTM {_n(p['rev_ttm'], '%')} | EPS YoY 분기 {_n(p['eps_q'], '%')} | 5년 CAGR {_n(p['cagr5'], '%')} | "
                f"영업이익률 {_n(p['opm'], '%')} | ROIC {_n(p['roic'], '%')} | PSR {_n(p['psr'])} | PEG {_n(p['peg'])}\n"
                f"시그널({_n(p['score'])}개): {sigs}\n"
                f"기저율: {' · '.join(br) or '데이터 축적 중'}\n"
                f"공시(5영업일): {dis}\n"
                f"사업: {p['biz'] or '—'}")
    return (f"■ {p['code']} {p['name']} ({p['ticker']}) | 業種 {ind} / {p['segment']} | 分類 {BUCKET_JA[p['bucket']]}\n"
            f"株価 {price(p['close'], mkey, 'ja')} ({_s(p['chg'])}) | 5MA {_n(p['sma5'])} / 20MA {_n(p['sma20'])} / 200MA {_n(p['sma200'])} "
            f"(200MA乖離 {_s(p['ext200'])}) | RSI {_n(p['rsi'])} | MACD-H {_n(p['macd_h'])} | RVOL {_n(p['rvol'])} | 52週位置 {_n(p['pos52'], '%')}\n"
            f"1週 {_s(p['pw'])} / 1ヶ月 {_s(p['p1'])} / 3ヶ月 {_s(p['p3'])} / YTD {_s(p['ytd'])} | 流入倍率 {_n(p['inflow'])}\n"
            f"売買代金 {amt(p['val'], mkey, 'ja')} | 時価総額 {amt(p['mcap'], mkey, 'ja')} | PER {_n(p['per'])} | PBR {_n(p['pbr'])} | ROE {_n(p['roe'], '%')} | "
            f"自己資本比率 {_n(p['eqr'], '%')} | 配当 {_n(p['div'], '%')} | D/E {_n(p['de'])}\n"
            f"売上YoY 四半期 {_n(p['rev_q'], '%')} / TTM {_n(p['rev_ttm'], '%')} | EPS YoY 四半期 {_n(p['eps_q'], '%')} | 5年CAGR {_n(p['cagr5'], '%')} | "
            f"営業利益率 {_n(p['opm'], '%')} | ROIC {_n(p['roic'], '%')} | PSR {_n(p['psr'])} | PEG {_n(p['peg'])}\n"
            f"シグナル({_n(p['score'])}件): {sigs}\n"
            f"基準率: {' · '.join(br) or 'データ蓄積中'}\n"
            f"開示(5営業日): {dis}\n"
            f"事業: {p['biz'] or '—'}")


PROMPT_HEAD = {
    "ko": ("당신은 글로벌 주식 전문 애널리스트입니다. 아래는 {date} 종가 기준 스크리너 데이터입니다. "
           "숫자는 아래 값을 그대로 인용하고(새로 추정하지 말 것), 웹 검색으로 최근 2주 뉴스·IR·실적을 확인한 뒤 종목마다 평가해 주세요.\n"
           "출력 형식(종목별): 총점 X/100 · 판단(매수검토/보류/패스) · 근거 2줄 · 펀더멘털 X/100 · 테크니컬 X/100 · 리스크 X/100(높을수록 리스크 낮음) · 촉매 X/100 · "
           "강점 3 · 약점·리스크 2 · 주목 포인트 2 · 참고한 뉴스(날짜·출처). 투자 시계는 분류가 '단기'면 1~3개월, 아니면 6~12개월.\n"
           "마지막에 총점 순으로 정렬한 요약표를 붙여 주세요. 본 분석은 참고용이며 최종 판단은 본인 책임입니다.\n"),
    "ja": ("あなたはグローバル株式の専門アナリストです。以下は{date}終値時点のスクリーナーデータです。"
           "数値は下記をそのまま引用し（新たに推定しない）、ウェブ検索で直近2週間のニュース・IR・決算を確認したうえで銘柄ごとに評価してください。\n"
           "出力形式(銘柄ごと): 総合 X/100 ・ 判断(買い検討/保留/パス) ・ 根拠2行 ・ ファンダ X/100 ・ テクニカル X/100 ・ リスク X/100(高いほど低リスク) ・ カタリスト X/100 ・ "
           "強み3 ・ 弱み/リスク2 ・ 注目ポイント2 ・ 参照ニュース(日付・出典)。投資時間軸は分類が「短期」なら1〜3ヶ月、それ以外は6〜12ヶ月。\n"
           "最後に総合点順の要約表を付けてください。本分析は参考情報であり、最終判断は自己責任です。\n"),
}
BUCKET_KO = {"short": "단기", "long": "중장기", "news": "공시"}
BUCKET_JA = {"short": "短期", "long": "中長期", "news": "開示"}


# ───────────────────────── (대기) LLM 자동 평가 — LLM_MODE=api 일 때만 ─────────────────────────
WEIGHTS = {"short": dict(fund=.30, tech=.30, risk=.20, cat=.20), "long": dict(fund=.40, tech=.20, risk=.20, cat=.20)}
WEIGHTS["news"] = WEIGHTS["short"]
LLM_SYSTEM = ("You are an equity analyst. Use ONLY the numbers given for price/valuation; use web search for recent news. "
              "Reply with a single JSON object and nothing else: "
              '{"fund":0-100,"tech":0-100,"risk":0-100,"cat":0-100,"hard_stop":false,"hard_stop_reason":"",'
              '"reason":"2 lines in Korean","strengths":["","",""],"risks":["",""],"watch":["",""],'
              '"news":[{"date":"","title":"","source":"","url":""}],"confidence":"high|med|low"}')


def call_claude(user_text):
    """Anthropic Messages API 직접 호출 (SDK 불필요). 키가 없으면 None.
    주의: API 키 없이 작성된 대기 코드라 실제 응답 형식은 docs.claude.com 에서 최신 확인 후 1종목으로 먼저 테스트할 것."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": CFG["LLM_MODEL"], "max_tokens": 1500, "system": LLM_SYSTEM,
            "messages": [{"role": "user", "content": user_text}],
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": CFG["LLM_MAX_SEARCH"]}]}
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=180, json=body,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    r.raise_for_status()
    text = "\n".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1]) if s >= 0 and e > s else None


def apply_llm(p, date, mkey):
    out = call_claude(PROMPT_HEAD["ko"].format(date=date) + "\n" + stock_block(p, date, "ko", mkey))
    if not out:
        return
    sub = {k: max(0, min(100, float(out.get(k, 0) or 0))) for k in ("fund", "tech", "risk", "cat")}
    w = WEIGHTS[p["bucket"]]
    total = round(sum(sub[k] * w[k] for k in sub), 1)
    hard = bool(out.get("hard_stop"))
    verdict = "패스" if hard or total < 50 else ("보류" if total < 70 else "매수검토")
    news = [x for x in (out.get("news") or []) if isinstance(x, dict) and str(x.get("url", "")).startswith("http")][:5]
    p["llm"] = dict(total=total, verdict=verdict, hard_stop=hard, hard_stop_reason=str(out.get("hard_stop_reason") or "")[:200],
                    reason=str(out.get("reason") or "")[:400], strengths=[str(x)[:120] for x in (out.get("strengths") or [])][:3],
                    risks=[str(x)[:120] for x in (out.get("risks") or [])][:2], watch=[str(x)[:120] for x in (out.get("watch") or [])][:2],
                    news=news, confidence=str(out.get("confidence") or "med"), model=CFG["LLM_MODEL"], **sub)


# ───────────────────────── 텔레그램 ─────────────────────────
def telegram(text):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("  텔레그램 생략 (TELEGRAM_TOKEN/CHAT_ID 없음)")
        return
    for chunk in [text[i:i + 3800] for i in range(0, len(text), 3800)]:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=20,
                          json={"chat_id": chat, "text": chunk, "parse_mode": "HTML", "disable_web_page_preview": True})
        print(f"  텔레그램 {r.status_code}")


def tg_message(brief):
    esc = html.escape
    m = MARKETS[brief["market"]]
    st = brief["universe"]
    lines = [f"📋 <b>운용 데스크 브리프 {brief['date']}</b> {m['label_ko']}",
             f"스크리닝 {st['total']:,} → 유동성 통과 {st['liquid']:,} → 후보 {st['candidates']} "
             f"(단기 {st['short']} · 중장기 {st['long']} · 공시 {st['news']})", ""]
    for b in ("short", "long", "news"):
        ps = [p for p in brief["picks"] if p["bucket"] == b]
        if not ps:
            continue
        lines.append(f"<b>{BUCKET_KO[b]}</b>")
        for p in ps:
            chg = f"{p['chg']:+.1f}%" if p["chg"] is not None else "—"
            tag = ""
            if p["llm"]:
                tag = f" | {p['llm']['total']:.0f}점 {p['llm']['verdict']}"
            elif b == "news" and p["tdnet"]:
                st0 = next((x for x in p["tdnet"] if x["strong"]), p["tdnet"][0])
                tag = f" | {esc(st0['title'][:22])}"
            sigs = "·".join(sig_label(k) for k in p["signals"][:3])
            lines.append(f"• {p['code']} {esc(p['name'][:12])} {chg} | {sigs} | 스코어 {p['score']:.0f}{tag}")
        lines.append("")
    lines.append(f'🔗 <a href="{CFG["BRIEF_URL"]}#{brief["market"]}">브리프 페이지 (수치·공시·분석 요청 복사)</a>')
    return "\n".join(lines)


# ───────────────────────── 생성 ─────────────────────────
def generate():
    m = CFG["MARKET"]
    if m not in MARKETS:
        sys.exit(f"MARKET 오류: {m}")
    p = snapshot_path(m, CFG["BRIEF_DATE"])
    if p is None:
        sys.exit(f"스냅샷 없음: history/{m}/{CFG['BRIEF_DATE'] or '*'}.csv.gz")
    date = p.name.replace(".csv.gz", "")
    print(f"[{m}] 스냅샷 {p.name}")
    df = load_snapshot(p)
    tdnet = fetch_tdnet(df["code"].tolist()) if m == "jp" else {}
    cooldown = recent_picks(CFG["COOLDOWN_DAYS"], date)
    picked, stats = select_candidates(df, tdnet, cooldown, m)
    print(f"  유니버스 {stats['total']:,} → 유동성 {stats['liquid']:,} → 후보 {stats['candidates']} "
          f"(단기 {stats['short']} · 중장기 {stats['long']} · 공시 {stats['news']}) / 쿨다운 제외 {len(cooldown)}")
    profiles = load_profiles(m)
    baserates, n_days = load_baserates(m)
    picks = [pick_record(b, r, profiles, baserates, tdnet, m) for b, r in picked]

    if CFG["LLM_MODE"] == "api":
        for i, pk in enumerate(picks, 1):
            try:
                apply_llm(pk, date, m)
                print(f"  LLM {i}/{len(picks)} {pk['code']} → {pk['llm']['total'] if pk['llm'] else '-'}")
            except Exception as e:  # noqa: BLE001
                print(f"  LLM {pk['code']} 실패: {type(e).__name__}: {str(e)[:80]}")
        picks.sort(key=lambda x: -(x["llm"]["total"] if x["llm"] else -1))

    mk = MARKETS[m]
    brief = dict(date=date, market=m, generated=datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
                 label_ko=mk["label_ko"], label_ja=mk["label_ja"], unit_ko=mk["unit_ko"], unit_ja=mk["unit_ja"],
                 llm_mode=CFG["LLM_MODE"], baserate_days=n_days, universe=stats, picks=picks,
                 config=dict(MIN_VAL=min_val(m), MIN_MCAP=min_mcap(m), MIN_PRICE=min_price(m), **{k: CFG[k] for k in ("N_SHORT", "N_LONG", "N_NEWS", "MAX_PER_INDUSTRY", "COOLDOWN_DAYS")}))
    out = BRIEFS / m
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{date}.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = [r for r in read_picks() if not (r["date"] == date and r.get("market") == m)]  # 재생성 시 같은 날짜 교체
    for pk in picks:
        row = dict(date=date, market=m, code=pk["code"], name=pk["name"], bucket=pk["bucket"],
                   score=pk["score"], close=pk["close"], signals=pk["signals"])
        if pk["llm"]:
            row.update(total=pk["llm"]["total"], verdict=pk["llm"]["verdict"])
        rows.append(row)
    (BRIEFS / "picks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"  저장: briefs/{m}/{date}.json ({len(picks)}종목) + picks.jsonl")
    telegram(tg_message(brief))
    return brief


# ───────────────────────── 페이지 ─────────────────────────
PAGE_T = {
    "ko": dict(title="운용 데스크 브리프", sub="종가 스냅샷에서 규칙으로 고른 오늘의 후보와 근거 데이터",
               gen="생성", base="기저율 축적", days="일", close="종가 기준", back="← 스크리너", total="스크리닝", liquid="유동성 통과", picks="후보", rank="📈 순위 추이", bt="📊 성과분석",
               other="日本語",
               tabs=[("all", "전체"), ("short", "단기"), ("long", "중장기"), ("news", "공시")],
               col=["코드", "종목", "분류", "등락", "스코어", "시그널", "200MA", "RSI", "RVOL", "거래대금", "PER", "판단"],
               copy="분석 요청 복사", copy_all="표시 중인 종목 전체 분석 요청 복사", copied="복사됨 ✓",
               nollm="미평가", verdict_lbl="판단", base_lbl="시그널 기저율", dis_lbl="TDnet 공시 (5영업일)", biz_lbl="사업",
               empty="아직 브리프가 없습니다. 첫 실행은 평일 18:03 JST 이후 자동으로 만들어집니다.",
               howto="복사한 텍스트를 Claude 채팅에 붙여 넣으면 100점 체계(펀더·테크·리스크·촉매)로 평가받을 수 있습니다. "
                     "숫자는 스크리너 값이 그대로 들어가 있어 모델이 새로 추정하지 않습니다. 주문 실행 기능은 없습니다.",
               foot="후보 선정 규칙 — 거래대금 ≥ {minval}{unit} · 시총 ≥ {mcap}{unit}{extra}, 단기: 단기 시그널 1개 이상 + 스코어 ≥2, 중장기: 추세·가치·성장 시그널 + 스코어 ≥3, "
                    "공시: 최근 강한 공시(상방·증배·자사주·분할·TOB) + 시그널 1개 이상 · 같은 업종 최대 {maxind}종목 · 최근 {cool}회 브리프에 나온 종목은 제외(공시 예외) · "
                    "참고 자료이며 투자 판단의 책임은 본인에게 있습니다."),
    "ja": dict(title="運用デスク・ブリーフ", sub="終値スナップショットからルールで選んだ本日の候補と根拠データ",
               gen="生成", base="基準率蓄積", days="日", close="終値基準", back="← スクリーナー", total="スクリーニング", liquid="流動性通過", picks="候補", rank="📈 ランキング推移", bt="📊 パフォーマンス",
               other="한국어",
               tabs=[("all", "すべて"), ("short", "短期"), ("long", "中長期"), ("news", "開示")],
               col=["コード", "銘柄", "分類", "騰落", "スコア", "シグナル", "200MA", "RSI", "RVOL", "売買代金", "PER", "判断"],
               copy="分析依頼をコピー", copy_all="表示中の銘柄すべての分析依頼をコピー", copied="コピー済み ✓",
               nollm="未評価", verdict_lbl="判断", base_lbl="シグナル基準率", dis_lbl="TDnet開示 (5営業日)", biz_lbl="事業",
               empty="ブリーフはまだありません。平日18:03 JST以降に自動生成されます。",
               howto="コピーしたテキストをClaudeのチャットに貼り付けると、100点方式(ファンダ・テクニカル・リスク・カタリスト)で評価が得られます。"
                     "数値はスクリーナーの値がそのまま入っており、モデルが新たに推定することはありません。発注機能はありません。",
               foot="候補選定ルール — 売買代金 ≥ {minval}{unit} ・ 時価総額 ≥ {mcap}{unit}{extra}、短期: 短期シグナル1つ以上 + スコア≥2、中長期: トレンド・バリュー・成長シグナル + スコア≥3、"
                    "開示: 直近の強い開示(上方・増配・自社株・分割・TOB) + シグナル1つ以上 ・ 同一業種は最大{maxind}銘柄 ・ 直近{cool}回のブリーフに出た銘柄は除外(開示は例外) ・ "
                    "参考情報であり、投資判断は自己責任です。"),
}

PAGE_HTML = """<!DOCTYPE html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — __DATE__</title><style>
:root{--bg:#0f141c;--surface:#171e29;--surface2:#1d2634;--line:#26303f;--text:#e9eef6;
--muted:#8a94a6;--faint:#5b6572;--up:#ff4f5e;--down:#3f8cff;--amber:#ffb224;--teal:#2dd4bf;--violet:#c084fc;--sky:#60cdff}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Pretendard','Malgun Gothic','Yu Gothic UI','Noto Sans JP',sans-serif;
font-size:13px;line-height:1.5;padding:14px 16px 50px}
.num{font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
a{color:var(--amber);text-decoration:none}
.topbar{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.dashbtn{padding:5px 12px;border:1px solid rgba(45,212,191,.45);border-radius:999px;background:var(--surface2);color:var(--teal);font-weight:600;font-size:12.5px}
.dashbtn:hover{background:var(--teal);color:#062a26}
.langbtn{margin-left:auto;padding:5px 12px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--faint);font-weight:600;font-size:12.5px}
.langbtn:hover{color:var(--text)}
h1{font-size:18px;font-weight:800;margin-bottom:2px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.mk{font-size:13px;font-weight:600;white-space:nowrap}.mk a{color:var(--muted);padding:2px 3px 3px}
.mk a.on{color:var(--amber);border-bottom:2px solid var(--amber)}.mk a:hover{color:var(--text)}.mk .sep{color:var(--faint);margin:0 4px}
.meta{color:var(--muted);font-size:12px;margin-bottom:6px}
.funnel{font-size:12.5px;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:9px 14px;margin:8px 0;display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.funnel .k{color:var(--muted)}.funnel b{color:var(--amber);font-size:14px}
.tabs{display:flex;gap:5px;margin:10px 0;flex-wrap:wrap;align-items:center}
.tab{padding:7px 13px;border:1px solid var(--line);border-radius:8px;background:var(--surface);cursor:pointer;font-weight:600;color:var(--muted);user-select:none}
.tab.on{color:var(--text);border-color:var(--amber);background:var(--surface2)}
.btn{padding:6px 12px;border:1px solid rgba(255,178,36,.5);border-radius:8px;background:var(--surface2);color:var(--amber);font-weight:700;font-size:12px;cursor:pointer;font-family:inherit}
.btn:hover{background:var(--amber);color:#2a1800}.btn.small{padding:3px 9px;font-size:11px}
.tabs .btn{margin-left:auto}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{background:var(--surface2);color:var(--muted);font-size:11.5px;font-weight:600;text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th.l,td.l{text-align:left}
td{padding:7px 10px;border-bottom:1px solid #1c2431;text-align:right;white-space:nowrap;vertical-align:middle}
tr.row{cursor:pointer}tr.row:hover td{background:var(--surface2)}
tr.det td{white-space:normal;text-align:left;background:#131a24;padding:12px 14px;border-bottom:1px solid var(--line)}
td.sg{white-space:normal;min-width:200px;line-height:1.9}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
.dw{position:sticky;left:0;max-width:calc(100vw - 34px)}
.up{color:var(--up)}.dn{color:var(--down)}.fl{color:var(--muted)}
.b{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1.5px 6px;margin:1px 5px 1px 0}
.b.s{background:rgba(255,178,36,.16);color:var(--amber)}.b.g{background:rgba(45,212,191,.13);color:var(--teal)}
.b.f{background:rgba(192,132,252,.14);color:var(--violet)}.b.w{background:rgba(96,205,255,.14);color:var(--sky)}
.b.i{background:rgba(138,148,166,.15);color:var(--muted)}
.bk{display:inline-block;font-size:10.5px;font-weight:700;border-radius:999px;padding:2px 8px}
.bk.short{background:rgba(255,178,36,.16);color:var(--amber)}.bk.long{background:rgba(45,212,191,.13);color:var(--teal)}.bk.news{background:rgba(192,132,252,.14);color:var(--violet)}
.vd{font-weight:800}.vd.buy{color:var(--up)}.vd.hold{color:var(--amber)}.vd.pass{color:var(--faint)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px 14px;margin:6px 0 10px}
.grid div{font-size:12px}.grid .k{color:var(--muted);font-size:10.5px;display:block}
.sec{margin-top:10px;color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.3px}
.dis{margin:3px 0}.dis .t{color:var(--faint);font-size:11px;margin-right:6px}.dis.strong a{color:var(--text);font-weight:700}
.llm{border-left:3px solid var(--amber);padding:6px 10px;margin:6px 0;background:var(--surface)}
.note{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;color:var(--muted);margin:10px 0;line-height:1.8}
footer{margin-top:14px;color:var(--faint);font-size:11px;line-height:1.7}
@media(max-width:760px){body{padding:10px 8px 30px}.hide-m{display:none}.tabs .btn{margin-left:0;width:100%}}
</style></head><body>
<div class="topbar">
  <a href="__BACK_HREF__">__BACK__</a>
  <a class="dashbtn" href="__RANK_HREF__">__RANK__</a>
  <a class="dashbtn" href="__BT_HREF__">__BT__</a>
  <a class="langbtn" href="__LANG_HREF__">__OTHER__</a>
</div>
<h1>__TITLE__ <span class="mk" id="mk"></span></h1>
<div class="meta" id="meta"></div>
<div id="app"></div>
<footer id="foot"></footer>
<script>
const BB=__BRIEFS__, T=__T__, PROMPTS=__PROMPTS__, HEADT=__HEAD__, LANG="__LANG__";
const SIG=__SIG__, KW=__KW__, GRP=__GRP__;
const MK=Object.keys(BB), UN=LANG==='ko'?'unit_ko':'unit_ja';
const LABEL={jp:{ko:'일본',ja:'日本'},kr:{ko:'한국',ja:'韓国'},us:{ko:'미국',ja:'米国'}};
const lbl=m=>(LABEL[m]||{})[LANG]||m;
let mkt=MK.includes(location.hash.slice(1))?location.hash.slice(1):(MK[0]||null), B=mkt?BB[mkt]:null;
let tab='all', open=new Set();
const head=()=>HEADT.replace('{date}',B?B.date:'');
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pc=(v,d=2)=>v==null?'<span class="fl">—</span>':`<span class="${v>0?'up':v<0?'dn':'fl'}">${v>0?'+':''}${v.toFixed(d)}%</span>`;
const n=(v,d=2)=>v==null?'—':v.toLocaleString(undefined,{maximumFractionDigits:d});
const BK={short:T.tabs[1][1],long:T.tabs[2][1],news:T.tabs[3][1]};
function vd(p){if(!p.llm)return `<span class="fl">${T.nollm}</span>`;const c=p.llm.verdict==='매수검토'?'buy':p.llm.verdict==='보류'?'hold':'pass';return `<span class="vd ${c}">${p.llm.total.toFixed(0)} ${esc(p.llm.verdict)}</span>`}
function copy(text,btn){navigator.clipboard.writeText(text).then(()=>{const o=btn.textContent;btn.textContent=T.copied;setTimeout(()=>btn.textContent=o,1500)})}
function detail(p){
  const g=[['200MA',n(p.sma200)],['5MA / 20MA',`${n(p.sma5)} / ${n(p.sma20)}`],['52w',`${n(p.lo52)} – ${n(p.hi52)} (${n(p.pos52,0)}%)`],
    ['1W / 1M / 3M',`${pc(p.pw,1)} / ${pc(p.p1,1)} / ${pc(p.p3,1)}`],['YTD',pc(p.ytd,1)],['MACD-H',n(p.macd_h)],
    ['MCap',n(p.mcap,0)],['PBR',n(p.pbr)],['ROE',pc(p.roe,1)],['EqR',pc(p.eqr,1)],['Div',pc(p.div)],['D/E',n(p.de)],
    ['Rev YoY Q / TTM',`${pc(p.rev_q,1)} / ${pc(p.rev_ttm,1)}`],['EPS YoY Q',pc(p.eps_q,1)],['5y CAGR',pc(p.cagr5,1)],['OPM',pc(p.opm,1)],['ROIC',pc(p.roic,1)],['PSR / PEG',`${n(p.psr)} / ${n(p.peg)}`],['Inflow',n(p.inflow)]];
  const base=Object.entries(p.baserate||{}).map(([k,hs])=>{const h=hs['5']?'5':hs['20']?'20':hs['1']?'1':null;if(!h)return '';const s=hs[h];
    return `<span class="b ${GRP[k]||'i'}">${esc(SIG[k])}</span><span class="num" style="font-size:11.5px;margin-right:12px">${h}d ${s.win}% · ${s.excess>0?'+':''}${s.excess}%p · n=${s.n}</span>`}).join('');
  const dis=(p.tdnet||[]).map(x=>{const tags=KW.map((l,i)=>(x.bits>>i)&1?`<span class="b ${x.strong?'s':'i'}">${esc(l)}</span>`:'').join('');
    return `<div class="dis ${x.strong?'strong':''}"><span class="t num">${esc(x.pub.slice(5))}</span>${tags}<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a></div>`}).join('');
  const llm=p.llm?`<div class="llm"><b>${vd(p)}</b> · F ${p.llm.fund} / T ${p.llm.tech} / R ${p.llm.risk} / C ${p.llm.cat} · ${esc(p.llm.confidence)}<br>${esc(p.llm.reason)}
    ${p.llm.hard_stop?`<br><b class="up">STOP</b> ${esc(p.llm.hard_stop_reason)}`:''}
    <br>✅ ${p.llm.strengths.map(esc).join(' · ')}<br>⚠️ ${p.llm.risks.map(esc).join(' · ')}<br>👁 ${p.llm.watch.map(esc).join(' · ')}
    ${p.llm.news.map(x=>`<br><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.date)} ${esc(x.title)}</a> <span class="fl">${esc(x.source)}</span>`).join('')}</div>`:'';
  return `<div class="dw"><div class="grid">${g.map(([k,v])=>`<div><span class="k">${k}</span><span class="num">${v}</span></div>`).join('')}</div>
    ${llm}
    ${base?`<div class="sec">${T.base_lbl}</div><div>${base}</div>`:''}
    ${dis?`<div class="sec">${T.dis_lbl}</div>${dis}`:''}
    ${p.biz?`<div class="sec">${T.biz_lbl}</div><div style="color:var(--muted)">${esc(p.biz)}</div>`:''}
    <div style="margin-top:10px"><button class="btn small" data-copy="${p.code}">${T.copy}</button></div></div>`;
}
function render(){
  $('#mk').innerHTML=MK.map(m=>`<a href="#${m}" data-m="${m}" class="${m===mkt?'on':''}">${lbl(m)}</a>`).join('<span class="sep">·</span>');
  if(!B||!B.picks||!B.picks.length){$('#app').innerHTML=`<div class="note">${T.empty}</div>`;$('#meta').textContent='';$('#foot').textContent='';return}
  const u=B.universe, c=B.config||{};
  $('#meta').textContent=`${lbl(m=mkt)} ${B.date} ${T.close} · ${T.gen} ${B.generated} · ${T.base} ${B.baserate_days}${T.days}`;
  const extra=c.MIN_PRICE>0?(LANG==='ko'?` · 주가 ≥ $${c.MIN_PRICE}`:` ・ 株価 ≥ $${c.MIN_PRICE}`):'';
  const fu=v=>B.market==='us'?`$${v}M`:`${v}${B[UN]}`;
  $('#foot').textContent=T.foot.replace('{minval}{unit}',fu(c.MIN_VAL)).replace('{mcap}{unit}',fu(c.MIN_MCAP)).replace('{extra}',extra).replace('{maxind}',c.MAX_PER_INDUSTRY).replace('{cool}',c.COOLDOWN_DAYS);
  const ps=B.picks.filter(p=>tab==='all'||p.bucket===tab);
  $('#app').innerHTML=`<div class="funnel"><span><span class="k">${T.total}</span> <b>${u.total.toLocaleString()}</b></span><span class="k">→</span>
    <span><span class="k">${T.liquid}</span> <b>${u.liquid.toLocaleString()}</b></span><span class="k">→</span>
    <span><span class="k">${T.picks}</span> <b>${u.candidates}</b> <span class="k">(${BK.short} ${u.short} · ${BK.long} ${u.long} · ${BK.news} ${u.news})</span></span></div>
  <div class="tabs">${T.tabs.map(([k,l])=>`<div class="tab ${k===tab?'on':''}" data-t="${k}">${l}</div>`).join('')}<button class="btn" id="copyall">${T.copy_all}</button></div>
  <div class="tw"><table><thead><tr>${T.col.map((c,i)=>`<th class="${i<3||i===5?'l':''} ${[6,8,9,10].includes(i)?'hide-m':''}">${c}</th>`).join('')}</tr></thead><tbody>
  ${ps.map(p=>`<tr class="row" data-c="${p.code}"><td class="l num">${p.code}</td><td class="l">${esc(p.name)}</td><td class="l"><span class="bk ${p.bucket}">${BK[p.bucket]}</span></td>
    <td class="num">${pc(p.chg)}</td><td class="num">${n(p.score,0)}</td>
    <td class="l sg">${p.signals.map(k=>`<span class="b ${GRP[k]||'i'}">${esc(SIG[k])}</span>`).join('')}</td>
    <td class="num hide-m">${pc(p.ext200,1)}</td><td class="num">${n(p.rsi,1)}</td><td class="num hide-m">${n(p.rvol)}</td>
    <td class="num hide-m">${n(p.val,0)}</td><td class="num hide-m">${n(p.per,1)}</td><td>${vd(p)}</td></tr>
    ${open.has(p.code)?`<tr class="det"><td colspan="12">${detail(p)}</td></tr>`:''}`).join('')}</tbody></table></div>
  <div class="note">${T.sub}. ${T.howto}</div>`;
}
document.addEventListener('click',e=>{
  const c=e.target.closest('[data-copy]');if(c){copy(head()+'\\n'+PROMPTS[mkt][c.dataset.copy],c);return}
  if(e.target.id==='copyall'){const ps=B.picks.filter(p=>tab==='all'||p.bucket===tab);copy(head()+'\\n'+ps.map(p=>PROMPTS[mkt][p.code]).join('\\n\\n'),e.target);return}
  const mt=e.target.closest('[data-m]');if(mt){e.preventDefault();mkt=mt.dataset.m;B=BB[mkt];tab='all';open=new Set();history.replaceState(null,'','#'+mkt);render();return}
  const t=e.target.closest('.tab');if(t){tab=t.dataset.t;render();return}
  const r=e.target.closest('tr.row');if(r){const k=r.dataset.c;open.has(k)?open.delete(k):open.add(k);render()}
});
window.addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(MK.includes(h)&&h!==mkt){mkt=h;B=BB[mkt];tab='all';open=new Set();render()}});
render();
</script></body></html>"""


def latest_brief(m):
    files = sorted(glob.glob(str(BRIEFS / m / "*.json")))
    return json.loads(Path(files[-1]).read_text(encoding="utf-8")) if files else None


def render_pages():
    out = Path(CFG["OUTPUT_DIR"])
    if not out.is_absolute():
        out = BASE / out
    briefs = {m: b for m in MARKETS if (b := latest_brief(m))}
    for m, b in briefs.items():                       # v0 형식(메타 없음) JSON 도 렌더되도록 보정
        mk = MARKETS[m]
        for k in ("label_ko", "label_ja", "unit_ko", "unit_ja"):
            b.setdefault(k, mk[k])
        cfg = b.setdefault("config", {})
        for k, v in (("MIN_VAL", MIN_VAL_DEFAULT[m]), ("MIN_MCAP", MIN_MCAP_DEFAULT[m]), ("MIN_PRICE", MIN_PRICE_DEFAULT[m]),
                     ("MAX_PER_INDUSTRY", CFG["MAX_PER_INDUSTRY"]), ("COOLDOWN_DAYS", CFG["COOLDOWN_DAYS"])):
            cfg.setdefault(k, v)
    latest = max((b["date"] for b in briefs.values()), default="—")
    grp = {**{k: "s" for k in SIG_SHORT}, **{k: "g" for k in SIG_TREND}, **{k: "f" for k in SIG_FUND},
           **{k: "w" for k in SIG_GROWTH}, "sig_inflow": "i"}
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")  # noqa: E731
    for lang in ("ko", "ja"):
        T = PAGE_T[lang]
        prompts = {m: {p["code"]: stock_block(p, b["date"], lang, m) for p in b["picks"]} for m, b in briefs.items()}
        rep = {
            "__LANG__": lang, "__TITLE__": T["title"], "__SUB__": T["sub"], "__DATE__": latest,
            "__BACK__": T["back"], "__BACK_HREF__": "../jp/index.html",
            "__RANK__": T["rank"], "__RANK_HREF__": "../ranking/index.html",
            "__BT__": T["bt"], "__BT_HREF__": "../backtest/index.html",
            "__OTHER__": T["other"], "__LANG_HREF__": "../ja/brief/index.html" if lang == "ko" else "../../brief/index.html",
            "__BRIEFS__": js(briefs), "__T__": js(T), "__PROMPTS__": js(prompts), "__HEAD__": js(PROMPT_HEAD[lang]),
            "__SIG__": js({k: sig_label(k, lang) for k in SIG_ALL}), "__KW__": js(KW_LABELS[lang]), "__GRP__": js(grp),
        }
        page = PAGE_HTML
        for k, v in rep.items():
            page = page.replace(k, v)
        d = out / ("brief" if lang == "ko" else "ja/brief")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        done = ", ".join(f"{m} {b['date']}" for m, b in briefs.items()) or "브리프 없음"
        print(f"  [{lang}] 페이지 → {d}/index.html ({done})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "page":
        render_pages()
    else:
        generate()
