# -*- coding: utf-8 -*-
"""
03_analyze.py
跑完六个分析任务，把结果导出为 CSV / JSON，供看板与报告使用
"""
import sys, io, os, sqlite3, csv, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "ecom.db")
RES = os.path.join(BASE, "results")
os.makedirs(RES, exist_ok=True)

con = sqlite3.connect(DB)
cur = con.cursor()

SUMMARY = {}


def q(sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def show(title, sql, limit=30):
    cols, rows = q(sql)
    print(f"\n{'='*72}\n{title}\n{'='*72}")
    print(" | ".join(f"{c}" for c in cols))
    print("-" * 72)
    for r in rows[:limit]:
        print(" | ".join("" if v is None else (f"{v:,.2f}" if isinstance(v, float) else f"{v:,}" if isinstance(v, int) else str(v)) for v in r))
    if len(rows) > limit:
        print(f"... 共 {len(rows)} 行")
    return cols, rows


def save_csv(name, cols, rows):
    p = os.path.join(RES, name)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    return p


# ============ 任务2 日活与流量 ============
cols, rows = show("任务 2.1  日活与流量总览", """
SELECT dt,
       COUNT(DISTINCT user_id) AS uv,
       SUM(behavior_type='pv') AS pv,
       ROUND(SUM(behavior_type='pv')*1.0/NULLIF(COUNT(DISTINCT user_id),0), 2) AS pv_per_uv,
       COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_uv
FROM user_behavior GROUP BY dt ORDER BY dt
""", limit=8)
save_csv("task2_daily_traffic.csv", cols, rows)

SUMMARY["avg_daily_uv"] = round(
    q("""SELECT AVG(daily_uv) FROM (
            SELECT dt, COUNT(DISTINCT user_id) daily_uv FROM user_behavior GROUP BY dt
         )""")[1][0][0], 0)
SUMMARY["total_users"] = q("SELECT COUNT(DISTINCT user_id) FROM user_behavior")[1][0][0]
SUMMARY["total_records"] = q("SELECT COUNT(*) FROM user_behavior")[1][0][0]

cols, rows = show("任务 2.2  时段分布（找出用户最活跃的时段）", """
SELECT CAST(strftime('%H', ts + 28800, 'unixepoch') AS INTEGER) AS hour_of_day,
       SUM(behavior_type='pv') AS pv,
       COUNT(DISTINCT user_id) AS uv,
       ROUND(SUM(behavior_type='pv')*100.0/SUM(SUM(behavior_type='pv')) OVER (), 2) AS pv_share_pct
FROM user_behavior GROUP BY hour_of_day ORDER BY hour_of_day
""")
save_csv("task2_hourly.csv", cols, rows)

# 高峰时段结论
peak = sorted(rows, key=lambda r: -r[1])[:3]
SUMMARY["peak_hours"] = [(r[0], r[3]) for r in peak]
SUMMARY["peak_share"] = round(sum(r[3] for r in peak), 2)

cols, rows = show("任务 2.3  周末 vs 工作日（比较人均活跃强度）", """
SELECT d.is_weekend,
       CASE d.is_weekend WHEN 1 THEN '周末' ELSE '工作日' END AS day_type,
       ROUND(AVG(t.daily_uv),0)          AS avg_uv,
       ROUND(AVG(t.daily_pv),0)          AS avg_pv,
       ROUND(AVG(t.daily_pv*1.0/t.daily_uv), 2) AS pv_per_uv
FROM (SELECT dt, COUNT(DISTINCT user_id) daily_uv, SUM(behavior_type='pv') daily_pv
      FROM user_behavior GROUP BY dt) t
JOIN date_dim d ON t.dt = d.dt
GROUP BY d.is_weekend
""")
save_csv("task2_weekend.csv", cols, rows)
for r in rows:
    SUMMARY[f"avg_uv_{r[1]}"] = r[2]
    SUMMARY[f"pv_per_uv_{r[1]}"] = r[4]

# ============ 任务3 漏斗 ============
cols, rows = show("任务 3.1  全局转化漏斗（核心）", """
SELECT
  COUNT(DISTINCT CASE WHEN behavior_type='pv'   THEN user_id END) AS browse_users,
  COUNT(DISTINCT CASE WHEN behavior_type='fav'  THEN user_id END) AS fav_users,
  COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END) AS cart_users,
  COUNT(DISTINCT CASE WHEN behavior_type='buy'  THEN user_id END) AS buy_users
FROM user_behavior
""")
save_csv("task3_funnel.csv", cols, rows)
browse, fav, cart, buy = rows[0]
SUMMARY["funnel"] = {"browse": browse, "fav": fav, "cart": cart, "buy": buy}
SUMMARY["conv_rate"] = round(buy / browse * 100, 2)

cols, rows = show("任务 3.2  漏斗逐层流失率", """
WITH f AS (
  SELECT COUNT(DISTINCT CASE WHEN behavior_type='pv'   THEN user_id END) AS s1,
         COUNT(DISTINCT CASE WHEN behavior_type='fav'  THEN user_id END) AS s2,
         COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END) AS s3,
         COUNT(DISTINCT CASE WHEN behavior_type='buy'  THEN user_id END) AS s4
  FROM user_behavior
)
SELECT '浏览' AS step, s1 AS users, 100.00 AS rate_pct, NULL AS drop_pct, NULL AS drop_from FROM f
UNION ALL SELECT '收藏', s2, ROUND(s2*100.0/s1,2), ROUND((s1-s2)*100.0/s1,2), '浏览→收藏' FROM f
UNION ALL SELECT '加购', s3, ROUND(s3*100.0/s2,2), ROUND((s2-s3)*100.0/s2,2), '收藏→加购' FROM f
UNION ALL SELECT '购买', s4, ROUND(s4*100.0/s3,2), ROUND((s3-s4)*100.0/s3,2), '加购→购买' FROM f
""")
save_csv("task3_funnel_steps.csv", cols, rows)
SUMMARY["funnel_steps"] = [dict(zip(cols, r)) for r in rows]

cols, rows = show("任务 3.3  按日漏斗趋势", """
SELECT dt,
       COUNT(DISTINCT CASE WHEN behavior_type='pv'  THEN user_id END) AS browse_users,
       COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users,
       ROUND(COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END)*100.0
             / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END),0), 2) AS conv_rate_pct
FROM user_behavior GROUP BY dt ORDER BY dt
""", limit=6)
save_csv("task3_daily_funnel.csv", cols, rows)

# ============ 任务4 路径 ============
cols, rows = show("任务 4.1  行为转移矩阵（Top 12）", """
WITH s AS (
  SELECT user_id, behavior_type, ts,
         LAG(behavior_type) OVER (PARTITION BY user_id ORDER BY ts) AS prev
  FROM user_behavior
)
SELECT prev AS from_step, behavior_type AS to_step,
       COUNT(*) AS transitions, COUNT(DISTINCT user_id) AS users
FROM s WHERE prev IS NOT NULL
GROUP BY from_step, to_step ORDER BY transitions DESC
""", limit=12)
save_csv("task4_transition.csv", cols, rows)

cols, rows = show("任务 4.2  购买前一步行为分布", """
WITH pb AS (
  SELECT user_id, behavior_type,
         LAG(behavior_type) OVER (PARTITION BY user_id ORDER BY ts) AS prev
  FROM user_behavior
)
SELECT prev AS step_before_buy,
       COUNT(DISTINCT user_id) AS users,
       ROUND(COUNT(DISTINCT user_id)*100.0/SUM(COUNT(DISTINCT user_id)) OVER (), 2) AS pct
FROM pb WHERE behavior_type='buy' AND prev IS NOT NULL
GROUP BY prev ORDER BY users DESC
""")
save_csv("task4_pre_buy.csv", cols, rows)
SUMMARY["pre_buy"] = [dict(zip(cols, r)) for r in rows]

# ============ 任务5 留存 ============
cols, rows = show("任务 5.1  次日留存率（按注册日）", """
WITH fd AS (SELECT user_id, MIN(dt) AS reg_dt FROM user_behavior GROUP BY user_id),
     act AS (SELECT DISTINCT user_id, dt FROM user_behavior)
SELECT f.reg_dt,
       COUNT(DISTINCT f.user_id) AS new_users,
       COUNT(DISTINCT CASE WHEN julianday(a.dt)-julianday(f.reg_dt)=1 THEN a.user_id END) AS retained_d1,
       ROUND(COUNT(DISTINCT CASE WHEN julianday(a.dt)-julianday(f.reg_dt)=1 THEN a.user_id END)*100.0
             / NULLIF(COUNT(DISTINCT f.user_id),0), 2) AS d1_retention_pct
FROM fd f LEFT JOIN act a ON f.user_id=a.user_id
GROUP BY f.reg_dt ORDER BY f.reg_dt
""", limit=8)
save_csv("task5_d1_retention.csv", cols, rows)

cols, rows = show("任务 5.2  留存矩阵（同期群口径，D0-D7 平均）", """
WITH fd AS (SELECT user_id, MIN(dt) AS reg_dt FROM user_behavior GROUP BY user_id),
     act AS (SELECT DISTINCT user_id, dt FROM user_behavior),
     sizes AS (SELECT reg_dt, COUNT(*) AS cohort_size FROM fd GROUP BY reg_dt),
     co AS (
       SELECT f.reg_dt,
              CAST(julianday(a.dt)-julianday(f.reg_dt) AS INTEGER) AS day_n,
              COUNT(DISTINCT f.user_id) AS users
       FROM fd f JOIN act a ON f.user_id=a.user_id
       WHERE julianday(a.dt)-julianday(f.reg_dt) BETWEEN 0 AND 7
       GROUP BY f.reg_dt, day_n
     )
SELECT co.day_n,
       ROUND(AVG(co.users*100.0/s.cohort_size), 2) AS avg_retention_pct
FROM co JOIN sizes s ON co.reg_dt = s.reg_dt
WHERE co.reg_dt <= '2025-11-23'     -- 只统计观察窗口完整的同期群
GROUP BY co.day_n ORDER BY co.day_n
""")
save_csv("task5_retention_matrix.csv", cols, rows)
SUMMARY["retention"] = [dict(zip(cols, r)) for r in rows]

cols, rows = show("任务 5.3  复购率", """
WITH bc AS (
  SELECT user_id, COUNT(*) AS buy_times FROM user_behavior
  WHERE behavior_type='buy' GROUP BY user_id
)
SELECT COUNT(*) AS buyer_users,
       SUM(CASE WHEN buy_times>=2 THEN 1 ELSE 0 END) AS repeat_buyers,
       ROUND(SUM(CASE WHEN buy_times>=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS repeat_rate_pct
FROM bc
""")
save_csv("task5_repeat.csv", cols, rows)
SUMMARY["repeat_rate"] = rows[0][2]

cols, rows = show("任务 5.4  用户活跃度分层", """
WITH u AS (
  SELECT user_id,
         SUM(behavior_type='pv')  AS pv_cnt,
         SUM(behavior_type='buy') AS buy_cnt
  FROM user_behavior GROUP BY user_id
)
SELECT CASE
         WHEN buy_cnt>=3            THEN 'A-高频购买'
         WHEN buy_cnt BETWEEN 1 AND 2 THEN 'B-有过购买'
         WHEN pv_cnt>=20            THEN 'C-高活跃浏览'
         WHEN pv_cnt BETWEEN 5 AND 19 THEN 'D-一般活跃'
         ELSE 'E-低活/沉默' END AS user_tier,
       COUNT(*) AS users,
       ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (), 2) AS pct
FROM u GROUP BY user_tier ORDER BY users DESC
""")
save_csv("task5_user_tier.csv", cols, rows)
SUMMARY["user_tier"] = [dict(zip(cols, r)) for r in rows]

# ============ 任务6 类目 ============
cols, rows = show("任务 6.1  类目流量结构（Top 15）", """
SELECT b.category_id, i.category_name,
       SUM(b.behavior_type='pv') AS pv,
       ROUND(SUM(b.behavior_type='pv')*100.0/SUM(SUM(b.behavior_type='pv')) OVER (), 2) AS pv_share_pct,
       COUNT(DISTINCT b.user_id) AS uv
FROM user_behavior b LEFT JOIN item_dim i ON b.item_id=i.item_id
GROUP BY b.category_id, i.category_name ORDER BY pv DESC
""")
save_csv("task6_category_traffic.csv", cols, rows)

cols, rows = show("任务 6.2  类目转化率排名", """
SELECT b.category_id, i.category_name,
       COUNT(DISTINCT CASE WHEN b.behavior_type='pv'  THEN b.user_id END) AS browse_u,
       COUNT(DISTINCT CASE WHEN b.behavior_type='buy' THEN b.user_id END) AS buy_u,
       ROUND(COUNT(DISTINCT CASE WHEN b.behavior_type='buy' THEN b.user_id END)*100.0
             / NULLIF(COUNT(DISTINCT CASE WHEN b.behavior_type='pv' THEN b.user_id END),0),2) AS conv_rate_pct
FROM user_behavior b LEFT JOIN item_dim i ON b.item_id=i.item_id
GROUP BY b.category_id, i.category_name
HAVING browse_u >= 100
ORDER BY conv_rate_pct DESC
""")
save_csv("task6_category_conv.csv", cols, rows)

cols, rows = show("任务 6.3  核心产出：高流量低转化类目", """
WITH cs AS (
  SELECT b.category_id, i.category_name,
         COUNT(DISTINCT CASE WHEN b.behavior_type='pv'  THEN b.user_id END) AS browse_u,
         COUNT(DISTINCT CASE WHEN b.behavior_type='buy' THEN b.user_id END) AS buy_u
  FROM user_behavior b LEFT JOIN item_dim i ON b.item_id=i.item_id
  GROUP BY b.category_id, i.category_name
  HAVING browse_u >= 100
),
site AS (SELECT SUM(browse_u) AS sb, SUM(buy_u)*1.0/NULLIF(SUM(browse_u),0) AS sc FROM cs)
SELECT c.category_id, c.category_name, c.browse_u,
       ROUND(c.browse_u*100.0/s.sb, 2) AS traffic_share_pct,
       ROUND(c.buy_u*100.0/NULLIF(c.browse_u,0), 2) AS conv_rate_pct,
       ROUND(s.sc*100, 2) AS site_conv_pct,
       ROUND((s.sc - c.buy_u*1.0/NULLIF(c.browse_u,0))*100, 2) AS gap_pct
FROM cs c CROSS JOIN site s
WHERE c.buy_u*1.0/NULLIF(c.browse_u,0) < s.sc
  AND c.browse_u*100.0/s.sb > 2
ORDER BY c.browse_u DESC
""")
save_csv("task6_opportunity.csv", cols, rows)
SUMMARY["opportunity"] = [dict(zip(cols, r)) for r in rows]
SUMMARY["site_conv"] = rows[0][5] if rows else None

cols, rows = show("任务 6.4  加购未购买人群（再营销目标）", """
SELECT b.category_id, i.category_name,
       COUNT(DISTINCT CASE WHEN b.behavior_type='cart' THEN b.user_id END) AS cart_u,
       COUNT(DISTINCT CASE WHEN b.behavior_type='buy'  THEN b.user_id END) AS buy_u,
       COUNT(DISTINCT CASE WHEN b.behavior_type='cart' THEN b.user_id END)
         - COUNT(DISTINCT CASE WHEN b.behavior_type='buy' THEN b.user_id END) AS cart_not_buy_u,
       ROUND(COUNT(DISTINCT CASE WHEN b.behavior_type='buy' THEN b.user_id END)*100.0
             / NULLIF(COUNT(DISTINCT CASE WHEN b.behavior_type='cart' THEN b.user_id END),0),2) AS cart_to_buy_pct
FROM user_behavior b LEFT JOIN item_dim i ON b.item_id=i.item_id
GROUP BY b.category_id, i.category_name
HAVING cart_u >= 100
ORDER BY cart_not_buy_u DESC
""")
save_csv("task6_cart_not_buy.csv", cols, rows)

# 每日 UV / PV 供图表
cols, rows = q("""SELECT dt, COUNT(DISTINCT user_id) uv, SUM(behavior_type='pv') pv
                  FROM user_behavior GROUP BY dt ORDER BY dt""")
with open(os.path.join(RES, "chart_daily.json"), "w", encoding="utf-8") as f:
    json.dump({"cols": cols, "rows": rows}, f, ensure_ascii=False)

with open(os.path.join(RES, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(SUMMARY, f, ensure_ascii=False, indent=2)

con.close()
print(f"\n\n结果已保存到: {RES}")
print(json.dumps({k: v for k, v in SUMMARY.items() if not isinstance(v, list)}, ensure_ascii=False, indent=2))
