# -*- coding: utf-8 -*-
"""
07_verify_sql.py
校验 sql_sqlite/ 目录下所有 SQL 语句能否在 ecom.db 上真正跑通。

用途：
  1. 面试前自证 —— 直接跑一遍，把结果截给面试官看
  2. 改完 SQL 后的回归检查 —— 防止改一处崩另一处
  3. 检查"静默空表" —— 语法没错但结果为空，这类问题不报错所以最容易被忽略

用法：
  python 07_verify_sql.py

判定标准：
  - 报错 = 失败
  - 返回 0 行 = 警告（可能是阈值不合理，也可能是业务上真的没有，需人工确认）
"""
import sys, io, os, re, sqlite3, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(BASE, "sql_sqlite")
DB = os.path.join(BASE, "ecom.db")

if not os.path.exists(DB):
    print(f"❌ 找不到数据库 {DB}\n   请先运行：python 02_build_db.py")
    sys.exit(1)

files = sorted(f for f in os.listdir(SQL_DIR) if f.endswith(".sql"))
con = sqlite3.connect(DB)

ok = fail = empty = 0
total_ms = 0.0
failures = []

print("=" * 62)
print("SQL 校验开始")
print("=" * 62)

for fn in files:
    txt = open(os.path.join(SQL_DIR, fn), encoding="utf-8").read()
    body = "\n".join(l for l in txt.splitlines() if not l.strip().startswith("--"))
    stmts = [s.strip() for s in body.split(";") if s.strip()]

    for i, s in enumerate(stmts, 1):
        t0 = time.time()
        try:
            rows = con.execute(s).fetchall()
            ms = (time.time() - t0) * 1000
            total_ms += ms
            if not rows:
                empty += 1
                print(f"⚠️  {fn} #{i}  0 行（空表，需人工确认阈值）  {ms:.0f}ms")
            else:
                ok += 1
                print(f"✅ {fn} #{i}  {len(rows)} 行  {ms:.0f}ms")
        except Exception as e:
            fail += 1
            msg = f"{type(e).__name__}: {str(e)[:80]}"
            failures.append((f"{fn} #{i}", msg))
            print(f"❌ {fn} #{i}  {msg}")

print("=" * 62)
print(f"通过 {ok} 条 / 失败 {fail} 条 / 空表 {empty} 条，总耗时 {total_ms/1000:.1f}s")

if failures:
    print("\n失败明细：")
    for k, v in failures:
        print(f"  {k}: {v}")
    sys.exit(1)

if empty:
    print("\n⚠️  存在空表语句，请确认阈值是否与数据规模匹配")

print("\n✅ 全部通过"
      if not empty else "\n✅ 无报错（有空表需要确认）")
