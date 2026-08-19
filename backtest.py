# -*- coding: utf-8 -*-
"""
backtest.py — 시그널 적중률 백테스트
=====================================
history/{jp,kr,us}/날짜.csv.gz 스냅샷을 전부 읽어, 각 시그널에 걸렸던 종목이
그 후 1·5·20 거래일 동안 실제로 어떻게 움직였는지(승률·평균수익·시장대비)를
집계하고 site/backtest/index.html 리포트와 results.json을 생성한다.

데이터가 부족한 초기에는 "축적 중" 안내 페이지를 만든다. 스냅샷은 종가판
실행 때마다 자동으로 쌓이므로 시간이 지날수록 통계가 촘촘해진다.
"""
import glob
import gzip
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")
OUT = Path(os.environ.get("OUTPUT_DIR", "site"))
if not OUT.is_absolute():
    OUT = BASE / OUT

FLOOR = {"jp": 1.0e8, "kr": 1.0e8, "us": 1.0e6}   # 거래대금 하한 (억엔/억원/$M 의 1)
HORIZONS = [1, 5, 20]
MKT_LABEL = {"jp": "🇯🇵 일본", "kr": "🇰🇷 한국", "us": "🇺🇸 미국"}

SIGNALS = [  # (컬럼, 표시명, 그룹)
    ("sig_spike", "급증", "s"), ("sig_x5", "5MA돌파", "s"), ("sig_x20", "20MA돌파", "s"),
    ("sig_high", "신고가권", "s"), ("sig_gap", "갭업", "s"), ("sig_oversold", "과매도반등", "s"),
    ("sig_gc", "GC직후", "g"), ("sig_reclaim", "200탈환", "g"),
    ("sig_trend", "정배열", "g"), ("sig_macd", "MACD골든", "g"),
    ("sig_value", "저평가", "f"), ("sig_div", "고배당", "f"), ("sig_qual", "우량", "f"),
]
GROUPS = [("grp_short", "단기(아무거나)", "s"), ("grp_long", "중장기(아무거나)", "g"),
          ("grp_fund", "펀더(아무거나)", "f"), ("grp_multi", "시그널 2개 이상", "m")]


def load_snapshots(m):
    """날짜순 스냅샷 로드 + 휴장일(가격 미변동) 제거."""
    files = sorted(glob.glob(str(BASE / "history" / m / "*.csv.gz")))
    snaps, prev_close = [], None
    for f in files:
        date = Path(f).name.replace(".csv.gz", "")
        try:
            df = pd.read_csv(f, compression="gzip", dtype={"code": str})
        except Exception:
            continue
        if "code" not in df.columns or "close" not in df.columns:
            continue
        df = df.dropna(subset=["code", "close"]).drop_duplicates(subset="code").set_index("code")
        if prev_close is not None:
            common = df.index.intersection(prev_close.index)
            if len(common) > 100:
                same = (df.loc[common, "close"] == prev_close.loc[common]).mean()
                if same > 0.97:      # 휴장일 스냅샷
                    continue
        prev_close = df["close"]
        sigcols = [c for c, _, _ in SIGNALS if c in df.columns]
        for c in sigcols:
            df[c] = df[c].fillna(False).astype(bool)
        df["grp_short"] = df[[c for c in sigcols if dict((a, g) for a, _, g in SIGNALS)[c] == "s"]].any(axis=1) if sigcols else False
        df["grp_long"] = df[[c for c in sigcols if dict((a, g) for a, _, g in SIGNALS)[c] == "g"]].any(axis=1) if sigcols else False
        df["grp_fund"] = df[[c for c in sigcols if dict((a, g) for a, _, g in SIGNALS)[c] == "f"]].any(axis=1) if sigcols else False
        df["grp_multi"] = df[sigcols].sum(axis=1) >= 2 if sigcols else False
        snaps.append((date, df))
    return snaps


