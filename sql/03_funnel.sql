-- ============================================================
-- 03_funnel.sql  转化漏斗分析（项目核心）
-- 业务问题：用户从浏览到购买，每一步流失多少？哪个环节最该优化？
-- 考察点：COUNT DISTINCT + CASE WHEN 一次扫描多口径聚合
-- ============================================================

USE ecom_analysis;

-- 3.1 全局漏斗：四层人数一次性算出
-- 关键点：用 CASE WHEN 条件聚合，一次表扫描得到四个指标
--         比写四个独立子查询高效得多（这也是面试高频考点）
SELECT
    COUNT(DISTINCT CASE WHEN behavior_type = 'pv'   THEN user_id END) AS browse_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'fav'  THEN user_id END) AS fav_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS cart_users,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy'  THEN user_id END) AS buy_users
FROM user_behavior;


-- 3.2 漏斗逐层流失率（把 3.1 的结果整理成漏斗）
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
-- 说明：HAVING 过滤样本量过小的类目，避免统计噪音
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
-- 业务含义：流量占比高但转化率低于全站均值的类目，是最该优先优化的
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
