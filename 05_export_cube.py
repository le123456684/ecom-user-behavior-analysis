# -*- coding: utf-8 -*-
"""
05_export_cube.py  (v2 — 修正去重口径)

v1 的错误：把「每日去重人数」跨日期相加当作区间去重人数。
           日 UV 相加得到的是「用户日/人次」，不是独立访客数。
           由此算出的转化率 10.51% 是错的（真实值 7.63%）。

v2 的做法：
  · 对固定的时间区间（全期 / 前15天 / 后15天）预先精确计算去重人数
  · 日粒度数据只用于趋势图（每日 UV 是当日去重，正确）
  · 加法型指标（PV 等计数）可以安全相加
"""
import sys, io, os, sqlite3, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "ecom.db")
OUT = os.path.join(BASE, "results", "dashboard_data.json")

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("SELECT DISTINCT dt FROM user_behavior ORDER BY dt")
ALL_DATES = [r[0] for r in cur.fetchall()]
RANGES = {
    "all":   (ALL_DATES[0], ALL_DATES[-1]),
    "first": (ALL_DATES[0], ALL_DATES[14]),
    "last":  (ALL_DATES[-15], ALL_DATES[-1]),
}
print("区间定义:")
for k, (a, b) in RANGES.items():
    print(f"  {k:6s} {a} ~ {b}")


def distinct_stats(where=""):
    """按行为类型返回区间去重人数 + 计数"""
    sql = f"""
    SELECT behavior_type, COUNT(DISTINCT user_id), COUNT(*)
    FROM user_behavior {where}
    GROUP BY behavior_type
    """
    cur.execute(sql)
    return {b: {"u": u, "c": c} for b, u, c in cur.fetchall()}


# ---------- 1. 平台级：精确区间去重 ----------
platform = {}
for k, (a, b) in RANGES.items():
    platform[k] = distinct_stats(f"WHERE dt BETWEEN '{a}' AND '{b}'")
    print(f"平台 [{k}] " + " | ".join(
        f"{bh} 人数={platform[k].get(bh,{}).get('u',0):,} 计数={platform[k].get(bh,{}).get('c',0):,}"
        for bh in ["pv", "fav", "cart", "buy"]))

# ---------- 2. 类目级：精确区间去重（pv / buy 驱动转化率） ----------
cur.execute("SELECT DISTINCT b.category_id, i.category_name FROM user_behavior b "
            "LEFT JOIN item_dim i ON b.item_id=i.item_id ORDER BY b.category_id")
cats = [(str(c), n) for c, n in cur.fetchall()]

category = {}
for k, (a, b) in RANGES.items():
    category[k] = {}
    for cid, cname in cats:
        cur.execute(f"""
        SELECT COUNT(DISTINCT CASE WHEN behavior_type='pv'   THEN user_id END),
               COUNT(DISTINCT CASE WHEN behavior_type='fav'  THEN user_id END),
               COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END),
               COUNT(DISTINCT CASE WHEN behavior_type='buy'  THEN user_id END),
               SUM(behavior_type='pv')
        FROM user_behavior
        WHERE dt BETWEEN '{a}' AND '{b}' AND category_id = {cid}
        """)
        pv, fv, ct, bu, pvc = cur.fetchone()
        category[k][cid] = {"pv": pv or 0, "fav": fv or 0, "cart": ct or 0,
                            "buy": bu or 0, "pvC": pvc or 0}
    print(f"类目 [{k}] 完成")

# ---------- 3. 日粒度（趋势图专用） ----------
cur.execute("""
SELECT dt, behavior_type, COUNT(DISTINCT user_id), COUNT(*)
FROM user_behavior GROUP BY dt, behavior_type
""")
daily = {}
for dt, beh, u, c in cur.fetchall():
    daily.setdefault(dt, {})[beh] = {"u": u, "c": c}

# 类目日粒度（只取 pv 计数，加法安全）
cur.execute("""SELECT dt, category_id, SUM(behavior_type='pv')
               FROM user_behavior GROUP BY dt, category_id""")
daily_cat = {}
for dt, cid, pvc in cur.fetchall():
    daily_cat.setdefault(dt, {})[str(cid)] = pvc or 0

# ---------- 4. 时段（加法安全） ----------
cur.execute("""SELECT CAST(strftime('%H', ts + 28800, 'unixepoch') AS INTEGER), SUM(behavior_type='pv')
               FROM user_behavior GROUP BY 1 ORDER BY 1""")
hours = [r[1] for r in cur.fetchall()]

# ---------- 5. 复购率 ----------
cur.execute("""WITH bc AS (SELECT user_id, COUNT(*) n FROM user_behavior
                           WHERE behavior_type='buy' GROUP BY user_id)
               SELECT COUNT(*), SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END) FROM bc""")
buyers, repeat = cur.fetchone()

con.close()

payload = {
    "dates": ALL_DATES,
    "ranges": {k: [a, b] for k, (a, b) in RANGES.items()},
    "platform": platform,
    "category": category,
    "categories": cats,
    "daily": daily,
    "dailyCat": daily_cat,
    "hours": hours,
    "totalBuyers": buyers,
    "repeatBuyers": repeat,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

print("\nSAVED:", OUT, f"{os.path.getsize(OUT)/1024:.0f} KB")
print("\n=== 口径核对 ===")
p = platform["all"]
conv_true = p["buy"]["u"] / p["pv"]["u"] * 100
uv_summed = sum(d["pv"]["u"] for d in daily.values())
print(f"全期独立访客（正确）      : {p['pv']['u']:,}")
print(f"日 UV 简单相加（错误做法）: {uv_summed:,}   ← 差 {uv_summed - p['pv']['u']:,}")
print(f"真实转化率（正确）        : {conv_true:.2f}%")
print(f"用相加值算的转化率（错误）: {p['buy']['u']/uv_summed*100:.2f}%")
