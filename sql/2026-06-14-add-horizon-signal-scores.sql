-- Run with a selected database, for example:
-- mysql -uroot -D stock_analysis_test < sql/2026-06-14-add-horizon-signal-scores.sql

SET @db_name = DATABASE();

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'short_term_score'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN short_term_score INT NULL COMMENT ''短期评分，-100到100'' AFTER signal_label',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'short_term_signal_label'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN short_term_signal_label VARCHAR(32) NULL COMMENT ''短期信号'' AFTER short_term_score',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'medium_term_score'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN medium_term_score INT NULL COMMENT ''中期评分，-100到100'' AFTER short_term_signal_label',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'medium_term_signal_label'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN medium_term_signal_label VARCHAR(32) NULL COMMENT ''中期信号'' AFTER medium_term_score',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'long_term_score'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN long_term_score INT NULL COMMENT ''长期评分，-100到100'' AFTER medium_term_signal_label',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'long_term_signal_label'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN long_term_signal_label VARCHAR(32) NULL COMMENT ''长期信号'' AFTER long_term_score',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND COLUMN_NAME = 'horizon_scores_json'
);
SET @ddl = IF(
  @column_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD COLUMN horizon_scores_json JSON NULL COMMENT ''短期/中期/长期评分完整快照'' AFTER advice',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND INDEX_NAME = 'idx_stock_daily_signal_score_short_term'
);
SET @ddl = IF(
  @index_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD INDEX idx_stock_daily_signal_score_short_term (short_term_score)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND INDEX_NAME = 'idx_stock_daily_signal_score_medium_term'
);
SET @ddl = IF(
  @index_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD INDEX idx_stock_daily_signal_score_medium_term (medium_term_score)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @db_name
    AND TABLE_NAME = 'stock_daily_signal_score'
    AND INDEX_NAME = 'idx_stock_daily_signal_score_long_term'
);
SET @ddl = IF(
  @index_exists = 0,
  'ALTER TABLE stock_daily_signal_score ADD INDEX idx_stock_daily_signal_score_long_term (long_term_score)',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
