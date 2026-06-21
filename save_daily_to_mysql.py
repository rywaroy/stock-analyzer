#!/usr/bin/env python3
"""Fetch stock analysis results and persist the latest daily snapshot to MySQL."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import signal_accuracy
import stock_fundamental_analysis as sfa


PROJECT_ROOT = Path(__file__).resolve().parent
SCORER_PATH = PROJECT_ROOT / ".codex/skills/stock-buy-signal-analysis/scripts/analyze_stock.py"
DEFAULT_INGEST_API_TOKEN = "stock-analysis-ingest-2026-6f8c2d91b7a443e0"


def describe_exception(exc: Exception) -> str:
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def log_status(args: argparse.Namespace, message: str) -> None:
    if getattr(args, "quiet", False):
        return
    timestamp = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def int_number(value: Any) -> int | None:
    numeric = number(value)
    if numeric is None:
        return None
    return int(round(numeric))


def sql_number(value: Any) -> str:
    numeric = number(value)
    if numeric is None:
        return "NULL"
    return repr(numeric)


def sql_int(value: Any) -> str:
    numeric = int_number(value)
    if numeric is None:
        return "NULL"
    return str(numeric)


def sql_text(value: Any) -> str:
    if value is None:
        return "NULL"
    encoded = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
    return f"CAST(FROM_BASE64('{encoded}') AS CHAR CHARACTER SET utf8mb4)"


def sql_json(value: Any) -> str:
    if value is None:
        return "NULL"
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return sql_text(text)


def sql_date(value: Any) -> str:
    if not value:
        return "NULL"
    return sql_text(str(value))


def upsert_sql(table: str, values: dict[str, str], update_columns: list[str] | None = None) -> str:
    columns = list(values)
    update_columns = update_columns if update_columns is not None else columns
    update_clause = ", ".join(f"{column}=VALUES({column})" for column in update_columns)
    return (
        f"INSERT INTO {table} ({', '.join(columns)})\n"
        f"VALUES ({', '.join(values[column] for column in columns)})\n"
        f"ON DUPLICATE KEY UPDATE {update_clause};"
    )


def market_from_code(code: str) -> str:
    return sfa.market_symbol(code)[:2]


def metric_values(item: dict[str, Any]) -> dict[str, float | None]:
    return {metric.get("label", ""): number(metric.get("value")) for metric in item.get("metrics", [])}


def format_decimal(value: Any, digits: int = 4) -> str:
    numeric = number(value)
    if numeric is None:
        return "暂无"
    return f"{numeric:.{digits}f}"


def format_percent(value: Any) -> str:
    numeric = number(value)
    if numeric is None:
        return "暂无"
    return f"{numeric:.2f}%"


HORIZON_KEYS = [
    ("short_term", "短期"),
    ("medium_term", "中期"),
    ("long_term", "长期"),
]
AI_ETF_PORTFOLIO_NAME = "AI_RECOMMENDED_ETF"
AI_ETF_INITIAL_NOTIONAL = 1_000_000.0
AI_ETF_TARGET_COUNT = 10


def value_from_mapping(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row.get(key)
    return None


def horizon_scores(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("horizon_scores") or {}


def horizon_value(result: dict[str, Any], key: str, field: str) -> Any:
    return (horizon_scores(result).get(key) or {}).get(field)


def horizon_summary_lines(result: dict[str, Any]) -> list[str]:
    lines = []
    for key, label in HORIZON_KEYS:
        score = horizon_value(result, key, "score")
        signal = horizon_value(result, key, "signal")
        if score is not None and signal:
            lines.append(f"- {label}评分：{score}/100（{signal}）")
    return lines


def score_side(score: Any) -> str:
    numeric = number(score)
    if numeric is None:
        return "unknown"
    if numeric >= 15:
        return "buy"
    if numeric <= -15:
        return "sell"
    return "watch"


def horizon_signal_phrase(result: dict[str, Any], key: str, fallback_label: str) -> str:
    horizon = horizon_scores(result).get(key) or {}
    label = str(horizon.get("label") or fallback_label)
    signal = str(horizon.get("signal") or "暂无")
    return f"{label}{signal}"


def fallback_score_conclusion(result: dict[str, Any]) -> str:
    if result["score"] >= 50:
        return "强买入偏向，但仍应等待成交量和趋势继续确认。"
    if result["score"] >= 15:
        return "买入偏向存在，更适合分批观察或等待技术面进一步确认。"
    if result["score"] > -15:
        return "观望。当前多空证据接近均衡，不适合给出明确买入或卖出信号。"
    if result["score"] > -50:
        return "卖出或回避偏向，短期风险证据强于机会证据。"
    return "强回避偏向，风险信号较集中。"


def report_conclusion(result: dict[str, Any]) -> tuple[str, str]:
    horizons = horizon_scores(result)
    if not all(key in horizons for key, _ in HORIZON_KEYS):
        conclusion = fallback_score_conclusion(result)
        return conclusion, conclusion

    sides = {key: score_side(horizon_value(result, key, "score")) for key, _ in HORIZON_KEYS}
    detail = "；".join(horizon_signal_phrase(result, key, label) for key, label in HORIZON_KEYS)
    strategy_adjustments = result.get("strategy_adjustments") or []
    confidence = result.get("confidence")
    source_errors = result.get("source_errors") or []

    if all(side == "buy" for side in sides.values()):
        base = "三周期一致偏多，买入偏向质量较高。"
    elif all(side == "sell" for side in sides.values()):
        base = "三周期一致偏空，优先回避或降低风险暴露。"
    elif all(side == "watch" for side in sides.values()):
        base = "三周期均偏观察，等待趋势或基本面给出更清晰证据。"
    elif sides["medium_term"] == "buy" and sides["long_term"] == "buy":
        if sides["short_term"] == "sell":
            base = "中长期偏多但短期风险未解除，优先等待短期修复确认。"
        else:
            base = "中长期偏多，适合分批观察并等待短期择时确认。"
    elif sides["short_term"] == "buy" and sides["medium_term"] != "buy" and sides["long_term"] != "buy":
        base = "短期偏多但中长期支撑不足，只适合交易性观察。"
    elif len(set(sides.values())) > 1:
        base = "周期证据分歧，优先观察确认。"
    else:
        base = fallback_score_conclusion(result)

    if confidence == "低" or source_errors:
        base = "数据置信度不足，优先观察复核。"
    elif strategy_adjustments:
        base = f"{base.rstrip('。')}，且已应用复盘校准。"

    return base, f"{base}（{detail}；总分 {result['score']}/100，{result['signal']}）"


def evaluation_summary_lines(result: dict[str, Any]) -> list[str]:
    if "evaluation_summary" not in result:
        return []
    return signal_accuracy.format_summary_lines(result.get("evaluation_summary"))


def generate_final_report(result: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    item = result["raw"]
    code = str(result.get("code") or item.get("code") or "")
    name = str(result.get("name") or item.get("name") or "")
    technical = item.get("technical") or {}
    trend = item.get("technical_trend") or {}
    metrics = metric_values(item)
    source_errors = result.get("source_errors") or []
    trade_date = technical.get("trade_date") or "未知交易日"

    display_name = f"{code} {name}".strip()
    title = f"{display_name} {trade_date} 最终分析报告"
    conclusion, conclusion_detail = report_conclusion(result)

    rsi = technical.get("rsi") or {}
    macd = technical.get("macd") or {}
    boll = technical.get("boll") or {}
    strengths = item.get("strengths") or ["暂无明确优势"]
    risks = item.get("risks") or ["暂无明确风险"]
    accuracy_lines = evaluation_summary_lines(result)
    strategy_adjustments = result.get("strategy_adjustments") or []

    lines = [
        f"# {display_name} 最终分析报告",
        "",
        f"- 交易日：{trade_date}",
        f"- 评分：{result['score']}/100",
        f"- 信号：{result['signal']}",
        f"- 置信度：{result['confidence']}",
        f"- 市场状态：{result['regime']}",
        *horizon_summary_lines(result),
        "",
        "## 结论",
        "",
        conclusion_detail,
        "",
        "## 核心数据",
        "",
        f"- 收盘价：{format_decimal(technical.get('latest_close'))}",
        f"- 成交量：{format_decimal(technical.get('latest_volume'))} 手",
        f"- 成交额：{format_decimal(technical.get('latest_amount'))} 元",
        "- RSI："
        f"{format_decimal(rsi.get('rsi6'), 6)} / {format_decimal(rsi.get('rsi12'), 6)} / {format_decimal(rsi.get('rsi24'), 6)}",
        "- MACD："
        f"DIF {format_decimal(macd.get('dif'), 6)} / DEA {format_decimal(macd.get('dea'), 6)} / 柱 {format_decimal(macd.get('bar'), 6)}",
        f"- BOLL：{boll.get('position') or '暂无'}",
        f"- 趋势评级：{trend.get('rating') or '暂无'}，趋势评分 {trend.get('score', '暂无')}",
        "- 财报期："
        f"{item.get('report_date') or '暂无'}，ROE {format_percent(metrics.get('ROE'))}，"
        f"经营现金流/净利润 {format_decimal(metrics.get('经营现金流/净利润'))} 倍",
        "",
        "## 分析",
        "",
        f"基本面优势：{'；'.join(str(value) for value in strengths)}。",
        f"主要风险：{'；'.join(str(value) for value in risks)}。",
        "",
        f"技术趋势：{trend.get('conclusion') or '暂无明确趋势结论'}",
        f"短线择时：{result['advice']}",
    ]
    if accuracy_lines:
        lines.extend(["", "## 历史验证", ""])
        lines.extend(accuracy_lines)
    if strategy_adjustments:
        lines.extend(["", "## 复盘与自学习", ""])
        horizons = horizon_scores(result)
        for adjustment in strategy_adjustments:
            horizon_key = str(adjustment.get("horizon") or "unknown")
            horizon = str((horizons.get(horizon_key) or {}).get("label") or horizon_key)
            adjustment_id = str(adjustment.get("id") or "unknown")
            reason = str(adjustment.get("reason") or "暂无原因")
            lines.append(f"- {horizon}：{adjustment_id}，{reason}")
    lines.extend(["", "## 操作建议", "", result["advice"]])
    if source_errors:
        lines.extend(["", "## 数据提醒", ""])
        lines.extend(str(error) for error in source_errors)
    report_text = "\n".join(lines).rstrip() + "\n"
    report_json = {
        "score": result["score"],
        "signal": result["signal"],
        "confidence": result["confidence"],
        "conclusion": conclusion,
        "regime": result["regime"],
        "advice": result["advice"],
        "horizon_scores": horizon_scores(result),
        "strategy_adjustments": strategy_adjustments,
        "strengths": strengths,
        "risks": risks,
        "source_errors": source_errors,
    }
    if "evaluation_summary" in result:
        report_json["evaluation_summary"] = result.get("evaluation_summary")
    return title, report_text, report_json


def result_trade_date(result: dict[str, Any]) -> str:
    return str(((result.get("raw") or {}).get("technical") or {}).get("trade_date") or "")


def result_close_price(result: dict[str, Any]) -> float | None:
    return number(((result.get("raw") or {}).get("technical") or {}).get("latest_close"))


def ai_etf_horizon_score(result: dict[str, Any], key: str) -> float:
    score = number(horizon_value(result, key, "score"))
    return score if score is not None else 0.0


def ai_etf_rank_score(result: dict[str, Any]) -> float:
    score = number(result.get("score")) or 0.0
    confidence = result.get("confidence")
    source_errors = result.get("source_errors") or []
    penalty = 0.0
    if confidence == "低":
        penalty += 15.0
    if source_errors:
        penalty += min(20.0, len(source_errors) * 5.0)
    return (
        ai_etf_horizon_score(result, "short_term") * 0.20
        + ai_etf_horizon_score(result, "medium_term") * 0.35
        + ai_etf_horizon_score(result, "long_term") * 0.35
        + score * 0.10
        - penalty
    )


def previous_holding_by_code(previous_holdings: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    grouped = {}
    for row in previous_holdings or []:
        code = str(value_from_mapping(row, "stock_code", "stockCode") or "")
        if code:
            grouped[code] = row
    return grouped


def normalized_action(previous_weight: float, target_weight: float) -> str:
    delta = round(target_weight - previous_weight, 6)
    if previous_weight <= 0 and target_weight > 0:
        return "buy"
    if previous_weight > 0 and target_weight <= 0:
        return "sell"
    if delta > 0.01:
        return "increase"
    if delta < -0.01:
        return "reduce"
    return "hold"


def action_reason(action: str, result: dict[str, Any] | None = None) -> str:
    if action == "buy":
        return "新纳入组合，三周期综合评分进入前十。"
    if action == "sell":
        return "不再进入本期前十，按调仓参考价模拟卖出。"
    if action == "increase":
        return "继续保留且目标权重提高。"
    if action == "reduce":
        return "继续保留但目标权重下调。"
    if result:
        return "继续保留，评分和风险状态仍满足组合要求。"
    return "本期无仓位变化。"


def holding_rationale(result: dict[str, Any], action: str) -> str:
    name = result.get("name") or ((result.get("raw") or {}).get("name")) or result.get("code")
    return (
        f"{action_reason(action, result)} {name} 综合分 {result.get('score')}，"
        f"短期 {horizon_value(result, 'short_term', 'score')}，"
        f"中期 {horizon_value(result, 'medium_term', 'score')}，"
        f"长期 {horizon_value(result, 'long_term', 'score')}。"
    )


def round_weight(value: float) -> float:
    return round(value, 4)


def build_ai_etf_portfolio(
    results: list[dict[str, Any]],
    adjust_type: str,
    previous_holdings: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    candidates = [
        result
        for result in results
        if result_trade_date(result)
        and result_close_price(result) is not None
        and str(result.get("code") or "")
    ]
    if len(candidates) < AI_ETF_TARGET_COUNT:
        return None

    ranked = sorted(candidates, key=lambda item: (ai_etf_rank_score(item), number(item.get("score")) or 0), reverse=True)
    selected = ranked[:AI_ETF_TARGET_COUNT]
    trade_date = result_trade_date(selected[0])
    previous_by_code = previous_holding_by_code(previous_holdings)
    target_weight = round_weight(100.0 / AI_ETF_TARGET_COUNT)
    holdings = []
    rebalance = []
    total_unrealized = 0.0
    total_realized = 0.0
    turnover = 0.0

    for result in selected:
        code = str(result.get("code"))
        item = result.get("raw") or {}
        previous = previous_by_code.get(code, {})
        previous_weight = number(value_from_mapping(previous, "target_weight_pct", "targetWeightPct")) or 0.0
        reference_price = result_close_price(result)
        simulated_notional = AI_ETF_INITIAL_NOTIONAL * target_weight / 100.0
        simulated_quantity = simulated_notional / reference_price if reference_price else None
        previous_price = number(value_from_mapping(previous, "reference_price", "referencePrice"))
        previous_quantity = number(value_from_mapping(previous, "simulated_quantity", "simulatedQuantity")) or 0.0
        unrealized = (
            (reference_price - previous_price) * previous_quantity
            if reference_price is not None and previous_price is not None and previous_quantity
            else 0.0
        )
        total_unrealized += unrealized
        delta = round_weight(target_weight - previous_weight)
        action = normalized_action(previous_weight, target_weight)
        turnover += abs(delta)
        holding = {
            "portfolioName": AI_ETF_PORTFOLIO_NAME,
            "tradeDate": trade_date,
            "adjustType": adjust_type,
            "stockCode": code,
            "stockName": result.get("name") or item.get("name") or "",
            "industry": item.get("industry") or "",
            "previousWeightPct": round_weight(previous_weight),
            "targetWeightPct": target_weight,
            "weightDeltaPct": delta,
            "action": action,
            "referencePrice": reference_price,
            "simulatedQuantity": simulated_quantity,
            "simulatedNotional": simulated_notional,
            "score": int_number(result.get("score")),
            "signalLabel": result.get("signal"),
            "shortTermScore": int_number(horizon_value(result, "short_term", "score")),
            "shortTermSignalLabel": horizon_value(result, "short_term", "signal"),
            "mediumTermScore": int_number(horizon_value(result, "medium_term", "score")),
            "mediumTermSignalLabel": horizon_value(result, "medium_term", "signal"),
            "longTermScore": int_number(horizon_value(result, "long_term", "score")),
            "longTermSignalLabel": horizon_value(result, "long_term", "signal"),
            "confidence": result.get("confidence"),
            "rationale": holding_rationale(result, action),
            "risks": item.get("risks") or [],
            "rankScore": round(ai_etf_rank_score(result), 4),
        }
        holdings.append(holding)
        rebalance.append(
            {
                **{key: holding[key] for key in ["portfolioName", "tradeDate", "adjustType", "stockCode", "stockName", "action"]},
                "previousWeightPct": holding["previousWeightPct"],
                "targetWeightPct": holding["targetWeightPct"],
                "weightDeltaPct": holding["weightDeltaPct"],
                "referencePrice": reference_price,
                "simulatedQuantityDelta": simulated_quantity if action in {"buy", "increase"} else 0,
                "simulatedNotionalDelta": simulated_notional * (delta / target_weight) if target_weight else 0,
                "realizedPnl": 0.0,
                "realizedReturnPct": 0.0,
                "reason": action_reason(action, result),
            }
        )

    selected_codes = {holding["stockCode"] for holding in holdings}
    for code, previous in previous_by_code.items():
        if code in selected_codes:
            continue
        previous_weight = number(value_from_mapping(previous, "target_weight_pct", "targetWeightPct")) or 0.0
        if previous_weight <= 0:
            continue
        previous_price = number(value_from_mapping(previous, "reference_price", "referencePrice"))
        previous_quantity = number(value_from_mapping(previous, "simulated_quantity", "simulatedQuantity")) or 0.0
        reference_price = previous_price
        realized_pnl = 0.0
        total_realized += realized_pnl
        turnover += previous_weight
        stock_name = str(value_from_mapping(previous, "stock_name", "stockName") or "")
        sell_entry = {
            "portfolioName": AI_ETF_PORTFOLIO_NAME,
            "tradeDate": trade_date,
            "adjustType": adjust_type,
            "stockCode": code,
            "stockName": stock_name,
            "industry": value_from_mapping(previous, "industry") or "",
            "previousWeightPct": round_weight(previous_weight),
            "targetWeightPct": 0.0,
            "weightDeltaPct": round_weight(-previous_weight),
            "action": "sell",
            "referencePrice": reference_price,
            "simulatedQuantity": 0.0,
            "simulatedNotional": 0.0,
            "score": None,
            "signalLabel": None,
            "shortTermScore": None,
            "shortTermSignalLabel": None,
            "mediumTermScore": None,
            "mediumTermSignalLabel": None,
            "longTermScore": None,
            "longTermSignalLabel": None,
            "confidence": None,
            "rationale": action_reason("sell"),
            "risks": [],
            "rankScore": None,
        }
        rebalance.append(
            {
                "portfolioName": AI_ETF_PORTFOLIO_NAME,
                "tradeDate": trade_date,
                "adjustType": adjust_type,
                "stockCode": code,
                "stockName": stock_name,
                "action": "sell",
                "previousWeightPct": round_weight(previous_weight),
                "targetWeightPct": 0.0,
                "weightDeltaPct": round_weight(-previous_weight),
                "referencePrice": reference_price,
                "simulatedQuantityDelta": -previous_quantity,
                "simulatedNotionalDelta": -(AI_ETF_INITIAL_NOTIONAL * previous_weight / 100.0),
                "realizedPnl": realized_pnl,
                "realizedReturnPct": 0.0,
                "reason": action_reason("sell"),
            }
        )
        holdings.append(sell_entry)

    total_pnl = total_realized + total_unrealized
    has_previous = bool(previous_by_code)
    selection_rule = (
        "基于上一期组合和短期20%/中期35%/长期35%/总分10%的排序调仓。"
        if has_previous
        else "首次生成，按三周期综合评分选出10只股票，每只等权10%。"
    )
    return {
        "portfolioName": AI_ETF_PORTFOLIO_NAME,
        "tradeDate": trade_date,
        "adjustType": adjust_type,
        "selectionRule": selection_rule,
        "nav": AI_ETF_INITIAL_NOTIONAL + total_pnl,
        "dailyReturnPct": 0.0,
        "cumulativeReturnPct": (total_pnl / AI_ETF_INITIAL_NOTIONAL) * 100.0,
        "realizedPnl": total_realized,
        "unrealizedPnl": total_unrealized,
        "totalPnl": total_pnl,
        "turnoverPct": min(200.0, round_weight(turnover)),
        "holdingCount": len([holding for holding in holdings if holding["targetWeightPct"] > 0]),
        "holdings": holdings,
        "rebalance": rebalance,
        "summary": {
            "candidateCount": len(candidates),
            "selectedCount": AI_ETF_TARGET_COUNT,
            "hasPreviousPortfolio": has_previous,
        },
    }


def load_scorer() -> Any:
    spec = importlib.util.spec_from_file_location("stock_buy_signal_scorer", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载评分脚本：{SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_analysis_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("缺少依赖：请用 README 中的 uv 命令运行") from exc

    codes = getattr(args, "resolved_codes", None) or sfa.resolve_input_codes(args.codes, args.codes_file)
    code_names = getattr(args, "code_names", None)
    if code_names is None:
        code_names = {} if args.codes else sfa.load_code_names_from_file(args.codes_file)
    log_status(args, f"准备分析 {len(codes)} 只股票")
    as_of_date = getattr(args, "as_of_date", None)
    skip_eastmoney = getattr(args, "skip_eastmoney", False)
    if as_of_date:
        spot, spot_error = {}, "历史回填模式不使用实时行情/估值快照"
        log_status(args, f"历史模式：{as_of_date:%Y-%m-%d} 不使用实时行情/估值快照")
    else:
        source_label = "新浪实时行情降级源" if skip_eastmoney else "实时估值快照"
        log_status(args, f"开始获取{source_label}")
        spot, spot_error = sfa.fetch_spot_snapshot(ak, codes, skip_eastmoney=skip_eastmoney)
        if spot_error:
            log_status(args, f"数据源提醒：{spot_error}")
        else:
            log_status(args, f"实时估值快照完成：{len(spot)}/{len(codes)}")
    adjust = "" if args.adjust == "none" else args.adjust
    analyses = []
    total = len(codes)
    for index, code in enumerate(codes, start=1):
        log_status(args, f"[{index}/{total}] 开始分析 {code}")
        if skip_eastmoney:
            analysis = sfa.build_analysis(
                ak,
                code,
                args.start_year,
                spot,
                args.technical_days,
                adjust,
                as_of_date,
                skip_eastmoney=True,
            )
        else:
            analysis = sfa.build_analysis(ak, code, args.start_year, spot, args.technical_days, adjust, as_of_date)
        if not analysis.name:
            analysis.name = code_names.get(code, "")
        if spot_error:
            analysis.source_errors.append(spot_error)
        trade_date = analysis.technical.trade_date if analysis.technical else "未知交易日"
        error_count = len(analysis.source_errors)
        suffix = f"，source_errors={error_count}" if error_count else ""
        log_status(args, f"[{index}/{total}] 完成分析 {code} {trade_date}{suffix}")
        analyses.append(analysis)
    return sfa.analyses_to_jsonable(analyses)


def security_statement(item: dict[str, Any]) -> str:
    code = str(item["code"])
    overview = item.get("overview") or {}
    values = {
        "stock_code": sql_text(code),
        "market": sql_text(market_from_code(code)),
        "symbol": sql_text(sfa.market_symbol(code)),
        "name": sql_text(item.get("name") or None),
        "industry": sql_text(item.get("industry") or None),
        "listed_date": sql_date(item.get("listed_at") or None),
        "total_shares": sql_number(overview.get("总股本")),
        "float_shares": sql_number(overview.get("流通股")),
    }
    return upsert_sql(
        "stock_security",
        values,
        ["market", "symbol", "name", "industry", "listed_date", "total_shares", "float_shares"],
    )


def quote_statement(item: dict[str, Any], adjust_type: str) -> str:
    technical = item.get("technical") or {}
    code = str(item["code"])
    volume_lots = number(technical.get("latest_volume"))
    values = {
        "stock_code": sql_text(code),
        "trade_date": sql_date(technical["trade_date"]),
        "adjust_type": sql_text(adjust_type),
        "open_price": "NULL",
        "high_price": "NULL",
        "low_price": "NULL",
        "close_price": sql_number(technical.get("latest_close")),
        "volume_shares": sql_number(volume_lots * 100 if volume_lots is not None else None),
        "volume_lots": sql_number(volume_lots),
        "amount": sql_number(technical.get("latest_amount")),
        "turnover_rate": sql_number(technical.get("turnover_rate")),
        "raw_json": sql_json(technical),
    }
    return upsert_sql(
        "stock_daily_quote",
        values,
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
    )


def technical_statement(item: dict[str, Any], adjust_type: str) -> str:
    technical = item.get("technical") or {}
    macd = technical.get("macd") or {}
    boll = technical.get("boll") or {}
    kdj = technical.get("kdj") or {}
    rsi = technical.get("rsi") or {}
    values = {
        "stock_code": sql_text(item["code"]),
        "trade_date": sql_date(technical["trade_date"]),
        "adjust_type": sql_text(adjust_type),
        "avg_volume_5": sql_number(technical.get("avg_volume_5")),
        "avg_volume_20": sql_number(technical.get("avg_volume_20")),
        "volume_ratio_5": sql_number(technical.get("volume_ratio_5")),
        "volume_ratio_20": "NULL",
        "macd_dif": sql_number(macd.get("dif")),
        "macd_dea": sql_number(macd.get("dea")),
        "macd_bar": sql_number(macd.get("bar")),
        "boll_mid": sql_number(boll.get("mid")),
        "boll_upper": sql_number(boll.get("upper")),
        "boll_lower": sql_number(boll.get("lower")),
        "boll_position": sql_text(boll.get("position") or None),
        "kdj_k": sql_number(kdj.get("k")),
        "kdj_d": sql_number(kdj.get("d")),
        "kdj_j": sql_number(kdj.get("j")),
        "rsi6": sql_number(rsi.get("rsi6")),
        "rsi12": sql_number(rsi.get("rsi12")),
        "rsi24": sql_number(rsi.get("rsi24")),
    }
    return upsert_sql(
        "stock_daily_technical",
        values,
        [column for column in values if column not in {"stock_code", "trade_date", "adjust_type"}],
    )


def financial_statement(item: dict[str, Any]) -> str | None:
    if not item.get("report_date"):
        return None
    metrics = metric_values(item)
    values = {
        "stock_code": sql_text(item["code"]),
        "report_date": sql_date(item.get("report_date")),
        "eps": sql_number(metrics.get("每股收益")),
        "net_asset_per_share": sql_number(metrics.get("每股净资产")),
        "operating_cash_per_share": sql_number(metrics.get("每股经营现金流")),
        "roe": sql_number(metrics.get("ROE")),
        "gross_margin": sql_number(metrics.get("毛利率")),
        "net_margin": sql_number(metrics.get("净利率")),
        "revenue_growth": sql_number(metrics.get("营收增长")),
        "net_profit_growth": sql_number(metrics.get("净利润增长")),
        "asset_growth": sql_number(metrics.get("总资产增长")),
        "debt_ratio": sql_number(metrics.get("资产负债率")),
        "current_ratio": sql_number(metrics.get("流动比率")),
        "quick_ratio": sql_number(metrics.get("速动比率")),
        "ocf_to_profit": sql_number(metrics.get("经营现金流/净利润")),
        "raw_json": sql_json(item.get("metrics") or []),
    }
    return upsert_sql(
        "stock_financial_report",
        values,
        [column for column in values if column not in {"stock_code", "report_date"}],
    )


def trend_statement(item: dict[str, Any], adjust_type: str) -> str:
    technical = item.get("technical") or {}
    trend = item.get("technical_trend") or {}
    values = {
        "stock_code": sql_text(item["code"]),
        "trade_date": sql_date(technical["trade_date"]),
        "adjust_type": sql_text(adjust_type),
        "trend_rating": sql_text(trend.get("rating") or None),
        "trend_score": sql_int(trend.get("score")),
        "conclusion": sql_text(trend.get("conclusion") or None),
        "signals_json": sql_json(trend.get("signals") or []),
    }
    return upsert_sql(
        "stock_daily_trend",
        values,
        ["trend_rating", "trend_score", "conclusion", "signals_json"],
    )


def trend_window_statements(item: dict[str, Any], adjust_type: str) -> list[str]:
    technical = item.get("technical") or {}
    trend = item.get("technical_trend") or {}
    statements = []
    for window in trend.get("windows") or []:
        values = {
            "stock_code": sql_text(item["code"]),
            "trade_date": sql_date(technical["trade_date"]),
            "adjust_type": sql_text(adjust_type),
            "window_days": sql_int(window.get("days")),
            "return_pct": sql_number(window.get("return_pct")),
            "close_vs_ma_pct": sql_number(window.get("close_vs_ma_pct")),
            "macd_positive_ratio": sql_number(window.get("macd_positive_ratio")),
            "boll_mid_above_ratio": sql_number(window.get("boll_mid_above_ratio")),
            "rsi24": sql_number(window.get("rsi24")),
            "volume_ratio_20": sql_number(window.get("volume_ratio_20")),
        }
        statements.append(
            upsert_sql(
                "stock_daily_trend_window",
                values,
                [column for column in values if column not in {"stock_code", "trade_date", "adjust_type", "window_days"}],
            )
        )
    return statements


def signal_outcome_statement(spec: dict[str, Any], result: dict[str, Any]) -> str:
    raw_signal = {
        "score": result.get("score"),
        "signal": result.get("signal"),
        "confidence": result.get("confidence"),
        "regime": result.get("regime"),
        "horizon": spec.get("horizon"),
        "horizon_score": (result.get("horizon_scores") or {}).get(spec.get("horizon")),
    }
    values = {
        "stock_code": sql_text(spec["stock_code"]),
        "signal_trade_date": sql_date(spec["signal_trade_date"]),
        "adjust_type": sql_text(spec["adjust_type"]),
        "horizon": sql_text(spec["horizon"]),
        "window_days": sql_int(spec["window_days"]),
        "signal_score": sql_int(spec.get("signal_score")),
        "signal_label": sql_text(spec.get("signal_label")),
        "signal_close": sql_number(spec.get("signal_close")),
        "status": sql_text("pending"),
        "raw_signal_json": sql_json(raw_signal),
    }
    return upsert_sql(
        "stock_signal_outcome",
        values,
        ["signal_score", "signal_label", "signal_close", "raw_signal_json"],
    )


def signal_outcome_statements(result: dict[str, Any], adjust_type: str) -> list[str]:
    return [signal_outcome_statement(spec, result) for spec in signal_accuracy.outcome_specs(result, adjust_type)]


def refresh_signal_outcomes_sql() -> str:
    return """
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
  );
