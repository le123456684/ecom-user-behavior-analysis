-- ============================================================
-- 03_funnel.sql  转化漏斗分析（项目核心，SQLite 可执行版）
-- 业务问题：用户从浏览到购买，每一步流失多少？哪个环节最该优化？
-- 与 MySQL 8 版无方言差异，本文件与 mysql 版逻辑完全一致。
-- 核心技巧：CASE WHEN 条件聚合 —— 一次表扫描算出 4 个漏斗层级
-- ============================================================

-- 3.1 全局漏斗：四层人数一次性算出
-- 【讲法】如果按"每层一个子查询"去写，要扫表 4 次；
--         用 COUNT(DISTINCT CASE WHEN 条件 THEN user_id END) 一次扫描就出 4 个数。
--         原理：CASE 不满足时返回 NULL，COUNT 不数 NULL，所以自动只数符合条件的人。
--         这是面试高频考点，也是"会不会写 SQL"的分水岭。
SELECT
    COUNT(DISTINCT CASE WHEN behavior_type = 'pv'   THEN user_id END) AS browse_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'fav'  THEN user_id END) AS fav_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS cart_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy'  THEN user_id END) AS buy_users
FROM user_behavior;


-- 3.2 漏斗逐层流失率（把 3.1 的结果整理成漏斗竖表）
-- 【讲法】先用 CTE funnel 把 4 个数算成一行，再用 UNION ALL 把它横过来变成 4 行，
--         每一行算两个率：本层转化率(rate_pct)、本层流失率(drop_pct)。
--         NULLIF(x, 0) 的作用：分母为 0 时返回 NULL 而不是报错（防除零）。
WITH funnel AS (
    SELECT
        COUNT(DISTINCT CASE WHEN behavior_type = 'pv'   THEN user_id END) AS s1_browse,
        COUNT(DISTINCT CASE WHEN behavior_type = 'fav'  THEN user_id END) AS s2_fav,
        COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS s3_cart,
        COUNT(DISTINCT CASE WHEN behavior_type = 'buy'  THEN user_id END) AS s4_buy
    FROM user_behavior
)
SELECT '浏览' AS step, s1_browse AS users, 100.00 AS rate_pct, NULL AS drop_pct FROM funnel
UNION ALL
SELECT '收藏', s2_fav,
       ROUND(s2_fav / NULLIF(s1_browse, 0) * 100, 2),
       ROUND((s1_browse - s2_fav) / NULLIF(s1_browse, 0) * 100, 2) FROM funnel
UNION ALL
SELECT '加购', s3_cart,
       ROUND(s3_cart / NULLIF(s2_fav, 0) * 100, 2),
       ROUND((s2_fav - s3_cart) / NULLIF(s2_fav, 0) * 100, 2) FROM funnel
UNION ALL
SELECT '购买', s4_buy,
       ROUND(s4_buy / NULLIF(s3_cart, 0) * 100, 2),
       ROUND((s3_cart - s4_buy) / NULLIF(s3_cart, 0) * 100, 2) FROM funnel;


-- 3.3 按日漏斗趋势：观察转化率是否稳定
-- 【讲法】加一个 dt 分组，口径不变。用途是看"转化率有没有某天突然掉下去"。
SELECT
    dt,
    COUNT(DISTINCT CASE WHEN behavior_type = 'pv'  THEN user_id END) AS browse_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_users,
    ROUND(COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) * 100.0
          / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type = 'pv' THEN user_id END), 0), 2)
        AS conv_rate_pct
FROM user_behavior
GROUP BY dt
ORDER BY dt;


-- 3.4 按类目的漏斗（找高流量低转化类目）
-- 【讲法】HAVING browse_u >= 100 是"样本量门槛"：
--         一个只有 3 个人访问的类目，转化率 33% 或 0% 都是噪音，不是洞察。
--         面试时主动说这一句，比写对 SQL 更加分。
SELECT
    category_id,
    COUNT(DISTINCT CASE WHEN behavior_type = 'pv'  THEN user_id END) AS browse_u,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_u,
    ROUND(COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) * 100.0
          / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type = 'pv' THEN user_id END), 0), 2)
        AS conv_rate_pct
FROM user_behavior
GROUP BY category_id
HAVING browse_u >= 100
ORDER BY conv_rate_pct DESC;


-- 3.5 高流量低转化类目（优化机会点）
-- 【讲法】两个窗口函数 SUM(...) OVER () 算的是"全站合计"，用来跟单个类目做对比：
--         - site_conv_pct：全站平均转化率（所有类目 buy 总数 ÷ browse 总数，注意不是各类目转化率的平均）
--         - 筛选条件：转化率低于全站 && 流量占比 > 2%（流量太小即使转化差也不值得优化）
WITH cat AS (
    SELECT
        category_id,
        COUNT(DISTINCT CASE WHEN behavior_type = 'pv'  THEN user_id END) AS browse_u,
        COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_u
    FROM user_behavior
    GROUP BY category_id
    HAVING browse_u >= 100
),
total AS (
    SELECT SUM(browse_u) AS total_browse FROM cat
)
SELECT
    c.category_id,
    c.browse_u,
    c.buy_u,
    ROUND(c.browse_u * 100.0 / t.total_browse, 2)                          AS traffic_share_pct,
    ROUND(c.buy_u * 100.0 / NULLIF(c.browse_u, 0), 2)                      AS conv_rate_pct,
    ROUND(SUM(c.buy_u) OVER () * 100.0 / NULLIF(SUM(c.browse_u) OVER (), 0), 2) AS site_conv_pct
FROM cat c CROSS JOIN total t
WHERE c.buy_u * 1.0 / NULLIF(c.browse_u, 0)
      < (SELECT SUM(buy_u) * 1.0 / NULLIF(SUM(browse_u), 0) FROM cat)
  AND c.browse_u * 100.0 / t.total_browse > 2
ORDER BY c.browse_u DESC
LIMIT 20;
