import 'dotenv/config';

import cors from 'cors';
import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import mysql from 'mysql2/promise';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const app = express();
const port = Number(process.env.PORT || process.env.STOCK_DASHBOARD_PORT || 3210);

const pool = mysql.createPool({
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

app.use(cors());
app.use(express.json());

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

const distPath = path.join(projectRoot, 'docs/.vitepress/dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
  });
}

app.use((err, _req, res, _next) => {
  const statusCode = err.statusCode || 500;
  console.error(err);
  res.status(statusCode).json({
    error: statusCode === 500 ? '服务端查询失败' : err.message,
    detail: process.env.NODE_ENV === 'production' ? undefined : err.message,
  });
});

app.listen(port, () => {
  console.log(`Stock analysis API listening on http://127.0.0.1:${port}`);
});
