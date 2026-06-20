#!/usr/bin/env python3
"""本地历史回测研究：只用信号日前可见数据评分，再用未来交易日验证。"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import sys
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import signal_accuracy
import stock_fundamental_analysis as sfa

PROJECT_ROOT = Path(__file__).resolve().parent
SCORER_PATH = PROJECT_ROOT / ".codex/skills/stock-buy-signal-analysis/scripts/analyze_stock.py"

HORIZON_LABELS = {
    "short_term": "短期",
    "medium_term": "中期",
    "long_term": "长期",
}
SIGNAL_SIDE_LABELS = {
    "buy_bias": "买入方向",
    "sell_avoid": "卖出/回避方向",
    "watch": "观望",
}
REFINED_REGIME_LABELS = {
    "downtrend_repair": "下跌修复",
    "bear_continuation": "弱势延续",
    "trend_extension": "趋势延续",
    "range_rebound": "震荡反弹",
    "trend": "趋势",
    "range": "震荡",
    "downtrend": "下跌",
    "mixed": "混合",
    "unknown": "未知",
}
MARKET_REGIME_LABELS = {
    "market_bear_rebound": "市场熊尾修复",
    "market_bear_continuation": "市场弱势延续",
    "market_bull_extension": "市场趋势延续",
    "market_range_rebound": "市场震荡反弹",
    "market_downtrend": "市场下跌",
    "market_range": "市场震荡",
    "market_trend": "市场趋势",
    "market_unknown": "市场未知",
}
TREND_THRESHOLDS = {
    20: (5, -5),
    60: (10, -10),
    120: (15, -15),
    250: (20, -20),
}
MARKET_TREND_THRESHOLDS = {
    20: (3, -3),
    60: (6, -6),
    120: (10, -10),
    250: (15, -15),
}
DEFAULT_STAGE_FOLD_FACTORS = [
    "market_trend_20d",
    "market_trend_60d",
    "market_trend_120d",
    "market_trend_250d",
    "market_macd_state",
    "trend_20d",
    "trend_60d",
    "trend_120d",
    "trend_250d",
    "volume_state",
    "horizon_alignment",
    "decline_duration",
    "decline_speed",
    "weak_tail_extreme",
    "tail_repair_signal",
    "macd_repair_continuity",
    "rsi_rebound_continuity",
    "kdj_rebound_continuity",
    "boll_recovery_continuity",
    "volume_continuity",
    "repair_continuity",
    "repair_speed",
    "macd_repair_speed",
    "rsi_rebound_speed",
    "kdj_rebound_speed",
    "boll_recovery_speed",
    "volume_expansion_speed",
    "repair_speed_profile",
    "repair_quality_confirmation",
    "repair_quality_sync",
    "market_decline_duration",
    "market_decline_speed",
    "market_tail_extreme",
    "market_tail_repair_signal",
    "market_volume_state",
    "market_macd_repair_continuity",
    "market_rsi_rebound_continuity",
    "market_kdj_rebound_continuity",
    "market_boll_recovery_continuity",
    "market_volume_continuity",
    "market_repair_continuity",
    "market_repair_speed",
    "market_macd_repair_speed",
    "market_rsi_rebound_speed",
    "market_kdj_rebound_speed",
    "market_boll_recovery_speed",
    "market_volume_expansion_speed",
    "market_repair_speed_profile",
    "market_repair_quality_confirmation",
]
DEFAULT_COUNTEREXAMPLE_FACTORS = [
    "repair_quality_sync",
    "market_repair_quality_confirmation",
    "repair_quality_confirmation",
    "market_repair_speed_profile",
    "repair_speed_profile",
    "market_macd_repair_speed",
    "macd_repair_speed",
    "market_boll_recovery_speed",
    "boll_recovery_speed",
    "market_volume_expansion_speed",
    "volume_expansion_speed",
    "market_tail_repair_signal",
    "tail_repair_signal",
    "market_decline_speed",
    "decline_speed",
    "market_trend_20d",
    "trend_20d",
]
DEFAULT_STAGE_BLOCK_PROFILE_FACTORS = [
    "market_trend_20d",
    "market_trend_60d",
    "market_decline_speed",
    "market_tail_extreme",
    "market_repair_speed_profile",
    "market_repair_quality_confirmation",
    "market_volume_expansion_speed",
    "trend_20d",
    "trend_60d",
    "decline_speed",
    "weak_tail_extreme",
    "repair_speed_profile",
    "repair_quality_sync",
    "volume_expansion_speed",
]
HORIZON_SELECTION_PROFILES = [
    (
        "弱势尾部基础",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
        },
    ),
    (
        "弱势尾部+市场跌速加快",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
            "market_decline_speed": "跌速加快",
        },
    ),
    (
        "弱势尾部+市场速度未形成",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
            "market_repair_speed_profile": "速度未形成",
        },
    ),
    (
        "弱势尾部+量能未改善",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
            "volume_expansion_speed": "速度未改善",
        },
    ),
    (
        "弱势尾部+质量同步不足",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
            "repair_quality_sync": "质量同步不足",
        },
    ),
    (
        "弱势尾部+未确认慢修复",
        {
            "market_trend_20d": "下跌",
            "market_trend_60d": "下跌",
            "trend_20d": "下跌",
            "trend_60d": "下跌",
            "market_repair_speed_profile": "速度未形成",
            "volume_expansion_speed": "速度未改善",
            "repair_quality_sync": "质量同步不足",
        },
    ),
]
DEFAULT_HORIZON_SELECTION_FACTOR_NAMES = [
    "market_decline_speed",
    "market_repair_speed_profile",
    "market_repair_quality_confirmation",
    "market_volume_expansion_speed",
    "market_tail_extreme",
    "decline_speed",
    "repair_speed_profile",
    "repair_quality_sync",
    "volume_expansion_speed",
    "weak_tail_extreme",
    "market_tail_repair_signal",
    "tail_repair_signal",
]
DEFAULT_HORIZON_STAGE_MIXED_PAIR_FACTORS = [
    ("market_repair_speed_profile", "market_volume_expansion_speed"),
    ("market_repair_speed_profile", "market_tail_extreme"),
    ("market_repair_speed_profile", "tail_repair_signal"),
    ("market_repair_speed_profile", "volume_expansion_speed"),
]
DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE = {
    "market_repair_speed_profile": "速度分化",
    "market_tail_extreme": "弱势低位",
}
DEFAULT_HORIZON_STAGE_DAILY_MARKET_CONTEXT_FACTORS = [
    "market_decline_speed",
    "market_tail_repair_signal",
    "market_repair_quality_confirmation",
    "market_volume_expansion_speed",
    "market_macd_repair_speed",
    "market_boll_recovery_speed",
]
DEFAULT_HORIZON_STAGE_DAILY_STOCK_CONTEXT_FACTORS = [
    "repair_quality_sync",
    "tail_repair_signal",
    "volume_expansion_speed",
    "macd_repair_speed",
    "boll_recovery_speed",
]
DEFAULT_REPAIR_BREADTH_STAGE_FOLD_FACTORS = [
    "market_decline_speed",
    "market_tail_repair_signal",
    "market_repair_quality_confirmation",
]
DEFAULT_REPAIR_BREADTH_CONTINUOUS_STAGE_FACTORS = [
    "market_volume_persistence",
    "market_macd_repair_persistence",
    "market_low_escape",
    "market_rebound_stretch",
    "volume_persistence",
    "macd_repair_persistence",
    "low_escape",
    "rebound_stretch",
]
DEFAULT_REPAIR_BREADTH_CONTINUOUS_COMBO_FACTORS = [
    ("market_volume_persistence", "market_rebound_stretch"),
    ("market_volume_persistence", "macd_repair_persistence"),
    ("market_rebound_stretch", "macd_repair_persistence"),
]
REPAIR_SPEED_IMPROVED_VALUES = {"速度温和改善", "速度改善明显"}
HORIZON_STAGE_LAG_RULES = [
    (
        "市场低位待确认",
        {"market_tail_repair_signal": "低位待确认"},
    ),
    (
        "市场跌速加快+低位修复确认",
        {"market_decline_speed": "跌速加快", "market_tail_repair_signal": "低位修复确认"},
    ),
    (
        "市场跌速加快+修复质量初步确认",
        {"market_decline_speed": "跌速加快", "market_repair_quality_confirmation": "修复质量初步确认"},
    ),
    (
        "市场修复质量未确认",
        {"market_repair_quality_confirmation": "修复质量未确认"},
    ),
]
HORIZON_STAGE_COUNTER_RULES = [
    (
        "市场跌速持平",
        {"market_decline_speed": "跌速持平"},
    ),
    (
        "市场速度共振明显",
        {"market_repair_speed_profile": "速度共振明显"},
    ),
    (
        "市场修复质量分化",
        {"market_repair_quality_confirmation": "修复质量分化"},
    ),
]
RESEARCH_REVIEW_STABLE_LAG_REASONS = {
    "市场跌速加快+低位修复确认",
    "市场修复质量未确认",
    "市场低位待确认",
}


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_scoring_item_from_series(
    code: str,
    name: str,
    series: list[dict[str, Any]],
    signal_index: int,
) -> dict[str, Any]:
    if signal_index < 0 or signal_index >= len(series):
        raise IndexError("signal_index 超出日线序列范围")
    visible_series = series[: signal_index + 1]
    snapshot = sfa.technical_snapshot_from_series(visible_series)
    trend = sfa.calculate_technical_trend(visible_series)
    return {
        "code": code,
        "name": name,
        "industry": "",
        "listed_at": "",
        "report_date": "",
        "overview": {},
        "valuation": {},
        "metrics": [],
        "technical": sfa.technical_to_jsonable(snapshot),
        "technical_trend": sfa.technical_trend_to_jsonable(trend),
        "strengths": ["历史研究模式只使用当时可见的技术与趋势数据"],
        "risks": ["历史基本面与实时估值未纳入本轮评分"],
        "source_errors": ["历史研究模式未使用实时估值和财务指标，避免未来函数"],
    }


def bucket_trend(days: int, return_pct: Any) -> str:
    value = number(return_pct)
    if value is None:
        return "未知"
    positive, negative = TREND_THRESHOLDS.get(days, (5, -5))
    if value >= positive:
        return "上涨"
    if value <= negative:
        return "下跌"
    return "震荡"


def bucket_market_trend(days: int, return_pct: Any) -> str:
    value = number(return_pct)
    if value is None:
        return "未知"
    positive, negative = MARKET_TREND_THRESHOLDS.get(days, (3, -3))
    if value >= positive:
        return "上涨"
    if value <= negative:
        return "下跌"
    return "震荡"


def decline_duration_state(
    r20: Any,
    r60: Any,
    r120: Any,
    thresholds: tuple[float, float, float],
) -> str:
    v20 = number(r20)
    v60 = number(r60)
    v120 = number(r120)
    t20, t60, t120 = thresholds
    if v20 is None or v60 is None:
        return "未知"
    short_down = v20 <= t20
    medium_down = v60 <= t60
    long_down = v120 is not None and v120 <= t120
    if short_down and medium_down and long_down:
        return "短中长期同步下跌"
    if short_down and medium_down:
        return "短中期同步下跌"
    if short_down:
        return "短期下跌"
    if v20 >= 0 and medium_down:
        return "短期修复中期仍弱"
    if v20 >= 0 and v60 >= 0:
        return "短中期非弱"
    return "混合"


def decline_speed_state(r20: Any, r60: Any) -> str:
    v20 = number(r20)
    v60 = number(r60)
    if v20 is None or v60 is None:
        return "未知"
    if v20 >= 0 and v60 < 0:
        return "短期修复"
    if v20 < 0 and v60 >= 0:
        return "短期转弱"
    if v20 >= 0 and v60 >= 0:
        return "非下跌"
    recent_rate = v20 / 20
    medium_rate = v60 / 60
    if recent_rate > medium_rate * 0.75:
        return "跌速放缓"
    if recent_rate < medium_rate * 1.25:
        return "跌速加快"
    return "跌速持平"


def weak_tail_extreme_state(boll_position: Any, rsi6: Any, kdj_j: Any) -> str:
    boll_text = str(boll_position or "")
    rsi_value = number(rsi6)
    j_value = number(kdj_j)
    if boll_text == "跌破下轨" or (rsi_value is not None and rsi_value <= 20) or (j_value is not None and j_value <= 0):
        return "极端超卖"
    if boll_text == "中轨下方" or (rsi_value is not None and rsi_value < 45) or (j_value is not None and j_value <= 20):
        return "弱势低位"
    if boll_text or rsi_value is not None or j_value is not None:
        return "常规"
    return "未知"


def volume_state_from_ratio(volume_ratio: Any) -> str:
    value = number(volume_ratio)
    if value is None:
        return "未知"
    if value >= 1.5:
        return "放量"
    if value <= 0.7:
        return "缩量"
    return "常规"


def tail_repair_signal_state(
    tail_extreme: str,
    macd_state: str,
    boll_position: Any,
    rsi6: Any,
    kdj_j: Any,
    volume_state: str,
) -> str:
    if tail_extreme == "未知":
        return "未知"
    if tail_extreme == "常规":
        return "常规"
    boll_text = str(boll_position or "")
    rsi_value = number(rsi6)
    j_value = number(kdj_j)
    oscillator_repair = (
        (bool(boll_text) and boll_text not in {"跌破下轨", "中轨下方"})
        or (rsi_value is not None and rsi_value >= 45)
        or (j_value is not None and j_value >= 20)
    )
    if macd_state == "多头" and volume_state == "放量":
        return "低位放量转强"
    if macd_state in {"多头", "转换"} and oscillator_repair:
        return "低位修复确认"
    if volume_state == "放量":
        return "低位放量未确认"
    if macd_state == "空头":
        return "低位空头延续"
    return "低位待确认"


def numeric_tail(series: list[dict[str, Any]], field: str, days: int) -> list[float]:
    values: list[float] = []
    for row in series[-days:]:
        value = number(row.get(field))
        if value is not None:
            values.append(value)
    return values


def consecutive_non_decreasing(values: list[float], min_steps: int = 3) -> bool:
    if len(values) < min_steps:
        return False
    recent = values[-min_steps:]
    return all(right >= left for left, right in zip(recent, recent[1:]))


def consecutive_non_increasing(values: list[float], min_steps: int = 3) -> bool:
    if len(values) < min_steps:
        return False
    recent = values[-min_steps:]
    return all(right <= left for left, right in zip(recent, recent[1:]))


def speed_bucket_from_votes(strong_votes: int, mild_votes: int, weak_votes: int) -> str:
    if strong_votes >= 2:
        return "速度改善明显"
    if strong_votes >= 1 or mild_votes >= 2:
        return "速度温和改善"
    if weak_votes >= 2:
        return "速度恶化"
    return "速度未改善"


def macd_repair_continuity_state(series: list[dict[str, Any]]) -> str:
    bars = numeric_tail(series, "macd_bar", 6)
    if len(bars) < 3:
        return "未知"
    latest = bars[-1]
    previous = bars[-2]
    crossed_up = latest > 0 and any(value <= 0 for value in bars[:-1])
    if crossed_up:
        return "MACD翻红"
    if latest < 0 and consecutive_non_decreasing(bars, 3):
        return "空头连续收敛"
    if latest < 0 and consecutive_non_increasing(bars, 3):
        return "空头继续扩散"
    if latest > 0 and latest >= previous:
        return "多头增强"
    if latest > 0:
        return "多头放缓"
    return "转换震荡"


def macd_repair_speed_state(series: list[dict[str, Any]]) -> str:
    bars = numeric_tail(series, "macd_bar", 10)
    if len(bars) < 4:
        return "未知"
    latest = bars[-1]
    previous = bars[-2]
    recent = bars[-6:]
    prior_low = min(recent[:-1])
    improvement = latest - prior_low
    scale = max(abs(prior_low), abs(latest), 0.05)
    improvement_ratio = improvement / scale
    strong_votes = sum(
        [
            latest > 0 and any(value <= 0 for value in recent[:-1]),
            consecutive_non_decreasing(bars, 4) and improvement_ratio >= 0.45,
            latest < 0 and improvement_ratio >= 0.65,
        ]
    )
    mild_votes = sum(
        [
            latest > previous,
            consecutive_non_decreasing(bars, 3),
            improvement_ratio >= 0.25,
        ]
    )
    weak_votes = sum(
        [
            latest < previous,
            consecutive_non_increasing(bars, 3),
            latest < 0 and latest <= prior_low,
        ]
    )
    return speed_bucket_from_votes(strong_votes, mild_votes, weak_votes)


def oscillator_rebound_continuity_state(series: list[dict[str, Any]], field: str, low_threshold: float) -> str:
    values = numeric_tail(series, field, 10)
    if len(values) < 3:
        return "未知"
    latest = values[-1]
    recent_low = min(values)
    was_low = recent_low <= low_threshold
    if was_low and latest >= low_threshold + 10 and consecutive_non_decreasing(values, 3):
        return "低位连续回升"
    if was_low and latest > recent_low and latest >= values[-2]:
        return "低位初步回升"
    if latest <= low_threshold:
        return "低位钝化"
    if consecutive_non_decreasing(values, 3):
        return "常规回升"
    return "常规"


def oscillator_rebound_speed_state(series: list[dict[str, Any]], field: str, low_threshold: float) -> str:
    values = numeric_tail(series, field, 10)
    if len(values) < 4:
        return "未知"
    latest = values[-1]
    previous = values[-2]
    recent_low = min(values)
    rebound = latest - recent_low
    was_low = recent_low <= low_threshold
    strong_votes = sum(
        [
            was_low and rebound >= 18,
            was_low and latest >= low_threshold + 10 and consecutive_non_decreasing(values, 3),
            latest >= previous + 8,
        ]
    )
    mild_votes = sum(
        [
            was_low and rebound >= 8,
            latest > previous,
            consecutive_non_decreasing(values, 3),
        ]
    )
    weak_votes = sum(
        [
            latest <= low_threshold,
            latest <= previous,
            rebound <= 3,
        ]
    )
    return speed_bucket_from_votes(strong_votes, mild_votes, weak_votes)


def boll_recovery_continuity_state(series: list[dict[str, Any]]) -> str:
    positions = [str(row.get("boll_position") or "") for row in series[-10:]]
    positions = [item for item in positions if item]
    if not positions:
        return "未知"
    latest = positions[-1]
    was_below_lower = "跌破下轨" in positions[:-1]
    was_below_mid = any(item in {"跌破下轨", "中轨下方"} for item in positions[:-1])
    if was_below_mid and latest == "中轨上方":
        return "重新站上中轨"
    if was_below_lower and latest != "跌破下轨":
        return "重新站回下轨内"
    if latest == "跌破下轨":
        return "仍跌破下轨"
    if latest == "中轨下方":
        return "仍在中轨下方"
    return "常规"


def trailing_count(values: list[str], predicate: Any) -> int:
    count = 0
    for value in reversed(values):
        if not predicate(value):
            break
        count += 1
    return count


def boll_recovery_speed_state(series: list[dict[str, Any]]) -> str:
    positions = [str(row.get("boll_position") or "") for row in series[-10:]]
    positions = [item for item in positions if item]
    if len(positions) < 3:
        return "未知"
    latest = positions[-1]
    not_lower_days = trailing_count(positions, lambda value: value != "跌破下轨")
    above_mid_days = trailing_count(positions, lambda value: value == "中轨上方")
    was_below_lower = "跌破下轨" in positions[:-1]
    was_below_mid = any(item in {"跌破下轨", "中轨下方"} for item in positions[:-1])
    strong_votes = sum(
        [
            latest == "中轨上方" and was_below_mid,
            above_mid_days >= 3,
            was_below_lower and not_lower_days >= 4,
        ]
    )
    mild_votes = sum(
        [
            latest != "跌破下轨" and was_below_lower,
            not_lower_days >= 3,
            latest == "中轨上方",
        ]
    )
    weak_votes = sum(
        [
            latest == "跌破下轨",
            latest == "中轨下方" and not_lower_days <= 2,
            not_lower_days <= 1,
        ]
    )
    return speed_bucket_from_votes(strong_votes, mild_votes, weak_votes)


def volume_continuity_state(series: list[dict[str, Any]]) -> str:
    ratios = numeric_tail(series, "volume_ratio_5", 5)
    if len(ratios) < 3:
        return "未知"
    recent3 = ratios[-3:]
    if sum(1 for value in recent3 if value >= 1.2) >= 3:
        return "连续温和放量"
    if sum(1 for value in recent3 if value >= 1.5) >= 2:
        return "连续明显放量"
    if ratios[-1] >= 1.5:
        return "单日放量"
    if sum(1 for value in recent3 if value <= 0.7) >= 2:
        return "连续缩量"
    return "常规"


def volume_expansion_speed_state(series: list[dict[str, Any]]) -> str:
    ratios = numeric_tail(series, "volume_ratio_5", 6)
    if len(ratios) < 3:
        return "未知"
    latest = ratios[-1]
    previous = ratios[-2]
    recent3 = ratios[-3:]
    strong_votes = sum(
        [
            latest >= 1.5,
            sum(1 for value in recent3 if value >= 1.2) >= 3,
            consecutive_non_decreasing(ratios, 3) and latest >= 1.2,
        ]
    )
    mild_votes = sum(
        [
            latest >= 1.2,
            latest > previous,
            sum(1 for value in recent3 if value >= 1.0) >= 2,
        ]
    )
    weak_votes = sum(
        [
            latest <= 0.8,
            latest <= previous,
            sum(1 for value in recent3 if value <= 0.7) >= 2,
        ]
    )
    return speed_bucket_from_votes(strong_votes, mild_votes, weak_votes)


def volume_persistence_state(series: list[dict[str, Any]]) -> str:
    ratios = numeric_tail(series, "volume_ratio_5", 8)
    if len(ratios) < 4:
        return "未知"
    recent5 = ratios[-5:]
    strong_days = sum(1 for value in recent5 if value >= 1.2)
    mild_days = sum(1 for value in recent5 if value >= 1.0)
    weak_days = sum(1 for value in recent5 if value <= 0.8)
    latest = ratios[-1]
    if strong_days >= 4:
        return "量能持续改善"
    if strong_days >= 2 and latest >= 1.2:
        return "量能改善延续"
    if mild_days >= 3 and latest >= 1.0:
        return "量能温和维持"
    if weak_days >= 3:
        return "量能持续不足"
    return "量能脉冲不连续"


def macd_repair_persistence_state(series: list[dict[str, Any]]) -> str:
    bars = numeric_tail(series, "macd_bar", 8)
    if len(bars) < 4:
        return "未知"
    recent = bars[-6:]
    latest = recent[-1]
    improving_steps = sum(1 for left, right in zip(recent, recent[1:]) if right >= left)
    deteriorating_steps = sum(1 for left, right in zip(recent, recent[1:]) if right < left)
    positive_days = sum(1 for value in recent if value > 0)
    if positive_days >= 4 and improving_steps >= 3:
        return "MACD多头持续"
    if improving_steps >= 5:
        return "MACD连续改善"
    if improving_steps >= 3 and latest > min(recent[:-1]):
        return "MACD改善不连续"
    if deteriorating_steps >= 4:
        return "MACD持续恶化"
    return "MACD震荡"


def low_escape_state(series: list[dict[str, Any]]) -> str:
    closes = numeric_tail(series, "close", 60)
    if len(closes) < 20:
        return "未知"
    latest = closes[-1]
    recent_low = min(closes)
    if recent_low <= 0:
        return "未知"
    distance_pct = (latest / recent_low - 1) * 100
    if distance_pct <= 3:
        return "仍贴近低点"
    if distance_pct <= 8:
        return "低位小幅脱离"
    if distance_pct <= 15:
        return "低位明显脱离"
    return "脱离低位较远"


def rebound_stretch_state(series: list[dict[str, Any]]) -> str:
    closes = numeric_tail(series, "close", 21)
    if len(closes) < 21:
        return "未知"
    latest = closes[-1]
    prior = closes[0]
    recent_low = min(closes)
    if prior <= 0 or recent_low <= 0:
        return "未知"
    return_20d = (latest / prior - 1) * 100
    low_distance_pct = (latest / recent_low - 1) * 100
    if return_20d >= 8 or low_distance_pct >= 15:
        return "20日反弹过度伸展"
    if return_20d >= 4 or low_distance_pct >= 8:
        return "20日反弹明显"
    if return_20d >= 0 and low_distance_pct >= 4:
        return "20日修复温和"
    if return_20d <= -5:
        return "20日仍下跌"
    return "20日修复不足"


def repair_continuity_state(factors: dict[str, str]) -> str:
    macd = factors.get("macd_repair_continuity") or "未知"
    rsi = factors.get("rsi_rebound_continuity") or "未知"
    kdj = factors.get("kdj_rebound_continuity") or "未知"
    boll = factors.get("boll_recovery_continuity") or "未知"
    volume = factors.get("volume_continuity") or "未知"
    repair_votes = sum(
        [
            macd in {"MACD翻红", "空头连续收敛", "多头增强"},
            rsi in {"低位连续回升", "低位初步回升"},
            kdj in {"低位连续回升", "低位初步回升"},
            boll in {"重新站上中轨", "重新站回下轨内"},
        ]
    )
    weak_votes = sum(
        [
            macd == "空头继续扩散",
            rsi == "低位钝化",
            kdj == "低位钝化",
            boll in {"仍跌破下轨", "仍在中轨下方"},
        ]
    )
    if repair_votes >= 3:
        return "连续修复确认"
    if repair_votes >= 2 and volume in {"连续明显放量", "连续温和放量", "单日放量"}:
        return "放量修复确认"
    if weak_votes >= 3:
        return "弱势延续确认"
    if repair_votes >= 2:
        return "修复初步形成"
    if weak_votes >= 2:
        return "弱势仍未修复"
    return "修复信号不足"


def repair_speed_state(factors: dict[str, str]) -> str:
    macd = factors.get("macd_repair_continuity") or "未知"
    rsi = factors.get("rsi_rebound_continuity") or "未知"
    kdj = factors.get("kdj_rebound_continuity") or "未知"
    boll = factors.get("boll_recovery_continuity") or "未知"
    volume = factors.get("volume_continuity") or "未知"
    continuity = factors.get("repair_continuity") or "未知"
    fast_votes = sum(
        [
            macd in {"MACD翻红", "多头增强"},
            rsi == "低位连续回升",
            kdj == "低位连续回升",
            boll == "重新站上中轨",
            volume in {"连续明显放量", "连续温和放量", "单日放量"},
        ]
    )
    gradual_votes = sum(
        [
            macd in {"空头连续收敛", "多头放缓"},
            rsi == "低位初步回升",
            kdj == "低位初步回升",
            boll == "重新站回下轨内",
        ]
    )
    weak_votes = sum(
        [
            macd == "空头继续扩散",
            rsi == "低位钝化",
            kdj == "低位钝化",
            boll in {"仍跌破下轨", "仍在中轨下方"},
        ]
    )
    if continuity == "连续修复确认" and fast_votes >= 4:
        return "快速修复确认"
    if continuity in {"连续修复确认", "放量修复确认"} and fast_votes >= 3:
        return "快速修复形成"
    if continuity in {"修复初步形成", "放量修复确认", "连续修复确认"} and gradual_votes >= 2:
        return "渐进修复"
    if continuity in {"弱势延续确认", "弱势仍未修复"} or weak_votes >= 3:
        return "修复未确认"
    if continuity == "未知":
        return "未知"
    return "修复速度不明"


def repair_speed_profile_state(factors: dict[str, str]) -> str:
    speed_values = [
        factors.get("macd_repair_speed"),
        factors.get("rsi_rebound_speed"),
        factors.get("kdj_rebound_speed"),
        factors.get("boll_recovery_speed"),
        factors.get("volume_expansion_speed"),
    ]
    known = [value for value in speed_values if value and value != "未知"]
    if len(known) < 3:
        return "未知"
    strong = sum(1 for value in known if value == "速度改善明显")
    mild = sum(1 for value in known if value == "速度温和改善")
    weak = sum(1 for value in known if value == "速度未改善")
    worse = sum(1 for value in known if value == "速度恶化")
    if strong >= 3:
        return "速度共振明显"
    if strong >= 2 and mild >= 1:
        return "速度共振偏强"
    if strong + mild >= 3 and worse == 0:
        return "速度温和共振"
    if worse >= 2 or weak + worse >= 4:
        return "速度未形成"
    return "速度分化"


def repair_quality_confirmation_state(factors: dict[str, str], prefix: str = "") -> str:
    tail_repair = factors.get(f"{prefix}tail_repair_signal") or "未知"
    volume_speed = factors.get(f"{prefix}volume_expansion_speed") or "未知"
    macd_speed = factors.get(f"{prefix}macd_repair_speed") or "未知"
    boll_speed = factors.get(f"{prefix}boll_recovery_speed") or "未知"
    decline_speed = factors.get(f"{prefix}decline_speed") or "未知"
    speed_profile = factors.get(f"{prefix}repair_speed_profile") or "未知"

    repair_confirmed = tail_repair in {"低位修复确认", "低位放量转强"}
    volume_confirmed = volume_speed in {"速度改善明显", "速度温和改善"}
    macd_not_worse = macd_speed != "速度恶化"
    boll_not_worse = boll_speed != "速度恶化"
    decline_decelerating = decline_speed in {"跌速放缓", "短期修复", "非下跌"}
    speed_confirmed = speed_profile in {"速度共振明显", "速度共振偏强", "速度温和共振"}

    risk_votes = sum(
        [
            tail_repair == "低位放量未确认",
            volume_speed == "速度恶化",
            macd_speed == "速度恶化",
            boll_speed == "速度恶化",
            decline_speed in {"跌速加快", "跌速持平"},
            speed_profile in {"速度未形成", "速度分化"},
        ]
    )
    confirm_votes = sum(
        [
            repair_confirmed,
            volume_confirmed,
            macd_not_worse,
            boll_not_worse,
            decline_decelerating,
            speed_confirmed,
        ]
    )
    if tail_repair == "未知" and speed_profile == "未知":
        return "未知"
    if repair_confirmed and volume_confirmed and macd_not_worse and decline_decelerating:
        return "修复质量确认"
    if repair_confirmed and confirm_votes >= 4 and risk_votes <= 1:
        return "修复质量初步确认"
    if risk_votes >= 3 or (tail_repair == "低位放量未确认" and volume_speed == "速度恶化"):
        return "修复质量恶化"
    if risk_votes >= 2:
        return "修复质量未确认"
    return "修复质量分化"


def repair_quality_sync_state(factors: dict[str, str]) -> str:
    market_quality = factors.get("market_repair_quality_confirmation") or "未知"
    stock_quality = factors.get("repair_quality_confirmation") or "未知"
    positive = {"修复质量确认", "修复质量初步确认"}

    market_positive = market_quality in positive
    stock_positive = stock_quality in positive
    market_worse = market_quality == "修复质量恶化"
    stock_worse = stock_quality == "修复质量恶化"

    if market_quality == "未知" and stock_quality == "未知":
        return "未知"
    if market_worse and stock_worse:
        return "双侧质量恶化"
    if (market_positive and stock_worse) or (stock_positive and market_worse):
        return "单侧确认对侧恶化"
    if market_positive and stock_positive:
        return "双侧质量同步确认"
    if market_positive and stock_quality != "未知":
        return "市场确认个股不恶化"
    if stock_positive and market_quality != "未知":
        return "个股确认市场不恶化"
    return "质量同步不足"


def continuous_repair_factor_tags_from_series(series: list[dict[str, Any]], prefix: str = "") -> dict[str, str]:
    if not series:
        return {
            f"{prefix}macd_repair_continuity": "未知",
            f"{prefix}rsi_rebound_continuity": "未知",
            f"{prefix}kdj_rebound_continuity": "未知",
            f"{prefix}boll_recovery_continuity": "未知",
            f"{prefix}volume_continuity": "未知",
            f"{prefix}repair_continuity": "未知",
            f"{prefix}repair_speed": "未知",
            f"{prefix}macd_repair_speed": "未知",
            f"{prefix}rsi_rebound_speed": "未知",
            f"{prefix}kdj_rebound_speed": "未知",
            f"{prefix}boll_recovery_speed": "未知",
            f"{prefix}volume_expansion_speed": "未知",
            f"{prefix}repair_speed_profile": "未知",
            f"{prefix}volume_persistence": "未知",
            f"{prefix}macd_repair_persistence": "未知",
            f"{prefix}low_escape": "未知",
            f"{prefix}rebound_stretch": "未知",
        }
    base = {
        "macd_repair_continuity": macd_repair_continuity_state(series),
        "rsi_rebound_continuity": oscillator_rebound_continuity_state(series, "rsi6", 30),
        "kdj_rebound_continuity": oscillator_rebound_continuity_state(series, "kdj_j", 20),
        "boll_recovery_continuity": boll_recovery_continuity_state(series),
        "volume_continuity": volume_continuity_state(series),
        "macd_repair_speed": macd_repair_speed_state(series),
        "rsi_rebound_speed": oscillator_rebound_speed_state(series, "rsi6", 30),
        "kdj_rebound_speed": oscillator_rebound_speed_state(series, "kdj_j", 20),
        "boll_recovery_speed": boll_recovery_speed_state(series),
        "volume_expansion_speed": volume_expansion_speed_state(series),
        "volume_persistence": volume_persistence_state(series),
        "macd_repair_persistence": macd_repair_persistence_state(series),
        "low_escape": low_escape_state(series),
        "rebound_stretch": rebound_stretch_state(series),
    }
    base["repair_continuity"] = repair_continuity_state(base)
    base["repair_speed"] = repair_speed_state(base)
    base["repair_speed_profile"] = repair_speed_profile_state(base)
    return {f"{prefix}{name}": value for name, value in base.items()}


def horizon_alignment(horizons: dict[str, Any]) -> str:
    short = number((horizons.get("short_term") or {}).get("score"))
    medium = number((horizons.get("medium_term") or {}).get("score"))
    long = number((horizons.get("long_term") or {}).get("score"))
    scores = [score for score in [short, medium, long] if score is not None]
    if len(scores) != 3:
        return "未知"
    if short >= 15 and medium >= 15 and long >= 15:
        return "三周期同向偏多"
    if short <= -15 and medium <= -15 and long <= -15:
        return "三周期同向偏空"
    if short >= 15 and medium < 15 and long < 15:
        return "短期偏多中长期不足"
    if short < 15 and medium >= 15 and long >= 15:
        return "中长期偏多短期观望"
    return "周期分歧"


def trend_return(windows: dict[int, dict[str, Any]], days: int) -> float | None:
    return number((windows.get(days) or {}).get("return_pct"))


def macd_state_from_values(macd_bar: Any, dif: Any, dea: Any) -> str:
    bar = number(macd_bar)
    dif_value = number(dif)
    dea_value = number(dea)
    if bar is None or dif_value is None or dea_value is None:
        return "未知"
    if bar > 0 and dif_value > dea_value:
        return "多头"
    if bar < 0 and dif_value < dea_value:
        return "空头"
    return "转换"


def classify_refined_market_regime(result: dict[str, Any]) -> str:
    raw = result.get("raw") or {}
    technical = raw.get("technical") or {}
    trend = raw.get("technical_trend") or {}
    windows = {int(window.get("days")): window for window in trend.get("windows", []) if window.get("days") is not None}

    r20 = trend_return(windows, 20)
    r60 = trend_return(windows, 60)
    r120 = trend_return(windows, 120)
    r250 = trend_return(windows, 250)

    long_weak = (r120 is not None and r120 <= -15) or (r250 is not None and r250 <= -20)
    short_repair = (
        (r20 is not None and r20 >= 5 and (r60 is None or r60 >= 0))
        or (r60 is not None and r60 >= 10 and (r20 is None or r20 >= 0))
    )
    if long_weak and short_repair:
        return "downtrend_repair"

    if (
        r20 is not None
        and r20 <= -5
        and r60 is not None
        and r60 <= -10
        and ((r120 is not None and r120 <= -15) or (r250 is not None and r250 <= -20))
    ):
        return "bear_continuation"

    if r60 is not None and r60 >= 10 and r120 is not None and r120 >= 15 and (r250 is None or r250 >= 20):
        return "trend_extension"

    boll = technical.get("boll") or {}
    kdj = technical.get("kdj") or {}
    rsi = technical.get("rsi") or {}
    macd = technical.get("macd") or {}
    boll_position = str(boll.get("position") or "")
    rsi6 = number(rsi.get("rsi6"))
    j_value = number(kdj.get("j"))
    macd_bar = number(macd.get("bar"))
    has_repair_indicator = (
        boll_position in {"跌破下轨", "中轨下方"}
        or (rsi6 is not None and rsi6 <= 45)
        or (j_value is not None and j_value <= 20)
    )
    has_rebound_confirmation = (r20 is not None and r20 >= 0) or (macd_bar is not None and macd_bar > 0)
    not_strong_trend = not (
        r60 is not None and r60 >= 10 and r120 is not None and r120 >= 15
    )
    if has_repair_indicator and has_rebound_confirmation and not_strong_trend:
        return "range_rebound"

    return str(result.get("regime") or "unknown")


def classify_market_regime(windows: dict[int, dict[str, Any]], latest: dict[str, Any] | None = None) -> str:
    latest = latest or {}
    r20 = trend_return(windows, 20)
    r60 = trend_return(windows, 60)
    r120 = trend_return(windows, 120)
    r250 = trend_return(windows, 250)

    long_weak = (r120 is not None and r120 <= -10) or (r250 is not None and r250 <= -15)
    short_repair = (
        (r20 is not None and r20 >= 3 and (r60 is None or r60 >= 0))
        or (r60 is not None and r60 >= 6 and (r20 is None or r20 >= 0))
    )
    if long_weak and short_repair:
        return "market_bear_rebound"

    if (
        r20 is not None
        and r20 <= -3
        and r60 is not None
        and r60 <= -6
        and ((r120 is not None and r120 <= -10) or (r250 is not None and r250 <= -15))
    ):
        return "market_bear_continuation"

    if r60 is not None and r60 >= 6 and r120 is not None and r120 >= 10 and (r250 is None or r250 >= 15):
        return "market_bull_extension"

    boll_position = str(latest.get("boll_position") or "")
    rsi6 = number(latest.get("rsi6"))
    j_value = number(latest.get("kdj_j"))
    macd_bar = number(latest.get("macd_bar"))
    has_repair_indicator = (
        boll_position in {"跌破下轨", "中轨下方"}
        or (rsi6 is not None and rsi6 <= 45)
        or (j_value is not None and j_value <= 20)
    )
    has_rebound_confirmation = (r20 is not None and r20 >= 0) or (macd_bar is not None and macd_bar > 0)
    not_strong_trend = not (r60 is not None and r60 >= 6 and r120 is not None and r120 >= 10)
    if has_repair_indicator and has_rebound_confirmation and not_strong_trend:
        return "market_range_rebound"

    if r20 is not None and r60 is not None and r20 < 0 and r60 < 0:
        return "market_downtrend"
    if r20 is not None and r60 is not None and r20 >= 0 and r60 >= 0:
        return "market_trend"
    if r20 is not None or r60 is not None:
        return "market_range"
    return "market_unknown"


def market_factor_tags_from_visible_series(
    visible_series: list[dict[str, Any]],
    benchmark_index: str,
) -> dict[str, str]:
    if not visible_series:
        return {
            "benchmark_index": benchmark_index,
            "market_regime": "market_unknown",
            "market_trend_20d": "未知",
            "market_trend_60d": "未知",
            "market_trend_120d": "未知",
            "market_trend_250d": "未知",
            "market_macd_state": "未知",
            "market_decline_duration": "未知",
            "market_decline_speed": "未知",
            "market_tail_extreme": "未知",
            "market_tail_repair_signal": "未知",
            "market_volume_state": "未知",
            "market_macd_repair_continuity": "未知",
            "market_rsi_rebound_continuity": "未知",
            "market_kdj_rebound_continuity": "未知",
            "market_boll_recovery_continuity": "未知",
            "market_volume_continuity": "未知",
            "market_repair_continuity": "未知",
            "market_repair_speed": "未知",
            "market_macd_repair_speed": "未知",
            "market_rsi_rebound_speed": "未知",
            "market_kdj_rebound_speed": "未知",
            "market_boll_recovery_speed": "未知",
            "market_volume_expansion_speed": "未知",
            "market_repair_speed_profile": "未知",
            "market_repair_quality_confirmation": "未知",
        }

    trend = sfa.calculate_technical_trend(visible_series)
    latest = visible_series[-1]
    windows = {int(window.days): {"return_pct": window.return_pct} for window in trend.windows}
    factors = {
        "benchmark_index": benchmark_index,
        "market_regime": classify_market_regime(windows, latest),
        "market_macd_state": macd_state_from_values(
            latest.get("macd_bar"),
            latest.get("macd_dif"),
            latest.get("macd_dea"),
        ),
    }
    for days in [20, 60, 120, 250]:
        factors[f"market_trend_{days}d"] = bucket_market_trend(days, (windows.get(days) or {}).get("return_pct"))
    factors["market_decline_duration"] = decline_duration_state(
        (windows.get(20) or {}).get("return_pct"),
        (windows.get(60) or {}).get("return_pct"),
        (windows.get(120) or {}).get("return_pct"),
        (-3, -6, -10),
    )
    factors["market_decline_speed"] = decline_speed_state(
        (windows.get(20) or {}).get("return_pct"),
        (windows.get(60) or {}).get("return_pct"),
    )
    factors["market_tail_extreme"] = weak_tail_extreme_state(
        latest.get("boll_position"),
        latest.get("rsi6"),
        latest.get("kdj_j"),
    )
    factors["market_volume_state"] = volume_state_from_ratio(latest.get("volume_ratio_5"))
    factors["market_tail_repair_signal"] = tail_repair_signal_state(
        factors["market_tail_extreme"],
        factors["market_macd_state"],
        latest.get("boll_position"),
        latest.get("rsi6"),
        latest.get("kdj_j"),
        factors["market_volume_state"],
    )
    factors.update(continuous_repair_factor_tags_from_series(visible_series, prefix="market_"))
    factors["market_repair_quality_confirmation"] = repair_quality_confirmation_state(factors, prefix="market_")
    return factors


def parsed_series_dates(series: list[dict[str, Any]]) -> list[dt.date]:
    dates = []
    for row in series:
        parsed = sfa.parse_date_like(row.get("date"))
        if parsed is None:
            raise ValueError(f"指数日线日期不可解析：{row.get('date')}")
        dates.append(parsed)
    return dates


def visible_series_as_of(
    series: list[dict[str, Any]],
    dates: list[dt.date],
    as_of_date: Any,
) -> list[dict[str, Any]]:
    parsed = sfa.parse_date_like(as_of_date)
    if parsed is None:
        return []
    end_index = bisect_right(dates, parsed)
    return series[:end_index]


def extract_factor_tags(result: dict[str, Any]) -> dict[str, str]:
    raw = result.get("raw") or {}
    technical = raw.get("technical") or {}
    trend = raw.get("technical_trend") or {}
    macd = technical.get("macd") or {}
    boll = technical.get("boll") or {}
    kdj = technical.get("kdj") or {}
    rsi = technical.get("rsi") or {}

    macd_state = macd_state_from_values(macd.get("bar"), macd.get("dif"), macd.get("dea"))

    j_value = number(kdj.get("j"))
    if j_value is None:
        kdj_j_zone = "未知"
    elif j_value >= 100:
        kdj_j_zone = "过热"
    elif j_value >= 80:
        kdj_j_zone = "偏高"
    elif j_value <= 0:
        kdj_j_zone = "超卖"
    else:
        kdj_j_zone = "常规"

    rsi6 = number(rsi.get("rsi6"))
    if rsi6 is None:
        rsi6_zone = "未知"
    elif rsi6 >= 80:
        rsi6_zone = "过热"
    elif rsi6 > 65:
        rsi6_zone = "偏热"
    elif rsi6 <= 20:
        rsi6_zone = "超卖"
    elif rsi6 < 45:
        rsi6_zone = "偏弱"
    else:
        rsi6_zone = "常规"

    volume_state = volume_state_from_ratio(technical.get("volume_ratio_5"))

    windows = {int(window.get("days")): window for window in trend.get("windows", []) if window.get("days") is not None}
    factors = {
        "regime": str(result.get("regime") or "unknown"),
        "refined_regime": classify_refined_market_regime(result),
        "macd_state": macd_state,
        "boll_position": str(boll.get("position") or "未知"),
        "kdj_j_zone": kdj_j_zone,
        "rsi6_zone": rsi6_zone,
        "volume_state": volume_state,
        "horizon_alignment": horizon_alignment(result.get("horizon_scores") or {}),
        "weak_tail_extreme": weak_tail_extreme_state(boll.get("position"), rsi.get("rsi6"), kdj.get("j")),
    }
    factors["tail_repair_signal"] = tail_repair_signal_state(
        factors["weak_tail_extreme"],
        macd_state,
        boll.get("position"),
        rsi.get("rsi6"),
        kdj.get("j"),
        volume_state,
    )
    for days in [20, 60, 120, 250]:
        factors[f"trend_{days}d"] = bucket_trend(days, (windows.get(days) or {}).get("return_pct"))
    factors["decline_duration"] = decline_duration_state(
        (windows.get(20) or {}).get("return_pct"),
        (windows.get(60) or {}).get("return_pct"),
        (windows.get(120) or {}).get("return_pct"),
        (-5, -10, -15),
    )
    factors["decline_speed"] = decline_speed_state(
        (windows.get(20) or {}).get("return_pct"),
        (windows.get(60) or {}).get("return_pct"),
    )
    return factors


def evaluate_result_windows(
    result: dict[str, Any],
    series: list[dict[str, Any]],
    signal_index: int,
    extra_factors: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    signal_row = series[signal_index]
    signal_close = number(signal_row.get("close"))
    if signal_close in (None, 0):
        return []

    outcomes: list[dict[str, Any]] = []
    horizons = result.get("horizon_scores") or {}
    factors = extract_factor_tags(result)
    if extra_factors:
        factors.update(extra_factors)
    factors.update(continuous_repair_factor_tags_from_series(series[: signal_index + 1]))
    if factors.get("market_regime") and factors.get("refined_regime"):
        factors["market_refined_regime"] = f"{factors['market_regime']}|{factors['refined_regime']}"
    factors["repair_quality_confirmation"] = repair_quality_confirmation_state(factors)
    factors["market_repair_quality_confirmation"] = repair_quality_confirmation_state(factors, prefix="market_")
    factors["repair_quality_sync"] = repair_quality_sync_state(factors)
    stage_classification = horizon_stage_classifier(factors)
    factors["horizon_stage_category"] = str(stage_classification.get("category") or "未知")
    factors["horizon_stage_reason"] = str(stage_classification.get("primary_reason") or "未知")
    for horizon, windows in signal_accuracy.HORIZON_WINDOWS.items():
        score_info = horizons.get(horizon) or {}
        signal_score = score_info.get("score")
        signal_label = score_info.get("signal")
        for window_days in windows:
            target_index = signal_index + window_days
            if target_index >= len(series):
                continue
            target_row = series[target_index]
            target_close = number(target_row.get("close"))
            if target_close is None:
                continue
            future_rows = series[signal_index + 1 : target_index + 1]
            future_closes = [number(row.get("close")) for row in future_rows]
            valid_closes = [close for close in future_closes if close is not None]
            return_pct = (target_close / signal_close - 1) * 100
            drawdowns = [(close / signal_close - 1) * 100 for close in valid_closes]
            outcome = {
                "stock_code": str(result.get("code") or ""),
                "stock_name": str(result.get("name") or ""),
                "regime": result.get("regime"),
                "refined_regime": factors.get("refined_regime"),
                "market_regime": factors.get("market_regime"),
                "horizon": horizon,
                "window_days": window_days,
                "signal_trade_date": signal_row.get("date"),
                "target_trade_date": target_row.get("date"),
                "signal_score": signal_score,
                "signal_label": signal_label,
                "signal_close": signal_close,
                "target_close": target_close,
                "return_pct": return_pct,
                "max_drawdown_pct": min(drawdowns) if drawdowns else None,
                "max_runup_pct": max(drawdowns) if drawdowns else None,
                "hit": signal_accuracy.classify_hit(signal_label, return_pct),
                "factors": factors,
            }
            review = research_review_layer_label(outcome)
            outcome.update(
                {
                    "review_layer_label": review["label"],
                    "review_layer_action": review["action"],
                    "review_layer_confidence": review["confidence"],
                    "review_layer_evidence_level": review["evidence_level"],
                    "review_layer_reasons": review["reasons"],
                }
            )
            outcomes.append(outcome)
    return outcomes


def average(values: Iterable[Any]) -> float | None:
    numeric_values = [value for item in values if (value := number(item)) is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def pct(value: Any) -> str:
    numeric = number(value)
    if numeric is None:
        return "暂无"
    return f"{numeric:.2f}%"


def decimal(value: Any) -> str:
    numeric = number(value)
    if numeric is None:
        return "暂无"
    return f"{numeric:.2f}"


def clamp_score(value: Any) -> int:
    numeric = number(value) or 0
    return max(-100, min(100, round(numeric)))


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


def signal_side(outcome: dict[str, Any]) -> str:
    score = number(outcome.get("signal_score"))
    label = str(outcome.get("signal_label") or "")
    if score is not None:
        if score >= 15:
            return "buy_bias"
        if score <= -15:
            return "sell_avoid"
        return "watch"
    if "买" in label:
        return "buy_bias"
    if "卖" in label or "回避" in label:
        return "sell_avoid"
    return "watch"


def research_review_layer_label(outcome: dict[str, Any]) -> dict[str, Any]:
    factors = outcome.get("factors") or {}
    side = signal_side(outcome)
    horizon = str(outcome.get("horizon") or "")
    window_days = int(outcome.get("window_days") or 0)
    category = str(factors.get("horizon_stage_category") or "")
    reason = str(factors.get("horizon_stage_reason") or "")
    market_volume_state = str(
        factors.get("market_volume_persistence") or factors.get("market_volume_expansion_speed") or ""
    )
    stock_macd_state = str(factors.get("macd_repair_persistence") or factors.get("macd_repair_speed") or "")

    if side != "sell_avoid":
        return {
            "label": "no_review_signal",
            "action": "keep_original_review",
            "confidence": "none",
            "evidence_level": "none",
            "reasons": ["非卖出/回避方向，不触发弱势尾部复核层"],
        }

    reasons: list[str] = []
    if category:
        reasons.append(category)
    if reason:
        reasons.append(reason)

    if category == "60日滞后优先复核" and reason in RESEARCH_REVIEW_STABLE_LAG_REASONS:
        action = "downgrade_to_watch_review" if horizon == "long_term" and window_days == 60 else "review_only"
        return {
            "label": "weak_tail_60d_lag_priority",
            "action": action,
            "confidence": "high" if action == "downgrade_to_watch_review" else "medium",
            "evidence_level": "cross_period_review",
            "reasons": reasons or ["命中弱势尾部 60 日滞后优先复核线"],
        }

    if (
        market_volume_state in REPAIR_SPEED_IMPROVED_VALUES | {"连续改善", "持续改善"}
        and stock_macd_state in REPAIR_SPEED_IMPROVED_VALUES | {"连续改善", "持续改善"}
    ):
        return {
            "label": "market_volume_stock_macd_repair_review",
            "action": "review_only",
            "confidence": "medium",
            "evidence_level": "conflicting_cross_period_review",
            "reasons": reasons + ["市场量能与个股 MACD 同步修复，保持复核不自动调分"],
        }

    if category in {"冲突继续复核", "反例口袋继续复核", "混合继续复核"}:
        return {
            "label": "mixed_review_only",
            "action": "review_only",
            "confidence": "low",
            "evidence_level": "mixed_or_counterexample_review",
            "reasons": reasons or ["阶段证据混合，保持人工复核"],
        }

    return {
        "label": "no_review_signal",
        "action": "keep_original_review",
        "confidence": "none",
        "evidence_level": "none",
        "reasons": reasons or ["未命中研究复核层"],
    }


def review_layer_info(outcome: dict[str, Any]) -> dict[str, Any]:
    label = outcome.get("review_layer_label")
    if label:
        return {
            "label": label,
            "action": outcome.get("review_layer_action") or "keep_original_review",
            "confidence": outcome.get("review_layer_confidence") or "none",
            "evidence_level": outcome.get("review_layer_evidence_level") or "none",
            "reasons": outcome.get("review_layer_reasons") or [],
        }
    return research_review_layer_label(outcome)


def adjusted_outcome_for_review_layer(outcome: dict[str, Any]) -> dict[str, Any]:
    adjusted = dict(outcome)
    review = review_layer_info(outcome)
    adjusted["review_layer_label"] = review["label"]
    adjusted["review_layer_action"] = review["action"]
    adjusted["review_layer_confidence"] = review["confidence"]
    adjusted["review_layer_evidence_level"] = review["evidence_level"]
    adjusted["review_layer_reasons"] = review["reasons"]
    if review["action"] != "downgrade_to_watch_review" or signal_side(outcome) != "sell_avoid":
        return adjusted
    adjusted_score = max(clamp_score(outcome.get("signal_score")), -14)
    adjusted_label = signal_label(adjusted_score)
    adjusted["signal_score"] = adjusted_score
    adjusted["signal_label"] = adjusted_label
    adjusted["hit"] = signal_accuracy.classify_hit(adjusted_label, outcome.get("return_pct"))
    return adjusted


def summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    directional = [item for item in items if item.get("hit") is not None]
    high_intensity = [item for item in items if abs(number(item.get("signal_score")) or 0) >= 70]
    high_directional = [item for item in high_intensity if item.get("hit") is not None]
    hits = [item for item in directional if item.get("hit") is True]
    high_hits = [item for item in high_directional if item.get("hit") is True]
    return {
        "sample_count": len(items),
        "directional_count": len(directional),
        "high_intensity_count": len(high_intensity),
        "hit_rate_pct": len(hits) / len(directional) * 100 if directional else None,
        "high_intensity_hit_rate_pct": len(high_hits) / len(high_directional) * 100 if high_directional else None,
        "avg_return_pct": average(item.get("return_pct") for item in items),
        "avg_max_drawdown_pct": average(item.get("max_drawdown_pct") for item in items),
        "avg_max_runup_pct": average(item.get("max_runup_pct") for item in items),
    }


def candidate_rule_matches(outcome: dict[str, Any], rule: dict[str, Any]) -> bool:
    if str(outcome.get("horizon") or "") != str(rule.get("horizon") or ""):
        return False
    if int(outcome.get("window_days") or 0) != int(rule.get("window_days") or 0):
        return False
    expected_side = rule.get("signal_side")
    if expected_side and signal_side(outcome) != str(expected_side):
        return False
    factors = outcome.get("factors") or {}
    factor_scope = rule.get("factor_scope") or {}
    if factor_scope:
        return all(factor_value_matches(factors.get(str(name)), expected) for name, expected in factor_scope.items())
    return str(factors.get(str(rule.get("factor_name") or "")) or "") == str(rule.get("factor_value") or "")


def factor_value_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (list, tuple, set)):
        return any(str(actual or "") == str(item) for item in expected)
    return str(actual or "") == str(expected)


def adjusted_outcome_for_rule(outcome: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    adjusted = dict(outcome)
    if not candidate_rule_matches(outcome, rule):
        return adjusted
    original_score = clamp_score(outcome.get("signal_score"))
    adjustment_mode = str(rule.get("score_adjustment_mode") or "score_bias")
    if adjustment_mode == "neutralize_to_watch":
        side = str(rule.get("signal_side") or signal_side(outcome))
        if side == "sell_avoid":
            adjusted_score = max(original_score, -14)
        elif side == "buy_bias":
            adjusted_score = min(original_score, 14)
        else:
            adjusted_score = original_score
    else:
        adjusted_score = clamp_score(original_score + (number(rule.get("score_bias")) or 0))
    adjusted_label = signal_label(adjusted_score)
    adjusted["signal_score"] = adjusted_score
    adjusted["signal_label"] = adjusted_label
    adjusted["hit"] = signal_accuracy.classify_hit(adjusted_label, outcome.get("return_pct"))
    adjusted["simulation_rule_id"] = rule.get("id")
    return adjusted


def compare_outcome_groups(baseline: list[dict[str, Any]], adjusted: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_summary = summarize_group(baseline)
    adjusted_summary = summarize_group(adjusted)
    baseline_directional = [item for item in baseline if item.get("hit") is not None]
    adjusted_directional = [item for item in adjusted if item.get("hit") is not None]
    baseline_wrong_directional = [item for item in baseline_directional if item.get("hit") is False]
    adjusted_wrong_directional = [item for item in adjusted_directional if item.get("hit") is False]
    neutralized_directional = [
        baseline_item
        for baseline_item, adjusted_item in zip(baseline, adjusted)
        if baseline_item.get("hit") is not None and adjusted_item.get("hit") is None
    ]
    neutralized_wrong_directional = [item for item in neutralized_directional if item.get("hit") is False]
    baseline_directional_avg_return = average(item.get("return_pct") for item in baseline_directional)
    adjusted_directional_avg_return = average(item.get("return_pct") for item in adjusted_directional)
    baseline_directional_avg_drawdown = average(item.get("max_drawdown_pct") for item in baseline_directional)
    adjusted_directional_avg_drawdown = average(item.get("max_drawdown_pct") for item in adjusted_directional)
    return {
        "matched_count": len(baseline),
        "baseline_hit_rate_pct": baseline_summary.get("hit_rate_pct"),
        "adjusted_hit_rate_pct": adjusted_summary.get("hit_rate_pct"),
        "hit_rate_delta_pct": (
            adjusted_summary["hit_rate_pct"] - baseline_summary["hit_rate_pct"]
            if adjusted_summary.get("hit_rate_pct") is not None and baseline_summary.get("hit_rate_pct") is not None
            else None
        ),
        "baseline_directional_count": baseline_summary.get("directional_count"),
        "adjusted_directional_count": adjusted_summary.get("directional_count"),
        "directional_count_delta": (
            int(adjusted_summary.get("directional_count") or 0)
            - int(baseline_summary.get("directional_count") or 0)
        ),
        "baseline_wrong_directional_count": len(baseline_wrong_directional),
        "adjusted_wrong_directional_count": len(adjusted_wrong_directional),
        "wrong_directional_count_delta": len(adjusted_wrong_directional) - len(baseline_wrong_directional),
        "neutralized_directional_count": len(neutralized_directional),
        "neutralized_wrong_directional_count": len(neutralized_wrong_directional),
        "neutralized_wrong_directional_rate_pct": (
            len(neutralized_wrong_directional) / len(neutralized_directional) * 100
            if neutralized_directional
            else None
        ),
        "neutralized_directional_avg_return_pct": average(item.get("return_pct") for item in neutralized_directional),
        "neutralized_wrong_directional_avg_return_pct": average(
            item.get("return_pct") for item in neutralized_wrong_directional
        ),
        "baseline_directional_avg_return_pct": baseline_directional_avg_return,
        "adjusted_directional_avg_return_pct": adjusted_directional_avg_return,
        "directional_avg_return_delta_pct": (
            adjusted_directional_avg_return - baseline_directional_avg_return
            if adjusted_directional_avg_return is not None and baseline_directional_avg_return is not None
            else None
        ),
        "baseline_directional_avg_drawdown_pct": baseline_directional_avg_drawdown,
        "adjusted_directional_avg_drawdown_pct": adjusted_directional_avg_drawdown,
        "directional_avg_drawdown_delta_pct": (
            adjusted_directional_avg_drawdown - baseline_directional_avg_drawdown
            if adjusted_directional_avg_drawdown is not None and baseline_directional_avg_drawdown is not None
            else None
        ),
        "avg_return_pct": baseline_summary.get("avg_return_pct"),
        "avg_max_drawdown_pct": baseline_summary.get("avg_max_drawdown_pct"),
    }


def summarize_rule_baskets(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in outcomes:
        parsed = sfa.parse_date_like(outcome.get("signal_trade_date"))
        date_key = parsed.isoformat() if parsed else str(outcome.get("signal_trade_date") or "unknown")
        by_date[date_key].append(outcome)

    baskets: list[dict[str, Any]] = []
    for date_key, items in sorted(by_date.items()):
        returns = [value for item in items if (value := number(item.get("return_pct"))) is not None]
        drawdowns = [value for item in items if (value := number(item.get("max_drawdown_pct"))) is not None]
        if not returns:
            continue
        baskets.append(
            {
                "date": date_key,
                "stock_count": len(returns),
                "avg_return_pct": average(returns),
                "avg_drawdown_pct": average(drawdowns),
            }
        )

    if not baskets:
        return {
            "basket_count": 0,
            "stock_signal_count": 0,
            "avg_basket_size": None,
            "avg_basket_return_pct": None,
            "positive_basket_rate_pct": None,
            "avg_basket_drawdown_pct": None,
            "worst_basket_return_pct": None,
            "worst_basket_date": None,
            "worst_basket_size": 0,
        }

    worst_basket = min(baskets, key=lambda item: number(item.get("avg_return_pct")) or 0)
    positive_count = sum(1 for basket in baskets if (number(basket.get("avg_return_pct")) or 0) > 0)
    return {
        "basket_count": len(baskets),
        "stock_signal_count": sum(int(basket.get("stock_count") or 0) for basket in baskets),
        "avg_basket_size": average(basket.get("stock_count") for basket in baskets),
        "avg_basket_return_pct": average(basket.get("avg_return_pct") for basket in baskets),
        "positive_basket_rate_pct": positive_count / len(baskets) * 100,
        "avg_basket_drawdown_pct": average(basket.get("avg_drawdown_pct") for basket in baskets),
        "worst_basket_return_pct": worst_basket.get("avg_return_pct"),
        "worst_basket_date": worst_basket.get("date"),
        "worst_basket_size": worst_basket.get("stock_count"),
    }


def candidate_rule_scope_matches(outcome: dict[str, Any], rule: dict[str, Any]) -> bool:
    expected_side = rule.get("signal_side")
    if expected_side and signal_side(outcome) != str(expected_side):
        return False
    factors = outcome.get("factors") or {}
    factor_scope = rule.get("factor_scope") or {}
    if factor_scope:
        return all(factor_value_matches(factors.get(str(name)), expected) for name, expected in factor_scope.items())
    return str(factors.get(str(rule.get("factor_name") or "")) or "") == str(rule.get("factor_value") or "")


def horizon_window_sort_key(horizon: str, window_days: int) -> tuple[int, int]:
    horizon_order = {"short_term": 0, "medium_term": 1, "long_term": 2}
    return horizon_order.get(horizon, 99), window_days


def summarize_rule_horizon_profile(
    outcomes: list[dict[str, Any]],
    rule: dict[str, Any],
    validation_from: dt.date | None,
) -> list[dict[str, Any]]:
    matched = [outcome for outcome in outcomes if candidate_rule_scope_matches(outcome, rule)]
    by_profile: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for outcome in matched:
        horizon = str(outcome.get("horizon") or "")
        window_days = int(outcome.get("window_days") or 0)
        if not horizon or not window_days:
            continue
        period = period_for_date(outcome.get("signal_trade_date"), validation_from)
        by_profile[(period, horizon, window_days)].append(outcome)

    rows = []
    period_order = {"train": 0, "validation": 1, "all": 2, "unknown": 3}
    for (period, horizon, window_days), items in sorted(
        by_profile.items(),
        key=lambda pair: (
            period_order.get(pair[0][0], 99),
            *horizon_window_sort_key(pair[0][1], pair[0][2]),
        ),
    ):
        summary = summarize_group(items)
        basket = summarize_rule_baskets(items)
        rows.append(
            {
                "period": period,
                "horizon": horizon,
                "window_days": window_days,
                "sample_count": summary.get("sample_count", 0),
                "directional_count": summary.get("directional_count", 0),
                "hit_rate_pct": summary.get("hit_rate_pct"),
                "avg_return_pct": summary.get("avg_return_pct"),
                "avg_max_drawdown_pct": summary.get("avg_max_drawdown_pct"),
                "basket_count": basket.get("basket_count", 0),
                "avg_basket_return_pct": basket.get("avg_basket_return_pct"),
                "positive_basket_rate_pct": basket.get("positive_basket_rate_pct"),
                "worst_basket_return_pct": basket.get("worst_basket_return_pct"),
            }
        )
    return rows


def simulate_candidate_rules(
    outcomes: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    validation_from: dt.date | None,
    rolling_bucket: str | None = None,
    stage_fold_factors: list[str] | None = None,
) -> list[dict[str, Any]]:
    simulations: list[dict[str, Any]] = []
    for rule in rules:
        matched = [outcome for outcome in outcomes if candidate_rule_matches(outcome, rule)]
        adjusted = [adjusted_outcome_for_rule(outcome, rule) for outcome in matched]
        by_period_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_period_adjusted: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for baseline_item, adjusted_item in zip(matched, adjusted):
            period = period_for_date(baseline_item.get("signal_trade_date"), validation_from)
            by_period_baseline[period].append(baseline_item)
            by_period_adjusted[period].append(adjusted_item)
        simulations.append(
            {
                "rule": rule,
                "train": compare_outcome_groups(by_period_baseline.get("train", []), by_period_adjusted.get("train", [])),
                "validation": compare_outcome_groups(
                    by_period_baseline.get("validation", []),
                    by_period_adjusted.get("validation", []),
                ),
                "all": compare_outcome_groups(matched, adjusted),
                "basket_train": summarize_rule_baskets(by_period_baseline.get("train", [])),
                "basket_validation": summarize_rule_baskets(by_period_baseline.get("validation", [])),
                "basket_all": summarize_rule_baskets(matched),
                "horizon_profile": summarize_rule_horizon_profile(outcomes, rule, validation_from),
            }
        )
        if should_build_counterexample_factors(rule):
            simulations[-1]["counterexample_factor_rows"] = summarize_rule_counterexample_factors(
                outcomes,
                rule,
                validation_from,
                matched_outcomes=matched,
            )
        if rolling_bucket and rolling_bucket != "none":
            folds = rolling_candidate_rule_folds(outcomes, rule, bucket=rolling_bucket, matched_outcomes=matched)
            simulations[-1]["rolling_folds"] = folds
            simulations[-1]["rolling_summary"] = rolling_candidate_rule_summary(folds, bucket=rolling_bucket)
        if stage_fold_factors:
            stage_folds: dict[str, list[dict[str, Any]]] = {}
            stage_summaries: dict[str, dict[str, Any]] = {}
            for factor_name in stage_fold_factors:
                folds = stage_candidate_rule_folds(outcomes, rule, factor_name, matched_outcomes=matched)
                if not folds:
                    continue
                stage_folds[factor_name] = folds
                stage_summaries[factor_name] = stage_candidate_rule_summary(folds, factor_name)
            simulations[-1]["stage_factor_folds"] = stage_folds
            simulations[-1]["stage_factor_summaries"] = stage_summaries
    return simulations


def should_build_counterexample_factors(rule: dict[str, Any]) -> bool:
    rule_id = str(rule.get("id") or "")
    return (
        (
            rule_id.startswith("continuous_speed_focus:")
            or rule_id.startswith("repair_quality_focus:")
            or rule_id.startswith("repair_quality_sync_focus:")
            or rule_id.startswith("repair_quality_failure_focus:")
            or rule_id.startswith("repair_quality_defense_pocket:")
            or rule_id.startswith("mixed_bucket_continuous_combo:")
        )
        and str(rule.get("horizon") or "") == "long_term"
        and int(rule.get("window_days") or 0) == 60
    )


def summarize_rule_counterexample_factors(
    outcomes: list[dict[str, Any]],
    rule: dict[str, Any],
    validation_from: dt.date | None,
    factor_names: list[str] | None = None,
    matched_outcomes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    names = factor_names or DEFAULT_COUNTEREXAMPLE_FACTORS
    directional = [
        outcome
        for outcome in (matched_outcomes if matched_outcomes is not None else outcomes)
        if (matched_outcomes is not None or candidate_rule_matches(outcome, rule)) and outcome.get("hit") is not None
    ]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for outcome in directional:
        factors = outcome.get("factors") or {}
        period = period_for_date(outcome.get("signal_trade_date"), validation_from)
        for factor_name in names:
            value = str(factors.get(factor_name) or "未知")
            grouped[(period, factor_name, value)].append(outcome)

    rows = []
    period_order = {"train": 0, "validation": 1, "all": 2, "unknown": 3}
    for (period, factor_name, factor_value), items in sorted(
        grouped.items(),
        key=lambda pair: (
            period_order.get(pair[0][0], 99),
            pair[0][1],
            -len(pair[1]),
            pair[0][2],
        ),
    ):
        correct = [item for item in items if item.get("hit") is True]
        wrong = [item for item in items if item.get("hit") is False]
        rows.append(
            {
                "period": period,
                "factor_name": factor_name,
                "factor_value": factor_value,
                "sample_count": len(items),
                "correct_count": len(correct),
                "wrong_count": len(wrong),
                "correct_rate_pct": len(correct) / len(items) * 100 if items else None,
                "wrong_rate_pct": len(wrong) / len(items) * 100 if items else None,
                "correct_avg_return_pct": average(item.get("return_pct") for item in correct),
                "wrong_avg_return_pct": average(item.get("return_pct") for item in wrong),
                "avg_drawdown_pct": average(item.get("max_drawdown_pct") for item in items),
            }
        )
    return rows


def fold_bucket_for_date(value: Any, bucket: str) -> str:
    parsed = sfa.parse_date_like(value)
    if parsed is None:
        return "unknown"
    if bucket == "quarter":
        quarter = (parsed.month - 1) // 3 + 1
        return f"{parsed.year}-Q{quarter}"
    return f"{parsed.year:04d}-{parsed.month:02d}"


def rolling_candidate_rule_folds(
    outcomes: list[dict[str, Any]],
    rule: dict[str, Any],
    bucket: str = "month",
    matched_outcomes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    matched = matched_outcomes if matched_outcomes is not None else [
        outcome for outcome in outcomes if candidate_rule_matches(outcome, rule)
    ]
    by_bucket_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket_adjusted: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in matched:
        bucket_key = fold_bucket_for_date(outcome.get("signal_trade_date"), bucket)
        by_bucket_baseline[bucket_key].append(outcome)
        by_bucket_adjusted[bucket_key].append(adjusted_outcome_for_rule(outcome, rule))

    folds = []
    for bucket_key in sorted(by_bucket_baseline):
        comparison = compare_outcome_groups(by_bucket_baseline[bucket_key], by_bucket_adjusted[bucket_key])
        comparison["bucket"] = bucket_key
        folds.append(comparison)
    return folds


def rolling_candidate_rule_summary(folds: list[dict[str, Any]], bucket: str) -> dict[str, Any]:
    folds_with_samples = [fold for fold in folds if int(fold.get("matched_count") or 0) > 0]
    total_matched = sum(int(fold.get("matched_count") or 0) for fold in folds_with_samples)
    max_fold_matched = max((int(fold.get("matched_count") or 0) for fold in folds_with_samples), default=0)
    neutralized_directional = sum(int(fold.get("neutralized_directional_count") or 0) for fold in folds_with_samples)
    neutralized_wrong = sum(int(fold.get("neutralized_wrong_directional_count") or 0) for fold in folds_with_samples)
    positive_wrong_delta_folds = sum(
        1 for fold in folds_with_samples if (number(fold.get("wrong_directional_count_delta")) or 0) < 0
    )
    return {
        "bucket": bucket,
        "fold_count": len(folds),
        "folds_with_samples": len(folds_with_samples),
        "total_matched_count": total_matched,
        "max_fold_sample_share_pct": (max_fold_matched / total_matched * 100 if total_matched else None),
        "weighted_neutralized_wrong_directional_rate_pct": (
            neutralized_wrong / neutralized_directional * 100 if neutralized_directional else None
        ),
        "positive_wrong_delta_fold_count": positive_wrong_delta_folds,
        "positive_wrong_delta_fold_share_pct": (
            positive_wrong_delta_folds / len(folds_with_samples) * 100 if folds_with_samples else None
        ),
    }


def stage_candidate_rule_folds(
    outcomes: list[dict[str, Any]],
    rule: dict[str, Any],
    factor_name: str,
    matched_outcomes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    matched = matched_outcomes if matched_outcomes is not None else [
        outcome for outcome in outcomes if candidate_rule_matches(outcome, rule)
    ]
    by_factor_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_factor_adjusted: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in matched:
        factors = outcome.get("factors") or {}
        factor_value = str(factors.get(factor_name) or "未知")
        bucket_key = f"{factor_name}={factor_value}"
        by_factor_baseline[bucket_key].append(outcome)
        by_factor_adjusted[bucket_key].append(adjusted_outcome_for_rule(outcome, rule))

    folds = []
    for bucket_key, baseline_items in sorted(
        by_factor_baseline.items(),
        key=lambda pair: (-len(pair[1]), pair[0]),
    ):
        comparison = compare_outcome_groups(baseline_items, by_factor_adjusted[bucket_key])
        comparison["bucket"] = bucket_key
        folds.append(comparison)
    return folds


def stage_candidate_rule_summary(folds: list[dict[str, Any]], factor_name: str) -> dict[str, Any]:
    folds_with_samples = [fold for fold in folds if int(fold.get("matched_count") or 0) > 0]
    total_matched = sum(int(fold.get("matched_count") or 0) for fold in folds_with_samples)
    max_fold_matched = max((int(fold.get("matched_count") or 0) for fold in folds_with_samples), default=0)
    neutralized_directional = sum(int(fold.get("neutralized_directional_count") or 0) for fold in folds_with_samples)
    neutralized_wrong = sum(int(fold.get("neutralized_wrong_directional_count") or 0) for fold in folds_with_samples)
    positive_wrong_delta_folds = sum(
        1 for fold in folds_with_samples if (number(fold.get("wrong_directional_count_delta")) or 0) < 0
    )
    return {
        "factor_name": factor_name,
        "folds_with_samples": len(folds_with_samples),
        "total_matched_count": total_matched,
        "max_fold_sample_share_pct": (max_fold_matched / total_matched * 100 if total_matched else None),
        "weighted_neutralized_wrong_directional_rate_pct": (
            neutralized_wrong / neutralized_directional * 100 if neutralized_directional else None
        ),
        "positive_wrong_delta_fold_count": positive_wrong_delta_folds,
        "positive_wrong_delta_fold_share_pct": (
            positive_wrong_delta_folds / len(folds_with_samples) * 100 if folds_with_samples else None
        ),
    }


def period_for_date(value: Any, validation_from: dt.date | None) -> str:
    if validation_from is None:
        return "all"
    parsed = sfa.parse_date_like(value)
    if parsed is None:
        return "unknown"
    return "validation" if parsed >= validation_from else "train"


def summarize_outcomes(
    outcomes: list[dict[str, Any]],
    validation_from: dt.date | None = None,
) -> dict[str, Any]:
    by_horizon_window: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    by_regime_horizon: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_refined_regime_horizon: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_market_regime_horizon: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_period_horizon_window: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_factor: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_signal_side_horizon_window: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_signal_side_refined_regime_horizon_window: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_signal_side_market_regime_horizon_window: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_signal_side_factor: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in outcomes:
        horizon = str(outcome.get("horizon") or "")
        window_days = int(outcome.get("window_days") or 0)
        regime = str(outcome.get("regime") or "unknown")
        refined_regime = str(outcome.get("refined_regime") or (outcome.get("factors") or {}).get("refined_regime") or "unknown")
        market_regime = str(outcome.get("market_regime") or (outcome.get("factors") or {}).get("market_regime") or "market_unknown")
        stock_code = str(outcome.get("stock_code") or "")
        period = period_for_date(outcome.get("signal_trade_date"), validation_from)
        if horizon and window_days:
            by_horizon_window[(horizon, window_days)].append(outcome)
            by_period_horizon_window[(period, horizon, window_days)].append(outcome)
            side = signal_side(outcome)
            if side != "watch":
                by_signal_side_horizon_window[(side, horizon, window_days)].append(outcome)
                by_signal_side_refined_regime_horizon_window[
                    (side, refined_regime, horizon, window_days)
                ].append(outcome)
                by_signal_side_market_regime_horizon_window[
                    (side, market_regime, horizon, window_days)
                ].append(outcome)
            for factor_name, factor_value in (outcome.get("factors") or {}).items():
                by_factor[(str(factor_name), str(factor_value), horizon, window_days)].append(outcome)
                if side != "watch":
                    by_signal_side_factor[
                        (side, str(factor_name), str(factor_value), horizon, window_days)
                    ].append(outcome)
        if regime and horizon:
            by_regime_horizon[(regime, horizon)].append(outcome)
        if refined_regime and horizon:
            by_refined_regime_horizon[(refined_regime, horizon)].append(outcome)
        if market_regime and horizon:
            by_market_regime_horizon[(market_regime, horizon)].append(outcome)
        if stock_code:
            by_stock[stock_code].append(outcome)

    return {
        "sample_count": len(outcomes),
        "by_horizon_window": {key: summarize_group(items) for key, items in sorted(by_horizon_window.items())},
        "by_regime_horizon": {key: summarize_group(items) for key, items in sorted(by_regime_horizon.items())},
        "by_refined_regime_horizon": {
            key: summarize_group(items) for key, items in sorted(by_refined_regime_horizon.items())
        },
        "by_market_regime_horizon": {
            key: summarize_group(items) for key, items in sorted(by_market_regime_horizon.items())
        },
        "by_period_horizon_window": {
            key: summarize_group(items) for key, items in sorted(by_period_horizon_window.items())
        },
        "by_factor": {key: summarize_group(items) for key, items in sorted(by_factor.items())},
        "by_signal_side_horizon_window": {
            key: summarize_group(items) for key, items in sorted(by_signal_side_horizon_window.items())
        },
        "by_signal_side_refined_regime_horizon_window": {
            key: summarize_group(items)
            for key, items in sorted(by_signal_side_refined_regime_horizon_window.items())
        },
        "by_signal_side_market_regime_horizon_window": {
            key: summarize_group(items)
            for key, items in sorted(by_signal_side_market_regime_horizon_window.items())
        },
        "by_signal_side_factor": {
            key: summarize_group(items) for key, items in sorted(by_signal_side_factor.items())
        },
        "by_stock": {key: summarize_group(items) for key, items in sorted(by_stock.items())},
    }


def candidate_observation_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    by_regime = summary.get("by_regime_horizon") or {}
    for (regime, horizon), item in by_regime.items():
        directional_count = int(item.get("directional_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        if directional_count < 5 or hit_rate is None:
            continue
        label = HORIZON_LABELS.get(horizon, horizon)
        if hit_rate < 45:
            lines.append(
                f"- `{regime}` 状态下 `{label}` 方向信号命中率 {hit_rate:.2f}%，样本 {directional_count}，后续应检查该状态是否过度奖励某类指标。"
            )
        elif hit_rate > 60:
            lines.append(
                f"- `{regime}` 状态下 `{label}` 方向信号命中率 {hit_rate:.2f}%，样本 {directional_count}，可作为候选优势规则继续验证。"
            )
    if not lines:
        return ["- 暂无达到样本门槛的候选调整；继续积累样本，避免过早优化。"]
    return lines


def factor_review_rows(summary: dict[str, Any], limit: int = 12) -> list[tuple[tuple[str, str, str, int], dict[str, Any]]]:
    rows = []
    for key, item in (summary.get("by_factor") or {}).items():
        sample_count = int(item.get("sample_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        if sample_count < 10 or hit_rate is None:
            continue
        rows.append((key, item))
    return sorted(
        rows,
        key=lambda pair: (
            abs((number(pair[1].get("hit_rate_pct")) or 50) - 50),
            int(pair[1].get("sample_count") or 0),
        ),
        reverse=True,
    )[:limit]


def signal_side_factor_review_rows(
    summary: dict[str, Any],
    limit: int = 12,
) -> list[tuple[tuple[str, str, str, str, int], dict[str, Any]]]:
    rows = []
    for key, item in (summary.get("by_signal_side_factor") or {}).items():
        sample_count = int(item.get("sample_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        if sample_count < 10 or hit_rate is None:
            continue
        rows.append((key, item))
    return sorted(
        rows,
        key=lambda pair: (
            abs((number(pair[1].get("hit_rate_pct")) or 50) - 50),
            abs(number(pair[1].get("avg_return_pct")) or 0),
            int(pair[1].get("sample_count") or 0),
        ),
        reverse=True,
    )[:limit]


def market_refined_cross_review_rows(
    summary: dict[str, Any],
    limit: int = 16,
) -> list[tuple[tuple[str, str, str, str, int], dict[str, Any]]]:
    rows = []
    for key, item in (summary.get("by_signal_side_factor") or {}).items():
        side, factor_name, _factor_value, _horizon, _window_days = key
        if factor_name != "market_refined_regime" or side == "watch":
            continue
        sample_count = int(item.get("sample_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        if sample_count < 30 or hit_rate is None:
            continue
        rows.append((key, item))
    return sorted(
        rows,
        key=lambda pair: (
            abs((number(pair[1].get("hit_rate_pct")) or 50) - 50),
            abs(number(pair[1].get("avg_return_pct")) or 0),
            int(pair[1].get("sample_count") or 0),
        ),
        reverse=True,
    )[:limit]


def candidate_rule_lines(summary: dict[str, Any]) -> list[str]:
    rows = signal_side_factor_review_rows(summary, limit=20)
    lines: list[str] = []
    for (side, factor_name, factor_value, horizon, window_days), item in rows:
        sample_count = int(item.get("sample_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        avg_return = number(item.get("avg_return_pct"))
        if hit_rate is None or sample_count < 30:
            continue
        label = HORIZON_LABELS.get(horizon, horizon)
        side_label = SIGNAL_SIDE_LABELS.get(side, side)
        scope = f"{side_label}/{factor_name}={factor_value}"
        if side == "buy_bias":
            if hit_rate >= 58 and (avg_return is None or avg_return >= 0):
                action = "候选增强买入筛选"
                follow_up = "下一轮用验证段确认后，再考虑提高相关买入方向权重。"
            elif hit_rate <= 45 or (avg_return is not None and avg_return < 0):
                action = "候选降低买入权重"
                follow_up = "下一轮检查是否应降低该条件下的买入方向分数。"
            else:
                continue
            lines.append(
                f"- {action}：`{scope}` 在 {label}{window_days}日样本 {sample_count}、命中率 {hit_rate:.2f}%、平均收益 {pct(avg_return)}；{follow_up}"
            )
        elif side == "sell_avoid":
            if hit_rate >= 58 and (avg_return is None or avg_return <= 0):
                action = "候选增强风险约束"
                follow_up = "下一轮用验证段确认后，再考虑提高该条件下的卖出/回避方向权重。"
            elif hit_rate <= 45 or (avg_return is not None and avg_return > 0):
                action = "候选降低风险约束"
                follow_up = "下一轮检查是否应降低该条件下的卖出/回避方向分数。"
            else:
                continue
            lines.append(
                f"- {action}：`{scope}` 在 {label}{window_days}日样本 {sample_count}、命中率 {hit_rate:.2f}%、平均收益 {pct(avg_return)}；{follow_up}"
            )
    if not lines:
        return ["- 暂无满足样本与效果门槛的候选优化规则；本轮不建议修改 active 权重。"]
    return lines


def build_candidate_rules(summary: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for (side, factor_name, factor_value, horizon, window_days), item in signal_side_factor_review_rows(
        summary,
        limit=80,
    ):
        sample_count = int(item.get("sample_count") or 0)
        hit_rate = number(item.get("hit_rate_pct"))
        avg_return = number(item.get("avg_return_pct"))
        if hit_rate is None or sample_count < 100:
            continue
        if side == "buy_bias":
            if hit_rate >= 58 and (avg_return is None or avg_return >= 0):
                score_bias = 5
                score_adjustment_mode = "score_bias"
                kind = "positive_filter"
            elif hit_rate <= 45 or (avg_return is not None and avg_return < 0):
                score_bias = -5
                score_adjustment_mode = "neutralize_to_watch"
                kind = "downweight"
            else:
                continue
        elif side == "sell_avoid":
            if hit_rate >= 58 and (avg_return is None or avg_return <= 0):
                score_bias = -5
                score_adjustment_mode = "score_bias"
                kind = "risk_constraint"
            elif hit_rate <= 45 or (avg_return is not None and avg_return > 0):
                score_bias = 5
                score_adjustment_mode = "neutralize_to_watch"
                kind = "downweight"
            else:
                continue
        else:
            continue
        rules.append(
            {
                "id": f"{kind}:{side}:{factor_name}={factor_value}:{horizon}:{window_days}",
                "signal_side": side,
                "factor_name": factor_name,
                "factor_value": factor_value,
                "horizon": horizon,
                "window_days": window_days,
                "score_bias": score_bias,
                "score_adjustment_mode": score_adjustment_mode,
                "kind": kind,
                "source_sample_count": sample_count,
                "source_hit_rate_pct": hit_rate,
                "source_avg_return_pct": avg_return,
            }
        )
        if len(rules) >= limit:
            break
    return rules


def weak_tail_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
    }
    focus_scopes = [
        (
            "market-fast-tail",
            {
                **base_scope,
                "market_decline_speed": "跌速加快",
                "market_tail_extreme": ["极端超卖", "弱势低位"],
            },
            "市场弱势延续与个股弱势延续交叉，同时市场跌速加快并处在低位/极端超卖尾部。",
        ),
        (
            "market-fast-stock-tail",
            {
                **base_scope,
                "market_decline_speed": "跌速加快",
                "market_tail_extreme": ["极端超卖", "弱势低位"],
                "weak_tail_extreme": ["极端超卖", "弱势低位"],
            },
            "在市场跌速加快且市场/个股都处在弱势尾部时，复核卖出/回避信号是否滞后。",
        ),
        (
            "dual-fast-dual-tail",
            {
                **base_scope,
                "market_decline_speed": "跌速加快",
                "decline_speed": "跌速加快",
                "market_tail_extreme": ["极端超卖", "弱势低位"],
                "weak_tail_extreme": ["极端超卖", "弱势低位"],
            },
            "市场和个股跌速都加快，且二者都在弱势尾部；这是更窄的卖出滞后复核假设。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"weak_tail_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def continuous_repair_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    repair_values = ["连续修复确认", "放量修复确认", "修复初步形成"]
    focus_scopes = [
        (
            "market-continuous-repair",
            {
                **base_scope,
                "market_repair_continuity": repair_values,
            },
            "弱尾部组合里，市场连续修复已经出现，用来验证卖出/回避信号是否更容易滞后。",
        ),
        (
            "stock-continuous-repair",
            {
                **base_scope,
                "repair_continuity": repair_values,
            },
            "弱尾部组合里，个股连续修复已经出现，用来验证卖出/回避信号是否更容易滞后。",
        ),
        (
            "dual-continuous-repair",
            {
                **base_scope,
                "market_repair_continuity": repair_values,
                "repair_continuity": repair_values,
            },
            "市场和个股都出现连续修复迹象，检验是否能形成更窄的观察降级候选。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"continuous_repair_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def repair_speed_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    fast_values = ["快速修复确认", "快速修复形成"]
    gradual_values = ["渐进修复"]
    focus_scopes = [
        (
            "market-fast-repair-speed",
            {
                **base_scope,
                "market_repair_speed": fast_values,
            },
            "弱尾部组合里，市场修复速度较快，用来验证卖出/回避信号是否更适合中期复核。",
        ),
        (
            "stock-fast-repair-speed",
            {
                **base_scope,
                "repair_speed": fast_values,
            },
            "弱尾部组合里，个股修复速度较快，用来验证卖出/回避信号是否更适合中期复核。",
        ),
        (
            "dual-fast-repair-speed",
            {
                **base_scope,
                "market_repair_speed": fast_values,
                "repair_speed": fast_values,
            },
            "市场和个股修复速度都较快，检验 horizon 是否从 60 日前移到 20 日。",
        ),
        (
            "market-gradual-repair-speed",
            {
                **base_scope,
                "market_repair_speed": gradual_values,
            },
            "市场修复速度偏渐进，检验是否更适合长期 60 日复核。",
        ),
        (
            "stock-gradual-repair-speed",
            {
                **base_scope,
                "repair_speed": gradual_values,
            },
            "个股修复速度偏渐进，检验是否更适合长期 60 日复核。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"repair_speed_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def continuous_speed_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    profile_values = ["速度共振明显", "速度共振偏强", "速度温和共振"]
    strong_values = ["速度改善明显", "速度温和改善"]
    focus_scopes = [
        (
            "market-speed-profile",
            {
                **base_scope,
                "market_repair_speed_profile": profile_values,
            },
            "弱尾部组合里，市场多个连续速度指标共振，用来验证卖出/回避是否更适合观察复核。",
        ),
        (
            "stock-speed-profile",
            {
                **base_scope,
                "repair_speed_profile": profile_values,
            },
            "弱尾部组合里，个股多个连续速度指标共振，用来验证卖出/回避是否更适合观察复核。",
        ),
        (
            "dual-speed-profile",
            {
                **base_scope,
                "market_repair_speed_profile": profile_values,
                "repair_speed_profile": profile_values,
            },
            "市场和个股连续速度共振同时出现，检验是否能收窄卖出滞后样本。",
        ),
        (
            "market-macd-boll-speed",
            {
                **base_scope,
                "market_macd_repair_speed": strong_values,
                "market_boll_recovery_speed": strong_values,
            },
            "市场 MACD 修复和 BOLL 回收同时加快，检验价格结构修复是否领先于评分。",
        ),
        (
            "stock-macd-boll-speed",
            {
                **base_scope,
                "macd_repair_speed": strong_values,
                "boll_recovery_speed": strong_values,
            },
            "个股 MACD 修复和 BOLL 回收同时加快，检验价格结构修复是否领先于评分。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"continuous_speed_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def repair_quality_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    quality_values = ["修复质量确认", "修复质量初步确认"]
    speed_values = ["速度共振明显", "速度共振偏强", "速度温和共振"]
    focus_scopes = [
        (
            "market-quality-confirmed",
            {
                **base_scope,
                "market_repair_speed_profile": speed_values,
                "market_repair_quality_confirmation": quality_values,
            },
            "市场连续速度共振且修复质量确认，检验是否能减少 60 日 sell/avoid 降级反例。",
        ),
        (
            "stock-quality-confirmed",
            {
                **base_scope,
                "repair_speed_profile": speed_values,
                "repair_quality_confirmation": quality_values,
            },
            "个股连续速度共振且修复质量确认，检验是否能减少 60 日 sell/avoid 降级反例。",
        ),
        (
            "dual-quality-confirmed",
            {
                **base_scope,
                "market_repair_quality_confirmation": quality_values,
                "repair_quality_confirmation": quality_values,
            },
            "市场和个股修复质量都确认，检验是否形成更窄的 60 日慢修复复核 scope。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"repair_quality_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def repair_quality_sync_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    sync_positive = ["双侧质量同步确认", "市场确认个股不恶化", "个股确认市场不恶化"]
    focus_scopes = [
        (
            "sync-non-deteriorating",
            {
                **base_scope,
                "repair_quality_sync": sync_positive,
            },
            "市场或个股至少一侧修复质量确认，且对侧没有恶化，检验同步防守条件是否减少 60 日反例。",
        ),
        (
            "dual-sync-confirmed",
            {
                **base_scope,
                "repair_quality_sync": "双侧质量同步确认",
            },
            "市场和个股修复质量同步确认，检验最窄质量共振 scope 是否仍有足够样本。",
        ),
        (
            "single-side-opposite-safe",
            {
                **base_scope,
                "repair_quality_sync": ["市场确认个股不恶化", "个股确认市场不恶化"],
            },
            "单侧修复质量确认且对侧不恶化，检验单侧确认是否需要降级为复核而非主动规则。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"repair_quality_sync_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def repair_quality_failure_focus_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    focus_scopes = [
        (
            "sync-deteriorating",
            {
                **base_scope,
                "repair_quality_sync": ["单侧确认对侧恶化", "双侧质量恶化"],
            },
            "同步质量出现对侧恶化或双侧恶化，反向检验 sell/avoid 是否仍应保留风控作用。",
        ),
        (
            "single-side-opposite-deteriorating",
            {
                **base_scope,
                "repair_quality_sync": "单侧确认对侧恶化",
            },
            "单侧修复确认但对侧质量恶化，检验这是观察降级反例还是仍可降级的慢修复样本。",
        ),
        (
            "dual-deteriorating",
            {
                **base_scope,
                "repair_quality_sync": "双侧质量恶化",
            },
            "市场和个股修复质量同时恶化，检验 sell/avoid 是否更接近有效风控。",
        ),
        (
            "sync-insufficient",
            {
                **base_scope,
                "repair_quality_sync": "质量同步不足",
            },
            "没有形成同步修复质量，检验未确认状态是否应从观察降级候选中排除。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"repair_quality_failure_focus:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def repair_quality_defense_pocket_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_refined_regime": "market_bear_continuation|bear_continuation",
        "market_decline_speed": "跌速加快",
        "market_tail_extreme": ["极端超卖", "弱势低位"],
        "weak_tail_extreme": ["极端超卖", "弱势低位"],
    }
    failure_states = ["单侧确认对侧恶化", "双侧质量恶化", "质量同步不足"]
    focus_scopes = [
        (
            "market-macd-speed-divergence",
            {
                **base_scope,
                "repair_quality_sync": failure_states,
                "market_macd_repair_speed": "速度未改善",
                "market_repair_speed_profile": "速度分化",
            },
            "市场 MACD 修复未改善且速度分化，检验是否是 sell/avoid 仍有效的风控口袋。",
        ),
        (
            "stock-volume-deterioration",
            {
                **base_scope,
                "repair_quality_sync": failure_states,
                "volume_expansion_speed": "速度恶化",
            },
            "个股量能速度恶化，检验量能失败是否应阻止 sell/avoid 被降级为观察。",
        ),
        (
            "market-quality-deterioration",
            {
                **base_scope,
                "repair_quality_sync": failure_states,
                "market_repair_quality_confirmation": "修复质量恶化",
            },
            "市场修复质量恶化，检验市场侧失败是否是有效风控口袋。",
        ),
        (
            "tail-pending",
            {
                **base_scope,
                "repair_quality_sync": failure_states,
                "tail_repair_signal": "低位待确认",
            },
            "低位修复仍待确认，检验未确认修复是否应保留原 sell/avoid 风控。",
        ),
        (
            "market-quality-stock-volume-defense",
            {
                **base_scope,
                "repair_quality_sync": failure_states,
                "market_repair_quality_confirmation": "修复质量恶化",
                "volume_expansion_speed": "速度恶化",
            },
            "市场修复质量恶化叠加个股量能恶化，检验更窄双侧失败风控口袋。",
        ),
    ]
    horizon_windows = [
        ("medium_term", 20),
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"repair_quality_defense_pocket:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def mixed_bucket_continuous_combo_candidate_rules() -> list[dict[str, Any]]:
    base_scope: dict[str, Any] = {
        "market_trend_20d": "下跌",
        "market_trend_60d": "下跌",
        "trend_20d": "下跌",
        "trend_60d": "下跌",
        "horizon_stage_category": "混合继续复核",
    }
    improved_values = sorted(REPAIR_SPEED_IMPROVED_VALUES)
    focus_scopes = [
        (
            "no-market-volume-pulse-still-down",
            {
                **base_scope,
                "market_volume_expansion_speed": ["速度未改善", "速度恶化"],
                "macd_repair_speed": improved_values,
                "market_volume_persistence": "量能脉冲不连续",
                "market_rebound_stretch": "20日仍下跌",
            },
            "混合桶中市场量能未改善但个股 MACD 已修复，若市场量能仍是脉冲且 20 日仍下跌，验证 sell/avoid 是否在 60 日窗口滞后。",
        ),
        (
            "market-volume-improved-still-down-macd-discontinuous",
            {
                **base_scope,
                "market_volume_expansion_speed": improved_values,
                "macd_repair_speed": improved_values,
                "market_rebound_stretch": "20日仍下跌",
                "macd_repair_persistence": "MACD改善不连续",
            },
            "混合桶中即便市场量能改善，如果市场 20 日仍下跌且个股 MACD 改善不连续，验证 sell/avoid 是否仍会在 60 日窗口滞后。",
        ),
    ]
    horizon_windows = [
        ("long_term", 60),
        ("long_term", 120),
    ]
    rules = []
    for scope_id, factor_scope, reason in focus_scopes:
        for horizon, window_days in horizon_windows:
            rules.append(
                {
                    "id": f"mixed_bucket_continuous_combo:{scope_id}:sell_avoid:{horizon}:{window_days}",
                    "signal_side": "sell_avoid",
                    "factor_scope": factor_scope,
                    "horizon": horizon,
                    "window_days": window_days,
                    "score_bias": 5,
                    "score_adjustment_mode": "neutralize_to_watch",
                    "kind": "research_focus",
                    "reason": reason,
                }
            )
    return rules


def rule_adjustment_label(rule: dict[str, Any]) -> str:
    mode = str(rule.get("score_adjustment_mode") or "score_bias")
    if mode == "neutralize_to_watch":
        return "推至观察边界"
    return str(rule.get("score_bias"))


def simulation_table_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| 规则 | 调整方式 | 数据段 | 匹配样本 | 方向样本变化 | 错误方向变化 | 降级错误率 | 原命中率 | 模拟命中率 | 命中变化 | 方向均收益变化 | 方向均回撤变化 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not simulations:
        return [*lines, "| 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |"]
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        rule_id = rule.get("id") or ""
        adjustment = rule_adjustment_label(rule)
        for period_key, period_label in [("train", "训练段"), ("validation", "验证段")]:
            item = simulation.get(period_key) or {}
            lines.append(
                f"| `{rule_id}` | {adjustment} | {period_label} | {item.get('matched_count', 0)} | "
                f"{item.get('directional_count_delta', 0)} | "
                f"{item.get('wrong_directional_count_delta', 0)} | "
                f"{pct(item.get('neutralized_wrong_directional_rate_pct'))} | "
                f"{pct(item.get('baseline_hit_rate_pct'))} | {pct(item.get('adjusted_hit_rate_pct'))} | "
                f"{pct(item.get('hit_rate_delta_pct'))} | {pct(item.get('directional_avg_return_delta_pct'))} | "
                f"{pct(item.get('directional_avg_drawdown_delta_pct'))} |"
            )
    return lines


def candidate_basket_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "- 这一节把同一信号日命中的股票视为一个等权篮子，避免同日密集信号把单票统计放大。",
        "",
        "| 规则 | 数据段 | 篮子数 | 信号数 | 平均篮子大小 | 等权篮子均收益 | 正收益篮子率 | 等权篮子均回撤 | 最差篮子日期 | 最差篮子收益 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    if not simulations:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        rule_id = rule.get("id") or ""
        for basket_key, period_label in [
            ("basket_train", "训练段"),
            ("basket_validation", "验证段"),
            ("basket_all", "全样本"),
        ]:
            basket = simulation.get(basket_key) or {}
            lines.append(
                f"| `{rule_id}` | {period_label} | {basket.get('basket_count', 0)} | "
                f"{basket.get('stock_signal_count', 0)} | {decimal(basket.get('avg_basket_size'))} | "
                f"{pct(basket.get('avg_basket_return_pct'))} | {pct(basket.get('positive_basket_rate_pct'))} | "
                f"{pct(basket.get('avg_basket_drawdown_pct'))} | {basket.get('worst_basket_date') or '暂无'} | "
                f"{pct(basket.get('worst_basket_return_pct'))} |"
            )
    return lines


def candidate_horizon_profile_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "- 这一节忽略候选规则自身的固定持有期，只保留方向和因子 scope，横向比较同一状态在不同窗口的表现，用来定位 horizon 漂移。",
        "",
        "| 规则 | 数据段 | 周期窗口 | 信号数 | 方向样本 | 命中率 | 平均收益 | 平均回撤 | 日篮数 | 日篮均收益 | 正收益日篮率 | 最差日篮收益 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not simulations:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |",
        ]
    has_rows = False
    period_labels = {"train": "训练段", "validation": "验证段", "all": "全样本", "unknown": "未知"}
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        rule_id = rule.get("id") or ""
        for row in simulation.get("horizon_profile") or []:
            sample_count = int(row.get("sample_count") or 0)
            if sample_count <= 0:
                continue
            has_rows = True
            horizon = str(row.get("horizon") or "")
            window_days = int(row.get("window_days") or 0)
            label = HORIZON_LABELS.get(horizon, horizon)
            period_label = period_labels.get(str(row.get("period") or ""), str(row.get("period") or ""))
            lines.append(
                f"| `{rule_id}` | {period_label} | {label} {window_days}日 | "
                f"{sample_count} | {row.get('directional_count', 0)} | {pct(row.get('hit_rate_pct'))} | "
                f"{pct(row.get('avg_return_pct'))} | {pct(row.get('avg_max_drawdown_pct'))} | "
                f"{row.get('basket_count', 0)} | {pct(row.get('avg_basket_return_pct'))} | "
                f"{pct(row.get('positive_basket_rate_pct'))} | {pct(row.get('worst_basket_return_pct'))} |"
            )
    if not has_rows:
        lines.append("| 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")
    return lines


def continuous_speed_scope_id(rule_id: str) -> str | None:
    parts = rule_id.split(":")
    if len(parts) < 5 or parts[0] != "continuous_speed_focus":
        return None
    return parts[1]


def horizon_profile_row_map(simulation: dict[str, Any]) -> dict[tuple[str, str, int], dict[str, Any]]:
    rows: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in simulation.get("horizon_profile") or []:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        period = str(row.get("period") or "")
        if period and horizon and window_days:
            rows[(period, horizon, window_days)] = row
    return rows


def horizon_selector_cell(row: dict[str, Any] | None) -> str:
    if not row:
        return "暂无"
    return (
        f"{row.get('sample_count', 0)} / "
        f"{pct(row.get('avg_return_pct'))} / "
        f"{row.get('basket_count', 0)}篮"
    )


def continuous_speed_horizon_verdict(row_map: dict[tuple[str, str, int], dict[str, Any]]) -> str:
    validation_20 = row_map.get(("validation", "medium_term", 20))
    validation_60 = row_map.get(("validation", "long_term", 60))
    train_20 = row_map.get(("train", "medium_term", 20))
    train_60 = row_map.get(("train", "long_term", 60))
    if not validation_20 or not validation_60 or not train_20 or not train_60:
        return "样本不足"
    validation_baskets = min(int(validation_20.get("basket_count") or 0), int(validation_60.get("basket_count") or 0))
    validation_samples = min(int(validation_20.get("sample_count") or 0), int(validation_60.get("sample_count") or 0))
    if validation_baskets < 3 or validation_samples < 50:
        return "验证日篮不足"
    train_20_return = number(train_20.get("avg_return_pct"))
    train_60_return = number(train_60.get("avg_return_pct"))
    validation_20_return = number(validation_20.get("avg_return_pct"))
    validation_60_return = number(validation_60.get("avg_return_pct"))
    if None in {train_20_return, train_60_return, validation_20_return, validation_60_return}:
        return "收益数据不足"
    assert train_20_return is not None
    assert train_60_return is not None
    assert validation_20_return is not None
    assert validation_60_return is not None
    if train_60_return >= train_20_return + 3 and validation_60_return >= validation_20_return:
        return "60日更稳"
    if validation_60_return >= validation_20_return + 5 and train_60_return >= train_20_return:
        return "60日占优"
    if train_20_return >= train_60_return - 2 and validation_20_return >= validation_60_return - 2:
        return "20日可复核"
    return "继续观察"


def continuous_speed_horizon_selector_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 连续速度持有期选择观察",
        "",
        "- 这一节把同一连续速度 scope 去重后横向比较 20/60/120 日，用来判断速度指标是否能解释 horizon 漂移。单元格格式为 `样本 / 平均收益 / 日篮数`。",
        "",
        "| 速度 scope | 训练20日 | 训练60日 | 训练120日 | 验证20日 | 验证60日 | 验证120日 | 观察 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    seen_scopes: set[str] = set()
    has_rows = False
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        scope_id = continuous_speed_scope_id(str(rule.get("id") or ""))
        if not scope_id or scope_id in seen_scopes:
            continue
        seen_scopes.add(scope_id)
        row_map = horizon_profile_row_map(simulation)
        has_rows = True
        lines.append(
            f"| `{scope_id}` | "
            f"{horizon_selector_cell(row_map.get(('train', 'medium_term', 20)))} | "
            f"{horizon_selector_cell(row_map.get(('train', 'long_term', 60)))} | "
            f"{horizon_selector_cell(row_map.get(('train', 'long_term', 120)))} | "
            f"{horizon_selector_cell(row_map.get(('validation', 'medium_term', 20)))} | "
            f"{horizon_selector_cell(row_map.get(('validation', 'long_term', 60)))} | "
            f"{horizon_selector_cell(row_map.get(('validation', 'long_term', 120)))} | "
            f"{continuous_speed_horizon_verdict(row_map)} |"
        )
    if not has_rows:
        lines.append("| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |")
    return lines


def counterexample_factor_diagnostic_lines(
    simulations: list[dict[str, Any]],
    min_samples: int = 5,
    max_rows_per_period: int = 8,
) -> list[str]:
    lines = [
        "## 连续速度反例因子诊断",
        "",
        "- 这一节只看连续速度 60 日候选。对 sell/avoid 规则来说，`有效风控` 表示原卖出/回避方向正确，属于降级为观察的反例风险；`滞后误杀` 表示原卖出/回避方向错误，属于降级受益样本。",
        "",
        "| 规则 | 数据段 | 因子 | 取值 | 样本 | 有效风控 | 滞后误杀 | 有效风控率 | 有效风控均收益 | 滞后误杀均收益 | 平均回撤 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    period_labels = {"train": "训练段", "validation": "验证段", "all": "全样本", "unknown": "未知"}
    has_rows = False
    for simulation in simulations:
        rows = simulation.get("counterexample_factor_rows") or []
        if not rows:
            continue
        rule = simulation.get("rule") or {}
        rule_id = str(rule.get("id") or "")
        for period in ["train", "validation"]:
            period_rows = [
                row
                for row in rows
                if row.get("period") == period and int(row.get("sample_count") or 0) >= min_samples
            ]
            period_rows = sorted(
                period_rows,
                key=lambda row: (
                    -(number(row.get("correct_rate_pct")) or -1),
                    -int(row.get("sample_count") or 0),
                    str(row.get("factor_name") or ""),
                    str(row.get("factor_value") or ""),
                ),
            )[:max_rows_per_period]
            for row in period_rows:
                has_rows = True
                lines.append(
                    f"| `{rule_id}` | {period_labels.get(period, period)} | "
                    f"{row.get('factor_name')} | {row.get('factor_value')} | "
                    f"{row.get('sample_count', 0)} | {row.get('correct_count', 0)} | {row.get('wrong_count', 0)} | "
                    f"{pct(row.get('correct_rate_pct'))} | {pct(row.get('correct_avg_return_pct'))} | "
                    f"{pct(row.get('wrong_avg_return_pct'))} | {pct(row.get('avg_drawdown_pct'))} |"
                )
    if not has_rows:
        lines.append("| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 |")
    return lines


def neutralize_confidence_rows(simulations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        if str(rule.get("score_adjustment_mode") or "") != "neutralize_to_watch":
            continue
        if str(rule.get("signal_side") or "") != "sell_avoid":
            continue

        train = simulation.get("train") or {}
        validation = simulation.get("validation") or {}
        validation_basket = simulation.get("basket_validation") or {}
        train_lag_rate = number(train.get("neutralized_wrong_directional_rate_pct"))
        validation_lag_rate = number(validation.get("neutralized_wrong_directional_rate_pct"))
        validation_sample_count = int(validation.get("matched_count") or 0)
        validation_basket_count = int(validation_basket.get("basket_count") or 0)
        evidence_penalty = 0.0
        if validation_sample_count < 50 or validation_basket_count < 3:
            evidence_penalty = 20.0
        elif validation_sample_count < 100 or validation_basket_count < 6:
            evidence_penalty = 10.0

        if validation_lag_rate is None:
            confidence = None
            effective_risk_rate = None
        else:
            base_confidence = (
                validation_lag_rate * 0.6 + train_lag_rate * 0.4
                if train_lag_rate is not None
                else validation_lag_rate
            )
            confidence = max(0.0, min(100.0, base_confidence - evidence_penalty))
            effective_risk_rate = max(0.0, min(100.0, 100.0 - validation_lag_rate))

        if validation_sample_count <= 0:
            verdict = "无验证样本"
        elif validation_sample_count < 50 or validation_basket_count < 3:
            verdict = "样本不足，仅作阶段线索"
        elif confidence is None:
            verdict = "收益证据不足"
        elif confidence >= 75:
            verdict = "高确信降级观察"
        elif confidence >= 60:
            verdict = "中等确信降级"
        elif confidence >= 45:
            verdict = "低确信，仅复核"
        else:
            verdict = "偏保留风控"

        rows.append(
            {
                "rule_id": str(rule.get("id") or ""),
                "horizon": str(rule.get("horizon") or ""),
                "window_days": int(rule.get("window_days") or 0),
                "train_sample_count": int(train.get("matched_count") or 0),
                "validation_sample_count": validation_sample_count,
                "validation_basket_count": validation_basket_count,
                "train_lag_rate_pct": train_lag_rate,
                "validation_lag_rate_pct": validation_lag_rate,
                "effective_risk_rate_pct": effective_risk_rate,
                "neutralize_confidence_pct": round(confidence, 2) if confidence is not None else None,
                "validation_avg_basket_return_pct": validation_basket.get("avg_basket_return_pct"),
                "verdict": verdict,
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -(number(row.get("neutralize_confidence_pct")) or -1),
            -int(row.get("validation_sample_count") or 0),
            str(row.get("rule_id") or ""),
        ),
    )


def neutralize_confidence_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 卖出/回避观察降级确信度",
        "",
        "- 这一节把 `neutralize_to_watch` 的卖出/回避候选转成连续诊断分数。分数只用于离线复盘和人工复核排序，不写入 active，也不代表买入信号。",
        "- `有效风控率` 约等于验证段里原 sell/avoid 仍然正确的比例；这个比例越高，越应该给观察降级打折。",
        "",
        "| 规则 | 周期窗口 | 训练样本 | 验证样本 | 验证日篮 | 训练滞后率 | 验证滞后率 | 有效风控率 | 降级确信度 | 验证日篮均收益 | 观察 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = neutralize_confidence_rows(simulations)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| `{row.get('rule_id')}` | {horizon_label} {window_days}日 | "
            f"{row.get('train_sample_count', 0)} | {row.get('validation_sample_count', 0)} | "
            f"{row.get('validation_basket_count', 0)} | {pct(row.get('train_lag_rate_pct'))} | "
            f"{pct(row.get('validation_lag_rate_pct'))} | {pct(row.get('effective_risk_rate_pct'))} | "
            f"{pct(row.get('neutralize_confidence_pct'))} | {pct(row.get('validation_avg_basket_return_pct'))} | "
            f"{row.get('verdict')} |"
        )
    return lines


def neutralize_signal_review_rows(
    outcomes: list[dict[str, Any]],
    simulations: list[dict[str, Any]],
    limit: int | None = 30,
) -> list[dict[str, Any]]:
    confidence_by_rule = {row["rule_id"]: row for row in neutralize_confidence_rows(simulations)}
    review_by_signal: dict[tuple[str, str, str, int, str], dict[str, Any]] = {}
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        rule_id = str(rule.get("id") or "")
        confidence_row = confidence_by_rule.get(rule_id)
        if not confidence_row or confidence_row.get("neutralize_confidence_pct") is None:
            continue
        if confidence_row.get("verdict") == "无验证样本":
            continue
        for outcome in outcomes:
            if outcome.get("hit") is None or not candidate_rule_matches(outcome, rule):
                continue
            key = (
                str(outcome.get("stock_code") or ""),
                str(outcome.get("signal_trade_date") or ""),
                str(outcome.get("horizon") or ""),
                int(outcome.get("window_days") or 0),
                str(outcome.get("signal_label") or ""),
            )
            existing = review_by_signal.get(key)
            confidence = number(confidence_row.get("neutralize_confidence_pct")) or 0.0
            rule_entry = {
                "rule_id": rule_id,
                "neutralize_confidence_pct": confidence,
                "effective_risk_rate_pct": confidence_row.get("effective_risk_rate_pct"),
                "verdict": confidence_row.get("verdict"),
            }
            if existing is None:
                hit = outcome.get("hit")
                if hit is False:
                    outcome_type = "滞后误杀"
                elif hit is True:
                    outcome_type = "有效风控"
                else:
                    outcome_type = "未知"
                review_by_signal[key] = {
                    "stock_code": str(outcome.get("stock_code") or ""),
                    "stock_name": str(outcome.get("stock_name") or ""),
                    "signal_trade_date": str(outcome.get("signal_trade_date") or ""),
                    "horizon": str(outcome.get("horizon") or ""),
                    "window_days": int(outcome.get("window_days") or 0),
                    "signal_score": outcome.get("signal_score"),
                    "signal_label": str(outcome.get("signal_label") or ""),
                    "return_pct": outcome.get("return_pct"),
                    "max_drawdown_pct": outcome.get("max_drawdown_pct"),
                    "outcome_type": outcome_type,
                    "factors": dict(outcome.get("factors") or {}),
                    "rules": [rule_entry],
                    "neutralize_confidence_pct": confidence,
                    "effective_risk_rate_pct": confidence_row.get("effective_risk_rate_pct"),
                    "verdict": confidence_row.get("verdict"),
                    "top_rule_id": rule_id,
                }
            else:
                existing["rules"].append(rule_entry)
                if confidence > (number(existing.get("neutralize_confidence_pct")) or 0.0):
                    existing["neutralize_confidence_pct"] = confidence
                    existing["effective_risk_rate_pct"] = confidence_row.get("effective_risk_rate_pct")
                    existing["verdict"] = confidence_row.get("verdict")
                    existing["top_rule_id"] = rule_id

    rows = []
    for item in review_by_signal.values():
        rules = sorted(
            item.get("rules") or [],
            key=lambda row: (-(number(row.get("neutralize_confidence_pct")) or 0.0), str(row.get("rule_id") or "")),
        )
        item["rules"] = rules
        item["matched_rule_count"] = len(rules)
        rows.append(item)

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            0 if row.get("outcome_type") == "滞后误杀" else 1,
            -(number(row.get("neutralize_confidence_pct")) or 0.0),
            str(row.get("signal_trade_date") or ""),
            str(row.get("stock_code") or ""),
        ),
    )
    return sorted_rows if limit is None else sorted_rows[:limit]


def neutralize_signal_daily_summary_rows(
    outcomes: list[dict[str, Any]],
    simulations: list[dict[str, Any]],
    limit: int | None = 20,
) -> list[dict[str, Any]]:
    signal_rows = neutralize_signal_review_rows(outcomes, simulations, limit=None)
    daily: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in signal_rows:
        key = (
            str(row.get("signal_trade_date") or ""),
            str(row.get("horizon") or ""),
            int(row.get("window_days") or 0),
        )
        bucket = daily.setdefault(
            key,
            {
                "signal_trade_date": key[0],
                "horizon": key[1],
                "window_days": key[2],
                "signal_count": 0,
                "lagging_false_negative_count": 0,
                "effective_risk_count": 0,
                "return_values": [],
                "drawdown_values": [],
                "confidence_values": [],
                "rule_counts": {},
            },
        )
        bucket["signal_count"] += 1
        if row.get("outcome_type") == "滞后误杀":
            bucket["lagging_false_negative_count"] += 1
        elif row.get("outcome_type") == "有效风控":
            bucket["effective_risk_count"] += 1
        return_value = number(row.get("return_pct"))
        if return_value is not None:
            bucket["return_values"].append(return_value)
        drawdown_value = number(row.get("max_drawdown_pct"))
        if drawdown_value is not None:
            bucket["drawdown_values"].append(drawdown_value)
        confidence_value = number(row.get("neutralize_confidence_pct"))
        if confidence_value is not None:
            bucket["confidence_values"].append(confidence_value)
        top_rule_id = str(row.get("top_rule_id") or "")
        if top_rule_id:
            rule_counts = bucket["rule_counts"]
            rule_counts[top_rule_id] = int(rule_counts.get(top_rule_id) or 0) + 1

    rows: list[dict[str, Any]] = []
    for bucket in daily.values():
        return_values = bucket.pop("return_values")
        drawdown_values = bucket.pop("drawdown_values")
        confidence_values = bucket.pop("confidence_values")
        rule_counts = bucket.pop("rule_counts")
        top_rule_id = ""
        top_rule_count = 0
        if rule_counts:
            top_rule_id, top_rule_count = sorted(
                rule_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )[0]
        signal_count = int(bucket.get("signal_count") or 0)
        bucket.update(
            {
                "lagging_false_negative_rate_pct": (
                    round(int(bucket.get("lagging_false_negative_count") or 0) / signal_count * 100, 2)
                    if signal_count
                    else None
                ),
                "avg_return_pct": round(sum(return_values) / len(return_values), 2) if return_values else None,
                "worst_return_pct": round(min(return_values), 2) if return_values else None,
                "avg_drawdown_pct": round(sum(drawdown_values) / len(drawdown_values), 2) if drawdown_values else None,
                "avg_neutralize_confidence_pct": (
                    round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None
                ),
                "top_rule_id": top_rule_id,
                "top_rule_count": top_rule_count,
                "distinct_top_rule_count": len(rule_counts),
            }
        )
        rows.append(bucket)

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -(number(row.get("avg_neutralize_confidence_pct")) or 0.0),
            -int(row.get("signal_count") or 0),
            str(row.get("signal_trade_date") or ""),
        ),
    )
    return sorted_rows if limit is None else sorted_rows[:limit]


def neutralize_signal_stage_block_rows(
    outcomes: list[dict[str, Any]],
    simulations: list[dict[str, Any]],
    limit_per_bucket: int = 12,
) -> list[dict[str, Any]]:
    daily_rows = neutralize_signal_daily_summary_rows(outcomes, simulations, limit=None)
    stage_blocks: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for daily_row in daily_rows:
        signal_date = str(daily_row.get("signal_trade_date") or "")
        if len(signal_date) < 7:
            continue
        buckets = [("月度", signal_date[:7])]
        if len(signal_date) >= 10:
            month = int(signal_date[5:7])
            quarter = (month - 1) // 3 + 1
            buckets.append(("季度", f"{signal_date[:4]}-Q{quarter}"))
        for bucket_type, period in buckets:
            key = (
                bucket_type,
                period,
                str(daily_row.get("horizon") or ""),
                int(daily_row.get("window_days") or 0),
            )
            bucket = stage_blocks.setdefault(
                key,
                {
                    "bucket_type": bucket_type,
                    "period": period,
                    "horizon": key[2],
                    "window_days": key[3],
                    "daily_basket_count": 0,
                    "signal_count": 0,
                    "lagging_false_negative_count": 0,
                    "effective_risk_count": 0,
                    "effective_risk_dominant_day_count": 0,
                    "avg_daily_return_values": [],
                    "avg_confidence_values": [],
                    "worst_daily_basket_return_pct": None,
                    "worst_daily_basket_date": "",
                },
            )
            bucket["daily_basket_count"] += 1
            bucket["signal_count"] += int(daily_row.get("signal_count") or 0)
            bucket["lagging_false_negative_count"] += int(daily_row.get("lagging_false_negative_count") or 0)
            bucket["effective_risk_count"] += int(daily_row.get("effective_risk_count") or 0)
            if int(daily_row.get("effective_risk_count") or 0) > int(
                daily_row.get("lagging_false_negative_count") or 0
            ):
                bucket["effective_risk_dominant_day_count"] += 1
            daily_return = number(daily_row.get("avg_return_pct"))
            if daily_return is not None:
                bucket["avg_daily_return_values"].append(daily_return)
                worst_return = number(bucket.get("worst_daily_basket_return_pct"))
                if worst_return is None or daily_return < worst_return:
                    bucket["worst_daily_basket_return_pct"] = daily_return
                    bucket["worst_daily_basket_date"] = signal_date
            confidence = number(daily_row.get("avg_neutralize_confidence_pct"))
            if confidence is not None:
                bucket["avg_confidence_values"].append(confidence)

    rows: list[dict[str, Any]] = []
    for bucket in stage_blocks.values():
        avg_daily_return_values = bucket.pop("avg_daily_return_values")
        avg_confidence_values = bucket.pop("avg_confidence_values")
        signal_count = int(bucket.get("signal_count") or 0)
        daily_basket_count = int(bucket.get("daily_basket_count") or 0)
        bucket.update(
            {
                "lagging_false_negative_rate_pct": (
                    round(
                        int(bucket.get("lagging_false_negative_count") or 0) / signal_count * 100,
                        2,
                    )
                    if signal_count
                    else None
                ),
                "avg_daily_basket_return_pct": (
                    round(sum(avg_daily_return_values) / len(avg_daily_return_values), 2)
                    if avg_daily_return_values
                    else None
                ),
                "avg_neutralize_confidence_pct": (
                    round(sum(avg_confidence_values) / len(avg_confidence_values), 2)
                    if avg_confidence_values
                    else None
                ),
                "effective_risk_dominant_day_share_pct": (
                    round(int(bucket.get("effective_risk_dominant_day_count") or 0) / daily_basket_count * 100, 2)
                    if daily_basket_count
                    else None
                ),
            }
        )
        rows.append(bucket)

    limited_rows: list[dict[str, Any]] = []
    for bucket_type in ("月度", "季度"):
        bucket_rows = [row for row in rows if row.get("bucket_type") == bucket_type]
        limited_rows.extend(
            sorted(
                bucket_rows,
                key=lambda row: (
                    -(number(row.get("avg_neutralize_confidence_pct")) or 0.0),
                    -int(row.get("daily_basket_count") or 0),
                    str(row.get("period") or ""),
                ),
            )[:limit_per_bucket]
        )
    return limited_rows


def neutralize_signal_stage_block_lines(outcomes: list[dict[str, Any]], simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 高确信观察降级阶段块汇总",
        "",
        "- 这一节把交易日篮继续聚合到月度和季度，检查高确信降级样本是不是只集中在少数交易日。",
        "",
        "| 粒度 | 阶段 | 周期窗口 | 日篮 | 样本 | 滞后误杀 | 有效风控 | 滞后率 | 日篮均收益 | 最差日篮 | 最差日篮日期 | 平均确信度 | 有效风控占优日 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    rows = neutralize_signal_stage_block_rows(outcomes, simulations)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| {row.get('bucket_type')} | {row.get('period')} | {horizon_label} {window_days}日 | "
            f"{row.get('daily_basket_count', 0)} | {row.get('signal_count', 0)} | "
            f"{row.get('lagging_false_negative_count', 0)} | {row.get('effective_risk_count', 0)} | "
            f"{pct(row.get('lagging_false_negative_rate_pct'))} | "
            f"{pct(row.get('avg_daily_basket_return_pct'))} | "
            f"{pct(row.get('worst_daily_basket_return_pct'))} | {row.get('worst_daily_basket_date')} | "
            f"{pct(row.get('avg_neutralize_confidence_pct'))} | "
            f"{pct(row.get('effective_risk_dominant_day_share_pct'))} |"
        )
    return lines


def neutralize_signal_stage_factor_profile_rows(
    outcomes: list[dict[str, Any]],
    simulations: list[dict[str, Any]],
    factor_names: list[str] | None = None,
    limit: int = 220,
) -> list[dict[str, Any]]:
    names = factor_names or DEFAULT_STAGE_BLOCK_PROFILE_FACTORS
    signal_rows = neutralize_signal_review_rows(outcomes, simulations, limit=None)
    stage_blocks = neutralize_signal_stage_block_rows(outcomes, simulations)
    stage_keys = {
        (
            str(block.get("bucket_type") or ""),
            str(block.get("period") or ""),
            str(block.get("horizon") or ""),
            int(block.get("window_days") or 0),
        )
        for block in stage_blocks
    }
    grouped: dict[tuple[str, str, str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    stage_totals: dict[tuple[str, str, str, int], int] = defaultdict(int)
    for row in signal_rows:
        signal_date = str(row.get("signal_trade_date") or "")
        if len(signal_date) < 7:
            continue
        month_key = (
            "月度",
            signal_date[:7],
            str(row.get("horizon") or ""),
            int(row.get("window_days") or 0),
        )
        keys = [month_key]
        if len(signal_date) >= 10:
            month = int(signal_date[5:7])
            quarter = (month - 1) // 3 + 1
            keys.append(("季度", f"{signal_date[:4]}-Q{quarter}", month_key[2], month_key[3]))
        factors = row.get("factors") or {}
        for stage_key in keys:
            if stage_key not in stage_keys:
                continue
            stage_totals[stage_key] += 1
            for factor_name in names:
                factor_value = str(factors.get(factor_name) or "未知")
                grouped[(*stage_key, factor_name, factor_value)].append(row)

    dominant: dict[tuple[str, str, str, int, str], tuple[str, list[dict[str, Any]]]] = {}
    for (*stage_key, factor_name, factor_value), rows in grouped.items():
        dominant_key = (*stage_key, factor_name)
        existing = dominant.get(dominant_key)
        if existing is None or len(rows) > len(existing[1]) or (
            len(rows) == len(existing[1]) and factor_value < existing[0]
        ):
            dominant[dominant_key] = (factor_value, rows)

    factor_order = {name: index for index, name in enumerate(names)}
    result_rows: list[dict[str, Any]] = []
    for (bucket_type, period, horizon, window_days, factor_name), (factor_value, rows) in dominant.items():
        stage_total = stage_totals.get((bucket_type, period, horizon, window_days), 0)
        lagging = [row for row in rows if row.get("outcome_type") == "滞后误杀"]
        effective = [row for row in rows if row.get("outcome_type") == "有效风控"]
        result_rows.append(
            {
                "bucket_type": bucket_type,
                "period": period,
                "horizon": horizon,
                "window_days": window_days,
                "factor_name": factor_name,
                "factor_value": factor_value,
                "sample_count": len(rows),
                "stage_sample_share_pct": round(len(rows) / stage_total * 100, 2) if stage_total else None,
                "lagging_false_negative_count": len(lagging),
                "effective_risk_count": len(effective),
                "lagging_false_negative_rate_pct": len(lagging) / len(rows) * 100 if rows else None,
                "avg_return_pct": average(row.get("return_pct") for row in rows),
                "avg_neutralize_confidence_pct": average(row.get("neutralize_confidence_pct") for row in rows),
            }
        )

    return sorted(
        result_rows,
        key=lambda row: (
            0 if row.get("bucket_type") == "季度" else 1,
            str(row.get("period") or ""),
            *horizon_window_sort_key(str(row.get("horizon") or ""), int(row.get("window_days") or 0)),
            factor_order.get(str(row.get("factor_name") or ""), 999),
        ),
    )[:limit]


def neutralize_signal_stage_factor_profile_lines(
    outcomes: list[dict[str, Any]],
    simulations: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "## 高确信观察降级阶段因子画像",
        "",
        "- 这一节为每个高确信阶段块列出关键因子的主导取值，用来解释阶段差异，而不是生成自动调分规则。",
        "",
        "| 粒度 | 阶段 | 周期窗口 | 因子 | 主导取值 | 覆盖样本 | 阶段占比 | 滞后误杀 | 有效风控 | 滞后率 | 平均收益 | 平均确信度 |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = neutralize_signal_stage_factor_profile_rows(outcomes, simulations)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| {row.get('bucket_type')} | {row.get('period')} | {horizon_label} {window_days}日 | "
            f"{row.get('factor_name')} | {row.get('factor_value')} | {row.get('sample_count', 0)} | "
            f"{pct(row.get('stage_sample_share_pct'))} | {row.get('lagging_false_negative_count', 0)} | "
            f"{row.get('effective_risk_count', 0)} | {pct(row.get('lagging_false_negative_rate_pct'))} | "
            f"{pct(row.get('avg_return_pct'))} | {pct(row.get('avg_neutralize_confidence_pct'))} |"
        )
    return lines


def horizon_selection_pair_key(outcome: dict[str, Any]) -> tuple[str, str]:
    return (
        str(outcome.get("stock_code") or ""),
        str(outcome.get("signal_trade_date") or ""),
    )


def quarter_for_signal_date(value: Any) -> str | None:
    parsed = sfa.parse_date_like(value)
    if parsed is None:
        return None
    quarter = (parsed.month - 1) // 3 + 1
    return f"{parsed.year}-Q{quarter}"


def profile_matches_factors(factors: dict[str, Any], profile: dict[str, Any]) -> bool:
    return all(factor_value_matches(factors.get(name), expected) for name, expected in profile.items())


def summarize_horizon_selection_pairs(items: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    medium_effective = [pair for pair in items if pair[0].get("hit") is True]
    medium_lagging = [pair for pair in items if pair[0].get("hit") is False]
    long_effective = [pair for pair in items if pair[1].get("hit") is True]
    long_lagging = [pair for pair in items if pair[1].get("hit") is False]
    transition_pairs = [pair for pair in items if pair[0].get("hit") is True and pair[1].get("hit") is False]
    both_lagging = [pair for pair in items if pair[0].get("hit") is False and pair[1].get("hit") is False]
    both_effective = [pair for pair in items if pair[0].get("hit") is True and pair[1].get("hit") is True]
    medium_returns = [number(pair[0].get("return_pct")) for pair in items]
    long_returns = [number(pair[1].get("return_pct")) for pair in items]
    return_deltas = [
        long_return - medium_return
        for medium_return, long_return in zip(medium_returns, long_returns)
        if medium_return is not None and long_return is not None
    ]
    pair_count = len(items)
    return {
        "pair_count": pair_count,
        "medium_effective_risk_count": len(medium_effective),
        "medium_lagging_count": len(medium_lagging),
        "long_effective_risk_count": len(long_effective),
        "long_lagging_count": len(long_lagging),
        "medium_effective_risk_rate_pct": len(medium_effective) / pair_count * 100 if pair_count else None,
        "long_lagging_rate_pct": len(long_lagging) / pair_count * 100 if pair_count else None,
        "risk_to_lag_count": len(transition_pairs),
        "risk_to_lag_rate_pct": len(transition_pairs) / pair_count * 100 if pair_count else None,
        "both_lagging_count": len(both_lagging),
        "both_effective_risk_count": len(both_effective),
        "medium_avg_return_pct": average(pair[0].get("return_pct") for pair in items),
        "long_avg_return_pct": average(pair[1].get("return_pct") for pair in items),
        "long_minus_medium_return_pct": average(return_deltas),
    }


def paired_horizon_selection_outcomes(outcomes: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    medium_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    long_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for outcome in outcomes:
        if signal_side(outcome) != "sell_avoid" or outcome.get("hit") is None:
            continue
        horizon = str(outcome.get("horizon") or "")
        window_days = int(outcome.get("window_days") or 0)
        if horizon == "medium_term" and window_days == 20:
            medium_by_key[horizon_selection_pair_key(outcome)] = outcome
        elif horizon == "long_term" and window_days == 60:
            long_by_key[horizon_selection_pair_key(outcome)] = outcome
    return [(medium_by_key[key], long_by_key[key]) for key in sorted(medium_by_key.keys() & long_by_key.keys())]


def horizon_selection_verdict(row: dict[str, Any]) -> str:
    risk_to_lag_rate = number(row.get("risk_to_lag_rate_pct")) or 0.0
    long_lag_rate = number(row.get("long_lagging_rate_pct")) or 0.0
    medium_effective_rate = number(row.get("medium_effective_risk_rate_pct")) or 0.0
    if risk_to_lag_rate >= 50 and long_lag_rate >= 70:
        return "20日风控转60日滞后"
    if medium_effective_rate >= 60 and long_lag_rate < 50:
        return "偏保留20日风控"
    if long_lag_rate >= 70:
        return "60日滞后主导"
    return "混合，继续复核"


def horizon_selection_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or HORIZON_SELECTION_PROFILES
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        quarters = ["全样本"]
        quarter = quarter_for_signal_date(medium.get("signal_trade_date"))
        if quarter:
            quarters.append(quarter)
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            for quarter_key in quarters:
                grouped[(profile_name, quarter_key)].append((medium, long))

    rows: list[dict[str, Any]] = []
    quarter_order = {"全样本": 0}
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, quarter_key), items in grouped.items():
        row = {
            "profile": profile_name,
            "period": quarter_key,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            quarter_order.get(str(row.get("period") or ""), 1),
            str(row.get("period") or ""),
        ),
    )


def horizon_selection_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日持有期选择验证",
        "",
        "- 这一节把同一股票、同一信号日的中期20日和长期60日结果配对，专门检验弱势尾部里 20 日风控是否会在 60 日变成滞后误杀。",
        "",
        "| 条件 | 阶段 | 配对样本 | 20日有效风控 | 20日滞后 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_selection_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('period')} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {row.get('medium_lagging_count', 0)} | "
            f"{pct(row.get('long_lagging_rate_pct'))} | {pct(row.get('risk_to_lag_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{pct(row.get('long_minus_medium_return_pct'))} | {row.get('verdict')} |"
        )
    return lines


def horizon_selection_factor_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    factor_names: list[str] | None = None,
    min_pair_count: int = 30,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or HORIZON_SELECTION_PROFILES
    selected_factors = factor_names or DEFAULT_HORIZON_SELECTION_FACTOR_NAMES
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            for factor_name in selected_factors:
                factor_value = factors.get(factor_name)
                if factor_value is None or str(factor_value) == "":
                    continue
                grouped[(profile_name, factor_name, str(factor_value))].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    factor_order = {name: index for index, name in enumerate(selected_factors)}
    for (profile_name, factor_name, factor_value), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        row = {
            "profile": profile_name,
            "factor_name": factor_name,
            "factor_value": factor_value,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            factor_order.get(str(row.get("factor_name") or ""), 999),
            -(number(row.get("pair_count")) or 0),
            str(row.get("factor_value") or ""),
        ),
    )


def horizon_selection_factor_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日阶段因子解释",
        "",
        "- 这一节把同股同日的 20/60 日配对样本按解释性因子分组，用来替代单纯季度标签，定位哪些状态更像 20 日风控或 60 日滞后。",
        "",
        "| 条件 | 因子 | 取值 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_selection_factor_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('factor_name')} | {row.get('factor_value')} | "
            f"{row.get('pair_count', 0)} | {pct(row.get('medium_effective_risk_rate_pct'))} | "
            f"{pct(row.get('long_lagging_rate_pct'))} | {pct(row.get('risk_to_lag_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{pct(row.get('long_minus_medium_return_pct'))} | {row.get('verdict')} |"
        )
    return lines


def horizon_stage_classifier(factors: dict[str, Any]) -> dict[str, Any]:
    lag_matches = [
        name for name, scope in HORIZON_STAGE_LAG_RULES if profile_matches_factors(factors, scope)
    ]
    counter_matches = [
        name for name, scope in HORIZON_STAGE_COUNTER_RULES if profile_matches_factors(factors, scope)
    ]
    if lag_matches and counter_matches:
        category = "冲突继续复核"
        primary_reason = f"{lag_matches[0]} / {counter_matches[0]}"
    elif lag_matches:
        category = "60日滞后优先复核"
        primary_reason = lag_matches[0]
    elif counter_matches:
        category = "反例口袋继续复核"
        primary_reason = counter_matches[0]
    else:
        category = "混合继续复核"
        primary_reason = "未命中阶段口袋"
    return {
        "category": category,
        "primary_reason": primary_reason,
        "lag_rule_count": len(lag_matches),
        "counter_rule_count": len(counter_matches),
        "lag_rules": lag_matches,
        "counter_rules": counter_matches,
    }


def horizon_stage_classifier_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    min_pair_count: int = 10,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            grouped[
                (
                    profile_name,
                    str(classification["category"]),
                    str(classification["primary_reason"]),
                )
            ].append((medium, long, classification))

    rows: list[dict[str, Any]] = []
    category_order = {
        "60日滞后优先复核": 0,
        "反例口袋继续复核": 1,
        "冲突继续复核": 2,
        "混合继续复核": 3,
    }
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, category, primary_reason), classified_items in grouped.items():
        if len(classified_items) < min_pair_count:
            continue
        pairs = [(medium, long) for medium, long, _classification in classified_items]
        row = {
            "profile": profile_name,
            "category": category,
            "primary_reason": primary_reason,
            **summarize_horizon_selection_pairs(pairs),
            "avg_lag_rule_count": average(item[2].get("lag_rule_count") for item in classified_items),
            "avg_counter_rule_count": average(item[2].get("counter_rule_count") for item in classified_items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            category_order.get(str(row.get("category") or ""), 999),
            -(number(row.get("pair_count")) or 0),
            str(row.get("primary_reason") or ""),
        ),
    )


def horizon_stage_classifier_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日多因子阶段分类器雏形",
        "",
        "- 这一节把阶段因子解释里的相对口袋组合成透明分类器，只用于报告诊断和人工复核排序，不自动调整评分。",
        "",
        "| 条件 | 分类 | 主导原因 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 60口袋均数 | 反例口袋均数 | 判断 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_classifier_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('category')} | {row.get('primary_reason')} | "
            f"{row.get('pair_count', 0)} | {pct(row.get('medium_effective_risk_rate_pct'))} | "
            f"{pct(row.get('long_lagging_rate_pct'))} | {pct(row.get('risk_to_lag_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{pct(row.get('long_minus_medium_return_pct'))} | {decimal(row.get('avg_lag_rule_count'))} | "
            f"{decimal(row.get('avg_counter_rule_count'))} | {row.get('verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_factor_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    factor_names: list[str] | None = None,
    min_pair_count: int = 30,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_factors = factor_names or DEFAULT_HORIZON_SELECTION_FACTOR_NAMES
    paired = paired_horizon_selection_outcomes(outcomes)
    mixed_pairs_by_profile: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    grouped: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            mixed_pairs_by_profile[profile_name].append((medium, long))
            for factor_name in selected_factors:
                factor_value = factors.get(factor_name)
                if factor_value is None or str(factor_value) == "":
                    continue
                grouped[(profile_name, factor_name, str(factor_value))].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    factor_order = {name: index for index, name in enumerate(selected_factors)}
    for (profile_name, factor_name, factor_value), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        bucket_pair_count = len(mixed_pairs_by_profile.get(profile_name) or [])
        row = {
            "profile": profile_name,
            "factor_name": factor_name,
            "factor_value": factor_value,
            "bucket_pair_count": bucket_pair_count,
            "bucket_share_pct": len(items) / bucket_pair_count * 100 if bucket_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            factor_order.get(str(row.get("factor_name") or ""), 999),
            -(number(row.get("pair_count")) or 0),
            str(row.get("factor_value") or ""),
        ),
    )


def horizon_stage_mixed_bucket_factor_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日未命中混合桶拆解",
        "",
        "- 这一节只拆多因子分类器里 `混合继续复核 / 未命中阶段口袋` 的配对样本，寻找下一轮分类器可以继续吸收或排除的因子。",
        "",
        "| 条件 | 因子 | 取值 | 混合桶占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_factor_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('factor_name')} | {row.get('factor_value')} | "
            f"{pct(row.get('bucket_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_pair_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    factor_pairs: list[tuple[str, str]] | None = None,
    min_pair_count: int = 30,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_pairs = factor_pairs or DEFAULT_HORIZON_STAGE_MIXED_PAIR_FACTORS
    paired = paired_horizon_selection_outcomes(outcomes)
    mixed_pairs_by_profile: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    grouped: dict[tuple[str, str, str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            mixed_pairs_by_profile[profile_name].append((medium, long))
            for left_name, right_name in selected_pairs:
                left_value = factors.get(left_name)
                right_value = factors.get(right_name)
                if left_value is None or right_value is None:
                    continue
                if str(left_value) == "" or str(right_value) == "":
                    continue
                grouped[
                    (
                        profile_name,
                        left_name,
                        str(left_value),
                        right_name,
                        str(right_value),
                    )
                ].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    pair_order = {pair: index for index, pair in enumerate(selected_pairs)}
    for (profile_name, left_name, left_value, right_name, right_value), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        bucket_pair_count = len(mixed_pairs_by_profile.get(profile_name) or [])
        row = {
            "profile": profile_name,
            "left_factor_name": left_name,
            "left_factor_value": left_value,
            "right_factor_name": right_name,
            "right_factor_value": right_value,
            "factor_pair": f"{left_name} + {right_name}",
            "factor_values": f"{left_value} + {right_value}",
            "bucket_pair_count": bucket_pair_count,
            "bucket_share_pct": len(items) / bucket_pair_count * 100 if bucket_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            pair_order.get(
                (
                    str(row.get("left_factor_name") or ""),
                    str(row.get("right_factor_name") or ""),
                ),
                999,
            ),
            -(number(row.get("pair_count")) or 0),
            str(row.get("factor_values") or ""),
        ),
    )


def horizon_stage_mixed_bucket_pair_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日未命中混合桶二阶组合拆解",
        "",
        "- 这一节继续拆 `混合继续复核 / 未命中阶段口袋`，只看市场修复速度与量能、尾部位置、尾部修复信号的二阶组合，用于寻找降确信或继续吸收的候选线索。",
        "",
        "| 条件 | 因子组合 | 取值组合 | 混合桶占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_pair_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('factor_pair')} | {row.get('factor_values')} | "
            f"{pct(row.get('bucket_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_target_fold_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    target_scope: dict[str, Any] | None = None,
    buckets: tuple[str, ...] = ("month", "quarter"),
    min_pair_count: int = 10,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_scope = DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE if target_scope is None else target_scope
    paired = paired_horizon_selection_outcomes(outcomes)
    target_pairs_by_profile: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    grouped: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        if not profile_matches_factors(factors, selected_scope):
            continue
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            target_pairs_by_profile[profile_name].append((medium, long))
            for bucket in buckets:
                bucket_key = fold_bucket_for_date(medium.get("signal_trade_date"), bucket)
                grouped[(profile_name, bucket, bucket_key)].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    bucket_order = {bucket: index for index, bucket in enumerate(buckets)}
    for (profile_name, bucket, bucket_key), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        target_pair_count = len(target_pairs_by_profile.get(profile_name) or [])
        row = {
            "profile": profile_name,
            "bucket": bucket,
            "bucket_label": "季度" if bucket == "quarter" else "月度",
            "period": bucket_key,
            "target_pair_count": target_pair_count,
            "target_share_pct": len(items) / target_pair_count * 100 if target_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            bucket_order.get(str(row.get("bucket") or ""), 999),
            str(row.get("period") or ""),
        ),
    )


def horizon_stage_mixed_bucket_target_fold_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日速度分化低位折叠验证",
        "",
        "- 这一节只看 `混合继续复核 / 未命中阶段口袋` 里的 `market_repair_speed_profile=速度分化` 且 `market_tail_extreme=弱势低位` 样本，按月度和季度折叠，验证降确信线索是否集中在少数阶段块。",
        "",
        "| 条件 | 折叠 | 阶段 | 目标占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_target_fold_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('bucket_label')} | {row.get('period')} | "
            f"{pct(row.get('target_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_target_daily_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    target_scope: dict[str, Any] | None = None,
    min_pair_count: int = 5,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_scope = DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE if target_scope is None else target_scope
    paired = paired_horizon_selection_outcomes(outcomes)
    target_pairs_by_profile: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        if not profile_matches_factors(factors, selected_scope):
            continue
        signal_date = str(medium.get("signal_trade_date") or "")
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            target_pairs_by_profile[profile_name].append((medium, long))
            grouped[(profile_name, signal_date)].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, signal_date), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        target_pair_count = len(target_pairs_by_profile.get(profile_name) or [])
        row = {
            "profile": profile_name,
            "signal_trade_date": signal_date,
            "month": fold_bucket_for_date(signal_date, "month"),
            "quarter": fold_bucket_for_date(signal_date, "quarter"),
            "target_pair_count": target_pair_count,
            "target_share_pct": len(items) / target_pair_count * 100 if target_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["verdict"] = horizon_selection_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            str(row.get("signal_trade_date") or ""),
        ),
    )


def horizon_stage_mixed_bucket_target_daily_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日速度分化低位日篮验证",
        "",
        "- 这一节继续下钻 `market_repair_speed_profile=速度分化` 且 `market_tail_extreme=弱势低位`，按具体信号日聚合，解释同一季度或月份内部为什么会分化。",
        "",
        "| 条件 | 信号日 | 月度 | 季度 | 目标占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_target_daily_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('signal_trade_date')} | {row.get('month')} | "
            f"{row.get('quarter')} | {pct(row.get('target_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('verdict')} |"
        )
    return lines


def factor_value_summary(
    items: list[tuple[dict[str, Any], dict[str, Any]]],
    factor_names: list[str],
    max_factors: int = 4,
) -> str:
    parts: list[str] = []
    for factor_name in factor_names:
        counts: dict[str, int] = defaultdict(int)
        total = 0
        for medium, long in items:
            factors = medium.get("factors") or long.get("factors") or {}
            value = factors.get(factor_name)
            if value is None or str(value) == "":
                continue
            counts[str(value)] += 1
            total += 1
        if not counts or total == 0:
            continue
        top_value, top_count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
        parts.append(f"{factor_name}={top_value}({top_count}/{total},{top_count / total * 100:.0f}%)")
    return "; ".join(parts[:max_factors]) if parts else "暂无"


def factor_value_share_pct(
    items: list[tuple[dict[str, Any], dict[str, Any]]],
    factor_name: str,
    accepted_values: set[str],
) -> float | None:
    total = 0
    matched = 0
    for medium, long in items:
        factors = medium.get("factors") or long.get("factors") or {}
        value = factors.get(factor_name)
        if value is None or str(value) == "":
            continue
        total += 1
        if str(value) in accepted_values:
            matched += 1
    return matched / total * 100 if total else None


def horizon_stage_mixed_bucket_target_daily_context_verdict(row: dict[str, Any]) -> str:
    long_lag_rate = number(row.get("long_lagging_rate_pct")) or 0.0
    long_avg_return = number(row.get("long_avg_return_pct")) or 0.0
    medium_avg_return = number(row.get("medium_avg_return_pct")) or 0.0
    if long_lag_rate >= 65 and long_avg_return > 0:
        return "仍偏60日滞后，不能降级"
    if long_lag_rate < 50 and long_avg_return < 0:
        return "60日风险兑现，削弱滞后假设"
    if medium_avg_return < 0 and long_avg_return > 0:
        return "20日风控后转60日滞后"
    return "混合，继续复核"


def horizon_stage_mixed_bucket_target_daily_context_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    target_scope: dict[str, Any] | None = None,
    market_factor_names: list[str] | None = None,
    stock_factor_names: list[str] | None = None,
    min_pair_count: int = 5,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_scope = DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE if target_scope is None else target_scope
    selected_market_factors = market_factor_names or DEFAULT_HORIZON_STAGE_DAILY_MARKET_CONTEXT_FACTORS
    selected_stock_factors = stock_factor_names or DEFAULT_HORIZON_STAGE_DAILY_STOCK_CONTEXT_FACTORS
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        if not profile_matches_factors(factors, selected_scope):
            continue
        signal_date = str(medium.get("signal_trade_date") or "")
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            grouped[(profile_name, signal_date)].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, signal_date), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        row = {
            "profile": profile_name,
            "signal_trade_date": signal_date,
            "pair_count": len(items),
            "market_visible_context": factor_value_summary(items, selected_market_factors),
            "stock_visible_context": factor_value_summary(items, selected_stock_factors),
            **summarize_horizon_selection_pairs(items),
        }
        row["context_verdict"] = horizon_stage_mixed_bucket_target_daily_context_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            str(row.get("signal_trade_date") or ""),
        ),
    )


def horizon_stage_mixed_bucket_target_daily_context_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日速度分化低位日篮可见变量对比",
        "",
        "- 这一节只用信号日前已计算出的市场与个股因子，解释同一目标桶在不同信号日为何分化；未来收益只用于右侧结果验证。",
        "",
        "| 条件 | 信号日 | 配对样本 | 20日有效风控 | 60日滞后 | 20日均收益 | 60日均收益 | 市场可见状态 | 个股可见状态 | 复盘判断 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    rows = horizon_stage_mixed_bucket_target_daily_context_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('signal_trade_date')} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{row.get('market_visible_context')} | {row.get('stock_visible_context')} | "
            f"{row.get('context_verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_target_repair_breadth_verdict(row: dict[str, Any]) -> str:
    market_volume = number(row.get("market_volume_improved_pct")) or 0.0
    stock_macd = number(row.get("stock_macd_repair_improved_pct")) or 0.0
    long_lag_rate = number(row.get("long_lagging_rate_pct")) or 0.0
    if market_volume >= 50 and stock_macd >= 50 and long_lag_rate < 50:
        return "量能+MACD广度支持降确信"
    if market_volume < 50 and stock_macd < 50 and long_lag_rate >= 60:
        return "修复广度不足，仍偏60日滞后"
    if market_volume < 50 and stock_macd >= 50:
        return "个股修复但市场量能不足"
    if market_volume >= 50 and stock_macd < 50:
        return "市场量能改善但个股修复不足"
    return "混合，继续复核"


def repair_breadth_combo_label(row: dict[str, Any]) -> str:
    market_volume = number(row.get("market_volume_improved_pct")) or 0.0
    stock_macd = number(row.get("stock_macd_repair_improved_pct")) or 0.0
    market_label = "市场量能改善" if market_volume >= 50 else "市场量能未改善"
    stock_label = "个股MACD修复广" if stock_macd >= 50 else "个股MACD修复窄"
    return f"{market_label}+{stock_label}"


def repair_breadth_combo_label_from_factors(factors: dict[str, Any]) -> str:
    market_volume = str(factors.get("market_volume_expansion_speed") or "")
    stock_macd = str(factors.get("macd_repair_speed") or "")
    market_label = "市场量能改善" if market_volume in REPAIR_SPEED_IMPROVED_VALUES else "市场量能未改善"
    stock_label = "个股MACD修复" if stock_macd in REPAIR_SPEED_IMPROVED_VALUES else "个股MACD未修复"
    return f"{market_label}+{stock_label}"


def repair_breadth_pair_verdict(row: dict[str, Any]) -> str:
    combo = str(row.get("combo_label") or "")
    long_lag_rate = number(row.get("long_lagging_rate_pct")) or 0.0
    long_avg_return = number(row.get("long_avg_return_pct")) or 0.0
    if combo == "市场量能改善+个股MACD修复" and long_lag_rate < 50 and long_avg_return < 0:
        return "量能确认后60日风险兑现"
    if combo.startswith("市场量能未改善") and long_lag_rate >= 60:
        return "市场量能未确认，60日仍易滞后"
    if combo == "市场量能改善+个股MACD未修复":
        return "市场改善但个股修复不足"
    return "混合，继续复核"


def repair_breadth_stage_fold_verdict(row: dict[str, Any]) -> str:
    combo = str(row.get("combo_label") or "")
    long_lag_rate = number(row.get("long_lagging_rate_pct")) or 0.0
    long_avg_return = number(row.get("long_avg_return_pct")) or 0.0
    if combo == "市场量能改善+个股MACD修复" and long_lag_rate >= 65 and long_avg_return > 0:
        return "量能改善仍滞后，阶段不支持降确信"
    if combo == "市场量能改善+个股MACD修复" and long_lag_rate < 50:
        return "量能改善降确信成立"
    if combo == "市场量能未改善+个股MACD修复" and long_lag_rate >= 60:
        return "缺市场量能，偏60日滞后"
    return "混合，继续复核"


def horizon_stage_mixed_bucket_target_repair_breadth_pair_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    target_scope: dict[str, Any] | None = None,
    min_pair_count: int = 10,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_scope = DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE if target_scope is None else target_scope
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        if not profile_matches_factors(factors, selected_scope):
            continue
        combo_label = repair_breadth_combo_label_from_factors(factors)
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            grouped[(profile_name, combo_label)].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, combo_label), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        row = {
            "profile": profile_name,
            "combo_label": combo_label,
            **summarize_horizon_selection_pairs(items),
        }
        row["pair_verdict"] = repair_breadth_pair_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            -(int(row.get("pair_count") or 0)),
            str(row.get("combo_label") or ""),
        ),
    )


def horizon_stage_mixed_bucket_repair_breadth_pair_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    min_pair_count: int = 30,
) -> list[dict[str, Any]]:
    return horizon_stage_mixed_bucket_target_repair_breadth_pair_rows(
        outcomes,
        profiles=profiles,
        target_scope={},
        min_pair_count=min_pair_count,
    )


def horizon_stage_mixed_bucket_repair_breadth_stage_fold_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    factor_names: list[str] | None = None,
    combo_labels: set[str] | None = None,
    buckets: tuple[str, ...] = ("month", "quarter"),
    min_pair_count: int = 10,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_factors = factor_names or DEFAULT_REPAIR_BREADTH_STAGE_FOLD_FACTORS
    selected_combos = combo_labels or {
        "市场量能改善+个股MACD修复",
        "市场量能未改善+个股MACD修复",
    }
    paired = paired_horizon_selection_outcomes(outcomes)
    total_pairs_by_combo: dict[tuple[str, str], int] = defaultdict(int)
    grouped: dict[tuple[str, str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        combo_label = repair_breadth_combo_label_from_factors(factors)
        if combo_label not in selected_combos:
            continue
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            total_pairs_by_combo[(profile_name, combo_label)] += 1
            for bucket in buckets:
                period = fold_bucket_for_date(medium.get("signal_trade_date"), bucket)
                grouped[(profile_name, combo_label, bucket, period)].append((medium, long))
            for factor_name in selected_factors:
                factor_value = factors.get(factor_name)
                if factor_value is None or str(factor_value) == "":
                    continue
                grouped[(profile_name, combo_label, factor_name, str(factor_value))].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    fold_order = {name: index for index, name in enumerate([*buckets, *selected_factors])}
    combo_order = {name: index for index, name in enumerate(sorted(selected_combos))}
    for (profile_name, combo_label, fold_name, fold_value), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        total_pair_count = total_pairs_by_combo.get((profile_name, combo_label), 0)
        row = {
            "profile": profile_name,
            "combo_label": combo_label,
            "fold_name": fold_name,
            "fold_label": {"month": "月度", "quarter": "季度"}.get(fold_name, fold_name),
            "fold_value": fold_value,
            "combo_pair_count": total_pair_count,
            "combo_share_pct": len(items) / total_pair_count * 100 if total_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["stage_fold_verdict"] = repair_breadth_stage_fold_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            combo_order.get(str(row.get("combo_label") or ""), 999),
            fold_order.get(str(row.get("fold_name") or ""), 999),
            str(row.get("fold_value") or ""),
        ),
    )


def horizon_stage_mixed_bucket_target_repair_breadth_daily_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    target_scope: dict[str, Any] | None = None,
    min_pair_count: int = 5,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_scope = target_scope or DEFAULT_HORIZON_STAGE_MIXED_FOLD_SCOPE
    paired = paired_horizon_selection_outcomes(outcomes)
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        if not profile_matches_factors(factors, selected_scope):
            continue
        signal_date = str(medium.get("signal_trade_date") or "")
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            grouped[(profile_name, signal_date)].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    for (profile_name, signal_date), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        row = {
            "profile": profile_name,
            "signal_trade_date": signal_date,
            "pair_count": len(items),
            "market_volume_improved_pct": factor_value_share_pct(
                items,
                "market_volume_expansion_speed",
                REPAIR_SPEED_IMPROVED_VALUES,
            ),
            "market_macd_repair_improved_pct": factor_value_share_pct(
                items,
                "market_macd_repair_speed",
                REPAIR_SPEED_IMPROVED_VALUES,
            ),
            "stock_macd_repair_improved_pct": factor_value_share_pct(
                items,
                "macd_repair_speed",
                REPAIR_SPEED_IMPROVED_VALUES,
            ),
            "stock_volume_improved_pct": factor_value_share_pct(
                items,
                "volume_expansion_speed",
                REPAIR_SPEED_IMPROVED_VALUES,
            ),
            **summarize_horizon_selection_pairs(items),
        }
        row["combo_label"] = repair_breadth_combo_label(row)
        row["breadth_verdict"] = horizon_stage_mixed_bucket_target_repair_breadth_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            str(row.get("signal_trade_date") or ""),
        ),
    )


def summarize_repair_breadth_daily_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("profile") or ""), str(row.get("combo_label") or ""))].append(row)

    combo_rows: list[dict[str, Any]] = []
    for (profile_name, combo_label), items in grouped.items():
        pair_count = sum(int(item.get("pair_count") or 0) for item in items)
        if pair_count <= 0:
            continue
        combo_row = {
            "profile": profile_name,
            "combo_label": combo_label,
            "daily_basket_count": len(items),
            "pair_count": pair_count,
            "avg_market_volume_improved_pct": average(item.get("market_volume_improved_pct") for item in items),
            "avg_stock_macd_repair_improved_pct": average(
                item.get("stock_macd_repair_improved_pct") for item in items
            ),
            "medium_effective_risk_rate_pct": sum(
                int(item.get("medium_effective_risk_count") or 0) for item in items
            )
            / pair_count
            * 100,
            "long_lagging_rate_pct": sum(int(item.get("long_lagging_count") or 0) for item in items)
            / pair_count
            * 100,
            "medium_avg_return_pct": average(item.get("medium_avg_return_pct") for item in items),
            "long_avg_return_pct": average(item.get("long_avg_return_pct") for item in items),
        }
        combo_row["combo_verdict"] = horizon_stage_mixed_bucket_target_repair_breadth_verdict(
            {
                **combo_row,
                "market_volume_improved_pct": combo_row.get("avg_market_volume_improved_pct"),
                "stock_macd_repair_improved_pct": combo_row.get("avg_stock_macd_repair_improved_pct"),
            }
        )
        combo_rows.append(combo_row)

    return sorted(
        combo_rows,
        key=lambda row: (
            str(row.get("profile") or ""),
            -(int(row.get("pair_count") or 0)),
            str(row.get("combo_label") or ""),
        ),
    )


def horizon_stage_mixed_bucket_target_repair_breadth_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日速度分化低位修复广度验证",
        "",
        "- 这一节把目标日篮里的市场量能改善、市场 MACD 修复、个股 MACD 修复和个股量能改善转成覆盖率，验证 `2023-10-25` 与 `2023-12-21` 的分化是否能被信号日前可见的修复广度解释。",
        "",
        "### 日篮明细",
        "",
        "| 条件 | 信号日 | 配对样本 | 市场量能改善 | 市场MACD改善 | 个股MACD改善 | 个股量能改善 | 20日有效风控 | 60日滞后 | 20日均收益 | 60日均收益 | 组合 | 判断 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    rows = horizon_stage_mixed_bucket_target_repair_breadth_daily_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('signal_trade_date')} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('market_volume_improved_pct'))} | {pct(row.get('market_macd_repair_improved_pct'))} | "
            f"{pct(row.get('stock_macd_repair_improved_pct'))} | {pct(row.get('stock_volume_improved_pct'))} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{row.get('combo_label')} | {row.get('breadth_verdict')} |"
        )

    lines.extend(
        [
            "",
            "### 配对组合",
            "",
            "| 条件 | 组合 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    pair_rows = horizon_stage_mixed_bucket_target_repair_breadth_pair_rows(outcomes)
    if pair_rows:
        for row in pair_rows:
            lines.append(
                f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('pair_count', 0)} | "
                f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
                f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
                f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
                f"{row.get('pair_verdict')} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "### 组合折叠",
            "",
            "| 条件 | 组合 | 日篮数 | 配对样本 | 平均市场量能改善 | 平均个股MACD改善 | 20日有效风控 | 60日滞后 | 20日均收益 | 60日均收益 | 判断 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summarize_repair_breadth_daily_rows(rows):
        lines.append(
            f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('daily_basket_count', 0)} | "
            f"{row.get('pair_count', 0)} | {pct(row.get('avg_market_volume_improved_pct'))} | "
            f"{pct(row.get('avg_stock_macd_repair_improved_pct'))} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('medium_avg_return_pct'))} | {pct(row.get('long_avg_return_pct'))} | "
            f"{row.get('combo_verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_repair_breadth_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日混合桶市场量能门槛泛化验证",
        "",
        "- 这一节把范围从 `速度分化+弱势低位` 目标桶放宽到整个 `混合继续复核 / 未命中阶段口袋`，检验市场量能改善是否只是少数日篮特例，还是能在更大混合桶里继续解释 20/60 日分化。",
        "",
        "| 条件 | 组合 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_repair_breadth_pair_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('pair_verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_repair_breadth_stage_fold_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日混合桶量能门槛阶段折叠验证",
        "",
        "- 这一节只看整个 `混合继续复核 / 未命中阶段口袋` 中个股 MACD 已修复的组合，把市场量能改善/未改善分别按月度、季度和市场状态折叠，解释量能门槛为什么跨窗口不稳定。",
        "",
        "| 条件 | 组合 | 折叠 | 取值 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_repair_breadth_stage_fold_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('fold_label')} | "
            f"{row.get('fold_value')} | {pct(row.get('combo_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('stage_fold_verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_repair_breadth_continuous_stage_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日混合桶量能门槛连续阶段验证",
        "",
        "- 这一节只看整个 `混合继续复核 / 未命中阶段口袋` 中个股 MACD 已修复的组合，把市场量能持续性、市场 MACD 修复持续性、指数脱离低点程度和 20 日反弹伸展程度纳入复核；这些变量全部只使用信号日前可见序列。",
        "",
        "| 条件 | 组合 | 连续变量 | 取值 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_repair_breadth_stage_fold_rows(
        outcomes,
        factor_names=DEFAULT_REPAIR_BREADTH_CONTINUOUS_STAGE_FACTORS,
        buckets=(),
    )
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('fold_label')} | "
            f"{row.get('fold_value')} | {pct(row.get('combo_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('stage_fold_verdict')} |"
        )
    return lines


def horizon_stage_mixed_bucket_repair_breadth_continuous_combo_rows(
    outcomes: list[dict[str, Any]],
    profiles: list[tuple[str, dict[str, Any]]] | None = None,
    factor_pairs: list[tuple[str, str]] | None = None,
    combo_labels: set[str] | None = None,
    min_pair_count: int = 10,
) -> list[dict[str, Any]]:
    selected_profiles = profiles or [HORIZON_SELECTION_PROFILES[0]]
    selected_pairs = factor_pairs or DEFAULT_REPAIR_BREADTH_CONTINUOUS_COMBO_FACTORS
    selected_combos = combo_labels or {
        "市场量能改善+个股MACD修复",
        "市场量能未改善+个股MACD修复",
    }
    paired = paired_horizon_selection_outcomes(outcomes)
    total_pairs_by_combo: dict[tuple[str, str], int] = defaultdict(int)
    grouped: dict[
        tuple[str, str, str, str, str],
        list[tuple[dict[str, Any], dict[str, Any]]],
    ] = defaultdict(list)
    for medium, long in paired:
        factors = medium.get("factors") or long.get("factors") or {}
        classification = horizon_stage_classifier(factors)
        if classification.get("category") != "混合继续复核":
            continue
        combo_label = repair_breadth_combo_label_from_factors(factors)
        if combo_label not in selected_combos:
            continue
        for profile_name, profile_scope in selected_profiles:
            if not profile_matches_factors(factors, profile_scope):
                continue
            total_pairs_by_combo[(profile_name, combo_label)] += 1
            for left_name, right_name in selected_pairs:
                left_value = factors.get(left_name)
                right_value = factors.get(right_name)
                if left_value is None or right_value is None:
                    continue
                if str(left_value) == "" or str(right_value) == "":
                    continue
                grouped[
                    (
                        profile_name,
                        combo_label,
                        left_name,
                        str(left_value),
                        f"{right_name}={right_value}",
                    )
                ].append((medium, long))

    rows: list[dict[str, Any]] = []
    profile_order = {name: index for index, (name, _scope) in enumerate(selected_profiles)}
    combo_order = {name: index for index, name in enumerate(sorted(selected_combos))}
    pair_order = {pair: index for index, pair in enumerate(selected_pairs)}
    for (profile_name, combo_label, left_name, left_value, right_part), items in grouped.items():
        if len(items) < min_pair_count:
            continue
        right_name, right_value = right_part.split("=", 1)
        total_pair_count = total_pairs_by_combo.get((profile_name, combo_label), 0)
        row = {
            "profile": profile_name,
            "combo_label": combo_label,
            "left_factor_name": left_name,
            "left_factor_value": left_value,
            "right_factor_name": right_name,
            "right_factor_value": right_value,
            "factor_pair": f"{left_name} + {right_name}",
            "factor_values": f"{left_value} + {right_value}",
            "combo_pair_count": total_pair_count,
            "combo_share_pct": len(items) / total_pair_count * 100 if total_pair_count else None,
            **summarize_horizon_selection_pairs(items),
        }
        row["continuous_combo_verdict"] = repair_breadth_stage_fold_verdict(row)
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            profile_order.get(str(row.get("profile") or ""), 999),
            combo_order.get(str(row.get("combo_label") or ""), 999),
            pair_order.get(
                (
                    str(row.get("left_factor_name") or ""),
                    str(row.get("right_factor_name") or ""),
                ),
                999,
            ),
            -(int(row.get("pair_count") or 0)),
            str(row.get("factor_values") or ""),
        ),
    )


def horizon_stage_mixed_bucket_repair_breadth_continuous_combo_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 弱势尾部20/60日混合桶量能门槛连续组合验证",
        "",
        "- 这一节在连续阶段变量上做二阶组合，验证单变量无法解释的量能门槛分裂是否来自“量能持续性 + 市场反弹状态”或“量能持续性 + 个股 MACD 持续性”的交互。",
        "",
        "| 条件 | 组合 | 连续变量组合 | 取值组合 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = horizon_stage_mixed_bucket_repair_breadth_continuous_combo_rows(outcomes)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |",
        ]
    for row in rows:
        lines.append(
            f"| {row.get('profile')} | {row.get('combo_label')} | {row.get('factor_pair')} | "
            f"{row.get('factor_values')} | {pct(row.get('combo_share_pct'))} | {row.get('pair_count', 0)} | "
            f"{pct(row.get('medium_effective_risk_rate_pct'))} | {pct(row.get('long_lagging_rate_pct'))} | "
            f"{pct(row.get('risk_to_lag_rate_pct'))} | {pct(row.get('medium_avg_return_pct'))} | "
            f"{pct(row.get('long_avg_return_pct'))} | {pct(row.get('long_minus_medium_return_pct'))} | "
            f"{row.get('continuous_combo_verdict')} |"
        )
    return lines


def neutralize_signal_daily_summary_lines(outcomes: list[dict[str, Any]], simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 高确信观察降级交易日汇总",
        "",
        "- 这一节把单信号复核样本按交易日聚合，避免把同一天密集触发的股票误读成彼此独立证据。",
        "",
        "| 信号日 | 周期窗口 | 样本 | 滞后误杀 | 有效风控 | 滞后率 | 平均收益 | 最差收益 | 平均回撤 | 平均确信度 | 主导规则 | 主导规则样本 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    rows = neutralize_signal_daily_summary_rows(outcomes, simulations)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 |",
        ]
    for row in rows:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| {row.get('signal_trade_date')} | {horizon_label} {window_days}日 | "
            f"{row.get('signal_count', 0)} | {row.get('lagging_false_negative_count', 0)} | "
            f"{row.get('effective_risk_count', 0)} | {pct(row.get('lagging_false_negative_rate_pct'))} | "
            f"{pct(row.get('avg_return_pct'))} | {pct(row.get('worst_return_pct'))} | "
            f"{pct(row.get('avg_drawdown_pct'))} | {pct(row.get('avg_neutralize_confidence_pct'))} | "
            f"`{row.get('top_rule_id')}` | {row.get('top_rule_count', 0)} |"
        )
    return lines


def neutralize_signal_review_lines(outcomes: list[dict[str, Any]], simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 单信号观察降级复核样本",
        "",
        "- 这一节把规则级降级确信度映射回具体历史信号，只列复核优先级最高的样本；它使用未来收益判断历史结果，因此只用于离线复盘。",
        "",
        "| 股票 | 信号日 | 周期窗口 | 原分数/信号 | 后续收益 | 结果类型 | 最大回撤 | 降级确信度 | 有效风控率 | 命中规则数 | 最高确信规则 | 观察 |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    rows = neutralize_signal_review_rows(outcomes, simulations)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 |",
        ]
    for row in rows:
        horizon = str(row.get("horizon") or "")
        window_days = int(row.get("window_days") or 0)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)
        stock_label = f"{row.get('stock_code')} {row.get('stock_name')}".strip()
        lines.append(
            f"| {stock_label} | {row.get('signal_trade_date')} | {horizon_label} {window_days}日 | "
            f"{row.get('signal_score')} / {row.get('signal_label')} | {pct(row.get('return_pct'))} | "
            f"{row.get('outcome_type')} | {pct(row.get('max_drawdown_pct'))} | "
            f"{pct(row.get('neutralize_confidence_pct'))} | {pct(row.get('effective_risk_rate_pct'))} | "
            f"{row.get('matched_rule_count', 0)} | `{row.get('top_rule_id')}` | {row.get('verdict')} |"
        )
    return lines


def review_layer_replay_rows(
    outcomes: list[dict[str, Any]],
    validation_from: dt.date | None,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for outcome in outcomes:
        review = review_layer_info(outcome)
        if review["label"] == "no_review_signal":
            continue
        period = period_for_date(outcome.get("signal_trade_date"), validation_from)
        horizon = str(outcome.get("horizon") or "")
        window_days = int(outcome.get("window_days") or 0)
        grouped[(period, review["label"], review["action"], horizon, window_days)].append(outcome)
        grouped[("all", review["label"], review["action"], horizon, window_days)].append(outcome)

    rows: list[dict[str, Any]] = []
    period_order = {"train": 0, "validation": 1, "all": 2, "unknown": 3}
    for (period, label, action, horizon, window_days), items in sorted(
        grouped.items(),
        key=lambda pair: (
            period_order.get(pair[0][0], 99),
            pair[0][1],
            pair[0][2],
            *horizon_window_sort_key(pair[0][3], pair[0][4]),
        ),
    ):
        adjusted = [adjusted_outcome_for_review_layer(item) for item in items]
        comparison = compare_outcome_groups(items, adjusted)
        basket = summarize_rule_baskets(items)
        rows.append(
            {
                "period": period,
                "label": label,
                "action": action,
                "horizon": horizon,
                "window_days": window_days,
                "basket_count": basket.get("basket_count", 0),
                "avg_basket_return_pct": basket.get("avg_basket_return_pct"),
                "worst_basket_return_pct": basket.get("worst_basket_return_pct"),
                **comparison,
            }
        )
    return rows


def review_layer_replay_lines(outcomes: list[dict[str, Any]], validation_from: dt.date | None) -> list[str]:
    lines = [
        "## 研究复核层新旧对照回放",
        "",
        "- 这一节把 Skill 中的研究复核层转成离线标签，只模拟观察降级，不写入 active 调分；它用于判断新逻辑是否整体减少错误方向。",
        "",
        "| 区间 | 复核标签 | 动作 | 周期窗口 | 样本 | 原方向样本 | 新方向样本 | 原命中率 | 新命中率 | 命中率变化 | 错误方向变化 | 被降级方向样本 | 被降级错误率 | 日篮 | 日篮均收益 | 最差日篮 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = review_layer_replay_rows(outcomes, validation_from)
    if not rows:
        return [
            *lines,
            "| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 0 | 暂无 | 暂无 |",
        ]
    period_labels = {"train": "训练段", "validation": "验证段", "all": "全样本", "unknown": "未知"}
    action_labels = {
        "downgrade_to_watch_review": "降级观察复核",
        "review_only": "仅复核",
        "keep_original_review": "保留原判断",
    }
    for row in rows:
        horizon_label = HORIZON_LABELS.get(str(row.get("horizon") or ""), str(row.get("horizon") or ""))
        lines.append(
            f"| {period_labels.get(str(row.get('period') or ''), row.get('period'))} | "
            f"`{row.get('label')}` | {action_labels.get(str(row.get('action') or ''), row.get('action'))} | "
            f"{horizon_label} {row.get('window_days')}日 | {row.get('matched_count', 0)} | "
            f"{row.get('baseline_directional_count', 0)} | {row.get('adjusted_directional_count', 0)} | "
            f"{pct(row.get('baseline_hit_rate_pct'))} | {pct(row.get('adjusted_hit_rate_pct'))} | "
            f"{pct(row.get('hit_rate_delta_pct'))} | {row.get('wrong_directional_count_delta', 0)} | "
            f"{row.get('neutralized_directional_count', 0)} | "
            f"{pct(row.get('neutralized_wrong_directional_rate_pct'))} | {row.get('basket_count', 0)} | "
            f"{pct(row.get('avg_basket_return_pct'))} | {pct(row.get('worst_basket_return_pct'))} |"
        )
    return lines


def research_review_portfolio_validation_rows(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenarios = [
        ("AI ETF买入候选中期20日", "medium_term", 20, "buy_bias", False),
        ("AI ETF买入候选长期60日", "long_term", 60, "buy_bias", False),
        ("复核降级观察机会篮长期60日", "long_term", 60, "sell_avoid", True),
    ]
    rows: list[dict[str, Any]] = []
    for scenario_name, horizon, window_days, side, review_only in scenarios:
        selected_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for outcome in outcomes:
            if str(outcome.get("horizon") or "") != horizon:
                continue
            if int(outcome.get("window_days") or 0) != window_days:
                continue
            if signal_side(outcome) != side:
                continue
            if review_only and review_layer_info(outcome)["action"] != "downgrade_to_watch_review":
                continue
            date_key = str(outcome.get("signal_trade_date") or "unknown")
            selected_by_date[date_key].append(outcome)
        selected: list[dict[str, Any]] = []
        for items in selected_by_date.values():
            selected.extend(
                sorted(items, key=lambda item: number(item.get("signal_score")) or 0, reverse=(side == "buy_bias"))[:10]
            )
        basket = summarize_rule_baskets(selected)
        rows.append(
            {
                "scenario": scenario_name,
                "horizon": horizon,
                "window_days": window_days,
                "signal_count": len(selected),
                **basket,
            }
        )
    return rows


def research_review_portfolio_validation_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 研究复核层组合级验证",
        "",
        "- 这一节按交易日构造最多 10 只股票的等权日篮，用来检查单股信号是否能转化为组合层面的稳定性；当前不模拟换手和交易成本。",
        "",
        "| 场景 | 周期窗口 | 日篮 | 信号 | 平均篮子大小 | 日篮均收益 | 正收益日篮率 | 平均回撤 | 最差日篮日 | 最差日篮收益 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in research_review_portfolio_validation_rows(outcomes):
        horizon_label = HORIZON_LABELS.get(str(row.get("horizon") or ""), str(row.get("horizon") or ""))
        lines.append(
            f"| {row.get('scenario')} | {horizon_label} {row.get('window_days')}日 | "
            f"{row.get('basket_count', 0)} | {row.get('stock_signal_count', row.get('signal_count', 0))} | "
            f"{decimal(row.get('avg_basket_size'))} | {pct(row.get('avg_basket_return_pct'))} | "
            f"{pct(row.get('positive_basket_rate_pct'))} | {pct(row.get('avg_basket_drawdown_pct'))} | "
            f"{row.get('worst_basket_date') or '暂无'} | {pct(row.get('worst_basket_return_pct'))} |"
        )
    return lines


def historical_fundamental_coverage_lines(metadata: dict[str, Any]) -> list[str]:
    return [
        "## 历史基本面覆盖度与缺口",
        "",
        "| 项目 | 当前状态 | 影响 | 下一步 |",
        "| --- | --- | --- | --- |",
        (
            f"| 历史技术数据 | 已按信号日截断，覆盖 {metadata.get('signal_count', 0)} 个评分快照 | "
            "可用于短中期择时与趋势回放 | 继续保持无未来函数 |"
        ),
        (
            "| 历史估值与财务指标 | 本离线回放暂不读取实时估值、财务指标和当前财报 | "
            "长期质量分只能作为低置信度边界，不能据此训练长期买入规则 | 按财报披露日接入 ROE、现金流、增速、估值分位 |"
        ),
        (
            "| 数据源错误记录 | 历史模式在 scoring item 中写入 source_errors | "
            "提醒分析时降低长期结论确信度 | 后续把 source_errors 聚合进 outcome 级覆盖统计 |"
        ),
    ]


def stock_pool_generalization_lines(metadata: dict[str, Any]) -> list[str]:
    codes_file = metadata.get("codes_file") or "stock.md"
    max_codes = metadata.get("max_codes") or "未限制"
    return [
        "## 股票池扩展与泛化验证",
        "",
        f"- 当前回放股票池：`{codes_file}`，实际股票数 {metadata.get('stock_count', 0)}，`--max-codes` 为 {max_codes}。",
        "- 当前结论只证明这组观察池内的历史表现，不等同于全 A 股泛化能力。",
        "- 后续泛化入口已经保留为 `--codes-file`：可分别准备沪深300、中证500、中证1000、行业分组和剔除/不剔除 ST 小市值的代码文件，然后用同一脚本回放。",
        "",
        "```bash",
        "uv run --python 3.12 --with-requirements requirements.txt \\",
        "  python research_signal_backtest.py --codes-file docs/research/stock-pool-hs300.md \\",
        "  --from-date 2023-06-19 --to-date 2026-06-19 \\",
        "  --validation-from 2024-06-19 --output docs/research/stock-signal-backtest-hs300.md",
        "```",
    ]


def review_layer_failure_case_rows(outcomes: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for outcome in outcomes:
        if signal_side(outcome) != "sell_avoid" or outcome.get("hit") is None:
            continue
        review = review_layer_info(outcome)
        if review["action"] == "downgrade_to_watch_review" and outcome.get("hit") is True:
            failure_type = "降级风险：原卖出/回避有效"
        elif review["label"] == "no_review_signal" and outcome.get("hit") is False:
            failure_type = "漏判风险：未识别卖出滞后"
        elif review["action"] == "review_only" and outcome.get("hit") is False:
            failure_type = "复核不足：仅复核但原方向错误"
        else:
            continue
        factors = outcome.get("factors") or {}
        rows.append(
            {
                "failure_type": failure_type,
                "stock_code": outcome.get("stock_code"),
                "stock_name": outcome.get("stock_name"),
                "signal_trade_date": outcome.get("signal_trade_date"),
                "horizon": outcome.get("horizon"),
                "window_days": outcome.get("window_days"),
                "review_label": review["label"],
                "review_action": review["action"],
                "return_pct": outcome.get("return_pct"),
                "max_drawdown_pct": outcome.get("max_drawdown_pct"),
                "stage_reason": factors.get("horizon_stage_reason") or "; ".join(review.get("reasons") or []),
            }
        )
    priority = {
        "降级风险：原卖出/回避有效": 0,
        "漏判风险：未识别卖出滞后": 1,
        "复核不足：仅复核但原方向错误": 2,
    }
    return sorted(
        rows,
        key=lambda row: (
            priority.get(str(row.get("failure_type") or ""), 99),
            -(abs(number(row.get("return_pct")) or 0)),
            str(row.get("signal_trade_date") or ""),
        ),
    )[:limit]


def review_layer_failure_case_lines(outcomes: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 研究复核层失败案例库",
        "",
        "- 这一节优先列出会伤害策略稳定性的反例：错误降级、漏掉卖出滞后、以及仅复核但仍不足的样本。",
        "",
        "| 类型 | 股票 | 信号日 | 周期窗口 | 复核标签 | 动作 | 后续收益 | 最大回撤 | 阶段原因 |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    rows = review_layer_failure_case_rows(outcomes)
    if not rows:
        return [*lines, "| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |"]
    action_labels = {
        "downgrade_to_watch_review": "降级观察复核",
        "review_only": "仅复核",
        "keep_original_review": "保留原判断",
    }
    for row in rows:
        horizon_label = HORIZON_LABELS.get(str(row.get("horizon") or ""), str(row.get("horizon") or ""))
        stock_label = f"{row.get('stock_code')} {row.get('stock_name')}".strip()
        lines.append(
            f"| {row.get('failure_type')} | {stock_label} | {row.get('signal_trade_date')} | "
            f"{horizon_label} {row.get('window_days')}日 | `{row.get('review_label')}` | "
            f"{action_labels.get(str(row.get('review_action') or ''), row.get('review_action'))} | "
            f"{pct(row.get('return_pct'))} | {pct(row.get('max_drawdown_pct'))} | {row.get('stage_reason') or '暂无'} |"
        )
    return lines


def stable_candidate_simulations(
    simulations: list[dict[str, Any]],
    min_train_samples: int = 100,
    min_validation_samples: int = 50,
    min_train_delta_pct: float = 1.0,
    min_validation_delta_pct: float = 0.0,
    min_neutralized_wrong_rate_pct: float = 60.0,
) -> list[dict[str, Any]]:
    stable = []
    for simulation in simulations:
        rule = simulation.get("rule") or {}
        train = simulation.get("train") or {}
        validation = simulation.get("validation") or {}
        train_count = int(train.get("matched_count") or 0)
        validation_count = int(validation.get("matched_count") or 0)
        if train_count < min_train_samples or validation_count < min_validation_samples:
            continue
        if str(rule.get("score_adjustment_mode") or "") == "neutralize_to_watch":
            train_wrong_rate = number(train.get("neutralized_wrong_directional_rate_pct"))
            validation_wrong_rate = number(validation.get("neutralized_wrong_directional_rate_pct"))
            train_wrong_delta = number(train.get("wrong_directional_count_delta"))
            validation_wrong_delta = number(validation.get("wrong_directional_count_delta"))
            if train_wrong_rate is None or validation_wrong_rate is None:
                continue
            if train_wrong_rate < min_neutralized_wrong_rate_pct:
                continue
            if validation_wrong_rate < min_neutralized_wrong_rate_pct:
                continue
            if train_wrong_delta is None or validation_wrong_delta is None:
                continue
            if train_wrong_delta >= 0 or validation_wrong_delta >= 0:
                continue
            stable.append(simulation)
            continue
        train_delta = number(train.get("hit_rate_delta_pct"))
        validation_delta = number(validation.get("hit_rate_delta_pct"))
        if train_delta is None or validation_delta is None:
            continue
        if train_delta < min_train_delta_pct or validation_delta < min_validation_delta_pct:
            continue
        train_return_delta = number(train.get("directional_avg_return_delta_pct"))
        validation_return_delta = number(validation.get("directional_avg_return_delta_pct"))
        train_drawdown_delta = number(train.get("directional_avg_drawdown_delta_pct"))
        validation_drawdown_delta = number(validation.get("directional_avg_drawdown_delta_pct"))
        if train_return_delta is not None and train_return_delta < 0:
            continue
        if validation_return_delta is not None and validation_return_delta < 0:
            continue
        if train_drawdown_delta is not None and train_drawdown_delta < 0:
            continue
        if validation_drawdown_delta is not None and validation_drawdown_delta < 0:
            continue
        stable.append(simulation)
    return stable


def stable_candidate_lines(simulations: list[dict[str, Any]]) -> list[str]:
    stable = stable_candidate_simulations(simulations)
    if not stable:
        return ["- 暂无规则同时满足训练段改善、验证段不退化和样本数门槛；本轮不写入 active。"]
    lines = []
    for simulation in stable:
        rule = simulation.get("rule") or {}
        train = simulation.get("train") or {}
        validation = simulation.get("validation") or {}
        if str(rule.get("score_adjustment_mode") or "") == "neutralize_to_watch":
            lines.append(
                f"- `{rule.get('id')}` 可进入 Candidate Adjustments：调整方式为推至观察边界；"
                f"训练样本 {train.get('matched_count', 0)}、训练降级错误率 {pct(train.get('neutralized_wrong_directional_rate_pct'))}、"
                f"训练错误方向变化 {train.get('wrong_directional_count_delta', 0)}；"
                f"验证样本 {validation.get('matched_count', 0)}、验证降级错误率 {pct(validation.get('neutralized_wrong_directional_rate_pct'))}、"
                f"验证错误方向变化 {validation.get('wrong_directional_count_delta', 0)}；建议先保持 candidate，继续跨区间验证，不直接进入 active。"
            )
        else:
            lines.append(
                f"- `{rule.get('id')}` 可进入 Candidate Adjustments：训练样本 {train.get('matched_count', 0)}、训练改善 {pct(train.get('hit_rate_delta_pct'))}；"
                f"验证样本 {validation.get('matched_count', 0)}、验证改善 {pct(validation.get('hit_rate_delta_pct'))}、"
                f"验证方向均收益变化 {pct(validation.get('directional_avg_return_delta_pct'))}、"
                f"验证方向均回撤变化 {pct(validation.get('directional_avg_drawdown_delta_pct'))}；建议先保持 candidate，继续跨区间验证。"
            )
    return lines


def rolling_stability_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 候选规则滚动折叠稳定性",
        "",
        "- 这一节按信号日期折叠候选规则，检查错误方向减少是否集中在少数月份/季度；集中度越高，越不适合直接 active。",
    ]
    simulations_with_folds = [simulation for simulation in simulations if simulation.get("rolling_folds")]
    if not simulations_with_folds:
        return [*lines, "- 暂无滚动折叠数据。"]

    for simulation in simulations_with_folds:
        rule = simulation.get("rule") or {}
        summary = simulation.get("rolling_summary") or {}
        folds = [fold for fold in simulation.get("rolling_folds") or [] if int(fold.get("matched_count") or 0) > 0]
        lines.extend(
            [
                "",
                f"### `{rule.get('id')}`",
                "",
                (
                    f"- 折叠粒度：{summary.get('bucket') or '未知'}；有样本折叠 {summary.get('folds_with_samples', 0)}；"
                    f"总匹配样本 {summary.get('total_matched_count', 0)}；"
                    f"最大单期样本占比 {pct(summary.get('max_fold_sample_share_pct'))}；"
                    f"加权降级错误率 {pct(summary.get('weighted_neutralized_wrong_directional_rate_pct'))}；"
                    f"错误方向减少折叠占比 {pct(summary.get('positive_wrong_delta_fold_share_pct'))}。"
                ),
                "",
                "| 折叠 | 匹配样本 | 错误方向变化 | 降级错误率 | 原命中率 | 被降级错误样本 |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for fold in folds:
            lines.append(
                f"| {fold.get('bucket')} | {fold.get('matched_count', 0)} | "
                f"{fold.get('wrong_directional_count_delta', 0)} | "
                f"{pct(fold.get('neutralized_wrong_directional_rate_pct'))} | "
                f"{pct(fold.get('baseline_hit_rate_pct'))} | "
                f"{fold.get('neutralized_wrong_directional_count', 0)} |"
            )
    return lines


def stage_factor_stability_lines(simulations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## 候选规则阶段因子折叠解释",
        "",
        "- 这一节按非日期因子折叠候选规则，用来判断候选是否能被市场/个股阶段解释，而不是只靠月份或季度聚类。",
    ]
    simulations_with_folds = [simulation for simulation in simulations if simulation.get("stage_factor_folds")]
    if not simulations_with_folds:
        return [*lines, "- 暂无阶段因子折叠数据。"]

    for simulation in simulations_with_folds:
        rule = simulation.get("rule") or {}
        stage_folds = simulation.get("stage_factor_folds") or {}
        stage_summaries = simulation.get("stage_factor_summaries") or {}
        lines.extend(["", f"### `{rule.get('id')}`"])
        for factor_name in sorted(stage_folds):
            folds = [fold for fold in stage_folds.get(factor_name) or [] if int(fold.get("matched_count") or 0) > 0]
            summary = stage_summaries.get(factor_name) or {}
            lines.extend(
                [
                    "",
                    f"#### `{factor_name}`",
                    "",
                    (
                        f"- 有样本因子值 {summary.get('folds_with_samples', 0)}；"
                        f"总匹配样本 {summary.get('total_matched_count', 0)}；"
                        f"最大单因子值样本占比 {pct(summary.get('max_fold_sample_share_pct'))}；"
                        f"加权降级错误率 {pct(summary.get('weighted_neutralized_wrong_directional_rate_pct'))}；"
                        f"错误方向减少因子值占比 {pct(summary.get('positive_wrong_delta_fold_share_pct'))}。"
                    ),
                    "",
                    "| 因子值 | 匹配样本 | 错误方向变化 | 降级错误率 | 原命中率 | 被降级错误样本 |",
                    "| --- | ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for fold in folds:
                lines.append(
                    f"| {fold.get('bucket')} | {fold.get('matched_count', 0)} | "
                    f"{fold.get('wrong_directional_count_delta', 0)} | "
                    f"{pct(fold.get('neutralized_wrong_directional_rate_pct'))} | "
                    f"{pct(fold.get('baseline_hit_rate_pct'))} | "
                    f"{fold.get('neutralized_wrong_directional_count', 0)} |"
                )
    return lines


def label_horizon_window(key: tuple[str, int]) -> str:
    horizon, window_days = key
    return f"{HORIZON_LABELS.get(horizon, horizon)} {window_days}日"


def core_finding_lines(summary: dict[str, Any]) -> list[str]:
    by_window = summary.get("by_horizon_window") or {}
    directional_items = [
        (key, item)
        for key, item in by_window.items()
        if int(item.get("directional_count") or 0) > 0 and number(item.get("hit_rate_pct")) is not None
    ]
    if not directional_items:
        return ["- 暂无足够方向样本形成核心发现。"]

    best_key, best_item = max(directional_items, key=lambda pair: number(pair[1].get("hit_rate_pct")) or -1)
    worst_key, worst_item = min(directional_items, key=lambda pair: number(pair[1].get("hit_rate_pct")) or 101)
    lines = [
        f"- 命中率最高的窗口是 {label_horizon_window(best_key)}：方向样本 {best_item['directional_count']}，命中率 {pct(best_item['hit_rate_pct'])}，平均收益 {pct(best_item['avg_return_pct'])}。",
        f"- 命中率最低的窗口是 {label_horizon_window(worst_key)}：方向样本 {worst_item['directional_count']}，命中率 {pct(worst_item['hit_rate_pct'])}，平均收益 {pct(worst_item['avg_return_pct'])}。",
    ]

    high_edges = []
    for key, item in directional_items:
        hit_rate = number(item.get("hit_rate_pct"))
        high_hit_rate = number(item.get("high_intensity_hit_rate_pct"))
        high_count = int(item.get("high_intensity_count") or 0)
        if hit_rate is None or high_hit_rate is None or high_count < 10:
            continue
        high_edges.append((key, high_count, high_hit_rate - hit_rate, high_hit_rate))
    if high_edges:
        key, high_count, delta, high_hit_rate = max(high_edges, key=lambda item: item[2])
        lines.append(
            f"- 高强度信号改善最明显的是 {label_horizon_window(key)}：高强度样本 {high_count}，命中率 {high_hit_rate:.2f}%，相对整体提升 {delta:.2f} 个百分点。"
        )
    else:
        lines.append("- 高强度信号样本暂未达到稳定比较门槛，先保留观察。")
    return lines


def theory_lines(summary: dict[str, Any]) -> list[str]:
    by_window = summary.get("by_horizon_window") or {}
    lines = [
        "- 短期评分主要用于择时，不应单独升级为投资结论；需要结合中期/长期结构确认。",
        "- 中长期窗口更适合检验趋势与质量逻辑，短期窗口更适合检查追涨、超卖和放量信号是否过度奖励。",
        "- 高强度样本只在样本量足够且验证段也改善时，才适合转化为候选权重调整。",
    ]
    long_items = [
        item
        for (horizon, _), item in by_window.items()
        if horizon == "long_term" and number(item.get("avg_return_pct")) is not None
    ]
    short_items = [
        item
        for (horizon, _), item in by_window.items()
        if horizon == "short_term" and number(item.get("hit_rate_pct")) is not None
    ]
    if long_items and average(item.get("avg_return_pct") for item in long_items) is not None:
        lines.append("- 如果长期窗口平均收益显著高于短期窗口，说明评分器更适合做趋势/配置筛选，而不是高频短线预测。")
    if short_items:
        lines.append("- 如果短期命中率接近 50%，下一轮应重点复盘 MACD、BOLL、KDJ、RSI 在不同市场状态下的权重。")
    return lines


def render_markdown_report(summary: dict[str, Any], metadata: dict[str, Any]) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 股票信号历史回测研究报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 回测区间：{metadata.get('from_date')} 至 {metadata.get('to_date')}",
        f"- 验证段起点：{metadata.get('validation_from') or '未切分'}",
        f"- 市场基准：{metadata.get('benchmark_index') or '未启用'}",
        f"- 股票数量：{metadata.get('stock_count', 0)}",
        f"- 信号样本：{metadata.get('signal_count', summary.get('sample_count', 0))}",
        "- 数据边界：每个信号日只使用当日及以前的日线数据；本研究不连接 MySQL，不上报生产接口。",
        "- 基本面边界：第一版不使用实时估值和财务指标，避免历史回看时混入未来财报或当前估值。",
        "- 策略边界：本报告只生成观察和候选规则，不自动修改 active 评分规则。",
        "",
        "## 核心发现",
        "",
        *core_finding_lines(summary),
        "",
        "## 初步分析理论",
        "",
        *theory_lines(summary),
        "",
        "## 分周期命中统计",
        "",
        "| 周期窗口 | 样本 | 方向样本 | 高强度样本 | 命中率 | 高强度命中率 | 平均收益 | 平均回撤 | 平均上冲 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (horizon, window_days), item in (summary.get("by_horizon_window") or {}).items():
        label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| {label} {window_days}日 | {item['sample_count']} | {item['directional_count']} | "
            f"{item['high_intensity_count']} | {pct(item['hit_rate_pct'])} | "
            f"{pct(item['high_intensity_hit_rate_pct'])} | {pct(item['avg_return_pct'])} | "
            f"{pct(item['avg_max_drawdown_pct'])} | {pct(item['avg_max_runup_pct'])} |"
        )

    lines.extend(
        [
            "",
            "## 市场状态观察",
            "",
            "| 状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for (regime, horizon), item in (summary.get("by_regime_horizon") or {}).items():
        label = HORIZON_LABELS.get(horizon, horizon)
        lines.append(
            f"| {regime}/{label} | {item['sample_count']} | {item['directional_count']} | "
            f"{pct(item['hit_rate_pct'])} | {pct(item['avg_return_pct'])} |"
        )

    lines.extend(
        [
            "",
            "## 细分市场状态观察",
            "",
            "| 细分状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    refined_rows = summary.get("by_refined_regime_horizon") or {}
    if refined_rows:
        for (refined_regime, horizon), item in refined_rows.items():
            label = HORIZON_LABELS.get(horizon, horizon)
            regime_label = REFINED_REGIME_LABELS.get(refined_regime, refined_regime)
            lines.append(
                f"| {regime_label} `{refined_regime}`/{label} | {item['sample_count']} | {item['directional_count']} | "
                f"{pct(item['hit_rate_pct'])} | {pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 市场基准状态观察",
            "",
            "| 市场状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    market_rows = summary.get("by_market_regime_horizon") or {}
    if market_rows:
        for (market_regime, horizon), item in market_rows.items():
            label = HORIZON_LABELS.get(horizon, horizon)
            regime_label = MARKET_REGIME_LABELS.get(market_regime, market_regime)
            lines.append(
                f"| {regime_label} `{market_regime}`/{label} | {item['sample_count']} | {item['directional_count']} | "
                f"{pct(item['hit_rate_pct'])} | {pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 训练/验证对照",
            "",
            "| 数据段 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    period_rows = summary.get("by_period_horizon_window") or {}
    if period_rows:
        for (period, horizon, window_days), item in period_rows.items():
            label = HORIZON_LABELS.get(horizon, horizon)
            period_label = {"train": "训练段", "validation": "验证段", "all": "全样本"}.get(period, period)
            lines.append(
                f"| {period_label} | {label} {window_days}日 | {item['sample_count']} | {item['directional_count']} | "
                f"{pct(item['hit_rate_pct'])} | {pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 买卖方向拆分",
            "",
            "| 方向 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    side_rows = summary.get("by_signal_side_horizon_window") or {}
    if side_rows:
        for (side, horizon, window_days), item in side_rows.items():
            side_label = SIGNAL_SIDE_LABELS.get(side, side)
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {side_label} | {label} {window_days}日 | {item['sample_count']} | {item['directional_count']} | "
                f"{pct(item['hit_rate_pct'])} | {pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 细分状态买卖方向拆分",
            "",
            "| 方向 | 细分状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    refined_side_rows = summary.get("by_signal_side_refined_regime_horizon_window") or {}
    if refined_side_rows:
        for (side, refined_regime, horizon, window_days), item in refined_side_rows.items():
            if int(item.get("sample_count") or 0) < 30:
                continue
            side_label = SIGNAL_SIDE_LABELS.get(side, side)
            regime_label = REFINED_REGIME_LABELS.get(refined_regime, refined_regime)
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {side_label} | {regime_label} `{refined_regime}` | {label} {window_days}日 | "
                f"{item['sample_count']} | {pct(item['hit_rate_pct'])} | "
                f"{pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
        if lines[-1] == "| --- | --- | --- | ---: | ---: | ---: | ---: |":
            lines.append("| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")
    else:
        lines.append("| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 市场与个股交叉状态归因",
            "",
            "| 方向 | 市场状态 | 个股状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    cross_rows = market_refined_cross_review_rows(summary)
    if cross_rows:
        for (side, _factor_name, factor_value, horizon, window_days), item in cross_rows:
            market_regime, refined_regime = str(factor_value).split("|", 1)
            side_label = SIGNAL_SIDE_LABELS.get(side, side)
            market_label = MARKET_REGIME_LABELS.get(market_regime, market_regime)
            refined_label = REFINED_REGIME_LABELS.get(refined_regime, refined_regime)
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {side_label} | {market_label} `{market_regime}` | {refined_label} `{refined_regime}` | "
                f"{label} {window_days}日 | {item['sample_count']} | {pct(item['hit_rate_pct'])} | "
                f"{pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 市场状态买卖方向拆分",
            "",
            "| 方向 | 市场状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    market_side_rows = summary.get("by_signal_side_market_regime_horizon_window") or {}
    if market_side_rows:
        for (side, market_regime, horizon, window_days), item in market_side_rows.items():
            if int(item.get("sample_count") or 0) < 30:
                continue
            side_label = SIGNAL_SIDE_LABELS.get(side, side)
            regime_label = MARKET_REGIME_LABELS.get(market_regime, market_regime)
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {side_label} | {regime_label} `{market_regime}` | {label} {window_days}日 | "
                f"{item['sample_count']} | {pct(item['hit_rate_pct'])} | "
                f"{pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
        if lines[-1] == "| --- | --- | --- | ---: | ---: | ---: | ---: |":
            lines.append("| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")
    else:
        lines.append("| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 因子归因复盘",
            "",
            "| 因子 | 取值 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    factor_rows = factor_review_rows(summary)
    if factor_rows:
        for (factor_name, factor_value, horizon, window_days), item in factor_rows:
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {factor_name} | {factor_value} | {label} {window_days}日 | {item['sample_count']} | "
                f"{item['directional_count']} | {pct(item['hit_rate_pct'])} | "
                f"{pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(
        [
            "",
            "## 买卖方向因子归因",
            "",
            "| 方向 | 因子 | 取值 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    side_factor_rows = signal_side_factor_review_rows(summary)
    if side_factor_rows:
        for (side, factor_name, factor_value, horizon, window_days), item in side_factor_rows:
            side_label = SIGNAL_SIDE_LABELS.get(side, side)
            label = HORIZON_LABELS.get(horizon, horizon)
            lines.append(
                f"| {side_label} | {factor_name} | {factor_value} | {label} {window_days}日 | "
                f"{item['sample_count']} | {item['directional_count']} | {pct(item['hit_rate_pct'])} | "
                f"{pct(item['avg_return_pct'])} | {pct(item['avg_max_drawdown_pct'])} |"
            )
    else:
        lines.append("| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |")

    lines.extend(["", "## 候选规则观察", "", *candidate_observation_lines(summary)])
    lines.extend(["", "## 候选优化规则", "", *candidate_rule_lines(summary)])
    lines.extend(["", "## 候选规则模拟对比", "", *simulation_table_lines(metadata.get("simulations") or [])])
    lines.extend(["", "## 候选规则组合级验证", "", *candidate_basket_lines(metadata.get("simulations") or [])])
    lines.extend(["", "## 候选规则跨持有期画像", "", *candidate_horizon_profile_lines(metadata.get("simulations") or [])])
    lines.extend(["", *continuous_speed_horizon_selector_lines(metadata.get("simulations") or [])])
    lines.extend(["", *counterexample_factor_diagnostic_lines(metadata.get("simulations") or [])])
    lines.extend(["", *neutralize_confidence_lines(metadata.get("simulations") or [])])
    lines.extend(
        [
            "",
            *neutralize_signal_stage_block_lines(
                metadata.get("outcomes") or [],
                metadata.get("simulations") or [],
            ),
        ]
    )
    lines.extend(
        [
            "",
            *neutralize_signal_stage_factor_profile_lines(
                metadata.get("outcomes") or [],
                metadata.get("simulations") or [],
            ),
        ]
    )
    lines.extend(["", *horizon_selection_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_selection_factor_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_classifier_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_factor_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_pair_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_target_fold_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_target_daily_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_target_daily_context_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_target_repair_breadth_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_repair_breadth_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_repair_breadth_stage_fold_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_repair_breadth_continuous_stage_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *horizon_stage_mixed_bucket_repair_breadth_continuous_combo_lines(metadata.get("outcomes") or [])])
    lines.extend(
        [
            "",
            *neutralize_signal_daily_summary_lines(
                metadata.get("outcomes") or [],
                metadata.get("simulations") or [],
            ),
        ]
    )
    lines.extend(
        [
            "",
            *neutralize_signal_review_lines(
                metadata.get("outcomes") or [],
                metadata.get("simulations") or [],
            ),
        ]
    )
    validation_from = sfa.parse_date_like(metadata.get("validation_from"))
    lines.extend(["", *review_layer_replay_lines(metadata.get("outcomes") or [], validation_from)])
    lines.extend(["", *historical_fundamental_coverage_lines(metadata)])
    lines.extend(["", *research_review_portfolio_validation_lines(metadata.get("outcomes") or [])])
    lines.extend(["", *stock_pool_generalization_lines(metadata)])
    lines.extend(["", *review_layer_failure_case_lines(metadata.get("outcomes") or [])])
    lines.extend(["", "## 稳定候选筛选", "", *stable_candidate_lines(metadata.get("simulations") or [])])
    lines.extend(["", *rolling_stability_lines(metadata.get("simulations") or [])])
    lines.extend(["", *stage_factor_stability_lines(metadata.get("simulations") or [])])
    errors = metadata.get("errors") or []
    if errors:
        lines.extend(["", "## 数据源问题", "", *[f"- {error}" for error in errors]])
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 用训练段发现候选规则，再用验证段复查，避免把单一年份噪声写成长期规则。",
            "- 只有重复样本支持的规则，才考虑进入 `review-memory.md` 的 candidate；active 调整需要更严格证据。",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_date(value: str) -> dt.date:
    parsed = sfa.parse_date_like(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD")
    return parsed


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def default_output_path(from_date: dt.date, to_date: dt.date) -> str:
    return str(PROJECT_ROOT / "docs/research" / f"stock-signal-backtest-{from_date:%Y-%m-%d}-to-{to_date:%Y-%m-%d}.md")


def default_validation_from(from_date: dt.date, to_date: dt.date) -> dt.date:
    total_days = (to_date - from_date).days
    return from_date + dt.timedelta(days=round(total_days * 2 / 3))


def parse_stage_fold_factors(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def parse_args(argv: list[str]) -> argparse.Namespace:
    today = dt.date.today()
    default_from = today - dt.timedelta(days=365)
    parser = argparse.ArgumentParser(description="本地历史回测股票信号评分，不写库、不上报。")
    parser.add_argument("codes", nargs="*", help="股票代码；不传则读取 stock.md")
    parser.add_argument("--codes-file", default=str(PROJECT_ROOT / "stock.md"))
    parser.add_argument("--from-date", type=parse_date, default=default_from)
    parser.add_argument("--to-date", type=parse_date, default=today)
    parser.add_argument("--validation-from", type=parse_date, help="验证段起始日期；默认取回测区间后 1/3")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-codes", type=positive_int)
    parser.add_argument("--sample-step", type=positive_int, default=1, help="每 N 个可评分交易日抽样一次")
    parser.add_argument("--technical-days", type=positive_int, default=520)
    parser.add_argument("--adjust", choices=["none", "qfq", "hfq"], default="qfq")
    parser.add_argument("--benchmark-index", default="sh000001", help="市场基准指数，默认上证指数 sh000001")
    parser.add_argument(
        "--rolling-bucket",
        choices=["none", "month", "quarter"],
        default="month",
        help="候选规则滚动折叠粒度，默认按月；none 表示不生成滚动折叠。",
    )
    parser.add_argument(
        "--stage-fold-factors",
        default=",".join(DEFAULT_STAGE_FOLD_FACTORS),
        help="候选规则阶段折叠因子，逗号分隔；留空表示不生成阶段因子折叠。",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.from_date > args.to_date:
        parser.error("--from-date 不能晚于 --to-date")
    if args.validation_from is None:
        args.validation_from = default_validation_from(args.from_date, args.to_date)
    if args.validation_from < args.from_date or args.validation_from > args.to_date:
        parser.error("--validation-from 必须位于回测区间内")
    if not args.output:
        args.output = default_output_path(args.from_date, args.to_date)
    args.stage_fold_factors = parse_stage_fold_factors(args.stage_fold_factors)
    return args


def load_scorer() -> Any:
    spec = importlib.util.spec_from_file_location("stock_buy_signal_scorer", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载评分脚本：{SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log(args: argparse.Namespace, message: str) -> None:
    if not getattr(args, "quiet", False):
        print(message, file=sys.stderr, flush=True)


def fetch_history_series(
    ak: Any,
    code: str,
    from_date: dt.date,
    to_date: dt.date,
    technical_days: int,
    adjust: str,
) -> list[dict[str, Any]]:
    warmup_calendar_days = max(technical_days * 3, 800)
    start_date = from_date - dt.timedelta(days=warmup_calendar_days)
    adjust_arg = "" if adjust == "none" else adjust
    hist_df = sfa.call_akshare_quietly(
        ak.stock_zh_a_daily,
        symbol=sfa.sina_symbol(code),
        start_date=start_date.strftime("%Y%m%d"),
        end_date=to_date.strftime("%Y%m%d"),
        adjust=adjust_arg,
    )
    if hist_df is None or hist_df.empty:
        return []
    rows = []
    for _, row in hist_df.iterrows():
        row_dict = sfa.dataframe_row_to_dict(row)
        volume = number(row_dict.get("volume"))
        turnover = number(row_dict.get("turnover"))
        rows.append(
            {
                "日期": row_dict.get("date"),
                "收盘": row_dict.get("close"),
                "最高": row_dict.get("high"),
                "最低": row_dict.get("low"),
                "成交量": volume / 100 if volume is not None else None,
                "成交额": row_dict.get("amount"),
                "换手率": turnover * 100 if turnover is not None else None,
            }
        )
    return sfa.calculate_technical_series(rows)


def fetch_benchmark_series(
    ak: Any,
    benchmark_index: str,
    from_date: dt.date,
    to_date: dt.date,
    technical_days: int,
) -> list[dict[str, Any]]:
    warmup_calendar_days = max(technical_days * 3, 800)
    start_date = from_date - dt.timedelta(days=warmup_calendar_days)
    hist_df = sfa.call_akshare_quietly(ak.stock_zh_index_daily, symbol=benchmark_index)
    if hist_df is None or hist_df.empty:
        return []
    rows = []
    for _, row in hist_df.iterrows():
        row_dict = sfa.dataframe_row_to_dict(row)
        row_date = sfa.parse_date_like(row_dict.get("date"))
        if row_date is None or row_date < start_date or row_date > to_date:
            continue
        rows.append(
            {
                "日期": row_dict.get("date"),
                "收盘": row_dict.get("close"),
                "最高": row_dict.get("high"),
                "最低": row_dict.get("low"),
                "成交量": row_dict.get("volume"),
                "成交额": row_dict.get("amount"),
                "换手率": row_dict.get("turnover_rate"),
            }
        )
    return sfa.calculate_technical_series(rows)


def iter_signal_indices(series: list[dict[str, Any]], from_date: dt.date, to_date: dt.date, sample_step: int) -> list[int]:
    indices = []
    eligible_count = 0
    for index, row in enumerate(series):
        row_date = sfa.parse_date_like(row.get("date"))
        if row_date is None or row_date < from_date or row_date > to_date:
            continue
        eligible_count += 1
        if (eligible_count - 1) % sample_step == 0:
            indices.append(index)
    return indices


def run_backtest(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("缺少依赖：请用 uv run --python 3.12 --with-requirements requirements.txt 运行") from exc

    scorer = load_scorer()
    codes = sfa.resolve_input_codes(args.codes, args.codes_file)
    if args.max_codes:
        codes = codes[: args.max_codes]
    code_names = {} if args.codes else sfa.load_code_names_from_file(args.codes_file)
    outcomes: list[dict[str, Any]] = []
    errors: list[str] = []
    signal_count = 0
    benchmark_series: list[dict[str, Any]] = []
    benchmark_dates: list[dt.date] = []
    market_factor_cache: dict[str, dict[str, str]] = {}

    if args.benchmark_index:
        try:
            benchmark_series = fetch_benchmark_series(
                ak,
                args.benchmark_index,
                args.from_date,
                args.to_date,
                args.technical_days,
            )
            benchmark_dates = parsed_series_dates(benchmark_series) if benchmark_series else []
            if not benchmark_series:
                errors.append(f"{args.benchmark_index} 市场基准指数日线为空，市场状态按未知处理")
        except Exception as exc:
            errors.append(f"{args.benchmark_index} 市场基准指数获取失败：{type(exc).__name__}: {exc}")
            benchmark_series = []
            benchmark_dates = []

    for index, code in enumerate(codes, start=1):
        name = code_names.get(code, "")
        log(args, f"[{index}/{len(codes)}] 获取并回测 {code} {name}".strip())
        try:
            series = fetch_history_series(ak, code, args.from_date, args.to_date, args.technical_days, args.adjust)
        except Exception as exc:
            errors.append(f"{code} 历史日线获取失败：{type(exc).__name__}: {exc}")
            continue
        if not series:
            errors.append(f"{code} 历史日线为空")
            continue
        for signal_index in iter_signal_indices(series, args.from_date, args.to_date, args.sample_step):
            item = build_scoring_item_from_series(code, name, series, signal_index)
            result = scorer.score_item(item)
            signal_count += 1
            signal_date = str(series[signal_index].get("date") or "")
            market_factors: dict[str, str] | None = None
            if benchmark_series and benchmark_dates:
                if signal_date not in market_factor_cache:
                    visible_benchmark = visible_series_as_of(benchmark_series, benchmark_dates, signal_date)
                    market_factor_cache[signal_date] = market_factor_tags_from_visible_series(
                        visible_benchmark,
                        args.benchmark_index,
                    )
                market_factors = market_factor_cache[signal_date]
            elif args.benchmark_index:
                market_factors = market_factor_tags_from_visible_series([], args.benchmark_index)
            outcomes.extend(evaluate_result_windows(result, series, signal_index, extra_factors=market_factors))

    summary = summarize_outcomes(outcomes, validation_from=args.validation_from)
    candidate_rules = [
        *build_candidate_rules(summary),
        *weak_tail_focus_candidate_rules(),
        *continuous_repair_focus_candidate_rules(),
        *repair_speed_focus_candidate_rules(),
        *continuous_speed_focus_candidate_rules(),
        *repair_quality_focus_candidate_rules(),
        *repair_quality_sync_focus_candidate_rules(),
        *repair_quality_failure_focus_candidate_rules(),
        *repair_quality_defense_pocket_candidate_rules(),
        *mixed_bucket_continuous_combo_candidate_rules(),
    ]
    simulations = simulate_candidate_rules(
        outcomes,
        candidate_rules,
        validation_from=args.validation_from,
        rolling_bucket=args.rolling_bucket,
        stage_fold_factors=args.stage_fold_factors,
    )
    metadata = {
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
        "validation_from": args.validation_from.isoformat(),
        "stock_count": len(codes),
        "signal_count": signal_count,
        "benchmark_index": args.benchmark_index,
        "codes_file": args.codes_file,
        "max_codes": args.max_codes,
        "errors": errors,
        "outcomes": outcomes,
        "simulations": simulations,
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(summary, metadata), encoding="utf-8")
    return output_path, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        output_path, summary = run_backtest(args)
    except Exception as exc:
        print(f"研究回测失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"研究报告已生成：{output_path}")
    print(f"成熟窗口样本：{summary.get('sample_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
