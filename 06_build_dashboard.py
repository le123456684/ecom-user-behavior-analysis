# -*- coding: utf-8 -*-
"""06_build_dashboard.py — 生成自包含交互看板 HTML（v2 修正去重口径）"""
import sys, io, os, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "results", "dashboard_data.json")
OUT = os.path.join(BASE, "dashboard.html")

cube = json.load(open(DATA, encoding="utf-8"))
D = json.dumps(cube, ensure_ascii=False, separators=(",", ":"))

# 用于看板里"口径纠错演示"的两个数字
p_all = cube["platform"]["all"]
uv_true = p_all["pv"]["u"]
buy_true = p_all["buy"]["u"]
uv_wrong = sum(v["pv"]["u"] for v in cube["daily"].values())
conv_true = buy_true / uv_true * 100
conv_wrong = buy_true / uv_wrong * 100

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>电商用户行为 · 核心指标看板</title>
<style>
  :root {{ --pri:#1F3A63; --sec:#2F5BD7; --acc:#B7791F; --red:#B4453C;
           --grn:#2F6B4F; --grey:#6B7280; --bd:#E3E9F3; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:22px; background:#EEF1F6; color:#222;
         font-family:"Microsoft YaHei","Segoe UI",sans-serif; font-size:13px; }}
  .wrap {{ max-width:1180px; margin:0 auto; }}
  header {{ display:flex; align-items:baseline; justify-content:space-between;
            margin-bottom:16px; flex-wrap:wrap; gap:8px; }}
  h1 {{ font-size:20px; color:var(--pri); margin:0; }}
  .hsub {{ color:var(--grey); font-size:12px; }}
  .bar {{ background:#fff; border-radius:6px; padding:13px 18px; margin-bottom:14px;
          display:flex; gap:22px; align-items:center; flex-wrap:wrap;
          box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .fld {{ display:flex; align-items:center; gap:7px; font-size:12.5px; }}
  .fld label {{ color:var(--grey); }}
  select {{ padding:5px 9px; border:1px solid var(--bd); border-radius:4px;
            background:#fff; color:#222; cursor:pointer; font-family:inherit; font-size:12.5px; }}
  .presets {{ display:flex; gap:6px; }}
  .presets button {{ padding:5px 11px; border:1px solid var(--bd); background:#fff;
                     border-radius:4px; cursor:pointer; font-family:inherit;
                     font-size:12px; color:#445; }}
  .presets button:hover {{ border-color:var(--sec); color:var(--sec); }}
  .presets button.on {{ background:var(--pri); color:#fff; border-color:var(--pri); }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:13px; margin-bottom:14px; }}
  .kpi {{ background:#fff; border-radius:6px; padding:15px 17px; border-left:3px solid var(--sec);
          box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .kpi .v {{ font-size:24px; font-weight:700; color:var(--pri); line-height:1.2;
             font-variant-numeric:tabular-nums; }}
  .kpi .l {{ font-size:11.5px; color:var(--grey); margin-top:3px; }}
  .kpi .d {{ font-size:10.5px; color:#94A3B8; margin-top:1px; }}
  .kpi.w {{ border-left-color:var(--red); }} .kpi.w .v {{ color:var(--red); }}
  .kpi.g {{ border-left-color:var(--grn); }} .kpi.g .v {{ color:var(--grn); }}
  .row {{ display:grid; grid-template-columns:1fr 1fr; gap:13px; margin-bottom:13px; }}
  .card {{ background:#fff; border-radius:6px; padding:16px 18px;
           box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .card h2 {{ font-size:13.5px; color:var(--pri); margin:0 0 3px; font-weight:700; }}
  .card .cap {{ font-size:11px; color:var(--grey); margin-bottom:11px; }}
  .full {{ grid-column:1/-1; }}
  .note {{ background:#FFF8E7; border-left:3px solid var(--acc); padding:11px 15px;
           border-radius:0 4px 4px 0; font-size:11.5px; color:#6B5320; margin-top:12px;
           line-height:1.7; }}
  .trap {{ background:#FDF2F1; border-left:3px solid var(--red); padding:13px 17px;
           border-radius:0 4px 4px 0; font-size:12px; color:#6B2B24; margin-bottom:14px;
           line-height:1.8; }}
  .trap b {{ color:var(--red); }}
  .cmp {{ display:inline-block; background:#fff; border:1px solid #F0C9C5; border-radius:4px;
          padding:2px 9px; margin:0 4px; font-variant-numeric:tabular-nums; }}
  svg {{ display:block; width:100%; height:auto; }}
  table {{ border-collapse:collapse; width:100%; font-size:11.5px; }}
  th {{ background:#F4F6FA; color:#445; padding:6px 8px; text-align:left;
        font-weight:600; border-bottom:1px solid var(--bd); }}
  td {{ padding:5.5px 8px; border-bottom:1px solid #F0F3F8;
        font-variant-numeric:tabular-nums; }}
  tr:hover td {{ background:#FAFBFD; }}
  .r {{ text-align:right; }} .red {{ color:var(--red); font-weight:700; }}
  .grn {{ color:var(--grn); font-weight:700; }}
  .pill {{ display:inline-block; padding:1px 7px; border-radius:8px; font-size:10.5px; }}
  .pill.r {{ background:#FDECEC; color:var(--red); }}
  .pill.g {{ background:#E9F5EF; color:var(--grn); }}
  footer {{ text-align:center; color:#94A3B8; font-size:11px; margin-top:20px; }}
  @media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }}
                              .row {{ grid-template-columns:1fr; }} }}
</style></head><body>
<div class="wrap">

<header>
  <h1>电商用户行为 · 核心指标看板</h1>
  <div class="hsub">数据范围 <span id="rangeTxt"></span>　|　口径：区间去重用户数</div>
</header>

<div class="bar">
  <div class="fld">
    <label>时间范围</label>
    <div class="presets" id="presets">
      <button data-p="all" class="on">全部 30 天</button>
      <button data-p="first">前 15 天</button>
      <button data-p="last">后 15 天</button>
    </div>
  </div>
  <div class="fld">
    <label>类目</label>
    <select id="catSel"><option value="all">全部类目</option></select>
  </div>
  <div class="fld" style="margin-left:auto;color:#94A3B8;font-size:11.5px">
    筛选后所有指标实时重算
  </div>
</div>

<div class="trap">
  <b>⚠ 口径纠错示例 · 为什么不能把每日 UV 相加</b><br>
  若把 30 天的「每日去重访客数」直接相加，会得到 <span class="cmp">{uv_wrong:,}</span>（用户日/人次），
  而真实的区间独立访客只有 <span class="cmp">{uv_true:,}</span> 人——<b>虚高 {uv_wrong/uv_true:.2f} 倍</b>。<br>
  连带影响：转化率会被算成 <span class="cmp">{conv_wrong:.2f}%</span>，而真实值是
  <span class="cmp"><b>{conv_true:.2f}%</b></span>。<br>
  <span style="color:#8A5B6B">本看板已对每个区间预先精确计算去重人数，不做任何简单相加。</span>
</div>

<div class="grid">
  <div class="kpi"><div class="v" id="k1">-</div><div class="l">访客数 UV</div><div class="d" id="k1d"></div></div>
  <div class="kpi"><div class="v" id="k2">-</div><div class="l">浏览量 PV</div><div class="d" id="k2d"></div></div>
  <div class="kpi"><div class="v" id="k3">-</div><div class="l">人均浏览深度</div><div class="d">PV ÷ UV</div></div>
  <div class="kpi w" id="k4box"><div class="v" id="k4">-</div><div class="l">购买转化率</div><div class="d">购买人数 ÷ 浏览人数</div></div>
</div>

<div class="row">
  <div class="card full">
    <h2>流量趋势</h2>
    <div class="cap">蓝线 PV（左轴，可加总）· 橙线 UV（右轴，每日去重，不可跨日相加）</div>
    <div id="trend"></div>
  </div>
</div>

<div class="row">
  <div class="card">
    <h2>转化漏斗</h2>
    <div class="cap" id="funnelCap"></div>
    <div id="funnel"></div>
  </div>
  <div class="card">
    <h2>全天时段分布</h2>
    <div class="cap">各时段浏览量占比（北京时间），红柱为峰值时段</div>
    <div id="hourly"></div>
  </div>
</div>

<div class="row">
  <div class="card full">
    <h2>类目流量与转化率对比</h2>
    <div class="cap">柱为流量占比，橙线为转化率；红色柱 = 高流量低转化机会点</div>
    <div id="catChart"></div>
    <table id="catTable" style="margin-top:12px"></table>
  </div>
</div>

<div class="note" id="caliberNote"></div>

<footer>数据口径详见指标字典　|　本看板为静态数据驱动的交互演示</footer>
</div>

<script>
const CUBE = {D};

const BEH = ["pv","fav","cart","buy"];
const BNAME = {{pv:"浏览",fav:"收藏",cart:"加购",buy:"购买"}};
const CP = ["#1F3A63","#3A66A8","#2F5BD7","#B7791F"];

let curRange = "all";
let catSel = "all";

CUBE.categories.forEach(([cid,name]) => {{
  const o = document.createElement("option");
  o.value = cid; o.textContent = name;
  document.getElementById("catSel").appendChild(o);
}});

function fmt(n) {{ return (n||0).toLocaleString("zh-CN"); }}
function pct(a,b) {{ return b ? (a/b*100) : 0; }}

// 取当前筛选下的行为人数（区间级，精确去重）
function stats() {{
  if (catSel === "all") return CUBE.platform[curRange];
  const c = CUBE.category[curRange][catSel] || {{}};
  return {{pv:{{u:c.pv||0,c:c.pvC||0}}, fav:{{u:c.fav||0,c:c.fav||0}},
           cart:{{u:c.cart||0,c:c.cart||0}}, buy:{{u:c.buy||0,c:c.buy||0}}}};
}}

// ---------- KPI ----------
function renderKPI() {{
  const s = stats();
  const uv = s.pv.u, pv = s.pv.c, buy = s.buy.u;
  const conv = pct(buy, uv);
  document.getElementById("k1").textContent = fmt(uv);
  document.getElementById("k2").textContent = fmt(pv);
  document.getElementById("k3").textContent = uv ? (pv/uv).toFixed(2) : "-";
  document.getElementById("k4").textContent = conv.toFixed(2) + "%";
  document.getElementById("k4box").className = "kpi " + (conv < 5 ? "w" : (conv > 8 ? "g" : ""));
  const r = CUBE.ranges[curRange];
  document.getElementById("k1d").textContent = r[0].slice(5) + " ~ " + r[1].slice(5);
  document.getElementById("k2d").textContent = "区间累计（可加总指标）";
  document.getElementById("rangeTxt").textContent = r[0] + " ~ " + r[1];
}}

// ---------- 趋势 ----------
function renderTrend() {{
  const dates = CUBE.dates;
  const data = dates.map(dt => {{
    const d = CUBE.daily[dt] || {{}};
    const g = b => (d[b] ? d[b] : {{u:0,c:0}});
    return {{dt, uv: g("pv").u, pv: g("pv").c}};
  }});
  const W = 1080, H = 220, pl = 52, pr = 54, pt = 14, pb = 30;
  const cw = W - pl - pr, ch = H - pt - pb;
  const muv = Math.max(...data.map(d=>d.uv),1) * 1.15;
  const mpv = Math.max(...data.map(d=>d.pv),1) * 1.15;
  const sx = i => pl + cw * i / (data.length-1);
  const py = v => pt + ch - ch*v/mpv;
  const uy = v => pt + ch - ch*v/muv;
  let s = `<svg viewBox="0 0 ${{W}} ${{H}}">`;
  for (let i=0;i<5;i++) {{
    const y = pt + ch*i/4;
    s += `<line x1="${{pl}}" y1="${{y}}" x2="${{W-pr}}" y2="${{y}}" stroke="#E5E7EB"/>`;
    s += `<text x="${{pl-6}}" y="${{y+3.5}}" font-size="10" fill="#94A3B8" text-anchor="end">${{Math.round(mpv*(1-i/4)/1000)}}k</text>`;
    s += `<text x="${{W-pr+6}}" y="${{y+3.5}}" font-size="10" fill="#B7791F">${{Math.round(muv*(1-i/4)/1000)}}k</text>`;
  }}
  const pl2 = data.map((d,i)=>`${{i?'L':'M'}}${{sx(i).toFixed(1)}},${{py(d.pv).toFixed(1)}}`).join(" ");
  s += `<path d="${{pl2}} L${{sx(data.length-1).toFixed(1)}},${{pt+ch}} L${{pl}},${{pt+ch}} Z" fill="#2F5BD7" opacity="0.10"/>`;
  s += `<path d="${{pl2}}" fill="none" stroke="#2F5BD7" stroke-width="2"/>`;
  const ul = data.map((d,i)=>`${{i?'L':'M'}}${{sx(i).toFixed(1)}},${{uy(d.uv).toFixed(1)}}`).join(" ");
  s += `<path d="${{ul}}" fill="none" stroke="#B7791F" stroke-width="1.8"/>`;
  data.forEach((d,i)=>{{
    if (i%5===0 || i===data.length-1)
      s += `<text x="${{sx(i).toFixed(1)}}" y="${{H-11}}" font-size="10" fill="#94A3B8" text-anchor="middle">${{d.dt.slice(5)}}</text>`;
  }});
  s += `<rect x="${{pl}}" y="2" width="16" height="3" fill="#2F5BD7"/><text x="${{pl+21}}" y="7.5" font-size="10.5" fill="#445">PV</text>`;
  s += `<rect x="${{pl+56}}" y="2" width="16" height="3" fill="#B7791F"/><text x="${{pl+77}}" y="7.5" font-size="10.5" fill="#445">UV（当日）</text>`;
  s += "</svg>";
  document.getElementById("trend").innerHTML = s;
}}

// ---------- 漏斗 ----------
function renderFunnel() {{
  const s = stats();
  const steps = BEH.map(b => [BNAME[b], s[b].u]);
  const W = 500, H = 240, pl = 62, bh = 32, gap = 22, cw = W - pl - 168;
  const mx = Math.max(steps[0][1],1);
  let out = `<svg viewBox="0 0 ${{W}} ${{H}}">`;
  steps.forEach(([n,v],i) => {{
    const y = 16 + i*(bh+gap), bw = Math.max(cw*v/mx, 4);
    out += `<text x="${{pl-9}}" y="${{y+bh/2+4}}" font-size="11.5" fill="#334" text-anchor="end">${{n}}</text>`;
    out += `<rect x="${{pl}}" y="${{y}}" width="${{bw.toFixed(1)}}" height="${{bh}}" fill="${{CP[i]}}" rx="3"/>`;
    out += `<text x="${{pl+bw+8}}" y="${{y+bh/2+4}}" font-size="12" font-weight="700" fill="${{CP[i]}}">${{fmt(v)}}</text>`;
    if (i>0) {{
      const drop = steps[i-1][1] ? (steps[i-1][1]-v)/steps[i-1][1]*100 : 0;
      const hl = i===3;
      out += `<text x="${{pl+bw+72}}" y="${{y+bh/2+4}}" font-size="10.5" fill="${{hl?'#B4453C':'#94A3B8'}}" font-weight="${{hl?700:400}}">↓${{drop.toFixed(1)}}%</text>`;
    }}
  }});
  out += "</svg>";
  document.getElementById("funnel").innerHTML = out;
  document.getElementById("funnelCap").textContent =
    (catSel==="all" ? "全站" : "当前类目") + `整体转化率 ${{pct(s.buy.u, s.pv.u).toFixed(2)}}%（购买人数 ÷ 浏览人数，均为区间去重）`;
}}

// ---------- 时段 ----------
function renderHourly() {{
  const Hs = CUBE.hours, total = Hs.reduce((a,b)=>a+b,0);
  const W = 500, H = 240, pl = 34, pr = 10, pt = 22, pb = 28;
  const cw = W - pl - pr, ch = H - pt - pb;
  const mx = Math.max(...Hs) * 1.18;
  const gap = cw/24, bw = gap*0.62;
  const pi = Hs.indexOf(Math.max(...Hs));
  let s = `<svg viewBox="0 0 ${{W}} ${{H}}">`;
  for (let i=0;i<5;i++) {{
    const y = pt + ch*i/4;
    s += `<line x1="${{pl}}" y1="${{y}}" x2="${{W-pr}}" y2="${{y}}" stroke="#E5E7EB"/>`;
  }}
  Hs.forEach((v,i)=>{{
    const x = pl + gap*i + (gap-bw)/2, bh = ch*v/mx;
    const col = i===pi ? "#B4453C" : (i>=19&&i<=22 ? "#1F3A63" : "#9DB4D6");
    s += `<rect x="${{x.toFixed(1)}}" y="${{(pt+ch-bh).toFixed(1)}}" width="${{bw.toFixed(1)}}" height="${{bh.toFixed(1)}}" fill="${{col}}" rx="1.5"/>`;
  }});
  [0,3,6,9,12,15,18,21].forEach(i=>{{
    s += `<text x="${{(pl+gap*i+gap/2).toFixed(1)}}" y="${{H-10}}" font-size="10" fill="#94A3B8" text-anchor="middle">${{i}}时</text>`;
  }});
  s += `<text x="${{(pl+gap*pi+gap/2).toFixed(1)}}" y="${{(pt+ch-ch*Hs[pi]/mx-6).toFixed(1)}}" font-size="11" font-weight="700" fill="#B4453C" text-anchor="middle">${{(Hs[pi]/total*100).toFixed(1)}}%</text>`;
  s += "</svg>";
  document.getElementById("hourly").innerHTML = s;
}}

// ---------- 类目对比 ----------
function renderCat() {{
  const cm = CUBE.category[curRange];
  const rows = CUBE.categories.map(([cid,name]) => {{
    const c = cm[cid] || {{}};
    return {{cid, name, browse:c.pv||0, buy:c.buy||0, conv:pct(c.buy||0, c.pv||0)}};
  }});
  const totB = rows.reduce((a,r)=>a+r.browse,0);
  const totY = rows.reduce((a,r)=>a+r.buy,0);
  const siteConv = totB ? totY/totB*100 : 0;
  rows.forEach(r => r.share = totB ? r.browse/totB*100 : 0);
  const sorted = rows.slice().sort((a,b)=>b.share-a.share);

  const W = 1080, H = 300, pl = 46, pr = 54, pt = 26, pb = 62;
  const cw = W-pl-pr, ch = H-pt-pb;
  const mxs = Math.max(...sorted.map(r=>r.share),1) * 1.2;
  const mxc = Math.max(...sorted.map(r=>r.conv), siteConv) * 1.25;
  const gap = cw/sorted.length, bw = gap*0.5;
  let s = `<svg viewBox="0 0 ${{W}} ${{H}}">`;
  for (let i=0;i<5;i++) {{
    const y = pt + ch*i/4;
    s += `<line x1="${{pl}}" y1="${{y}}" x2="${{W-pr}}" y2="${{y}}" stroke="#EEF1F6"/>`;
    s += `<text x="${{pl-6}}" y="${{y+3.5}}" font-size="10" fill="#94A3B8" text-anchor="end">${{(mxs*(1-i/4)).toFixed(0)}}%</text>`;
    s += `<text x="${{W-pr+6}}" y="${{y+3.5}}" font-size="10" fill="#B7791F">${{(mxc*(1-i/4)).toFixed(1)}}%</text>`;
  }}
  const yref = pt + ch - ch*siteConv/mxc;
  s += `<line x1="${{pl}}" y1="${{yref.toFixed(1)}}" x2="${{W-pr}}" y2="${{yref.toFixed(1)}}" stroke="#B4453C" stroke-width="1.2" stroke-dasharray="5,3"/>`;
  s += `<text x="${{W-pr-4}}" y="${{(yref-5).toFixed(1)}}" font-size="10" fill="#B4453C" text-anchor="end">类目均值 ${{siteConv.toFixed(2)}}%</text>`;
  const pts = [];
  sorted.forEach((r,i)=>{{
    const cx = pl + gap*i + gap/2, bh = ch*r.share/mxs;
    const bad = r.conv < siteConv && r.share > 10;
    s += `<rect x="${{(cx-bw/2).toFixed(1)}}" y="${{(pt+ch-bh).toFixed(1)}}" width="${{bw.toFixed(1)}}" height="${{bh.toFixed(1)}}" fill="${{bad?'#B4453C':'#1F3A63'}}" rx="2" opacity="0.88"/>`;
    pts.push([cx, pt + ch - ch*r.conv/mxc]);
  }});
  s += `<path d="${{pts.map((p,i)=>`${{i?'L':'M'}}${{p[0].toFixed(1)}},${{p[1].toFixed(1)}}`).join(" ")}}" fill="none" stroke="#B7791F" stroke-width="2"/>`;
  pts.forEach(p=>{{ s += `<circle cx="${{p[0].toFixed(1)}}" cy="${{p[1].toFixed(1)}}" r="3.2" fill="#fff" stroke="#B7791F" stroke-width="1.8"/>`; }});
  sorted.forEach((r,i)=>{{
    const cx = pl + gap*i + gap/2;
    s += `<text x="${{cx.toFixed(1)}}" y="${{H-40}}" font-size="10.5" fill="#445" text-anchor="end" transform="rotate(-40 ${{cx.toFixed(1)}} ${{H-40}})">${{r.name}}</text>`;
  }});
  s += `<rect x="${{pl}}" y="4" width="12" height="9" fill="#1F3A63" opacity="0.88"/><text x="${{pl+17}}" y="12" font-size="10.5" fill="#445">流量占比</text>`;
  s += `<rect x="${{pl+82}}" y="4" width="12" height="9" fill="#B4453C" opacity="0.88"/><text x="${{pl+99}}" y="12" font-size="10.5" fill="#445">高流量低转化</text>`;
  s += `<rect x="${{pl+196}}" y="6" width="12" height="3" fill="#B7791F"/><text x="${{pl+213}}" y="12" font-size="10.5" fill="#445">转化率（右轴）</text>`;
  s += "</svg>";
  document.getElementById("catChart").innerHTML = s;

  let t = `<thead><tr><th>类目</th><th class="r">流量占比</th><th class="r">浏览人数</th>
           <th class="r">购买人数</th><th class="r">转化率</th><th class="r">与均值差</th><th>判定</th></tr></thead><tbody>`;
  rows.slice().sort((a,b)=>b.browse-a.browse).forEach(r=>{{
    const gv = r.conv - siteConv;
    const bad = gv < 0 && r.share > 10;
    t += `<tr><td><strong>${{r.name}}</strong></td><td class="r">${{r.share.toFixed(2)}}%</td>
      <td class="r">${{fmt(r.browse)}}</td><td class="r">${{fmt(r.buy)}}</td>
      <td class="r">${{r.conv.toFixed(2)}}%</td>
      <td class="r ${{gv<0?'red':'grn'}}">${{gv>=0?'+':''}}${{gv.toFixed(2)}} pp</td>
      <td>${{bad ? '<span class="pill r">高流量低转化</span>'
              : (gv>0 ? '<span class="pill g">健康</span>' : '<span class="pill">常态</span>')}}</td></tr>`;
  }});
  t += "</tbody>";
  document.getElementById("catTable").innerHTML = t;

  const s2 = stats();
  const worst = rows.slice().sort((a,b)=>b.browse-a.browse).find(r => r.conv < siteConv);
  document.getElementById("caliberNote").innerHTML =
    `<strong>口径提示：</strong>本表按「人 × 类目」统计——跨类目用户会被重复计入分母，`
    + `因此类目汇总转化率 <b>${{siteConv.toFixed(2)}}%</b> 与全站漏斗口径转化率 `
    + `<b>${{pct(s2.buy.u, s2.pv.u).toFixed(2)}}%</b> 不同。两个数字都对，但不能混用：`
    + `平台级结论用漏斗口径，类目横向对比用本表口径。`
    + (worst ? `<br><strong>当前最大机会点：</strong>${{worst.name}} —— 流量占比 ${{worst.share.toFixed(2)}}%，`
              + `转化率 ${{worst.conv.toFixed(2)}}%，低于类目均值 ${{(siteConv-worst.conv).toFixed(2)}} 个百分点。` : "");
}}

function renderAll() {{ renderKPI(); renderTrend(); renderFunnel(); renderHourly(); renderCat(); }}

document.getElementById("presets").addEventListener("click", e => {{
  if (e.target.tagName !== "BUTTON") return;
  document.querySelectorAll("#presets button").forEach(b=>b.classList.remove("on"));
  e.target.classList.add("on");
  curRange = e.target.dataset.p;
  renderAll();
}});

document.getElementById("catSel").addEventListener("change", e => {{
  catSel = e.target.value;
  renderAll();
}});

renderAll();
</script>
</body></html>'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print("SAVED:", OUT, os.path.getsize(OUT), "bytes")
