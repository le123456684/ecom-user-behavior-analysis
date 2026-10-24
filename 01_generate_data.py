# -*- coding: utf-8 -*-
"""
01_generate_data.py  (v2 — 修正两个真实性问题)

v1 的两个问题（真实项目中同样会踩到）：
  ① 时段分布错位：ts 是 UTC 纪元值，直接按 UTC 解读会偏移 8 小时
     → v2 明确：数据存标准 UTC 纪元值；展示北京时间需在 SQL 中 +8h
       （注意：datetime.timestamp() 已按本地时区转换，生成时不可再手动偏移，
         否则会「负负得正」变成双重偏移——这个坑我实际踩了一次）
  ② 留存曲线不衰减：活跃日均匀撒在整个窗口，用户天天都在
     → v2 改为「首访后按衰减概率激活」，模拟注意力自然衰减

v1 的转化率 37% 也不真实（真实电商约 5~8%）→ v2 下调购买概率
"""
import sys, io, os, csv, random, datetime
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
random.seed(20260926)

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "data")
os.makedirs(OUT_DIR, exist_ok=True)

START = datetime.date(2025, 11, 1)
DAYS = 30
N_USERS = 20000
TZ_OFFSET = 8 * 3600   # UTC+8

# (类目ID, 名称, 流量权重, 转化系数, 加购系数)
CATEGORIES = [
    (1,  "女装",      0.16, 1.15, 1.20),
    (2,  "男装",      0.09, 0.95, 0.95),
    (3,  "数码电子",  0.20, 0.45, 0.65),   # ← 高流量 · 低转化（核心机会点）
    (4,  "食品生鲜",  0.11, 1.40, 1.30),
    (5,  "母婴用品",  0.07, 1.30, 1.15),
    (6,  "运动户外",  0.08, 0.85, 0.95),
    (7,  "美妆个护",  0.13, 1.55, 1.35),   # ← 高流量 · 高转化（健康标杆）
    (8,  "图书文娱",  0.05, 1.10, 1.00),
    (9,  "家居家装",  0.04, 1.95, 1.60),   # ← 低流量 · 高转化（小众高潜）
    (10, "汽车用品",  0.07, 0.70, 0.85),
]
CAT_W = [c[2] for c in CATEGORIES]
CAT_META = {c[0]: {"name": c[1], "conv": c[3], "cart": c[4]} for c in CATEGORIES}

ITEMS_BY_CAT = {}
_iid = 100000
for cid, *_ in CATEGORIES:
    ids = []
    for _ in range(200):
        _iid += 1
        ids.append(_iid)
    ITEMS_BY_CAT[cid] = ids

# 分层：(名称, 占比, 每日行为数, 强度, 次日起活跃概率, 活跃衰减率, 行为概率(pv,fav,cart,buy))
TIERS = [
    ("A-高频购买",   0.015, (15, 35), 2.4, 0.75, 0.97, (0.58, 0.09, 0.14, 0.120)),
    ("B-有过购买",   0.050, (10, 26), 1.9, 0.65, 0.93, (0.65, 0.10, 0.13, 0.030)),
    ("C-高活跃浏览", 0.180, (8, 22),  1.7, 0.55, 0.88, (0.84, 0.09, 0.06, 0.0010)),
    ("D-一般活跃",   0.450, (4, 12),  1.0, 0.45, 0.80, (0.89, 0.06, 0.04, 0.0004)),
    ("E-低活沉默",   0.305, (1, 5),   0.5, 0.25, 0.65, (0.95, 0.03, 0.015, 0.0001)),
]
TIER_MAP = {t[0]: t for t in TIERS}


def pick_tier():
    r, acc = random.random(), 0.0
    for t in TIERS:
        acc += t[1]
        if r <= acc:
            return t[0]
    return TIERS[-1][0]


def weighted_cat():
    return random.choices([c[0] for c in CATEGORIES], weights=CAT_W, k=1)[0]


