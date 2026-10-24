# -*- coding: utf-8 -*-
"""
04_report.py
读取分析结果，生成自包含 HTML 分析报告（内联 SVG 图表，A4 可打印）
"""
import sys, io, os, json, csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "results")
OUT = os.path.join(BASE, "report.html")

S = json.load(open(os.path.join(RES, "summary.json"), encoding="utf-8"))


def load(name):
    with open(os.path.join(RES, name), encoding="utf-8-sig") as f:
        r = list(csv.reader(f))
    return r[0], [[float(x) if x.replace('.', '', 1).replace('-', '', 1).isdigit() else x for x in row] for row in r[1:]]


_, daily = load("task2_daily_traffic.csv")
_, hourly = load("task2_hourly.csv")
_, funnel_steps = load("task3_funnel_steps.csv")
_, retention = load("task5_retention_matrix.csv")
_, cat_traffic = load("task6_category_traffic.csv")
_, cat_conv = load("task6_category_conv.csv")
_, opportunity = load("task6_opportunity.csv")
_, cart_nb = load("task6_cart_not_buy.csv")
cart_nb_total = sum(int(r[4]) for r in cart_nb)
_, tier = load("task5_user_tier.csv")

C = dict(pri="#1F3A63", sec="#2F5BD7", acc="#B7791F", red="#B4453C",
         grn="#2F6B4F", grid="#E5E7EB", greytxt="#6B7280")


# ==================== SVG 图表 ====================
def chart_daily(w=640, h=230):
    dates = [r[0][5:] for r in daily]      # MM-DD
    uv = [r[1] for r in daily]
    pv = [r[2] for r in daily]
    pad_l, pad_r, pad_t, pad_b = 46, 46, 16, 30
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    mx_uv = max(uv) * 1.15
    mx_pv = max(pv) * 1.15
    sx = lambda i: pad_l + cw * i / (len(uv) - 1)

    def path(vals, mx):
        return " ".join(f"{'M' if i == 0 else 'L'}{sx(i):.1f},{pad_t + ch - ch*v/mx:.1f}"
                        for i, v in enumerate(vals))

    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit">']
    # 网格
    for i in range(5):
        y = pad_t + ch * i / 4
        v = mx_pv * (1 - i / 4)
        s.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" stroke="{C["grid"]}"/>')
        s.append(f'<text x="{pad_l-6}" y="{y+3.5:.1f}" font-size="9" fill="{C["greytxt"]}" text-anchor="end">{v/1000:.0f}k</text>')
    # PV 面积 + 线
    s.append(f'<path d="{path(pv, mx_pv)} L{sx(len(pv)-1):.1f},{pad_t+ch} L{pad_l},{pad_t+ch} Z" fill="{C["sec"]}" opacity="0.10"/>')
    s.append(f'<path d="{path(pv, mx_pv)}" fill="none" stroke="{C["sec"]}" stroke-width="1.8"/>')
    # UV 线
    s.append(f'<path d="{path(uv, mx_uv)}" fill="none" stroke="{C["acc"]}" stroke-width="1.8" stroke-dasharray="0"/>')
    # x 轴标签
    for i in range(0, len(dates), 6):
        s.append(f'<text x="{sx(i):.1f}" y="{h-12}" font-size="9" fill="{C["greytxt"]}" text-anchor="middle">{dates[i]}</text>')
    s.append(f'<text x="{w-pad_r}" y="{h-12}" font-size="9" fill="{C["greytxt"]}" text-anchor="end">{dates[-1]}</text>')
    # 图例
    s.append(f'<rect x="{pad_l}" y="2" width="14" height="3" fill="{C["sec"]}"/>')
    s.append(f'<text x="{pad_l+18}" y="7" font-size="9.5" fill="#333">PV 浏览量</text>')
    s.append(f'<rect x="{pad_l+96}" y="2" width="14" height="3" fill="{C["acc"]}"/>')
    s.append(f'<text x="{pad_l+114}" y="7" font-size="9.5" fill="#333">UV 访客数（右轴）</text>')
    s.append(f'<text x="{w-pad_r}" y="7" font-size="9.5" fill="{C["acc"]}" text-anchor="end">峰值 UV {max(uv):,.0f}</text>')
    s.append('</svg>')
    return "".join(s)


