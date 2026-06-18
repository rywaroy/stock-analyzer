#!/usr/bin/env python3
"""用 AKShare 批量生成 A 股基本面分析报告。"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests


MISSING = "暂无数据"
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CODES_FILE = PROJECT_ROOT / "stock.md"


@dataclass
class Metric:
    label: str
    value: float | None
    unit: str = ""
    source_name: str | None = None
    note: str = ""


@dataclass
class TechnicalSnapshot:
    trade_date: str = ""
    latest_close: float | None = None
    latest_volume: float | None = None
    latest_amount: float | None = None
    turnover_rate: float | None = None
    avg_volume_5: float | None = None
    avg_volume_20: float | None = None
    volume_ratio_5: float | None = None
    macd_dif: float | None = None
    macd_dea: float | None = None
    macd_bar: float | None = None
    boll_mid: float | None = None
    boll_upper: float | None = None
    boll_lower: float | None = None
    boll_position: str = ""
    kdj_k: float | None = None
    kdj_d: float | None = None
    kdj_j: float | None = None
    rsi6: float | None = None
    rsi12: float | None = None
    rsi24: float | None = None
    signals: list[str] = field(default_factory=list)


@dataclass
class TrendWindow:
    days: int
    return_pct: float | None = None
    close_vs_ma_pct: float | None = None
    macd_positive_ratio: float | None = None
    boll_mid_above_ratio: float | None = None
    rsi24: float | None = None
    volume_ratio_20: float | None = None


@dataclass
class TechnicalTrendAnalysis:
    rating: str = "技术趋势数据不足"
    score: int = 0
    conclusion: str = "长期技术指标数据不足，暂不形成趋势判断。"
    windows: list[TrendWindow] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)


@dataclass
class StockAnalysis:
    code: str
    name: str = ""
    industry: str = ""
    listed_at: str = ""
    report_date: str = ""
    overview: dict[str, Any] = field(default_factory=dict)
    valuation: dict[str, Any] = field(default_factory=dict)
    metrics: list[Metric] = field(default_factory=list)
    technical: TechnicalSnapshot | None = None
    technical_trend: TechnicalTrendAnalysis | None = None
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)


METRIC_CANDIDATES = {
    "eps": ["摊薄每股收益(元)", "加权每股收益(元)", "基本每股收益(元)", "每股收益_调整后(元)"],
    "net_asset_per_share": ["每股净资产_调整后(元)", "每股净资产_调整前(元)", "每股净资产(元)"],
    "operating_cash_per_share": ["每股经营性现金流(元)", "每股经营现金流量(元)", "每股经营现金净流量(元)"],
    "roe": ["加权净资产收益率(%)", "净资产收益率(%)", "净资产报酬率(%)"],
    "gross_margin": ["销售毛利率(%)", "主营业务利润率(%)"],
    "net_margin": ["销售净利率(%)", "营业利润率(%)"],
    "revenue_growth": ["主营业务收入增长率(%)", "营业收入增长率(%)"],
    "net_profit_growth": ["净利润增长率(%)", "归属母公司股东的净利润增长率(%)"],
    "asset_growth": ["总资产增长率(%)"],
    "debt_ratio": ["资产负债率(%)"],
    "current_ratio": ["流动比率"],
    "quick_ratio": ["速动比率"],
    "ocf_to_profit": ["经营现金净流量与净利润的比率(%)", "经营现金净流量与净利润的比率"],
    "ocf_to_revenue": ["经营现金净流量对销售收入比率(%)", "现金流入结构比率(%)"],
}


DISPLAY_METRICS = [
    ("eps", "每股收益", "元"),
    ("net_asset_per_share", "每股净资产", "元"),
    ("operating_cash_per_share", "每股经营现金流", "元"),
    ("roe", "ROE", "%"),
    ("gross_margin", "毛利率", "%"),
    ("net_margin", "净利率", "%"),
    ("revenue_growth", "营收增长", "%"),
    ("net_profit_growth", "净利润增长", "%"),
    ("asset_growth", "总资产增长", "%"),
    ("debt_ratio", "资产负债率", "%"),
    ("current_ratio", "流动比率", ""),
    ("quick_ratio", "速动比率", ""),
    ("ocf_to_profit", "经营现金流/净利润", "倍"),
]


def parse_codes(parts: Iterable[str]) -> list[str]:
    raw = " ".join(parts)
    tokens = [item for item in re.split(r"[\s,，;；]+", raw) if item]
    codes: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        code = normalize_code(token)
        if code not in seen:
            codes.append(code)
            seen.add(code)
    if not codes:
        raise ValueError("请至少输入一个股票代码，例如：000001,600519")
    return codes


def clean_codes_file_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""
    stripped = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
    return stripped.split("#", 1)[0].strip()


def load_codes_from_file(path: str | Path = DEFAULT_CODES_FILE) -> list[str]:
    codes_file = Path(path).expanduser()
    if not codes_file.exists():
        raise ValueError(f"未找到股票代码文件：{codes_file}")

    codes: list[str] = []
    seen: set[str] = set()
    for line_no, line in enumerate(codes_file.read_text(encoding="utf-8").splitlines(), start=1):
        cleaned = clean_codes_file_line(line)
        if not cleaned:
            continue
        try:
            line_codes = parse_codes([cleaned])
        except ValueError as exc:
            raise ValueError(f"{codes_file}:{line_no} 股票代码格式不正确：{cleaned}") from exc
        for code in line_codes:
            if code not in seen:
                codes.append(code)
                seen.add(code)
    if not codes:
        raise ValueError(f"{codes_file} 没有可分析的股票代码")
    return codes


def load_code_names_from_file(path: str | Path = DEFAULT_CODES_FILE) -> dict[str, str]:
    codes_file = Path(path).expanduser()
    if not codes_file.exists():
        raise ValueError(f"未找到股票代码文件：{codes_file}")

    names: dict[str, str] = {}
    for line_no, line in enumerate(codes_file.read_text(encoding="utf-8").splitlines(), start=1):
        cleaned = clean_codes_file_line(line)
        if not cleaned or "-" not in cleaned:
            continue
        raw_code, raw_name = cleaned.split("-", 1)
        name = raw_name.strip()
        if not name:
            continue
        try:
            code = normalize_code(raw_code)
        except ValueError as exc:
            raise ValueError(f"{codes_file}:{line_no} 股票代码格式不正确：{cleaned}") from exc
        names.setdefault(code, name)
    return names


def resolve_input_codes(parts: Iterable[str], codes_file: str | Path = DEFAULT_CODES_FILE) -> list[str]:
    parts = list(parts)
    if parts:
        return parse_codes(parts)
    return load_codes_from_file(codes_file)


def normalize_code(raw: str) -> str:
    token = raw.strip().upper()
    token = token.replace("SH", "").replace("SZ", "").replace("BJ", "")
    token = token.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    match = re.search(r"\d{6}", token)
    if not match:
        raise ValueError(f"股票代码格式不正确：{raw}")
    return match.group(0)


def market_symbol(code: str) -> str:
    if code.startswith(("6", "9")):
        return f"SH{code}"
    if code.startswith(("4", "8")):
        return f"BJ{code}"
    return f"SZ{code}"


def sina_symbol(code: str) -> str:
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def to_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if text in {"", "-", "--", "None", "nan", "NaN"}:
        return None
    multiplier = 1.0
    if text.endswith("万亿"):
        multiplier = 1_000_000_000_000
        text = text[:-2]
    elif text.endswith("亿"):
        multiplier = 100_000_000
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10_000
        text = text[:-1]
    text = text.replace(",", "").replace("%", "")
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def parse_date_like(value: Any) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt).date()
        except ValueError:
            continue
    return None


def dataframe_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return dict(row)


def call_akshare_quietly(func: Any, *args: Any, **kwargs: Any) -> Any:
    """屏蔽 AKShare 内部 tqdm 进度条，保证 CLI 输出可被下游解析。"""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


def summarize_exception(exc: Exception) -> str:
    text = re.sub(r"\s+", " ", str(exc)).strip()
    host_match = re.search(r"host='([^']+)'", text)
    if "Unable to connect to proxy" in text and host_match:
        return f"{exc.__class__.__name__}: Unable to connect to proxy; host={host_match.group(1)}"
    if "Max retries exceeded" in text and host_match:
        return f"{exc.__class__.__name__}: Max retries exceeded; host={host_match.group(1)}"

    def replace_url(match: re.Match[str]) -> str:
        parsed = urlparse(match.group(0))
        return parsed.netloc or match.group(0)

    text = re.sub(r"https?://\S+", replace_url, text)
    if len(text) > 220:
        text = f"{text[:217]}..."
    return f"{exc.__class__.__name__}: {text}"


def pick_metric(row: dict[str, Any], key: str) -> tuple[str | None, float | None]:
    candidates = METRIC_CANDIDATES[key]
    for name in candidates:
        if name in row:
            value = to_number(row.get(name))
            if value is not None:
                return name, value
    for column, raw_value in row.items():
        normalized_column = str(column).replace(" ", "")
        for name in candidates:
            if name.replace(" ", "") in normalized_column:
                value = to_number(raw_value)
                if value is not None:
                    return str(column), value
    return None, None


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    factor = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(value * factor + result[-1] * (1 - factor))
    return result


def cn_sma_latest(values: list[float], period: int, weight: int = 1) -> float | None:
    if not values:
        return None
    result = values[0]
    for value in values[1:]:
        result = (weight * value + (period - weight) * result) / period
    return result


def cn_sma_series(values: list[float], period: int, weight: int = 1) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for value in values[1:]:
        result.append((weight * value + (period - weight) * result[-1]) / period)
    return result


def rolling_std(values: list[float]) -> float | None:
    avg = average(values)
    if avg is None:
        return None
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def latest_rsi(closes: list[float], period: int) -> float | None:
    if len(closes) <= period:
        return None
    changes = [closes[index] - closes[index - 1] for index in range(1, len(closes))]
    gains = [max(change, 0) for change in changes]
    total_changes = [abs(change) for change in changes]
    avg_gain = cn_sma_latest(gains, period, 1) or 0
    avg_change = cn_sma_latest(total_changes, period, 1) or 0
    if avg_change == 0 and avg_gain == 0:
        return 50.0
    if avg_change == 0:
        return 100.0
    return avg_gain / avg_change * 100


def calculate_kdj(highs: list[float], lows: list[float], closes: list[float], period: int = 9) -> tuple[float | None, float | None, float | None]:
    if not highs or not lows or not closes:
        return None, None, None
    k = 50.0
    d = 50.0
    for index, close in enumerate(closes):
        start = max(0, index - period + 1)
        recent_high = max(highs[start : index + 1])
        recent_low = min(lows[start : index + 1])
        if recent_high == recent_low:
            rsv = 50.0
        else:
            rsv = (close - recent_low) / (recent_high - recent_low) * 100
        k = 2 / 3 * k + 1 / 3 * rsv
        d = 2 / 3 * d + 1 / 3 * k
    return k, d, 3 * k - 2 * d


def calculate_kdj_series(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    k_values: list[float] = []
    d_values: list[float] = []
    j_values: list[float] = []
    k = 50.0
    d = 50.0
    for index, close in enumerate(closes):
        start = max(0, index - period + 1)
        recent_high = max(highs[start : index + 1])
        recent_low = min(lows[start : index + 1])
        if recent_high == recent_low:
            rsv = 50.0
        else:
            rsv = (close - recent_low) / (recent_high - recent_low) * 100
        k = 2 / 3 * k + 1 / 3 * rsv
        d = 2 / 3 * d + 1 / 3 * k
        k_values.append(k)
        d_values.append(d)
        j_values.append(3 * k - 2 * d)
    return k_values, d_values, j_values


def classify_boll_position(close: float | None, mid: float | None, upper: float | None, lower: float | None) -> str:
    if close is None or mid is None or upper is None or lower is None:
        return ""
    if close > upper:
        return "突破上轨"
    if close < lower:
        return "跌破下轨"
    if close >= mid:
        return "中轨上方"
    return "中轨下方"


def normalize_daily_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, float | str | None]]:
    daily_rows: list[dict[str, Any]] = []
    for row in rows:
        close = to_number(row.get("收盘", row.get("close")))
        high = to_number(row.get("最高", row.get("high")))
        low = to_number(row.get("最低", row.get("low")))
        volume = to_number(row.get("成交量", row.get("volume")))
        if close is None or high is None or low is None or volume is None:
            continue
        daily_rows.append(
            {
                "date": str(row.get("日期", row.get("date", ""))),
                "close": close,
                "high": high,
                "low": low,
                "volume": volume,
                "amount": to_number(row.get("成交额", row.get("amount"))),
                "turnover_rate": to_number(row.get("换手率", row.get("turnover_rate"))),
            }
        )
    daily_rows.sort(key=lambda item: item["date"])
    return daily_rows


def moving_average_at(values: list[float], index: int, period: int) -> float | None:
    if index + 1 < period:
        return None
    return average(values[index - period + 1 : index + 1])


def rolling_std_at(values: list[float], index: int, period: int) -> float | None:
    if index + 1 < period:
        return None
    return rolling_std(values[index - period + 1 : index + 1])


def calculate_rsi_series(closes: list[float], period: int) -> list[float | None]:
    if not closes:
        return []
    output: list[float | None] = [None]
    changes = [closes[index] - closes[index - 1] for index in range(1, len(closes))]
    gains = [max(change, 0) for change in changes]
    total_changes = [abs(change) for change in changes]
    smoothed_gains = cn_sma_series(gains, period, 1)
    smoothed_changes = cn_sma_series(total_changes, period, 1)
    for index, avg_change in enumerate(smoothed_changes, start=1):
        if index < period:
            output.append(None)
            continue
        avg_gain = smoothed_gains[index - 1]
        if avg_change == 0 and avg_gain == 0:
            output.append(50.0)
        elif avg_change == 0:
            output.append(100.0)
        else:
            output.append(avg_gain / avg_change * 100)
    return output


def calculate_technical_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    daily_rows = normalize_daily_rows(rows)
    if not daily_rows:
        return []

    closes = [float(item["close"]) for item in daily_rows]
    highs = [float(item["high"]) for item in daily_rows]
    lows = [float(item["low"]) for item in daily_rows]
    volumes = [float(item["volume"]) for item in daily_rows]
    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    dif_values = [fast - slow for fast, slow in zip(ema12, ema26)]
    dea_values = ema_series(dif_values, 9)
    k_values, d_values, j_values = calculate_kdj_series(highs, lows, closes)
    rsi6_values = calculate_rsi_series(closes, 6)
    rsi12_values = calculate_rsi_series(closes, 12)
    rsi24_values = calculate_rsi_series(closes, 24)

    series: list[dict[str, Any]] = []
    for index, row in enumerate(daily_rows):
        ma20 = moving_average_at(closes, index, 20)
        ma60 = moving_average_at(closes, index, 60)
        ma120 = moving_average_at(closes, index, 120)
        ma250 = moving_average_at(closes, index, 250)
        boll_mid = ma20
        std20 = rolling_std_at(closes, index, 20)
        boll_upper = boll_mid + 2 * std20 if boll_mid is not None and std20 is not None else None
        boll_lower = boll_mid - 2 * std20 if boll_mid is not None and std20 is not None else None
        avg_volume_5 = average(volumes[max(0, index - 4) : index + 1])
        avg_volume_20 = average(volumes[max(0, index - 19) : index + 1])
        volume_ratio_5 = volumes[index] / avg_volume_5 if avg_volume_5 else None
        volume_ratio_20 = volumes[index] / avg_volume_20 if avg_volume_20 else None
        macd_dif = dif_values[index]
        macd_dea = dea_values[index]
        series.append(
            {
                "date": row["date"],
                "close": closes[index],
                "high": highs[index],
                "low": lows[index],
                "volume": volumes[index],
                "amount": row["amount"],
                "turnover_rate": row["turnover_rate"],
                "avg_volume_5": avg_volume_5,
                "avg_volume_20": avg_volume_20,
                "volume_ratio_5": volume_ratio_5,
                "volume_ratio_20": volume_ratio_20,
                "ma20": ma20,
                "ma60": ma60,
                "ma120": ma120,
                "ma250": ma250,
                "macd_dif": macd_dif,
                "macd_dea": macd_dea,
                "macd_bar": (macd_dif - macd_dea) * 2,
                "boll_mid": boll_mid,
                "boll_upper": boll_upper,
                "boll_lower": boll_lower,
                "boll_position": classify_boll_position(closes[index], boll_mid, boll_upper, boll_lower),
                "kdj_k": k_values[index],
                "kdj_d": d_values[index],
                "kdj_j": j_values[index],
                "rsi6": rsi6_values[index],
                "rsi12": rsi12_values[index],
                "rsi24": rsi24_values[index],
            }
        )
    return series


def technical_snapshot_from_series(series: list[dict[str, Any]]) -> TechnicalSnapshot:
    if not series:
        return TechnicalSnapshot()

    latest = series[-1]

    snapshot = TechnicalSnapshot(
        trade_date=latest["date"],
        latest_close=latest["close"],
        latest_volume=latest["volume"],
        latest_amount=latest["amount"],
        turnover_rate=latest["turnover_rate"],
        avg_volume_5=latest["avg_volume_5"],
        avg_volume_20=latest["avg_volume_20"],
        volume_ratio_5=latest["volume_ratio_5"],
        macd_dif=latest["macd_dif"],
        macd_dea=latest["macd_dea"],
        macd_bar=latest["macd_bar"],
        boll_mid=latest["boll_mid"],
        boll_upper=latest["boll_upper"],
        boll_lower=latest["boll_lower"],
        boll_position=latest["boll_position"],
        kdj_k=latest["kdj_k"],
        kdj_d=latest["kdj_d"],
        kdj_j=latest["kdj_j"],
        rsi6=latest["rsi6"],
        rsi12=latest["rsi12"],
        rsi24=latest["rsi24"],
    )

    snapshot.signals = build_technical_signals(snapshot)
    return snapshot


def calculate_technical_snapshot(rows: Iterable[dict[str, Any]]) -> TechnicalSnapshot:
    return technical_snapshot_from_series(calculate_technical_series(rows))


def build_technical_signals(snapshot: TechnicalSnapshot) -> list[str]:
    signals: list[str] = []
    if snapshot.volume_ratio_5 is not None:
        if snapshot.volume_ratio_5 >= 1.5:
            signals.append(f"成交量较 5 日均量放大，量比 {snapshot.volume_ratio_5:.2f}")
        elif snapshot.volume_ratio_5 <= 0.7:
            signals.append(f"成交量较 5 日均量收缩，量比 {snapshot.volume_ratio_5:.2f}")
        else:
            signals.append(f"成交量接近 5 日均量，量比 {snapshot.volume_ratio_5:.2f}")

    if snapshot.macd_dif is not None and snapshot.macd_dea is not None and snapshot.macd_bar is not None:
        if snapshot.macd_dif > snapshot.macd_dea and snapshot.macd_bar > 0:
            signals.append("MACD 位于多头区域，短线动能偏强")
        elif snapshot.macd_dif < snapshot.macd_dea and snapshot.macd_bar < 0:
            signals.append("MACD 位于空头区域，短线动能偏弱")
        else:
            signals.append("MACD 动能接近转换区，需要结合后续柱体变化")

    if snapshot.boll_position:
        signals.append(f"BOLL 价格处于{snapshot.boll_position}")

    if snapshot.kdj_k is not None and snapshot.kdj_d is not None and snapshot.kdj_j is not None:
        if snapshot.kdj_j >= 100:
            signals.append("KDJ-J 进入高位区域，短线追高风险上升")
        elif snapshot.kdj_j <= 0:
            signals.append("KDJ-J 进入低位区域，短线可能存在超卖修复")
        elif snapshot.kdj_k > snapshot.kdj_d:
            signals.append("KDJ K 值高于 D 值，短线结构偏强")
        else:
            signals.append("KDJ K 值低于 D 值，短线结构偏弱")

    if snapshot.rsi6 is not None:
        if snapshot.rsi6 >= 80:
            signals.append(f"RSI6 为 {snapshot.rsi6:.2f}，短线偏热")
        elif snapshot.rsi6 <= 20:
            signals.append(f"RSI6 为 {snapshot.rsi6:.2f}，短线偏冷")
        else:
            signals.append(f"RSI6 为 {snapshot.rsi6:.2f}，短线强弱处于常规区间")

    return signals or ["技术指标数据不足，暂不形成技术面判断"]


def ratio_of_true(values: Iterable[bool]) -> float | None:
    items = list(values)
    if not items:
        return None
    return sum(1 for item in items if item) / len(items)


def calculate_window_return(series: list[dict[str, Any]], days: int) -> float | None:
    if len(series) <= days:
        return None
    base = to_number(series[-days - 1].get("close"))
    latest = to_number(series[-1].get("close"))
    if base in (None, 0) or latest is None:
        return None
    return (latest / base - 1) * 100


def latest_ma_for_window(latest: dict[str, Any], days: int) -> float | None:
    if days <= 20:
        return to_number(latest.get("ma20"))
    if days <= 60:
        return to_number(latest.get("ma60"))
    if days <= 120:
        return to_number(latest.get("ma120"))
    return to_number(latest.get("ma250"))


def build_trend_window(series: list[dict[str, Any]], days: int) -> TrendWindow | None:
    if len(series) < days:
        return None
    latest = series[-1]
    latest_close = to_number(latest.get("close"))
    latest_ma = latest_ma_for_window(latest, days)
    close_vs_ma_pct = None
    if latest_close is not None and latest_ma not in (None, 0):
        close_vs_ma_pct = (latest_close / latest_ma - 1) * 100

    window_rows = series[-days:]
    macd_positive_ratio = ratio_of_true(
        to_number(row.get("macd_bar")) is not None and to_number(row.get("macd_bar")) > 0
        for row in window_rows
    )
    boll_mid_above_ratio = ratio_of_true(
        to_number(row.get("close")) is not None
        and to_number(row.get("boll_mid")) is not None
        and to_number(row.get("close")) >= to_number(row.get("boll_mid"))
        for row in window_rows
    )
    return TrendWindow(
        days=days,
        return_pct=calculate_window_return(series, days),
        close_vs_ma_pct=close_vs_ma_pct,
        macd_positive_ratio=macd_positive_ratio,
        boll_mid_above_ratio=boll_mid_above_ratio,
        rsi24=to_number(latest.get("rsi24")),
        volume_ratio_20=to_number(latest.get("volume_ratio_20")),
    )


def add_score_for_threshold(value: float | None, positive_threshold: float, negative_threshold: float) -> int:
    if value is None:
        return 0
    if value >= positive_threshold:
        return 1
    if value <= negative_threshold:
        return -1
    return 0


def calculate_technical_trend(series: list[dict[str, Any]]) -> TechnicalTrendAnalysis:
    windows = [window for days in [20, 60, 120, 250] if (window := build_trend_window(series, days))]
    if not windows:
        return TechnicalTrendAnalysis(signals=["长期技术指标数据不足，至少需要 20 根有效日线"])

    latest = series[-1]
    latest_close = to_number(latest.get("close"))
    ma20 = to_number(latest.get("ma20"))
    ma60 = to_number(latest.get("ma60"))
    ma120 = to_number(latest.get("ma120"))
    ma250 = to_number(latest.get("ma250"))
    score = 0

    threshold_by_days = {
        20: (5, -5),
        60: (10, -10),
        120: (15, -15),
        250: (20, -20),
    }
    for window in windows:
        positive, negative = threshold_by_days[window.days]
        score += add_score_for_threshold(window.return_pct, positive, negative)

    if latest_close is not None and ma20 is not None:
        score += 1 if latest_close >= ma20 else -1
    if latest_close is not None and ma60 is not None:
        score += 1 if latest_close >= ma60 else -1
    if ma20 is not None and ma60 is not None and ma120 is not None:
        if ma20 > ma60 > ma120:
            score += 2
        elif ma20 < ma60 < ma120:
            score -= 2
    if ma60 is not None and ma120 is not None and ma250 is not None:
        if ma60 > ma120 > ma250:
            score += 1
        elif ma60 < ma120 < ma250:
            score -= 1

    recent20 = next((window for window in windows if window.days == 20), None)
    recent60 = next((window for window in windows if window.days == 60), None)
    if recent20:
        score += add_score_for_threshold(recent20.macd_positive_ratio, 0.6, 0.4)
    if recent60:
        score += add_score_for_threshold(recent60.boll_mid_above_ratio, 0.6, 0.4)

    latest_rsi24 = to_number(latest.get("rsi24"))
    if latest_rsi24 is not None:
        if 45 <= latest_rsi24 <= 70:
            score += 1
        elif latest_rsi24 >= 80 or latest_rsi24 <= 30:
            score -= 1

    if score >= 5:
        rating = "技术趋势偏强"
        conclusion = "中长期走势偏强，回调时更适合结合基本面继续跟踪。"
    elif score >= 2:
        rating = "技术趋势中性偏强"
        conclusion = "趋势结构略偏积极，但仍需要观察量能和关键均线能否持续配合。"
    elif score >= -1:
        rating = "技术趋势震荡"
        conclusion = "技术走势偏震荡，尚未形成足够清晰的方向优势。"
    else:
        rating = "技术趋势偏弱"
        conclusion = "中长期走势偏弱，除非基本面显著改善或趋势重新站上关键均线，否则应更谨慎。"

    signals = build_trend_signals(windows, latest, rating, score)
    return TechnicalTrendAnalysis(
        rating=rating,
        score=score,
        conclusion=conclusion,
        windows=windows,
        signals=signals,
    )


def build_trend_signals(windows: list[TrendWindow], latest: dict[str, Any], rating: str, score: int) -> list[str]:
    signals = [f"综合评分 {rating}，分值 {score}"]
    by_days = {window.days: window for window in windows}
    for days in [20, 60, 120, 250]:
        window = by_days.get(days)
        if window and window.return_pct is not None:
            signals.append(f"近 {days} 日涨跌幅 {window.return_pct:.2f}%，相对对应均线 {format_value(window.close_vs_ma_pct, '%')}")

    ma20 = to_number(latest.get("ma20"))
    ma60 = to_number(latest.get("ma60"))
    ma120 = to_number(latest.get("ma120"))
    ma250 = to_number(latest.get("ma250"))
    if ma20 is not None and ma60 is not None and ma120 is not None:
        if ma20 > ma60 > ma120:
            signals.append("MA20 > MA60 > MA120，均线呈多头排列")
        elif ma20 < ma60 < ma120:
            signals.append("MA20 < MA60 < MA120，均线呈空头排列")
        else:
            signals.append("MA20/MA60/MA120 未形成清晰排列，趋势仍有分歧")
    if ma60 is not None and ma120 is not None and ma250 is not None:
        if ma60 > ma120 > ma250:
            signals.append("MA60 > MA120 > MA250，中长期均线结构偏强")
        elif ma60 < ma120 < ma250:
            signals.append("MA60 < MA120 < MA250，中长期均线结构偏弱")

    recent20 = by_days.get(20)
    if recent20 and recent20.macd_positive_ratio is not None:
        signals.append(f"近 20 日 MACD 柱体为正占比 {recent20.macd_positive_ratio * 100:.2f}%")
    recent60 = by_days.get(60)
    if recent60 and recent60.boll_mid_above_ratio is not None:
        signals.append(f"近 60 日收盘价位于 BOLL 中轨上方占比 {recent60.boll_mid_above_ratio * 100:.2f}%")
    return signals


EASTMONEY_STOCK_FIELDS = ",".join(
    [
        "f43",
        "f50",
        "f57",
        "f58",
        "f84",
        "f85",
        "f116",
        "f117",
        "f127",
        "f162",
        "f167",
        "f168",
        "f170",
        "f189",
    ]
)

EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def eastmoney_stock_snapshot(code: str, timeout: float = 10, max_retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = requests.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params={
                    "fltt": "2",
                    "invt": "2",
                    "fields": EASTMONEY_STOCK_FIELDS,
                    "secid": f"{1 if code.startswith('6') else 0}.{code}",
                },
                headers=EASTMONEY_HEADERS,
                timeout=timeout,
            )
            data = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(1 + attempt)
    else:
        raise last_error or RuntimeError(f"东财个股快照请求失败：{code}")

    row = data.get("data") or {}
    if data.get("rc") != 0 or not row:
        raise ValueError(f"东财个股快照为空：{code}")
    return {
        "代码": row.get("f57"),
        "名称": row.get("f58"),
        "最新价": row.get("f43"),
        "涨跌幅": row.get("f170"),
        "总市值": row.get("f116"),
        "流通市值": row.get("f117"),
        "市盈率-动态": row.get("f162"),
        "市净率": row.get("f167"),
        "换手率": row.get("f168"),
        "量比": row.get("f50"),
        "股票代码": row.get("f57"),
        "股票简称": row.get("f58"),
        "行业": row.get("f127"),
        "总股本": row.get("f84"),
        "流通股": row.get("f85"),
        "上市时间": row.get("f189"),
        "最新": row.get("f43"),
    }


def should_stop_eastmoney_attempts(exc: Exception) -> bool:
    text = str(exc)
    return any(
        marker in text
        for marker in [
            "Unable to connect to proxy",
            "RemoteDisconnected",
            "Max retries exceeded",
            "Connection aborted",
        ]
    )


def sina_spot_row_to_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    code = normalize_code(str(row.get("代码", "")))
    name = str(row.get("名称") or "")
    latest = row.get("最新价")
    return {
        "代码": code,
        "名称": name,
        "最新价": latest,
        "涨跌幅": row.get("涨跌幅"),
        "成交量": row.get("成交量"),
        "成交额": row.get("成交额"),
        "股票代码": code,
        "股票简称": name,
        "最新": latest,
        "数据源": "新浪实时行情",
    }


def fetch_sina_spot_snapshot(ak: Any, codes: list[str]) -> tuple[dict[str, dict[str, Any]], str | None]:
    try:
        spot_df = call_akshare_quietly(ak.stock_zh_a_spot)
    except Exception as exc:
        return {}, f"新浪实时行情获取失败：{summarize_exception(exc)}"
    if spot_df is None or spot_df.empty:
        return {}, "新浪实时行情为空"

    code_set = set(codes)
    result: dict[str, dict[str, Any]] = {}
    for _, row in spot_df.iterrows():
        row_dict = dataframe_row_to_dict(row)
        try:
            code = normalize_code(str(row_dict.get("代码", "")))
        except ValueError:
            continue
        if code in code_set:
            result[code] = sina_spot_row_to_snapshot(row_dict)
    if result:
        return result, None
    return {}, "新浪实时行情未覆盖目标股票"


def fetch_code_name_info(ak: Any, code: str) -> tuple[dict[str, Any], str | None]:
    try:
        code_name_df = call_akshare_quietly(ak.stock_info_a_code_name)
    except Exception as exc:
        return {}, f"A股代码名称表获取失败：{summarize_exception(exc)}"
    if code_name_df is None or code_name_df.empty:
        return {}, "A股代码名称表为空"

    for _, row in code_name_df.iterrows():
        row_dict = dataframe_row_to_dict(row)
        try:
            row_code = normalize_code(str(row_dict.get("code") or row_dict.get("代码") or ""))
        except ValueError:
            continue
        if row_code == code:
            name = str(row_dict.get("name") or row_dict.get("名称") or "")
            return {
                "代码": code,
                "名称": name,
                "股票代码": code,
                "股票简称": name,
                "数据源": "A股代码名称表",
            }, None
    return {}, f"A股代码名称表未覆盖目标股票：{code}"


def fetch_spot_snapshot(
    ak: Any,
    codes: list[str],
    skip_eastmoney: bool = False,
) -> tuple[dict[str, dict[str, Any]], str | None]:
    result: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    eastmoney_stopped = False
    if not skip_eastmoney:
        for code in codes:
            try:
                result[code] = eastmoney_stock_snapshot(code)
            except Exception as exc:
                errors.append(f"{code}: {summarize_exception(exc)}")
                if should_stop_eastmoney_attempts(exc):
                    eastmoney_stopped = True
                    break
    missing_codes = [code for code in codes if code not in result]
    fallback_error = None
    if missing_codes:
        fallback_result, fallback_error = fetch_sina_spot_snapshot(ak, missing_codes)
        result.update(fallback_result)
    if result:
        if skip_eastmoney:
            warning = (
                "实时估值快照降级：已跳过Eastmoney；"
                "已使用新浪实时行情补充可用字段；缺少动态市盈率/市净率/市值/股本/行业/上市时间"
            )
            if fallback_error and len(result) < len(codes):
                warning = f"{warning}；{fallback_error}"
            return result, warning
        if errors:
            stop_note = "；已停止继续尝试Eastmoney" if eastmoney_stopped else ""
            warning = (
                f"实时估值快照降级：Eastmoney失败（{'; '.join(errors[:3])}）{stop_note}；"
                "已使用新浪实时行情补充可用字段；缺少动态市盈率/市净率/市值/股本/行业/上市时间"
            )
            if fallback_error and len(result) < len(codes):
                warning = f"{warning}；{fallback_error}"
            return result, warning
        return result, None
    if skip_eastmoney:
        suffix = f"；{fallback_error}" if fallback_error else ""
        return {}, f"实时估值快照获取失败：已跳过Eastmoney{suffix}"
    if errors:
        suffix = f"；{fallback_error}" if fallback_error else ""
        return {}, f"实时估值快照获取失败：{'; '.join(errors[:3])}{suffix}"
    return {}, "实时估值快照为空"


def fetch_akshare_spot_snapshot(ak: Any, codes: list[str]) -> tuple[dict[str, dict[str, Any]], str | None]:
    try:
        spot_df = call_akshare_quietly(ak.stock_zh_a_spot_em)
    except Exception as exc:  # AKShare 数据源偶发超时，单独降级。
        return {}, f"实时估值快照获取失败：{summarize_exception(exc)}"
    if spot_df is None or spot_df.empty:
        return {}, "实时估值快照为空"
    result: dict[str, dict[str, Any]] = {}
    code_set = set(codes)
    for _, row in spot_df.iterrows():
        row_dict = dataframe_row_to_dict(row)
        code = normalize_code(str(row_dict.get("代码", "")))
        if code in code_set:
            result[code] = row_dict
    return result, None


def fetch_individual_info(ak: Any, code: str, skip_eastmoney: bool = False) -> tuple[dict[str, Any], str | None]:
    if skip_eastmoney:
        fallback, fallback_error = fetch_code_name_info(ak, code)
        if fallback:
            return fallback, (
                "个股信息降级：已跳过Eastmoney；"
                "已使用A股代码名称表；缺少行业/股本/上市时间/估值字段"
            )
        suffix = f"；{fallback_error}" if fallback_error else ""
        return {}, f"个股信息获取失败：已跳过Eastmoney{suffix}"
    try:
        snapshot = eastmoney_stock_snapshot(code)
    except Exception as exc:
        eastmoney_error = summarize_exception(exc)
        fallback, fallback_error = fetch_code_name_info(ak, code)
        if fallback:
            return fallback, (
                f"个股信息降级：Eastmoney失败（{eastmoney_error}）；"
                "已使用A股代码名称表；缺少行业/股本/上市时间/估值字段"
            )
        suffix = f"；{fallback_error}" if fallback_error else ""
        return {}, f"个股信息获取失败：{eastmoney_error}{suffix}"
    return snapshot, None


def fetch_akshare_individual_info(ak: Any, code: str) -> tuple[dict[str, Any], str | None]:
    try:
        info_df = call_akshare_quietly(ak.stock_individual_info_em, symbol=code, timeout=10)
    except Exception as exc:
        return {}, f"个股信息获取失败：{summarize_exception(exc)}"
    if info_df is None or info_df.empty:
        return {}, "个股信息为空"
    info: dict[str, Any] = {}
    for _, row in info_df.iterrows():
        row_dict = dataframe_row_to_dict(row)
        item = row_dict.get("item")
        if item:
            info[str(item)] = row_dict.get("value")
    return info, None


def fetch_financial_indicator(
    ak: Any,
    code: str,
    start_year: str,
    as_of_date: dt.date | None = None,
) -> tuple[dict[str, Any], str, str | None]:
    if as_of_date is not None:
        return {}, "", "历史回填模式不使用实时财务指标接口，避免未来财报影响历史评分"
    try:
        indicator_df = call_akshare_quietly(
            ak.stock_financial_analysis_indicator,
            symbol=code,
            start_year=start_year,
        )
    except Exception as exc:
        return {}, "", f"财务指标获取失败：{summarize_exception(exc)}"
    if indicator_df is None or indicator_df.empty:
        return {}, "", "财务指标为空；可尝试把 --start-year 调早一些"
    indicator_df = indicator_df.sort_values(by="日期", ascending=True)
    latest = dataframe_row_to_dict(indicator_df.iloc[-1])
    report_date = str(latest.get("日期", ""))
    return latest, report_date, None


def fetch_technical_snapshot(
    ak: Any,
    code: str,
    technical_days: int,
    adjust: str,
    as_of_date: dt.date | None = None,
) -> tuple[TechnicalSnapshot | None, TechnicalTrendAnalysis | None, str | None]:
    end_date = as_of_date or dt.date.today()
    warmup_rows = max(technical_days, 260)
    start_date = end_date - dt.timedelta(days=max(warmup_rows * 3, 520))
    try:
        hist_df = call_akshare_quietly(
            ak.stock_zh_a_daily,
            symbol=sina_symbol(code),
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust=adjust,
        )
    except Exception as exc:
        return None, None, f"技术面日线获取失败：{summarize_exception(exc)}"
    if hist_df is None or hist_df.empty:
        return None, None, "技术面日线为空"
    raw_rows: list[dict[str, Any]] = []
    for _, row in hist_df.iterrows():
        row_dict = dataframe_row_to_dict(row)
        row_date = parse_date_like(row_dict.get("date"))
        if as_of_date is not None and (row_date is None or row_date > as_of_date):
            continue
        raw_rows.append(row_dict)
    if not raw_rows:
        return None, None, f"技术面日线截至 {end_date:%Y-%m-%d} 为空"

    rows: list[dict[str, Any]] = []
    for row_dict in raw_rows[-warmup_rows:]:
        volume = to_number(row_dict.get("volume"))
        turnover = to_number(row_dict.get("turnover"))
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
    series = calculate_technical_series(rows)
    snapshot = technical_snapshot_from_series(series)
    if not snapshot.trade_date:
        return None, None, "技术面日线缺少可计算的 OHLCV 数据"
    trend = calculate_technical_trend(series)
    return snapshot, trend, None


def build_analysis(
    ak: Any,
    code: str,
    start_year: str,
    spot: dict[str, dict[str, Any]],
    technical_days: int,
    adjust: str,
    as_of_date: dt.date | None = None,
    skip_eastmoney: bool = False,
) -> StockAnalysis:
    analysis = StockAnalysis(code=code)

    spot_row = spot.get(code, {})
    if spot_row:
        info, info_error = spot_row, None
    else:
        info, info_error = fetch_individual_info(ak, code, skip_eastmoney)
    if info_error:
        analysis.source_errors.append(info_error)

    financial, report_date, financial_error = fetch_financial_indicator(ak, code, start_year, as_of_date)
    if financial_error:
        analysis.source_errors.append(financial_error)

    technical, technical_trend, technical_error = fetch_technical_snapshot(ak, code, technical_days, adjust, as_of_date)
    if technical_error:
        analysis.source_errors.append(technical_error)
    analysis.technical = technical
    analysis.technical_trend = technical_trend

    analysis.name = str(spot_row.get("名称") or info.get("股票简称") or "")
    analysis.industry = str(info.get("行业") or "")
    analysis.listed_at = format_date_like(info.get("上市时间"))
    analysis.report_date = report_date

    analysis.overview = {
        "最新价": spot_row.get("最新价") or info.get("最新"),
        "涨跌幅": spot_row.get("涨跌幅"),
        "总市值": spot_row.get("总市值") or info.get("总市值"),
        "流通市值": spot_row.get("流通市值") or info.get("流通市值"),
        "总股本": info.get("总股本"),
        "流通股": info.get("流通股"),
    }
    analysis.valuation = {
        "市盈率-动态": spot_row.get("市盈率-动态"),
        "市净率": spot_row.get("市净率"),
        "换手率": spot_row.get("换手率"),
        "量比": spot_row.get("量比"),
    }

    for key, label, unit in DISPLAY_METRICS:
        source_name, value = pick_metric(financial, key) if financial else (None, None)
        analysis.metrics.append(Metric(label=label, value=value, unit=unit, source_name=source_name))

    evaluate_analysis(analysis)
    return analysis


def evaluate_analysis(analysis: StockAnalysis) -> None:
    metric_map = {metric.label: metric.value for metric in analysis.metrics}
    pe = to_number(analysis.valuation.get("市盈率-动态"))
    pb = to_number(analysis.valuation.get("市净率"))
    roe = metric_map.get("ROE")
    revenue_growth = metric_map.get("营收增长")
    profit_growth = metric_map.get("净利润增长")
    debt_ratio = metric_map.get("资产负债率")
    ocf_per_share = metric_map.get("每股经营现金流")
    ocf_to_profit = metric_map.get("经营现金流/净利润")
    financial_industry = any(word in analysis.industry for word in ["银行", "保险", "证券", "金融"])

    if roe is not None:
        if roe >= 15:
            analysis.strengths.append(f"ROE {roe:.2f}%，股东回报能力较强")
        elif roe < 5:
            analysis.risks.append(f"ROE {roe:.2f}%，盈利效率偏弱")

    if revenue_growth is not None and profit_growth is not None:
        if revenue_growth > 10 and profit_growth > 10:
            analysis.strengths.append("营收和净利润均保持两位数增长，成长性表现较好")
        elif revenue_growth < 0 and profit_growth < 0:
            analysis.risks.append("营收与净利润同比均为负，经营增长承压")
        elif revenue_growth > 0 > profit_growth:
            analysis.risks.append("营收增长但净利润下滑，需关注费用、毛利率或减值压力")

    lacks_industry = not analysis.industry
    lacks_liquidity_metrics = metric_map.get("流动比率") is None and metric_map.get("速动比率") is None
    if debt_ratio is not None and lacks_industry and debt_ratio > 85 and lacks_liquidity_metrics:
        analysis.risks.append(
            f"资产负债率 {debt_ratio:.2f}%，行业信息缺失；若属于金融行业需按行业口径另行判断"
        )
    elif debt_ratio is not None and not financial_industry:
        if debt_ratio < 45:
            analysis.strengths.append(f"资产负债率 {debt_ratio:.2f}%，资本结构相对稳健")
        elif debt_ratio > 70:
            analysis.risks.append(f"资产负债率 {debt_ratio:.2f}%，偿债压力需要重点跟踪")
    elif debt_ratio is not None and financial_industry:
        analysis.risks.append("金融行业资产负债率口径特殊，需结合资本充足率等行业指标另行判断")

    if ocf_per_share is not None:
        if ocf_per_share > 0:
            analysis.strengths.append("每股经营现金流为正，利润质量有现金流支撑")
        else:
            analysis.risks.append("每股经营现金流为负，需关注回款和现金流质量")
    if ocf_to_profit is not None and ocf_to_profit < 0.5:
        analysis.risks.append(f"经营现金流/净利润 {ocf_to_profit:.2f}倍，利润现金含量偏弱")

    if pe is not None:
        if pe <= 0:
            analysis.risks.append("动态市盈率为负或不可用，可能处于亏损或盈利异常阶段")
        elif pe < 15:
            analysis.strengths.append(f"动态市盈率 {pe:.2f}，估值相对不高")
        elif pe > 60:
            analysis.risks.append(f"动态市盈率 {pe:.2f}，估值对成长兑现要求较高")
    if pb is not None:
        if pb < 1:
            analysis.strengths.append(f"市净率 {pb:.2f}，账面价值角度估值较低")
        elif pb > 5:
            analysis.risks.append(f"市净率 {pb:.2f}，资产价格溢价较高")

    if not analysis.strengths:
        analysis.strengths.append("暂未从已获取指标中识别出明显优势")
    if not analysis.risks:
        analysis.risks.append("暂未从已获取指标中识别出明显风险点")


def format_date_like(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def format_value(value: Any, unit: str = "") -> str:
    number = to_number(value)
    if number is None:
        return MISSING
    if unit == "%":
        return f"{number:.2f}%"
    if unit == "元":
        return f"{number:.3f}元"
    if unit == "倍":
        return f"{number:.2f}倍"
    return f"{number:.2f}"


def format_money(value: Any) -> str:
    number = to_number(value)
    if number is None:
        return MISSING
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:.2f}亿"
    if abs(number) >= 10_000:
        return f"{number / 10_000:.2f}万"
    return f"{number:.2f}"


def format_quantity(value: Any, unit: str = "") -> str:
    number = to_number(value)
    if number is None:
        return MISSING
    return f"{number:,.0f}{unit}"


def format_decimal(value: Any, digits: int = 3) -> str:
    number = to_number(value)
    if number is None:
        return MISSING
    return f"{number:.{digits}f}"


def grade_overall(analysis: StockAnalysis) -> str:
    positive = sum(1 for item in analysis.strengths if not item.startswith("暂未"))
    negative = sum(1 for item in analysis.risks if not item.startswith("暂未"))
    if analysis.source_errors and positive == 0 and negative == 0:
        return "数据不足，暂不形成判断"
    if positive >= negative + 2:
        return "基本面质量偏强，但仍需结合行业周期、估值分位和后续财报验证"
    if negative >= positive + 2:
        return "基本面信号偏谨慎，建议先核查风险指标变化原因"
    return "基本面信号中性，优势与风险需要结合行业和估值进一步比较"


def render_markdown(analyses: list[StockAnalysis]) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 股票基本面分析报告",
        "",
        f"- 生成时间：{now}",
        "- 数据源：AKShare（东方财富实时行情/个股信息，新浪财务指标/日线行情）",
        "- 说明：本报告仅供研究和自动化筛查，不构成投资建议。",
        "",
    ]
    for analysis in analyses:
        title_name = f" {analysis.name}" if analysis.name else ""
        lines.extend(
            [
                f"## {analysis.code}{title_name}",
                "",
                "### 公司与行情概览",
                "",
                f"- 行业：{analysis.industry or MISSING}",
                f"- 上市时间：{analysis.listed_at or MISSING}",
                f"- 最新价：{format_value(analysis.overview.get('最新价'))}",
                f"- 涨跌幅：{format_value(analysis.overview.get('涨跌幅'), '%')}",
                f"- 总市值：{format_money(analysis.overview.get('总市值'))}",
                f"- 流通市值：{format_money(analysis.overview.get('流通市值'))}",
                "",
                "### 估值与交易活跃度",
                "",
                f"- 动态市盈率：{format_value(analysis.valuation.get('市盈率-动态'))}",
                f"- 市净率：{format_value(analysis.valuation.get('市净率'))}",
                f"- 换手率：{format_value(analysis.valuation.get('换手率'), '%')}",
                f"- 量比：{format_value(analysis.valuation.get('量比'))}",
                "",
            ]
        )
        if analysis.technical:
            technical = analysis.technical
            lines.extend(
                [
                    f"### 技术面指标快照（交易日：{technical.trade_date or MISSING}）",
                    "",
                    "| 指标 | 数值 |",
                    "| --- | ---: |",
                    f"| 成交量 | {format_quantity(technical.latest_volume, '手')} / 5日量比 {format_decimal(technical.volume_ratio_5, 2)} |",
                    f"| 成交额 | {format_money(technical.latest_amount)} |",
                    f"| 换手率 | {format_value(technical.turnover_rate, '%')} |",
                    f"| MACD | DIF {format_decimal(technical.macd_dif)} / DEA {format_decimal(technical.macd_dea)} / 柱 {format_decimal(technical.macd_bar)} |",
                    f"| BOLL | 中轨 {format_decimal(technical.boll_mid)} / 上轨 {format_decimal(technical.boll_upper)} / 下轨 {format_decimal(technical.boll_lower)} / {technical.boll_position or MISSING} |",
                    f"| KDJ | K {format_decimal(technical.kdj_k, 2)} / D {format_decimal(technical.kdj_d, 2)} / J {format_decimal(technical.kdj_j, 2)} |",
                    f"| RSI | RSI6 {format_decimal(technical.rsi6, 2)} / RSI12 {format_decimal(technical.rsi12, 2)} / RSI24 {format_decimal(technical.rsi24, 2)} |",
                    "",
                    "**技术面解读**",
                    "",
                ]
            )
            lines.extend(f"- {item}" for item in technical.signals)
            lines.append("")
        else:
            lines.extend(
                [
                    "### 技术面指标快照",
                    "",
                    "- 暂无可计算的技术面数据",
                    "",
                ]
            )
        if analysis.technical_trend:
            trend = analysis.technical_trend
            lines.extend(
                [
                    "### 长期技术趋势分析",
                    "",
                    f"- 趋势评级：{trend.rating}",
                    f"- 趋势评分：{trend.score}",
                    f"- 走势结论：{trend.conclusion}",
                    "",
                    "| 窗口 | 涨跌幅 | 相对均线 | MACD柱体为正占比 | BOLL中轨上方占比 |",
                    "| --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for window in trend.windows:
                lines.append(
                    f"| {window.days}日 | {format_value(window.return_pct, '%')} | "
                    f"{format_value(window.close_vs_ma_pct, '%')} | "
                    f"{format_value(ratio_to_percent(window.macd_positive_ratio), '%')} | "
                    f"{format_value(ratio_to_percent(window.boll_mid_above_ratio), '%')} |"
                )
            lines.extend(["", "**长期趋势信号**", ""])
            lines.extend(f"- {item}" for item in trend.signals)
            lines.append("")
        lines.extend(
            [
                f"### 财务指标快照（报告期：{analysis.report_date or MISSING}）",
                "",
                "| 指标 | 数值 | 来源字段 |",
                "| --- | ---: | --- |",
            ]
        )
        for metric in analysis.metrics:
            lines.append(
                f"| {metric.label} | {format_value(metric.value, metric.unit)} | {metric.source_name or MISSING} |"
            )
        lines.extend(
            [
                "",
                "### 基本面解读",
                "",
                "**优势观察**",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in analysis.strengths)
        lines.extend(["", "**风险观察**", ""])
        lines.extend(f"- {item}" for item in analysis.risks)
        if analysis.source_errors:
            lines.extend(["", "**数据获取提醒**", ""])
            lines.extend(f"- {item}" for item in analysis.source_errors)
        lines.extend(["", f"**综合观察：** {grade_overall(analysis)}", ""])
    return "\n".join(lines).rstrip() + "\n"


def analyses_to_jsonable(analyses: list[StockAnalysis]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for analysis in analyses:
        payload.append(
            {
                "code": analysis.code,
                "name": analysis.name,
                "industry": analysis.industry,
                "listed_at": analysis.listed_at,
                "report_date": analysis.report_date,
                "overview": analysis.overview,
                "valuation": analysis.valuation,
                "technical": technical_to_jsonable(analysis.technical),
                "technical_trend": technical_trend_to_jsonable(analysis.technical_trend),
                "metrics": [
                    {
                        "label": metric.label,
                        "value": metric.value,
                        "unit": metric.unit,
                        "source_name": metric.source_name,
                    }
                    for metric in analysis.metrics
                ],
                "strengths": analysis.strengths,
                "risks": analysis.risks,
                "source_errors": analysis.source_errors,
                "overall": grade_overall(analysis),
            }
        )
    return payload


def ratio_to_percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100


def technical_to_jsonable(snapshot: TechnicalSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "trade_date": snapshot.trade_date,
        "latest_close": snapshot.latest_close,
        "latest_volume": snapshot.latest_volume,
        "latest_amount": snapshot.latest_amount,
        "turnover_rate": snapshot.turnover_rate,
        "avg_volume_5": snapshot.avg_volume_5,
        "avg_volume_20": snapshot.avg_volume_20,
        "volume_ratio_5": snapshot.volume_ratio_5,
        "macd": {
            "dif": snapshot.macd_dif,
            "dea": snapshot.macd_dea,
            "bar": snapshot.macd_bar,
        },
        "boll": {
            "mid": snapshot.boll_mid,
            "upper": snapshot.boll_upper,
            "lower": snapshot.boll_lower,
            "position": snapshot.boll_position,
        },
        "kdj": {
            "k": snapshot.kdj_k,
            "d": snapshot.kdj_d,
            "j": snapshot.kdj_j,
        },
        "rsi": {
            "rsi6": snapshot.rsi6,
            "rsi12": snapshot.rsi12,
            "rsi24": snapshot.rsi24,
        },
        "signals": snapshot.signals,
    }


def technical_trend_to_jsonable(trend: TechnicalTrendAnalysis | None) -> dict[str, Any] | None:
    if trend is None:
        return None
    return {
        "rating": trend.rating,
        "score": trend.score,
        "conclusion": trend.conclusion,
        "windows": [
            {
                "days": window.days,
                "return_pct": window.return_pct,
                "close_vs_ma_pct": window.close_vs_ma_pct,
                "macd_positive_ratio": window.macd_positive_ratio,
                "boll_mid_above_ratio": window.boll_mid_above_ratio,
                "rsi24": window.rsi24,
                "volume_ratio_20": window.volume_ratio_20,
            }
            for window in trend.windows
        ],
        "signals": trend.signals,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="输入一串 A 股代码，批量生成基本面和技术面分析报告。")
    parser.add_argument("codes", nargs="*", help="股票代码，支持空格、英文逗号、中文逗号分隔；不传则读取 stock.md")
    parser.add_argument(
        "--codes-file",
        default=str(DEFAULT_CODES_FILE),
        help="股票代码文件，默认读取项目根目录 stock.md；仅在不传 codes 时生效",
    )
    parser.add_argument(
        "--start-year",
        default=str(dt.date.today().year - 5),
        help="财务指标抓取起始年份，默认取最近约 5 年",
    )
    parser.add_argument("-o", "--output", help="输出文件路径；不传则打印到终端")
    parser.add_argument("--json", action="store_true", help="输出 JSON，便于后续程序处理")
    parser.add_argument("--technical-days", type=int, default=120, help="技术指标保留的最近日线数量，长期趋势会至少自动保留 260 根")
    parser.add_argument(
        "--adjust",
        default="qfq",
        choices=["none", "qfq", "hfq"],
        help="日线复权方式：none 为不复权，qfq 为前复权，hfq 为后复权；默认 qfq",
    )
    parser.add_argument("--as-of-date", type=parse_arg_date, help="按指定日期回看分析，只使用该日期及以前的日线数据")
    return parser.parse_args(argv)


def parse_arg_date(value: str) -> dt.date:
    parsed = parse_date_like(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD")
    return parsed


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        codes = resolve_input_codes(args.codes, args.codes_file)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2

    try:
        import akshare as ak
    except ImportError:
        print("缺少依赖：请先安装 requirements.txt 中的依赖，或使用 README 里的 uv 命令运行。", file=sys.stderr)
        return 1

    if args.as_of_date:
        spot, spot_error = {}, "历史回填模式不使用实时行情/估值快照"
    else:
        spot, spot_error = fetch_spot_snapshot(ak, codes)
    adjust = "" if args.adjust == "none" else args.adjust
    analyses: list[StockAnalysis] = []
    for code in codes:
        analysis = build_analysis(ak, code, args.start_year, spot, args.technical_days, adjust, args.as_of_date)
        if spot_error:
            analysis.source_errors.append(spot_error)
        analyses.append(analysis)

    if args.json:
        content = json.dumps(analyses_to_jsonable(analyses), ensure_ascii=False, indent=2)
    else:
        content = render_markdown(analyses)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
