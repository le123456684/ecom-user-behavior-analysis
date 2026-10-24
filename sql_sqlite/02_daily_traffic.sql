-- ============================================================
-- 02_daily_traffic.sql  日活与流量概览（SQLite 可执行版）
-- 业务问题：平台日活趋势如何？人均浏览深度是否健康？有无异常波动？
-- 与 MySQL 8 版的唯一差异：第 2.3 段的 HOUR(FROM_UNIXTIME(ts))
--   MySQL  : HOUR(FROM_UNIXTIME(ts))
--   SQLite : CAST(strftime('%H', ts, 'unixepoch') AS INTEGER)
--   原因    : SQLite 没有 FROM_UNIXTIME，统一用 strftime 把秒级时间戳格式化
-- ============================================================

-- 2.1 日活与流量总览
-- 【讲法】一次扫描同时算出 4 个指标：uv / pv / 人均深度 / 购买人数
--         COUNT(DISTINCT CASE WHEN ... THEN user_id END) 是"条件去重计数"，
--         关键在 CASE 不满足条件时返回 NULL，而 COUNT 不计 NULL —— 所以自动只数符合条件的。
SELECT
    dt,
    COUNT(DISTINCT user_id)                     AS uv,           -- 独立访客
    SUM(behavior_type = 'pv')                   AS pv,           -- 页面浏览
    ROUND(SUM(behavior_type = 'pv')
          / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS pv_per_uv, -- 人均浏览深度
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_uv
FROM user_behavior
GROUP BY dt
ORDER BY dt;


-- 2.2 异常波动排查：找出 UV 明显低于均值的日期
-- 【讲法】窗口函数 AVG(uv) OVER () 的作用：不折叠分组，把"全期平均值"贴在每一行上，
--         这样每一行都能同时看到"我这天是多少"和"全期平均是多少"。
-- 【不用窗口函数怎么写】见下方注释块（用子查询求均值再交叉连接）。
WITH daily AS (
    SELECT dt, COUNT(DISTINCT user_id) AS uv
    FROM user_behavior
    GROUP BY dt
)
SELECT
    dt,
    uv,
    ROUND(AVG(uv) OVER (), 0) AS avg_uv,
    ROUND(uv / AVG(uv) OVER () * 100, 2) AS pct_of_avg
FROM daily
ORDER BY pct_of_avg ASC
LIMIT 10;

-- 【等价子查询写法】初学者版本，结果完全一样，面试时可以用来对照：
-- WITH daily AS (SELECT dt, COUNT(DISTINCT user_id) AS uv FROM user_behavior GROUP BY dt)
-- SELECT d.dt, d.uv, ROUND(a.avg_uv, 0) AS avg_uv,
--        ROUND(d.uv / a.avg_uv * 100, 2) AS pct_of_avg
-- FROM daily d
-- CROSS JOIN (SELECT AVG(uv) AS avg_uv FROM daily) a    -- 这段就是把"全期均值"做成一张只有一行的表
-- ORDER BY pct_of_avg ASC LIMIT 10;


-- 2.3 时段分布：一天中什么时段用户最活跃
-- 【方言差异点】ts 是秒级 Unix 时间戳，要换算成"小时"
--   MySQL : HOUR(FROM_UNIXTIME(ts))
--   SQLite: CAST(strftime('%H', ts, 'unixepoch') AS INTEGER)
-- 【讲法】SUM(SUM(pv)) OVER () 是"嵌套聚合 + 窗口"：
--         内层 SUM(pv) 按小时聚合出每小时的 pv，
--         外层 SUM(...) OVER () 再把各小时的 pv 加总得到全天总量，
--         两者相除就是"这个小时占全天的比例"。
SELECT
    CAST(strftime('%H', ts, 'unixepoch') AS INTEGER)  AS hour_of_day,
    SUM(behavior_type = 'pv')                  AS pv,
    COUNT(DISTINCT user_id)                    AS uv,
    ROUND(SUM(behavior_type = 'pv') * 100.0
          / SUM(SUM(behavior_type = 'pv')) OVER (), 2) AS pv_share_pct
FROM user_behavior
GROUP BY hour_of_day
ORDER BY hour_of_day;


-- 2.4 周末 vs 工作日对比
-- 【讲法】两段式：先用子查询算出"每天的 uv/pv"，再拿结果去关联日期维度表，
--         按 is_weekend 分组求平均。这是最标准的"先聚合到日、再聚合到类别"的思路。
SELECT
    d.is_weekend,
    CASE d.is_weekend WHEN 1 THEN '周末' ELSE '工作日' END AS day_type,
    ROUND(AVG(t.daily_uv), 0)  AS avg_uv,
    ROUND(AVG(t.daily_pv), 0)  AS avg_pv
FROM (
    SELECT dt,
           COUNT(DISTINCT user_id)   AS daily_uv,
           SUM(behavior_type = 'pv') AS daily_pv
    FROM user_behavior
    GROUP BY dt
) t
JOIN date_dim d ON t.dt = d.dt
GROUP BY d.is_weekend;
