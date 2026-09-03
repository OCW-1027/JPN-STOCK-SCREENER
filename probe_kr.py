# -*- coding: utf-8 -*-
"""
probe_kr.py — 한국 수급 데이터 소스 탐색 (1회성 진단)
=======================================================
개발 컨테이너에서는 네이버·KRX가 403으로 막히지만 GitHub Actions에서는 열린 전례가 있다.
어떤 엔드포인트가 실제로 응답하는지 Actions에서 한 번 돌려 확인한 뒤,
성공한 경로만 골라 supply_kr.py 본체를 만든다.

Actions > Run workflow 로 수동 실행하고 로그만 확인하면 된다. 파일은 남기지 않는다.
"""
import json
import sys
import time

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "ko-KR,ko;q=0.9"}
CODE = "005930"          # 삼성전자로 시험
TODAY = time.strftime("%Y%m%d")


def show(label, r, want_json=True):
    """응답 요약 한 줄 + 성공 시 데이터 구조."""
    size = len(r.content)
    ok = r.status_code == 200
    head = ""
    if ok and want_json:
        try:
            j = r.json()
            if isinstance(j, dict):
                keys = list(j.keys())[:6]
                head = f"dict keys={keys}"
                for k in j:
                    if isinstance(j[k], list) and j[k]:
                        head += f" | {k}[{len(j[k])}] 첫항목키={list(j[k][0].keys())[:8]}"
                        break
            elif isinstance(j, list):
                head = f"list[{len(j)}]"
                if j and isinstance(j[0], dict):
                    head += f" 첫항목키={list(j[0].keys())[:8]}"
        except Exception:
            head = "JSON 아님: " + r.text[:70].replace("\n", " ")
    elif ok:
        head = r.text[:70].replace("\n", " ")
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label:34s} {r.status_code}  {size:>8,}b  {head[:130]}")
    return ok


def probe(label, url, method="get", data=None, headers=None, session=None):
    s = session or requests
    h = {**UA, **(headers or {})}
    try:
        r = s.post(url, headers=h, data=data, timeout=20) if method == "post" \
            else s.get(url, headers=h, timeout=20)
        return show(label, r), r
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {label:34s} 예외 {type(e).__name__}: {str(e)[:60]}")
        return False, None


def main():
    print("=" * 78)
    print(f"한국 수급 소스 탐색  종목={CODE}  기준일={TODAY}")
    print("=" * 78)

    print("\n[A] 네이버 — 종목 상세 / 투자자 동향")
    probe("m.stock 종목 통합", f"https://m.stock.naver.com/api/stock/{CODE}/integration")
    probe("m.stock 투자자별 거래", f"https://m.stock.naver.com/api/stock/{CODE}/trend")
    probe("m.stock 외국인·기관", f"https://m.stock.naver.com/api/stock/{CODE}/investor")
    probe("api.stock 투자자별", f"https://api.stock.naver.com/stock/{CODE}/trend")
    probe("api.stock 종목 정보", f"https://api.stock.naver.com/stock/{CODE}/basic")
    probe("polling 실시간", f"https://polling.finance.naver.com/api/realtime/domestic/stock/{CODE}")
    probe("finance 외인/기관 HTML", f"https://finance.naver.com/item/frgn.naver?code={CODE}")

    print("\n[B] 네이버 — 시장 전체 투자자 동향")
    probe("업종·투자자 종합", "https://m.stock.naver.com/api/index/KOSPI/investor")
    probe("시장 투자자별 매매",
          "https://m.stock.naver.com/api/stocks/investorTrend/KOSPI?type=all")

    print("\n[C] KRX 정보데이터시스템 (세션 필요)")
    s = requests.Session()
    s.headers.update(UA)
    try:
        s.get("http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd"
              "?menuId=MDC0201020103", timeout=20)
        print(f"    (세션 쿠키: {list(s.cookies.keys())})")
    except Exception as e:  # noqa: BLE001
        print(f"    (세션 획득 실패: {str(e)[:50]})")
    kh = {"Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    probe("KRX 전종목 공매도", url, "post", session=s, headers=kh,
          data={"bld": "dbms/MDC/STAT/standard/MDCSTAT03701", "locale": "ko_KR",
                "mktId": "ALL", "trdDd": TODAY})
    probe("KRX 투자자별 거래실적", url, "post", session=s, headers=kh,
          data={"bld": "dbms/MDC/STAT/standard/MDCSTAT02201", "locale": "ko_KR",
                "mktId": "STK", "trdDd": TODAY, "share": "1", "money": "1"})
    probe("KRX 공매도 잔고", url, "post", session=s, headers=kh,
          data={"bld": "dbms/MDC/STAT/srt/MDCSTAT30001", "locale": "ko_KR",
                "mktTpCd": "1", "trdDd": TODAY})

    print("\n[D] 기타 공개 소스")
    probe("SEIBro 공매도", "https://seibro.or.kr/websquare/control.jsp")
    probe("공매도종합포털", "https://short.krx.co.kr/contents/SRT/99/SRT99000001.jsp")

    print("\n" + "=" * 78)
    print("성공(✓)한 항목의 '첫항목키'를 보고 어떤 필드를 쓸 수 있는지 판단한다.")
    print("=" * 78)


if __name__ == "__main__":
    main()