def pick_behavior(probs, cat_id):
    pv, fav, cart, buy = probs
    cart *= CAT_META[cat_id]["cart"]
    buy *= CAT_META[cat_id]["conv"]
    total = pv + fav + cart + buy
    r = random.random() * total
    if r < pv:   return "pv"
    r -= pv
    if r < fav:  return "fav"
    r -= fav
    if r < cart: return "cart"
    return "buy"


# 活跃时段权重（本地时间）：晚 19-23 点为高峰
HOUR_W = [3,1,1,1,1,1, 2,4,6,8,9,10, 10,9,9,9,10,12, 14,18,22,24,20,10]

rows = []
u_days = defaultdict(set)
u_pv, u_buy = defaultdict(int), defaultdict(int)
u_first, u_last = {}, {}

for uid in range(1, N_USERS + 1):
    tier = pick_tier()
    name, _, (bmin, bmax), intensity, base_p, decay, probs = TIER_MAP[tier]

    first = random.randint(0, DAYS - 1)

    # ---- 活跃日：首访后按衰减概率激活，模拟注意力衰减 ----
    active = [first]
    for off in range(first + 1, DAYS):
        if random.random() < base_p * (decay ** (off - first)):
            active.append(off)

    fav_cats = [weighted_cat() for _ in range(random.randint(1, 3))]

    for off in active:
        d = START + datetime.timedelta(days=off)
        is_wk = 1 if d.isoweekday() >= 6 else 0
        wk_uplift = 1.18 if is_wk else 1.0          # 周末活跃度提升
        n_beh = max(1, int(random.randint(bmin, bmax) * intensity / 1.8 * wk_uplift))
        for _ in range(n_beh):
            cat = random.choice(fav_cats) if random.random() < 0.7 else weighted_cat()
            it = random.choice(ITEMS_BY_CAT[cat])
            beh = pick_behavior(probs, cat)

            hour = random.choices(range(24), weights=HOUR_W, k=1)[0]
            # 本地时间 → 标准 UTC 纪元值（timestamp() 自动完成时区换算，勿再手动偏移）
            local = datetime.datetime(d.year, d.month, d.day, hour,
                                      random.randint(0, 59), random.randint(0, 59))
            ts = int(local.timestamp())

            rows.append((uid, it, cat, beh, ts, d.isoformat()))
            u_days[uid].add(d.isoformat())
            if beh == "pv":  u_pv[uid] += 1
            elif beh == "buy": u_buy[uid] += 1

    u_first[uid] = min(u_days[uid])
    u_last[uid] = max(u_days[uid])

print("生成行为记录数:", len(rows))

def write(fn, header, data):
    p = os.path.join(OUT_DIR, fn)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(data)
    print("SAVED:", p)

write("user_behavior.csv", ["user_id", "item_id", "category_id", "behavior_type", "ts", "dt"], rows)
write("user_dim.csv", ["user_id", "first_visit_dt", "last_visit_dt", "active_days", "total_pv", "total_buy"],
      [[u, u_first[u], u_last[u], len(u_days[u]), u_pv[u], u_buy[u]] for u in sorted(u_days)])
write("date_dim.csv", ["dt", "yw", "day_of_week", "is_weekend"],
      [[(START + datetime.timedelta(days=i)).isoformat(),
        (START + datetime.timedelta(days=i)).isocalendar()[1],
        (START + datetime.timedelta(days=i)).isoweekday(),
        1 if (START + datetime.timedelta(days=i)).isoweekday() >= 6 else 0] for i in range(DAYS)])
write("item_dim.csv", ["item_id", "category_id", "category_name"],
      [[i, cid, CAT_META[cid]["name"]] for cid, ids in ITEMS_BY_CAT.items() for i in ids])

bc = Counter(r[3] for r in rows)
print("\n行为分布:", dict(bc))
buyers = sum(1 for u in u_days if u_buy[u] > 0)
print(f"用户数: {len(u_days)} | 有购买行为用户: {buyers} ({buyers/len(u_days)*100:.2f}%)")
print("活跃天数分布:", dict(sorted(Counter(len(v) for v in u_days.values()).items())))