""".strip()


def score_statement(result: dict[str, Any], adjust_type: str) -> str:
    item = result["raw"]
    technical = item.get("technical") or {}
    values = {
        "stock_code": sql_text(result["code"]),
        "trade_date": sql_date(technical["trade_date"]),
        "adjust_type": sql_text(adjust_type),
        "score": sql_int(result["score"]),
        "signal_label": sql_text(result["signal"]),
        "short_term_score": sql_int(horizon_value(result, "short_term", "score")),
        "short_term_signal_label": sql_text(horizon_value(result, "short_term", "signal")),
        "medium_term_score": sql_int(horizon_value(result, "medium_term", "score")),
        "medium_term_signal_label": sql_text(horizon_value(result, "medium_term", "signal")),
        "long_term_score": sql_int(horizon_value(result, "long_term", "score")),
        "long_term_signal_label": sql_text(horizon_value(result, "long_term", "signal")),
        "confidence": sql_text(result["confidence"]),
        "regime": sql_text(result["regime"]),
        "advice": sql_text(result["advice"]),
        "horizon_scores_json": sql_json(horizon_scores(result)),
        "score_parts_json": sql_json(result.get("parts") or []),
        "source_errors_json": sql_json(result.get("source_errors") or []),
        "raw_analysis_json": sql_json(item),
    }
    return upsert_sql(
        "stock_daily_signal_score",
        values,
        [column for column in values if column not in {"stock_code", "trade_date", "adjust_type"}],
    )


def report_statement(result: dict[str, Any], adjust_type: str) -> str:
    item = result["raw"]
    technical = item.get("technical") or {}
    title, report_text, report_json = generate_final_report(result)
    values = {
        "stock_code": sql_text(result["code"]),
        "trade_date": sql_date(technical["trade_date"]),
        "adjust_type": sql_text(adjust_type),
        "report_type": sql_text("final_summary"),
        "report_title": sql_text(title),
        "report_text": sql_text(report_text),
        "report_format": sql_text("markdown"),
        "report_json": sql_json(report_json),
    }
    return upsert_sql(
        "stock_daily_report",
        values,
        ["report_title", "report_text", "report_format", "report_json"],
    )


def ai_etf_snapshot_statement(portfolio: dict[str, Any]) -> str:
    values = {
        "portfolio_name": sql_text(portfolio["portfolioName"]),
        "trade_date": sql_date(portfolio["tradeDate"]),
        "adjust_type": sql_text(portfolio["adjustType"]),
        "selection_rule": sql_text(portfolio.get("selectionRule")),
        "nav": sql_number(portfolio.get("nav")),
        "daily_return_pct": sql_number(portfolio.get("dailyReturnPct")),
        "cumulative_return_pct": sql_number(portfolio.get("cumulativeReturnPct")),
        "realized_pnl": sql_number(portfolio.get("realizedPnl")),
        "unrealized_pnl": sql_number(portfolio.get("unrealizedPnl")),
        "total_pnl": sql_number(portfolio.get("totalPnl")),
        "turnover_pct": sql_number(portfolio.get("turnoverPct")),
        "holding_count": sql_int(portfolio.get("holdingCount")),
        "summary_json": sql_json(portfolio.get("summary") or {}),
    }
    return upsert_sql(
        "stock_ai_etf_snapshot",
        values,
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
    )


def ai_etf_holding_statement(holding: dict[str, Any]) -> str:
    values = {
        "portfolio_name": sql_text(holding["portfolioName"]),
        "trade_date": sql_date(holding["tradeDate"]),
        "adjust_type": sql_text(holding["adjustType"]),
        "stock_code": sql_text(holding["stockCode"]),
        "stock_name": sql_text(holding.get("stockName") or None),
        "industry": sql_text(holding.get("industry") or None),
        "previous_weight_pct": sql_number(holding.get("previousWeightPct")),
        "target_weight_pct": sql_number(holding.get("targetWeightPct")),
        "weight_delta_pct": sql_number(holding.get("weightDeltaPct")),
        "action": sql_text(holding.get("action")),
        "reference_price": sql_number(holding.get("referencePrice")),
        "simulated_quantity": sql_number(holding.get("simulatedQuantity")),
        "simulated_notional": sql_number(holding.get("simulatedNotional")),
        "score": sql_int(holding.get("score")),
        "signal_label": sql_text(holding.get("signalLabel")),
        "short_term_score": sql_int(holding.get("shortTermScore")),
        "short_term_signal_label": sql_text(holding.get("shortTermSignalLabel")),
        "medium_term_score": sql_int(holding.get("mediumTermScore")),
        "medium_term_signal_label": sql_text(holding.get("mediumTermSignalLabel")),
        "long_term_score": sql_int(holding.get("longTermScore")),
        "long_term_signal_label": sql_text(holding.get("longTermSignalLabel")),
        "confidence": sql_text(holding.get("confidence")),
        "rationale": sql_text(holding.get("rationale")),
        "risks_json": sql_json(holding.get("risks") or []),
        "raw_json": sql_json(holding),
    }
    return upsert_sql(
        "stock_ai_etf_holding",
        values,
        [column for column in values if column not in {"portfolio_name", "trade_date", "adjust_type", "stock_code"}],
    )


def ai_etf_trade_statement(trade: dict[str, Any]) -> str:
    values = {
        "portfolio_name": sql_text(trade["portfolioName"]),
        "trade_date": sql_date(trade["tradeDate"]),
        "adjust_type": sql_text(trade["adjustType"]),
        "stock_code": sql_text(trade["stockCode"]),
        "stock_name": sql_text(trade.get("stockName") or None),
        "action": sql_text(trade.get("action")),
        "previous_weight_pct": sql_number(trade.get("previousWeightPct")),
        "target_weight_pct": sql_number(trade.get("targetWeightPct")),
        "weight_delta_pct": sql_number(trade.get("weightDeltaPct")),
        "reference_price": sql_number(trade.get("referencePrice")),
        "simulated_quantity_delta": sql_number(trade.get("simulatedQuantityDelta")),
        "simulated_notional_delta": sql_number(trade.get("simulatedNotionalDelta")),
        "realized_pnl": sql_number(trade.get("realizedPnl")),
        "realized_return_pct": sql_number(trade.get("realizedReturnPct")),
        "reason": sql_text(trade.get("reason")),
        "raw_json": sql_json(trade),
    }
    return upsert_sql(
        "stock_ai_etf_trade",
        values,
        [column for column in values if column not in {"portfolio_name", "trade_date", "adjust_type", "stock_code", "action"}],
    )


def ai_etf_statements(portfolio: dict[str, Any] | None) -> list[str]:
    if not portfolio:
        return []
    statements = [ai_etf_snapshot_statement(portfolio)]
    statements.extend(ai_etf_holding_statement(holding) for holding in portfolio.get("holdings") or [])
    statements.extend(ai_etf_trade_statement(trade) for trade in portfolio.get("rebalance") or [])
    return statements


def build_report_sql(results: list[dict[str, Any]], adjust_type: str) -> str:
    statements = ["SET NAMES utf8mb4;", "START TRANSACTION;"]
    statements.extend(report_statement(result, adjust_type) for result in results)
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def build_persist_sql(
    results: list[dict[str, Any]],
    adjust_type: str,
    include_reports: bool = True,
    previous_ai_etf_holdings: list[dict[str, Any]] | None = None,
) -> str:
    statements = ["SET NAMES utf8mb4;", "START TRANSACTION;"]
    persisted_codes = []
    for result in results:
        item = result["raw"]
        technical = item.get("technical") or {}
        if not technical.get("trade_date"):
            raise RuntimeError(f"{item.get('code')} 缺少技术面交易日，无法写入每日数据表")
        persisted_codes.append(str(item["code"]))
        statements.append(security_statement(item))
        statements.append(quote_statement(item, adjust_type))
        statements.append(technical_statement(item, adjust_type))
        financial_sql = financial_statement(item)
        if financial_sql:
            statements.append(financial_sql)
        statements.append(trend_statement(item, adjust_type))
        statements.extend(trend_window_statements(item, adjust_type))
        statements.append(score_statement(result, adjust_type))
        statements.extend(signal_outcome_statements(result, adjust_type))
        if include_reports:
            statements.append(report_statement(result, adjust_type))

    portfolio = build_ai_etf_portfolio(results, adjust_type, previous_ai_etf_holdings)
    statements.extend(ai_etf_statements(portfolio))

    message = f"已写入 {len(persisted_codes)} 只股票的每日分析数据"
    statements.append(
        upsert_sql(
            "stock_data_ingest_run",
            {
                "run_finished_at": "CURRENT_TIMESTAMP",
                "status": sql_text("success"),
                "stock_codes_json": sql_json(persisted_codes),
                "message": sql_text(message),
            },
            ["run_finished_at", "status", "stock_codes_json", "message"],
        )
    )
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def validate_database_name(database: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise ValueError("database 只支持字母、数字和下划线")
    return database


def mysql_command(args: argparse.Namespace, use_database: bool) -> list[str]:
    command = [args.mysql_bin, f"--user={args.user}", "--default-character-set=utf8mb4", "--binary-mode"]
    if args.host:
        command.append(f"--host={args.host}")
    if args.port:
        command.append(f"--port={args.port}")
    if use_database:
        command.append(f"--database={args.database}")
    return command


def run_mysql(sql: str, args: argparse.Namespace, use_database: bool) -> None:
    env = os.environ.copy()
    if args.password:
        env["MYSQL_PWD"] = args.password
    result = subprocess.run(
        mysql_command(args, use_database),
        input=sql,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"MySQL 执行失败：{detail}")


def query_mysql(sql: str, args: argparse.Namespace, use_database: bool) -> str:
    env = os.environ.copy()
    if args.password:
        env["MYSQL_PWD"] = args.password
    result = subprocess.run(
        mysql_command(args, use_database) + ["--batch", "--raw", "--skip-column-names"],
        input=sql,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"MySQL 查询失败：{detail}")
    return result.stdout


def parse_mysql_nullable(value: str) -> str | None:
    return None if value in {"", "NULL", "\\N"} else value


def fetch_latest_ai_etf_holdings(args: argparse.Namespace, trade_date: str, adjust_type: str) -> list[dict[str, Any]]:
    if not trade_date:
        return []
    sql = f"""
