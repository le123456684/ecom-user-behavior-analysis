-- ============================================================
-- 05_retention.sql  留存分析
-- 业务问题：用户来了之后还会回来吗？次日/7 日留存是多少？
-- 考察点：CTE + 自关联 + DATEDIFF + 留存口径设计
-- ============================================================

USE ecom_analysis;

-- 5.1 次日留存率（按注册日分组）
WITH first_day AS (
    SELECT user_id, MIN(dt) AS reg_dt
    FROM user_behavior
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT user_id, dt
    FROM user_behavior
)
SELECT
    f.reg_dt,
    COUNT(DISTINCT f.user_id) AS new_users,
    COUNT(DISTINCT CASE WHEN DATEDIFF(a.dt, f.reg_dt) = 1
                        THEN a.user_id END) AS retained_d1,
    ROUND(COUNT(DISTINCT CASE WHEN DATEDIFF(a.dt, f.reg_dt) = 1
                              THEN a.user_id END) * 100.0
          / NULLIF(COUNT(DISTINCT f.user_id), 0), 2) AS d1_retention_pct
FROM first_day f
LEFT JOIN activity a ON f.user_id = a.user_id
GROUP BY f.reg_dt
ORDER BY f.reg_dt;


-- 5.2 留存矩阵（第 N 日留存，N = 0..7）
-- 说明：这是标准的留存表做法，能直接喂给 Tableau 画留存曲线
WITH first_day AS (
    SELECT user_id, MIN(dt) AS reg_dt
    FROM user_behavior
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT user_id, dt
    FROM user_behavior
),
cohort AS (
    SELECT
        f.reg_dt,
        DATEDIFF(a.dt, f.reg_dt) AS day_n,
        COUNT(DISTINCT f.user_id) AS users
    FROM first_day f
    JOIN activity a ON f.user_id = a.user_id
    WHERE DATEDIFF(a.dt, f.reg_dt) BETWEEN 0 AND 7
    GROUP BY f.reg_dt, day_n
)
SELECT
    reg_dt,
    SUM(CASE WHEN day_n = 0 THEN users ELSE 0 END) AS d0,
    SUM(CASE WHEN day_n = 1 THEN users ELSE 0 END) AS d1,
    SUM(CASE WHEN day_n = 2 THEN users ELSE 0 END) AS d2,
    SUM(CASE WHEN day_n = 3 THEN users ELSE 0 END) AS d3,
    SUM(CASE WHEN day_n = 7 THEN users ELSE 0 END) AS d7
FROM cohort
GROUP BY reg_dt
ORDER BY reg_dt;


-- 5.3 复购率
-- 口径：购买次数 >= 2 的用户 ÷ 有购买行为的用户
WITH buy_cnt AS (
    SELECT user_id, COUNT(*) AS buy_times
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id
)
SELECT
    COUNT(*)                                            AS buyer_users,
    SUM(CASE WHEN buy_times >= 2 THEN 1 ELSE 0 END)     AS repeat_buyers,
    ROUND(SUM(CASE WHEN buy_times >= 2 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0), 2)                     AS repeat_rate_pct
FROM buy_cnt;


-- 5.4 用户活跃度分层
-- 业务含义：区分高价值用户与沉睡用户，为运营分层触达提供依据
WITH u AS (
    SELECT
        user_id,
        COUNT(*) FILTER (WHERE behavior_type = 'pv')  AS pv_cnt,
        COUNT(*) FILTER (WHERE behavior_type = 'buy') AS buy_cnt
    FROM user_behavior
    GROUP BY user_id
)
SELECT
    CASE
        WHEN buy_cnt >= 3                     THEN 'A-高频购买'
        WHEN buy_cnt BETWEEN 1 AND 2          THEN 'B-有过购买'
        WHEN pv_cnt >= 20                     THEN 'C-高活跃浏览'
        WHEN pv_cnt BETWEEN 5 AND 19          THEN 'D-一般活跃'
        ELSE                                       'E-低活/沉默'
    END AS user_tier,
    COUNT(*) AS users,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM u
GROUP BY user_tier
ORDER BY users DESC;

-- 注：FILTER 子句 MySQL 8 不支持时，改用 SUM(behavior_type = 'pv')
