-- ============================================================
-- 01_create_table.sql
-- 电商用户行为分析 · 建库建表脚本
-- 数据源：淘宝用户行为数据集（UserBehavior）
-- ============================================================

CREATE DATABASE IF NOT EXISTS ecom_analysis
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE ecom_analysis;

-- ------------------------------------------------------------
-- 主表：用户行为流水
-- 字段说明：
--   user_id       用户 ID
--   item_id       商品 ID
--   category_id   商品类目 ID
--   behavior_type 行为类型：pv(浏览) / fav(收藏) / cart(加购) / buy(购买)
--   ts            行为时间戳（秒级 Unix 时间戳）
--   dt            行为日期（由 ts 派生，预先算好避免查询时反复转换）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS user_behavior;

CREATE TABLE user_behavior (
  user_id       BIGINT       NOT NULL COMMENT '用户ID',
  item_id       BIGINT       NOT NULL COMMENT '商品ID',
  category_id   BIGINT       NOT NULL COMMENT '类目ID',
  behavior_type VARCHAR(10)  NOT NULL COMMENT '行为类型: pv/fav/cart/buy',
  ts            BIGINT       NOT NULL COMMENT '行为时间戳(秒)',
  dt            DATE         NOT NULL COMMENT '行为日期',
  PRIMARY KEY (user_id, item_id, behavior_type, ts),
  KEY idx_dt       (dt),
  KEY idx_behavior (behavior_type),
  KEY idx_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户行为流水表';


-- ------------------------------------------------------------
-- 维度表：商品维度
-- 说明：原数据集只有 category_id，类目名称需要自行映射或留空
-- ------------------------------------------------------------
DROP TABLE IF EXISTS item_dim;

CREATE TABLE item_dim (
  item_id       BIGINT      NOT NULL,
  category_id   BIGINT      NOT NULL,
  category_name VARCHAR(64) DEFAULT NULL COMMENT '类目名称(可后续补充)',
  PRIMARY KEY (item_id),
  KEY idx_cat (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品维度表';


-- ------------------------------------------------------------
-- 维度表：日期维度
-- 用途：时间切片分析（按周、按周末、按工作日）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS date_dim;

CREATE TABLE date_dim (
  dt          DATE        NOT NULL,
  yw          INT         NOT NULL COMMENT '年周序号',
  day_of_week TINYINT     NOT NULL COMMENT '1=周一 ... 7=周日',
  is_weekend  TINYINT     NOT NULL COMMENT '1=周末 0=工作日',
  PRIMARY KEY (dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日期维度表';


-- ------------------------------------------------------------
-- 派生表：用户活跃汇总
-- 用途：留存分析、用户分层，避免每次现算
-- ------------------------------------------------------------
DROP TABLE IF EXISTS user_dim;

CREATE TABLE user_dim (
  user_id         BIGINT  NOT NULL,
  first_visit_dt  DATE    NOT NULL COMMENT '首次活跃日期',
  last_visit_dt   DATE    NOT NULL COMMENT '最近活跃日期',
  active_days     INT     NOT NULL COMMENT '活跃天数',
  total_pv        INT     NOT NULL DEFAULT 0 COMMENT '累计浏览次数',
  total_buy       INT     NOT NULL DEFAULT 0 COMMENT '累计购买次数',
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户维度汇总表';


-- ============================================================
-- 数据导入提示
-- ------------------------------------------------------------
-- 若手上有 CSV / TSV 文件，用 LOAD DATA 导入主表。
-- 注意：原始数据只有 ts 没有 dt，需在导入时用
--       FROM_UNIXTIME(ts, '%Y-%m-%d') 派生，或先导入临时表再转换。
--
-- 示例（临时表 → 主表，规避只读文件权限与路径限制）：
--
--   LOAD DATA LOCAL INFILE 'UserBehavior.csv'
--   INTO TABLE tmp_behavior
--   FIELDS TERMINATED BY ','
--   LINES TERMINATED BY '\n'
--   (user_id, item_id, category_id, behavior_type, ts);
--
--   INSERT INTO user_behavior (user_id, item_id, category_id, behavior_type, ts, dt)
--   SELECT user_id, item_id, category_id, behavior_type, ts,
--          DATE(FROM_UNIXTIME(ts))
--   FROM tmp_behavior
--   WHERE ts BETWEEN 1511539200 AND 1512316800;  -- 按需限定时间范围
--
-- 提示：先只导入 100 万～500 万条跑通全流程，再考虑全量。
--       全量导入耗时长且容易在环境问题上卡住，不要一开始就上全量。
-- ============================================================