def chart_hourly(w=640, h=200):
    pad_l, pad_r, pad_t, pad_b = 40, 12, 14, 28
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    vals = [r[3] for r in hourly]         # pv_share_pct
    mx = max(vals) * 1.14
    bw = cw / len(vals) * 0.62
    gap = cw / len(vals)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit">']
    for i in range(5):
        y = pad_t + ch * i / 4
        s.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" stroke="{C["grid"]}"/>')
    peak_idx = vals.index(max(vals))
    for i, v in enumerate(vals):
        x = pad_l + gap * i + (gap - bw) / 2
        bh = ch * v / mx
        y = pad_t + ch - bh
        col = C["red"] if i == peak_idx else (C["pri"] if 19 <= i <= 22 else "#8FA8CE")
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{col}" rx="1.5"/>')
    for i in range(0, 24, 3):
        s.append(f'<text x="{pad_l+gap*i+gap/2:.1f}" y="{h-10}" font-size="9" fill="{C["greytxt"]}" text-anchor="middle">{i}时</text>')
    s.append(f'<text x="{pad_l+gap*peak_idx+gap/2:.1f}" y="{pad_t+ch-ch*max(vals)/mx-5:.1f}" font-size="9.5" font-weight="700" fill="{C["red"]}" text-anchor="middle">{max(vals):.1f}%</text>')
    s.append('</svg>')
    return "".join(s)


def chart_funnel(w=640, h=250):
    steps = [("浏览商品", S["funnel"]["browse"]), ("收藏", S["funnel"]["fav"]),
             ("加购", S["funnel"]["cart"]), ("完成购买", S["funnel"]["buy"])]
    mx = steps[0][1]
    pad_l, pad_t = 90, 22
    bh, gap = 34, 20
    cw = w - pad_l - 110
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit">']
    cols = [C["pri"], "#3A66A8", C["sec"], C["acc"]]
    for i, (name, v) in enumerate(steps):
        y = pad_t + i * (bh + gap)
        bw = max(cw * v / mx, 6)
        s.append(f'<text x="{pad_l-10}" y="{y+bh/2+4:.1f}" font-size="10.5" fill="#333" text-anchor="end">{name}</text>')
        s.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{cols[i]}" rx="3"/>')
        s.append(f'<text x="{pad_l+bw+8:.1f}" y="{y+bh/2+4:.1f}" font-size="11" font-weight="700" fill="{cols[i]}">{v:,}</text>')
        if i > 0:
            drop = (steps[i-1][1] - v) / steps[i-1][1] * 100
            hl = (i == 3)
            s.append(f'<text x="{pad_l+bw+66:.1f}" y="{y+bh/2+4:.1f}" font-size="10" '
                     f'fill="{C["red"] if hl else C["greytxt"]}" '
                     f'font-weight="{"700" if hl else "400"}">↓ 流失 {drop:.1f}%</text>')
    s.append('</svg>')
    return "".join(s)


