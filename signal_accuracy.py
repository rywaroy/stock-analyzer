"""Build and summarize historical validation records for stock signal scores."""

from __future__ import annotations

from typing import Any


HORIZON_WINDOWS: dict[str, list[int]] = {
    "short_term": [1, 3, 5],
    "medium_term": [10, 20],
    "long_term": [60, 120],
}

HORIZON_LABELS = {
    "short_term": "短期",
    "medium_term": "中期",
    "long_term": "长期",
}

BUY_SIGNALS = {"强买", "买入偏向"}
SELL_SIGNALS = {"卖出偏向", "强卖/回避"}


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_hit(signal_label: str | None, return_pct: float | None) -> bool | None:
    """Classify directional accuracy. Watch signals are not directional samples."""
    value = number(return_pct)
    if value is None or not signal_label:
        return None
    if signal_label in BUY_SIGNALS:
        return value > 0
    if signal_label in SELL_SIGNALS:
        return value < 0
    return None


def outcome_specs(result: dict[str, Any], adjust_type: str) -> list[dict[str, Any]]:
    item = result.get("raw") or {}
    technical = item.get("technical") or {}
    trade_date = technical.get("trade_date")
    signal_close = number(technical.get("latest_close"))
    stock_code = str(result.get("code") or item.get("code") or "")
    if not stock_code or not trade_date or signal_close is None:
        return []

    specs: list[dict[str, Any]] = []
    horizons = result.get("horizon_scores") or {}
    for horizon, windows in HORIZON_WINDOWS.items():
        score_info = horizons.get(horizon) or {}
        signal_score = score_info.get("score")
        signal_label = score_info.get("signal")
        for window_days in windows:
            specs.append(
                {
                    "stock_code": stock_code,
                    "signal_trade_date": trade_date,
                    "adjust_type": adjust_type,
                    "horizon": horizon,
                    "window_days": window_days,
                    "signal_score": signal_score,
                    "signal_label": signal_label,
                    "signal_close": signal_close,
                }
            )
    return specs


def empty_summary() -> dict[str, dict[int, dict[str, Any]]]:
    return {horizon: {} for horizon in HORIZON_WINDOWS}


def format_pct(value: Any) -> str:
    numeric = number(value)
    if numeric is None:
        return "暂无"
    return f"{numeric:.2f}%"


def format_summary_lines(summary: dict[str, dict[int, dict[str, Any]]] | None) -> list[str]:
    if not summary:
        return ["暂无已到期历史验证样本，先持续积累。"]

    lines: list[str] = []
    for horizon, windows in HORIZON_WINDOWS.items():
        label = HORIZON_LABELS[horizon]
        for window_days in windows:
            item = (summary.get(horizon) or {}).get(window_days)
            if not item:
                continue
            lines.append(
                f"- {label} {window_days}日：高强度样本 {int(item.get('sample_count') or 0)}，"
                f"命中率 {format_pct(item.get('hit_rate_pct'))}，"
                f"平均收益 {format_pct(item.get('avg_return_pct'))}，"
                f"平均回撤 {format_pct(item.get('avg_max_drawdown_pct'))}，"
                f"平均上冲 {format_pct(item.get('avg_max_runup_pct'))}"
            )
    return lines or ["暂无已到期历史验证样本，先持续积累。"]


def parse_summary_rows(rows: list[list[str]]) -> dict[str, dict[int, dict[str, Any]]]:
    summary = empty_summary()
    for row in rows:
        if len(row) != 8:
            continue
        horizon, window_days, sample_count, directional_count, hit_rate, avg_return, avg_drawdown, avg_runup = row
        if horizon not in summary:
            continue
        summary[horizon][int(window_days)] = {
            "sample_count": int(float(sample_count)),
            "directional_count": int(float(directional_count)),
            "hit_rate_pct": number(hit_rate),
            "avg_return_pct": number(avg_return),
            "avg_excess_return_pct": None,
            "avg_max_drawdown_pct": number(avg_drawdown),
            "avg_max_runup_pct": number(avg_runup),
        }
    return summary
