-- ============================================================
-- 04_path_analysis.sql  用户行为路径分析（SQLite 可执行版）
-- 业务问题：用户在购买前经过哪些行为组合？哪条路径转化最高？
-- 核心：LAG / ROW_NUMBER / 转移矩阵 / 序列压缩成字符串
-- 与 MySQL 8 版差异（第 4.3 段）：
--   MySQL  : GROUP_CONCAT(behavior_type ORDER BY step_no SEPARATOR '>')
--   SQLite : GROUP_CONCAT(behavior_type, '>' ORDER BY step_no)
--   注意参数顺序不同：MySQL 是"字段 + ORDER BY + SEPARATOR 关键字"，
--   SQLite 是"字段, 分隔符 + ORDER BY"（需要 SQLite 3.44+）
-- ============================================================

-- 4.1 行为转移矩阵：上一步行为 → 下一步行为
-- 【讲法】LAG(字段) OVER (PARTITION BY 用户 ORDER BY 时间)
--         = "按用户分组、按时间排序后，取我这一行的上一行的值"。
--         于是每一行都同时带着"我做了什么"和"我上一步做了什么"，
--         两句一配就是一个转移对，GROUP BY 后计数就是转移矩阵。
-- 【不用窗口函数怎么写】用两次表自己连自己（自连接），见下方注释：
--   SELECT cur.behavior_type, prev.behavior_type, ...
--   FROM user_behavior cur
--   LEFT JOIN user_behavior prev
--     ON cur.user_id = prev.user_id AND prev.ts < cur.ts   -- 找"上一步"
--   ...但 prev 可能匹配到多条（所有更早的行为），还要再取最大的那个 ts，
--   写成子查询就是：prev.ts = (SELECT MAX(ts) FROM user_behavior p2
--                              WHERE p2.user_id = cur.user_id AND p2.ts < cur.ts)
--   这一层嵌套就是 LAG 存在的原因：它把"取上一行"这件事变成了一句。
WITH user_seq AS (
    SELECT
        user_id,
        behavior_type,
        ts,
        LAG(behavior_type) OVER (PARTITION BY user_id ORDER BY ts) AS prev_behavior
    FROM user_behavior
)
SELECT
    prev_behavior AS from_step,
    behavior_type AS to_step,
    COUNT(*)                    AS transitions,
    COUNT(DISTINCT user_id)     AS users
FROM user_seq
WHERE prev_behavior IS NOT NULL      -- 每个用户第一步没有"上一步"，剔除
GROUP BY from_step, to_step
ORDER BY transitions DESC;


-- 4.2 用户的完整行为序列（仅看购买用户）
-- 【讲法】两个窗口函数各解决一个问题：
--   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts) = 这是该用户的第几步
--   COUNT(*)     OVER (PARTITION BY user_id)             = 该用户总共几步
--   前者给"位置"，后者给"长度"。有了这两个就能筛"总步数 ≤ 8 的短路径"，
--   因为长路径（几百步）噪音太大，看不出版式。
WITH buy_users AS (
    SELECT DISTINCT user_id
    FROM user_behavior
    WHERE behavior_type = 'buy'
),
seq AS (
    SELECT
        b.user_id,
        b.behavior_type,
        b.ts,
        ROW_NUMBER() OVER (PARTITION BY b.user_id ORDER BY b.ts)  AS step_no,
        COUNT(*)     OVER (PARTITION BY b.user_id)                AS total_steps
    FROM user_behavior b
    JOIN buy_users u ON b.user_id = u.user_id
)
SELECT user_id, step_no, total_steps, behavior_type
FROM seq
WHERE total_steps <= 8       -- 只看短路径，长路径噪音大
ORDER BY user_id, step_no
LIMIT 200;


-- 4.3 计算各条路径的出现频次（把序列压成字符串再聚合）
-- 【方言差异点】MySQL 用 SEPARATOR 关键字，SQLite 用逗号位置传分隔符
-- 【讲法】思路是"两步压缩"：
--   第一步 ROW_NUMBER 给每个用户的每条行为编号（决定顺序）
--   第二步 GROUP_CONCAT 把同一用户前 5 步的行为按编号拼成 'pv>cart>buy' 这种字符串
--   最后按字符串分组计数，就得到"有多少人走了这条路径"
--   GROUP_CONCAT 里的 ORDER BY step_no 是关键：不加它，拼接顺序不保证，路径就乱了。
WITH seq AS (
    SELECT
        user_id,
        behavior_type,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts) AS step_no
    FROM user_behavior
    WHERE user_id IN (SELECT DISTINCT user_id FROM user_behavior WHERE behavior_type = 'buy')
),
path_str AS (
    SELECT
        user_id,
        GROUP_CONCAT(behavior_type, '>' ORDER BY step_no) AS path
    FROM seq
    WHERE step_no <= 5      -- 只取前 5 步，控制路径长度
    GROUP BY user_id
)
SELECT
    path,
    COUNT(*) AS user_cnt
FROM path_str
GROUP BY path
ORDER BY user_cnt DESC
LIMIT 20;


-- 4.4 购买前一步行为的分布
-- 【讲法】这段是全项目信息量最高的一句，三个函数配合：
--   LAG(behavior_type)  = 上一步是什么（用来找"买之前做了什么"）
--   ROW_NUMBER() DESC   = 从后往前编号（这段其实没被用到，见下方说明）
--   SUM(COUNT(DISTINCT user_id)) OVER () = 先按"上一步行为"分组算人数，
--                                        再对这些人求和得到总人数，用于算占比
-- 【要点】WHERE behavior_type = 'buy' 是先筛出购买行，再取它们的 prev_behavior，
--         所以得到的是"购买动作的前一步"分布，业务含义：临门一脚前用户在看什么。
-- 【小瑕疵，面试可主动说】rn 这一列算出来了但没用到，属于可删的冗余列。
WITH pre_buy AS (
    SELECT
        user_id,
        behavior_type,
        LAG(behavior_type) OVER (PARTITION BY user_id ORDER BY ts) AS prev_behavior,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts DESC)  AS rn
    FROM user_behavior
)
SELECT
    prev_behavior AS step_before_buy,
    COUNT(DISTINCT user_id) AS users,
    ROUND(COUNT(DISTINCT user_id) * 100.0
          / SUM(COUNT(DISTINCT user_id)) OVER (), 2) AS pct
FROM pre_buy
WHERE behavior_type = 'buy'
  AND prev_behavior IS NOT NULL
GROUP BY prev_behavior
ORDER BY users DESC;

-- 【等价子查询写法（4.4 的 pct 列）】不嵌套聚合时的经典写法：
-- 先算完各分组人数，再除以总人数：
--   WITH t AS (SELECT prev_behavior, COUNT(DISTINCT user_id) u FROM pre_buy
--              WHERE behavior_type='buy' AND prev_behavior IS NOT NULL
--              GROUP BY prev_behavior)
--   SELECT prev_behavior, u, ROUND(u*100.0/(SELECT SUM(u) FROM t), 2) AS pct FROM t;
