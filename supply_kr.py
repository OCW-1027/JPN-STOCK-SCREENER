# -*- coding: utf-8 -*-
"""
supply_kr.py — 한국 투자자별 매매동향 수집 (네이버)
====================================================
m.stock.naver.com/api/stock/{code}/trend 이 종목당 최근 10영업일의
외국인·기관·개인 순매수와 외국인 지분율을 준다. (Actions 환경에서 동작 확인 완료)

종목당 1회 호출이라 2,700종목이면 13분 이상 걸린다. 그래서
15분 주기 파이프라인(daily.yml)에는 넣지 않고 별도 워크플로로 하루 1회만 돈다.
— 프로필 수집이 daily에 묶여 있다가 15분 주기를 망가뜨렸던 전례를 피하기 위함.

출력: supply/kr.json
  {code: {f_net5, f_net1, f_ratio, f_days, o_net5, o_net1, o_days, i_net5}}
    f_net5  최근 5일 외국인 순매수 합(주)
    f_net1  전일 외국인 순매수(주)
    f_ratio 외국인 지분율(%)
    f_days  외국인 연속 순매수 일수 (음수면 연속 순매도)
    o_*     기관 동일
    i_net5  최근 5일 개인 순매수 합
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")
URL = "https://m.stock.naver.com/api/stock/{code}/trend"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
      "Referer": "https://m.stock.naver.com/", "Accept": "application/json"}

SLEEP = float(os.environ.get("KR_SLEEP", "0.25"))
LIMIT = int(os.environ.get("KR_LIMIT", "0"))          # 0=전 종목
MAX_FAIL = 40                                          # 연속 실패 시 중단(차단 추정)


def universe():
    """시가총액순 코스피·코스닥 종목코드."""
    from tradingview_screener import Query, col
    n, df = (Query().set_markets("korea").select("name", "market_cap_basic")
             .where(col("type") == "stock", col("exchange") == "KRX")
             .limit(12000).get_scanner_data())
    df = df.sort_values("market_cap_basic", ascending=False)
    codes = [str(c) for c in df["name"].tolist()]
    return codes[:LIMIT] if LIMIT else codes


def streak(vals):
    """앞(최신)에서부터 같은 부호가 이어지는 일수. 순매수면 +, 순매도면 -."""
    if not vals or vals[0] == 0:
        return 0
    sign = 1 if vals[0] > 0 else -1
    n = 0
    for v in vals:
        if (v > 0 and sign > 0) or (v < 0 and sign < 0):
            n += 1
        else:
            break
    return n * sign


def fetch(code, session):
    r = session.get(URL.format(code=code), headers=UA, timeout=12)
    if r.status_code != 200:
        return None
    rows = r.json()
    if not isinstance(rows, list) or not rows:
        return None
    # 최신순 정렬 (bizdate 내림차순)
    rows = sorted(rows, key=lambda x: str(x.get("bizdate", "")), reverse=True)

    def nums(key):
        out = []
        for x in rows:
            v = x.get(key)
            try:
                out.append(int(str(v).replace(",", "")))
            except (TypeError, ValueError):
                out.append(0)
        return out

    f, o, i = nums("foreignerPureBuyQuant"), nums("organPureBuyQuant"), nums("individualPureBuyQuant")
    # 지분율은 "46.70%" 형태로 오므로 % 기호를 떼고 변환한다.
    try:
        ratio = float(str(rows[0].get("foreignerHoldRatio", ""))
                      .replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        ratio = None
    return {
        "f_net1": f[0], "f_net5": sum(f[:5]), "f_days": streak(f), "f_ratio": ratio,
        "o_net1": o[0], "o_net5": sum(o[:5]), "o_days": streak(o),
        "i_net5": sum(i[:5]),
    }


def main():
    print("=" * 60)
    print("한국 투자자별 매매동향 수집", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    codes = universe()
    print(f"  대상 {len(codes)}종목 (요청 간격 {SLEEP}초 · 예상 {len(codes)*SLEEP/60:.1f}분)")

    s = requests.Session()
    out, ok, fail, consec = {}, 0, 0, 0
    for idx, c in enumerate(codes, 1):
        try:
            d = fetch(c, s)
            if d:
                out[c] = d
                ok += 1
                consec = 0
            else:
                fail += 1
                consec += 1
        except Exception:
            fail += 1
            consec += 1
        if consec >= MAX_FAIL:
            print(f"  연속 실패 {consec}회 — 차단 추정, 중단 (수집분은 저장)")
            break
        if idx % 500 == 0:
            print(f"    {idx}/{len(codes)} 진행 (성공 {ok} / 실패 {fail})")
        time.sleep(SLEEP)

    if not out:
        print("  수집 0건 — 기존 파일 유지하고 종료")
        return

    d = BASE / "supply"
    d.mkdir(exist_ok=True)
    (d / "kr.json").write_text(
        json.dumps({"meta": {"asof": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
                             "count": len(out)}, "data": out}, ensure_ascii=False),
        encoding="utf-8")
    print(f"  완료 — 성공 {ok} / 실패 {fail} → supply/kr.json")


if __name__ == "__main__":
    main()
