#!/usr/bin/env python3
"""Score A-share buy/sell signals from the project's stock analysis JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


SKILL_ROOT = Path(__file__).resolve().parents[1]
STRATEGY_MEMORY_PATH = SKILL_ROOT / "references" / "review-memory.md"
MEMORY_JSON_START = "<!-- strategy-memory-json:start -->"
MEMORY_JSON_END = "<!-- strategy-memory-json:end -->"


def clamp(value: float, lower: int = -100, upper: int = 100) -> int:
    return max(lower, min(upper, round(value)))


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_map(item: dict[str, Any]) -> dict[str, float | None]:
    return {metric.get("label", ""): number(metric.get("value")) for metric in item.get("metrics", [])}


def add(parts: list[dict[str, Any]], module: str, points: float, reason: str) -> None:
    parts.append({"module": module, "points": points, "reason": reason})


def empty_strategy_memory() -> dict[str, Any]:
    return {"version": 1, "active_adjustments": []}


def extract_strategy_memory_payload(text: str) -> str:
    start = text.find(MEMORY_JSON_START)
    end = text.find(MEMORY_JSON_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("复盘 memory 缺少 strategy-memory-json 标记块")

    block = text[start + len(MEMORY_JSON_START) : end]
    fence_start = block.find("```json")
    if fence_start == -1:
        raise ValueError("复盘 memory 标记块内缺少 json 代码块")
    payload_start = block.find("\n", fence_start)
    fence_end = block.find("```", payload_start + 1)
    if payload_start == -1 or fence_end == -1:
        raise ValueError("复盘 memory JSON 代码块未正确闭合")
    return block[payload_start:fence_end].strip()


def validate_strategy_memory(memory: Any) -> dict[str, Any]:
    if not isinstance(memory, dict):
        raise ValueError("复盘 memory 必须是 JSON object")
    adjustments = memory.get("active_adjustments", [])
    if not isinstance(adjustments, list):
        raise ValueError("复盘 memory 的 active_adjustments 必须是数组")
    return memory


@lru_cache(maxsize=1)
def load_strategy_memory(memory_path: str | None = None) -> dict[str, Any]:
    path = Path(memory_path) if memory_path else STRATEGY_MEMORY_PATH
    if not path.exists():
        return empty_strategy_memory()
    payload = extract_strategy_memory_payload(path.read_text(encoding="utf-8"))
    return validate_strategy_memory(json.loads(payload))


HORIZON_DEFINITIONS = {
    "short_term": {
        "label": "短期",
        "weights": {"fundamental": 0.25, "trend": 0.60, "timing": 3.20, "data_penalty": 3.0},
        "reasons": {
            "fundamental": "基本面只做短线底线约束，避免纯技术追高",
            "trend": "趋势环境影响短线胜率和反弹可持续性",
            "timing": "MACD、BOLL、KDJ、RSI 和成交量是短期主权重",
        },
    },
    "medium_term": {
        "label": "中期",
        "weights": {"fundamental": 0.70, "trend": 1.70, "timing": 1.10, "data_penalty": 2.0},
        "reasons": {
            "fundamental": "基本面对中期持有提供质量支撑",
            "trend": "20/60/120 日趋势是中期评分主权重",
            "timing": "短线动能用于确认中期入场节奏",
        },
    },
    "long_term": {
        "label": "长期",
        "weights": {"fundamental": 1.50, "trend": 1.20, "timing": 0.25, "data_penalty": 1.0},
        "reasons": {
            "fundamental": "ROE、成长、现金流和估值是长期主权重",
            "trend": "120/250 日结构用于确认长期趋势是否配合",
            "timing": "短线择时只作为长期建仓节奏参考",
        },
    },
}


def score_fundamentals(item: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    metrics = metric_map(item)
    valuation = item.get("valuation") or {}
    parts: list[dict[str, Any]] = []

    roe = metrics.get("ROE")
    if roe is not None:
        if roe >= 15:
            add(parts, "基本面", 12, f"ROE {roe:.2f}% 较强")
        elif roe >= 8:
            add(parts, "基本面", 6, f"ROE {roe:.2f}% 尚可")
        elif roe < 5:
            add(parts, "基本面", -8, f"ROE {roe:.2f}% 偏弱")

    revenue_growth = metrics.get("营收增长")
    profit_growth = metrics.get("净利润增长")
    if revenue_growth is not None and profit_growth is not None:
        if revenue_growth > 20 and profit_growth > 20:
            add(parts, "基本面", 12, "营收和净利润均高增长")
        elif revenue_growth > 10 and profit_growth > 10:
            add(parts, "基本面", 8, "营收和净利润均保持增长")
        elif revenue_growth < 0 and profit_growth < 0:
            add(parts, "基本面", -10, "营收和净利润同时下滑")
        elif revenue_growth > 0 > profit_growth:
            add(parts, "基本面", -6, "营收增长但净利润下滑")

    debt_ratio = metrics.get("资产负债率")
    if debt_ratio is not None:
        if debt_ratio < 45:
            add(parts, "基本面", 6, f"资产负债率 {debt_ratio:.2f}% 较稳健")
        elif debt_ratio > 70:
            add(parts, "基本面", -8, f"资产负债率 {debt_ratio:.2f}% 偏高")

    ocf_per_share = metrics.get("每股经营现金流")
    if ocf_per_share is not None:
        add(parts, "基本面", 3 if ocf_per_share > 0 else -5, f"每股经营现金流 {ocf_per_share:.3f}")

    ocf_to_profit = metrics.get("经营现金流/净利润")
    if ocf_to_profit is not None:
        if ocf_to_profit >= 1:
            add(parts, "基本面", 8, f"经营现金流/净利润 {ocf_to_profit:.2f}倍，利润现金含量好")
        elif ocf_to_profit >= 0.5:
            add(parts, "基本面", 3, f"经营现金流/净利润 {ocf_to_profit:.2f}倍，现金含量一般")
        else:
            add(parts, "基本面", -8, f"经营现金流/净利润 {ocf_to_profit:.2f}倍，现金含量偏弱")

    pe = number(valuation.get("市盈率-动态"))
    if pe is not None:
        if pe <= 0:
            add(parts, "基本面", -8, "动态市盈率为负或不可用，盈利阶段需谨慎")
        elif pe <= 25:
            add(parts, "基本面", 5, f"动态市盈率 {pe:.2f} 不高")
        elif pe > 60:
            add(parts, "基本面", -8, f"动态市盈率 {pe:.2f} 偏高")

    return sum(part["points"] for part in parts), parts


def window_map(item: dict[str, Any]) -> dict[int, dict[str, Any]]:
    trend = item.get("technical_trend") or {}
    return {int(window.get("days")): window for window in trend.get("windows", []) if window.get("days") is not None}


def detect_regime(item: dict[str, Any]) -> str:
    trend = item.get("technical_trend") or {}
    windows = window_map(item)
    rating = trend.get("rating", "")
    r20 = number((windows.get(20) or {}).get("return_pct"))
    r60 = number((windows.get(60) or {}).get("return_pct"))
    r120 = number((windows.get(120) or {}).get("return_pct"))

    if "偏弱" in rating and (r60 is None or r60 < 0):
        return "downtrend"
    if r20 is not None and r20 < 0 and any(value is not None and value > 0 for value in [r60, r120]):
        return "range"
    if "偏强" in rating and (r20 is None or r20 >= 0):
        return "trend"
    return "mixed"


def score_trend(item: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    trend = item.get("technical_trend") or {}
    windows = window_map(item)
    parts: list[dict[str, Any]] = []

    trend_score = number(trend.get("score"))
    if trend_score is not None:
        add(parts, "长期趋势", max(-28, min(28, trend_score * 4)), f"长期趋势评分 {trend_score:.0f}：{trend.get('rating', '未知')}")

    thresholds = {
        20: (5, -5, 4, -5),
        60: (10, -10, 5, -6),
        120: (15, -15, 6, -8),
        250: (20, -20, 5, -8),
    }
    for days, (pos_threshold, neg_threshold, pos_points, neg_points) in thresholds.items():
        value = number((windows.get(days) or {}).get("return_pct"))
        if value is None:
            continue
        if value >= pos_threshold:
            add(parts, "长期趋势", pos_points, f"近 {days} 日涨幅 {value:.2f}%")
        elif value <= neg_threshold:
            add(parts, "长期趋势", neg_points, f"近 {days} 日跌幅 {value:.2f}%")

    r20 = number((windows.get(20) or {}).get("return_pct"))
    r60 = number((windows.get(60) or {}).get("return_pct"))
    r120 = number((windows.get(120) or {}).get("return_pct"))
    if r20 is not None and r20 < -5 and any(value is not None and value > 10 for value in [r60, r120]):
        add(parts, "长期趋势", -3, "长期仍强但近 20 日回撤，买点需要等待确认")

    return sum(part["points"] for part in parts), parts


def score_timing(item: dict[str, Any], regime: str) -> tuple[float, list[dict[str, Any]]]:
    technical = item.get("technical") or {}
    macd = technical.get("macd") or {}
    boll = technical.get("boll") or {}
    kdj = technical.get("kdj") or {}
    rsi = technical.get("rsi") or {}
    parts: list[dict[str, Any]] = []

    macd_bar = number(macd.get("bar"))
    dif = number(macd.get("dif"))
    dea = number(macd.get("dea"))
    if macd_bar is not None and dif is not None and dea is not None:
        if macd_bar > 0 and dif > dea:
            add(parts, "短线择时", 8 if regime == "trend" else 5, "MACD 柱体为正，短线动能配合")
        elif macd_bar < 0 and dif < dea:
            add(parts, "短线择时", -10 if regime == "downtrend" else -8, "MACD 柱体为负，短线动能偏弱")

    boll_position = str(boll.get("position") or "")
    if boll_position:
        if regime == "range":
            points_by_position = {"跌破下轨": 8, "突破上轨": -8, "中轨上方": 4, "中轨下方": -4}
        elif regime == "trend":
            points_by_position = {"跌破下轨": -8, "突破上轨": 4, "中轨上方": 5, "中轨下方": -5}
        else:
            points_by_position = {"跌破下轨": 3, "突破上轨": -4, "中轨上方": 3, "中轨下方": -3}
        add(parts, "短线择时", points_by_position.get(boll_position, 0), f"BOLL 位置：{boll_position}")

    j_value = number(kdj.get("j"))
    if j_value is not None:
        if j_value >= 100:
            add(parts, "短线择时", -7, f"KDJ-J {j_value:.2f} 过热")
        elif j_value >= 80:
            add(parts, "短线择时", -4, f"KDJ-J {j_value:.2f} 偏高")
        elif j_value <= 0:
            add(parts, "短线择时", 4 if regime != "downtrend" else 1, f"KDJ-J {j_value:.2f} 超卖")

    rsi6 = number(rsi.get("rsi6"))
    rsi24 = number(rsi.get("rsi24"))
    if rsi6 is not None:
        if rsi6 >= 80:
            add(parts, "短线择时", -7, f"RSI6 {rsi6:.2f} 过热")
        elif rsi6 <= 20:
            add(parts, "短线择时", 4 if regime != "downtrend" else 1, f"RSI6 {rsi6:.2f} 超卖")
        elif 45 <= rsi6 <= 65:
            add(parts, "短线择时", 2, f"RSI6 {rsi6:.2f} 处于常规区间")
    if rsi24 is not None:
        if 45 <= rsi24 <= 65:
            add(parts, "短线择时", 2, f"RSI24 {rsi24:.2f} 中期强弱平衡")
        elif rsi24 < 35:
            add(parts, "短线择时", -3, f"RSI24 {rsi24:.2f} 中期偏弱")

    volume_ratio = number(technical.get("volume_ratio_5"))
    if volume_ratio is not None:
        if volume_ratio >= 1.5:
            add(parts, "短线择时", 2 if regime == "trend" else -1, f"成交量放大，5日量比 {volume_ratio:.2f}")
        elif volume_ratio <= 0.7:
            add(parts, "短线择时", -2, f"成交量收缩，5日量比 {volume_ratio:.2f}")

    return sum(part["points"] for part in parts), parts


def confidence(score: int, item: dict[str, Any]) -> str:
    errors = item.get("source_errors") or []
    if abs(score) < 15 or len(errors) >= 2:
        return "低"
    if abs(score) < 35 or errors:
        return "中"
    return "高"


def signal_label(score: int) -> str:
    if score >= 50:
        return "强买"
    if score >= 15:
        return "买入偏向"
    if score > -15:
        return "观望"
    if score > -50:
        return "卖出偏向"
    return "强卖/回避"


def signal_side_for_score(score: int) -> str:
    if score >= 15:
        return "buy_bias"
    if score <= -15:
        return "sell_avoid"
    return "watch"


def operation_advice(score: int, regime: str) -> str:
    if score >= 50:
        return "可考虑正向配置，但仍建议分批并设置失效条件。"
    if score >= 15:
        if regime == "range":
            return "买入偏向存在，但更适合等回踩 BOLL 中下轨或重新放量转强后分批。"
        return "买入偏向存在，适合分批试仓，等待趋势指标继续确认。"
    if score > -15:
        return "接近中性，当前更适合观察，等待趋势或基本面出现更一致信号。"
    if score > -50:
        return "卖出或回避偏向，除非后续重新站上关键均线且动能修复。"
    return "风险信号较强，优先回避，等待重新形成趋势结构。"


def horizon_advice(horizon: str, score: int, regime: str) -> str:
    if horizon == "short_term":
        if score >= 50:
            return "短期动能和环境配合，可考虑顺势但需要严格止损。"
        if score >= 15:
            return "短期有买入偏向，更适合小仓位试探或等待放量确认。"
        if score > -15:
            return "短期信号不够一致，等待突破、回踩或动能修复。"
        return "短期风险偏高，先回避追涨或降低仓位。"

    if horizon == "medium_term":
        if score >= 50:
            return "中期趋势和质量配合，适合分批配置并跟踪关键均线。"
        if score >= 15:
            return "中期偏正向，可分批跟踪，等待趋势继续确认。"
        if score > -15:
            return "中期证据混合，观察 20/60/120 日趋势是否重新同向。"
        return "中期偏弱，除非重新站回关键均线并改善量价结构。"

    if score >= 50:
        return "长期质量和趋势较强，适合纳入长期观察或分批配置池。"
    if score >= 15:
        return "长期有正向基础，但仍要结合估值、安全边际和仓位管理。"
    if score > -15:
        return "长期吸引力不足，等待基本面或长期趋势给出更清晰证据。"
    if regime == "downtrend":
        return "长期趋势偏弱，优先等待长期结构修复。"
    return "长期风险收益不占优，暂不适合提高配置权重。"


def score_horizons(
    fundamental_score: float,
    trend_score: float,
    timing_score: float,
    data_penalty: float,
    regime: str,
    strategy_memory: dict[str, Any] | None = None,
    strategy_factors: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    horizons: dict[str, dict[str, Any]] = {}
    applied_strategy_adjustments: list[dict[str, Any]] = []
    for key, definition in HORIZON_DEFINITIONS.items():
        weights = dict(definition["weights"])
        reasons = dict(definition["reasons"])
        horizon_adjustments = matching_strategy_adjustments(strategy_memory, key, regime, strategy_factors)
        for adjustment in horizon_adjustments:
            adjustment_id = str(adjustment["id"])
            for component, multiplier in (adjustment.get("component_weight_multipliers") or {}).items():
                if component not in weights:
                    raise ValueError(f"复盘 memory 包含未知权重组件：{component}")
                factor = number(multiplier)
                if factor is None or factor <= 0:
                    raise ValueError(f"复盘 memory 权重倍数无效：{adjustment_id}.{component}")
                weights[component] *= factor
                reasons[component] = f"{reasons[component]}；复盘 {adjustment_id} 权重 x{factor:g}"
        parts = [
            {
                "module": f"{definition['label']}基本面",
                "points": fundamental_score * weights["fundamental"],
                "reason": reasons["fundamental"],
            },
            {
                "module": f"{definition['label']}趋势",
                "points": trend_score * weights["trend"],
                "reason": reasons["trend"],
            },
            {
                "module": f"{definition['label']}择时",
                "points": timing_score * weights["timing"],
                "reason": reasons["timing"],
            },
        ]
        if data_penalty:
            parts.append(
                {
                    "module": f"{definition['label']}数据质量",
                    "points": data_penalty * weights["data_penalty"],
                    "reason": "技术面数据缺失时降低该时间维度置信度和评分",
                }
            )
        for adjustment in horizon_adjustments:
            bias = number(adjustment.get("score_bias"))
            if bias:
                parts.append(
                    {
                        "module": f"{definition['label']}复盘校准",
                        "points": bias,
                        "reason": f"复盘 {adjustment['id']}: {adjustment.get('reason', '')}",
                    }
                )
        score = clamp(sum(part["points"] for part in parts))
        applied_adjustment_ids: set[str] = set()
        for adjustment in horizon_adjustments:
            adjustment_id = str(adjustment["id"])
            if adjustment.get("component_weight_multipliers") or number(adjustment.get("score_bias")):
                applied_adjustment_ids.add(adjustment_id)
            if str(adjustment.get("score_adjustment_mode") or "") != "neutralize_to_watch":
                continue
            expected_side = str((adjustment.get("scope") or {}).get("signal_side") or "")
            current_side = signal_side_for_score(score)
            if expected_side and current_side != expected_side:
                continue
            boundary = number(adjustment.get("target_score_boundary"))
            if current_side == "sell_avoid":
                adjusted_score = max(score, clamp(boundary if boundary is not None else -14))
            elif current_side == "buy_bias":
                adjusted_score = min(score, clamp(boundary if boundary is not None else 14))
            else:
                continue
            if adjusted_score == score:
                continue
            parts.append(
                {
                    "module": f"{definition['label']}复盘观察降级",
                    "points": adjusted_score - score,
                    "reason": f"复盘 {adjustment_id}: {adjustment.get('reason', '')}",
                }
            )
            score = adjusted_score
            applied_adjustment_ids.add(adjustment_id)
        for adjustment in horizon_adjustments:
            adjustment_id = str(adjustment["id"])
            if adjustment_id not in applied_adjustment_ids:
                continue
            applied_strategy_adjustments.append(
                {
                    "id": adjustment_id,
                    "horizon": key,
                    "regime": regime,
                    "mode": adjustment.get("score_adjustment_mode") or "score_bias",
                    "reason": adjustment.get("reason", ""),
                }
            )
        horizons[key] = {
            "label": definition["label"],
            "score": score,
            "signal": signal_label(score),
            "advice": horizon_advice(key, score, regime),
            "parts": parts,
        }
    return horizons, applied_strategy_adjustments


def matching_strategy_adjustments(
    strategy_memory: dict[str, Any] | None,
    horizon: str,
    regime: str,
    strategy_factors: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if not strategy_memory:
        return []
    strategy_factors = strategy_factors or {}
    adjustments: list[dict[str, Any]] = []
    for adjustment in strategy_memory.get("active_adjustments", []):
        if adjustment.get("status", "active") != "active":
            continue
        if "id" not in adjustment:
            raise ValueError("复盘 memory 的 active adjustment 缺少 id")
        scope = adjustment.get("scope") or {}
        horizons = scope.get("horizons") or list(HORIZON_DEFINITIONS)
        regimes = scope.get("regimes") or ["trend", "range", "downtrend", "mixed"]
        if horizon not in horizons or regime not in regimes:
            continue
        scoped_factors = scope.get("factors") or {}
        if any(str(strategy_factors.get(str(name)) or "") != str(value) for name, value in scoped_factors.items()):
            continue
        adjustments.append(adjustment)
    return adjustments


def strategy_factor_tags(item: dict[str, Any], regime: str) -> dict[str, str]:
    factors = {"regime": regime}
    for source_key in ["factors", "strategy_factors"]:
        for name, value in (item.get(source_key) or {}).items():
            factors[str(name)] = str(value)
    return factors


def score_item(item: dict[str, Any], strategy_memory: dict[str, Any] | None = None) -> dict[str, Any]:
    regime = detect_regime(item)
    strategy_factors = strategy_factor_tags(item, regime)
    fundamental_score, fundamental_parts = score_fundamentals(item)
    trend_score, trend_parts = score_trend(item)
    timing_score, timing_parts = score_timing(item, regime)
    data_penalty = -5 if not item.get("technical") else 0
    total = clamp(fundamental_score + trend_score + timing_score + data_penalty)
    memory = validate_strategy_memory(strategy_memory) if strategy_memory is not None else load_strategy_memory()
    horizon_scores, strategy_adjustments = score_horizons(
        fundamental_score,
        trend_score,
        timing_score,
        data_penalty,
        regime,
        memory,
        strategy_factors,
    )
    parts = fundamental_parts + trend_parts + timing_parts
    if data_penalty:
        add(parts, "数据质量", data_penalty, "技术面数据缺失，降低评分")
    return {
        "code": item.get("code"),
        "name": item.get("name"),
        "score": total,
        "signal": signal_label(total),
        "confidence": confidence(total, item),
        "regime": regime,
        "advice": operation_advice(total, regime),
        "horizon_scores": horizon_scores,
        "strategy_adjustments": strategy_adjustments,
        "parts": parts,
        "source_errors": item.get("source_errors") or [],
        "raw": item,
    }


def run_project_analysis(args: argparse.Namespace) -> list[dict[str, Any]]:
    root = Path(args.project_root).resolve() if args.project_root else project_root()
    if args.input_json:
        return json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    command = [
        sys.executable,
        str(root / "stock_fundamental_analysis.py"),
        *args.codes,
        "--codes-file",
        args.codes_file,
        "--json",
        "--start-year",
        args.start_year,
        "--technical-days",
        str(args.technical_days),
        "--adjust",
        args.adjust,
    ]
    if args.as_of_date:
        command.extend(["--as-of-date", args.as_of_date])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "stock_fundamental_analysis.py failed")
    return json.loads(result.stdout)


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# 股票买卖信号评分", ""]
    for result in results:
        name = f" {result['name']}" if result.get("name") else ""
        lines.extend(
            [
                f"## {result['code']}{name}",
                "",
                f"- 分数：{result['score']}/100",
                f"- 信号：{result['signal']}",
                f"- 置信度：{result['confidence']}",
                f"- 市场状态：{result['regime']}",
                f"- 操作建议：{result['advice']}",
                "",
                "### 时间维度评分",
                "",
                "| 维度 | 分数 | 信号 | 操作提示 |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for horizon in result.get("horizon_scores", {}).values():
            lines.append(
                f"| {horizon['label']} | {horizon['score']}/100 | {horizon['signal']} | {horizon['advice']} |"
            )
        lines.extend(
            [
                "",
                "### 评分拆解",
                "",
                "| 模块 | 分数 | 原因 |",
                "| --- | ---: | --- |",
            ]
        )
        for part in result["parts"]:
            lines.append(f"| {part['module']} | {part['points']:.1f} | {part['reason']} |")
        strategy_adjustments = result.get("strategy_adjustments") or []
        if strategy_adjustments:
            lines.extend(["", "### 复盘与自学习", ""])
            horizons = result.get("horizon_scores") or {}
            for adjustment in strategy_adjustments:
                horizon_key = str(adjustment.get("horizon") or "unknown")
                horizon = str((horizons.get(horizon_key) or {}).get("label") or horizon_key)
                adjustment_id = str(adjustment.get("id") or "unknown")
                reason = str(adjustment.get("reason") or "暂无原因")
                lines.append(f"- {horizon}：{adjustment_id}，{reason}")
        if result["source_errors"]:
            lines.extend(["", "### 数据提醒", ""])
            lines.extend(f"- {error}" for error in result["source_errors"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score A-share buy/sell signals from local project data.")
    parser.add_argument("codes", nargs="*", help="Stock codes, e.g. 002466 600519 or '002466,600519'. Empty means read stock.md.")
    parser.add_argument("--codes-file", default="stock.md", help="Stock code file used when no positional codes are provided.")
    parser.add_argument("--input-json", help="Use existing stock_fundamental_analysis.py JSON output instead of fetching.")
    parser.add_argument("--project-root", help="Override project root.")
    parser.add_argument("--start-year", default="2021")
    parser.add_argument("--technical-days", type=int, default=260)
    parser.add_argument("--adjust", choices=["none", "qfq", "hfq"], default="qfq")
    parser.add_argument("--as-of-date", help="按指定日期回看分析，只使用该日期及以前的日线数据")
    parser.add_argument("--json", action="store_true", help="Output structured scoring JSON.")
    args = parser.parse_args(argv)
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        items = run_project_analysis(args)
        results = [score_item(item) for item in items]
    except Exception as exc:
        print(f"评分失败：{exc}", file=sys.stderr)
        return 1

    if args.json:
        for result in results:
            result.pop("raw", None)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(results), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
