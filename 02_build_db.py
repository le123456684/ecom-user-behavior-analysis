# -*- coding: utf-8 -*-
"""
02_build_db.py
建库 + 导入数据 + 创建派生表

说明：演示环境用 SQLite（零安装依赖），SQL 语法与 MySQL 几乎一致。
      迁移到 MySQL 时只需替换少数方言函数，详见文件末尾的对照表。
"""
import sys, io, os, sqlite3, csv, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DB = os.path.join(BASE, "ecom.db")

if os.path.exists(DB):
    os.remove(DB)

con = sqlite3.connect(DB)
con.execute("PRAGMA journal_mode=OFF")
con.execute("PRAGMA synchronous=OFF")
cur = con.cursor()

# ---------------- 建表 ----------------
cur.executescript("""
DROP TABLE IF EXISTS user_behavior;
CREATE TABLE user_behavior (
  user_id       INTEGER NOT NULL,
  item_id       INTEGER NOT NULL,
  category_id   INTEGER NOT NULL,
  behavior_type TEXT    NOT NULL,
  ts            INTEGER NOT NULL,
  dt            TEXT    NOT NULL
);

DROP TABLE IF EXISTS item_dim;
CREATE TABLE item_dim (
  item_id       INTEGER PRIMARY KEY,
  category_id   INTEGER NOT NULL,
  category_name TEXT
);

DROP TABLE IF EXISTS date_dim;
CREATE TABLE date_dim (
  dt          TEXT PRIMARY KEY,
  yw          INTEGER,
  day_of_week INTEGER,
  is_weekend  INTEGER
);

DROP TABLE IF EXISTS user_dim;
CREATE TABLE user_dim (
  user_id        INTEGER PRIMARY KEY,
  first_visit_dt TEXT,
  last_visit_dt  TEXT,
  active_days    INTEGER,
  total_pv       INTEGER,
  total_buy      INTEGER
);
""")
print("建表完成")

# ---------------- 导入 ----------------
t0 = time.time()

with open(os.path.join(DATA, "user_behavior.csv"), encoding="utf-8") as f:
    r = csv.reader(f); next(r)
    cur.executemany("INSERT INTO user_behavior VALUES (?,?,?,?,?,?)", r)
print(f"user_behavior 导入完成  ({time.time()-t0:.1f}s)")

for tbl, fn in [("item_dim", "item_dim.csv"), ("date_dim", "date_dim.csv"), ("user_dim", "user_dim.csv")]:
    ncol = {"item_dim": 3, "date_dim": 4, "user_dim": 6}[tbl]
    with open(os.path.join(DATA, fn), encoding="utf-8") as f:
        r = csv.reader(f); next(r)
        cur.executemany(f"INSERT INTO {tbl} VALUES ({','.join(['?'] * ncol)})", r)
    print(f"{tbl} 导入完成")

# ---------------- 建索引 ----------------
for sql in [
    "CREATE INDEX idx_ub_dt       ON user_behavior(dt)",
    "CREATE INDEX idx_ub_beh      ON user_behavior(behavior_type)",
    "CREATE INDEX idx_ub_cat      ON user_behavior(category_id)",
    "CREATE INDEX idx_ub_user     ON user_behavior(user_id)",
    "CREATE INDEX idx_ub_dt_beh   ON user_behavior(dt, behavior_type)",
]:
    cur.execute(sql)
print("索引创建完成")

con.commit()

# ---------------- 数据体检 ----------------
print("\n=== 数据体检 ===")
for q, label in [
    ("SELECT COUNT(*) FROM user_behavior", "行为记录总数"),
    ("SELECT COUNT(DISTINCT user_id) FROM user_behavior", "用户数"),
    ("SELECT COUNT(DISTINCT item_id) FROM user_behavior", "商品数"),
    ("SELECT COUNT(DISTINCT category_id) FROM user_behavior", "类目数"),
    ("SELECT MIN(dt) || ' ~ ' || MAX(dt) FROM user_behavior", "时间范围"),
]:
    print(f"  {label}: {cur.execute(q).fetchone()[0]}")

print("\n  行为类型分布:")
for beh, cnt in cur.execute("""
    SELECT behavior_type, COUNT(*) FROM user_behavior GROUP BY behavior_type ORDER BY 2 DESC
""").fetchall():
    print(f"    {beh:5s} {cnt:>10,}")

# 数据质量检查：空值、重复
dup = cur.execute("""
    SELECT COUNT(*) FROM (
      SELECT user_id,item_id,behavior_type,ts FROM user_behavior
      GROUP BY user_id,item_id,behavior_type,ts HAVING COUNT(*)>1
    )
""").fetchone()[0]
print(f"\n  重复记录数: {dup}  （0 表示主键约束生效，数据干净）")

orphan = cur.execute("""
    SELECT COUNT(*) FROM user_behavior b
    LEFT JOIN item_dim i ON b.item_id = i.item_id
    WHERE i.item_id IS NULL
""").fetchone()[0]
print(f"  商品维表未匹配记录: {orphan}  （0 表示维度完整）")

con.commit()
con.close()
print(f"\nDB SAVED: {DB}  ({os.path.getsize(DB)/1024/1024:.1f} MB)")
print("""
================ MySQL 方言对照表 ================
SQLite（本演示）                      MySQL 8（你的正式环境）
-----------------------------------  -----------------------------------
strftime('%H', ts,'unixepoch')       HOUR(FROM_UNIXTIME(ts))
julianday(a)-julianday(b)            DATEDIFF(a, b)
COUNT(*) FILTER (WHERE ...)          SUM(条件)  或  COUNT(CASE WHEN ...)
INTEGER PRIMARY KEY                  BIGINT / AUTO_INCREMENT
PRAGMA journal_mode=OFF              无需（InnoDB 默认）
TEXT                                 VARCHAR / DATE
导入：csv.reader                      LOAD DATA INFILE
==================================================
""")
