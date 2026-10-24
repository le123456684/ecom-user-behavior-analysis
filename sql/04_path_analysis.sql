-- ============================================================
-- 04_path_analysis.sql  用户行为路径分析
-- 业务问题：用户在购买前经过哪些行为组合？哪条路径转化最高？
-- 考察点：CTE(WITH) + 窗口函数 LAG / ROW_NUMBER / 转移矩阵
-- ============================================================

USE ecom_analysis;

-- 4.1 行为转移矩阵：上一步行为 → 下一步行为
-- 用途：看清用户在整个平台上的流转规律
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
WHERE prev_behavior IS NOT NULL
GROUP BY from_step, to_step
ORDER BY transitions DESC;


-- 4.2 用户的完整行为序列（仅看购买用户）
-- 用途：观察典型购买路径
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
        GROUP_CONCAT(behavior_type ORDER BY step_no SEPARATOR '>') AS path
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
-- 业务含义：用户往往"最后一步"做了什么才成交？指导推荐与促销策略
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