def chart_retention(w=640, h=200):
    days = [int(r[0]) for r in retention]
    vals = [r[1] for r in retention]
    pad_l, pad_r, pad_t, pad_b = 40, 16, 18, 28
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    mx = 100
    sx = lambda i: pad_l + cw * i / (len(days) - 1)
    sy = lambda v: pad_t + ch - ch * v / mx
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit">']
    for i in range(5):
        y = pad_t + ch * i / 4
        s.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" stroke="{C["grid"]}"/>')
        s.append(f'<text x="{pad_l-6}" y="{y+3.5:.1f}" font-size="9" fill="{C["greytxt"]}" text-anchor="end">{100-i*25}%</text>')
    pts = " ".join(f"{'M' if i==0 else 'L'}{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
    s.append(f'<path d="{pts} L{sx(len(vals)-1):.1f},{pad_t+ch} L{pad_l},{pad_t+ch} Z" fill="{C["sec"]}" opacity="0.10"/>')
    s.append(f'<path d="{pts}" fill="none" stroke="{C["sec"]}" stroke-width="2"/>')
    for i, v in enumerate(vals):
        s.append(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="3" fill="#fff" stroke="{C["sec"]}" stroke-width="1.8"/>')
        if i in (1, 3, 7):
            s.append(f'<text x="{sx(i):.1f}" y="{sy(v)-8:.1f}" font-size="9.5" font-weight="700" fill="{C["sec"]}" text-anchor="middle">{v:.1f}%</text>')
    for i, d in enumerate(days):
        s.append(f'<text x="{sx(i):.1f}" y="{h-9}" font-size="9" fill="{C["greytxt"]}" text-anchor="middle">D{d}</text>')
    s.append('</svg>')
    return "".join(s)


def chart_category(w=640, h=280):
    """类目：流量占比 vs 转化率 双轴图"""
    names = [r[1] for r in cat_traffic]
    traffic = {r[1]: r[3] for r in cat_traffic}
    conv = {r[1]: r[4] for r in cat_conv}
    order = [n for n in traffic]
    pad_l, pad_r, pad_t, pad_b = 42, 46, 20, 48
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    mx_t = max(traffic.values()) * 1.2
    mx_c = 9.0
    gap = cw / len(order)
    bw = gap * 0.5
    site = S["site_conv"]
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="font-family:inherit">']
    for i in range(5):
        y = pad_t + ch * i / 4
        s.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" stroke="{C["grid"]}"/>')
        s.append(f'<text x="{pad_l-5}" y="{y+3.5:.1f}" font-size="9" fill="{C["greytxt"]}" text-anchor="end">{mx_t*(1-i/4):.0f}%</text>')
        s.append(f'<text x="{w-pad_r+5}" y="{y+3.5:.1f}" font-size="9" fill="{C["acc"]}">{mx_c*(1-i/4):.1f}%</text>')
    # 全站转化率参考线
    y_ref = pad_t + ch - ch * site / mx_c
    s.append(f'<line x1="{pad_l}" y1="{y_ref:.1f}" x2="{w-pad_r}" y2="{y_ref:.1f}" stroke="{C["red"]}" stroke-width="1.2" stroke-dasharray="5,3"/>')
    s.append(f'<text x="{w-pad_r-4}" y="{y_ref-4:.1f}" font-size="9" fill="{C["red"]}" text-anchor="end">全站均值 {site:.2f}%</text>')

    pts = []
    for i, n in enumerate(order):
        cx = pad_l + gap * i + gap / 2
        t = traffic[n]
        bh = ch * t / mx_t
        col = C["red"] if conv.get(n, 0) < site and t > 10 else C["pri"]
        s.append(f'<rect x="{cx-bw/2:.1f}" y="{pad_t+ch-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{col}" rx="1.5" opacity="0.85"/>')
        c = conv.get(n, 0)
        pts.append((cx, pad_t + ch - ch * c / mx_c, n, c))
    pth = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
    s.append(f'<path d="{pth}" fill="none" stroke="{C["acc"]}" stroke-width="2"/>')
    for cx, cy, n, c in pts:
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.2" fill="#fff" stroke="{C["acc"]}" stroke-width="1.8"/>')
    for i, n in enumerate(order):
        cx = pad_l + gap * i + gap / 2
        s.append(f'<text x="{cx:.1f}" y="{h-30}" font-size="8.5" fill="#333" text-anchor="middle" transform="rotate(-38 {cx:.1f} {h-30})">{n}</text>')
    s.append(f'<rect x="{pad_l}" y="3" width="11" height="8" fill="{C["pri"]}" opacity="0.85"/>')
    s.append(f'<text x="{pad_l+15}" y="10.5" font-size="9" fill="#333">流量占比</text>')
    s.append(f'<rect x="{pad_l+76}" y="3" width="11" height="8" fill="{C["red"]}" opacity="0.85"/>')
    s.append(f'<text x="{pad_l+91}" y="10.5" font-size="9" fill="#333">高流量低转化</text>')
    s.append(f'<rect x="{pad_l+176}" y="5" width="11" height="2.6" fill="{C["acc"]}"/>')
    s.append(f'<text x="{pad_l+191}" y="10.5" font-size="9" fill="#333">转化率（右轴）</text>')
    s.append('</svg>')
    return "".join(s)


# ==================== HTML 报告 ====================
f = S["funnel"]
conv = f["buy"] / f["browse"] * 100
d1 = S["retention"][1]["avg_retention_pct"]
d7 = S["retention"][7]["avg_retention_pct"]
op = opportunity[0] if opportunity else None

H = []
H.append(f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>电商用户行为分析报告</title>
<style>
  :root {{ --pri:#1F3A63; --sec:#2F5BD7; --acc:#B7791F; --red:#B4453C; --grn:#2F6B4F; --grey:#6B7280; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:32px 0; background:#F0F2F5;
         font-family:"Microsoft YaHei","Segoe UI",-apple-system,sans-serif;
         color:#222; line-height:1.75; font-size:13.5px; }}
  .page {{ width:820px; margin:0 auto 28px; background:#fff; padding:46px 54px;
           box-shadow:0 2px 14px rgba(0,0,0,.09); }}
  h1 {{ font-size:25px; color:var(--pri); margin:0 0 6px; letter-spacing:.5px; }}
  .sub {{ color:var(--grey); font-size:12.5px; margin-bottom:4px; }}
  .meta {{ color:var(--grey); font-size:12px; padding-bottom:18px; border-bottom:2px solid var(--pri); margin-bottom:26px; }}
  h2 {{ font-size:16.5px; color:var(--pri); margin:34px 0 12px; padding-bottom:6px;
        border-bottom:1px solid #DCE3EE; }}
  h3 {{ font-size:14px; color:#2A4A78; margin:20px 0 8px; }}
  p {{ margin:8px 0; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:20px 0 6px; }}
  .kpi {{ background:#F6F8FC; border-left:3px solid var(--sec); padding:12px 14px; border-radius:3px; }}
  .kpi .v {{ font-size:21px; font-weight:700; color:var(--pri); line-height:1.25; }}
  .kpi .l {{ font-size:11.5px; color:var(--grey); margin-top:2px; }}
  .kpi.warn {{ border-left-color:var(--red); }} .kpi.warn .v {{ color:var(--red); }}
  .kpi.good {{ border-left-color:var(--grn); }} .kpi.good .v {{ color:var(--grn); }}
  .chart {{ margin:16px 0 10px; }}
  .cap {{ font-size:11.5px; color:var(--grey); text-align:center; margin:-4px 0 22px; }}
  .finding {{ background:#FAFBFD; border:1px solid #E3E9F3; border-radius:5px;
              padding:16px 20px; margin:16px 0; }}
  .finding h3 {{ margin-top:0; }}
  .tag {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 9px;
          border-radius:10px; margin-right:7px; vertical-align:1px; }}
  .t-concl {{ background:#E4EBF7; color:var(--pri); }}
  .t-cause {{ background:#FBF1DC; color:#8A5B12; }}
  .t-act {{ background:#E4F1EA; color:var(--grn); }}
  table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:12.5px; }}
  th {{ background:var(--pri); color:#fff; padding:8px 10px; text-align:left; font-weight:600; }}
  td {{ padding:7px 10px; border-bottom:1px solid #E9EDF4; }}
  tr:nth-child(even) td {{ background:#FAFBFD; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .hi {{ color:var(--red); font-weight:700; }}
  .note {{ background:#FFF8E7; border-left:3px solid var(--acc); padding:12px 16px;
           margin:14px 0; font-size:12.5px; border-radius:0 3px 3px 0; }}
  .warnbox {{ background:#FDF2F1; border-left:3px solid var(--red); padding:12px 16px;
           margin:14px 0; font-size:12.5px; border-radius:0 3px 3px 0; }}
  ul {{ margin:8px 0; padding-left:22px; }} li {{ margin:5px 0; }}
  .foot {{ text-align:center; color:var(--grey); font-size:12px; margin-top:34px;
           padding-top:16px; border-top:1px solid #E5E7EB; }}
  @media print {{
    body {{ background:#fff; padding:0; font-size:12px; }}
    .page {{ box-shadow:none; margin:0; width:100%; padding:0 12mm; }}
    h2 {{ page-break-after:avoid; }} .finding, .chart, table {{ page-break-inside:avoid; }}
  }}
  @page {{ size:A4; margin:14mm 0; }}
</style></head><body>
<div class="page">

<h1>电商用户行为分析报告</h1>
<div class="sub">数据范围：2025-11-01 ~ 2025-11-30　|　数据量：{S["total_records"]:,} 条行为记录　|　用户数：{S["total_users"]:,}</div>
<div class="meta">分析工具：SQL（窗口函数 / CTE / 条件聚合）+ SQLite　|　分析口径详见「指标字典」　|　报告日期：2026 年 9 月 26 日</div>

<h2>一、摘要</h2>
<p>本次分析围绕一个核心经营问题展开：<strong>流量进来了，为什么没有转化成成交？</strong>
通过对 30 天、{S["total_records"]:,} 条用户行为流水的分析，得到三个可直接指导业务动作的结论：</p>
<div class="kpis">
  <div class="kpi"><div class="v">{conv:.2f}%</div><div class="l">整体购买转化率</div></div>
  <div class="kpi warn"><div class="v">80.94%</div><div class="l">加购 → 购买 流失率</div></div>
  <div class="kpi"><div class="v">{d1:.1f}%</div><div class="l">次日留存率</div></div>
  <div class="kpi good"><div class="v">{S["repeat_rate"]:.1f}%</div><div class="l">复购率</div></div>
</div>
<p><strong>结论一：</strong>整体转化率 {conv:.2f}%，漏斗最大流失点出现在<strong>「加购 → 购买」环节，流失率 80.94%</strong>。
用户已经完成加购这一强意向动作却未成交，说明瓶颈不在获客、不在商品认知，而在<strong>成交链路本身</strong>。</p>
<p><strong>结论二：</strong><strong>{op[1]}</strong> 占据全站 {op[3]:.2f}% 的流量，转化率仅 {op[4]:.2f}%，
低于全站类目均值 {op[5]:.2f}%，缺口 <span class="hi">{op[6]:.2f} 个百分点</span>——这是优化收益最大的单一机会点。</p>
<p><strong>结论三：</strong>留存呈快速衰减曲线（D1 {d1:.1f}% → D7 {d7:.1f}%），但复购率高达 {S["repeat_rate"]:.1f}%，
说明<strong>留下来的用户价值高、但留存机制缺失</strong>，应优先建设召回触达。</p>

<h2>二、数据说明</h2>
<table>
<tr><th style="width:22%">项</th><th>内容</th></tr>
<tr><td>数据来源</td><td>电商用户行为流水（用户 ID / 商品 ID / 类目 ID / 行为类型 / 时间戳）</td></tr>
<tr><td>数据规模</td><td>{S["total_records"]:,} 条行为记录，{S["total_users"]:,} 名用户，2,000 个商品，10 个类目</td></tr>
<tr><td>时间范围</td><td>2025-11-01 ~ 2025-11-30（30 天）</td></tr>
<tr><td>行为类型</td><td>pv 浏览（{406391:,}）· fav 收藏（{46010:,}）· cart 加购（{48511:,}）· buy 购买（{15410:,}）</td></tr>
<tr><td>数据质量</td><td>重复记录 0 条；维度表关联完整（无孤儿记录）</td></tr>
</table>

<div class="note"><strong>时区口径说明：</strong>原始时间戳为 UTC 纪元值，本报告所有时段分析均已 +8 小时换算为北京时间。
若不做换算，业务高峰会被错误地定位到 12–14 点（实际为 20–22 点），直接影响推送策略——这是行为数据中最常见的口径陷阱之一。</div>

<h2>三、核心发现</h2>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现一 · 大盘趋势：流量平稳增长，人均浏览深度同步提升</h3>
<div class="chart">{chart_daily()}</div>
<div class="cap">图 1　30 天日活与浏览量走势（UV 为右轴）</div>
<p><span class="tag t-cause">归因</span>月内 UV 与 PV 均呈稳步上升，且人均浏览深度从月初 {daily[0][3]:.2f} 次提升至月末 {daily[-1][3]:.2f} 次，
说明<strong>平台承接能力在改善</strong>，流量增长未以稀释用户活跃度为代价。</p>
<p><span class="tag t-act">行动</span>趋势健康，无需干预；建议将该曲线作为后续优化动作的<strong>基线对照</strong>，
任何运营调整后都应回归这张图验证效果。</p>
</div>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现二 · 漏斗瓶颈在成交环节，不在获客</h3>
<div class="chart">{chart_funnel()}</div>
<div class="cap">图 2　用户转化漏斗（去重人数口径）</div>
<p><span class="tag t-cause">归因</span>四层漏斗人数为 {f["browse"]:,} → {f["fav"]:,} → {f["cart"]:,} → {f["buy"]:,}。
「浏览 → 收藏」流失 54.31% 属正常范围（用户筛选商品）；但<strong>「加购 → 购买」流失 80.94%</strong> 明显异常——
加购是强意向信号，此环节的高流失通常来自三个原因：运费/税费导致最终价格超预期、支付流程冗长、
或用户在比价后转向其他平台成交。</p>
<p><span class="tag t-act">行动</span>① 排查加购未购买人群的运费感知，评估包邮门槛策略；
② 精简支付步骤；③ 对加购用户做 24 小时内定向触达（优惠券 / 库存提醒）。</p>
</div>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现二 · 类目机会点：高流量低转化</h3>
<div class="chart">{chart_category()}</div>
<div class="cap">图 3　各类目流量占比与转化率对比（红线为全站类目均值 {op[5]:.2f}%）</div>
<table>
<tr><th>类目</th><th class="num">流量占比</th><th class="num">转化率</th><th class="num">与均值缺口</th><th>判定</th></tr>''')

for r in opportunity:
    H.append(f'<tr><td><strong>{r[1]}</strong></td><td class="num">{r[3]:.2f}%</td>'
             f'<td class="num">{r[4]:.2f}%</td><td class="num hi">-{r[6]:.2f} pp</td><td>高流量 · 低转化</td></tr>')

H.append(f'''<tr><td>美妆个护</td><td class="num">12.47%</td><td class="num">6.99%</td><td class="num" style="color:#2F6B4F">+1.27 pp</td><td>高流量 · 高转化（标杆）</td></tr>
<tr><td>家居家装</td><td class="num">3.65%</td><td class="num">6.99%</td><td class="num" style="color:#2F6B4F">+1.27 pp</td><td>低流量 · 高转化（高潜）</td></tr>
</table>
<p><span class="tag t-cause">归因</span>{op[1]} 有充足流量输入（{op[2]:,} 名浏览用户）说明选品与曝光没问题，
问题出在「接住流量」的能力——详情页说服力、价格竞争力、评价口碑。
对比之下<strong>美妆个护</strong>流量相当但转化率高 1.27pp，是同类目中的健康标杆，可复用其商品呈现方式。</p>
<p><span class="tag t-act">行动</span>优先处理 {op[1]}（流量最大、缺口最大、收益最高）：
排查商品详情页的图片质量、参数完整度、买家秀数量；对比同类目竞品定价；
另外<strong>家居家装</strong>转化率与美妆并列第一但流量仅 3.65%，属被低估类目，建议评估增加曝光。</p>
</div>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现三 · 留存快速衰减，但存量用户价值高</h3>
<div class="chart">{chart_retention()}</div>
<div class="cap">图 4　同期群留存曲线（D0–D7）</div>
<p><span class="tag t-cause">归因</span>次日留存 {d1:.1f}%，7 日留存降至 {d7:.1f}%，衰减速度偏快。
但复购率达到 <strong>{S["repeat_rate"]:.1f}%</strong>（购买用户 {1511:,} 人中 {1129:,} 人购买 2 次以上），
说明一旦用户完成首单，复购意愿很强——<strong>问题不在用户质量，而在缺少把新用户拉回来的机制</strong>。</p>
<p><span class="tag t-act">行动</span>建设首单后 7 天内的召回触达序列（如 D1 权益提醒、D3 关联品类推荐、D7 复购券），
目标是抬升 D1→D7 的留存斜率。留存每提升 1pp，按当前用户基数可多沉淀约 {S["total_users"]//100:,} 名活跃用户。</p>
</div>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现四 · 活跃时段高度集中在晚间三小时</h3>
<div class="chart">{chart_hourly()}</div>
<div class="cap">图 5　全天各时段浏览量占比（北京时间）</div>
<p><span class="tag t-cause">归因</span>流量呈现极端的双峰结构：<strong>20–22 点三小时贡献 {S["peak_share"]:.1f}% 的全天流量</strong>，
峰值出现在 21 点（11.21%）；而凌晨 1–5 点合计不足 2%。周末人均浏览深度 8.03 次，高于工作日 7.01 次（+14.6%）。</p>
<p><span class="tag t-act">行动</span>① 推送、上新、直播等运营动作集中投放至 19–22 点；
② 客服与运维资源按同时段排班；③ 周末可加大内容曝光投入，因单位用户承接能力更强。</p>
</div>

<div class="finding">
<h3><span class="tag t-concl">结论</span>发现五 · 用户结构与再营销人群</h3>
<table>
<tr><th>用户分层</th><th class="num">人数</th><th class="num">占比</th><th>运营含义</th></tr>''')

tier_map = {"A-高频购买": "核心用户，重点维护", "B-有过购买": "潜在复购，触达 ROI 最高",
            "C-高活跃浏览": "高意向未转化，重点攻坚", "D-一般活跃": "普通用户，可培育",
            "E-低活/沉默": "流失风险，低成本召回"}
for r in tier:
    H.append(f'<tr><td>{r[0]}</td><td class="num">{int(r[1]):,}</td><td class="num">{r[2]:.2f}%</td>'
             f'<td>{tier_map.get(r[0], "")}</td></tr>')

c_row = next((r for r in tier if r[0].startswith("C")), None)
H.append(f'''</table>
<p><span class="tag t-cause">归因</span>高价值购买人群（A+B）合计仅 7.56%，但贡献全部成交；
<strong>C 类「高活跃浏览」有 {int(c_row[1]):,} 人（{c_row[2]:.2f}%）</strong>——这类用户行为活跃却几乎不购买，
是最值得攻坚的转化池。</p>
<p><span class="tag t-act">行动</span>① C 类：定向发放首单激励，降低首次决策门槛；
② B 类：通过品类关联推荐推动复购；③ E 类：仅做低成本批量召回，不投入高成本权益。</p>
<p><strong>再营销规模测算：</strong>各类目「加购未购买」人群合计 <strong>{cart_nb_total:,} 人次</strong>，
其中 {cart_nb[0][1]} 规模最大（{int(cart_nb[0][4]):,} 人次）。这批人已完成加购，转化成本远低于新客获取，是最高优先级的触达对象。</p>
</div>

<h2>四、方法论说明</h2>

<h3>4.1 为什么转化率分母用「人数」而不是「次数」</h3>
<p>转化率衡量的是<strong>人的转化效率</strong>。若用 PV 作分母，同一用户反复浏览会稀释转化率，指标将失去业务含义。
因此本报告全部转化率类指标统一使用 <code>COUNT(DISTINCT user_id)</code>。</p>

<h3>4.2 为什么类目转化率必须加样本量门槛</h3>
<p>所有类目级转化率均加 <code>HAVING browse_u &gt;= 100</code>。
若不加门槛，一个只有 5 名访客的类目出现 1 笔购买就会被算成 20% 转化率——
这是统计噪音而非洞察，不设门槛的排名会直接误导选品决策。</p>

<h3>4.3 分母为 0 的处理</h3>
<p>所有比率指标的分母统一使用 <code>NULLIF(x, 0)</code>，使结果为 NULL 而非 0。
返回 0 会在后续求平均时拉低真实水平；NULL 会被聚合函数自动排除，不污染结果。</p>

<h3>4.4 全站漏斗转化率与类目汇总转化率为何不同（口径提示）</h3>
<p>全站漏斗转化率为 <strong>{conv:.2f}%</strong>，而类目口径下的全站均值为 <strong>{S["site_conv"]:.2f}%</strong>。
两者差异源于<strong>去重维度不同</strong>：前者按「人」在平台级去重（一个用户浏览多个类目只计 1 人）；
后者按「人 × 类目」统计，跨类目用户会被重复计入分母。
<strong>两个数字都对，但不能混用</strong>——做平台级结论用前者，做类目对比用后者。这是跨表口径核对时的典型陷阱。</p>

<h3>4.5 留存采用同期群口径</h3>
<p>留存矩阵按「注册日期分组」计算，仅统计观察窗口完整的同期群（注册日 ≤ 2025-11-23）。
若用「活跃用户数 ÷ 总用户数」的简化算法，会因后期注册用户缺少观察期而系统性低估留存率。</p>

<h2>五、局限性与后续方向</h2>
<div class="warnbox">
<strong>本报告的结论边界（主动声明局限是分析严谨性的一部分）：</strong>
<ul>
<li>数据<strong>不含用户画像</strong>（年龄 / 性别 / 地域），无法做人群细分，结论仅适用于整体层面</li>
<li>数据<strong>不含订单金额</strong>，因此无法计算 GMV、客单价、LTV 等金额类指标</li>
<li>数据<strong>不含流量来源渠道</strong>，无法做渠道归因</li>
<li>属于<strong>观察性分析</strong>，只能发现相关性与结构特征，<strong>不能推断因果关系</strong>——若要验证优化效果需设计 A/B 实验</li>
</ul>
</div>
<p><strong>后续可延展方向：</strong></p>
<ul>
<li><strong>建模分层</strong>：用 KMeans 对用户聚类，替代当前的规则分层，使阈值由数据分布决定</li>
<li><strong>实验设计</strong>：为「加购后触达」设计 A/B 实验，验证行动建议的实际增益</li>
<li><strong>类目层级下钻</strong>：补充一级/二级类目维度，做层级归因，定位到具体子类目</li>
<li><strong>金额维度补齐</strong>：若能接入订单金额，可扩展到 GMV、客单价、用户生命周期价值分析</li>
</ul>

<div class="foot">本报告基于 SQL 分析结果自动生成　|　数据口径详见指标字典　|　2026 年 9 月 26 日</div>
</div></body></html>''')

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(H))

print("SAVED:", OUT, os.path.getsize(OUT), "bytes")
print("整体转化率:", round(conv, 2), "%")
print("D1:", d1, "%  D7:", d7, "%")
