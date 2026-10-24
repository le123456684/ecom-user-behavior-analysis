-- ============================================================
-- 06_category.sql  类目维度分析
-- 业务问题：哪些类目是「高流量低转化」，值得优先优化？
-- 考察点：多维度交叉 + NULLIF 边界处理 + HAVING 样本量门槛
-- ============================================================

USE ecom_analysis;

-- 6.1 类目流量结构：各占多少流量
SELECT
    category_id,
    SUM(behavior_type = 'pv')                                  AS pv,
    ROUND(SUM(behavior_type = 'pv') * 100.0
          / SUM(SUM(behavior_type = 'pv')) OVER (), 2)         AS pv_share_pct,
    COUNT(DISTINCT user_id)                                    AS uv
FROM user_behavior
GROUP BY category_id
ORDER BY pv DESC
LIMIT 30;


-- 6.2 类目转化率排名
-- HAVING 过滤样本量不足的类目：只有几十个访客的类目转化率是噪音，不是洞察
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


-- 6.3 核心产出：高流量低转化类目清单
-- 判定标准（写在指标字典里）：
--   流量占比 > 2%  且  转化率 < 全站平均转化率
-- 业务含义：有流量但成交差 —— 优化收益最大的一批类目
WITH cat_stat AS (
    SELECT
        category_id,
        COUNT(DISTINCT CASE WHEN behavior_type = 'pv'  THEN user_id END) AS browse_u,
        COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_u
    FROM user_behavior
    GROUP BY category_id
    HAVING browse_u >= 100
),
site AS (
    SELECT
        SUM(browse_u)                                  AS site_browse,
        SUM(buy_u)                                     AS site_buy,
        SUM(buy_u) * 1.0 / NULLIF(SUM(browse_u), 0)    AS site_conv
    FROM cat_stat
)
SELECT
    c.category_id,
    c.browse_u,
    c.buy_u,
    ROUND(c.browse_u * 100.0 / s.site_browse, 2)                AS traffic_share_pct,
    ROUND(c.buy_u * 100.0 / NULLIF(c.browse_u, 0), 2)           AS conv_rate_pct,
    ROUND(s.site_conv * 100, 2)                                 AS site_conv_pct,
    ROUND((s.site_conv - c.buy_u * 1.0 / NULLIF(c.browse_u, 0)) * 100, 2) AS gap_pct
FROM cat_stat c
CROSS JOIN site s
WHERE c.buy_u * 1.0 / NULLIF(c.browse_u, 0) < s.site_conv
  AND c.browse_u * 100.0 / s.site_browse > 2
ORDER BY c.browse_u DESC;


-- 6.4 类目加购率对比
-- 加购但未购买 = 高意向人群，是再营销的重点目标
SELECT
    category_id,
    COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS cart_u,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy'  THEN user_id END) AS buy_u,
    COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END)
      - COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS cart_not_buy_u,
    ROUND(COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) * 100.0
          / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END), 0), 2)
        AS cart_to_buy_pct
FROM user_behavior
GROUP BY category_id
HAVING cart_u >= 100
ORDER BY cart_not_buy_u DESC
LIMIT 20;


-- 6.5 爆款识别：被浏览最多但转化一般的商品
SELECT
    item_id,
    category_id,
    SUM(behavior_type = 'pv')  AS pv,
    SUM(behavior_type = 'cart') AS cart_cnt,
    SUM(behavior_type = 'buy')  AS buy_cnt,
    ROUND(SUM(behavior_type = 'buy') * 100.0
          / NULLIF(SUM(behavior_type = 'pv'), 0), 2) AS pv_to_buy_pct
FROM user_behavior
GROUP BY item_id, category_id
HAVING pv >= 500
ORDER BY pv DESC
LIMIT 30;
