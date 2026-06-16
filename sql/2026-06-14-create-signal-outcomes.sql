-- Run with a selected database, for example:
-- mysql -uroot -D stock_analysis_test < sql/2026-06-14-create-signal-outcomes.sql

CREATE TABLE IF NOT EXISTS stock_signal_outcome (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  signal_trade_date DATE NOT NULL COMMENT '信号生成交易日',
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  horizon VARCHAR(32) NOT NULL COMMENT 'short_term/medium_term/long_term',
  window_days SMALLINT NOT NULL COMMENT '第N个未来交易日',
  signal_score INT NULL COMMENT '当时该周期评分',
  signal_label VARCHAR(32) NULL COMMENT '当时该周期信号',
  signal_close DECIMAL(18,4) NULL COMMENT '信号日收盘价',
  target_trade_date DATE NULL COMMENT '目标交易日',
  target_close DECIMAL(18,4) NULL COMMENT '目标交易日收盘价',
  return_pct DECIMAL(12,6) NULL COMMENT '目标日收益率，百分比数值',
  benchmark_code VARCHAR(32) NULL COMMENT '基准代码，预留',
  benchmark_return_pct DECIMAL(12,6) NULL COMMENT '基准收益率，百分比数值',
  excess_return_pct DECIMAL(12,6) NULL COMMENT '超额收益率，百分比数值',
  max_drawdown_pct DECIMAL(12,6) NULL COMMENT '窗口内最低收益率，百分比数值',
  max_runup_pct DECIMAL(12,6) NULL COMMENT '窗口内最高收益率，百分比数值',
  hit TINYINT(1) NULL COMMENT '方向信号是否命中；观望为NULL',
  status ENUM('pending','matured','missing_quote') NOT NULL DEFAULT 'pending',
  evaluated_at TIMESTAMP NULL,
  raw_signal_json JSON NULL COMMENT '当时评分快照',
  raw_result_json JSON NULL COMMENT '到期结果快照',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_signal_outcome (stock_code, signal_trade_date, adjust_type, horizon, window_days),
  KEY idx_stock_signal_outcome_status (status, signal_trade_date),
  KEY idx_stock_signal_outcome_horizon (horizon, window_days, status),
  KEY idx_stock_signal_outcome_stock (stock_code, horizon, window_days),
  CONSTRAINT fk_stock_signal_outcome_score
    FOREIGN KEY (stock_code, signal_trade_date, adjust_type)
    REFERENCES stock_daily_signal_score (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='买卖信号历史验证结果';
