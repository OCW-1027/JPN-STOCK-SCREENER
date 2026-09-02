# -*- coding: utf-8 -*-
"""
ranking.py — 거래대금 상위 100위 순위 추이
===========================================
history/{jp,kr,us}/*.csv.gz 스냅샷에서 날짜별 거래대금 순위를 뽑아
site/ranking/(ja/ranking/) 페이지와 data.json을 만든다.

- 세로축 = 순위(1위가 위), 가로축 = 날짜. 순위가 올라갈수록 선이 위로.
- 최신일 상위 20종목만 색선으로 강조, 나머지는 흐린 회색.
- 종목 클릭 → 해당 선만 강조. 표에서 순위 변동(▲▼)도 함께 표시.
- 스냅샷이 2일 미만이면 "축적 중" 안내를 띄운다.
"""
import glob
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

TOP_N = 100          # 순위 집계 범위
HILITE = 20          # 색선으로 강조할 상위 종목 수
KEEP_DAYS = 60       # 그래프에 표시할 최근 영업일 수
DIV = {"jp": 1e8, "kr": 1e8, "us": 1e6}          # 거래대금 표시 단위 (억엔/억원/$M)
MCAP_DIV = {"jp": 1e8, "kr": 1e8, "us": 1e9}     # 시총 표시 단위 (억엔/억원/$B)
METRICS = {"value": "Value.Traded", "mcap": "market_cap_basic"}


def load_market(m, metric="value"):
    """날짜별 상위 TOP_N 순위 테이블. metric: value(거래대금) | mcap(시가총액)"""
    col = METRICS[metric]
    files = sorted(glob.glob(str(BASE / "history" / m / "*.csv.gz")))[-KEEP_DAYS:]
    dates, per_day, names = [], [], {}
    prev_close = None
    for f in files:
        date = Path(f).name.replace(".csv.gz", "")
        try:
            df = pd.read_csv(f, compression="gzip", dtype={"code": str})
        except Exception:
            continue
        if col not in df.columns or "code" not in df.columns:
            continue
        df = df.dropna(subset=["code", col]).drop_duplicates(subset="code")
        # 휴장일(가격이 전일과 거의 동일) 제거
        if prev_close is not None and "close" in df.columns:
            cur = df.set_index("code")["close"]
            common = cur.index.intersection(prev_close.index)
            if len(common) > 100 and (cur.loc[common] == prev_close.loc[common]).mean() > 0.97:
                continue
        if "close" in df.columns:
            prev_close = df.set_index("code")["close"]

        top = df.nlargest(TOP_N, col).reset_index(drop=True)
        namecol = "disp_name" if "disp_name" in top.columns else (
            "m_name" if "m_name" in top.columns else "description")
        day = {}
        for rank, row in enumerate(top.itertuples(index=False), start=1):
            code = str(getattr(row, "code"))
            day[code] = (rank, 0.0)
            nm = getattr(row, namecol, None) if namecol in top.columns else None
            if isinstance(nm, str) and nm.strip():
                names.setdefault(code, nm.strip())
        # Value.Traded 는 컬럼명에 점이 있어 itertuples 접근이 어려움 → 직접 매핑
        vals = dict(zip(top["code"].astype(str), top[col].astype(float)))
        day = {c: (r, vals.get(c, 0.0)) for c, (r, _v) in day.items()}
        dates.append(date)
        per_day.append(day)

    codes = sorted({c for d in per_day for c in d})
    series = {}
    for c in codes:
        ranks = [d.get(c, (None, None))[0] for d in per_day]
        values = [d.get(c, (None, None))[1] for d in per_day]
        series[c] = {"name": names.get(c, c), "ranks": ranks, "values": values}
    return dates, series


def build(m, metric="value"):
    dates, series = load_market(m, metric)
    if not dates:
        return {"dates": [], "series": {}, "latest": [], "n_days": 0}
    last = len(dates) - 1
    latest = sorted(
        [(c, s["ranks"][last]) for c, s in series.items() if s["ranks"][last]],
        key=lambda x: x[1])
    order = [c for c, _ in latest]
    # 변동 계산 (전일 대비)
    rows = []
    for c in order:
        s = series[c]
        cur = s["ranks"][last]
        prev = s["ranks"][last - 1] if last > 0 else None
        rows.append({
            "code": c, "name": s["name"], "rank": cur,
            "prev": prev, "delta": (prev - cur) if (prev and cur) else None,
            "value": round((s["values"][last] or 0) /
                           (DIV[m] if metric == "value" else MCAP_DIV[m]), 1),
            "chg": (round((s["values"][last] / s["values"][last - 1] - 1) * 100, 1)
                    if (last > 0 and s["values"][last] and s["values"][last - 1]) else None),
            "best": min([r for r in s["ranks"] if r], default=None),
        })
    return {"dates": dates, "series": series, "rows": rows,
            "hilite": order[:HILITE], "n_days": len(dates)}


