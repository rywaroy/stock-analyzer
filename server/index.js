import "dotenv/config";

import cors from "cors";
import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import mysql from "mysql2/promise";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
export const DEFAULT_INGEST_API_TOKEN =
  "stock-analysis-ingest-2026-6f8c2d91b7a443e0";

const AI_ETF_PORTFOLIO_NAME = "AI_RECOMMENDED_ETF";
const AI_ETF_INITIAL_NOTIONAL = 1_000_000;
const AI_ETF_TARGET_COUNT = 10;
const AI_ETF_WEIGHT_CHANGE_THRESHOLD = 0.5;
const AI_ETF_MIN_HOLD_DAYS = 20;
const AI_ETF_SELL_MEDIUM_THRESHOLD = -15;
const AI_ETF_SELL_LONG_THRESHOLD = -15;
const AI_ETF_ENTRY_MEDIUM_THRESHOLD = 25;
const AI_ETF_ENTRY_LONG_THRESHOLD = 20;
const HORIZON_STABILITY_MAX_DELTA = {
  medium_term: 18,
  long_term: 12,
};
const TOTAL_SCORE_STABILITY_MAX_DELTA = 25;
const HISTORICAL_SCORE_LOOKBACK_ROWS = 20;
const HISTORY_SCORE_HORIZONS = [
  ["overall", "总分", "score", []],
  ["medium_term", "中期", "medium_term_score", [20, 60, 120]],
  ["long_term", "长期", "long_term_score", [60, 120, 250]],
];

let pool;

export function createDefaultPool() {
  return mysql.createPool({
    host: process.env.MYSQL_HOST || "127.0.0.1",
    port: Number(process.env.MYSQL_PORT || 3306),
    user: process.env.MYSQL_USER || "root",
    password: process.env.MYSQL_PASSWORD || "",
    database: process.env.MYSQL_DATABASE || "stock_analysis_test",
    waitForConnections: true,
    connectionLimit: Number(process.env.MYSQL_CONNECTION_LIMIT || 8),
    timezone: "+08:00",
    dateStrings: true,
    decimalNumbers: true,
    charset: "utf8mb4",
  });
}

function unauthorizedIngestError() {
  const error = new Error("上报接口未授权");
  error.statusCode = 401;
  return error;
}

