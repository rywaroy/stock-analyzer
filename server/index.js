import 'dotenv/config';

import cors from 'cors';
import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import mysql from 'mysql2/promise';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
export const DEFAULT_INGEST_API_TOKEN = 'stock-analysis-ingest-2026-6f8c2d91b7a443e0';

let pool;

export function createDefaultPool() {
  return mysql.createPool({
    host: process.env.MYSQL_HOST || '127.0.0.1',
    port: Number(process.env.MYSQL_PORT || 3306),
    user: process.env.MYSQL_USER || 'root',
    password: process.env.MYSQL_PASSWORD || '',
    database: process.env.MYSQL_DATABASE || 'stock_analysis_test',
    waitForConnections: true,
    connectionLimit: Number(process.env.MYSQL_CONNECTION_LIMIT || 8),
    timezone: '+08:00',
    dateStrings: true,
    decimalNumbers: true,
    charset: 'utf8mb4',
  });
}

function unauthorizedIngestError() {
  const error = new Error('上报接口未授权');
  error.statusCode = 401;
  return error;
}

function requireIngestAuth(ingestToken) {
  return (req, _res, next) => {
    const authHeader = req.get('authorization') || '';
    if (!ingestToken || authHeader !== `Bearer ${ingestToken}`) {
      next(unauthorizedIngestError());
      return;
    }
    next();
  };
}

export function createApp({
  pool: configuredPool = createDefaultPool(),
  ingestToken = process.env.INGEST_API_TOKEN || DEFAULT_INGEST_API_TOKEN,
  projectRootPath = projectRoot,
} = {}) {
  pool = configuredPool;
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: '20mb' }));

