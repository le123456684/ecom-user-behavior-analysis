-- ============================================================
-- 05_retention.sql  留存分析（SQLite 可执行版）
-- 业务问题：用户来了之后还会回来吗？次日/7 日留存是多少？
-- 与 MySQL 8 版差异（5.1 / 5.2 / 5.3 段）：
--   MySQL  : DATEDIFF(a.dt, f.reg_dt)
--   SQLite : CAST(julianday(a.dt) - julianday(f.reg_dt) AS INTEGER)
--   原因    : SQLite 没有 DATEDIFF，用 julianday 把日期转成"儒略日数"再相减，
--             差值是天数（浮点），CAST 成整数即为相隔天数
-- 另：5.4 用了 FILTER (WHERE ...)，SQLite 3.30+ 支持，
--     MySQL 8 不支持，MySQL 版请改用 SUM(behavior_type = 'pv')
-- ============================================================

-- 5.1 次日留存率（按注册日分组）
-- 【讲法】这是留存的标准四步：
--   ① first_day：每个用户最早出现的日期 = 注册日（用 MIN(dt) 求）
--   ② activity：每个用户有哪些"活跃日"（DISTINCT 去重，一天算一次）
--   ③ 两张表按 user_id 左连接：把"注册日"和"他出现的每一天"配对
--   ④ 判断 a.dt - reg_dt = 1 的，就是次日留存
-- 注意用 LEFT JOIN 而不是 JOIN：当天注册当天流失的人也要算进分母。
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
    COUNT(DISTINCT CASE WHEN CAST(julianday(a.dt) - julianday(f.reg_dt) AS INTEGER) = 1
                        THEN a.user_id END) AS retained_d1,
    ROUND(COUNT(DISTINCT CASE WHEN CAST(julianday(a.dt) - julianday(f.reg_dt) AS INTEGER) = 1
                              THEN a.user_id END) * 100.0
          / NULLIF(COUNT(DISTINCT f.user_id), 0), 2) AS d1_retention_pct
FROM first_day f
LEFT JOIN activity a ON f.user_id = a.user_id
GROUP BY f.reg_dt
ORDER BY f.reg_dt;


-- 5.2 留存矩阵（第 N 日留存，N = 0..7）
-- 【讲法】按"注册日"分组（同期群 cohort），每个注册日一行，
--         每行看这批人在第 0/1/2/3/7 天还有多少人回来。
--         最后用 SUM(CASE WHEN day_n = N ...) 把行转列（经典行转列写法）。
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
        CAST(julianday(a.dt) - julianday(f.reg_dt) AS INTEGER) AS day_n,
        COUNT(DISTINCT f.user_id) AS users
    FROM first_day f
    JOIN activity a ON f.user_id = a.user_id
    WHERE CAST(julianday(a.dt) - julianday(f.reg_dt) AS INTEGER) BETWEEN 0 AND 7
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
-- 【讲法】口径必须先说清再写 SQL。这里分母是"有购买的用户数"，不是"全部用户数"，
--         因为没买过的人谈不上"复购"。
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
-- 【讲法】两段式：先按用户算出 pv 次数和 buy 次数，再用 CASE WHEN 打标签，
--         最后按标签分组统计人数和占比。
--         FILTER (WHERE ...) 是"带条件的聚合"，比 SUM(CASE WHEN ...) 更易读，
--         但只有 PostgreSQL / SQLite 3.30+ 支持，MySQL 8 要用 SUM(CASE WHEN)。
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

-- 【MySQL 8 兼容写法】把上面两个 FILTER 换成：
--   SUM(CASE WHEN behavior_type = 'pv'  THEN 1 ELSE 0 END) AS pv_cnt,
--   SUM(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS buy_cnt
