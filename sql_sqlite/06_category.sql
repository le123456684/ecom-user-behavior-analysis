-- ============================================================
-- 06_category.sql  类目维度分析（SQLite 可执行版）
-- 业务问题：哪些类目是「高流量低转化」，值得优先优化？
-- 与 MySQL 8 版无方言差异。

-- 核心产出是 6.3：把"流量占比"和"转化率"两个维度交叉，
-- 找出"有人看但没人买"的类目 —— 这类优化的边际收益最高。
-- ============================================================

-- 6.1 类目流量结构：各占多少流量
-- 【讲法】SUM(SUM(pv)) OVER () 的含义：内层按类目求 pv，外层把各类目 pv 求和得总量，
--         相除就是"这个类目占全站流量的比例"。
--         为什么不能直接用 SUM(pv)/COUNT(*)？因为 COUNT(*) 是行为条数不是总量。
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
-- 【讲法】HAVING 过滤样本量不足的类目：只有几十个访客的类目转化率是噪音，不是洞察。
--         这句是"数据分析素养"的体现，比 SQL 语法更值钱。
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
-- 判定标准（写进指标字典）：
--   流量占比 > 2%  且  转化率 < 全站平均转化率
-- 【讲法】两个 CTE 分工：
--   cat_stat：每个类目的浏览人数、购买人数（已过样本量门槛）
--   site：全站口径（总浏览、总购买、总转化率），只有一行
--   最后 CROSS JOIN 把这一行挂到每个类目上，逐个对比。
-- 【关键口径】site_conv 用的是"总购买 ÷ 总浏览"，不是"各类目转化率的平均"——
--   后者叫辛普森悖论陷阱，会因为小样本类目拉偏结果。面试爱问这个。
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
-- 【讲法】加购但没买的人数 = 高意向人群，是再营销的直接目标。
--         注意这是"人数差"不是"行为差"：加购过的人数减去购买过的人数，
--         两者有重叠（既加购又购买的人），所以差值含义是"加购了但没成交的净人数"。
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
-- 【讲法】这里用 SUM(behavior_type = 'pv') 而不是 COUNT(DISTINCT user_id)，
--         因为商品维度看的是"浏览次数"体现的热度，不是"多少人来过"。
-- ⚠️ 【阈值必须跟着数据规模走 —— 这段原来是个坑】
--     原阈值写的是 HAVING pv >= 500，但本数据集只有 2000 个商品，
--     单个商品最大 pv 仅 468，所以这段永远返回 0 行（不报错、就是空表）。
--     现按分位数改为 300（约 P85，即"浏览量前 15% 的商品"）。
--     面试可以主动讲这一点：阈值不是拍脑袋写的，要按分位数或者业务定义来定。
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
HAVING pv >= 300
ORDER BY pv DESC
LIMIT 30;