def analyze(m):
    snaps = load_snapshots(m)
    dates = [d for d, _ in snaps]
    res = {"dates": dates, "n_days": len(dates), "signals": {}, "horizon_days": {}}
    if len(dates) < 2:
        return res
    keys = [(c, n) for c, n, _ in SIGNALS] + [(c, n) for c, n, _ in GROUPS]
    acc = {k[0]: {h: {"r": [], "x": []} for h in HORIZONS} for k in keys}
    hcount = {h: 0 for h in HORIZONS}

    for h in HORIZONS:
        for i in range(len(snaps) - h):
            d0, a = snaps[i]
            _, b = snaps[i + h]
            common = a.index.intersection(b.index)
            base = a.loc[common]
            ret = (b.loc[common, "close"] / base["close"] - 1) * 100
            liq = base.get("Value.Traded", pd.Series(0, index=common)).fillna(0) >= FLOOR[m]
            uni = ret[liq]
            if len(uni) < 50:
                continue
            mkt = uni.mean()
            hcount[h] += 1
            for c, _n in keys:
                if c not in base.columns:
                    continue
                mask = base[c].fillna(False).astype(bool) & liq
                r = ret[mask]
                if len(r):
                    acc[c][h]["r"].extend(r.tolist())
                    acc[c][h]["x"].extend((r - mkt).tolist())

    for c, n in keys:
        res["signals"][c] = {"name": n}
        for h in HORIZONS:
            r = pd.Series(acc[c][h]["r"])
            x = pd.Series(acc[c][h]["x"])
            if len(r) == 0:
                res["signals"][c][str(h)] = None
                continue
            res["signals"][c][str(h)] = {
                "n": int(len(r)),
                "win": round(float((r > 0).mean() * 100), 1),
                "avg": round(float(r.mean()), 2),
                "med": round(float(r.median()), 2),
                "excess": round(float(x.mean()), 2),
                "best": round(float(r.max()), 1),
                "worst": round(float(r.min()), 1),
            }
    res["horizon_days"] = {str(h): hcount[h] for h in HORIZONS}
    return res


HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>시그널 성과 분석 — __GEN__</title><style>
:root{--bg:#0f141c;--surface:#171e29;--surface2:#1d2634;--line:#26303f;--text:#e9eef6;
--muted:#8a94a6;--faint:#5b6572;--up:#ff4f5e;--down:#3f8cff;--amber:#ffb224;--teal:#2dd4bf;--violet:#c084fc}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Pretendard','Malgun Gothic','Yu Gothic UI',sans-serif;
font-size:13px;line-height:1.5;padding:14px 16px 50px}
.num{font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
a{color:var(--amber);text-decoration:none}
h1{font-size:18px;font-weight:800;margin-bottom:4px}h1 span{color:var(--amber)}
.meta{color:var(--muted);font-size:12px;margin-bottom:12px}
.tabs{display:flex;gap:5px;margin:10px 0;flex-wrap:wrap}
.tab{padding:7px 13px;border:1px solid var(--line);border-radius:8px;background:var(--surface);
cursor:pointer;font-weight:600;color:var(--muted);user-select:none}
.tab.on{color:var(--text);border-color:var(--amber);background:var(--surface2)}
.htabs .tab.on{border-color:var(--teal)}
.note{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
color:var(--muted);margin:10px 0;line-height:1.8}
.note b{color:var(--text)}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line);
border-radius:10px;overflow:hidden}
th{background:var(--surface2);color:var(--muted);font-size:11.5px;font-weight:600;text-align:right;
padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th.l,td.l{text-align:left}
td{padding:7px 10px;border-bottom:1px solid #1c2431;text-align:right;white-space:nowrap}
.up{color:var(--up)}.dn{color:var(--down)}.fl{color:var(--muted)}
.b{display:inline-block;font-size:10px;font-weight:700;border-radius:4px;padding:1.5px 6px;margin-right:6px}
.b.s{background:rgba(255,178,36,.16);color:var(--amber)}
.b.g{background:rgba(45,212,191,.13);color:var(--teal)}
.b.f{background:rgba(192,132,252,.14);color:var(--violet)}
.b.m{background:rgba(138,148,166,.15);color:var(--muted)}
.wb{display:inline-block;height:8px;border-radius:4px;background:var(--amber);vertical-align:middle;margin-right:6px}
footer{margin-top:14px;color:var(--faint);font-size:11px;line-height:1.7}
@media(max-width:760px){body{padding:10px 8px 30px}.hide-m{display:none}}
</style></head><body>
<div style="margin-bottom:8px"><a href="../jp/index.html">← 스크리너로</a></div>
<h1>시그널 <span>성과 분석</span></h1>
<div class="meta">생성 __GEN__ · 시그널에 걸린 종목이 이후 실제로 어떻게 움직였는지 (거래대금 하한 적용, 시장평균 대비)</div>
<div class="tabs" id="mt"></div>
<div class="tabs htabs" id="ht"></div>
<div id="body"></div>
<footer>승률 = 수익률 &gt; 0 비율 · 시장대비 = 같은 기간 유니버스 평균수익 차감(초과수익) ·
표본 = (시그널 발생 종목 × 관측일) 누적 · 스냅샷은 매 영업일 종가판에서 자동 축적 ·
과거 성과는 미래 수익을 보장하지 않으며 참고 자료입니다.</footer>
<script>
const R=__RESULTS__;
const H=[["1","+1일"],["5","+5일"],["20","+20일"]];
let mkt=Object.keys(R)[0], hz="1";
const $=s=>document.querySelector(s);
const pc=v=>v==null?'—':`<span class="${v>0?'up':v<0?'dn':'fl'}">${v>0?'+':''}${v.toFixed(2)}%</span>`;
function tabs(){
  $('#mt').innerHTML=Object.keys(R).map(m=>`<div class="tab ${m===mkt?'on':''}" data-m="${m}">${R[m].label} <span style="color:var(--faint);font-size:11px">${R[m].n_days}일</span></div>`).join('');
  $('#ht').innerHTML=H.map(([k,l])=>{
    const d=R[mkt].horizon_days[k]||0;
    return `<div class="tab ${k===hz?'on':''}" data-h="${k}">${l} <span style="color:var(--faint);font-size:11px">${d}회 관측</span></div>`}).join('');
}
function render(){
  tabs();
  const M=R[mkt];
  if(M.n_days<2){
    $('#body').innerHTML=`<div class="note"><b>데이터 축적 중입니다 (현재 ${M.n_days}일)</b><br>
    매 영업일 종가판 실행마다 스냅샷이 자동으로 쌓입니다.<br>
    · 스냅샷 2일차 → <b>+1일 수익률</b> 첫 집계 · 6일차 → +5일 · 21일차 → +20일<br>
    한두 달 뒤에는 "어떤 시그널이 실제로 먹혔는가"를 표본 수백~수천 건으로 평가할 수 있습니다.</div>`;
    return;
  }
  const rows=Object.entries(M.signals).map(([k,v])=>({k,name:v.name,grp:v.grp,st:v[hz]}))
    .filter(r=>r.st).sort((a,b)=>b.st.excess-a.st.excess);
  if(!rows.length){
    $('#body').innerHTML=`<div class="note">이 구간(+${hz}일)은 아직 관측치가 없습니다 — 스냅샷 ${+hz+1}일 이상 필요.</div>`;
    return;
  }
  $('#body').innerHTML=`<table><thead><tr>
  <th class="l">시그널</th><th>표본</th><th class="l">승률</th><th>평균수익</th>
  <th class="hide-m">중앙값</th><th>시장대비</th><th class="hide-m">최고/최저</th></tr></thead><tbody>`+
  rows.map(r=>`<tr><td class="l"><span class="b ${r.grp}">${r.name}</span></td>
  <td class="num">${r.st.n.toLocaleString()}</td>
  <td class="l num"><span class="wb" style="width:${Math.max(4,r.st.win)*0.9}px"></span>${r.st.win.toFixed(1)}%</td>
  <td class="num">${pc(r.st.avg)}</td>
  <td class="num hide-m">${pc(r.st.med)}</td>
  <td class="num">${pc(r.st.excess)}</td>
  <td class="num hide-m fl">+${r.st.best}% / ${r.st.worst}%</td></tr>`).join('')+`</tbody></table>
  <div class="note" style="margin-top:10px">읽는 법: <b>시장대비</b>가 +면 그 시그널이 시장평균보다 잘 갔다는 뜻입니다.
  표본이 적을 때(수십 건 이하)는 우연일 수 있으니 표본 수를 함께 보세요.</div>`;
}
$('#mt').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){mkt=t.dataset.m;render()}});
$('#ht').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){hz=t.dataset.h;render()}});
render();
</script></body></html>"""


def main():
    print("=" * 60)
    print("백테스트 실행", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    results = {}
    grp_of = {c: g for c, _n, g in SIGNALS} | {c: g for c, _n, g in GROUPS}
    for m in ("jp", "kr", "us"):
        r = analyze(m)
        for c, v in r["signals"].items():
            v["grp"] = grp_of.get(c, "m")
        r["label"] = MKT_LABEL[m]
        results[m] = r
        print(f"  [{m}] 유효 스냅샷 {r['n_days']}일 / 관측 {r['horizon_days'] or '-'}")

    out = OUT / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    gen = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    payload = json.dumps(results, ensure_ascii=False).replace("</", "<\\/")
    (out / "index.html").write_text(
        HTML.replace("__GEN__", gen).replace("__RESULTS__", payload), encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"  완료 → {out}/index.html")


if __name__ == "__main__":
    main()
