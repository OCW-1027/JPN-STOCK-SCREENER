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

import i18n

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


HTML = """<!DOCTYPE html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__PAGE_TITLE__ — __GEN__</title><style>
:root{--bg:#0f141c;--surface:#171e29;--surface2:#1d2634;--line:#26303f;--text:#e9eef6;
--muted:#8a94a6;--faint:#5b6572;--up:#ff4f5e;--down:#3f8cff;--amber:#ffb224;--teal:#2dd4bf;--violet:#c084fc}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Pretendard','Malgun Gothic','Yu Gothic UI','Noto Sans JP',sans-serif;
font-size:13px;line-height:1.5;padding:14px 16px 50px}
.num{font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
a{color:var(--amber);text-decoration:none}
.topbar{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.langbtn{margin-left:auto;padding:5px 12px;border:1px solid var(--line);border-radius:999px;
background:var(--surface);color:var(--faint);font-weight:600;font-size:12.5px}
.langbtn:hover{color:var(--text)}
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
<div class="topbar">
  <a href="__BACK_HREF__">__BACK__</a>
  <a class="langbtn" href="__LANG_HREF__">__OTHER_LANG__</a>
</div>
<h1>__TITLE__</h1>
<div class="meta">__GEN_LABEL__ __GEN__ · __LEAD__</div>
<div class="tabs" id="mt"></div>
<div class="tabs htabs" id="ht"></div>
<div id="body"></div>
<footer>__FOOTER__</footer>
<script>
const R=__RESULTS__;
const T=__T__;
const H=[["1",T.h1],["5",T.h5],["20",T.h20]];
let mkt=Object.keys(R)[0], hz="1";
const $=s=>document.querySelector(s);
const pc=v=>v==null?'—':`<span class="${v>0?'up':v<0?'dn':'fl'}">${v>0?'+':''}${v.toFixed(2)}%</span>`;
function tabs(){
  $('#mt').innerHTML=Object.keys(R).map(m=>`<div class="tab ${m===mkt?'on':''}" data-m="${m}">${R[m].label} <span style="color:var(--faint);font-size:11px">${R[m].n_days}${T.days}</span></div>`).join('');
  $('#ht').innerHTML=H.map(([k,l])=>{
    const d=R[mkt].horizon_days[k]||0;
    return `<div class="tab ${k===hz?'on':''}" data-h="${k}">${l} <span style="color:var(--faint);font-size:11px">${d}${T.obs}</span></div>`}).join('');
}
function render(){
  tabs();
  const M=R[mkt];
  if(M.n_days<2){
    $('#body').innerHTML=`<div class="note"><b>${T.acc_title.replace('{n}',M.n_days)}</b><br>${T.acc_body}</div>`;
    return;
  }
  const rows=Object.entries(M.signals).map(([k,v])=>({k,name:v.name,grp:v.grp,st:v[hz]}))
    .filter(r=>r.st).sort((a,b)=>b.st.excess-a.st.excess);
  if(!rows.length){
    $('#body').innerHTML=`<div class="note">${T.none.replace('{h}',hz).replace('{need}',(+hz)+1)}</div>`;
    return;
  }
  $('#body').innerHTML=`<table><thead><tr>
  <th class="l">${T.col_sig}</th><th>${T.col_n}</th><th class="l">${T.col_win}</th><th>${T.col_avg}</th>
  <th class="hide-m">${T.col_med}</th><th>${T.col_exc}</th><th class="hide-m">${T.col_minmax}</th></tr></thead><tbody>`+
  rows.map(r=>`<tr><td class="l"><span class="b ${r.grp}">${r.name}</span></td>
  <td class="num">${r.st.n.toLocaleString()}</td>
  <td class="l num"><span class="wb" style="width:${Math.max(4,r.st.win)*0.9}px"></span>${r.st.win.toFixed(1)}%</td>
  <td class="num">${pc(r.st.avg)}</td>
  <td class="num hide-m">${pc(r.st.med)}</td>
  <td class="num">${pc(r.st.excess)}</td>
  <td class="num hide-m fl">+${r.st.best}% / ${r.st.worst}%</td></tr>`).join('')+`</tbody></table>
  <div class="note" style="margin-top:10px">${T.howto}</div>`;
}
$('#mt').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){mkt=t.dataset.m;render()}});
$('#ht').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){hz=t.dataset.h;render()}});
render();
</script></body></html>"""


def main():
    print("=" * 60)
    print("백테스트 실행", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    base = {}
    grp_of = {c: g for c, _n, g in SIGNALS} | {c: g for c, _n, g in GROUPS}
    for m in ("jp", "kr", "us"):
        r = analyze(m)
        for c, v in r["signals"].items():
            v["grp"] = grp_of.get(c, "m")
        base[m] = r
        print(f"  [{m}] 유효 스냅샷 {r['n_days']}일 / 관측 {r['horizon_days'] or '-'}")

    gen = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    for lang in ("ko", "ja"):
        L = i18n.BT_UI[lang]
        idx = 0 if lang == "ko" else 1
        results = {}
        for m, r in base.items():
            rr = json.loads(json.dumps(r))          # 깊은 복사
            rr["label"] = L["markets"][m]
            for c, v in rr["signals"].items():
                v["name"] = i18n.SIGNAL_I18N.get(c, (v["name"], v["name"]))[idx]
            results[m] = rr

        out = (OUT / "backtest") if lang == "ko" else (OUT / "ja" / "backtest")
        out.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(results, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        tpl = json.dumps(L, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        html = HTML
        for k, v in {
            "__LANG__": lang, "__PAGE_TITLE__": L["page_title"], "__TITLE__": L["title"],
            "__BACK__": L["back"], "__BACK_HREF__": ("../jp/index.html" if lang == "ko"
                                                     else "../jp/index.html"),
            "__LANG_HREF__": ("../ja/backtest/index.html" if lang == "ko"
                              else "../../backtest/index.html"),
            "__OTHER_LANG__": L["other_lang"], "__GEN_LABEL__": L["gen"], "__GEN__": gen,
            "__LEAD__": L["lead"], "__FOOTER__": L["foot"],
        }.items():
            html = html.replace(k, v)
        html = html.replace("__RESULTS__", payload).replace("__T__", tpl)
        (out / "index.html").write_text(html, encoding="utf-8")
        if lang == "ko":
            (out / "results.json").write_text(
                json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [{lang}] 완료 → {out}/index.html")


if __name__ == "__main__":
    main()
