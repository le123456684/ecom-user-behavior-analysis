-- ============================================================
-- 02_daily_traffic.sql  日活与流量概览
-- 业务问题：平台的日活趋势如何？人均浏览深度是否健康？有无异常波动？
-- 考察点：COUNT DISTINCT / 按日聚合 / 派生指标
-- ============================================================

USE ecom_analysis;

-- 2.1 日活与流量总览
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
-- 说明：用窗口函数算全期均值，再用子查询做对比
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


-- 2.3 时段分布：一天中什么时段用户最活跃
-- 用途：为运营推送时间提供依据
SELECT
    HOUR(FROM_UNIXTIME(ts))                    AS hour_of_day,
    SUM(behavior_type = 'pv')                  AS pv,
    COUNT(DISTINCT user_id)                    AS uv,
    ROUND(SUM(behavior_type = 'pv') * 100.0
          / SUM(SUM(behavior_type = 'pv')) OVER (), 2) AS pv_share_pct
FROM user_behavior
GROUP BY hour_of_day
ORDER BY hour_of_day;


-- 2.4 周末 vs 工作日对比
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