function parseJson(value, fallback) {
  if (value == null || value === '') {
    return fallback;
  }
  if (typeof value === 'object') {
    return value;
  }
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function toNumber(value) {
  if (value == null || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function validateStockCode(code) {
  if (!/^[0-9A-Za-z]{1,16}$/.test(code || '')) {
    const error = new Error('stock code 格式不正确');
    error.statusCode = 400;
    throw error;
  }
  return code;
}

function validateTradeDate(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '')) {
    const error = new Error('trade date 格式应为 YYYY-MM-DD');
    error.statusCode = 400;
    throw error;
  }
  return date;
}

function horizonOrderExpression(column = 'horizon') {
  return `FIELD(${column}, 'short_term', 'medium_term', 'long_term')`;
}

function mapDateSummary(row) {
  return {
    tradeDate: row.tradeDate,
    stockCount: Number(row.stockCount || 0),
    avgScore: toNumber(row.avgScore),
    maxScore: toNumber(row.maxScore),
    minScore: toNumber(row.minScore),
    buyBiasCount: Number(row.buyBiasCount || 0),
    watchCount: Number(row.watchCount || 0),
    sellBiasCount: Number(row.sellBiasCount || 0),
    highConfidenceCount: Number(row.highConfidenceCount || 0),
    sourceErrorCount: Number(row.sourceErrorCount || 0),
    updatedAt: row.updatedAt,
  };
}

function mapAnalysisItem(row) {
  const reportJson = parseJson(row.report_json, {});
  const sourceErrors = parseJson(row.source_errors_json, []);
  return {
    stockCode: row.stockCode,
    name: row.name || '',
    displayName: [row.stockCode, row.name].filter(Boolean).join(' '),
    industry: row.industry || '',
    tradeDate: row.tradeDate,
    adjustType: row.adjustType,
    score: row.score,
    signalLabel: row.signalLabel,
    shortTermScore: row.shortTermScore,
    shortTermSignalLabel: row.shortTermSignalLabel,
    mediumTermScore: row.mediumTermScore,
    mediumTermSignalLabel: row.mediumTermSignalLabel,
    longTermScore: row.longTermScore,
    longTermSignalLabel: row.longTermSignalLabel,
    confidence: row.confidence,
    regime: row.regime,
    advice: row.advice || reportJson.advice || '',
    closePrice: toNumber(row.closePrice),
    turnoverRate: toNumber(row.turnoverRate),
    volumeLots: toNumber(row.volumeLots),
    amount: toNumber(row.amount),
    trendRating: row.trendRating,
    trendScore: toNumber(row.trendScore),
    reportTitle: row.reportTitle || '',
    strengths: Array.isArray(reportJson.strengths) ? reportJson.strengths : [],
    risks: Array.isArray(reportJson.risks) ? reportJson.risks : [],
    horizonScores: parseJson(row.horizon_scores_json, {}),
    sourceErrors,
    sourceErrorCount: sourceErrors.length,
  };
}

function mapDetail(row) {
  const reportJson = parseJson(row.report_json, {});
  const sourceErrors = parseJson(row.source_errors_json, []);
  return {
    stockCode: row.stockCode,
    name: row.name || '',
    displayName: [row.stockCode, row.name].filter(Boolean).join(' '),
    industry: row.industry || '',
    listedDate: row.listedDate,
    tradeDate: row.tradeDate,
    adjustType: row.adjustType,
    score: row.score,
    signalLabel: row.signalLabel,
    shortTermScore: row.shortTermScore,
    shortTermSignalLabel: row.shortTermSignalLabel,
    mediumTermScore: row.mediumTermScore,
    mediumTermSignalLabel: row.mediumTermSignalLabel,
    longTermScore: row.longTermScore,
    longTermSignalLabel: row.longTermSignalLabel,
    confidence: row.confidence,
    regime: row.regime,
    advice: row.advice || reportJson.advice || '',
    horizonScores: parseJson(row.horizon_scores_json, {}),
    scoreParts: parseJson(row.score_parts_json, []),
    sourceErrors,
    quote: {
      closePrice: toNumber(row.closePrice),
      volumeLots: toNumber(row.volumeLots),
      amount: toNumber(row.amount),
      turnoverRate: toNumber(row.turnoverRate),
    },
    technical: {
      ma5: toNumber(row.ma5),
      ma10: toNumber(row.ma10),
      ma20: toNumber(row.ma20),
      ma60: toNumber(row.ma60),
      ma120: toNumber(row.ma120),
      ma250: toNumber(row.ma250),
      avgVolume5: toNumber(row.avgVolume5),
      avgVolume20: toNumber(row.avgVolume20),
      volumeRatio5: toNumber(row.volumeRatio5),
      volumeRatio20: toNumber(row.volumeRatio20),
      macdDif: toNumber(row.macdDif),
      macdDea: toNumber(row.macdDea),
      macdBar: toNumber(row.macdBar),
      bollMid: toNumber(row.bollMid),
      bollUpper: toNumber(row.bollUpper),
      bollLower: toNumber(row.bollLower),
      bollPosition: row.bollPosition,
      kdjK: toNumber(row.kdjK),
      kdjD: toNumber(row.kdjD),
      kdjJ: toNumber(row.kdjJ),
      rsi6: toNumber(row.rsi6),
      rsi12: toNumber(row.rsi12),
      rsi24: toNumber(row.rsi24),
    },
    trend: {
      rating: row.trendRating,
      score: toNumber(row.trendScore),
      conclusion: row.trendConclusion || '',
      signals: parseJson(row.trendSignalsJson, []),
    },
    report: {
      title: row.reportTitle || '',
      text: row.reportText || '',
      json: reportJson,
    },
  };
}

async function loadDateSummaries() {
  const [rows] = await pool.query(`
    SELECT
      DATE_FORMAT(s.trade_date, '%Y-%m-%d') AS tradeDate,
      COUNT(*) AS stockCount,
      ROUND(AVG(s.score), 1) AS avgScore,
      MAX(s.score) AS maxScore,
      MIN(s.score) AS minScore,
      SUM(CASE WHEN s.signal_label IN ('强买', '买入偏向') THEN 1 ELSE 0 END) AS buyBiasCount,
      SUM(CASE WHEN s.signal_label = '观望' THEN 1 ELSE 0 END) AS watchCount,
      SUM(CASE WHEN s.signal_label IN ('卖出偏向', '强卖', '强卖/回避') THEN 1 ELSE 0 END) AS sellBiasCount,
      SUM(CASE WHEN s.confidence = '高' THEN 1 ELSE 0 END) AS highConfidenceCount,
      SUM(COALESCE(JSON_LENGTH(s.source_errors_json), 0)) AS sourceErrorCount,
      DATE_FORMAT(MAX(s.updated_at), '%Y-%m-%d %H:%i:%s') AS updatedAt
    FROM stock_daily_signal_score s
    GROUP BY s.trade_date
    ORDER BY s.trade_date DESC
  `);
  return rows.map(mapDateSummary);
}

async function latestTradeDate(stockCode = null) {
  const params = [];
  let where = '';
  if (stockCode) {
    where = 'WHERE stock_code = ?';
    params.push(stockCode);
  }
  const [rows] = await pool.query(
    `SELECT DATE_FORMAT(MAX(trade_date), '%Y-%m-%d') AS tradeDate FROM stock_daily_signal_score ${where}`,
    params,
  );
  return rows[0]?.tradeDate || null;
}

function numberOrNull(value) {
  if (value == null || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function intOrNull(value) {
  const numeric = numberOrNull(value);
  return numeric == null ? null : Math.round(numeric);
}

function jsonValue(value) {
  return value == null ? null : JSON.stringify(value);
}

function metricValues(item) {
  const values = {};
  for (const metric of item.metrics || []) {
    values[metric.label || ''] = numberOrNull(metric.value);
  }
  return values;
}

function marketFromCode(code) {
  if (String(code).startsWith('6')) return 'SH';
  if (String(code).startsWith('4') || String(code).startsWith('8')) return 'BJ';
  return 'SZ';
}

function horizonValue(result, key, field) {
  return (result.horizon_scores?.[key] || {})[field];
}

async function upsert(connection, table, row, updateColumns = Object.keys(row)) {
  const columns = Object.keys(row);
  const placeholders = columns.map(() => '?').join(', ');
  const updates = updateColumns.map((column) => `${column}=VALUES(${column})`).join(', ');
  const params = columns.map((column) => (row[column] === undefined ? null : row[column]));
  await connection.query(
    `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${placeholders}) ON DUPLICATE KEY UPDATE ${updates}`,
    params,
  );
}

async function persistSecurity(connection, item) {
  const code = String(item.code);
  const overview = item.overview || {};
  await upsert(
    connection,
    'stock_security',
    {
      stock_code: code,
      market: marketFromCode(code),
      symbol: `${marketFromCode(code)}${code}`,
      name: item.name || null,
      industry: item.industry || null,
      listed_date: item.listed_at || null,
      total_shares: numberOrNull(overview['总股本']),
      float_shares: numberOrNull(overview['流通股']),
    },
    ['market', 'symbol', 'name', 'industry', 'listed_date', 'total_shares', 'float_shares'],
  );
}

async function persistQuote(connection, item, adjustType) {
  const technical = item.technical || {};
  const volumeLots = numberOrNull(technical.latest_volume);
  await upsert(
    connection,
    'stock_daily_quote',
    {
      stock_code: String(item.code),
      trade_date: technical.trade_date,
      adjust_type: adjustType,
      open_price: null,
      high_price: null,
      low_price: null,
      close_price: numberOrNull(technical.latest_close),
      volume_shares: volumeLots == null ? null : volumeLots * 100,
      volume_lots: volumeLots,
      amount: numberOrNull(technical.latest_amount),
      turnover_rate: numberOrNull(technical.turnover_rate),
      raw_json: jsonValue(technical),
    },
    [
      'open_price',
      'high_price',
      'low_price',
      'close_price',
      'volume_shares',
      'volume_lots',
      'amount',
      'turnover_rate',
      'raw_json',
    ],
  );
}

async function persistTechnical(connection, item, adjustType) {
  const technical = item.technical || {};
  const macd = technical.macd || {};
  const boll = technical.boll || {};
  const kdj = technical.kdj || {};
  const rsi = technical.rsi || {};
  const row = {
    stock_code: String(item.code),
    trade_date: technical.trade_date,
    adjust_type: adjustType,
    avg_volume_5: numberOrNull(technical.avg_volume_5),
    avg_volume_20: numberOrNull(technical.avg_volume_20),
    volume_ratio_5: numberOrNull(technical.volume_ratio_5),
    volume_ratio_20: null,
    macd_dif: numberOrNull(macd.dif),
    macd_dea: numberOrNull(macd.dea),
    macd_bar: numberOrNull(macd.bar),
    boll_mid: numberOrNull(boll.mid),
    boll_upper: numberOrNull(boll.upper),
    boll_lower: numberOrNull(boll.lower),
    boll_position: boll.position || null,
    kdj_k: numberOrNull(kdj.k),
    kdj_d: numberOrNull(kdj.d),
    kdj_j: numberOrNull(kdj.j),
    rsi6: numberOrNull(rsi.rsi6),
    rsi12: numberOrNull(rsi.rsi12),
    rsi24: numberOrNull(rsi.rsi24),
  };
  await upsert(
    connection,
    'stock_daily_technical',
    row,
    Object.keys(row).filter((column) => !['stock_code', 'trade_date', 'adjust_type'].includes(column)),
  );
}

async function persistFinancial(connection, item) {
  if (!item.report_date) {
    return;
  }
  const metrics = metricValues(item);
  const row = {
    stock_code: String(item.code),
    report_date: item.report_date,
    eps: numberOrNull(metrics['每股收益']),
    net_asset_per_share: numberOrNull(metrics['每股净资产']),
    operating_cash_per_share: numberOrNull(metrics['每股经营现金流']),
    roe: numberOrNull(metrics.ROE),
    gross_margin: numberOrNull(metrics['毛利率']),
    net_margin: numberOrNull(metrics['净利率']),
    revenue_growth: numberOrNull(metrics['营收增长']),
    net_profit_growth: numberOrNull(metrics['净利润增长']),
    asset_growth: numberOrNull(metrics['总资产增长']),
    debt_ratio: numberOrNull(metrics['资产负债率']),
    current_ratio: numberOrNull(metrics['流动比率']),
    quick_ratio: numberOrNull(metrics['速动比率']),
    ocf_to_profit: numberOrNull(metrics['经营现金流/净利润']),
    raw_json: jsonValue(item.metrics || []),
  };
  await upsert(
    connection,
    'stock_financial_report',
    row,
    Object.keys(row).filter((column) => !['stock_code', 'report_date'].includes(column)),
  );
}

async function persistTrend(connection, item, adjustType) {
  const technical = item.technical || {};
  const trend = item.technical_trend || {};
  await upsert(
    connection,
    'stock_daily_trend',
    {
      stock_code: String(item.code),
      trade_date: technical.trade_date,
      adjust_type: adjustType,
      trend_rating: trend.rating || null,
      trend_score: intOrNull(trend.score),
      conclusion: trend.conclusion || null,
      signals_json: jsonValue(trend.signals || []),
    },
    ['trend_rating', 'trend_score', 'conclusion', 'signals_json'],
  );
}

async function persistTrendWindows(connection, item, adjustType) {
  const technical = item.technical || {};
  const trend = item.technical_trend || {};
  for (const window of trend.windows || []) {
    const row = {
      stock_code: String(item.code),
      trade_date: technical.trade_date,
      adjust_type: adjustType,
      window_days: intOrNull(window.days),
      return_pct: numberOrNull(window.return_pct),
      close_vs_ma_pct: numberOrNull(window.close_vs_ma_pct),
      macd_positive_ratio: numberOrNull(window.macd_positive_ratio),
      boll_mid_above_ratio: numberOrNull(window.boll_mid_above_ratio),
      rsi24: numberOrNull(window.rsi24),
      volume_ratio_20: numberOrNull(window.volume_ratio_20),
    };
    await upsert(
      connection,
      'stock_daily_trend_window',
      row,
      Object.keys(row).filter((column) => !['stock_code', 'trade_date', 'adjust_type', 'window_days'].includes(column)),
    );
  }
}

async function persistScore(connection, result, adjustType) {
  const item = result.raw || {};
  const technical = item.technical || {};
  const row = {
    stock_code: String(result.code),
    trade_date: technical.trade_date,
    adjust_type: adjustType,
    score: intOrNull(result.score),
    signal_label: result.signal,
    short_term_score: intOrNull(horizonValue(result, 'short_term', 'score')),
    short_term_signal_label: horizonValue(result, 'short_term', 'signal') || null,
    medium_term_score: intOrNull(horizonValue(result, 'medium_term', 'score')),
    medium_term_signal_label: horizonValue(result, 'medium_term', 'signal') || null,
    long_term_score: intOrNull(horizonValue(result, 'long_term', 'score')),
    long_term_signal_label: horizonValue(result, 'long_term', 'signal') || null,
    confidence: result.confidence,
    regime: result.regime,
    advice: result.advice || null,
    horizon_scores_json: jsonValue(result.horizon_scores || {}),
    score_parts_json: jsonValue(result.parts || []),
    source_errors_json: jsonValue(result.source_errors || []),
    raw_analysis_json: jsonValue(item),
  };
  await upsert(
    connection,
    'stock_daily_signal_score',
    row,
    Object.keys(row).filter((column) => !['stock_code', 'trade_date', 'adjust_type'].includes(column)),
  );
}

function outcomeSpecs(result, adjustType) {
  const windows = {
    short_term: [1, 3, 5],
    medium_term: [10, 20],
    long_term: [60, 120],
  };
  const item = result.raw || {};
  const technical = item.technical || {};
  const stockCode = String(result.code || item.code || '');
  const signalClose = numberOrNull(technical.latest_close);
  if (!stockCode || !technical.trade_date || signalClose == null) {
    return [];
  }
  return Object.entries(windows).flatMap(([horizon, windowDays]) => {
    const scoreInfo = result.horizon_scores?.[horizon] || {};
    return windowDays.map((days) => ({
      stock_code: stockCode,
      signal_trade_date: technical.trade_date,
      adjust_type: adjustType,
      horizon,
      window_days: days,
      signal_score: intOrNull(scoreInfo.score),
      signal_label: scoreInfo.signal || null,
      signal_close: signalClose,
      raw_signal_json: jsonValue({
        score: result.score,
        signal: result.signal,
        confidence: result.confidence,
        regime: result.regime,
        horizon,
        horizon_score: scoreInfo,
      }),
    }));
  });
}

async function persistSignalOutcomes(connection, result, adjustType) {
  for (const spec of outcomeSpecs(result, adjustType)) {
    await upsert(
      connection,
      'stock_signal_outcome',
      { ...spec, status: 'pending' },
      ['signal_score', 'signal_label', 'signal_close', 'raw_signal_json'],
    );
  }
}

async function refreshSignalOutcomes(connection) {
  await connection.query(`
UPDATE stock_signal_outcome outcome
JOIN (
  SELECT target_rank.id, target_rank.trade_date AS target_trade_date, target_rank.close_price AS target_close
  FROM (
    SELECT
      outcome_inner.id,
      outcome_inner.window_days,
      quote.trade_date,
      quote.close_price,
      ROW_NUMBER() OVER (PARTITION BY outcome_inner.id ORDER BY quote.trade_date) AS future_rank
    FROM stock_signal_outcome outcome_inner
    JOIN stock_daily_quote quote
      ON quote.stock_code = outcome_inner.stock_code
     AND quote.adjust_type = outcome_inner.adjust_type
     AND quote.trade_date > outcome_inner.signal_trade_date
    WHERE outcome_inner.signal_close IS NOT NULL
      AND quote.close_price IS NOT NULL
  ) target_rank
  WHERE target_rank.future_rank = target_rank.window_days
) target
  ON target.id = outcome.id
JOIN (
  SELECT
    range_rank.id,
    MIN((range_rank.close_price / NULLIF(range_rank.signal_close, 0) - 1) * 100) AS max_drawdown_pct,
    MAX((range_rank.close_price / NULLIF(range_rank.signal_close, 0) - 1) * 100) AS max_runup_pct
  FROM (
    SELECT
      outcome_inner.id,
      outcome_inner.window_days,
      outcome_inner.signal_close,
      quote.close_price,
      ROW_NUMBER() OVER (PARTITION BY outcome_inner.id ORDER BY quote.trade_date) AS future_rank
    FROM stock_signal_outcome outcome_inner
    JOIN stock_daily_quote quote
      ON quote.stock_code = outcome_inner.stock_code
     AND quote.adjust_type = outcome_inner.adjust_type
     AND quote.trade_date > outcome_inner.signal_trade_date
    WHERE outcome_inner.signal_close IS NOT NULL
      AND quote.close_price IS NOT NULL
  ) range_rank
  WHERE range_rank.future_rank <= range_rank.window_days
  GROUP BY range_rank.id
) range_stats
  ON range_stats.id = outcome.id
SET
  outcome.target_trade_date = target.target_trade_date,
  outcome.target_close = target.target_close,
  outcome.return_pct = (target.target_close / NULLIF(outcome.signal_close, 0) - 1) * 100,
  outcome.max_drawdown_pct = range_stats.max_drawdown_pct,
  outcome.max_runup_pct = range_stats.max_runup_pct,
  outcome.hit = CASE
    WHEN outcome.signal_label IN ('强买', '买入偏向')
      THEN IF((target.target_close / NULLIF(outcome.signal_close, 0) - 1) * 100 > 0, 1, 0)
    WHEN outcome.signal_label IN ('卖出偏向', '强卖/回避')
      THEN IF((target.target_close / NULLIF(outcome.signal_close, 0) - 1) * 100 < 0, 1, 0)
    ELSE NULL
  END,
  outcome.status = 'matured',
  outcome.evaluated_at = CURRENT_TIMESTAMP,
  outcome.raw_result_json = JSON_OBJECT(
    'target_trade_date', target.target_trade_date,
    'target_close', target.target_close,
    'max_drawdown_pct', range_stats.max_drawdown_pct,
    'max_runup_pct', range_stats.max_runup_pct
  )
`);
}

function emptyEvaluationSummary() {
  return { short_term: {}, medium_term: {}, long_term: {} };
}

async function fetchEvaluationSummariesForResults(connection, results, adjustType) {
  const codes = [...new Set(results.map((result) => String(result.code)).filter(Boolean))];
  if (!codes.length) {
    return {};
  }
  const placeholders = codes.map(() => '?').join(', ');
  const [rows] = await connection.query(
    `
SELECT
  stock_code,
  horizon,
  window_days,
  COUNT(*) AS sample_count,
  SUM(CASE WHEN hit IS NULL THEN 0 ELSE 1 END) AS directional_count,
  AVG(CASE WHEN hit IS NULL THEN NULL ELSE hit END) * 100 AS hit_rate_pct,
  AVG(return_pct) AS avg_return_pct,
  AVG(max_drawdown_pct) AS avg_max_drawdown_pct,
  AVG(max_runup_pct) AS avg_max_runup_pct
FROM stock_signal_outcome
WHERE status = 'matured'
  AND adjust_type = ?
  AND stock_code IN (${placeholders})
  AND (signal_score > 70 OR signal_score < -70)
GROUP BY stock_code, horizon, window_days
ORDER BY stock_code, horizon, window_days
`,
    [adjustType, ...codes],
  );
  const summaries = {};
  for (const row of rows) {
    summaries[row.stock_code] ||= emptyEvaluationSummary();
    if (summaries[row.stock_code][row.horizon]) {
      summaries[row.stock_code][row.horizon][Number(row.window_days)] = {
        sample_count: Number(row.sample_count || 0),
        directional_count: Number(row.directional_count || 0),
        hit_rate_pct: numberOrNull(row.hit_rate_pct),
        avg_return_pct: numberOrNull(row.avg_return_pct),
        avg_excess_return_pct: null,
        avg_max_drawdown_pct: numberOrNull(row.avg_max_drawdown_pct),
        avg_max_runup_pct: numberOrNull(row.avg_max_runup_pct),
      };
    }
  }
  return summaries;
}

function formatDecimal(value, digits = 4) {
  const numeric = numberOrNull(value);
  return numeric == null ? '暂无' : numeric.toFixed(digits);
}

function formatPercent(value) {
  const numeric = numberOrNull(value);
  return numeric == null ? '暂无' : `${numeric.toFixed(2)}%`;
}

function formatEvaluationLines(summary) {
  const labels = { short_term: '短期', medium_term: '中期', long_term: '长期' };
  const windows = { short_term: [1, 3, 5], medium_term: [10, 20], long_term: [60, 120] };
  const lines = [];
  for (const [horizon, daysList] of Object.entries(windows)) {
    for (const days of daysList) {
      const item = summary?.[horizon]?.[days];
      if (!item) continue;
      lines.push(
        `- ${labels[horizon]} ${days}日：高强度样本 ${Number(item.sample_count || 0)}，` +
          `命中率 ${formatPercent(item.hit_rate_pct)}，` +
          `平均收益 ${formatPercent(item.avg_return_pct)}，` +
          `平均回撤 ${formatPercent(item.avg_max_drawdown_pct)}，` +
          `平均上冲 ${formatPercent(item.avg_max_runup_pct)}`,
      );
    }
  }
  return lines.length ? lines : ['暂无已到期历史验证样本，先持续积累。'];
}

function generateFinalReport(result) {
  const item = result.raw || {};
  const code = String(result.code || item.code || '');
  const name = String(result.name || item.name || '');
  const technical = item.technical || {};
  const trend = item.technical_trend || {};
  const metrics = metricValues(item);
  const sourceErrors = result.source_errors || [];
  const tradeDate = technical.trade_date || '未知交易日';
  const displayName = [code, name].filter(Boolean).join(' ');
  let conclusion = '观望。当前多空证据接近均衡，不适合给出明确买入或卖出信号。';
  if (result.score >= 50) conclusion = '强买入偏向，但仍应等待成交量和趋势继续确认。';
  else if (result.score >= 15) conclusion = '买入偏向存在，更适合分批观察或等待技术面进一步确认。';
  else if (result.score <= -50) conclusion = '强回避偏向，风险信号较集中。';
  else if (result.score <= -15) conclusion = '卖出或回避偏向，短期风险证据强于机会证据。';

  const rsi = technical.rsi || {};
  const macd = technical.macd || {};
  const boll = technical.boll || {};
  const strengths = item.strengths || ['暂无明确优势'];
  const risks = item.risks || ['暂无明确风险'];
  const horizonLines = [
    ['short_term', '短期'],
    ['medium_term', '中期'],
    ['long_term', '长期'],
  ]
    .filter(([key]) => result.horizon_scores?.[key]?.score != null && result.horizon_scores?.[key]?.signal)
    .map(([key, label]) => `- ${label}评分：${result.horizon_scores[key].score}/100（${result.horizon_scores[key].signal}）`);

  const lines = [
    `# ${displayName} 最终分析报告`,
    '',
    `- 交易日：${tradeDate}`,
    `- 评分：${result.score}/100`,
    `- 信号：${result.signal}`,
    `- 置信度：${result.confidence}`,
    `- 市场状态：${result.regime}`,
    ...horizonLines,
    '',
    '## 结论',
    '',
    conclusion,
    '',
    '## 核心数据',
    '',
    `- 收盘价：${formatDecimal(technical.latest_close)}`,
    `- 成交量：${formatDecimal(technical.latest_volume)} 手`,
    `- 成交额：${formatDecimal(technical.latest_amount)} 元`,
    `- RSI：${formatDecimal(rsi.rsi6, 6)} / ${formatDecimal(rsi.rsi12, 6)} / ${formatDecimal(rsi.rsi24, 6)}`,
    `- MACD：DIF ${formatDecimal(macd.dif, 6)} / DEA ${formatDecimal(macd.dea, 6)} / 柱 ${formatDecimal(macd.bar, 6)}`,
    `- BOLL：${boll.position || '暂无'}`,
    `- 趋势评级：${trend.rating || '暂无'}，趋势评分 ${trend.score ?? '暂无'}`,
    `- 财报期：${item.report_date || '暂无'}，ROE ${formatPercent(metrics.ROE)}，经营现金流/净利润 ${formatDecimal(metrics['经营现金流/净利润'])} 倍`,
    '',
    '## 分析',
    '',
    `基本面优势：${strengths.map(String).join('；')}。`,
    `主要风险：${risks.map(String).join('；')}。`,
    '',
    `技术趋势：${trend.conclusion || '暂无明确趋势结论'}`,
    `短线择时：${result.advice}`,
    '',
    '## 历史验证',
    '',
    ...formatEvaluationLines(result.evaluation_summary),
    '',
    '## 操作建议',
    '',
    result.advice,
  ];
  if (sourceErrors.length) {
    lines.push('', '## 数据提醒', '', ...sourceErrors.map(String));
  }
  const reportText = `${lines.join('\n').trimEnd()}\n`;
  const reportJson = {
    score: result.score,
    signal: result.signal,
    confidence: result.confidence,
    regime: result.regime,
    advice: result.advice,
    horizon_scores: result.horizon_scores || {},
    strengths,
    risks,
    source_errors: sourceErrors,
    evaluation_summary: result.evaluation_summary || emptyEvaluationSummary(),
  };
  return {
    title: `${displayName} ${tradeDate} 最终分析报告`,
    text: reportText,
    json: reportJson,
  };
}

async function persistReport(connection, result, adjustType) {
  const item = result.raw || {};
  const technical = item.technical || {};
  const report = generateFinalReport(result);
  await upsert(
    connection,
    'stock_daily_report',
    {
      stock_code: String(result.code),
      trade_date: technical.trade_date,
      adjust_type: adjustType,
      report_type: 'final_summary',
      report_title: report.title,
      report_text: report.text,
      report_format: 'markdown',
      report_json: jsonValue(report.json),
    },
    ['report_title', 'report_text', 'report_format', 'report_json'],
  );
}

async function persistIngestResults(connection, results, adjustType) {
  const persistedCodes = [];
  for (const result of results) {
    const item = result.raw || {};
    const technical = item.technical || {};
    if (!technical.trade_date) {
      const error = new Error(`${item.code || result.code || '未知股票'} 缺少技术面交易日，无法写入每日数据表`);
      error.statusCode = 400;
      throw error;
    }
    persistedCodes.push(String(result.code));
    await persistSecurity(connection, item);
    await persistQuote(connection, item, adjustType);
    await persistTechnical(connection, item, adjustType);
    await persistFinancial(connection, item);
    await persistTrend(connection, item, adjustType);
    await persistTrendWindows(connection, item, adjustType);
    await persistScore(connection, result, adjustType);
    await persistSignalOutcomes(connection, result, adjustType);
  }
  await upsert(
    connection,
    'stock_data_ingest_run',
    {
      run_finished_at: new Date(),
      status: 'success',
      stock_codes_json: jsonValue(persistedCodes),
      message: `已通过接口写入 ${persistedCodes.length} 只股票的每日分析数据`,
    },
    ['run_finished_at', 'status', 'stock_codes_json', 'message'],
  );
  await refreshSignalOutcomes(connection);
  const summaries = await fetchEvaluationSummariesForResults(connection, results, adjustType);
  for (const result of results) {
    result.evaluation_summary = summaries[String(result.code)] || emptyEvaluationSummary();
    await persistReport(connection, result, adjustType);
  }
}

app.get('/api/health', async (_req, res) => {
  const [rows] = await pool.query('SELECT 1 AS ok');
  res.json({
    ok: rows[0]?.ok === 1,
    database: process.env.MYSQL_DATABASE || 'stock_analysis_test',
  });
});

app.get('/api/dates', async (_req, res) => {
  const dates = await loadDateSummaries();
  res.json({ dates });
});

app.get('/api/analysis', async (req, res) => {
  const summaries = await loadDateSummaries();
  const tradeDate = req.query.date ? validateTradeDate(String(req.query.date)) : summaries[0]?.tradeDate;

  if (!tradeDate) {
    res.json({ tradeDate: null, summary: null, items: [] });
    return;
  }

  const [rows] = await pool.query(
    `
      SELECT
        DATE_FORMAT(s.trade_date, '%Y-%m-%d') AS tradeDate,
        s.stock_code AS stockCode,
        COALESCE(sec.name, '') AS name,
        COALESCE(sec.industry, '') AS industry,
        s.adjust_type AS adjustType,
        s.score,
        s.signal_label AS signalLabel,
        s.short_term_score AS shortTermScore,
        s.short_term_signal_label AS shortTermSignalLabel,
        s.medium_term_score AS mediumTermScore,
        s.medium_term_signal_label AS mediumTermSignalLabel,
        s.long_term_score AS longTermScore,
        s.long_term_signal_label AS longTermSignalLabel,
        s.confidence,
        s.regime,
        s.advice,
        s.horizon_scores_json,
        s.source_errors_json,
        q.close_price AS closePrice,
        q.turnover_rate AS turnoverRate,
        q.volume_lots AS volumeLots,
        q.amount,
        t.trend_rating AS trendRating,
        t.trend_score AS trendScore,
        r.report_title AS reportTitle,
        r.report_json
      FROM stock_daily_signal_score s
      LEFT JOIN stock_security sec ON sec.stock_code = s.stock_code
      LEFT JOIN stock_daily_quote q
        ON q.stock_code = s.stock_code
       AND q.trade_date = s.trade_date
       AND q.adjust_type = s.adjust_type
      LEFT JOIN stock_daily_trend t
        ON t.stock_code = s.stock_code
       AND t.trade_date = s.trade_date
       AND t.adjust_type = s.adjust_type
      LEFT JOIN stock_daily_report r
        ON r.stock_code = s.stock_code
       AND r.trade_date = s.trade_date
       AND r.adjust_type = s.adjust_type
       AND r.report_type = 'final_summary'
      WHERE s.trade_date = ?
      ORDER BY s.score DESC, s.stock_code ASC
    `,
    [tradeDate],
  );

  res.json({
    tradeDate,
    summary: summaries.find((item) => item.tradeDate === tradeDate) || null,
    items: rows.map(mapAnalysisItem),
  });
});

app.get('/api/stocks/:code', async (req, res) => {
  const stockCode = validateStockCode(req.params.code);
  const tradeDate = req.query.date
    ? validateTradeDate(String(req.query.date))
    : await latestTradeDate(stockCode);

  if (!tradeDate) {
    res.status(404).json({ error: '没有找到该股票的分析记录' });
    return;
  }

  const [rows] = await pool.query(
    `
      SELECT
        DATE_FORMAT(s.trade_date, '%Y-%m-%d') AS tradeDate,
        s.stock_code AS stockCode,
        COALESCE(sec.name, '') AS name,
        COALESCE(sec.industry, '') AS industry,
        DATE_FORMAT(sec.listed_date, '%Y-%m-%d') AS listedDate,
        s.adjust_type AS adjustType,
        s.score,
        s.signal_label AS signalLabel,
        s.short_term_score AS shortTermScore,
        s.short_term_signal_label AS shortTermSignalLabel,
        s.medium_term_score AS mediumTermScore,
        s.medium_term_signal_label AS mediumTermSignalLabel,
        s.long_term_score AS longTermScore,
        s.long_term_signal_label AS longTermSignalLabel,
        s.confidence,
        s.regime,
        s.advice,
        s.horizon_scores_json,
        s.score_parts_json,
        s.source_errors_json,
        q.close_price AS closePrice,
        q.volume_lots AS volumeLots,
        q.amount,
        q.turnover_rate AS turnoverRate,
        tech.ma5,
        tech.ma10,
        tech.ma20,
        tech.ma60,
        tech.ma120,
        tech.ma250,
        tech.avg_volume_5 AS avgVolume5,
        tech.avg_volume_20 AS avgVolume20,
        tech.volume_ratio_5 AS volumeRatio5,
        tech.volume_ratio_20 AS volumeRatio20,
        tech.macd_dif AS macdDif,
        tech.macd_dea AS macdDea,
        tech.macd_bar AS macdBar,
        tech.boll_mid AS bollMid,
        tech.boll_upper AS bollUpper,
        tech.boll_lower AS bollLower,
        tech.boll_position AS bollPosition,
        tech.kdj_k AS kdjK,
        tech.kdj_d AS kdjD,
        tech.kdj_j AS kdjJ,
        tech.rsi6,
        tech.rsi12,
        tech.rsi24,
        trend.trend_rating AS trendRating,
        trend.trend_score AS trendScore,
        trend.conclusion AS trendConclusion,
        trend.signals_json AS trendSignalsJson,
        report.report_title AS reportTitle,
        report.report_text AS reportText,
        report.report_json
      FROM stock_daily_signal_score s
      LEFT JOIN stock_security sec ON sec.stock_code = s.stock_code
      LEFT JOIN stock_daily_quote q
        ON q.stock_code = s.stock_code
       AND q.trade_date = s.trade_date
       AND q.adjust_type = s.adjust_type
      LEFT JOIN stock_daily_technical tech
        ON tech.stock_code = s.stock_code
       AND tech.trade_date = s.trade_date
       AND tech.adjust_type = s.adjust_type
      LEFT JOIN stock_daily_trend trend
        ON trend.stock_code = s.stock_code
       AND trend.trade_date = s.trade_date
       AND trend.adjust_type = s.adjust_type
      LEFT JOIN stock_daily_report report
        ON report.stock_code = s.stock_code
       AND report.trade_date = s.trade_date
       AND report.adjust_type = s.adjust_type
       AND report.report_type = 'final_summary'
      WHERE s.stock_code = ?
        AND s.trade_date = ?
      LIMIT 1
    `,
    [stockCode, tradeDate],
  );

  if (!rows.length) {
    res.status(404).json({ error: '没有找到该日期的股票分析记录' });
    return;
  }

  const [financialRows] = await pool.query(
    `
      SELECT
        DATE_FORMAT(report_date, '%Y-%m-%d') AS reportDate,
        eps,
        net_asset_per_share AS netAssetPerShare,
        operating_cash_per_share AS operatingCashPerShare,
        roe,
        gross_margin AS grossMargin,
        net_margin AS netMargin,
        revenue_growth AS revenueGrowth,
        net_profit_growth AS netProfitGrowth,
        asset_growth AS assetGrowth,
        debt_ratio AS debtRatio,
        current_ratio AS currentRatio,
        quick_ratio AS quickRatio,
        ocf_to_profit AS ocfToProfit
      FROM stock_financial_report
      WHERE stock_code = ?
      ORDER BY report_date DESC
      LIMIT 1
    `,
    [stockCode],
  );

  const [windowRows] = await pool.query(
    `
      SELECT
        window_days AS windowDays,
        return_pct AS returnPct,
        close_vs_ma_pct AS closeVsMaPct,
        macd_positive_ratio AS macdPositiveRatio,
        boll_mid_above_ratio AS bollMidAboveRatio,
        rsi24,
        volume_ratio_20 AS volumeRatio20
      FROM stock_daily_trend_window
      WHERE stock_code = ?
        AND trade_date = ?
      ORDER BY window_days ASC
    `,
    [stockCode, tradeDate],
  );

  const [historyRows] = await pool.query(
    `
      SELECT
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        score,
        signal_label AS signalLabel,
        short_term_score AS shortTermScore,
        medium_term_score AS mediumTermScore,
        long_term_score AS longTermScore,
        confidence
      FROM stock_daily_signal_score
      WHERE stock_code = ?
      ORDER BY trade_date ASC
    `,
    [stockCode],
  );

  const [accuracyRows] = await pool.query(
    `
      SELECT
        horizon,
        window_days AS windowDays,
        COUNT(*) AS sampleCount,
        SUM(CASE WHEN hit IS NULL THEN 0 ELSE 1 END) AS directionalCount,
        AVG(CASE WHEN hit IS NULL THEN NULL ELSE hit END) * 100 AS hitRatePct,
        AVG(return_pct) AS avgReturnPct,
        AVG(max_drawdown_pct) AS avgMaxDrawdownPct,
        AVG(max_runup_pct) AS avgMaxRunupPct
      FROM stock_signal_outcome
      WHERE stock_code = ?
        AND status = 'matured'
        AND (signal_score > 70 OR signal_score < -70)
      GROUP BY horizon, window_days
      ORDER BY ${horizonOrderExpression('horizon')}, window_days ASC
    `,
    [stockCode],
  );

  res.json({
    detail: mapDetail(rows[0]),
    financial: financialRows[0] || null,
    trendWindows: windowRows,
    history: historyRows,
    accuracySummary: accuracyRows,
  });
});

app.get('/api/stocks/:code/history', async (req, res) => {
  const stockCode = validateStockCode(req.params.code);
  const [rows] = await pool.query(
    `
      SELECT
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        score,
        signal_label AS signalLabel,
        short_term_score AS shortTermScore,
        medium_term_score AS mediumTermScore,
        long_term_score AS longTermScore,
        confidence
      FROM stock_daily_signal_score
      WHERE stock_code = ?
      ORDER BY trade_date ASC
    `,
    [stockCode],
  );
  res.json({ stockCode, history: rows });
});

app.post('/api/ingest/daily-analysis', requireIngestAuth(ingestToken), async (req, res) => {
  const adjustType = req.body?.adjustType || 'qfq';
  const results = Array.isArray(req.body?.results) ? req.body.results : null;
  if (!['none', 'qfq', 'hfq'].includes(adjustType)) {
    const error = new Error('adjustType 只支持 none/qfq/hfq');
    error.statusCode = 400;
    throw error;
  }
  if (!results) {
    const error = new Error('results 必须是数组');
    error.statusCode = 400;
    throw error;
  }
  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();
    await persistIngestResults(connection, results, adjustType);
    await connection.commit();
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
  res.json({
    ok: true,
    adjustType,
    persistedCount: results.length,
    items: results.map((result) => ({
      stockCode: String(result.code),
      tradeDate: result.raw?.technical?.trade_date || null,
      score: result.score,
      signal: result.signal,
      confidence: result.confidence,
    })),
  });
});

const distPath = path.join(projectRootPath, 'docs/.vitepress/dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
  });
}

app.use((err, _req, res, _next) => {
  const statusCode = err.statusCode || 500;
  if (statusCode >= 500) {
    console.error(err);
  }
  res.status(statusCode).json({
    error: statusCode === 500 ? '服务端查询失败' : err.message,
    detail: process.env.NODE_ENV === 'production' ? undefined : err.message,
  });
});

  return app;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT || process.env.STOCK_DASHBOARD_PORT || 3210);
  const app = createApp();
  app.listen(port, () => {
    console.log(`Stock analysis API listening on http://127.0.0.1:${port}`);
  });
}