SELECT
  stock_code,
  stock_name,
  industry,
  target_weight_pct,
  reference_price,
  simulated_quantity,
  simulated_notional
FROM stock_ai_etf_holding
WHERE portfolio_name = {sql_text(AI_ETF_PORTFOLIO_NAME)}
  AND adjust_type = {sql_text(adjust_type)}
  AND trade_date = (
    SELECT MAX(trade_date)
    FROM stock_ai_etf_holding
    WHERE portfolio_name = {sql_text(AI_ETF_PORTFOLIO_NAME)}
      AND adjust_type = {sql_text(adjust_type)}
      AND trade_date < {sql_date(trade_date)}
  )
  AND target_weight_pct > 0
ORDER BY stock_code;
"""
    output = query_mysql(sql, args, use_database=True)
    holdings = []
    for line in output.splitlines():
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != 7:
            continue
        holdings.append(
            {
                "stock_code": cells[0],
                "stock_name": parse_mysql_nullable(cells[1]),
                "industry": parse_mysql_nullable(cells[2]),
                "target_weight_pct": number(parse_mysql_nullable(cells[3])),
                "reference_price": number(parse_mysql_nullable(cells[4])),
                "simulated_quantity": number(parse_mysql_nullable(cells[5])),
                "simulated_notional": number(parse_mysql_nullable(cells[6])),
            }
        )
    return holdings


def fetch_evaluation_summaries(args: argparse.Namespace, stock_codes: list[str], adjust_type: str) -> dict[str, Any]:
    if not stock_codes:
        return {}
    code_list = ", ".join(sql_text(code) for code in stock_codes)
    sql = f"""
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
  AND adjust_type = {sql_text(adjust_type)}
  AND stock_code IN ({code_list})
  AND (signal_score > 70 OR signal_score < -70)