function requireIngestAuth(ingestToken) {
  return (req, _res, next) => {
    const authHeader = req.get("authorization") || "";
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
  app.use(express.json({ limit: "20mb" }));

  function parseJson(value, fallback) {
    if (value == null || value === "") {
      return fallback;
    }
    if (typeof value === "object") {
      return value;
    }
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function toNumber(value) {
    if (value == null || value === "") {
      return null;
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  function validateStockCode(code) {
    if (!/^[0-9A-Za-z]{1,16}$/.test(code || "")) {
      const error = new Error("stock code 格式不正确");
      error.statusCode = 400;
      throw error;
    }
    return code;
  }

  function validateTradeDate(date) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date || "")) {
      const error = new Error("trade date 格式应为 YYYY-MM-DD");
      error.statusCode = 400;
      throw error;
    }
    return date;
  }

  function horizonOrderExpression(column = "horizon") {
    return `FIELD(${column}, 'short_term', 'medium_term', 'long_term')`;
  }

  function asyncHandler(handler) {
    return (req, res, next) => {
      Promise.resolve(handler(req, res, next)).catch(next);
    };
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
      name: row.name || "",
      displayName: [row.stockCode, row.name].filter(Boolean).join(" "),
      industry: row.industry || "",
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
      conclusion: reportJson.conclusion || "",
      advice: row.advice || reportJson.advice || "",
      closePrice: toNumber(row.closePrice),
      turnoverRate: toNumber(row.turnoverRate),
      volumeLots: toNumber(row.volumeLots),
      amount: toNumber(row.amount),
      trendRating: row.trendRating,
      trendScore: toNumber(row.trendScore),
      reportTitle: row.reportTitle || "",
      strengths: Array.isArray(reportJson.strengths)
        ? reportJson.strengths
        : [],
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
      name: row.name || "",
      displayName: [row.stockCode, row.name].filter(Boolean).join(" "),
      industry: row.industry || "",
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
      conclusion: reportJson.conclusion || "",
      advice: row.advice || reportJson.advice || "",
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
        conclusion: row.trendConclusion || "",
        signals: parseJson(row.trendSignalsJson, []),
      },
      report: {
        title: row.reportTitle || "",
        text: row.reportText || "",
        json: reportJson,
      },
    };
  }

  function mapAiEtfSnapshot(row) {
    return {
      portfolioName: row.portfolioName,
      tradeDate: row.tradeDate,
      adjustType: row.adjustType,
      selectionRule: row.selectionRule || "",
      nav: toNumber(row.nav),
      dailyReturnPct: toNumber(row.dailyReturnPct),
      cumulativeReturnPct: toNumber(row.cumulativeReturnPct),
      realizedPnl: toNumber(row.realizedPnl),
      unrealizedPnl: toNumber(row.unrealizedPnl),
      totalPnl: toNumber(row.totalPnl),
      turnoverPct: toNumber(row.turnoverPct),
      holdingCount: Number(row.holdingCount || 0),
      summary: parseJson(row.summary_json, {}),
      updatedAt: row.updatedAt,
    };
  }

  function mapAiEtfHolding(row) {
    return {
      portfolioName: row.portfolioName,
      tradeDate: row.tradeDate,
      stockCode: row.stockCode,
      stockName: row.stockName || "",
      industry: row.industry || "",
      previousWeightPct: toNumber(row.previousWeightPct),
      targetWeightPct: toNumber(row.targetWeightPct),
      weightDeltaPct: toNumber(row.weightDeltaPct),
      action: row.action,
      referencePrice: toNumber(row.referencePrice),
      simulatedQuantity: toNumber(row.simulatedQuantity),
      simulatedNotional: toNumber(row.simulatedNotional),
      score: toNumber(row.score),
      signalLabel: row.signalLabel || "",
      shortTermScore: toNumber(row.shortTermScore),
      shortTermSignalLabel: row.shortTermSignalLabel || "",
      mediumTermScore: toNumber(row.mediumTermScore),
      mediumTermSignalLabel: row.mediumTermSignalLabel || "",
      longTermScore: toNumber(row.longTermScore),
      longTermSignalLabel: row.longTermSignalLabel || "",
      confidence: row.confidence || "",
      rationale: row.rationale || "",
      risks: parseJson(row.risks_json, []),
    };
  }

  function mapAiEtfTrade(row) {
    return {
      portfolioName: row.portfolioName,
      tradeDate: row.tradeDate,
      stockCode: row.stockCode,
      stockName: row.stockName || "",
      action: row.action,
      previousWeightPct: toNumber(row.previousWeightPct),
      targetWeightPct: toNumber(row.targetWeightPct),
      weightDeltaPct: toNumber(row.weightDeltaPct),
      referencePrice: toNumber(row.referencePrice),
      simulatedQuantityDelta: toNumber(row.simulatedQuantityDelta),
      simulatedNotionalDelta: toNumber(row.simulatedNotionalDelta),
      realizedPnl: toNumber(row.realizedPnl),
      realizedReturnPct: toNumber(row.realizedReturnPct),
      reason: row.reason || "",
    };
  }

  function resultTradeDate(result) {
    return String(result?.raw?.technical?.trade_date || "");
  }

  function groupResultsByTradeDate(results = []) {
    const grouped = {};
    for (const result of results) {
      const tradeDate = resultTradeDate(result);
      if (!tradeDate) continue;
      grouped[tradeDate] ||= [];
      grouped[tradeDate].push(result);
    }
    return grouped;
  }

  function resultClosePrice(result) {
    return numberOrNull(result?.raw?.technical?.latest_close);
  }

  function isStarMarketStock(code) {
    return String(code || "").startsWith("688");
  }

  function aiEtfRankScore(result) {
    let penalty = 0;
    if (result.confidence === "低") penalty += 15;
    const sourceErrors = result.source_errors || [];
    if (sourceErrors.length) penalty += Math.min(20, sourceErrors.length * 5);
    return (
      horizonScore(result, "short_term") * 0.2 +
      horizonScore(result, "medium_term") * 0.35 +
      horizonScore(result, "long_term") * 0.35 +
      (numberOrNull(result.score) || 0) * 0.1 -
      penalty
    );
  }

  function aiEtfValidCandidate(result) {
    return Boolean(
      resultTradeDate(result) &&
        resultClosePrice(result) != null &&
        result.code &&
        !isStarMarketStock(result.code) &&
        result.confidence !== "低" &&
        !(result.source_errors || []).length &&
        horizonScore(result, "medium_term") > 0 &&
        horizonScore(result, "long_term") > 0,
    );
  }

  function aiEtfEntryCandidate(result) {
    return (
      aiEtfValidCandidate(result) &&
      horizonScore(result, "medium_term") >= AI_ETF_ENTRY_MEDIUM_THRESHOLD &&
      horizonScore(result, "long_term") >= AI_ETF_ENTRY_LONG_THRESHOLD
    );
  }

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function previousHoldingDays(previous, tradeDate) {
    const firstHeld = parseDate(previous.first_held_date || previous.firstHeldDate || previous.trade_date || previous.tradeDate);
    const current = parseDate(tradeDate);
    if (!firstHeld || !current) return null;
    return Math.max(0, Math.round((current - firstHeld) / 86400000));
  }

  function previousFirstHeldDate(previous, tradeDate) {
    return String(previous.first_held_date || previous.firstHeldDate || previous.trade_date || previous.tradeDate || tradeDate);
  }

  function aiEtfShouldSell(result, previous, tradeDate) {
    if (!result) return { sell: true, reason: "本期分析结果缺失，无法继续验证持仓逻辑。" };
    const mediumScore = horizonScore(result, "medium_term");
    const longScore = horizonScore(result, "long_term");
    const sourceErrors = result.source_errors || [];
    const severeBreak = mediumScore <= -30 || longScore <= -30;
    if (sourceErrors.length) return { sell: true, reason: "关键数据源异常，组合不继续承担无法验证的持仓风险。" };
    if (result.confidence === "低") return { sell: true, reason: "评分置信度降为低，退出组合等待重新观察。" };
    if (mediumScore <= AI_ETF_SELL_MEDIUM_THRESHOLD) {
      return { sell: true, reason: `中期评分降至 ${mediumScore.toFixed(0)}，触发组合卖出纪律。` };
    }
    if (longScore <= AI_ETF_SELL_LONG_THRESHOLD) {
      return { sell: true, reason: `长期评分降至 ${longScore.toFixed(0)}，触发组合卖出纪律。` };
    }
    const heldDays = previousHoldingDays(previous, tradeDate);
    if (heldDays != null && heldDays < AI_ETF_MIN_HOLD_DAYS && !severeBreak) {
      return { sell: false, reason: `持仓仅 ${heldDays} 天，未触发硬性风控，维持最小持有期纪律。` };
    }
    if (!aiEtfValidCandidate(result)) {
      return { sell: true, reason: "中长期质量不再满足组合观察池要求。" };
    }
    return { sell: false, reason: "继续保留，仍符合中长期持仓纪律。" };
  }

  function roundWeight(value) {
    return Math.round(value * 10000) / 10000;
  }

  function clampWeight(value, lower = 5, upper = 15) {
    return Math.max(lower, Math.min(upper, value));
  }

  function boundedNormalizeWeights(rawWeights, lower = 5, upper = 15) {
    const entries = Object.entries(rawWeights);
    if (!entries.length) return {};
    const weights = Object.fromEntries(entries.map(([code, value]) => [code, clampWeight(value, lower, upper)]));
    for (let index = 0; index < 20; index += 1) {
      const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
      const diff = 100 - total;
      if (Math.abs(diff) < 0.0001) break;
      const adjustable = Object.keys(weights).filter((code) => (diff > 0 ? weights[code] < upper : weights[code] > lower));
      if (!adjustable.length) break;
      const step = diff / adjustable.length;
      for (const code of adjustable) {
        weights[code] = clampWeight(weights[code] + step, lower, upper);
      }
    }
    const rounded = Object.fromEntries(Object.entries(weights).map(([code, value]) => [code, roundWeight(value)]));
    const residual = roundWeight(100 - Object.values(rounded).reduce((sum, value) => sum + value, 0));
    if (residual) {
      const target = Object.keys(rounded).sort((left, right) => {
        const leftRoom = residual > 0 ? upper - rounded[left] : rounded[left] - lower;
        const rightRoom = residual > 0 ? upper - rounded[right] : rounded[right] - lower;
        return rightRoom - leftRoom;
      })[0];
      rounded[target] = roundWeight(rounded[target] + residual);
    }
    return rounded;
  }

  function previousHoldingByCode(previousHoldings = []) {
    const grouped = {};
    for (const row of previousHoldings) {
      const code = String(row.stock_code || row.stockCode || "");
      if (code) grouped[code] = row;
    }
    return grouped;
  }

  function normalizedAction(previousWeight, targetWeight) {
    const delta = roundWeight(targetWeight - previousWeight);
    if (previousWeight <= 0 && targetWeight > 0) return "buy";
    if (previousWeight > 0 && targetWeight <= 0) return "sell";
    if (delta > AI_ETF_WEIGHT_CHANGE_THRESHOLD) return "increase";
    if (delta < -AI_ETF_WEIGHT_CHANGE_THRESHOLD) return "reduce";
    return "hold";
  }

  function actionReason(action, result = null, detail = null) {
    if (detail) return detail;
    if (action === "buy") return "新纳入组合，已经通过观察池质量筛选。";
    if (action === "sell") return "持仓质量不再满足组合纪律，按调仓参考价模拟卖出。";
    if (action === "increase") return "继续保留且目标权重随中长期胜率和组合约束小幅提高。";
    if (action === "reduce") return "继续保留但目标权重随中长期胜率和风险约束小幅下调。";
    if (result) return "继续保留，评分和风险状态仍满足组合纪律。";
    return "本期无仓位变化。";
  }

  function holdingRationale(result, action) {
    const name = result.name || result.raw?.name || result.code;
    return `${actionReason(action, result)} ${name} 综合分 ${result.score}，短期 ${horizonScore(result, "short_term")}，中期 ${horizonScore(result, "medium_term")}，长期 ${horizonScore(result, "long_term")}。`;
  }

  function selectAiEtfHoldings(candidates, previousByCode, tradeDate) {
    const resultByCode = Object.fromEntries(candidates.map((result) => [String(result.code), result]));
    const retained = [];
    const sellReasons = {};
    for (const [code, previous] of Object.entries(previousByCode)) {
      const previousWeight = numberOrNull(previous.target_weight_pct ?? previous.targetWeightPct) || 0;
      if (previousWeight <= 0) continue;
      const decision = aiEtfShouldSell(resultByCode[code], previous, tradeDate);
      if (decision.sell) {
        sellReasons[code] = decision.reason;
      } else if (resultByCode[code]) {
        retained.push(resultByCode[code]);
      }
    }
    retained.sort((left, right) => aiEtfRankScore(right) - aiEtfRankScore(left));
    const selected = retained.slice(0, AI_ETF_TARGET_COUNT);
    const selectedCodes = new Set(selected.map((result) => String(result.code)));
    const entryCandidates = candidates
      .filter((result) => !selectedCodes.has(String(result.code)) && aiEtfEntryCandidate(result))
      .sort((left, right) => aiEtfRankScore(right) - aiEtfRankScore(left));
    const fallbackCandidates = candidates
      .filter((result) => !selectedCodes.has(String(result.code)) && aiEtfValidCandidate(result))
      .sort((left, right) => aiEtfRankScore(right) - aiEtfRankScore(left));
    const fillPool = [...entryCandidates];
    if (selected.length + fillPool.length < AI_ETF_TARGET_COUNT) {
      const known = new Set(fillPool.map((result) => String(result.code)));
      fillPool.push(...fallbackCandidates.filter((result) => !known.has(String(result.code))));
    }
    return { selected: [...selected, ...fillPool].slice(0, AI_ETF_TARGET_COUNT), sellReasons };
  }

  function targetWeightsForSelection(selected, previousByCode) {
    if (!selected.length) return {};
    if (!Object.keys(previousByCode).length) {
      return Object.fromEntries(selected.map((result) => [String(result.code), roundWeight(100 / selected.length)]));
    }
    const rankScores = selected.map(aiEtfRankScore);
    const averageRank = rankScores.reduce((sum, value) => sum + value, 0) / rankScores.length;
    const rawWeights = {};
    selected.forEach((result, index) => {
      const code = String(result.code);
      const desired = clampWeight(10 + (rankScores[index] - averageRank) * 0.08);
      const previousWeight = numberOrNull(previousByCode[code]?.target_weight_pct ?? previousByCode[code]?.targetWeightPct);
      rawWeights[code] = previousWeight ? previousWeight * 0.7 + desired * 0.3 : desired;
    });
    return boundedNormalizeWeights(rawWeights);
  }

  function buildAiEtfPortfolio(results, adjustType, previousHoldings = []) {
    const candidates = results.filter(
      (result) =>
        resultTradeDate(result) &&
        resultClosePrice(result) != null &&
        result.code &&
        !isStarMarketStock(result.code),
    );
    if (!candidates.length) return null;
    const previousByCode = previousHoldingByCode(previousHoldings);
    const tradeDate = candidates.map(resultTradeDate).sort().at(-1);
    const { selected, sellReasons } = selectAiEtfHoldings(candidates, previousByCode, tradeDate);
    if (selected.length < AI_ETF_TARGET_COUNT) return null;

    const targetWeights = targetWeightsForSelection(selected, previousByCode);
    const holdings = [];
    const rebalance = [];
    let totalUnrealized = 0;
    let totalRealized = 0;
    let turnover = 0;

    for (const result of selected) {
      const code = String(result.code);
      const item = result.raw || {};
      const previous = previousByCode[code] || {};
      const previousWeight = numberOrNull(previous.target_weight_pct ?? previous.targetWeightPct) || 0;
      const targetWeight = targetWeights[code];
      const referencePrice = resultClosePrice(result);
      let simulatedNotional = (AI_ETF_INITIAL_NOTIONAL * targetWeight) / 100;
      let simulatedQuantity = referencePrice ? simulatedNotional / referencePrice : null;
      const previousPrice = numberOrNull(previous.reference_price ?? previous.referencePrice);
      const previousQuantity = numberOrNull(previous.simulated_quantity ?? previous.simulatedQuantity) || 0;
      const unrealized =
        referencePrice != null && previousPrice != null && previousQuantity
          ? (referencePrice - previousPrice) * previousQuantity
          : 0;
      totalUnrealized += unrealized;
      const delta = roundWeight(targetWeight - previousWeight);
      const action = normalizedAction(previousWeight, targetWeight);
      turnover += Math.abs(delta);
      if (action === "hold" && previousQuantity) {
        simulatedQuantity = previousQuantity;
        simulatedNotional = referencePrice ? simulatedQuantity * referencePrice : simulatedNotional;
      }
      const actionDetail = previousByCode[code] ? "继续保留，已经通过观察期和中长期质量筛选。" : null;
      const holding = {
        portfolioName: AI_ETF_PORTFOLIO_NAME,
        tradeDate,
        adjustType,
        stockCode: code,
        stockName: result.name || item.name || "",
        industry: item.industry || "",
        previousWeightPct: roundWeight(previousWeight),
        targetWeightPct: targetWeight,
        weightDeltaPct: delta,
        action,
        referencePrice,
        simulatedQuantity,
        simulatedNotional,
        score: intOrNull(result.score),
        signalLabel: result.signal,
        shortTermScore: intOrNull(result.horizon_scores?.short_term?.score),
        shortTermSignalLabel: result.horizon_scores?.short_term?.signal,
        mediumTermScore: intOrNull(result.horizon_scores?.medium_term?.score),
        mediumTermSignalLabel: result.horizon_scores?.medium_term?.signal,
        longTermScore: intOrNull(result.horizon_scores?.long_term?.score),
        longTermSignalLabel: result.horizon_scores?.long_term?.signal,
        confidence: result.confidence,
        rationale: actionDetail ? `${actionDetail} ${holdingRationale(result, action)}` : holdingRationale(result, action),
        risks: item.risks || [],
        rankScore: Math.round(aiEtfRankScore(result) * 10000) / 10000,
        firstHeldDate: previous ? previousFirstHeldDate(previous, tradeDate) : tradeDate,
        holdingDays: previous ? previousHoldingDays(previous, tradeDate) : 0,
      };
      holdings.push(holding);
      rebalance.push({
        portfolioName: AI_ETF_PORTFOLIO_NAME,
        tradeDate,
        adjustType,
        stockCode: code,
        stockName: holding.stockName,
        action,
        previousWeightPct: holding.previousWeightPct,
        targetWeightPct: holding.targetWeightPct,
        weightDeltaPct: holding.weightDeltaPct,
        referencePrice,
        simulatedQuantityDelta:
          action === "buy"
            ? simulatedQuantity
            : ["increase", "reduce"].includes(action)
              ? (simulatedQuantity || 0) - previousQuantity
              : 0,
        simulatedNotionalDelta: (AI_ETF_INITIAL_NOTIONAL * delta) / 100,
        realizedPnl: 0,
        realizedReturnPct: 0,
        reason: actionReason(action, result, actionDetail),
      });
    }

    const selectedCodes = new Set(holdings.map((holding) => holding.stockCode));
    const resultByCode = Object.fromEntries(candidates.map((result) => [String(result.code), result]));
    for (const [code, previous] of Object.entries(previousByCode)) {
      if (selectedCodes.has(code)) continue;
      const previousWeight = numberOrNull(previous.target_weight_pct ?? previous.targetWeightPct) || 0;
      if (previousWeight <= 0) continue;
      const previousPrice = numberOrNull(previous.reference_price ?? previous.referencePrice);
      const previousQuantity = numberOrNull(previous.simulated_quantity ?? previous.simulatedQuantity) || 0;
      const currentResult = resultByCode[code];
      const referencePrice = currentResult ? resultClosePrice(currentResult) : previousPrice;
      const realizedPnl =
        referencePrice != null && previousPrice != null && previousQuantity
          ? (referencePrice - previousPrice) * previousQuantity
          : 0;
      totalRealized += realizedPnl;
      turnover += previousWeight;
      const stockName = String(previous.stock_name || previous.stockName || "");
      const sellReason = sellReasons[code] || actionReason("sell");
      holdings.push({
        portfolioName: AI_ETF_PORTFOLIO_NAME,
        tradeDate,
        adjustType,
        stockCode: code,
        stockName,
        industry: previous.industry || "",
        previousWeightPct: roundWeight(previousWeight),
        targetWeightPct: 0,
        weightDeltaPct: roundWeight(-previousWeight),
        action: "sell",
        referencePrice,
        simulatedQuantity: 0,
        simulatedNotional: 0,
        score: null,
        signalLabel: null,
        shortTermScore: null,
        shortTermSignalLabel: null,
        mediumTermScore: null,
        mediumTermSignalLabel: null,
        longTermScore: null,
        longTermSignalLabel: null,
        confidence: null,
        rationale: sellReason,
        risks: [],
        rankScore: null,
      });
      rebalance.push({
        portfolioName: AI_ETF_PORTFOLIO_NAME,
        tradeDate,
        adjustType,
        stockCode: code,
        stockName,
        action: "sell",
        previousWeightPct: roundWeight(previousWeight),
        targetWeightPct: 0,
        weightDeltaPct: roundWeight(-previousWeight),
        referencePrice,
        simulatedQuantityDelta: -previousQuantity,
        simulatedNotionalDelta: -(AI_ETF_INITIAL_NOTIONAL * previousWeight) / 100,
        realizedPnl,
        realizedReturnPct:
          referencePrice != null && previousPrice != null && previousPrice !== 0
            ? (referencePrice / previousPrice - 1) * 100
            : 0,
        reason: sellReason,
      });
    }

    const totalPnl = totalRealized + totalUnrealized;
    const hasPrevious = Boolean(Object.keys(previousByCode).length);
    return {
      portfolioName: AI_ETF_PORTFOLIO_NAME,
      tradeDate,
      adjustType,
      selectionRule: hasPrevious
        ? "基金经理式低换手组合：保留仍合格持仓，最小持有期约束，只有中长期恶化/低置信/数据异常才卖出；新增股票需通过观察池质量筛选。"
        : "首次建仓：从观察池中选择中期、长期均为正且数据置信度合格的10只股票，等权配置。",
      nav: AI_ETF_INITIAL_NOTIONAL + totalPnl,
      dailyReturnPct: 0,
      cumulativeReturnPct: (totalPnl / AI_ETF_INITIAL_NOTIONAL) * 100,
      realizedPnl: totalRealized,
      unrealizedPnl: totalUnrealized,
      totalPnl,
      turnoverPct: Math.min(200, roundWeight(turnover)),
      holdingCount: holdings.filter((holding) => holding.targetWeightPct > 0).length,
      holdings,
      rebalance,
      summary: {
        candidateCount: candidates.length,
        selectedCount: AI_ETF_TARGET_COUNT,
        hasPreviousPortfolio: hasPrevious,
        retainedCount: holdings.filter((holding) => holding.targetWeightPct > 0 && previousByCode[holding.stockCode]).length,
        soldCount: holdings.filter((holding) => holding.action === "sell").length,
        minHoldDays: AI_ETF_MIN_HOLD_DAYS,
        entryRule: {
          mediumTermScoreAtLeast: AI_ETF_ENTRY_MEDIUM_THRESHOLD,
          longTermScoreAtLeast: AI_ETF_ENTRY_LONG_THRESHOLD,
          confidence: "非低",
          sourceErrors: "无关键数据异常",
        },
        sellRule: {
          mediumTermScoreAtOrBelow: AI_ETF_SELL_MEDIUM_THRESHOLD,
          longTermScoreAtOrBelow: AI_ETF_SELL_LONG_THRESHOLD,
          confidence: "低",
          sourceErrors: "任一关键异常",
        },
      },
    };
  }

  function previousScoreByCode(previousScores = []) {
    const grouped = {};
    for (const row of previousScores) {
      const code = String(row.stock_code || row.stockCode || "");
      if (code) grouped[code] = row;
    }
    return grouped;
  }

  function addStabilityPart(result, horizon, previousDayScore, rawScore, adjustedScore) {
    const horizonInfo = result.horizon_scores?.[horizon];
    if (!horizonInfo) return;
    const label = String(horizonInfo.label || horizon);
    horizonInfo.parts ||= [];
    horizonInfo.parts.push({
      module: `${label}稳定器`,
      points: adjustedScore - rawScore,
      reason: `参考上一交易日 ${previousDayScore}/100，限制中长期分数单日跳变。`,
    });
  }

  function applyScoreStability(results, previousScores = []) {
    const previousByCode = previousScoreByCode(previousScores);
    if (!Object.keys(previousByCode).length) return results;
    for (const result of results) {
      const previous = previousByCode[String(result.code || "")];
      if (!previous) continue;
      const applied = [];
      for (const [horizon, maxDelta] of Object.entries(HORIZON_STABILITY_MAX_DELTA)) {
        const horizonInfo = result.horizon_scores?.[horizon];
        if (!horizonInfo || stabilityBreakDetected(result, horizon)) continue;
        const previousScore = intOrNull(previous[`${horizon}_score`] ?? previous[`${horizon}Score`]);
        const currentScore = intOrNull(horizonInfo.score);
        const adjustedScore = dampScoreChange(previousScore, currentScore, maxDelta);
        if (previousScore == null || currentScore == null || adjustedScore == null || adjustedScore === currentScore) {
          continue;
        }
        horizonInfo.score = adjustedScore;
        horizonInfo.signal = signalLabelFromScore(adjustedScore);
        horizonInfo.advice = horizonAdvice(horizon, adjustedScore, result.regime);
        addStabilityPart(result, horizon, previousScore, currentScore, adjustedScore);
        applied.push({
          horizon,
          previousScore,
          rawScore: currentScore,
          stabilizedScore: adjustedScore,
          maxDelta,
        });
      }
      const previousTotal = previous.score;
      const currentTotal = intOrNull(result.score);
      const adjustedTotal = dampScoreChange(previousTotal, currentTotal, TOTAL_SCORE_STABILITY_MAX_DELTA);
      if (currentTotal != null && adjustedTotal != null && adjustedTotal !== currentTotal) {
        result.score = adjustedTotal;
        result.signal = signalLabelFromScore(adjustedTotal);
        applied.push({
          horizon: "overall",
          previousScore: intOrNull(previousTotal),
          rawScore: currentTotal,
          stabilizedScore: adjustedTotal,
          maxDelta: TOTAL_SCORE_STABILITY_MAX_DELTA,
        });
      }
      if (applied.length) {
        result.stability_adjustments ||= [];
        result.stability_adjustments.push(...applied);
      }
    }
    return results;
  }

  async function fetchLatestSignalScoresBefore(connection, tradeDate, adjustType) {
    if (!tradeDate) return [];
    const [rows] = await connection.query(
      `
      SELECT
        stock_code,
        score,
        short_term_score,
        medium_term_score,
        long_term_score
      FROM stock_daily_signal_score
      WHERE adjust_type = ?
        AND trade_date = (
          SELECT MAX(trade_date)
          FROM stock_daily_signal_score
          WHERE adjust_type = ?
            AND trade_date < ?
        )
      ORDER BY stock_code
      `,
      [adjustType, adjustType, tradeDate],
    );
    return rows;
  }

  async function fetchHistoricalSignalScoresBefore(
    connection,
    stockCodes,
    tradeDate,
    adjustType,
    limit = HISTORICAL_SCORE_LOOKBACK_ROWS,
  ) {
    const uniqueCodes = [...new Set((stockCodes || []).map(String).filter(Boolean))];
    if (!uniqueCodes.length || !tradeDate) return {};
    const [rows] = await connection.query(
      `
      SELECT
        stock_code,
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS trade_date,
        score,
        short_term_score,
        medium_term_score,
        long_term_score,
        horizon_scores_json,
        score_parts_json,
        raw_analysis_json
      FROM (
        SELECT
          stock_code,
          trade_date,
          score,
          short_term_score,
          medium_term_score,
          long_term_score,
          horizon_scores_json,
          score_parts_json,
          raw_analysis_json,
          ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date DESC) AS row_rank
        FROM stock_daily_signal_score
        WHERE adjust_type = ?
          AND trade_date < ?
          AND stock_code IN (?)
      ) ranked_scores
      WHERE row_rank <= ?
      ORDER BY stock_code, trade_date
      `,
      [adjustType, tradeDate, uniqueCodes, limit],
    );
    const grouped = {};
    for (const row of rows) {
      const code = String(row.stock_code || "");
      if (!code) continue;
      grouped[code] ||= [];
      grouped[code].push(row);
    }
    return grouped;
  }

  async function fetchLatestAiEtfHoldingsBefore(connection, tradeDate, adjustType) {
    if (!tradeDate) return [];
    const [rows] = await connection.query(
      `
      SELECT
        stock_code,
        stock_name,
        industry,
        target_weight_pct,
        reference_price,
        simulated_quantity,
        simulated_notional,
        raw_json
      FROM stock_ai_etf_holding
      WHERE portfolio_name = ?
        AND adjust_type = ?
        AND trade_date = (
          SELECT MAX(trade_date)
          FROM stock_ai_etf_holding
          WHERE portfolio_name = ?
            AND adjust_type = ?
            AND trade_date < ?
        )
        AND target_weight_pct > 0
      ORDER BY stock_code
      `,
      [AI_ETF_PORTFOLIO_NAME, adjustType, AI_ETF_PORTFOLIO_NAME, adjustType, tradeDate],
    );
    return rows.map((row) => {
      const raw = parseJson(row.raw_json, {});
      return {
        ...row,
        first_held_date: raw.firstHeldDate || raw.tradeDate || row.tradeDate,
      };
    });
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
    let where = "";
    if (stockCode) {
      where = "WHERE stock_code = ?";
      params.push(stockCode);
    }
    const [rows] = await pool.query(
      `SELECT DATE_FORMAT(MAX(trade_date), '%Y-%m-%d') AS tradeDate FROM stock_daily_signal_score ${where}`,
      params,
    );
    return rows[0]?.tradeDate || null;
  }

  function numberOrNull(value) {
    if (value == null || value === "") {
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

  function signalLabelFromScore(score) {
    const numeric = intOrNull(score);
    if (numeric == null) return "观望";
    if (numeric >= 50) return "强买";
    if (numeric >= 15) return "买入偏向";
    if (numeric > -15) return "观望";
    if (numeric > -50) return "卖出偏向";
    return "强卖/回避";
  }

  function formatSignedNumber(value, digits = 0) {
    const numeric = numberOrNull(value);
    if (numeric == null) return "暂无";
    return `${numeric > 0 ? "+" : ""}${numeric.toFixed(digits)}`;
  }

  function scoreChangeWord(delta) {
    const numeric = numberOrNull(delta);
    if (numeric == null) return "变化";
    if (numeric > 0) return "升高";
    if (numeric < 0) return "下降";
    return "持平";
  }

  function resultScoreForHorizon(result, horizon) {
    return horizon === "overall" ? intOrNull(result.score) : intOrNull(horizonValue(result, horizon, "score"));
  }

  function tradeDateFromRow(row) {
    return String(row.trade_date || row.tradeDate || "").slice(0, 10);
  }

  function rawAnalysisFromRow(row) {
    return parseJson(row.raw_analysis_json ?? row.rawAnalysisJson ?? row.raw_analysis ?? row.raw, {});
  }

  function horizonScoresFromRow(row) {
    return parseJson(row.horizon_scores_json ?? row.horizonScoresJson ?? row.horizon_scores ?? row.horizonScores, {});
  }

  function trendReturnFromRaw(raw, days) {
    for (const window of raw?.technical_trend?.windows || []) {
      if (Number(window.days) === days) {
        return numberOrNull(window.return_pct);
      }
    }
    return null;
  }

  function scorePartsByModule(horizonInfo = {}) {
    const modules = {};
    for (const part of horizonInfo.parts || []) {
      const module = String(part.module || "").trim();
      const points = numberOrNull(part.points);
      if (!module || points == null) continue;
      modules[module] = (modules[module] || 0) + points;
    }
    return modules;
  }

  function topScoreParts(horizonInfo = {}, limit = 3) {
    return (horizonInfo.parts || [])
      .map((part) => ({
        module: String(part.module || "").trim(),
        points: numberOrNull(part.points),
        reason: String(part.reason || ""),
      }))
      .filter((part) => part.module && part.points != null)
      .sort((left, right) => Math.abs(right.points) - Math.abs(left.points))
      .slice(0, limit)
      .map((part) => ({
        ...part,
        points: Number(part.points.toFixed(2)),
      }));
  }

  function formatKeyParts(parts = []) {
    if (!parts.length) return "暂无";
    return parts.map((part) => `${part.module} ${formatSignedNumber(part.points, 2)} 分`).join("；");
  }

  function buildPartComparisons(previousHorizon = {}, currentHorizon = {}, limit = 3) {
    const previousParts = scorePartsByModule(previousHorizon);
    const currentParts = scorePartsByModule(currentHorizon);
    const modules = new Set([...Object.keys(previousParts), ...Object.keys(currentParts)]);
    return [...modules]
      .map((module) => {
        const previousPoints = previousParts[module] || 0;
        const currentPoints = currentParts[module] || 0;
        const deltaPoints = currentPoints - previousPoints;
        return {
          module,
          previousPoints: Number(previousPoints.toFixed(2)),
          currentPoints: Number(currentPoints.toFixed(2)),
          deltaPoints: Number(deltaPoints.toFixed(2)),
        };
      })
      .filter((item) => Math.abs(item.deltaPoints) >= 2)
      .sort((left, right) => Math.abs(right.deltaPoints) - Math.abs(left.deltaPoints))
      .slice(0, limit);
  }

  function buildTrendComparisons(result, previousRow, daysList) {
    const currentRaw = result.raw || {};
    const previousRaw = rawAnalysisFromRow(previousRow);
    const comparisons = [];
    for (const days of daysList) {
      const previousReturn = trendReturnFromRaw(previousRaw, days);
      const currentReturn = trendReturnFromRaw(currentRaw, days);
      if (previousReturn == null || currentReturn == null) continue;
      comparisons.push({
        days,
        previousReturnPct: Number(previousReturn.toFixed(2)),
        currentReturnPct: Number(currentReturn.toFixed(2)),
        deltaPct: Number((currentReturn - previousReturn).toFixed(2)),
      });
    }
    return comparisons;
  }

  function matchingStabilityAdjustment(result, horizon) {
    return (result.stability_adjustments || []).find((adjustment) => String(adjustment.horizon || "") === horizon) || null;
  }

  function buildHistoryExplanations(label, scoreSummary, trendComparisons, partComparisons, stabilityAdjustment) {
    const explanations = [];
    const delta = numberOrNull(scoreSummary.deltaFromPrevious);
    if (delta != null && Math.abs(delta) >= 10) {
      explanations.push(`${label}较上一期${scoreChangeWord(delta)} ${Math.abs(delta).toFixed(0)} 分，需要结合历史证据复核。`);
    }
    let trendExplanationCount = 0;
    for (const comparison of trendComparisons) {
      const trendDelta = numberOrNull(comparison.deltaPct);
      if (trendDelta == null || Math.abs(trendDelta) < 3) continue;
      const direction = trendDelta > 0 ? "改善" : "走弱";
      explanations.push(
        `近 ${comparison.days} 日收益从 ${formatPercent(comparison.previousReturnPct)} 变为 ${formatPercent(comparison.currentReturnPct)}，${direction} ${Math.abs(trendDelta).toFixed(2)} 个百分点。`,
      );
      trendExplanationCount += 1;
      if (trendExplanationCount >= 2) break;
    }
    if (stabilityAdjustment) {
      explanations.push(
        `稳定器参考上一期 ${stabilityAdjustment.previousScore}/100，将原始 ${stabilityAdjustment.rawScore}/100 调整为 ${stabilityAdjustment.stabilizedScore}/100。`,
      );
    }
    for (const comparison of partComparisons) {
      explanations.push(
        `评分项「${comparison.module}」从 ${formatSignedNumber(comparison.previousPoints, 2)} 分变为 ${formatSignedNumber(comparison.currentPoints, 2)} 分，变化 ${formatSignedNumber(comparison.deltaPoints, 2)} 分。`,
      );
    }
    if (!explanations.length) {
      explanations.push(`${label}历史分数和核心证据变化有限，当前判断主要延续上一期。`);
    }
    return explanations.slice(0, 4);
  }

  function buildHistoricalScoreContext(result, historicalRows = []) {
    const rows = historicalRows
      .filter((row) => tradeDateFromRow(row))
      .sort((left, right) => tradeDateFromRow(left).localeCompare(tradeDateFromRow(right)));
    if (!rows.length) return {};
    const previousRow = rows.at(-1);
    const previousHorizons = horizonScoresFromRow(previousRow);
    const horizons = {};
    for (const [horizon, label, field, daysList] of HISTORY_SCORE_HORIZONS) {
      const values = rows.map((row) => intOrNull(row[field])).filter((value) => value != null);
      const currentScore = resultScoreForHorizon(result, horizon);
      const previousScore = intOrNull(previousRow[field]);
      if (currentScore == null || previousScore == null) continue;
      const recentAverage = values.length ? Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1)) : null;
      const scoreSummary = {
        label,
        currentScore,
        previousScore,
        deltaFromPrevious: currentScore - previousScore,
        recentAverage,
        recentMin: values.length ? Math.min(...values) : null,
        recentMax: values.length ? Math.max(...values) : null,
        deltaFromAverage: recentAverage == null ? null : Number((currentScore - recentAverage).toFixed(1)),
        currentSignal: signalLabelFromScore(currentScore),
        previousSignal: signalLabelFromScore(previousScore),
      };
      if (horizon !== "overall") {
        const currentHorizon = result.horizon_scores?.[horizon] || {};
        const previousHorizon = previousHorizons[horizon] || {};
        const trendComparisons = buildTrendComparisons(result, previousRow, daysList);
        const partComparisons = buildPartComparisons(previousHorizon, currentHorizon);
        scoreSummary.trendComparisons = trendComparisons;
        scoreSummary.partComparisons = partComparisons;
        scoreSummary.previousKeyParts = topScoreParts(previousHorizon);
        scoreSummary.currentKeyParts = topScoreParts(currentHorizon);
        scoreSummary.explanations = buildHistoryExplanations(
          label,
          scoreSummary,
          trendComparisons,
          partComparisons,
          matchingStabilityAdjustment(result, horizon),
        );
      }
      horizons[horizon] = scoreSummary;
    }
    return {
      lookbackCount: rows.length,
      previousTradeDate: tradeDateFromRow(previousRow),
      horizons,
    };
  }

  function applyHistoricalScoreContext(results, historicalScoresByCode = {}) {
    for (const result of results) {
      const context = buildHistoricalScoreContext(result, historicalScoresByCode[String(result.code || "")] || []);
      if (Object.keys(context).length) {
        result.historical_score_context = context;
      }
    }
    return results;
  }

  function historicalScoreContextLines(context = {}) {
    const horizons = context.horizons || {};
    if (!Object.keys(horizons).length) return [];
    const lookback = context.lookbackCount;
    const lines = [`- 对比窗口：最近 ${lookback} 次历史评分；上一期：${context.previousTradeDate || "暂无"}。`];
    for (const key of ["overall", "medium_term", "long_term"]) {
      const item = horizons[key];
      if (!item) continue;
      const delta = numberOrNull(item.deltaFromPrevious);
      const deltaPhrase = delta == null ? "暂无" : `${scoreChangeWord(delta)} ${Math.abs(delta).toFixed(0)} 分`;
      lines.push(
        `- ${item.label || key}：当前 ${item.currentScore}/100；上一期 ${item.previousScore}/100（${deltaPhrase}）；近 ${lookback} 次均值 ${formatDecimal(item.recentAverage, 1)}，区间 ${item.recentMin}~${item.recentMax}。`,
      );
      if (key === "medium_term" || key === "long_term") {
        lines.push(
          `- ${item.label || key}评分项：上一期 ${formatKeyParts(item.previousKeyParts || [])}；本期 ${formatKeyParts(item.currentKeyParts || [])}。`,
        );
        for (const explanation of item.explanations || []) {
          lines.push(`- ${item.label || key}依据：${explanation}`);
        }
      }
    }
    return lines;
  }

  function scoreSide(score) {
    const numeric = numberOrNull(score);
    if (numeric == null) return "unknown";
    if (numeric >= 15) return "buy";
    if (numeric <= -15) return "sell";
    return "watch";
  }

  function horizonAdvice(horizon, score, regime = "mixed") {
    if (horizon === "short_term") {
      if (score >= 50) return "短期动能和环境配合，可考虑顺势但需要严格止损。";
      if (score >= 15) return "短期有买入偏向，更适合小仓位试探或等待放量确认。";
      if (score > -15) return "短期信号不够一致，等待突破、回踩或动能修复。";
      return "短期风险偏高，先回避追涨或降低仓位。";
    }
    if (horizon === "medium_term") {
      if (score >= 50) return "中期趋势和质量配合，适合分批配置并跟踪关键均线。";
      if (score >= 15) return "中期偏正向，可分批跟踪，等待趋势继续确认。";
      if (score > -15) return "中期证据混合，观察 20/60/120 日趋势是否重新同向。";
      return "中期偏弱，除非重新站回关键均线并改善量价结构。";
    }
    if (score >= 50) return "长期质量和趋势较强，适合纳入长期观察或分批配置池。";
    if (score >= 15) return "长期有正向基础，但仍要结合估值、安全边际和仓位管理。";
    if (score > -15) return "长期吸引力不足，等待基本面或长期趋势给出更清晰证据。";
    if (regime === "downtrend") return "长期趋势偏弱，优先等待长期结构修复。";
    return "长期风险收益不占优，暂不适合提高配置权重。";
  }

  function horizonScore(result, key) {
    return numberOrNull(result?.horizon_scores?.[key]?.score) ?? 0;
  }

  function trendWindowReturn(result, days) {
    for (const window of result?.raw?.technical_trend?.windows || []) {
      if (Number(window.days) === days) {
        return numberOrNull(window.return_pct);
      }
    }
    return null;
  }

  function dampScoreChange(previousScore, currentScore, maxDelta) {
    const previous = intOrNull(previousScore);
    const current = intOrNull(currentScore);
    if (previous == null || current == null) return current;
    const delta = current - previous;
    if (Math.abs(delta) <= maxDelta) return current;
    return previous + (delta > 0 ? maxDelta : -maxDelta);
  }

  function stabilityBreakDetected(result, horizon) {
    if (result.confidence === "低" || (result.source_errors || []).length > 0) {
      return true;
    }
    if (horizon === "medium_term") {
      const r20 = trendWindowReturn(result, 20);
      const r60 = trendWindowReturn(result, 60);
      return (r20 != null && r20 <= -10) || (r60 != null && r60 <= -15) || horizonScore(result, "short_term") <= -50;
    }
    if (horizon === "long_term") {
      const r60 = trendWindowReturn(result, 60);
      const r120 = trendWindowReturn(result, 120);
      return (r60 != null && r60 <= -18) || (r120 != null && r120 <= -25);
    }
    return false;
  }

  function metricValues(item) {
    const values = {};
    for (const metric of item.metrics || []) {
      values[metric.label || ""] = numberOrNull(metric.value);
    }
    return values;
  }

  function marketFromCode(code) {
    if (String(code).startsWith("6")) return "SH";
    if (String(code).startsWith("4") || String(code).startsWith("8"))
      return "BJ";
    return "SZ";
  }

  function horizonValue(result, key, field) {
    return (result.horizon_scores?.[key] || {})[field];
  }

  function fallbackScoreConclusion(result) {
    if (result.score >= 50)
      return "强买入偏向，但仍应等待成交量和趋势继续确认。";
    if (result.score >= 15)
      return "买入偏向存在，更适合分批观察或等待技术面进一步确认。";
    if (result.score > -15)
      return "观望。当前多空证据接近均衡，不适合给出明确买入或卖出信号。";
    if (result.score > -50)
      return "卖出或回避偏向，短期风险证据强于机会证据。";
    return "强回避偏向，风险信号较集中。";
  }

  function horizonSignalPhrase(result, key, fallbackLabel) {
    const horizon = result.horizon_scores?.[key] || {};
    return `${horizon.label || fallbackLabel}${horizon.signal || "暂无"}`;
  }

  function reportConclusion(result) {
    const horizonKeys = [
      ["short_term", "短期"],
      ["medium_term", "中期"],
      ["long_term", "长期"],
    ];
    const hasAllHorizons = horizonKeys.every(
      ([key]) => result.horizon_scores?.[key],
    );
    if (!hasAllHorizons) {
      const conclusion = fallbackScoreConclusion(result);
      return { conclusion, conclusionDetail: conclusion };
    }

    const sides = Object.fromEntries(
      horizonKeys.map(([key]) => [key, scoreSide(horizonValue(result, key, "score"))]),
    );
    const detail = horizonKeys
      .map(([key, label]) => horizonSignalPhrase(result, key, label))
      .join("；");
    const strategyAdjustments = result.strategy_adjustments || [];
    const sourceErrors = result.source_errors || [];

    let base;
    if (horizonKeys.every(([key]) => sides[key] === "buy")) {
      base = "三周期一致偏多，买入偏向质量较高。";
    } else if (horizonKeys.every(([key]) => sides[key] === "sell")) {
      base = "三周期一致偏空，优先回避或降低风险暴露。";
    } else if (horizonKeys.every(([key]) => sides[key] === "watch")) {
      base = "三周期均偏观察，等待趋势或基本面给出更清晰证据。";
    } else if (sides.medium_term === "buy" && sides.long_term === "buy") {
      base =
        sides.short_term === "sell"
          ? "中长期偏多但短期风险未解除，优先等待短期修复确认。"
          : "中长期偏多，适合分批观察并等待短期择时确认。";
    } else if (
      sides.short_term === "buy" &&
      sides.medium_term !== "buy" &&
      sides.long_term !== "buy"
    ) {
      base = "短期偏多但中长期支撑不足，只适合交易性观察。";
    } else if (new Set(Object.values(sides)).size > 1) {
      base = "周期证据分歧，优先观察确认。";
    } else {
      base = fallbackScoreConclusion(result);
    }

    if (result.confidence === "低" || sourceErrors.length) {
      base = "数据置信度不足，优先观察复核。";
    } else if (strategyAdjustments.length) {
      base = `${base.replace(/。$/, "")}，且已应用复盘校准。`;
    }

    return {
      conclusion: base,
      conclusionDetail: `${base}（${detail}；总分 ${result.score}/100，${result.signal}）`,
    };
  }

  async function upsert(
    connection,
    table,
    row,
    updateColumns = Object.keys(row),
  ) {
    const columns = Object.keys(row);
    const placeholders = columns.map(() => "?").join(", ");
    const updates = updateColumns
      .map((column) => `${column}=VALUES(${column})`)
      .join(", ");
    const params = columns.map((column) =>
      row[column] === undefined ? null : row[column],
    );
    await connection.query(
      `INSERT INTO ${table} (${columns.join(", ")}) VALUES (${placeholders}) ON DUPLICATE KEY UPDATE ${updates}`,
      params,
    );
  }

  async function persistSecurity(connection, item) {
    const code = String(item.code);
    const overview = item.overview || {};
    await upsert(
      connection,
      "stock_security",
      {
        stock_code: code,
        market: marketFromCode(code),
        symbol: `${marketFromCode(code)}${code}`,
        name: item.name || null,
        industry: item.industry || null,
        listed_date: item.listed_at || null,
        total_shares: numberOrNull(overview["总股本"]),
        float_shares: numberOrNull(overview["流通股"]),
      },
      [
        "market",
        "symbol",
        "name",
        "industry",
        "listed_date",
        "total_shares",
        "float_shares",
      ],
    );
  }

  async function persistQuote(connection, item, adjustType) {
    const technical = item.technical || {};
    const volumeLots = numberOrNull(technical.latest_volume);
    await upsert(
      connection,
      "stock_daily_quote",
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
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_shares",
        "volume_lots",
        "amount",
        "turnover_rate",
        "raw_json",
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
      "stock_daily_technical",
      row,
      Object.keys(row).filter(
        (column) =>
          !["stock_code", "trade_date", "adjust_type"].includes(column),
      ),
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
      eps: numberOrNull(metrics["每股收益"]),
      net_asset_per_share: numberOrNull(metrics["每股净资产"]),
      operating_cash_per_share: numberOrNull(metrics["每股经营现金流"]),
      roe: numberOrNull(metrics.ROE),
      gross_margin: numberOrNull(metrics["毛利率"]),
      net_margin: numberOrNull(metrics["净利率"]),
      revenue_growth: numberOrNull(metrics["营收增长"]),
      net_profit_growth: numberOrNull(metrics["净利润增长"]),
      asset_growth: numberOrNull(metrics["总资产增长"]),
      debt_ratio: numberOrNull(metrics["资产负债率"]),
      current_ratio: numberOrNull(metrics["流动比率"]),
      quick_ratio: numberOrNull(metrics["速动比率"]),
      ocf_to_profit: numberOrNull(metrics["经营现金流/净利润"]),
      raw_json: jsonValue(item.metrics || []),
    };
    await upsert(
      connection,
      "stock_financial_report",
      row,
      Object.keys(row).filter(
        (column) => !["stock_code", "report_date"].includes(column),
      ),
    );
  }

  async function persistTrend(connection, item, adjustType) {
    const technical = item.technical || {};
    const trend = item.technical_trend || {};
    await upsert(
      connection,
      "stock_daily_trend",
      {
        stock_code: String(item.code),
        trade_date: technical.trade_date,
        adjust_type: adjustType,
        trend_rating: trend.rating || null,
        trend_score: intOrNull(trend.score),
        conclusion: trend.conclusion || null,
        signals_json: jsonValue(trend.signals || []),
      },
      ["trend_rating", "trend_score", "conclusion", "signals_json"],
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
        "stock_daily_trend_window",
        row,
        Object.keys(row).filter(
          (column) =>
            ![
              "stock_code",
              "trade_date",
              "adjust_type",
              "window_days",
            ].includes(column),
        ),
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
      short_term_score: intOrNull(horizonValue(result, "short_term", "score")),
      short_term_signal_label:
        horizonValue(result, "short_term", "signal") || null,
      medium_term_score: intOrNull(
        horizonValue(result, "medium_term", "score"),
      ),
      medium_term_signal_label:
        horizonValue(result, "medium_term", "signal") || null,
      long_term_score: intOrNull(horizonValue(result, "long_term", "score")),
      long_term_signal_label:
        horizonValue(result, "long_term", "signal") || null,
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
      "stock_daily_signal_score",
      row,
      Object.keys(row).filter(
        (column) =>
          !["stock_code", "trade_date", "adjust_type"].includes(column),
      ),
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
    const stockCode = String(result.code || item.code || "");
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
        "stock_signal_outcome",
        { ...spec, status: "pending" },
        ["signal_score", "signal_label", "signal_close", "raw_signal_json"],
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

  async function fetchEvaluationSummariesForResults(
    connection,
    results,
    adjustType,
  ) {
    const codes = [
      ...new Set(results.map((result) => String(result.code)).filter(Boolean)),
    ];
    if (!codes.length) {
      return {};
    }
    const placeholders = codes.map(() => "?").join(", ");
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
    return numeric == null ? "暂无" : numeric.toFixed(digits);
  }

  function formatPercent(value) {
    const numeric = numberOrNull(value);
    return numeric == null ? "暂无" : `${numeric.toFixed(2)}%`;
  }

  function formatEvaluationLines(summary) {
    const labels = {
      short_term: "短期",
      medium_term: "中期",
      long_term: "长期",
    };
    const windows = {
      short_term: [1, 3, 5],
      medium_term: [10, 20],
      long_term: [60, 120],
    };
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
    return lines.length ? lines : ["暂无已到期历史验证样本，先持续积累。"];
  }

  function generateFinalReport(result) {
    const item = result.raw || {};
    const code = String(result.code || item.code || "");
    const name = String(result.name || item.name || "");
    const technical = item.technical || {};
    const trend = item.technical_trend || {};
    const metrics = metricValues(item);
    const sourceErrors = result.source_errors || [];
    const tradeDate = technical.trade_date || "未知交易日";
    const displayName = [code, name].filter(Boolean).join(" ");
    const { conclusion, conclusionDetail } = reportConclusion(result);

    const rsi = technical.rsi || {};
    const macd = technical.macd || {};
    const boll = technical.boll || {};
    const strengths = item.strengths || ["暂无明确优势"];
    const risks = item.risks || ["暂无明确风险"];
    const stabilityAdjustments = result.stability_adjustments || [];
    const historicalContext = result.historical_score_context || {};
    const historicalLines = historicalScoreContextLines(historicalContext);
    const horizonLines = [
      ["short_term", "短期"],
      ["medium_term", "中期"],
      ["long_term", "长期"],
    ]
      .filter(
        ([key]) =>
          result.horizon_scores?.[key]?.score != null &&
          result.horizon_scores?.[key]?.signal,
      )
      .map(
        ([key, label]) =>
          `- ${label}评分：${result.horizon_scores[key].score}/100（${result.horizon_scores[key].signal}）`,
      );

    const lines = [
      `# ${displayName} 最终分析报告`,
      "",
      `- 交易日：${tradeDate}`,
      `- 评分：${result.score}/100`,
      `- 信号：${result.signal}`,
      `- 置信度：${result.confidence}`,
      `- 市场状态：${result.regime}`,
      ...horizonLines,
      "",
      "## 结论",
      "",
      conclusionDetail,
      "",
      "## 核心数据",
      "",
      `- 收盘价：${formatDecimal(technical.latest_close)}`,
      `- 成交量：${formatDecimal(technical.latest_volume)} 手`,
      `- 成交额：${formatDecimal(technical.latest_amount)} 元`,
      `- RSI：${formatDecimal(rsi.rsi6, 6)} / ${formatDecimal(rsi.rsi12, 6)} / ${formatDecimal(rsi.rsi24, 6)}`,
      `- MACD：DIF ${formatDecimal(macd.dif, 6)} / DEA ${formatDecimal(macd.dea, 6)} / 柱 ${formatDecimal(macd.bar, 6)}`,
      `- BOLL：${boll.position || "暂无"}`,
      `- 趋势评级：${trend.rating || "暂无"}，趋势评分 ${trend.score ?? "暂无"}`,
      `- 财报期：${item.report_date || "暂无"}，ROE ${formatPercent(metrics.ROE)}，经营现金流/净利润 ${formatDecimal(metrics["经营现金流/净利润"])} 倍`,
      "",
      "## 分析",
      "",
      `基本面优势：${strengths.map(String).join("；")}。`,
      `主要风险：${risks.map(String).join("；")}。`,
      "",
      `技术趋势：${trend.conclusion || "暂无明确趋势结论"}`,
      `短线择时：${result.advice}`,
      "",
      "## 历史验证",
      "",
      ...formatEvaluationLines(result.evaluation_summary),
    ];
    if (historicalLines.length) {
      lines.push("", "## 历史分数对照", "", ...historicalLines);
    }
    lines.push("", "## 操作建议", "", result.advice);
    if (sourceErrors.length) {
      lines.push("", "## 数据提醒", "", ...sourceErrors.map(String));
    }
    if (stabilityAdjustments.length) {
      lines.push(
        "",
        "## 评分稳定性",
        "",
        ...stabilityAdjustments.map(
          (adjustment) =>
            `- ${adjustment.horizon}：上一期 ${adjustment.previousScore}，原始 ${adjustment.rawScore}，稳定后 ${adjustment.stabilizedScore}。`,
        ),
      );
    }
    const reportText = `${lines.join("\n").trimEnd()}\n`;
    const reportJson = {
      score: result.score,
      signal: result.signal,
      confidence: result.confidence,
      conclusion,
      regime: result.regime,
      advice: result.advice,
      horizon_scores: result.horizon_scores || {},
      strengths,
      risks,
      source_errors: sourceErrors,
      stability_adjustments: stabilityAdjustments,
      evaluation_summary: result.evaluation_summary || emptyEvaluationSummary(),
    };
    if (Object.keys(historicalContext).length) {
      reportJson.historical_score_context = historicalContext;
    }
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
      "stock_daily_report",
      {
        stock_code: String(result.code),
        trade_date: technical.trade_date,
        adjust_type: adjustType,
        report_type: "final_summary",
        report_title: report.title,
        report_text: report.text,
        report_format: "markdown",
        report_json: jsonValue(report.json),
      },
      ["report_title", "report_text", "report_format", "report_json"],
    );
  }

  async function persistAiEtf(connection, aiEtf, adjustType) {
    if (!aiEtf) {
      return null;
    }
    const portfolioName = aiEtf.portfolioName || "AI_RECOMMENDED_ETF";
    const tradeDate = aiEtf.tradeDate;
    if (!tradeDate) {
      const error = new Error("aiEtf.tradeDate 不能为空");
      error.statusCode = 400;
      throw error;
    }
    validateTradeDate(tradeDate);
    const effectiveAdjustType = aiEtf.adjustType || adjustType;
    await upsert(
      connection,
      "stock_ai_etf_snapshot",
      {
        portfolio_name: portfolioName,
        trade_date: tradeDate,
        adjust_type: effectiveAdjustType,
        selection_rule: aiEtf.selectionRule || null,
        nav: numberOrNull(aiEtf.nav),
        daily_return_pct: numberOrNull(aiEtf.dailyReturnPct),
        cumulative_return_pct: numberOrNull(aiEtf.cumulativeReturnPct),
        realized_pnl: numberOrNull(aiEtf.realizedPnl),
        unrealized_pnl: numberOrNull(aiEtf.unrealizedPnl),
        total_pnl: numberOrNull(aiEtf.totalPnl),
        turnover_pct: numberOrNull(aiEtf.turnoverPct),
        holding_count: intOrNull(aiEtf.holdingCount ?? aiEtf.holdings?.filter((item) => Number(item.targetWeightPct) > 0).length ?? 0),
        summary_json: jsonValue(aiEtf.summary || {}),
      },
      [
        "selection_rule",
        "nav",
        "daily_return_pct",
        "cumulative_return_pct",
        "realized_pnl",
        "unrealized_pnl",
        "total_pnl",
        "turnover_pct",
        "holding_count",
        "summary_json",
      ],
    );

    for (const holding of aiEtf.holdings || []) {
      await upsert(
        connection,
        "stock_ai_etf_holding",
        {
          portfolio_name: portfolioName,
          trade_date: tradeDate,
          adjust_type: effectiveAdjustType,
          stock_code: String(holding.stockCode),
          stock_name: holding.stockName || null,
          industry: holding.industry || null,
          previous_weight_pct: numberOrNull(holding.previousWeightPct),
          target_weight_pct: numberOrNull(holding.targetWeightPct),
          weight_delta_pct: numberOrNull(holding.weightDeltaPct),
          action: holding.action || "hold",
          reference_price: numberOrNull(holding.referencePrice),
          simulated_quantity: numberOrNull(holding.simulatedQuantity),
          simulated_notional: numberOrNull(holding.simulatedNotional),
          score: intOrNull(holding.score),
          signal_label: holding.signalLabel || null,
          short_term_score: intOrNull(holding.shortTermScore),
          short_term_signal_label: holding.shortTermSignalLabel || null,
          medium_term_score: intOrNull(holding.mediumTermScore),
          medium_term_signal_label: holding.mediumTermSignalLabel || null,
          long_term_score: intOrNull(holding.longTermScore),
          long_term_signal_label: holding.longTermSignalLabel || null,
          confidence: holding.confidence || null,
          rationale: holding.rationale || null,
          risks_json: jsonValue(holding.risks || []),
          raw_json: jsonValue(holding),
        },
        [
          "stock_name",
          "industry",
          "previous_weight_pct",
          "target_weight_pct",
          "weight_delta_pct",
          "action",
          "reference_price",
          "simulated_quantity",
          "simulated_notional",
          "score",
          "signal_label",
          "short_term_score",
          "short_term_signal_label",
          "medium_term_score",
          "medium_term_signal_label",
          "long_term_score",
          "long_term_signal_label",
          "confidence",
          "rationale",
          "risks_json",
          "raw_json",
        ],
      );
    }

    for (const trade of aiEtf.rebalance || []) {
      await upsert(
        connection,
        "stock_ai_etf_trade",
        {
          portfolio_name: portfolioName,
          trade_date: tradeDate,
          adjust_type: effectiveAdjustType,
          stock_code: String(trade.stockCode),
          stock_name: trade.stockName || null,
          action: trade.action || "hold",
          previous_weight_pct: numberOrNull(trade.previousWeightPct),
          target_weight_pct: numberOrNull(trade.targetWeightPct),
          weight_delta_pct: numberOrNull(trade.weightDeltaPct),
          reference_price: numberOrNull(trade.referencePrice),
          simulated_quantity_delta: numberOrNull(trade.simulatedQuantityDelta),
          simulated_notional_delta: numberOrNull(trade.simulatedNotionalDelta),
          realized_pnl: numberOrNull(trade.realizedPnl),
          realized_return_pct: numberOrNull(trade.realizedReturnPct),
          reason: trade.reason || null,
          raw_json: jsonValue(trade),
        },
        [
          "stock_name",
          "previous_weight_pct",
          "target_weight_pct",
          "weight_delta_pct",
          "reference_price",
          "simulated_quantity_delta",
          "simulated_notional_delta",
          "realized_pnl",
          "realized_return_pct",
          "reason",
          "raw_json",
        ],
      );
    }

    return {
      portfolioName,
      tradeDate,
      holdingCount: Number(aiEtf.holdingCount || aiEtf.holdings?.filter((item) => Number(item.targetWeightPct) > 0).length || 0),
    };
  }

  async function fetchLatestSignalTradeDate(connection, adjustType) {
    const [rows] = await connection.query(
      `
      SELECT DATE_FORMAT(MAX(trade_date), '%Y-%m-%d') AS tradeDate
      FROM stock_daily_signal_score
      WHERE adjust_type = ?
      `,
      [adjustType],
    );
    return rows[0]?.tradeDate || null;
  }

  async function fetchAiEtfCandidateResults(connection, adjustType, tradeDate = null) {
    const effectiveTradeDate = tradeDate || (await fetchLatestSignalTradeDate(connection, adjustType));
    if (!effectiveTradeDate) return [];
    const [rows] = await connection.query(
      `
      SELECT
        stock_code AS code,
        score,
        signal_label AS signal,
        confidence,
        regime,
        advice,
        horizon_scores_json,
        score_parts_json,
        source_errors_json,
        raw_analysis_json
      FROM stock_daily_signal_score
      WHERE adjust_type = ?
        AND trade_date = ?
      ORDER BY stock_code
      `,
      [adjustType, effectiveTradeDate],
    );
    return rows.map((row) => {
      const raw = parseJson(row.raw_analysis_json, {});
      return {
        code: String(row.code),
        name: raw.name || "",
        score: intOrNull(row.score),
        signal: row.signal,
        confidence: row.confidence,
        regime: row.regime,
        advice: row.advice,
        horizon_scores: parseJson(row.horizon_scores_json, {}),
        parts: parseJson(row.score_parts_json, []),
        source_errors: parseJson(row.source_errors_json, []),
        raw,
      };
    });
  }

  async function persistIngestResults(connection, results, adjustType, aiEtf = null, buildAiEtf = false) {
    const incomingTradeDates = results.map(resultTradeDate).filter(Boolean).sort();
    const latestIncomingTradeDate = incomingTradeDates.at(-1) || null;
    if (results.length) {
      for (const [tradeDate, dateResults] of Object.entries(groupResultsByTradeDate(results))) {
        const previousScores = await fetchLatestSignalScoresBefore(connection, tradeDate, adjustType);
        applyScoreStability(dateResults, previousScores);
        const historicalScores = await fetchHistoricalSignalScoresBefore(
          connection,
          dateResults.map((result) => result.code),
          tradeDate,
          adjustType,
        );
        applyHistoricalScoreContext(dateResults, historicalScores);
      }
    }
    const persistedCodes = [];
    for (const result of results) {
      const item = result.raw || {};
      const technical = item.technical || {};
      if (!technical.trade_date) {
        const error = new Error(
          `${item.code || result.code || "未知股票"} 缺少技术面交易日，无法写入每日数据表`,
        );
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
    if (results.length) {
      await upsert(
        connection,
        "stock_data_ingest_run",
        {
          run_finished_at: new Date(),
          status: "success",
          stock_codes_json: jsonValue(persistedCodes),
          message: `已通过接口写入 ${persistedCodes.length} 只股票的每日分析数据`,
        },
        ["run_finished_at", "status", "stock_codes_json", "message"],
      );
      await refreshSignalOutcomes(connection);
      const summaries = await fetchEvaluationSummariesForResults(
        connection,
        results,
        adjustType,
      );
      for (const result of results) {
        result.evaluation_summary =
          summaries[String(result.code)] || emptyEvaluationSummary();
        await persistReport(connection, result, adjustType);
      }
    }
    if (aiEtf) {
      return persistAiEtf(connection, aiEtf, adjustType);
    }
    if (buildAiEtf) {
      const tradeDate = latestIncomingTradeDate || (await fetchLatestSignalTradeDate(connection, adjustType));
      const candidateResults = results.length ? results : await fetchAiEtfCandidateResults(connection, adjustType, tradeDate);
      const previousHoldings = await fetchLatestAiEtfHoldingsBefore(connection, tradeDate, adjustType);
      const portfolio = buildAiEtfPortfolio(candidateResults, adjustType, previousHoldings);
      return persistAiEtf(connection, portfolio, adjustType);
    }
    return null;
  }

  app.get("/api/health", asyncHandler(async (_req, res) => {
    const [rows] = await pool.query("SELECT 1 AS ok");
    res.json({
      ok: rows[0]?.ok === 1,
      database: process.env.MYSQL_DATABASE || "stock_analysis_test",
    });
  }));

  app.get("/api/dates", asyncHandler(async (_req, res) => {
    const dates = await loadDateSummaries();
    res.json({ dates });
  }));

  app.get("/api/ai-etf/dates", asyncHandler(async (_req, res) => {
    const [rows] = await pool.query(`
      SELECT
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        portfolio_name AS portfolioName,
        adjust_type AS adjustType,
        holding_count AS holdingCount,
        turnover_pct AS turnoverPct,
        total_pnl AS totalPnl,
        DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updatedAt
      FROM stock_ai_etf_snapshot
      ORDER BY trade_date DESC, updated_at DESC
    `);
    res.json({
      dates: rows.map((row) => ({
        tradeDate: row.tradeDate,
        portfolioName: row.portfolioName,
        adjustType: row.adjustType,
        holdingCount: Number(row.holdingCount || 0),
        turnoverPct: toNumber(row.turnoverPct),
        totalPnl: toNumber(row.totalPnl),
        updatedAt: row.updatedAt,
      })),
    });
  }));

  app.get("/api/ai-etf", asyncHandler(async (req, res) => {
    const tradeDate = req.query.date
      ? validateTradeDate(String(req.query.date))
      : null;
    const snapshotParams = [];
    const snapshotWhere = tradeDate ? "WHERE trade_date = ?" : "";
    if (tradeDate) {
      snapshotParams.push(tradeDate);
    }
    const [snapshotRows] = await pool.query(
      `
      SELECT
        portfolio_name AS portfolioName,
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        adjust_type AS adjustType,
        selection_rule AS selectionRule,
        nav,
        daily_return_pct AS dailyReturnPct,
        cumulative_return_pct AS cumulativeReturnPct,
        realized_pnl AS realizedPnl,
        unrealized_pnl AS unrealizedPnl,
        total_pnl AS totalPnl,
        turnover_pct AS turnoverPct,
        holding_count AS holdingCount,
        summary_json,
        DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updatedAt
      FROM stock_ai_etf_snapshot
      ${snapshotWhere}
      ORDER BY trade_date DESC, updated_at DESC
      LIMIT 1
    `,
      snapshotParams,
    );
    if (!snapshotRows.length) {
      res.json({ snapshot: null, holdings: [], rebalance: [] });
      return;
    }
    const snapshot = mapAiEtfSnapshot(snapshotRows[0]);
    const commonParams = [snapshot.portfolioName, snapshot.tradeDate, snapshot.adjustType];
    const [holdingRows] = await pool.query(
      `
      SELECT
        portfolio_name AS portfolioName,
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        stock_code AS stockCode,
        stock_name AS stockName,
        industry,
        previous_weight_pct AS previousWeightPct,
        target_weight_pct AS targetWeightPct,
        weight_delta_pct AS weightDeltaPct,
        action,
        reference_price AS referencePrice,
        simulated_quantity AS simulatedQuantity,
        simulated_notional AS simulatedNotional,
        score,
        signal_label AS signalLabel,
        short_term_score AS shortTermScore,
        short_term_signal_label AS shortTermSignalLabel,
        medium_term_score AS mediumTermScore,
        medium_term_signal_label AS mediumTermSignalLabel,
        long_term_score AS longTermScore,
        long_term_signal_label AS longTermSignalLabel,
        confidence,
        rationale,
        risks_json
      FROM stock_ai_etf_holding
      WHERE portfolio_name = ?
        AND trade_date = ?
        AND adjust_type = ?
      ORDER BY target_weight_pct DESC, stock_code ASC
    `,
      commonParams,
    );
    const [tradeRows] = await pool.query(
      `
      SELECT
        portfolio_name AS portfolioName,
        DATE_FORMAT(trade_date, '%Y-%m-%d') AS tradeDate,
        stock_code AS stockCode,
        stock_name AS stockName,
        action,
        previous_weight_pct AS previousWeightPct,
        target_weight_pct AS targetWeightPct,
        weight_delta_pct AS weightDeltaPct,
        reference_price AS referencePrice,
        simulated_quantity_delta AS simulatedQuantityDelta,
        simulated_notional_delta AS simulatedNotionalDelta,
        realized_pnl AS realizedPnl,
        realized_return_pct AS realizedReturnPct,
        reason
      FROM stock_ai_etf_trade
      WHERE portfolio_name = ?
        AND trade_date = ?
        AND adjust_type = ?
      ORDER BY FIELD(action, 'buy', 'increase', 'reduce', 'sell', 'hold', 'watch'), stock_code ASC
    `,
      commonParams,
    );
    res.json({
      snapshot,
      holdings: holdingRows.map(mapAiEtfHolding),
      rebalance: tradeRows.map(mapAiEtfTrade),
    });
  }));

  app.get("/api/analysis", asyncHandler(async (req, res) => {
    const summaries = await loadDateSummaries();
    const tradeDate = req.query.date
      ? validateTradeDate(String(req.query.date))
      : summaries[0]?.tradeDate;

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
  }));

  app.get("/api/stocks/:code", asyncHandler(async (req, res) => {
    const stockCode = validateStockCode(req.params.code);
    const tradeDate = req.query.date
      ? validateTradeDate(String(req.query.date))
      : await latestTradeDate(stockCode);

    if (!tradeDate) {
      res.status(404).json({ error: "没有找到该股票的分析记录" });
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
      res.status(404).json({ error: "没有找到该日期的股票分析记录" });
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
      ORDER BY ${horizonOrderExpression("horizon")}, window_days ASC
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
  }));

  app.get("/api/stocks/:code/history", asyncHandler(async (req, res) => {
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
  }));

  app.post(
    "/api/ingest/daily-analysis",
    requireIngestAuth(ingestToken),
    asyncHandler(async (req, res) => {
      const adjustType = req.body?.adjustType || "qfq";
      const results = Array.isArray(req.body?.results)
        ? req.body.results
        : null;
      const aiEtf = req.body?.aiEtf || null;
      const buildAiEtf = Boolean(req.body?.buildAiEtf);
      if (!["none", "qfq", "hfq"].includes(adjustType)) {
        const error = new Error("adjustType 只支持 none/qfq/hfq");
        error.statusCode = 400;
        throw error;
      }
      if (!results) {
        const error = new Error("results 必须是数组");
        error.statusCode = 400;
        throw error;
      }
      const connection = await pool.getConnection();
      let aiEtfResult = null;
      try {
        await connection.beginTransaction();
        aiEtfResult = await persistIngestResults(connection, results, adjustType, aiEtf, buildAiEtf);
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
        aiEtf: aiEtfResult,
        items: results.map((result) => ({
          stockCode: String(result.code),
          tradeDate: result.raw?.technical?.trade_date || null,
          score: result.score,
          signal: result.signal,
          confidence: result.confidence,
        })),
      });
    }),
  );

  const distPath = path.join(projectRootPath, "docs/.vitepress/dist");
  if (fs.existsSync(distPath)) {
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.use((err, _req, res, _next) => {
    const statusCode = err.statusCode || 500;
    if (statusCode >= 500) {
      console.error(err);
    }
    res.status(statusCode).json({
      error: statusCode === 500 ? "服务端查询失败" : err.message,
      detail: process.env.NODE_ENV === "production" ? undefined : err.message,
    });
  });

  return app;
}

export function shouldStartServer(argv = process.argv, env = process.env) {
  return Boolean(env.pm_id || (argv[1] && import.meta.url === pathToFileURL(argv[1]).href));
}

if (shouldStartServer()) {
  const port = Number(process.env.PORT || process.env.STOCK_DASHBOARD_PORT || 8001);
  const app = createApp();
  app.listen(port, () => {
    console.log(`Stock analysis API listening on http://127.0.0.1:${port}`);
  });
}