HTML = """<!DOCTYPE html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__PAGE_TITLE__ — __GEN__</title><style>
:root{--bg:#0f141c;--surface:#171e29;--surface2:#1d2634;--line:#26303f;--text:#e9eef6;
--muted:#8a94a6;--faint:#5b6572;--up:#ff4f5e;--down:#3f8cff;--amber:#ffb224;--teal:#2dd4bf}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Pretendard','Malgun Gothic','Yu Gothic UI','Noto Sans JP',sans-serif;
font-size:13px;line-height:1.5;padding:14px 16px 50px;overflow-x:hidden;max-width:100vw}
.num{font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
a{color:var(--amber);text-decoration:none}
.topbar{display:flex;align-items:center;gap:9px;margin-bottom:8px;flex-wrap:wrap}
.langbtn{margin-left:auto;padding:5px 12px;border:1px solid var(--line);border-radius:999px;
background:var(--surface);color:var(--faint);font-weight:600;font-size:12.5px}
h1{font-size:18px;font-weight:800;margin-bottom:4px}h1 span{color:var(--amber)}
.meta{color:var(--muted);font-size:12px;margin-bottom:10px}
.tabs{display:flex;gap:5px;margin:10px 0;flex-wrap:wrap}
.tab{padding:7px 13px;border:1px solid var(--line);border-radius:8px;background:var(--surface);
cursor:pointer;font-weight:600;color:var(--muted);user-select:none}
.tab.on{color:var(--text);border-color:var(--amber);background:var(--surface2)}
.note{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
color:var(--muted);margin:10px 0;line-height:1.8}
.note b{color:var(--text)}
.chartbox{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 6px 4px;
overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;
width:100%;max-width:100%;contain:paint}
.chartinner{display:inline-block;min-width:min-content}
.chartbox svg{display:block}
.scrollhint{color:var(--faint);font-size:11px;margin:4px 2px 0}
.tablebox{width:100%;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;
border-radius:10px;margin-top:12px}
.tablebox table{margin-top:0}
svg{display:block}
.gl{stroke:#232d3c;stroke-width:1}
.axis{fill:var(--faint);font-size:10px;font-family:ui-monospace,Consolas,monospace}
.ln{fill:none;stroke-width:1.6;opacity:.85;cursor:pointer}
.ln.dim{stroke:#2a3444;stroke-width:1;opacity:.5}
.ln.sel{stroke-width:3.2;opacity:1}
.lbl{font-size:10.5px;cursor:pointer}
.dot{cursor:pointer}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line);
border-radius:10px;overflow:hidden;margin-top:12px}
th{background:var(--surface2);color:var(--muted);font-size:11.5px;font-weight:600;text-align:right;
padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th.l,td.l{text-align:left}
td{padding:6px 10px;border-bottom:1px solid #1c2431;text-align:right;white-space:nowrap}
tbody tr{cursor:pointer}tbody tr:hover td{background:#1b2433}
tbody tr.sel td{background:#243149}
.up{color:var(--up)}.dn{color:var(--down)}.fl{color:var(--muted)}
footer{margin-top:14px;color:var(--faint);font-size:11px;line-height:1.7}
@media(max-width:760px){
  body{padding:10px 8px 30px;overflow-x:hidden}
  .hide-m{display:none}
  table{font-size:12px}
  td,th{padding:6px 5px}
  td:nth-child(3){white-space:normal;min-width:90px;max-width:120px}
  .topbar,.tabs{gap:5px}
  .tab{padding:6px 10px;font-size:12.5px}
}
__BTC_CSS__
</style></head><body>
<div class="topbar">
  <a href="__BACK_HREF__">__BACK__</a>
  <a class="langbtn" style="margin-left:0;color:var(--amber);border-color:rgba(255,178,36,.4)"
     href="../backtest/index.html">__BT__</a>
  __BTC_LINK__
  <a class="langbtn" href="__LANG_HREF__">__OTHER_LANG__</a>
</div>
<h1>__TITLE__</h1>
<div class="meta">__GEN_LABEL__ __GEN__ · __LEAD__</div>
<div class="tabs" id="mt"></div>
<div class="tabs" id="mtx"></div>
<div id="body"></div>
<footer>__FOOTER__</footer>
<script>
const R=__DATA__, T=__T__;
let mkt=Object.keys(R)[0], metric="value", sel=null;
const $=s=>document.querySelector(s);
const COLORS=['#ff4f5e','#ffb224','#2dd4bf','#3f8cff','#c084fc','#60cdff','#f472b6','#a3e635',
'#fb923c','#38bdf8','#f87171','#34d399','#e879f9','#facc15','#22d3ee','#fca5a5','#86efac',
'#93c5fd','#fdba74','#d8b4fe'];

function tabs(){
  $('#mt').innerHTML=Object.keys(R).map(m=>
    `<div class="tab ${m===mkt?'on':''}" data-m="${m}">${T.markets[m]} <span style="color:var(--faint);font-size:11px">${R[m][metric].n_days}${T.days}</span></div>`).join('');
  $('#mtx').innerHTML=[['value',T.m_value],['mcap',T.m_mcap]].map(([k,l])=>
    `<div class="tab ${k===metric?'on':''}" data-x="${k}" style="${k===metric?'border-color:var(--teal)':''}">${l}</div>`).join('');
}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}

function chart(M){
  const d=M.dates, n=d.length;
  if(n<2) return '';
  const narrow = window.innerWidth < 760;
  const per = narrow ? 46 : 74, RrW = narrow ? 96 : 132;
  const W=Math.max(narrow?520:680, n*per+RrW+38), H=narrow?430:540,
        L=narrow?32:44, Rr=RrW, Tp=16, Bt=34;
  const iw=W-L-Rr, ih=H-Tp-Bt;
  const x=i=>L+(n===1?iw/2:iw*i/(n-1));
  // 상위권을 넓게: sqrt 스케일 (1~100위 → 상단이 더 벌어짐)
  const y=r=>Tp+ih*(Math.sqrt(r-1)/Math.sqrt(99));
  let s=`<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" style="max-width:none">`;
  [1,3,5,10,20,30,50,70,100].forEach(r=>{
    s+=`<line class="gl" x1="${L}" y1="${y(r)}" x2="${L+iw}" y2="${y(r)}"/>`;
    s+=`<text class="axis" x="${L-8}" y="${y(r)+3}" text-anchor="end">${r}</text>`;});
  d.forEach((dt,i)=>{ s+=`<text class="axis" x="${x(i)}" y="${H-12}" text-anchor="middle">${dt.slice(5)}</text>`;});
  const hi=M.hilite||[]; const labels=[];
  // 흐린 선 먼저
  Object.entries(M.series).forEach(([c,v])=>{
    if(hi.includes(c))return;
    const pts=v.ranks.map((r,i)=>r?`${x(i)},${y(r)}`:null).filter(Boolean);
    if(pts.length>1) s+=`<polyline class="ln dim ${sel===c?'sel':''}" data-c="${c}" points="${pts.join(' ')}"/>`;
  });
  hi.forEach((c,k)=>{
    const v=M.series[c]; const col=COLORS[k%COLORS.length];
    const pts=v.ranks.map((r,i)=>r?`${x(i)},${y(r)}`:null).filter(Boolean);
    if(pts.length<1)return;
    if(pts.length>1) s+=`<polyline class="ln ${sel&&sel!==c?'dim':''} ${sel===c?'sel':''}" data-c="${c}" points="${pts.join(' ')}" stroke="${col}"/>`;
    v.ranks.forEach((r,i)=>{ if(r) s+=`<circle class="dot" data-c="${c}" cx="${x(i)}" cy="${y(r)}" r="${sel===c?3.6:2.4}" fill="${col}"><title>${esc(v.name)} ${d[i]} ${r}${T.rank_unit}</title></circle>`;});
    const lastR=[...v.ranks].reverse().find(r=>r);
    if(lastR) labels.push({c, col, r:lastR, name:v.name, i:v.ranks.lastIndexOf(lastR)});
  });
  // 라벨 세로 겹침 제거: 위에서부터 최소 간격 확보
  labels.sort((a,b)=>a.r-b.r);
  let prevY=-99;
  labels.forEach(o=>{
    let ly=Math.max(y(o.r)+3.5, prevY+12);
    prevY=ly;
    s+=`<line class="gl" x1="${x(o.i)}" y1="${y(o.r)}" x2="${x(o.i)+5}" y2="${ly-3.5}" stroke="${o.col}" opacity=".4"/>`;
    s+=`<text class="lbl" data-c="${o.c}" x="${x(o.i)+7}" y="${ly}" fill="${o.col}">${o.r}. ${esc(o.name).slice(0,10)}</text>`;
  });
  return s+'</svg>';
}

function table(M){
  const rows=(M.rows||[]).slice(0,100);
  return `<div class="tablebox"><table><thead><tr><th class="l">${T.col_rank}</th><th class="l">${T.col_code}</th>
  <th class="l">${T.col_name}</th><th>${T.col_delta}</th><th>${metric==='value'?T.col_value:T.col_mcap}</th><th class="hide-m">${T.col_chg}</th>
  <th class="hide-m">${T.col_best}</th></tr></thead><tbody>`+
  rows.map(r=>{
    const dl=r.delta==null?`<span class="fl">${T.new_in}</span>`
      :r.delta>0?`<span class="up">▲${r.delta}</span>`
      :r.delta<0?`<span class="dn">▼${-r.delta}</span>`:`<span class="fl">—</span>`;
    return `<tr data-c="${r.code}" class="${sel===r.code?'sel':''}">
      <td class="l num">${r.rank}</td><td class="l num">${esc(r.code)}</td>
      <td class="l">${esc(r.name)}</td><td class="num">${dl}</td>
      <td class="num">${r.value.toLocaleString()}</td>
      <td class="num hide-m">${r.chg==null?'<span class="fl">—</span>':(r.chg>0?`<span class="up">+${r.chg}%</span>`:r.chg<0?`<span class="dn">${r.chg}%</span>`:'<span class="fl">0%</span>')}</td>
      
      <td class="num hide-m fl">${r.best||'—'}</td></tr>`;
  }).join('')+'</tbody></table></div>';
}

function render(){
  tabs();
  const M=R[mkt][metric];
  if(!M||M.n_days<2){
    $('#body').innerHTML=`<div class="note"><b>${T.acc_title.replace('{n}',M?M.n_days:0)}</b><br>${T.acc_body}</div>`;
    return;
  }
  const hint = window.innerWidth<760 ? `<div class="scrollhint">${T.scroll_hint||''}</div>` : '';
  $('#body').innerHTML=`<div class="chartbox"><div class="chartinner">${chart(M)}</div></div>${hint}
    <div class="note" style="margin-top:10px">${T.howto}</div>${table(M)}`;
  document.querySelectorAll('[data-c]').forEach(el=>el.addEventListener('click',()=>{
    sel = sel===el.dataset.c ? null : el.dataset.c; render();
  }));
}
$('#mt').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){mkt=t.dataset.m;sel=null;render()}});
$('#mtx').addEventListener('click',e=>{const t=e.target.closest('.tab');if(t){metric=t.dataset.x;sel=null;render()}});
render();
</script>__BTC_JS__
</body></html>"""