GROUP BY stock_code, horizon, window_days
ORDER BY stock_code, horizon, window_days;
"""
    output = query_mysql(sql, args, use_database=True)
    grouped: dict[str, list[list[str]]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != 9:
            continue
        grouped.setdefault(cells[0], []).append(cells[1:])
    return {code: signal_accuracy.parse_summary_rows(rows) for code, rows in grouped.items()}


def ensure_schema(args: argparse.Namespace) -> None:
    schema_path = Path(args.schema).resolve()
    schema_sql = schema_path.read_text(encoding="utf-8")
    schema_sql = re.sub(r"\bstock_analysis_test\b", validate_database_name(args.database), schema_sql)
    run_mysql(schema_sql, args, use_database=False)
    for migration_path in sorted(schema_path.parent.glob("20*.sql")):
        run_mysql(migration_path.read_text(encoding="utf-8"), args, use_database=True)


def parse_arg_date(value: str) -> dt.date:
    parsed = sfa.parse_date_like(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD")
    return parsed


def iter_dates(start: dt.date, end: dt.date) -> list[dt.date]:
    if start > end:
        raise ValueError("--backfill-from 不能晚于 --backfill-to")
    days = (end - start).days
    return [start + dt.timedelta(days=offset) for offset in range(days + 1)]


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def chunked(values: list[str], batch_size: int | None) -> list[list[str]]:
    if not batch_size:
        return [values]
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def requested_as_of_dates(args: argparse.Namespace) -> list[dt.date | None]:
    if args.backfill_from or args.backfill_to:
        if not args.backfill_from or not args.backfill_to:
            raise ValueError("--backfill-from 和 --backfill-to 必须同时传入")
        return iter_dates(args.backfill_from, args.backfill_to)
    return [args.as_of_date]


def analysis_trade_date(result: dict[str, Any]) -> str:
    return str(((result.get("raw") or {}).get("technical") or {}).get("trade_date") or "")


def filter_new_trade_date_results(
    results: list[dict[str, Any]],
    seen_keys: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for result in results:
        key = (str(result.get("code") or ""), analysis_trade_date(result))
        if not key[0] or not key[1] or key in seen_keys:
            continue
        seen_keys.add(key)
        filtered.append(result)
    return filtered


def analyze_results(args: argparse.Namespace, scorer: Any) -> list[dict[str, Any]]:
    items = fetch_analysis_items(args)
    total = len(items)
    log_status(args, f"开始评分 {total} 只股票")
    results = []
    for index, item in enumerate(items, start=1):
        result = scorer.score_item(item)
        log_status(
            args,
            f"[{index}/{total}] 评分完成 {result['code']} score={result['score']} signal={result['signal']} confidence={result['confidence']}",
        )
        results.append(result)
    return results


def persist_results(results: list[dict[str, Any]], args: argparse.Namespace) -> None:
    trade_dates = sorted({analysis_trade_date(result) for result in results if analysis_trade_date(result)})
    previous_holdings = fetch_latest_ai_etf_holdings(args, trade_dates[-1], args.adjust) if trade_dates else []
    run_mysql(
        build_persist_sql(
            results,
            args.adjust,
            include_reports=False,
            previous_ai_etf_holdings=previous_holdings,
        ),
        args,
        use_database=True,
    )
    run_mysql(refresh_signal_outcomes_sql(), args, use_database=True)
    stock_codes = [str(result["code"]) for result in results]
    summaries = fetch_evaluation_summaries(args, stock_codes, args.adjust)
    for result in results:
        result["evaluation_summary"] = summaries.get(str(result["code"]), signal_accuracy.empty_summary())
    run_mysql(build_report_sql(results, args.adjust), args, use_database=True)


def upload_results(
    results: list[dict[str, Any]],
    args: argparse.Namespace,
    adjust_type: str,
    ai_etf: dict[str, Any] | None = None,
) -> dict[str, Any]:
    token = getattr(args, "ingest_token", "") or os.environ.get("INGEST_API_TOKEN", "") or DEFAULT_INGEST_API_TOKEN
    payload = json.dumps({"adjustType": adjust_type, "results": results, "aiEtf": ai_etf}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        getattr(args, "ingest_url"),
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"上报接口返回 {exc.code}：{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"上报接口请求失败：{exc.reason}") from exc
    return json.loads(body) if body else {}


def health_url_for_ingest_url(ingest_url: str) -> str:
    parsed = urllib.parse.urlsplit(ingest_url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/api/health", "", ""))


def run_preflight(args: argparse.Namespace) -> int:
    failures: list[str] = []
    log_status(args, "开始环境预检")

    try:
        import akshare as ak

        version = getattr(ak, "__version__", "unknown")
        log_status(args, f"akshare 可导入：{version}")
    except Exception as exc:
        failures.append(f"akshare 导入失败：{describe_exception(exc)}")

    try:
        load_scorer()
        log_status(args, "评分器可加载")
    except Exception as exc:
        failures.append(f"评分器加载失败：{describe_exception(exc)}")

    try:
        codes = sfa.resolve_input_codes(args.codes, args.codes_file)
        preview = ", ".join(codes[:5])
        more = "..." if len(codes) > 5 else ""
        log_status(args, f"股票代码文件可读取：{len(codes)} 只（{preview}{more}）")
    except Exception as exc:
        failures.append(f"股票代码读取失败：{describe_exception(exc)}")

    if args.ingest_url:
        health_url = health_url_for_ingest_url(args.ingest_url)
        try:
            request = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            if payload.get("ok") is False:
                failures.append(f"生产服务健康检查失败：{payload}")
            else:
                database = payload.get("database")
                suffix = f"，database={database}" if database else ""
                log_status(args, f"生产服务健康检查通过：{health_url}{suffix}")
        except Exception as exc:
            failures.append(f"生产服务健康检查失败：{describe_exception(exc)}")

    if failures:
        for failure in failures:
            log_status(args, failure)
        return 1
    log_status(args, "环境预检通过")
    return 0


def render_dry_run_sql(results: list[dict[str, Any]], adjust_type: str) -> str:
    sql = build_persist_sql(results, adjust_type)
    return sql + "\n" + refresh_signal_outcomes_sql() + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取股票每日分析数据，并写入本地 MySQL。")
    parser.add_argument("codes", nargs="*", help="股票代码，支持空格、英文逗号、中文逗号分隔；不传则读取 stock.md")
    parser.add_argument(
        "--codes-file",
        default=str(PROJECT_ROOT / "stock.md"),
        help="股票代码文件，默认读取项目根目录 stock.md；仅在不传 codes 时生效",
    )
    parser.add_argument("--database", default="stock_analysis_test")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int)
    parser.add_argument("--mysql-bin", default="mysql")
    parser.add_argument("--schema", default=str(PROJECT_ROOT / "sql/schema.sql"))
    parser.add_argument("--skip-schema", action="store_true", help="跳过 CREATE DATABASE/TABLE")
    parser.add_argument("--start-year", default="2021")
    parser.add_argument("--technical-days", type=int, default=260)
    parser.add_argument("--adjust", choices=["none", "qfq", "hfq"], default="qfq")
    parser.add_argument("--as-of-date", type=parse_arg_date, help="按指定日期回看分析，只使用该日期及以前的日线数据")
    parser.add_argument("--backfill-from", type=parse_arg_date, help="历史回填起始日期，需与 --backfill-to 同时使用")
    parser.add_argument("--backfill-to", type=parse_arg_date, help="历史回填结束日期，需与 --backfill-from 同时使用")
    parser.add_argument("--ingest-url", default="", help="通过 Express ingest 接口上报分析结果，传入后不直连本地 MySQL")
    parser.add_argument("--ingest-token", default="", help="Express ingest 接口 Bearer Token；也可用 INGEST_API_TOKEN")
    parser.add_argument("--batch-size", type=positive_int, help="按指定数量分批分析并写入/上报，例如 10 表示每 10 只提交一次")
    parser.add_argument("--skip-eastmoney", action="store_true", help="跳过 Eastmoney 实时概要/估值接口，直接使用降级数据源")
    parser.add_argument("--preflight", action="store_true", help="只检查运行环境、代码文件和生产服务健康，不抓取或写入股票数据")
    parser.add_argument("--quiet", action="store_true", help="关闭进度日志，仅保留最终结果或错误")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的 SQL，不写库")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    started_at = time.monotonic()
    try:
        validate_database_name(args.database)
        if args.preflight:
            return run_preflight(args)
        scorer = load_scorer()
        as_of_dates = requested_as_of_dates(args)
        if args.dry_run and args.ingest_url:
            raise ValueError("--dry-run 仅支持本地 MySQL SQL 输出，不能与 --ingest-url 同时使用")
        if not args.dry_run and not args.ingest_url and not args.skip_schema:
            ensure_schema(args)
        seen_keys: set[tuple[str, str]] = set()
        all_results: list[dict[str, Any]] = []
        dry_run_parts: list[str] = []
        resolved_codes = sfa.resolve_input_codes(args.codes, args.codes_file) if args.batch_size else None
        code_names = {} if args.codes or not args.batch_size else sfa.load_code_names_from_file(args.codes_file)
        for as_of_date in as_of_dates:
            run_args = argparse.Namespace(**vars(args))
            run_args.as_of_date = as_of_date
            batches = chunked(resolved_codes, args.batch_size) if resolved_codes is not None else [None]
            date_had_results = False
            for batch_index, batch_codes in enumerate(batches, start=1):
                if batch_codes is not None:
                    run_args = argparse.Namespace(**vars(args))
                    run_args.as_of_date = as_of_date
                    run_args.resolved_codes = batch_codes
                    run_args.code_names = code_names
                    log_status(args, f"开始处理第 {batch_index}/{len(batches)} 批：{len(batch_codes)} 只股票")
                results = analyze_results(run_args, scorer)
                if args.backfill_from or args.backfill_to:
                    results = filter_new_trade_date_results(results, seen_keys)
                if not results:
                    continue
                date_had_results = True
                if args.dry_run:
                    dry_run_parts.append(render_dry_run_sql(results, args.adjust))
                elif args.ingest_url:
                    batch_label = f"第 {batch_index}/{len(batches)} 批，" if batch_codes is not None else ""
                    log_status(args, f"开始上报生产 ingest：{batch_label}{len(results)} 条结果")
                    ai_etf = build_ai_etf_portfolio(results, args.adjust)
                    upload_response = upload_results(results, run_args, args.adjust, ai_etf=ai_etf)
                    persisted_count = upload_response.get("persistedCount")
                    suffix = f"，persistedCount={persisted_count}" if persisted_count is not None else ""
                    log_status(args, f"生产 ingest 上报完成{suffix}")
                else:
                    batch_label = f"第 {batch_index}/{len(batches)} 批，" if batch_codes is not None else ""
                    log_status(args, f"开始写入本地 MySQL：{batch_label}{len(results)} 条结果")
                    persist_results(results, run_args)
                    log_status(args, "本地 MySQL 写入完成")
                all_results.extend(results)
            if not date_had_results:
                label = f"{as_of_date:%Y-%m-%d}" if as_of_date else "本次运行"
                print(f"{label} 无新的交易日快照，已跳过")
        if args.dry_run:
            print("\n".join(dry_run_parts), end="")
            return 0
    except Exception as exc:
        print(f"入库失败：{exc}", file=sys.stderr)
        return 1

    for result in all_results:
        item = result["raw"]
        trade_date = (item.get("technical") or {}).get("trade_date") or "未知交易日"
        print(
            f"{result['code']} {trade_date} 已写入："
            f"score={result['score']} signal={result['signal']} confidence={result['confidence']}"
        )
    elapsed = time.monotonic() - started_at
    log_status(args, f"任务完成：{len(all_results)} 条结果，耗时 {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
