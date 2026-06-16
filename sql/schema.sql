CREATE DATABASE IF NOT EXISTS stock_analysis_test
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE stock_analysis_test;

CREATE TABLE IF NOT EXISTS stock_security (
  stock_code VARCHAR(16) NOT NULL COMMENT '6位股票代码，如002466',
  market VARCHAR(8) NOT NULL COMMENT '交易所/市场：SH/SZ/BJ',
  symbol VARCHAR(16) NOT NULL COMMENT '带市场前缀的代码，如SZ002466',
  name VARCHAR(64) NULL COMMENT '股票简称',
  industry VARCHAR(128) NULL COMMENT '行业',
  listed_date DATE NULL COMMENT '上市日期',
  total_shares DECIMAL(24,4) NULL COMMENT '总股本，股',
  float_shares DECIMAL(24,4) NULL COMMENT '流通股，股',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (stock_code),
  UNIQUE KEY uk_stock_security_symbol (symbol),
  KEY idx_stock_security_market (market),
  KEY idx_stock_security_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票基础信息';

CREATE TABLE IF NOT EXISTS stock_daily_quote (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL COMMENT '交易日',
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq' COMMENT '复权方式',
  open_price DECIMAL(18,4) NULL,
  high_price DECIMAL(18,4) NULL,
  low_price DECIMAL(18,4) NULL,
  close_price DECIMAL(18,4) NULL,
  volume_shares DECIMAL(24,4) NULL COMMENT '成交量，股',
  volume_lots DECIMAL(24,4) NULL COMMENT '成交量，手',
  amount DECIMAL(24,4) NULL COMMENT '成交额，元',
  turnover_rate DECIMAL(12,6) NULL COMMENT '换手率，百分比数值，如6.71',
  source VARCHAR(64) NOT NULL DEFAULT 'akshare.stock_zh_a_daily',
  raw_json JSON NULL COMMENT '原始行情行，便于排查口径',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_quote (stock_code, trade_date, adjust_type),
  KEY idx_stock_daily_quote_date (trade_date),
  CONSTRAINT fk_stock_daily_quote_security
    FOREIGN KEY (stock_code) REFERENCES stock_security (stock_code)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日OHLCV行情';

CREATE TABLE IF NOT EXISTS stock_daily_technical (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  ma5 DECIMAL(18,4) NULL,
  ma10 DECIMAL(18,4) NULL,
  ma20 DECIMAL(18,4) NULL,
  ma60 DECIMAL(18,4) NULL,
  ma120 DECIMAL(18,4) NULL,
  ma250 DECIMAL(18,4) NULL,
  avg_volume_5 DECIMAL(24,4) NULL COMMENT '5日平均成交量，手',
  avg_volume_20 DECIMAL(24,4) NULL COMMENT '20日平均成交量，手',
  volume_ratio_5 DECIMAL(12,6) NULL COMMENT '当日成交量/5日均量',
  volume_ratio_20 DECIMAL(12,6) NULL COMMENT '当日成交量/20日均量',
  macd_dif DECIMAL(18,6) NULL,
  macd_dea DECIMAL(18,6) NULL,
  macd_bar DECIMAL(18,6) NULL,
  boll_mid DECIMAL(18,4) NULL,
  boll_upper DECIMAL(18,4) NULL,
  boll_lower DECIMAL(18,4) NULL,
  boll_position VARCHAR(32) NULL COMMENT '突破上轨/中轨上方/中轨下方/跌破下轨',
  kdj_k DECIMAL(12,6) NULL,
  kdj_d DECIMAL(12,6) NULL,
  kdj_j DECIMAL(12,6) NULL,
  rsi6 DECIMAL(12,6) NULL,
  rsi12 DECIMAL(12,6) NULL,
  rsi24 DECIMAL(12,6) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_technical (stock_code, trade_date, adjust_type),
  KEY idx_stock_daily_technical_date (trade_date),
  CONSTRAINT fk_stock_daily_technical_quote
    FOREIGN KEY (stock_code, trade_date, adjust_type)
    REFERENCES stock_daily_quote (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日技术指标';

CREATE TABLE IF NOT EXISTS stock_financial_report (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  report_date DATE NOT NULL COMMENT '财务报告期',
  eps DECIMAL(18,6) NULL COMMENT '每股收益',
  net_asset_per_share DECIMAL(18,6) NULL COMMENT '每股净资产',
  operating_cash_per_share DECIMAL(18,6) NULL COMMENT '每股经营现金流',
  roe DECIMAL(12,6) NULL COMMENT 'ROE，百分比数值',
  gross_margin DECIMAL(12,6) NULL COMMENT '毛利率，百分比数值',
  net_margin DECIMAL(12,6) NULL COMMENT '净利率，百分比数值',
  revenue_growth DECIMAL(12,6) NULL COMMENT '营收增长率，百分比数值',
  net_profit_growth DECIMAL(12,6) NULL COMMENT '净利润增长率，百分比数值',
  asset_growth DECIMAL(12,6) NULL COMMENT '总资产增长率，百分比数值',
  debt_ratio DECIMAL(12,6) NULL COMMENT '资产负债率，百分比数值',
  current_ratio DECIMAL(18,6) NULL,
  quick_ratio DECIMAL(18,6) NULL,
  ocf_to_profit DECIMAL(18,6) NULL COMMENT '经营现金流/净利润，倍数',
  source VARCHAR(64) NOT NULL DEFAULT 'akshare.stock_financial_analysis_indicator',
  raw_json JSON NULL COMMENT '原始财务指标行',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_financial_report (stock_code, report_date),
  KEY idx_stock_financial_report_date (report_date),
  CONSTRAINT fk_stock_financial_report_security
    FOREIGN KEY (stock_code) REFERENCES stock_security (stock_code)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='财务报告期基本面指标';

CREATE TABLE IF NOT EXISTS stock_daily_trend (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  trend_rating VARCHAR(32) NULL COMMENT '技术趋势偏强/震荡/偏弱',
  trend_score INT NULL COMMENT '内部趋势评分',
  conclusion VARCHAR(512) NULL,
  signals_json JSON NULL COMMENT '长期趋势信号列表',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_trend (stock_code, trade_date, adjust_type),
  KEY idx_stock_daily_trend_date (trade_date),
  CONSTRAINT fk_stock_daily_trend_quote
    FOREIGN KEY (stock_code, trade_date, adjust_type)
    REFERENCES stock_daily_quote (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日长期技术趋势总览';

CREATE TABLE IF NOT EXISTS stock_daily_trend_window (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  window_days SMALLINT NOT NULL COMMENT '20/60/120/250',
  return_pct DECIMAL(12,6) NULL COMMENT '窗口涨跌幅，百分比数值',
  close_vs_ma_pct DECIMAL(12,6) NULL COMMENT '收盘价相对对应均线，百分比数值',
  macd_positive_ratio DECIMAL(12,6) NULL COMMENT '窗口内MACD柱体为正占比，0-1',
  boll_mid_above_ratio DECIMAL(12,6) NULL COMMENT '窗口内收盘价在BOLL中轨上方占比，0-1',
  rsi24 DECIMAL(12,6) NULL,
  volume_ratio_20 DECIMAL(12,6) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_trend_window (stock_code, trade_date, adjust_type, window_days),
  KEY idx_stock_daily_trend_window_date (trade_date, window_days),
  CONSTRAINT fk_stock_daily_trend_window_trend
    FOREIGN KEY (stock_code, trade_date, adjust_type)
    REFERENCES stock_daily_trend (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日长期技术趋势窗口明细';

CREATE TABLE IF NOT EXISTS stock_daily_signal_score (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL COMMENT '评分对应的最新交易日',
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  score INT NOT NULL COMMENT '-100到100；正数买入偏向，负数卖出偏向',
  signal_label VARCHAR(32) NOT NULL COMMENT '强买/买入偏向/观望/卖出偏向/强卖',
  short_term_score INT NULL COMMENT '短期评分，-100到100',
  short_term_signal_label VARCHAR(32) NULL COMMENT '短期信号',
  medium_term_score INT NULL COMMENT '中期评分，-100到100',
  medium_term_signal_label VARCHAR(32) NULL COMMENT '中期信号',
  long_term_score INT NULL COMMENT '长期评分，-100到100',
  long_term_signal_label VARCHAR(32) NULL COMMENT '长期信号',
  confidence VARCHAR(16) NOT NULL COMMENT '高/中/低',
  regime VARCHAR(32) NULL COMMENT 'trend/range/downtrend/mixed',
  advice VARCHAR(512) NULL,
  horizon_scores_json JSON NULL COMMENT '短期/中期/长期评分完整快照',
  score_parts_json JSON NULL COMMENT '评分拆解',
  source_errors_json JSON NULL COMMENT '数据源失败提醒',
  raw_analysis_json JSON NULL COMMENT '当日完整分析快照',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_signal_score (stock_code, trade_date, adjust_type),
  KEY idx_stock_daily_signal_score_date (trade_date),
  KEY idx_stock_daily_signal_score_score (score),
  KEY idx_stock_daily_signal_score_short_term (short_term_score),
  KEY idx_stock_daily_signal_score_medium_term (medium_term_score),
  KEY idx_stock_daily_signal_score_long_term (long_term_score),
  CONSTRAINT fk_stock_daily_signal_score_quote
    FOREIGN KEY (stock_code, trade_date, adjust_type)
    REFERENCES stock_daily_quote (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日买卖信号评分';

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

CREATE TABLE IF NOT EXISTS stock_daily_report (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stock_code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL COMMENT '报告对应的最新交易日',
  adjust_type ENUM('none','qfq','hfq') NOT NULL DEFAULT 'qfq',
  report_type VARCHAR(32) NOT NULL DEFAULT 'final_summary' COMMENT '报告类型，如final_summary',
  report_title VARCHAR(255) NOT NULL,
  report_text LONGTEXT NOT NULL COMMENT '人可读的最终中文总结报告',
  report_format ENUM('markdown','plain_text') NOT NULL DEFAULT 'markdown',
  report_json JSON NULL COMMENT '可选结构化摘要',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stock_daily_report (stock_code, trade_date, adjust_type, report_type),
  KEY idx_stock_daily_report_date (trade_date, report_type),
  CONSTRAINT fk_stock_daily_report_quote
    FOREIGN KEY (stock_code, trade_date, adjust_type)
    REFERENCES stock_daily_quote (stock_code, trade_date, adjust_type)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日最终总结报告';

CREATE TABLE IF NOT EXISTS stock_data_ingest_run (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  run_finished_at TIMESTAMP NULL,
  status ENUM('running','success','failed') NOT NULL DEFAULT 'running',
  stock_codes_json JSON NULL,
  message VARCHAR(1024) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_stock_data_ingest_run_status (status, run_started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='数据入库任务记录';
