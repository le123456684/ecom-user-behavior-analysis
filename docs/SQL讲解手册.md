# SQL 讲解手册 · 电商用户行为分析项目

> 用途：把 `sql_sqlite/` 里每段代码讲到"面试官随便指一行，老大都能说清"。
> 配套：`sql_sqlite/` 是可直接跑的 SQLite 版（22 条语句全部实测通过，总耗时 11.3 秒）；
>       `sql/` 是 MySQL 8 版（4 条依赖方言函数，本机跑不通，差异见第四部分）。

---

## 第一部分：3 分钟搞懂窗口函数

### 一句话

> **窗口函数 = 不折叠分组的聚合。**

### 展开讲

普通 `GROUP BY`：把多行压成一行，**明细消失**，只剩汇总值。

```
用户A 100 元  ┐
用户B 200 元  ├─→ 平均 150 元   ← 三个人的明细没了
用户C 150 元  ┘
```

窗口函数：**明细全留着**，在旁边多出一列算好的汇总值。

```
用户A 100 元   平均150    ← 明细还在
用户B 200 元   平均150    ← 每行都带着"全组平均"
用户C 150 元   平均150
```

**为什么需要它**：因为很多业务问题问的是"**我** 和 **整体** 比怎么样"——我这一天比全期平均高低多少、我这个类目占全站流量多少、我这一步是第几步。这类问题必须先保住明细行，`GROUP BY` 做不到。

### 语法怎么读

```sql
函数名(...) OVER ( PARTITION BY 按谁分组  ORDER BY 组内怎么排序 )
```

| 部分 | 作用 | 类比 |
|---|---|---|
| `OVER` | 标志：这是个窗口函数 | 开门 |
| `PARTITION BY` | 按什么分组（**但不折叠**） | 相当于"再分班"，每个班各算各的 |
| `ORDER BY` | 组内排序 | 决定"上一行是谁"、"累计到哪为止" |
| 空的 `OVER ()` | 整张表算一组 | 全班一起算 |

**关键点：`PARTITION BY` 和 `GROUP BY` 长得很像，但结果完全不同——前者不减少行数，后者减少行数。**

---

## 第二部分：项目里用到的 9 个用法（逐个拆）

### ① `LAG(behavior_type) OVER (PARTITION BY user_id ORDER BY ts)`

**在哪用**：`04_path_analysis.sql` 4.1 和 4.4
**解决什么问题**：想知道"这个用户**上一步**做了什么"。

**怎么读**：按用户分组、按时间排序，然后取"我这一行的上一行"的值。

```
user_id=1  ts=100  pv    prev=NULL
user_id=1  ts=200  cart  prev=pv      ← 上一行是 pv
user_id=1  ts=300  buy   prev=cart    ← 上一行是 cart
```

于是每一行都同时带着"我做了什么"和"我上一步做了什么"，相邻两行一配就是一次行为转移，`GROUP BY` 计数就得到转移矩阵。

**不用窗口函数怎么写**（这是面试必问的"不学新语法怎么实现"）：

```sql
-- 用自连接找"上一步"：难点是"上一步"可能匹配到多条更早的记录
SELECT cur.behavior_type, prev.behavior_type
FROM user_behavior cur
LEFT JOIN user_behavior prev
  ON cur.user_id = prev.user_id
 AND prev.ts = (SELECT MAX(p2.ts) FROM user_behavior p2
                WHERE p2.user_id = cur.user_id AND p2.ts < cur.ts)
```

**面试可以这样说**：`LAG` 就是把"取上一行"这个动作变成一句话。用子查询也能实现，但要在 `ON` 里再套一层 `MAX` 子查询，可读性和性能都差。

---

### ② `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts)`

**在哪用**：`04_path_analysis.sql` 4.2、4.3
**解决什么问题**：给每个用户的每条行为**编号**（这是第 1 步、第 2 步……）。

**怎么读**：按用户分组、按时间排序，从 1 开始发号。

**为什么需要**：因为要"取前 5 步"。没有编号，你没法表达"前 5 步"这个概念。

**延伸**：`ROW_NUMBER` 是本项目里的"分组取 TopN"工具。面试爱问的"每个用户取最新一条"，标准答案就是：

```sql
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts DESC) rn
  FROM user_behavior
) t WHERE rn = 1;
```

**这句一定要会**，它是窗口函数最高频的面试题，也是闲鱼/接单场景里最常见的需求（"每组取最新一条"）。

---

### ③ `COUNT(*) OVER (PARTITION BY user_id)`

**在哪用**：`04_path_analysis.sql` 4.2
**解决什么问题**：知道"这个用户总共多少步"，用来筛"短路径"。

**怎么读**：按用户分组数行数，但**不折叠**，所以每一行都带上"我所在的这个用户一共有几步"。

**注意**：`COUNT(*) OVER (PARTITION BY user_id)` 和 `COUNT(*) GROUP BY user_id` 数值一样，区别是前者保留明细行，后者只剩一行。

---

### ④ `AVG(uv) OVER ()`（空括号）

**在哪用**：`02_daily_traffic.sql` 2.2
**解决什么问题**：每一行都带上"全期平均 UV"，用来判断某天是不是异常。

