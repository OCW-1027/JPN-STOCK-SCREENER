# -*- coding: utf-8 -*-
"""
supply.py — 일본 수급 데이터 수집 (JPX 공개 자료)
=================================================
① 銘柄別信用取引週末残高  — 주간 PDF (매주 화요일, 전주 금요일 기준). 3,700종목.
   → 신용매수/매도 잔고, 전주비, 대차배율(매수÷매도)
② 空売り残高報告            — 일별 Excel. 발행주식 0.5% 이상 숏 포지션을 가진 기관.
   → 종목별 합산 공매도 잔고 비율과 직전 대비 증감

출력: supply/jp.json  {code: {...}}  — screener.py가 읽어 일본 페이지에만 컬럼을 채운다.
주의: 대차배율 1배 미만은 약세 신호가 아니라 주주우대 크로스(優待つなぎ売り)인 경우가 많다.
      우대 권리월(3·9월) 전후에는 외식·소매주가 대거 잡히므로 해석에 유의.
"""
import io
import json
import re
import sys
from datetime import datetime
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
JPX = "https://www.jpx.co.jp"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}


def _num(s):
    s = str(s).replace(",", "").replace("▲", "-").replace(" ", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


# ─────────────── ① 신용잔고 (주간 PDF) ───────────────
def fetch_margin():
    import pdfplumber
    # 2026-09 JPX 페이지 재편: 종목별 주간 파일이 05.html → 01.html 로 이동. 둘 다 시도.
    files = []
    for pg in ("01.html", "05.html", "index.html"):
        page = requests.get(f"{JPX}/markets/statistics-equities/margin/{pg}", headers=UA, timeout=20).text
        files = sorted(set(re.findall(r'href="([^"]+syumatsu\d{10}\.pdf)"', page)))
        if files:
            break
    if not files:
        raise RuntimeError("신용잔고 PDF 링크 없음 (01/05/index 모두)")
    latest = files[-1]
    asof = re.search(r"syumatsu(\d{4})(\d{2})(\d{2})", latest)
    asof = f"{asof.group(1)}-{asof.group(2)}-{asof.group(3)}"
    pdf = requests.get(JPX + latest, headers=UA, timeout=60).content

    out = {}
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for pg in doc.pages:
            tbl = pg.extract_table()
            if not tbl:
                continue
            for row in tbl:
                if not row or not row[0] or len(row) < 8:
                    continue
                head = str(row[0]).replace("\n", " ").strip()
                m = re.match(r"^[A-Z]?\s*(.+?)\s+([0-9][0-9A-Z]{3})0\s*$", head)
                if not m:
                    continue
                code = m.group(2)
                sell, sell_chg, buy, buy_chg = _num(row[4]), _num(row[5]), _num(row[6]), _num(row[7])
                if sell is None or buy is None:
                    continue
                out[code] = {
                    "m_sell": sell, "m_sell_chg": sell_chg,
                    "m_buy": buy, "m_buy_chg": buy_chg,
                    "m_ratio": round(buy / sell, 2) if sell > 0 else None,
                }
    print(f"  [신용잔고] {asof} 기준 {len(out)}종목")
    return out, asof


# ─────────────── ② 공매도 잔고 (일별 Excel) ───────────────
# 긴 법인명 → 화면용 짧은 표기
_SHORT = [
    ("GOLDMAN SACHS", "Goldman Sachs"), ("Barclays Capital", "Barclays"),
    ("モルガン・スタンレーMUFG", "Morgan Stanley MUFG"), ("Morgan Stanley & Co", "Morgan Stanley Intl"),
    ("Nomura International", "Nomura Intl"), ("JPM Securities Japan", "JPMorgan Japan"),
    ("J.P. Morgan Securities", "JPMorgan"), ("MERRILL LYNCH", "Merrill Lynch"),
    ("UBS AG", "UBS"), ("Citigroup Global Markets", "Citi"), ("BNP Paribas", "BNP Paribas"),
    ("Societe Generale", "SocGen"), ("Diversified Select Opportunities", "Diversified Select Opp."),
    ("Man Numeric", "Man Numeric"), ("Two Sigma", "Two Sigma"), ("Millennium", "Millennium"),
    ("Marshall Wace", "Marshall Wace"), ("Point72", "Point72"), ("Citadel", "Citadel"),
    ("AQR", "AQR"), ("Squarepoint", "Squarepoint"), ("Qube", "Qube"),
]


def _short_name(name):
    for k, v in _SHORT:
        if k.lower() in name.lower():
            return v
    return name[:26]


def fetch_short():
    page = requests.get(f"{JPX}/markets/public/short-selling/index.html", headers=UA, timeout=20).text
    files = sorted(set(re.findall(r'href="([^"]+_Short_Positions\.xls)"', page)))
    if not files:
        raise RuntimeError("공매도 파일 링크 없음")
    latest = files[-1]
    asof = re.search(r"(\d{4})(\d{2})(\d{2})_Short", latest)
    asof = f"{asof.group(1)}-{asof.group(2)}-{asof.group(3)}"
    xls = requests.get(JPX + latest, headers=UA, timeout=60).content
    df = pd.read_excel(io.BytesIO(xls), sheet_name=0, header=None)

    # 헤더 행(銘柄コード가 있는 행) 아래부터
    hdr = next(i for i in range(min(15, len(df))) if "銘柄コード" in "".join(map(str, df.iloc[i].tolist())))
    body = df.iloc[hdr + 2:]
    agg = {}
    for _, r in body.iterrows():
        code = str(r.iloc[2]).strip()
        if not re.match(r"^[0-9][0-9A-Z]{3}$", code):
            continue
        cur = pd.to_numeric(r.iloc[10], errors="coerce")
        prev = pd.to_numeric(r.iloc[14], errors="coerce")
        if pd.isna(cur):
            continue
        a = agg.setdefault(code, {"s_pct": 0.0, "s_prev": 0.0, "s_n": 0, "_who": []})
        a["s_pct"] += float(cur) * 100
        a["s_prev"] += (float(prev) * 100) if not pd.isna(prev) else float(cur) * 100
        a["s_n"] += 1
        # 기관명: 종목별 상위 5곳을 이름·현재%·증감%p로 보존
        #   ※ 대부분 프라임 브로커 명의(헤지펀드 고객 포지션)이므로 "그 증권사의 견해"로 읽지 말 것
        name = str(r.iloc[5]).strip().replace("\n", " ")
        pct = round(float(cur) * 100, 2)
        chg = round(pct - float(prev) * 100, 2) if not pd.isna(prev) else None
        a["_who"].append([_short_name(name), pct, chg])
    for a in agg.values():
        a["s_pct"] = round(a["s_pct"], 2)
        a["s_chg"] = round(a["s_pct"] - a["s_prev"], 2)
        del a["s_prev"]
        a["s_who"] = sorted(a.pop("_who"), key=lambda x: -x[1])[:5]
    print(f"  [공매도] {asof} 기준 {len(agg)}종목 (0.5%↑ 포지션 보유 기관 합산)")
    return agg, asof


# ─────────────── ③ 역일보 / 품대료 (일별 Excel) ───────────────
def fetch_premium():
    """JPX 品貸料率一覧 → {code: {gy_rate, gy_excess}}. 역일보 미발생 종목은 제외."""
    page = requests.get(f"{JPX}/markets/statistics-equities/margin/02.html", headers=UA, timeout=20).text
    links = re.findall(r'href="([^"]+Premium_Charges\.xlsx)"', page)
    if not links:
        raise RuntimeError("품대료 파일 링크 없음")
    xl = requests.get(JPX + links[0], headers=UA, timeout=60).content
    df = pd.read_excel(io.BytesIO(xl), header=None)
    hdr = next(i for i in range(min(10, len(df))) if "Code" in "".join(map(str, df.iloc[i].tolist())))
    body = df.iloc[hdr + 1:].copy()
    body.columns = ["date", "code", "name", "ex", "excess", "maxrate", "rate"][:body.shape[1]]
    asof = str(body["date"].iloc[0])
    asof = f"{asof[:4]}-{asof[4:6]}-{asof[6:8]}"
    out = {}
    for _, r in body.iterrows():
        code = str(r["code"]).strip()
        if not re.match(r"^[0-9][0-9A-Z]{3}$", code):
            continue
        rate = pd.to_numeric(r["rate"], errors="coerce")     # '*****' = 미발생 → NaN
        if pd.isna(rate) or rate <= 0:
            continue
        ex = pd.to_numeric(r["excess"], errors="coerce")
        out[code] = {"gy_rate": round(float(rate), 2),
                     "gy_excess": int(ex) if not pd.isna(ex) else None}
    print(f"  [역일보] {asof} 기준 {len(out)}종목 발생 (대차종목 {len(body)}개 중)")
    return out, asof


def main():
    print("=" * 60)
    print("일본 수급 데이터 수집", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    merged, meta = {}, {}
    try:
        m, asof = fetch_margin()
        meta["margin_asof"] = asof
        for c, v in m.items():
            merged.setdefault(c, {}).update(v)
    except Exception as e:  # noqa: BLE001
        print(f"  [신용잔고] 실패: {type(e).__name__}: {str(e)[:80]}")
    try:
        s, asof = fetch_short()
        meta["short_asof"] = asof
        for c, v in s.items():
            merged.setdefault(c, {}).update(v)
    except Exception as e:  # noqa: BLE001
        print(f"  [공매도] 실패: {type(e).__name__}: {str(e)[:80]}")

    try:
        g, asof = fetch_premium()
        meta["premium_asof"] = asof
        for c, v in g.items():
            merged.setdefault(c, {}).update(v)
    except Exception as e:  # noqa: BLE001
        print(f"  [역일보] 실패: {type(e).__name__}: {str(e)[:80]}")

    out = BASE / "supply"
    out.mkdir(exist_ok=True)
    (out / "jp.json").write_text(json.dumps({"meta": meta, "data": merged}, ensure_ascii=False),
                                 encoding="utf-8")
    print(f"  완료 → supply/jp.json ({len(merged)}종목)")


if __name__ == "__main__":
    main()