def main():
    print("=" * 60)
    print("거래대금 순위 추이", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
    print("=" * 60)
    base = {}
    for m in ("jp", "kr", "us"):
        base[m] = {}
        for metric in ("value", "mcap"):
            b = build(m, metric)
            base[m][metric] = b
            tag = "대금" if metric == "value" else "시총"
            print(f"  [{m}] {tag}: 스냅샷 {b['n_days']}일" +
                  (f" | 1위 {b['rows'][0]['name'][:14]}" if b.get("rows") else ""))

    gen = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    for lang in ("ko", "ja"):
        L = i18n.RANK_UI[lang]
        payload = json.dumps(base, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        tpl = json.dumps(L, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        html = HTML
        for k, v in {
            "__LANG__": lang, "__PAGE_TITLE__": L["page_title"], "__TITLE__": L["title"],
            "__BACK__": L["back"], "__BACK_HREF__": "../jp/index.html",
            "__LANG_HREF__": ("../ja/ranking/index.html" if lang == "ko"
                              else "../../ranking/index.html"),
            "__OTHER_LANG__": L["other_lang"], "__GEN_LABEL__": L["gen"], "__GEN__": gen,
            "__LEAD__": L["lead"], "__FOOTER__": L["foot"],
            "__BT__": i18n.UI[lang]["nav_bt"],
            "__BTC_LINK__": i18n.btc_link(lang, "langbtn btc"),
            "__BTC_CSS__": i18n.BTC_CSS, "__BTC_JS__": i18n.BTC_JS,
        }.items():
            html = html.replace(k, v)
        html = html.replace("__DATA__", payload).replace("__T__", tpl)
        out = (OUT / "ranking") if lang == "ko" else (OUT / "ja" / "ranking")
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")
        if lang == "ko":
            (out / "data.json").write_text(
                json.dumps({m: {k: {"dates": v["dates"], "rows": v.get("rows", [])}
                                for k, v in mv.items()}
                            for m, mv in base.items()}, ensure_ascii=False),
                encoding="utf-8")
        print(f"  [{lang}] 완료 → {out}/index.html")


if __name__ == "__main__":
    main()