**怎么读**：空括号 = 整张表一组，所以 `AVG(uv) OVER ()` 就是全表平均，贴在每一行上。

**等价子查询写法**：

```sql
SELECT d.dt, d.uv, a.avg_uv
FROM daily d
CROSS JOIN (SELECT AVG(uv) AS avg_uv FROM daily) a   -- 做成只有一行的表，再交叉连接
```

**为什么两种都行**：`CROSS JOIN` 一行表等于"给每一行贴同一个值"，效果和窗口函数一样，只是多写一层。

---

### ⑤ `SUM(SUM(pv)) OVER ()`（嵌套聚合 + 窗口）

**在哪用**：`02_daily_traffic.sql` 2.3、`06_category.sql` 6.1
**解决什么问题**：算"这个小时/这个类目占全天的比例"。

**怎么读**（分两步看）：

1. 内层 `SUM(pv)` —— 普通的按小时 `GROUP BY` 聚合，给出每小时的 pv
2. 外层 `SUM(...) OVER ()` —— 把各小时的 pv 再加一遍，得到全天总量

**为什么不直接写 `SUM(pv) / 总数`**：因为在 `GROUP BY` 之后，`SUM(pv)` 已经是每小时的量了，此时再想拿"总量"就必须从聚合结果里再聚合一次——这就是嵌套的原因。

**这是全项目最难的一句**，面试官大概率会指着它问。答案就是上面这两步。

---

### ⑥ `SUM(COUNT(DISTINCT user_id)) OVER ()`

**在哪用**：`04_path_analysis.sql` 4.4
**解决什么问题**：算"购买前各行为类型的人数占比"。

**怎么读**：先按"上一步行为"分组算出各类人数（`COUNT(DISTINCT user_id)`），再用窗口把这些人数加总，就是总人数，两者相除就是占比。

**等价子查询写法**（更容易讲）：

```sql
WITH t AS (
  SELECT prev_behavior, COUNT(DISTINCT user_id) AS u
  FROM pre_buy WHERE behavior_type='buy' AND prev_behavior IS NOT NULL
  GROUP BY prev_behavior
)
SELECT prev_behavior, u, ROUND(u*100.0/(SELECT SUM(u) FROM t), 2) AS pct FROM t;
```

---

### ⑦ `SUM(buy_u) OVER ()`

**在哪用**：`03_funnel.sql` 3.5
**解决什么问题**：把"全站合计"贴到每个类目上，用来算全站平均转化率。

**注意口径**：这里算的是**加权平均**（总购买 ÷ 总浏览），不是"各类目转化率的简单平均"。两者结果不同，后者会被小样本类目拉偏——这就是**辛普森悖论**，面试高频考点。

---

### ⑧ `SUM(COUNT(*)) OVER ()`

**在哪用**：`05_retention.sql` 5.4
**解决什么问题**：用户分层后，算每层占多少比例。

**怎么读**：`COUNT(*)` 是每层人数（`GROUP BY user_tier` 之后），`SUM(...) OVER ()` 是各层人数之和 = 总人数。

---

### ⑨ `FILTER (WHERE behavior_type = 'pv')`

**在哪用**：`05_retention.sql` 5.4
**解决什么问题**：带条件的计数。

**注意方言**：PostgreSQL / SQLite 3.30+ 支持；**MySQL 8 不支持**，要换成 `SUM(CASE WHEN behavior_type='pv' THEN 1 ELSE 0 END)`。

**这是面试可以主动提的点**："我知道这个语法不是所有数据库都支持，MySQL 里要写成 CASE WHEN。"

---

## 第三部分：CTE（WITH 子句）怎么讲

**一句话**：`WITH 名字 AS (查询)` 就是把一段查询起个名字，后面的查询可以直接用这个名字，相当于**临时的视图**。

**为什么用它，三个理由**：

1. **可读性**：留存分析那个查询，如果不用 CTE 就得写成三层嵌套子查询，从里往外读很痛苦
2. **复用**：`funnel` 这个 CTE 在 3.2 里被 `UNION ALL` 用了 4 次
3. **分步调试**：可以先把 CTE 单独跑一下看数据对不对，再接后面的

**和临时表（CREATE TEMPORARY TABLE）的区别**：

| | CTE | 临时表 |
|---|---|---|
| 生命周期 | 只在当前这条查询里有效 | 会话结束前一直存在 |
| 能不能建索引 | 不能 | 能 |
| 适合 | 中小数据量的分步计算 | 大数据量、需要反复访问 |

**面试可以这样说**："这个项目我用 CTE 主要是为了可读性和复用；如果数据量上了亿级、同一个中间结果要反复扫，我会改成临时表并建索引。"

---

## 第四部分：方言对照表（MySQL 8 vs SQLite）

这部分是加分项——**能说清方言差异，说明真跑过，不是抄的。**

| 功能 | MySQL 8 | SQLite | 说明 |
|---|---|---|---|
| 秒级时间戳转小时 | `HOUR(FROM_UNIXTIME(ts))` | `CAST(strftime('%H', ts, 'unixepoch') AS INTEGER)` | SQLite 无 FROM_UNIXTIME |
| 日期相差天数 | `DATEDIFF(a, b)` | `CAST(julianday(a) - julianday(b) AS INTEGER)` | 儒略日数相减 |
| 字符串拼接聚合 | `GROUP_CONCAT(x ORDER BY y SEPARATOR '>')` | `GROUP_CONCAT(x, '>' ORDER BY y)` | 参数顺序不同 |
| 条件聚合 | `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` | 同左，或 `COUNT(*) FILTER (WHERE ...)` | FILTER 在 MySQL 不支持 |
| 建库 | `CREATE DATABASE` + `USE` | 无（SQLite 是文件库） |  |
| 自增主键 | `AUTO_INCREMENT` | `INTEGER PRIMARY KEY AUTOINCREMENT` |  |
| 分页 | `LIMIT n OFFSET m` | 同左 | 两边一致 |
| 窗口函数 | 8.0+ 完整支持 | 3.25+ 支持 | 老版本 MySQL 5.7 不支持窗口函数 |

---

## 第五部分：面试可能追问的 8 个问题（标准答案）

**Q1：你这些 SQL 在什么环境下跑的？**
> "数据管道跑在 SQLite 上（零依赖、克隆即用），同时写了 MySQL 8 版。有几处方言差异，比如时间戳转小时、日期差、字符串聚合，我都做了对照。"

**Q2：为什么用窗口函数不用子查询？**
> "主要是可读性和性能。比如转移矩阵用 LAG 一句话就表达了，用子查询要在 ON 条件里再套一层 MAX 子查询。另外窗口函数只扫一次表，多个窗口可以一次算完。"

**Q3：ROW_NUMBER 和 RANK 有什么区别？**
> "遇到并列时 RANK 会跳号（1,1,3），ROW_NUMBER 不跳（1,2,3），DENSE_RANK 不跳号也不留空（1,1,2）。取 TopN 一般用 ROW_NUMBER，因为能保证每个组恰好取 N 条。"

**Q4：你这个复购率的口径是怎么定的？**
> "购买次数 ≥ 2 的用户 ÷ 有购买行为的用户。分母特意排除了没买过的人，因为没买过谈不上复购。如果按全部用户算，复购率会被稀释得没有意义。"

**Q5：为什么要 HAVING browse_u >= 100？**
> "过滤样本量不足的类目。只有几十个访客的类目，转化率 33% 还是 0% 都是噪音，不是洞察。这个门槛本身没有绝对标准，取决于数据和业务容忍度。"

**Q6：全站平均转化率你是怎么算的？**
> "用的是加权平均（总购买人数 ÷ 总浏览人数），不是各类目转化率的简单平均。后者会被小样本类目拉偏，这是辛普森悖论。"

**Q7：数据量多大？跑得动吗？**
> "51.6 万条行为记录、2 万用户、2000 个商品、30 天、10 个类目。整个 22 条查询串行跑完 11 秒左右，单条最慢的是路径分析那两条（约 1.5 秒）。数据量再大一个量级就会考虑建索引或者预聚合。"

**Q8：这个项目有没有什么不足？**
> "有三点：一是数据是程序化生成的模拟数据，不是真实业务数据，用来验证方法论可以，但不能说它是真实案例；二是路径分析里的 rn 列算了但没用到，是冗余；三是爆款识别原来阈值写 500，但数据集里最大 pv 只有 468，会永远返回空表，我改成了按分位数取 300。"
>
> **这个回答是整个面试里最值钱的一句**——主动指出自己的问题，比被问出来强一百倍。

---

## 第六部分：老大的自检清单

面试前把这 6 条过一遍，全过就可以上了：

- [ ] 能一句话解释窗口函数和 GROUP BY 的区别（不折叠分组）
- [ ] 能闭卷手写"每个用户取最新一条"的 ROW_NUMBER 写法
- [ ] 能说清 `SUM(SUM(pv)) OVER ()` 这两层分别在干什么
- [ ] 能说出 3 个以上 MySQL / SQLite 的方言差异
- [ ] 能说清复购率、留存的**口径**（不只是会写 SQL）
- [ ] 能主动说出这个项目的 3 个不足

---

## 附：本次修正记录

| 问题 | 原来 | 现在 | 影响 |
|---|---|---|---|
| 时间戳转小时 | `HOUR(FROM_UNIXTIME(ts))` | `CAST(strftime('%H', ts,'unixepoch') AS INTEGER)` | SQLite 下原本报错 |
| 日期差 | `DATEDIFF(a,b)` | `CAST(julianday(a)-julianday(b) AS INTEGER)` | 留存两条原本报错 |
| 字符串聚合 | `GROUP_CONCAT(x ORDER BY y SEPARATOR '>')` | `GROUP_CONCAT(x, '>' ORDER BY y)` | 路径频次原本报错 |
| 爆款阈值 | `HAVING pv >= 500` | `HAVING pv >= 300` | 原本永远返回空表（最大 pv 468） |

**修正前**：22 条语句中 18 条可执行、4 条报错，另有 1 条静默返回空表。
**修正后**：**22 条全部通过，0 报错，0 空表。**
