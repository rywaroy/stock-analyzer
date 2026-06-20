import importlib.util
import contextlib
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import stock_fundamental_analysis as sfa
import save_daily_to_mysql as mysql_sink
import research_signal_backtest as research_backtest
import signal_accuracy
from stock_fundamental_analysis import (
    DISPLAY_METRICS,
    Metric,
    StockAnalysis,
    evaluate_analysis,
    format_money,
    load_codes_from_file,
    normalize_code,
    parse_codes,
    pick_metric,
    render_markdown,
)


SCORER_PATH = Path(__file__).resolve().parents[1] / ".codex/skills/stock-buy-signal-analysis/scripts/analyze_stock.py"


def make_ai_etf_result(index: int, trade_date: str = "2026-06-12") -> dict:
    code = f"{index:06d}"
    score = 80 - index
    return {
        "code": code,
        "name": f"测试股票{index}",
        "score": score,
        "signal": "买入偏向" if score >= 15 else "观望",
        "confidence": "高" if index % 3 else "中",
        "regime": "trend",
        "advice": "测试建议",
        "horizon_scores": {
            "short_term": {"label": "短期", "score": 30 - index, "signal": "买入偏向"},
            "medium_term": {"label": "中期", "score": 60 - index, "signal": "买入偏向"},
            "long_term": {"label": "长期", "score": 70 - index, "signal": "买入偏向"},
        },
        "parts": [],
        "source_errors": [],
        "raw": {
            "code": code,
            "name": f"测试股票{index}",
            "industry": "测试行业",
            "listed_at": "2020-01-01",
            "report_date": "2026-03-31",
            "overview": {},
            "technical": {
                "trade_date": trade_date,
                "latest_close": 10 + index,
            },
            "technical_trend": {"rating": "技术趋势偏强", "score": 60 - index, "windows": []},
            "metrics": [],
            "strengths": [f"优势{index}"],
            "risks": [f"风险{index}"],
        },
    }


def load_signal_scorer():
    spec = importlib.util.spec_from_file_location("stock_buy_signal_scorer", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载评分脚本：{SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StockFundamentalAnalysisTest(unittest.TestCase):
    def make_research_rows(self, count: int = 270) -> list[dict]:
        start = dt.date(2025, 1, 1)
        rows = []
        for index in range(count):
            close = 10 + index * 0.1
            rows.append(
                {
                    "日期": (start + dt.timedelta(days=index)).isoformat(),
                    "收盘": close,
                    "最高": close + 0.3,
                    "最低": close - 0.3,
                    "成交量": 100_000 + index * 100,
                    "成交额": 1_000_000 + index * 1000,
                    "换手率": 1.0,
                }
            )
        return rows

    def test_research_backtest_builds_scoring_item_without_future_rows(self):
        series = sfa.calculate_technical_series(self.make_research_rows())
        signal_index = 249

        item = research_backtest.build_scoring_item_from_series("000001", "平安银行", series, signal_index)

        self.assertEqual(item["technical"]["trade_date"], series[signal_index]["date"])
        self.assertEqual(item["technical"]["latest_close"], series[signal_index]["close"])
        self.assertNotEqual(item["technical"]["trade_date"], series[-1]["date"])
        self.assertIn("避免未来函数", item["source_errors"][0])

    def test_research_backtest_evaluates_future_trading_windows_after_signal_date(self):
        series = sfa.calculate_technical_series(self.make_research_rows())
        signal_index = 249
        result = {
            "code": "000001",
            "name": "平安银行",
            "regime": "trend",
            "horizon_scores": {
                "short_term": {"score": 72, "signal": "强买"},
                "medium_term": {"score": 18, "signal": "买入偏向"},
                "long_term": {"score": -20, "signal": "卖出偏向"},
            },
        }

        outcomes = research_backtest.evaluate_result_windows(result, series, signal_index)
        short_day_1 = next(item for item in outcomes if item["horizon"] == "short_term" and item["window_days"] == 1)
        long_day_120 = [item for item in outcomes if item["horizon"] == "long_term" and item["window_days"] == 120]

        self.assertEqual(short_day_1["signal_trade_date"], series[signal_index]["date"])
        self.assertEqual(short_day_1["target_trade_date"], series[signal_index + 1]["date"])
        self.assertGreater(short_day_1["return_pct"], 0)
        self.assertTrue(short_day_1["hit"])
        self.assertIn("repair_continuity", short_day_1["factors"])
        self.assertIn("macd_repair_continuity", short_day_1["factors"])
        self.assertIn("repair_quality_sync", short_day_1["factors"])
        self.assertIn("horizon_stage_category", short_day_1["factors"])
        self.assertEqual(long_day_120, [])

    def test_research_backtest_extracts_factor_tags_from_visible_snapshot(self):
        result = {
            "regime": "trend",
            "horizon_scores": {
                "short_term": {"score": -3, "signal": "观望"},
                "medium_term": {"score": 32, "signal": "买入偏向"},
                "long_term": {"score": 61, "signal": "强买"},
            },
            "raw": {
                "technical": {
                    "volume_ratio_5": 1.8,
                    "macd": {"dif": 0.8, "dea": 0.5, "bar": 0.6},
                    "boll": {"position": "中轨上方"},
                    "kdj": {"j": 86},
                    "rsi": {"rsi6": 66},
                },
                "technical_trend": {
                    "windows": [
                        {"days": 20, "return_pct": -3},
                        {"days": 60, "return_pct": 12},
                        {"days": 120, "return_pct": 18},
                        {"days": 250, "return_pct": 5},
                    ]
                },
            },
        }

        factors = research_backtest.extract_factor_tags(result)

        self.assertEqual(factors["regime"], "trend")
        self.assertEqual(factors["macd_state"], "多头")
        self.assertEqual(factors["boll_position"], "中轨上方")
        self.assertEqual(factors["kdj_j_zone"], "偏高")
        self.assertEqual(factors["rsi6_zone"], "偏热")
        self.assertEqual(factors["volume_state"], "放量")
        self.assertEqual(factors["trend_20d"], "震荡")
        self.assertEqual(factors["trend_60d"], "上涨")
        self.assertEqual(factors["trend_120d"], "上涨")
        self.assertEqual(factors["horizon_alignment"], "中长期偏多短期观望")
        self.assertEqual(factors["decline_duration"], "混合")
        self.assertEqual(factors["decline_speed"], "短期转弱")
        self.assertEqual(factors["weak_tail_extreme"], "常规")
        self.assertEqual(factors["tail_repair_signal"], "常规")

    def test_research_backtest_classifies_weak_tail_factor_states(self):
        self.assertEqual(
            research_backtest.decline_duration_state(-8, -12, -18, (-5, -10, -15)),
            "短中长期同步下跌",
        )
        self.assertEqual(
            research_backtest.decline_duration_state(2, -12, -18, (-5, -10, -15)),
            "短期修复中期仍弱",
        )
        self.assertEqual(research_backtest.decline_speed_state(-2, -18), "跌速放缓")
        self.assertEqual(research_backtest.decline_speed_state(-12, -18), "跌速加快")
        self.assertEqual(research_backtest.weak_tail_extreme_state("跌破下轨", 48, 55), "极端超卖")
        self.assertEqual(research_backtest.weak_tail_extreme_state("中轨下方", 44, 30), "弱势低位")
        self.assertEqual(
            research_backtest.tail_repair_signal_state("极端超卖", "多头", "中轨下方", 42, 12, "放量"),
            "低位放量转强",
        )
        self.assertEqual(
            research_backtest.tail_repair_signal_state("弱势低位", "转换", "中轨下方", 47, 22, "常规"),
            "低位修复确认",
        )
        self.assertEqual(
            research_backtest.tail_repair_signal_state("弱势低位", "空头", "中轨下方", 35, 10, "缩量"),
            "低位空头延续",
        )

    def test_research_backtest_classifies_continuous_repair_factor_states(self):
        series = [
            {
                "macd_bar": bar,
                "rsi6": rsi,
                "kdj_j": kdj,
                "boll_position": boll,
                "volume_ratio_5": volume,
            }
            for bar, rsi, kdj, boll, volume in [
                (-0.8, 18, -5, "跌破下轨", 0.8),
                (-0.7, 22, 2, "跌破下轨", 0.9),
                (-0.5, 27, 8, "中轨下方", 1.1),
                (-0.2, 33, 16, "中轨下方", 1.3),
                (0.1, 42, 32, "中轨上方", 1.6),
            ]
        ]

        factors = research_backtest.continuous_repair_factor_tags_from_series(series)

        self.assertEqual(factors["macd_repair_continuity"], "MACD翻红")
        self.assertEqual(factors["rsi_rebound_continuity"], "低位连续回升")
        self.assertEqual(factors["kdj_rebound_continuity"], "低位连续回升")
        self.assertEqual(factors["boll_recovery_continuity"], "重新站上中轨")
        self.assertEqual(factors["volume_continuity"], "单日放量")
        self.assertEqual(factors["repair_continuity"], "连续修复确认")
        self.assertEqual(factors["repair_speed"], "快速修复确认")
        self.assertEqual(factors["macd_repair_speed"], "速度改善明显")
        self.assertEqual(factors["rsi_rebound_speed"], "速度改善明显")
        self.assertEqual(factors["kdj_rebound_speed"], "速度改善明显")
        self.assertEqual(factors["boll_recovery_speed"], "速度温和改善")
        self.assertEqual(factors["volume_expansion_speed"], "速度改善明显")
        self.assertEqual(factors["repair_speed_profile"], "速度共振明显")

    def test_research_backtest_classifies_continuous_speed_profile(self):
        fast_series = [
            {
                "macd_bar": bar,
                "rsi6": rsi,
                "kdj_j": kdj,
                "boll_position": boll,
                "volume_ratio_5": volume,
            }
            for bar, rsi, kdj, boll, volume in [
                (-1.0, 19, -8, "跌破下轨", 0.7),
                (-0.8, 23, -2, "跌破下轨", 0.9),
                (-0.5, 31, 9, "中轨下方", 1.0),
                (-0.1, 39, 19, "中轨下方", 1.3),
                (0.2, 50, 35, "中轨上方", 1.7),
            ]
        ]
        weak_series = [
            {
                "macd_bar": bar,
                "rsi6": rsi,
                "kdj_j": kdj,
                "boll_position": "跌破下轨",
                "volume_ratio_5": volume,
            }
            for bar, rsi, kdj, volume in [
                (-0.2, 29, 18, 1.0),
                (-0.3, 27, 15, 0.9),
                (-0.4, 25, 12, 0.8),
                (-0.5, 23, 10, 0.7),
            ]
        ]

        fast_factors = research_backtest.continuous_repair_factor_tags_from_series(fast_series)
        weak_factors = research_backtest.continuous_repair_factor_tags_from_series(weak_series)

        self.assertEqual(fast_factors["repair_speed_profile"], "速度共振明显")
        self.assertEqual(weak_factors["repair_speed_profile"], "速度未形成")

    def test_research_backtest_classifies_repair_quality_confirmation(self):
        confirmed = {
            "tail_repair_signal": "低位修复确认",
            "volume_expansion_speed": "速度改善明显",
            "macd_repair_speed": "速度温和改善",
            "boll_recovery_speed": "速度温和改善",
            "decline_speed": "跌速放缓",
            "repair_speed_profile": "速度共振偏强",
        }
        deteriorating = {
            "tail_repair_signal": "低位放量未确认",
            "volume_expansion_speed": "速度恶化",
            "macd_repair_speed": "速度恶化",
            "boll_recovery_speed": "速度未改善",
            "decline_speed": "跌速持平",
            "repair_speed_profile": "速度分化",
        }
        market_confirmed = {
            "market_tail_repair_signal": "低位放量转强",
            "market_volume_expansion_speed": "速度温和改善",
            "market_macd_repair_speed": "速度未改善",
            "market_boll_recovery_speed": "速度温和改善",
            "market_decline_speed": "跌速放缓",
            "market_repair_speed_profile": "速度温和共振",
        }

        self.assertEqual(research_backtest.repair_quality_confirmation_state(confirmed), "修复质量确认")
        self.assertEqual(research_backtest.repair_quality_confirmation_state(deteriorating), "修复质量恶化")
        self.assertEqual(
            research_backtest.repair_quality_confirmation_state(market_confirmed, prefix="market_"),
            "修复质量确认",
        )

    def test_research_backtest_classifies_repair_quality_sync(self):
        self.assertEqual(
            research_backtest.repair_quality_sync_state(
                {
                    "market_repair_quality_confirmation": "修复质量确认",
                    "repair_quality_confirmation": "修复质量初步确认",
                }
            ),
            "双侧质量同步确认",
        )
        self.assertEqual(
            research_backtest.repair_quality_sync_state(
                {
                    "market_repair_quality_confirmation": "修复质量确认",
                    "repair_quality_confirmation": "修复质量分化",
                }
            ),
            "市场确认个股不恶化",
        )
        self.assertEqual(
            research_backtest.repair_quality_sync_state(
                {
                    "market_repair_quality_confirmation": "修复质量恶化",
                    "repair_quality_confirmation": "修复质量确认",
                }
            ),
            "单侧确认对侧恶化",
        )
        self.assertEqual(
            research_backtest.repair_quality_sync_state(
                {
                    "market_repair_quality_confirmation": "修复质量恶化",
                    "repair_quality_confirmation": "修复质量恶化",
                }
            ),
            "双侧质量恶化",
        )

    def test_research_backtest_classifies_repair_speed_states(self):
        gradual_factors = {
            "macd_repair_continuity": "空头连续收敛",
            "rsi_rebound_continuity": "低位初步回升",
            "kdj_rebound_continuity": "低位初步回升",
            "boll_recovery_continuity": "重新站回下轨内",
            "volume_continuity": "常规",
            "repair_continuity": "修复初步形成",
        }
        weak_factors = {
            "macd_repair_continuity": "空头继续扩散",
            "rsi_rebound_continuity": "低位钝化",
            "kdj_rebound_continuity": "低位钝化",
            "boll_recovery_continuity": "仍跌破下轨",
            "volume_continuity": "连续缩量",
            "repair_continuity": "弱势延续确认",
        }

        self.assertEqual(research_backtest.repair_speed_state(gradual_factors), "渐进修复")
        self.assertEqual(research_backtest.repair_speed_state(weak_factors), "修复未确认")

    def test_research_backtest_classifies_refined_market_regimes(self):
        def make_result(
            r20: float,
            r60: float,
            r120: float,
            r250: float,
            regime: str = "mixed",
            boll_position: str = "中轨上方",
            rsi6: float = 55,
            kdj_j: float = 50,
            macd_bar: float = 0,
        ) -> dict:
            return {
                "regime": regime,
                "raw": {
                    "technical": {
                        "boll": {"position": boll_position},
                        "rsi": {"rsi6": rsi6},
                        "kdj": {"j": kdj_j},
                        "macd": {"bar": macd_bar},
                    },
                    "technical_trend": {
                        "windows": [
                            {"days": 20, "return_pct": r20},
                            {"days": 60, "return_pct": r60},
                            {"days": 120, "return_pct": r120},
                            {"days": 250, "return_pct": r250},
                        ]
                    },
                },
            }

        self.assertEqual(
            research_backtest.classify_refined_market_regime(make_result(6, 4, -18, -25)),
            "downtrend_repair",
        )
        self.assertEqual(
            research_backtest.classify_refined_market_regime(make_result(-6, -12, -18, -25)),
            "bear_continuation",
        )
        self.assertEqual(
            research_backtest.classify_refined_market_regime(make_result(3, 12, 18, 25, regime="trend")),
            "trend_extension",
        )
        self.assertEqual(
            research_backtest.classify_refined_market_regime(
                make_result(1, 2, -2, 3, regime="range", boll_position="中轨下方", rsi6=42, kdj_j=18, macd_bar=0.1)
            ),
            "range_rebound",
        )

    def test_research_backtest_adds_refined_regime_to_factor_tags_and_summary(self):
        outcome = {
            "horizon": "medium_term",
            "window_days": 20,
            "signal_score": 35,
            "signal_label": "买入偏向",
            "return_pct": 4.0,
            "max_drawdown_pct": -2.0,
            "hit": True,
            "factors": {"refined_regime": "downtrend_repair"},
        }

        summary = research_backtest.summarize_outcomes([outcome])
        report = research_backtest.render_markdown_report(summary, metadata={})

        refined_stats = summary["by_refined_regime_horizon"][("downtrend_repair", "medium_term")]
        self.assertEqual(refined_stats["sample_count"], 1)
        self.assertEqual(refined_stats["hit_rate_pct"], 100.0)
        self.assertIn("细分市场状态观察", report)
        self.assertIn("下跌修复 `downtrend_repair`", report)

    def test_research_backtest_classifies_market_regimes_from_visible_index_series(self):
        rows = []
        start = dt.date(2025, 1, 1)
        for index in range(360):
            if index < 260:
                close = 120 - index * 0.25
            else:
                close = 55 + (index - 260) * 0.1
            rows.append(
                {
                    "日期": (start + dt.timedelta(days=index)).isoformat(),
                    "收盘": close,
                    "最高": close + 0.8,
                    "最低": close - 0.8,
                    "成交量": 1_000_000 + index * 100,
                }
            )
        series = sfa.calculate_technical_series(rows)
        factors = research_backtest.market_factor_tags_from_visible_series(series, "sh000001")

        self.assertEqual(factors["benchmark_index"], "sh000001")
        self.assertEqual(factors["market_regime"], "market_bear_rebound")
        self.assertEqual(factors["market_trend_250d"], "下跌")
        self.assertIn(factors["market_decline_duration"], {"短期修复中期仍弱", "混合", "短中期非弱"})
        self.assertIn(factors["market_decline_speed"], {"短期修复", "非下跌", "跌速放缓"})
        self.assertIn(factors["market_tail_extreme"], {"弱势低位", "常规", "极端超卖"})
        self.assertIn(
            factors["market_tail_repair_signal"],
            {"低位放量转强", "低位修复确认", "低位放量未确认", "低位空头延续", "低位待确认", "常规"},
        )
        self.assertIn(factors["market_volume_state"], {"放量", "常规", "缩量"})
        self.assertIn("market_repair_speed_profile", factors)
        self.assertIn(
            factors["market_repair_speed_profile"],
            {"速度共振明显", "速度共振偏强", "速度温和共振", "速度分化", "速度未形成", "未知"},
        )
        self.assertIn("market_repair_quality_confirmation", factors)
        self.assertIn(
            factors["market_repair_quality_confirmation"],
            {"修复质量确认", "修复质量初步确认", "修复质量未确认", "修复质量恶化", "修复质量分化", "未知"},
        )

    def test_research_backtest_market_visible_series_respects_signal_date(self):
        series = sfa.calculate_technical_series(self.make_research_rows(40))
        dates = research_backtest.parsed_series_dates(series)

        visible = research_backtest.visible_series_as_of(series, dates, "2025-01-10")

        self.assertEqual(visible[-1]["date"], "2025-01-10")
        self.assertLess(len(visible), len(series))

    def test_research_backtest_summarizes_market_regime_by_signal_side(self):
        outcomes = []
        for _ in range(30):
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": -35,
                    "signal_label": "卖出偏向",
                    "return_pct": 18.0,
                    "max_drawdown_pct": -5.0,
                    "hit": False,
                    "factors": {"market_regime": "market_bear_rebound"},
                }
            )

        summary = research_backtest.summarize_outcomes(outcomes)
        report = research_backtest.render_markdown_report(summary, metadata={"benchmark_index": "sh000001"})

        market_stats = summary["by_market_regime_horizon"][("market_bear_rebound", "long_term")]
        side_key = ("sell_avoid", "market_bear_rebound", "long_term", 120)
        self.assertEqual(market_stats["sample_count"], 30)
        self.assertEqual(summary["by_signal_side_market_regime_horizon_window"][side_key]["hit_rate_pct"], 0.0)
        self.assertIn("市场基准状态观察", report)
        self.assertIn("市场状态买卖方向拆分", report)
        self.assertIn("市场熊尾修复 `market_bear_rebound`", report)

    def test_research_backtest_adds_market_refined_cross_factor(self):
        series = sfa.calculate_technical_series(self.make_research_rows())
        signal_index = 249
        result = {
            "code": "000001",
            "name": "平安银行",
            "regime": "downtrend",
            "horizon_scores": {
                "short_term": {"score": -20, "signal": "卖出偏向"},
                "medium_term": {"score": -25, "signal": "卖出偏向"},
                "long_term": {"score": -35, "signal": "卖出偏向"},
            },
            "raw": {
                "technical": {},
                "technical_trend": {
                    "windows": [
                        {"days": 20, "return_pct": -6},
                        {"days": 60, "return_pct": -12},
                        {"days": 120, "return_pct": -18},
                        {"days": 250, "return_pct": -25},
                    ]
                },
            },
        }

        outcomes = research_backtest.evaluate_result_windows(
            result,
            series,
            signal_index,
            extra_factors={"market_regime": "market_bear_continuation"},
        )
        summary = research_backtest.summarize_outcomes(outcomes * 5)
        report = research_backtest.render_markdown_report(summary, metadata={"benchmark_index": "sh000001"})

        factor = outcomes[0]["factors"]["market_refined_regime"]
        self.assertEqual(factor, "market_bear_continuation|bear_continuation")
        self.assertIn("市场与个股交叉状态归因", report)
        self.assertIn("市场弱势延续 `market_bear_continuation`", report)

    def test_research_backtest_summarizes_outcomes_and_renders_chinese_report(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "regime": "trend",
                "horizon": "short_term",
                "window_days": 5,
                "signal_score": 72,
                "signal_label": "强买",
                "return_pct": 2.0,
                "max_drawdown_pct": -1.0,
                "max_runup_pct": 3.0,
                "hit": True,
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "regime": "trend",
                "horizon": "short_term",
                "window_days": 5,
                "signal_score": 80,
                "signal_label": "强买",
                "return_pct": -2.0,
                "max_drawdown_pct": -3.0,
                "max_runup_pct": 1.0,
                "hit": False,
            },
            {
                "stock_code": "000003",
                "stock_name": "测试",
                "regime": "range",
                "horizon": "medium_term",
                "window_days": 20,
                "signal_score": 5,
                "signal_label": "观望",
                "return_pct": 1.0,
                "max_drawdown_pct": -0.5,
                "max_runup_pct": 1.5,
                "hit": None,
            },
        ]

        summary = research_backtest.summarize_outcomes(outcomes)
        report = research_backtest.render_markdown_report(
            summary,
            metadata={
                "from_date": "2025-06-19",
                "to_date": "2026-06-19",
                "validation_from": "2026-03-01",
                "stock_count": 110,
                "signal_count": 3,
                "errors": [],
                "simulations": [
                    {
                        "rule": {
                            "id": "test-risk",
                            "factor_name": "macd_state",
                            "factor_value": "多头",
                            "horizon": "short_term",
                            "window_days": 5,
                            "score_bias": -20,
                        },
                        "train": {
                            "matched_count": 10,
                            "baseline_hit_rate_pct": 40.0,
                            "adjusted_hit_rate_pct": 55.0,
                            "hit_rate_delta_pct": 15.0,
                        },
                        "validation": {
                            "matched_count": 8,
                            "baseline_hit_rate_pct": 38.0,
                            "adjusted_hit_rate_pct": 50.0,
                            "hit_rate_delta_pct": 12.0,
                        },
                    }
                ],
            },
        )

        short_summary = summary["by_horizon_window"][("short_term", 5)]
        self.assertEqual(short_summary["sample_count"], 2)
        self.assertEqual(short_summary["directional_count"], 2)
        self.assertEqual(short_summary["high_intensity_count"], 2)
        self.assertEqual(short_summary["hit_rate_pct"], 50.0)
        self.assertEqual(short_summary["avg_return_pct"], 0.0)
        self.assertIn("股票信号历史回测研究报告", report)
        self.assertIn("不自动修改 active 评分规则", report)
        self.assertIn("短期 5日", report)
        self.assertIn("核心发现", report)
        self.assertIn("初步分析理论", report)
        self.assertIn("训练/验证对照", report)
        self.assertIn("因子归因复盘", report)
        self.assertIn("候选优化规则", report)
        self.assertIn("候选规则模拟对比", report)
        self.assertIn("test-risk", report)
        self.assertIn("稳定候选筛选", report)

    def test_research_backtest_summarizes_train_validation_and_factors(self):
        outcomes = [
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2025-07-01",
                "signal_score": 35,
                "signal_label": "买入偏向",
                "return_pct": 1.0,
                "max_drawdown_pct": -0.4,
                "max_runup_pct": 1.8,
                "hit": True,
                "factors": {"macd_state": "多头", "regime": "trend"},
            },
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2026-03-01",
                "signal_score": 30,
                "signal_label": "买入偏向",
                "return_pct": -2.0,
                "max_drawdown_pct": -2.5,
                "max_runup_pct": 0.3,
                "hit": False,
                "factors": {"macd_state": "多头", "regime": "trend"},
            },
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2026-03-02",
                "signal_score": -30,
                "signal_label": "卖出偏向",
                "return_pct": -1.0,
                "max_drawdown_pct": -1.4,
                "max_runup_pct": 0.2,
                "hit": True,
                "factors": {"macd_state": "空头", "regime": "downtrend"},
            },
        ]

        summary = research_backtest.summarize_outcomes(outcomes, validation_from=dt.date(2026, 3, 1))

        train_short = summary["by_period_horizon_window"][("train", "short_term", 5)]
        validation_short = summary["by_period_horizon_window"][("validation", "short_term", 5)]
        macd_bull = summary["by_factor"][("macd_state", "多头", "short_term", 5)]
        self.assertEqual(train_short["sample_count"], 1)
        self.assertEqual(validation_short["sample_count"], 2)
        self.assertEqual(macd_bull["sample_count"], 2)
        self.assertEqual(macd_bull["hit_rate_pct"], 50.0)
        self.assertEqual(macd_bull["avg_return_pct"], -0.5)

    def test_research_backtest_splits_buy_and_sell_direction_stats(self):
        outcomes = [
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-07-01",
                "signal_score": 55,
                "signal_label": "强买",
                "return_pct": 8.0,
                "max_drawdown_pct": -3.0,
                "max_runup_pct": 10.0,
                "hit": True,
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-07-02",
                "signal_score": 35,
                "signal_label": "买入偏向",
                "return_pct": -4.0,
                "max_drawdown_pct": -6.0,
                "max_runup_pct": 1.0,
                "hit": False,
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-07-03",
                "signal_score": -40,
                "signal_label": "卖出偏向",
                "return_pct": -5.0,
                "max_drawdown_pct": -7.0,
                "max_runup_pct": 0.5,
                "hit": True,
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-07-04",
                "signal_score": -60,
                "signal_label": "强卖/回避",
                "return_pct": 3.0,
                "max_drawdown_pct": -1.0,
                "max_runup_pct": 5.0,
                "hit": False,
            },
        ]

        summary = research_backtest.summarize_outcomes(outcomes)
        report = research_backtest.render_markdown_report(summary, metadata={})

        buy_stats = summary["by_signal_side_horizon_window"][("buy_bias", "long_term", 60)]
        sell_stats = summary["by_signal_side_horizon_window"][("sell_avoid", "long_term", 60)]
        self.assertEqual(buy_stats["directional_count"], 2)
        self.assertEqual(buy_stats["hit_rate_pct"], 50.0)
        self.assertEqual(buy_stats["avg_return_pct"], 2.0)
        self.assertEqual(sell_stats["directional_count"], 2)
        self.assertEqual(sell_stats["hit_rate_pct"], 50.0)
        self.assertEqual(sell_stats["avg_return_pct"], -1.0)
        self.assertIn("买卖方向拆分", report)
        self.assertIn("买入方向", report)
        self.assertIn("卖出/回避方向", report)

    def test_research_backtest_splits_refined_regime_stats_by_signal_side(self):
        outcomes = []
        for _ in range(30):
            outcomes.append(
                {
                    "horizon": "medium_term",
                    "window_days": 20,
                    "signal_score": 35,
                    "signal_label": "买入偏向",
                    "return_pct": 6.0,
                    "max_drawdown_pct": -2.0,
                    "hit": True,
                    "factors": {"refined_regime": "downtrend_repair"},
                }
            )
            outcomes.append(
                {
                    "horizon": "medium_term",
                    "window_days": 20,
                    "signal_score": -35,
                    "signal_label": "卖出偏向",
                    "return_pct": 4.0,
                    "max_drawdown_pct": -1.0,
                    "hit": False,
                    "factors": {"refined_regime": "downtrend_repair"},
                }
            )

        summary = research_backtest.summarize_outcomes(outcomes)
        report = research_backtest.render_markdown_report(summary, metadata={})

        buy_key = ("buy_bias", "downtrend_repair", "medium_term", 20)
        sell_key = ("sell_avoid", "downtrend_repair", "medium_term", 20)
        self.assertEqual(summary["by_signal_side_refined_regime_horizon_window"][buy_key]["hit_rate_pct"], 100.0)
        self.assertEqual(summary["by_signal_side_refined_regime_horizon_window"][sell_key]["hit_rate_pct"], 0.0)
        self.assertIn("细分状态买卖方向拆分", report)
        self.assertIn("下跌修复 `downtrend_repair`", report)

    def test_research_backtest_splits_factor_stats_by_signal_side(self):
        outcomes = []
        for _ in range(5):
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": 55,
                    "signal_label": "强买",
                    "return_pct": 12.0,
                    "max_drawdown_pct": -4.0,
                    "max_runup_pct": 18.0,
                    "hit": True,
                    "factors": {"trend_120d": "上涨"},
                }
            )
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": 35,
                    "signal_label": "买入偏向",
                    "return_pct": -2.0,
                    "max_drawdown_pct": -6.0,
                    "max_runup_pct": 3.0,
                    "hit": False,
                    "factors": {"trend_120d": "上涨"},
                }
            )
        for _ in range(10):
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": -45,
                    "signal_label": "卖出偏向",
                    "return_pct": -8.0,
                    "max_drawdown_pct": -10.0,
                    "max_runup_pct": 1.0,
                    "hit": True,
                    "factors": {"trend_120d": "下跌"},
                }
            )

        summary = research_backtest.summarize_outcomes(outcomes)
        report = research_backtest.render_markdown_report(summary, metadata={})

        buy_factor = summary["by_signal_side_factor"][("buy_bias", "trend_120d", "上涨", "long_term", 120)]
        sell_factor = summary["by_signal_side_factor"][("sell_avoid", "trend_120d", "下跌", "long_term", 120)]
        self.assertEqual(buy_factor["sample_count"], 10)
        self.assertEqual(buy_factor["hit_rate_pct"], 50.0)
        self.assertEqual(buy_factor["avg_return_pct"], 5.0)
        self.assertEqual(sell_factor["sample_count"], 10)
        self.assertEqual(sell_factor["hit_rate_pct"], 100.0)
        self.assertEqual(sell_factor["avg_return_pct"], -8.0)
        self.assertIn("买卖方向因子归因", report)
        self.assertIn("trend_120d", report)

    def test_research_backtest_simulates_candidate_rule_score_bias(self):
        outcomes = [
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2025-07-01",
                "signal_score": 20,
                "signal_label": "买入偏向",
                "return_pct": -1.0,
                "max_drawdown_pct": -1.6,
                "max_runup_pct": 0.2,
                "hit": False,
                "factors": {"macd_state": "多头"},
            },
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2026-03-01",
                "signal_score": 22,
                "signal_label": "买入偏向",
                "return_pct": -2.0,
                "max_drawdown_pct": -2.4,
                "max_runup_pct": 0.1,
                "hit": False,
                "factors": {"macd_state": "多头"},
            },
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2026-03-02",
                "signal_score": 25,
                "signal_label": "买入偏向",
                "return_pct": 1.5,
                "max_drawdown_pct": -0.5,
                "max_runup_pct": 2.0,
                "hit": True,
                "factors": {"macd_state": "空头"},
            },
        ]
        rules = [
            {
                "id": "macd-bull-risk-test",
                "factor_name": "macd_state",
                "factor_value": "多头",
                "horizon": "short_term",
                "window_days": 5,
                "score_bias": -45,
                "kind": "risk_constraint",
            }
        ]

        simulations = research_backtest.simulate_candidate_rules(
            outcomes,
            rules,
            validation_from=dt.date(2026, 3, 1),
        )

        simulation = simulations[0]
        self.assertEqual(simulation["train"]["matched_count"], 1)
        self.assertEqual(simulation["train"]["baseline_hit_rate_pct"], 0.0)
        self.assertEqual(simulation["train"]["adjusted_hit_rate_pct"], 100.0)
        self.assertEqual(simulation["validation"]["matched_count"], 1)
        self.assertEqual(simulation["validation"]["adjusted_hit_rate_pct"], 100.0)

    def test_research_backtest_candidate_simulation_reports_directional_coverage_and_returns(self):
        outcomes = [
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2025-07-01",
                "signal_score": 15,
                "signal_label": "买入偏向",
                "return_pct": -4.0,
                "max_drawdown_pct": -5.0,
                "max_runup_pct": 1.0,
                "hit": False,
                "factors": {"rsi6_zone": "超卖"},
            },
            {
                "horizon": "short_term",
                "window_days": 5,
                "signal_trade_date": "2025-07-02",
                "signal_score": 25,
                "signal_label": "买入偏向",
                "return_pct": 6.0,
                "max_drawdown_pct": -1.0,
                "max_runup_pct": 7.0,
                "hit": True,
                "factors": {"rsi6_zone": "超卖"},
            },
        ]
        rules = [
            {
                "id": "reduce-borderline-buy",
                "signal_side": "buy_bias",
                "factor_name": "rsi6_zone",
                "factor_value": "超卖",
                "horizon": "short_term",
                "window_days": 5,
                "score_bias": -5,
                "kind": "downweight",
            }
        ]

        simulations = research_backtest.simulate_candidate_rules(outcomes, rules, validation_from=None)
        comparison = simulations[0]["all"]

        self.assertEqual(comparison["baseline_directional_count"], 2)
        self.assertEqual(comparison["adjusted_directional_count"], 1)
        self.assertEqual(comparison["directional_count_delta"], -1)
        self.assertEqual(comparison["baseline_directional_avg_return_pct"], 1.0)
        self.assertEqual(comparison["adjusted_directional_avg_return_pct"], 6.0)
        self.assertEqual(comparison["directional_avg_return_delta_pct"], 5.0)
        self.assertEqual(comparison["baseline_directional_avg_drawdown_pct"], -3.0)
        self.assertEqual(comparison["adjusted_directional_avg_drawdown_pct"], -1.0)
        self.assertEqual(comparison["directional_avg_drawdown_delta_pct"], 2.0)

    def test_research_backtest_candidate_rule_can_neutralize_sell_signal_to_watch(self):
        outcome = {
            "horizon": "long_term",
            "window_days": 120,
            "signal_score": -82,
            "signal_label": "强卖/回避",
            "return_pct": 18.0,
            "hit": False,
            "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
        }
        rule = {
            "id": "neutralize-bear-tail-sell",
            "signal_side": "sell_avoid",
            "factor_name": "market_refined_regime",
            "factor_value": "market_bear_continuation|bear_continuation",
            "horizon": "long_term",
            "window_days": 120,
            "score_bias": 5,
            "score_adjustment_mode": "neutralize_to_watch",
        }

        adjusted = research_backtest.adjusted_outcome_for_rule(outcome, rule)

        self.assertEqual(adjusted["signal_score"], -14)
        self.assertEqual(adjusted["signal_label"], "观望")
        self.assertIsNone(adjusted["hit"])
        self.assertEqual(adjusted["simulation_rule_id"], "neutralize-bear-tail-sell")

    def test_research_backtest_candidate_simulation_reports_neutralized_wrong_directional_samples(self):
        outcomes = [
            {
                "horizon": "long_term",
                "window_days": 120,
                "signal_trade_date": "2025-08-01",
                "signal_score": -82,
                "signal_label": "强卖/回避",
                "return_pct": 18.0,
                "max_drawdown_pct": -2.0,
                "max_runup_pct": 22.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "long_term",
                "window_days": 120,
                "signal_trade_date": "2025-08-02",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": -6.0,
                "max_drawdown_pct": -12.0,
                "max_runup_pct": 1.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
        ]
        rules = [
            {
                "id": "neutralize-bear-tail-sell",
                "signal_side": "sell_avoid",
                "factor_name": "market_refined_regime",
                "factor_value": "market_bear_continuation|bear_continuation",
                "horizon": "long_term",
                "window_days": 120,
                "score_bias": 5,
                "score_adjustment_mode": "neutralize_to_watch",
            }
        ]

        simulations = research_backtest.simulate_candidate_rules(outcomes, rules, validation_from=None)
        comparison = simulations[0]["all"]

        self.assertEqual(comparison["baseline_directional_count"], 2)
        self.assertEqual(comparison["adjusted_directional_count"], 0)
        self.assertEqual(comparison["directional_count_delta"], -2)
        self.assertEqual(comparison["baseline_wrong_directional_count"], 1)
        self.assertEqual(comparison["adjusted_wrong_directional_count"], 0)
        self.assertEqual(comparison["wrong_directional_count_delta"], -1)
        self.assertEqual(comparison["neutralized_directional_count"], 2)
        self.assertEqual(comparison["neutralized_wrong_directional_count"], 1)
        self.assertEqual(comparison["neutralized_wrong_directional_rate_pct"], 50.0)
        self.assertEqual(comparison["neutralized_wrong_directional_avg_return_pct"], 18.0)

    def test_research_backtest_summarizes_candidate_rule_baskets(self):
        outcomes = [
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-01",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": 2.0,
                "max_drawdown_pct": -1.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-01",
                "signal_score": -40,
                "signal_label": "卖出偏向",
                "return_pct": 4.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-02",
                "signal_score": -30,
                "signal_label": "卖出偏向",
                "return_pct": -2.0,
                "max_drawdown_pct": -4.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-03",
                "signal_score": -45,
                "signal_label": "卖出偏向",
                "return_pct": 6.0,
                "max_drawdown_pct": -2.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-03",
                "signal_score": -42,
                "signal_label": "卖出偏向",
                "return_pct": -2.0,
                "max_drawdown_pct": -2.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
        ]
        rules = [
            {
                "id": "basket-rule",
                "signal_side": "sell_avoid",
                "factor_name": "market_refined_regime",
                "factor_value": "market_bear_continuation|bear_continuation",
                "horizon": "medium_term",
                "window_days": 20,
                "score_adjustment_mode": "neutralize_to_watch",
            }
        ]

        simulations = research_backtest.simulate_candidate_rules(
            outcomes,
            rules,
            validation_from=dt.date(2025, 1, 3),
        )

        simulation = simulations[0]
        self.assertEqual(simulation["basket_train"]["basket_count"], 2)
        self.assertEqual(simulation["basket_train"]["stock_signal_count"], 3)
        self.assertEqual(simulation["basket_train"]["avg_basket_return_pct"], 0.5)
        self.assertEqual(simulation["basket_validation"]["basket_count"], 1)
        self.assertEqual(simulation["basket_validation"]["stock_signal_count"], 2)
        self.assertEqual(simulation["basket_validation"]["avg_basket_return_pct"], 2.0)
        self.assertEqual(simulation["basket_all"]["basket_count"], 3)
        self.assertAlmostEqual(simulation["basket_all"]["avg_basket_size"], 5 / 3)
        self.assertEqual(simulation["basket_all"]["positive_basket_rate_pct"], 2 / 3 * 100)
        self.assertEqual(simulation["basket_all"]["worst_basket_date"], "2025-01-02")
        self.assertEqual(simulation["basket_all"]["worst_basket_return_pct"], -2.0)
        self.assertEqual(simulation["basket_all"]["worst_basket_size"], 1)

    def test_research_backtest_renders_candidate_basket_section(self):
        simulations = [
            {
                "rule": {"id": "basket-rule", "score_adjustment_mode": "neutralize_to_watch"},
                "train": {},
                "validation": {},
                "all": {},
                "basket_train": {
                    "basket_count": 0,
                    "stock_signal_count": 0,
                },
                "basket_validation": {
                    "basket_count": 1,
                    "stock_signal_count": 2,
                    "avg_basket_size": 2.0,
                    "avg_basket_return_pct": 2.0,
                    "positive_basket_rate_pct": 100.0,
                    "avg_basket_drawdown_pct": -2.0,
                    "worst_basket_date": "2025-01-03",
                    "worst_basket_return_pct": 2.0,
                },
                "basket_all": {
                    "basket_count": 1,
                    "stock_signal_count": 2,
                    "avg_basket_size": 2.0,
                    "avg_basket_return_pct": 2.0,
                    "positive_basket_rate_pct": 100.0,
                    "avg_basket_drawdown_pct": -2.0,
                    "worst_basket_date": "2025-01-03",
                    "worst_basket_return_pct": 2.0,
                },
            }
        ]

        report = research_backtest.render_markdown_report({}, metadata={"simulations": simulations})

        self.assertIn("## 候选规则组合级验证", report)
        self.assertIn("| `basket-rule` | 验证段 | 1 | 2 | 2.00 | 2.00% | 100.00% | -2.00% | 2025-01-03 | 2.00% |", report)

    def test_research_review_layer_labels_stable_weak_tail_lag(self):
        outcome = {
            "horizon": "long_term",
            "window_days": 60,
            "signal_score": -42,
            "signal_label": "卖出偏向",
            "return_pct": 12.0,
            "hit": False,
            "factors": {
                "horizon_stage_category": "60日滞后优先复核",
                "horizon_stage_reason": "市场跌速加快+低位修复确认",
            },
        }

        review = research_backtest.research_review_layer_label(outcome)
        adjusted = research_backtest.adjusted_outcome_for_review_layer(outcome)

        self.assertEqual(review["label"], "weak_tail_60d_lag_priority")
        self.assertEqual(review["action"], "downgrade_to_watch_review")
        self.assertEqual(adjusted["signal_score"], -14)
        self.assertEqual(adjusted["signal_label"], "观望")
        self.assertNotIn("买", adjusted["signal_label"])

    def test_research_review_layer_replay_compares_original_and_review_logic(self):
        outcomes = [
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-02",
                "signal_score": -42,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {
                    "horizon_stage_category": "60日滞后优先复核",
                    "horizon_stage_reason": "市场修复质量未确认",
                },
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-02-02",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": -8.0,
                "max_drawdown_pct": -10.0,
                "hit": True,
                "factors": {
                    "horizon_stage_category": "60日滞后优先复核",
                    "horizon_stage_reason": "市场低位待确认",
                },
            },
        ]

        rows = research_backtest.review_layer_replay_rows(outcomes, validation_from=dt.date(2025, 2, 1))
        all_row = next(row for row in rows if row["period"] == "all")

        self.assertEqual(all_row["label"], "weak_tail_60d_lag_priority")
        self.assertEqual(all_row["neutralized_directional_count"], 2)
        self.assertEqual(all_row["neutralized_wrong_directional_count"], 1)
        self.assertEqual(all_row["wrong_directional_count_delta"], -1)

    def test_research_review_layer_reports_six_optimization_sections(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-02",
                "signal_score": -42,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {
                    "horizon_stage_category": "60日滞后优先复核",
                    "horizon_stage_reason": "市场修复质量未确认",
                },
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-02",
                "signal_score": 36,
                "signal_label": "买入偏向",
                "return_pct": 5.0,
                "max_drawdown_pct": -2.0,
                "hit": True,
                "factors": {},
            },
        ]
        metadata = {
            "from_date": "2024-01-01",
            "to_date": "2025-01-01",
            "validation_from": "2024-07-01",
            "stock_count": 110,
            "signal_count": 2,
            "codes_file": "stock.md",
            "outcomes": outcomes,
            "simulations": [],
        }

        report = research_backtest.render_markdown_report({}, metadata=metadata)

        self.assertIn("## 研究复核层新旧对照回放", report)
        self.assertIn("## 历史基本面覆盖度与缺口", report)
        self.assertIn("## 研究复核层组合级验证", report)
        self.assertIn("## 股票池扩展与泛化验证", report)
        self.assertIn("## 研究复核层失败案例库", report)
        self.assertIn("不写入 active 调分", report)

    def test_research_review_layer_failure_case_library_keeps_counterexamples(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-02",
                "signal_score": -42,
                "signal_label": "卖出偏向",
                "return_pct": -9.0,
                "max_drawdown_pct": -12.0,
                "hit": True,
                "factors": {
                    "horizon_stage_category": "60日滞后优先复核",
                    "horizon_stage_reason": "市场低位待确认",
                },
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-02-02",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": 15.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {},
            },
        ]

        rows = research_backtest.review_layer_failure_case_rows(outcomes)

        self.assertEqual(rows[0]["failure_type"], "降级风险：原卖出/回避有效")
        self.assertEqual(rows[1]["failure_type"], "漏判风险：未识别卖出滞后")

    def test_research_backtest_summarizes_candidate_rule_horizon_profile(self):
        outcomes = [
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-01",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": 4.0,
                "max_drawdown_pct": -2.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-01",
                "signal_score": -42,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "long_term",
                "window_days": 120,
                "signal_trade_date": "2025-01-03",
                "signal_score": -45,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "max_drawdown_pct": -5.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-03",
                "signal_score": 45,
                "signal_label": "买入偏向",
                "return_pct": 9.0,
                "max_drawdown_pct": -1.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-03",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": -3.0,
                "max_drawdown_pct": -6.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_range|bear_continuation"},
            },
        ]
        rules = [
            {
                "id": "horizon-profile-rule",
                "signal_side": "sell_avoid",
                "factor_name": "market_refined_regime",
                "factor_value": "market_bear_continuation|bear_continuation",
                "horizon": "medium_term",
                "window_days": 20,
                "score_adjustment_mode": "neutralize_to_watch",
            }
        ]

        simulations = research_backtest.simulate_candidate_rules(
            outcomes,
            rules,
            validation_from=dt.date(2025, 1, 3),
        )

        profile = {
            (row["period"], row["horizon"], row["window_days"]): row
            for row in simulations[0]["horizon_profile"]
        }
        self.assertEqual(profile[("train", "medium_term", 20)]["sample_count"], 1)
        self.assertEqual(profile[("train", "medium_term", 20)]["avg_return_pct"], 4.0)
        self.assertEqual(profile[("train", "long_term", 60)]["sample_count"], 1)
        self.assertEqual(profile[("train", "long_term", 60)]["avg_return_pct"], 12.0)
        self.assertEqual(profile[("validation", "long_term", 120)]["sample_count"], 1)
        self.assertEqual(profile[("validation", "long_term", 120)]["basket_count"], 1)
        self.assertNotIn(("validation", "long_term", 60), profile)

    def test_research_backtest_renders_candidate_horizon_profile_section(self):
        simulations = [
            {
                "rule": {"id": "horizon-profile-rule"},
                "horizon_profile": [
                    {
                        "period": "validation",
                        "horizon": "long_term",
                        "window_days": 60,
                        "sample_count": 2,
                        "directional_count": 2,
                        "hit_rate_pct": 0.0,
                        "avg_return_pct": 12.0,
                        "avg_max_drawdown_pct": -3.0,
                        "basket_count": 1,
                        "avg_basket_return_pct": 12.0,
                        "positive_basket_rate_pct": 100.0,
                        "worst_basket_return_pct": 12.0,
                    }
                ],
            }
        ]

        report = research_backtest.render_markdown_report({}, metadata={"simulations": simulations})

        self.assertIn("## 候选规则跨持有期画像", report)
        self.assertIn(
            "| `horizon-profile-rule` | 验证段 | 长期 60日 | 2 | 2 | 0.00% | 12.00% | -3.00% | 1 | 12.00% | 100.00% | 12.00% |",
            report,
        )

    def test_research_backtest_renders_continuous_speed_horizon_selector_section(self):
        horizon_profile = [
            {
                "period": "train",
                "horizon": "medium_term",
                "window_days": 20,
                "sample_count": 120,
                "avg_return_pct": 4.0,
                "basket_count": 5,
            },
            {
                "period": "train",
                "horizon": "long_term",
                "window_days": 60,
                "sample_count": 120,
                "avg_return_pct": 12.0,
                "basket_count": 5,
            },
            {
                "period": "train",
                "horizon": "long_term",
                "window_days": 120,
                "sample_count": 120,
                "avg_return_pct": 5.0,
                "basket_count": 5,
            },
            {
                "period": "validation",
                "horizon": "medium_term",
                "window_days": 20,
                "sample_count": 80,
                "avg_return_pct": 7.0,
                "basket_count": 4,
            },
            {
                "period": "validation",
                "horizon": "long_term",
                "window_days": 60,
                "sample_count": 80,
                "avg_return_pct": 15.0,
                "basket_count": 4,
            },
            {
                "period": "validation",
                "horizon": "long_term",
                "window_days": 120,
                "sample_count": 80,
                "avg_return_pct": 6.0,
                "basket_count": 4,
            },
        ]
        simulations = [
            {
                "rule": {"id": "continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20"},
                "horizon_profile": horizon_profile,
            },
            {
                "rule": {"id": "continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60"},
                "horizon_profile": horizon_profile,
            },
        ]

        report = research_backtest.render_markdown_report({}, metadata={"simulations": simulations})

        self.assertIn("## 连续速度持有期选择观察", report)
        self.assertEqual(report.count("| `stock-speed-profile` |"), 1)
        self.assertIn("| `stock-speed-profile` | 120 / 4.00% / 5篮 | 120 / 12.00% / 5篮 |", report)
        self.assertIn("60日更稳", report)

    def test_research_backtest_summarizes_continuous_speed_counterexample_factors(self):
        outcomes = [
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-02",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": -4.0,
                "max_drawdown_pct": -8.0,
                "hit": True,
                "factors": {
                    "repair_speed_profile": "速度共振偏强",
                    "volume_expansion_speed": "速度未改善",
                },
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-01-03",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -2.0,
                "hit": False,
                "factors": {
                    "repair_speed_profile": "速度共振偏强",
                    "volume_expansion_speed": "速度改善明显",
                },
            },
            {
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2025-02-03",
                "signal_score": -35,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {
                    "repair_speed_profile": "速度共振偏强",
                    "volume_expansion_speed": "速度改善明显",
                },
            },
        ]
        rule = {
            "id": "continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60",
            "signal_side": "sell_avoid",
            "factor_scope": {"repair_speed_profile": ["速度共振偏强"]},
            "horizon": "long_term",
            "window_days": 60,
            "score_adjustment_mode": "neutralize_to_watch",
        }

        simulations = research_backtest.simulate_candidate_rules(
            outcomes,
            [rule],
            validation_from=dt.date(2025, 2, 1),
        )
        rows = simulations[0]["counterexample_factor_rows"]
        train_profile = next(
            row
            for row in rows
            if row["period"] == "train"
            and row["factor_name"] == "repair_speed_profile"
            and row["factor_value"] == "速度共振偏强"
        )

        self.assertEqual(train_profile["sample_count"], 2)
        self.assertEqual(train_profile["correct_count"], 1)
        self.assertEqual(train_profile["wrong_count"], 1)
        self.assertEqual(train_profile["correct_rate_pct"], 50.0)
        self.assertEqual(train_profile["correct_avg_return_pct"], -4.0)
        self.assertEqual(train_profile["wrong_avg_return_pct"], 12.0)

    def test_research_backtest_renders_counterexample_factor_diagnostic_section(self):
        simulations = [
            {
                "rule": {"id": "continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60"},
                "counterexample_factor_rows": [
                    {
                        "period": "validation",
                        "factor_name": "volume_expansion_speed",
                        "factor_value": "速度未改善",
                        "sample_count": 6,
                        "correct_count": 4,
                        "wrong_count": 2,
                        "correct_rate_pct": 66.6667,
                        "correct_avg_return_pct": -5.0,
                        "wrong_avg_return_pct": 8.0,
                        "avg_drawdown_pct": -7.0,
                    }
                ],
            }
        ]

        report = research_backtest.render_markdown_report({}, metadata={"simulations": simulations})

        self.assertIn("## 连续速度反例因子诊断", report)
        self.assertIn("有效风控", report)
        self.assertIn(
            "| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 验证段 | volume_expansion_speed | 速度未改善 | 6 | 4 | 2 | 66.67% | -5.00% | 8.00% | -7.00% |",
            report,
        )

    def test_research_backtest_summarizes_neutralize_confidence_rows(self):
        simulations = [
            {
                "rule": {
                    "id": "repair_quality_defense_pocket:market-quality:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 220,
                    "neutralized_wrong_directional_rate_pct": 76.0,
                },
                "validation": {
                    "matched_count": 180,
                    "neutralized_wrong_directional_rate_pct": 82.0,
                },
                "basket_validation": {
                    "basket_count": 12,
                    "avg_basket_return_pct": 11.5,
                },
            },
            {
                "rule": {
                    "id": "repair_quality_defense_pocket:thin:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 20,
                    "neutralized_wrong_directional_rate_pct": 64.0,
                },
                "validation": {
                    "matched_count": 12,
                    "neutralized_wrong_directional_rate_pct": 90.0,
                },
                "basket_validation": {
                    "basket_count": 2,
                    "avg_basket_return_pct": 8.0,
                },
            },
        ]

        rows = research_backtest.neutralize_confidence_rows(simulations)

        self.assertEqual(rows[0]["rule_id"], "repair_quality_defense_pocket:market-quality:sell_avoid:long_term:60")
        self.assertEqual(rows[0]["neutralize_confidence_pct"], 79.6)
        self.assertEqual(rows[0]["effective_risk_rate_pct"], 18.0)
        self.assertEqual(rows[0]["verdict"], "高确信降级观察")
        self.assertEqual(rows[1]["verdict"], "样本不足，仅作阶段线索")

    def test_research_backtest_renders_neutralize_confidence_section(self):
        simulations = [
            {
                "rule": {
                    "id": "repair_quality_defense_pocket:market-quality:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 220,
                    "neutralized_wrong_directional_rate_pct": 76.0,
                },
                "validation": {
                    "matched_count": 180,
                    "neutralized_wrong_directional_rate_pct": 82.0,
                },
                "basket_validation": {
                    "basket_count": 12,
                    "avg_basket_return_pct": 11.5,
                },
            }
        ]

        report = research_backtest.render_markdown_report({}, metadata={"simulations": simulations})

        self.assertIn("## 卖出/回避观察降级确信度", report)
        self.assertIn(
            "| `repair_quality_defense_pocket:market-quality:sell_avoid:long_term:60` | 长期 60日 | 220 | 180 | 12 | 76.00% | 82.00% | 18.00% | 79.60% | 11.50% | 高确信降级观察 |",
            report,
        )

    def test_research_backtest_summarizes_neutralize_signal_review_rows(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -32,
                "signal_label": "卖出偏向",
                "return_pct": -5.0,
                "max_drawdown_pct": -8.0,
                "hit": True,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        rows = research_backtest.neutralize_signal_review_rows(outcomes, simulations, limit=10)

        self.assertEqual(rows[0]["stock_code"], "000001")
        self.assertEqual(rows[0]["matched_rule_count"], 1)
        self.assertEqual(rows[0]["neutralize_confidence_pct"], 81.0)
        self.assertEqual(rows[0]["outcome_type"], "滞后误杀")
        self.assertEqual(rows[1]["outcome_type"], "有效风控")

    def test_research_backtest_summarizes_neutralize_signal_daily_rows(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -32,
                "signal_label": "卖出偏向",
                "return_pct": -5.0,
                "max_drawdown_pct": -8.0,
                "hit": True,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        rows = research_backtest.neutralize_signal_daily_summary_rows(outcomes, simulations)

        self.assertEqual(rows[0]["signal_trade_date"], "2022-09-01")
        self.assertEqual(rows[0]["signal_count"], 2)
        self.assertEqual(rows[0]["lagging_false_negative_count"], 1)
        self.assertEqual(rows[0]["effective_risk_count"], 1)
        self.assertEqual(rows[0]["lagging_false_negative_rate_pct"], 50.0)
        self.assertEqual(rows[0]["avg_return_pct"], 3.5)
        self.assertEqual(rows[0]["worst_return_pct"], -5.0)
        self.assertEqual(rows[0]["avg_drawdown_pct"], -6.0)
        self.assertEqual(rows[0]["avg_neutralize_confidence_pct"], 81.0)
        self.assertEqual(rows[0]["top_rule_count"], 2)

    def test_research_backtest_renders_neutralize_signal_daily_section(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            }
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes, "simulations": simulations},
        )

        self.assertIn("## 高确信观察降级交易日汇总", report)
        self.assertIn(
            "| 2022-09-01 | 长期 60日 | 1 | 1 | 0 | 100.00% | 12.00% | 12.00% | -4.00% | 81.00% | `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 1 |",
            report,
        )

    def test_research_backtest_summarizes_neutralize_signal_stage_blocks(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -32,
                "signal_label": "卖出偏向",
                "return_pct": -5.0,
                "max_drawdown_pct": -8.0,
                "hit": True,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
            {
                "stock_code": "000063",
                "stock_name": "中兴通讯",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-02",
                "signal_score": -40,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            },
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        rows = research_backtest.neutralize_signal_stage_block_rows(outcomes, simulations)
        monthly = next(row for row in rows if row["bucket_type"] == "月度" and row["period"] == "2022-09")
        quarterly = next(row for row in rows if row["bucket_type"] == "季度" and row["period"] == "2022-Q3")

        self.assertEqual(monthly["daily_basket_count"], 2)
        self.assertEqual(monthly["signal_count"], 3)
        self.assertEqual(monthly["lagging_false_negative_count"], 2)
        self.assertEqual(monthly["effective_risk_count"], 1)
        self.assertEqual(monthly["lagging_false_negative_rate_pct"], 66.67)
        self.assertEqual(monthly["avg_daily_basket_return_pct"], 5.75)
        self.assertEqual(monthly["worst_daily_basket_return_pct"], 3.5)
        self.assertEqual(monthly["worst_daily_basket_date"], "2022-09-01")
        self.assertEqual(monthly["effective_risk_dominant_day_share_pct"], 0.0)
        self.assertEqual(quarterly["signal_count"], 3)

    def test_research_backtest_renders_neutralize_signal_stage_block_section(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            }
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes, "simulations": simulations},
        )

        self.assertIn("## 高确信观察降级阶段块汇总", report)
        self.assertIn(
            "| 月度 | 2022-09 | 长期 60日 | 1 | 1 | 1 | 0 | 100.00% | 12.00% | 12.00% | 2022-09-01 | 81.00% | 0.00% |",
            report,
        )

    def test_research_backtest_summarizes_neutralize_signal_stage_factor_profile(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {
                    "repair_speed_profile": "速度共振明显",
                    "market_trend_20d": "下跌",
                    "repair_quality_sync": "市场确认个股不恶化",
                },
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -32,
                "signal_label": "卖出偏向",
                "return_pct": -5.0,
                "max_drawdown_pct": -8.0,
                "hit": True,
                "factors": {
                    "repair_speed_profile": "速度共振明显",
                    "market_trend_20d": "下跌",
                    "repair_quality_sync": "市场确认个股不恶化",
                },
            },
            {
                "stock_code": "000063",
                "stock_name": "中兴通讯",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-02",
                "signal_score": -40,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "max_drawdown_pct": -3.0,
                "hit": False,
                "factors": {
                    "repair_speed_profile": "速度共振明显",
                    "market_trend_20d": "下跌",
                    "repair_quality_sync": "双侧质量恶化",
                },
            },
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        rows = research_backtest.neutralize_signal_stage_factor_profile_rows(
            outcomes,
            simulations,
            factor_names=["market_trend_20d", "repair_quality_sync"],
        )
        monthly_market = next(
            row
            for row in rows
            if row["bucket_type"] == "月度"
            and row["period"] == "2022-09"
            and row["factor_name"] == "market_trend_20d"
        )
        monthly_sync = next(
            row
            for row in rows
            if row["bucket_type"] == "月度"
            and row["period"] == "2022-09"
            and row["factor_name"] == "repair_quality_sync"
        )

        self.assertEqual(monthly_market["factor_value"], "下跌")
        self.assertEqual(monthly_market["sample_count"], 3)
        self.assertEqual(monthly_market["stage_sample_share_pct"], 100.0)
        self.assertEqual(monthly_market["lagging_false_negative_count"], 2)
        self.assertEqual(monthly_market["lagging_false_negative_rate_pct"], 66.66666666666666)
        self.assertEqual(monthly_sync["factor_value"], "市场确认个股不恶化")
        self.assertEqual(monthly_sync["sample_count"], 2)
        self.assertEqual(monthly_sync["stage_sample_share_pct"], 66.67)

    def test_research_backtest_renders_neutralize_signal_stage_factor_profile_section(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {
                    "repair_speed_profile": "速度共振明显",
                    "market_trend_20d": "下跌",
                },
            }
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes, "simulations": simulations},
        )

        self.assertIn("## 高确信观察降级阶段因子画像", report)
        self.assertIn(
            "| 月度 | 2022-09 | 长期 60日 | market_trend_20d | 下跌 | 1 | 100.00% | 1 | 0 | 100.00% | 12.00% | 81.00% |",
            report,
        )

    def test_research_backtest_summarizes_horizon_selection_rows(self):
        outcomes = [
            {
                "stock_code": "000001",
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": -4.0,
                "hit": True,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度未形成",
                },
            },
            {
                "stock_code": "000001",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-04-27",
                "signal_score": -52,
                "signal_label": "强卖/回避",
                "return_pct": 12.0,
                "hit": False,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度未形成",
                },
            },
            {
                "stock_code": "000002",
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2022-04-28",
                "signal_score": -32,
                "signal_label": "卖出偏向",
                "return_pct": 3.0,
                "hit": False,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度未形成",
                },
            },
            {
                "stock_code": "000002",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-04-28",
                "signal_score": -48,
                "signal_label": "卖出偏向",
                "return_pct": 16.0,
                "hit": False,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度未形成",
                },
            },
        ]

        rows = research_backtest.horizon_selection_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_repair_speed_profile": "速度未形成"})],
        )
        all_sample = next(row for row in rows if row["period"] == "全样本")

        self.assertEqual(all_sample["pair_count"], 2)
        self.assertEqual(all_sample["medium_effective_risk_count"], 1)
        self.assertEqual(all_sample["medium_lagging_count"], 1)
        self.assertEqual(all_sample["long_lagging_count"], 2)
        self.assertEqual(all_sample["risk_to_lag_count"], 1)
        self.assertEqual(all_sample["medium_effective_risk_rate_pct"], 50.0)
        self.assertEqual(all_sample["long_lagging_rate_pct"], 100.0)
        self.assertEqual(all_sample["risk_to_lag_rate_pct"], 50.0)
        self.assertEqual(all_sample["medium_avg_return_pct"], -0.5)
        self.assertEqual(all_sample["long_avg_return_pct"], 14.0)
        self.assertEqual(all_sample["long_minus_medium_return_pct"], 14.5)
        self.assertEqual(all_sample["verdict"], "20日风控转60日滞后")

    def test_research_backtest_summarizes_horizon_selection_factor_rows(self):
        outcomes = []
        for stock_code, factor_value, medium_hit, long_hit, medium_return, long_return in [
            ("000001", "速度未形成", True, False, -4.0, 12.0),
            ("000002", "速度未形成", False, False, 3.0, 16.0),
            ("000003", "速度共振偏强", True, True, -5.0, -2.0),
        ]:
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_repair_speed_profile": factor_value,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        rows = research_backtest.horizon_selection_factor_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            factor_names=["market_repair_speed_profile"],
            min_pair_count=1,
        )
        not_formed = next(row for row in rows if row["factor_value"] == "速度未形成")
        stronger = next(row for row in rows if row["factor_value"] == "速度共振偏强")

        self.assertEqual(not_formed["pair_count"], 2)
        self.assertEqual(not_formed["medium_effective_risk_rate_pct"], 50.0)
        self.assertEqual(not_formed["long_lagging_rate_pct"], 100.0)
        self.assertEqual(not_formed["risk_to_lag_rate_pct"], 50.0)
        self.assertEqual(not_formed["long_minus_medium_return_pct"], 14.5)
        self.assertEqual(not_formed["verdict"], "20日风控转60日滞后")
        self.assertEqual(stronger["pair_count"], 1)
        self.assertEqual(stronger["medium_effective_risk_rate_pct"], 100.0)
        self.assertEqual(stronger["long_lagging_rate_pct"], 0.0)
        self.assertEqual(stronger["verdict"], "偏保留20日风控")

    def test_research_backtest_renders_horizon_selection_section(self):
        outcomes = [
            {
                "stock_code": "000001",
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": -4.0,
                "hit": True,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                },
            },
            {
                "stock_code": "000001",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-04-27",
                "signal_score": -52,
                "signal_label": "强卖/回避",
                "return_pct": 12.0,
                "hit": False,
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                },
            },
        ]

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日持有期选择验证", report)
        self.assertIn(
            "| 弱势尾部基础 | 全样本 | 1 | 100.00% | 0 | 100.00% | 100.00% | -4.00% | 12.00% | 16.00% | 20日风控转60日滞后 |",
            report,
        )

    def test_research_backtest_renders_horizon_selection_factor_section(self):
        outcomes = []
        for index in range(30):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_decline_speed": "跌速加快",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": 4.0,
                    "hit": False,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": 12.0,
                    "hit": False,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日阶段因子解释", report)
        self.assertIn(
            "| 弱势尾部基础 | market_decline_speed | 跌速加快 | 30 | 0.00% | 100.00% | 0.00% | 4.00% | 12.00% | 8.00% | 60日滞后主导 |",
            report,
        )

    def test_research_backtest_summarizes_horizon_stage_classifier_rows(self):
        outcomes = []

        def add_pair(stock_code, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {"market_trend_20d": "下跌", **factors},
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        add_pair("000001", {"market_tail_repair_signal": "低位待确认"}, False, False, 4.0, 12.0)
        add_pair("000002", {"market_decline_speed": "跌速持平"}, True, True, -3.0, -1.0)
        add_pair(
            "000003",
            {"market_tail_repair_signal": "低位待确认", "market_decline_speed": "跌速持平"},
            True,
            False,
            -2.0,
            8.0,
        )
        add_pair("000004", {"market_decline_speed": "跌速放缓"}, False, True, 2.0, -1.0)

        rows = research_backtest.horizon_stage_classifier_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_category = {row["category"]: row for row in rows}

        lag = by_category["60日滞后优先复核"]
        self.assertEqual(lag["primary_reason"], "市场低位待确认")
        self.assertEqual(lag["pair_count"], 1)
        self.assertEqual(lag["long_lagging_rate_pct"], 100.0)
        self.assertEqual(lag["avg_lag_rule_count"], 1.0)
        self.assertEqual(lag["avg_counter_rule_count"], 0.0)
        self.assertEqual(lag["verdict"], "60日滞后主导")

        counter = by_category["反例口袋继续复核"]
        self.assertEqual(counter["primary_reason"], "市场跌速持平")
        self.assertEqual(counter["medium_effective_risk_rate_pct"], 100.0)
        self.assertEqual(counter["long_lagging_rate_pct"], 0.0)
        self.assertEqual(counter["avg_lag_rule_count"], 0.0)
        self.assertEqual(counter["avg_counter_rule_count"], 1.0)
        self.assertEqual(counter["verdict"], "偏保留20日风控")

        conflict = by_category["冲突继续复核"]
        self.assertEqual(conflict["primary_reason"], "市场低位待确认 / 市场跌速持平")
        self.assertEqual(conflict["risk_to_lag_rate_pct"], 100.0)
        self.assertEqual(conflict["avg_lag_rule_count"], 1.0)
        self.assertEqual(conflict["avg_counter_rule_count"], 1.0)
        self.assertEqual(conflict["verdict"], "20日风控转60日滞后")

        mixed = by_category["混合继续复核"]
        self.assertEqual(mixed["primary_reason"], "未命中阶段口袋")
        self.assertEqual(mixed["long_lagging_rate_pct"], 0.0)
        self.assertEqual(mixed["verdict"], "混合，继续复核")

    def test_research_backtest_renders_horizon_stage_classifier_section(self):
        outcomes = []
        for index in range(10):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_tail_repair_signal": "低位待确认",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": 4.0,
                    "hit": False,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": 12.0,
                    "hit": False,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日多因子阶段分类器雏形", report)
        self.assertIn(
            "| 弱势尾部基础 | 60日滞后优先复核 | 市场低位待确认 | 10 | 0.00% | 100.00% | 0.00% | 4.00% | 12.00% | 8.00% | 1.00 | 0.00 | 60日滞后主导 |",
            report,
        )

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_factor_rows(self):
        outcomes = []

        def add_pair(stock_code, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        add_pair("000001", {"repair_quality_sync": "质量同步不足"}, False, False, 4.0, 12.0)
        add_pair("000002", {"repair_quality_sync": "质量同步不足"}, True, False, -2.0, 8.0)
        add_pair("000003", {"repair_quality_sync": "质量同步改善"}, True, True, -3.0, -1.0)
        add_pair("000004", {"market_tail_repair_signal": "低位待确认"}, False, False, 5.0, 15.0)

        rows = research_backtest.horizon_stage_mixed_bucket_factor_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            factor_names=["repair_quality_sync"],
            min_pair_count=1,
        )
        by_value = {row["factor_value"]: row for row in rows}

        self.assertEqual(set(by_value), {"质量同步不足", "质量同步改善"})
        weak_sync = by_value["质量同步不足"]
        self.assertEqual(weak_sync["bucket_pair_count"], 3)
        self.assertEqual(weak_sync["bucket_share_pct"], 2 / 3 * 100)
        self.assertEqual(weak_sync["pair_count"], 2)
        self.assertEqual(weak_sync["long_lagging_rate_pct"], 100.0)
        self.assertEqual(weak_sync["risk_to_lag_rate_pct"], 50.0)
        self.assertEqual(weak_sync["long_minus_medium_return_pct"], 9.0)
        self.assertEqual(weak_sync["verdict"], "20日风控转60日滞后")

        improving = by_value["质量同步改善"]
        self.assertEqual(improving["pair_count"], 1)
        self.assertEqual(improving["medium_effective_risk_rate_pct"], 100.0)
        self.assertEqual(improving["long_lagging_rate_pct"], 0.0)
        self.assertEqual(improving["verdict"], "偏保留20日风控")

    def test_research_backtest_renders_horizon_stage_mixed_bucket_factor_section(self):
        outcomes = []
        for index in range(30):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "repair_quality_sync": "质量同步不足",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": 4.0,
                    "hit": False,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": 12.0,
                    "hit": False,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日未命中混合桶拆解", report)
        self.assertIn(
            "| 弱势尾部基础 | repair_quality_sync | 质量同步不足 | 100.00% | 30 | 0.00% | 100.00% | 0.00% | 4.00% | 12.00% | 8.00% | 60日滞后主导 |",
            report,
        )

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_pair_rows(self):
        outcomes = []

        def add_pair(stock_code, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        add_pair(
            "000001",
            {"market_repair_speed_profile": "速度分化", "market_volume_expansion_speed": "速度温和改善"},
            True,
            True,
            -3.0,
            -1.0,
        )
        add_pair(
            "000002",
            {"market_repair_speed_profile": "速度分化", "market_volume_expansion_speed": "速度未改善"},
            False,
            False,
            4.0,
            12.0,
        )
        add_pair(
            "000003",
            {"market_repair_speed_profile": "速度未形成", "market_volume_expansion_speed": "速度未改善"},
            True,
            False,
            -2.0,
            8.0,
        )
        add_pair(
            "000004",
            {"market_tail_repair_signal": "低位待确认", "market_volume_expansion_speed": "速度未改善"},
            False,
            False,
            5.0,
            15.0,
        )

        rows = research_backtest.horizon_stage_mixed_bucket_pair_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            factor_pairs=[("market_repair_speed_profile", "market_volume_expansion_speed")],
            min_pair_count=1,
        )
        by_values = {row["factor_values"]: row for row in rows}

        self.assertEqual(
            set(by_values),
            {
                "速度分化 + 速度温和改善",
                "速度分化 + 速度未改善",
                "速度未形成 + 速度未改善",
            },
        )
        split_warm = by_values["速度分化 + 速度温和改善"]
        self.assertEqual(split_warm["bucket_pair_count"], 3)
        self.assertEqual(split_warm["bucket_share_pct"], 1 / 3 * 100)
        self.assertEqual(split_warm["medium_effective_risk_rate_pct"], 100.0)
        self.assertEqual(split_warm["long_lagging_rate_pct"], 0.0)
        self.assertEqual(split_warm["verdict"], "偏保留20日风控")

        not_formed = by_values["速度未形成 + 速度未改善"]
        self.assertEqual(not_formed["long_lagging_rate_pct"], 100.0)
        self.assertEqual(not_formed["risk_to_lag_rate_pct"], 100.0)
        self.assertEqual(not_formed["verdict"], "20日风控转60日滞后")

    def test_research_backtest_renders_horizon_stage_mixed_bucket_pair_section(self):
        outcomes = []
        for index in range(30):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_volume_expansion_speed": "速度温和改善",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": -3.0,
                    "hit": True,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": -1.0,
                    "hit": True,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日未命中混合桶二阶组合拆解", report)
        self.assertIn(
            "| 弱势尾部基础 | market_repair_speed_profile + market_volume_expansion_speed | 速度分化 + 速度温和改善 | 100.00% | 30 | 100.00% | 0.00% | 0.00% | -3.00% | -1.00% | 2.00% | 偏保留20日风控 |",
            report,
        )

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_target_fold_rows(self):
        outcomes = []

        def add_pair(stock_code, signal_date, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": signal_date,
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        target_factors = {"market_repair_speed_profile": "速度分化", "market_tail_extreme": "弱势低位"}
        add_pair("000001", "2022-04-27", target_factors, True, True, -3.0, -1.0)
        add_pair("000002", "2022-04-28", target_factors, False, False, 4.0, 12.0)
        add_pair("000003", "2022-05-05", target_factors, True, False, -2.0, 8.0)
        add_pair(
            "000004",
            "2022-05-06",
            {"market_repair_speed_profile": "速度未形成", "market_tail_extreme": "极端超卖"},
            False,
            False,
            5.0,
            15.0,
        )

        rows = research_backtest.horizon_stage_mixed_bucket_target_fold_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            buckets=("month", "quarter"),
            min_pair_count=1,
        )
        by_key = {(row["bucket"], row["period"]): row for row in rows}

        april = by_key[("month", "2022-04")]
        self.assertEqual(april["target_pair_count"], 3)
        self.assertEqual(april["target_share_pct"], 2 / 3 * 100)
        self.assertEqual(april["pair_count"], 2)
        self.assertEqual(april["medium_effective_risk_rate_pct"], 50.0)
        self.assertEqual(april["long_lagging_rate_pct"], 50.0)
        self.assertEqual(april["verdict"], "混合，继续复核")

        may = by_key[("month", "2022-05")]
        self.assertEqual(may["pair_count"], 1)
        self.assertEqual(may["risk_to_lag_rate_pct"], 100.0)
        self.assertEqual(may["verdict"], "20日风控转60日滞后")

        quarter = by_key[("quarter", "2022-Q2")]
        self.assertEqual(quarter["pair_count"], 3)
        self.assertEqual(quarter["target_share_pct"], 100.0)
        self.assertEqual(quarter["long_lagging_rate_pct"], 2 / 3 * 100)

    def test_research_backtest_renders_horizon_stage_mixed_bucket_target_fold_section(self):
        outcomes = []
        for index in range(10):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_tail_extreme": "弱势低位",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": -3.0,
                    "hit": True,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": -1.0,
                    "hit": True,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日速度分化低位折叠验证", report)
        self.assertIn(
            "| 弱势尾部基础 | 月度 | 2022-04 | 100.00% | 10 | 100.00% | 0.00% | 0.00% | -3.00% | -1.00% | 2.00% | 偏保留20日风控 |",
            report,
        )

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_target_daily_rows(self):
        outcomes = []

        def add_pair(stock_code, signal_date, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": signal_date,
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        target_factors = {"market_repair_speed_profile": "速度分化", "market_tail_extreme": "弱势低位"}
        add_pair("000001", "2022-04-27", target_factors, True, True, -3.0, -1.0)
        add_pair("000002", "2022-04-27", target_factors, False, False, 4.0, 12.0)
        add_pair("000003", "2022-04-28", target_factors, True, False, -2.0, 8.0)
        add_pair(
            "000004",
            "2022-04-28",
            {"market_repair_speed_profile": "速度未形成", "market_tail_extreme": "极端超卖"},
            False,
            False,
            5.0,
            15.0,
        )

        rows = research_backtest.horizon_stage_mixed_bucket_target_daily_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_date = {row["signal_trade_date"]: row for row in rows}

        self.assertEqual(set(by_date), {"2022-04-27", "2022-04-28"})
        first_day = by_date["2022-04-27"]
        self.assertEqual(first_day["target_pair_count"], 3)
        self.assertEqual(first_day["target_share_pct"], 2 / 3 * 100)
        self.assertEqual(first_day["pair_count"], 2)
        self.assertEqual(first_day["month"], "2022-04")
        self.assertEqual(first_day["quarter"], "2022-Q2")
        self.assertEqual(first_day["long_lagging_rate_pct"], 50.0)
        self.assertEqual(first_day["verdict"], "混合，继续复核")

        second_day = by_date["2022-04-28"]
        self.assertEqual(second_day["pair_count"], 1)
        self.assertEqual(second_day["risk_to_lag_rate_pct"], 100.0)
        self.assertEqual(second_day["verdict"], "20日风控转60日滞后")

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_target_daily_context_rows(self):
        outcomes = []

        def add_pair(stock_code, signal_date, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": signal_date,
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_tail_extreme": "弱势低位",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        reducer_context = {
            "market_decline_speed": "短期修复",
            "market_tail_repair_signal": "低位放量未确认",
            "market_repair_quality_confirmation": "修复质量恶化",
            "market_volume_expansion_speed": "速度温和改善",
            "repair_quality_sync": "质量同步不足",
            "tail_repair_signal": "低位待确认",
            "volume_expansion_speed": "速度未改善",
        }
        lag_context = {
            "market_decline_speed": "跌速加快",
            "market_tail_repair_signal": "低位放量未确认",
            "market_repair_quality_confirmation": "修复质量恶化",
            "market_volume_expansion_speed": "速度未改善",
            "repair_quality_sync": "质量同步不足",
            "tail_repair_signal": "低位空头延续",
            "volume_expansion_speed": "速度恶化",
        }
        add_pair("000001", "2022-04-27", reducer_context, False, True, 3.0, -2.0)
        add_pair("000002", "2022-04-27", reducer_context, True, True, -1.0, -3.0)
        add_pair("000003", "2022-05-10", lag_context, True, False, -2.0, 6.0)
        add_pair("000004", "2022-05-10", lag_context, True, False, -4.0, 8.0)

        rows = research_backtest.horizon_stage_mixed_bucket_target_daily_context_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_date = {row["signal_trade_date"]: row for row in rows}

        self.assertEqual(set(by_date), {"2022-04-27", "2022-05-10"})
        self.assertIn("market_decline_speed=短期修复(2/2,100%)", by_date["2022-04-27"]["market_visible_context"])
        self.assertIn("repair_quality_sync=质量同步不足(2/2,100%)", by_date["2022-04-27"]["stock_visible_context"])
        self.assertEqual(by_date["2022-04-27"]["long_lagging_rate_pct"], 0.0)
        self.assertEqual(by_date["2022-04-27"]["context_verdict"], "60日风险兑现，削弱滞后假设")
        self.assertEqual(by_date["2022-05-10"]["long_lagging_rate_pct"], 100.0)
        self.assertEqual(by_date["2022-05-10"]["context_verdict"], "仍偏60日滞后，不能降级")

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_target_repair_breadth_rows(self):
        outcomes = []

        def add_pair(stock_code, signal_date, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": signal_date,
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_tail_extreme": "弱势低位",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        broad_repair = {
            "market_volume_expansion_speed": "速度温和改善",
            "market_macd_repair_speed": "速度温和改善",
            "macd_repair_speed": "速度温和改善",
            "volume_expansion_speed": "速度未改善",
        }
        weak_repair = {
            "market_volume_expansion_speed": "速度未改善",
            "market_macd_repair_speed": "速度未改善",
            "macd_repair_speed": "速度未改善",
            "volume_expansion_speed": "速度未改善",
        }
        add_pair("000001", "2022-04-27", broad_repair, False, True, 4.0, -3.0)
        add_pair("000002", "2022-04-27", broad_repair, True, True, -1.0, -4.0)
        add_pair("000003", "2022-05-10", weak_repair, True, False, -2.0, 6.0)
        add_pair("000004", "2022-05-10", weak_repair, True, False, -4.0, 8.0)

        rows = research_backtest.horizon_stage_mixed_bucket_target_repair_breadth_daily_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_date = {row["signal_trade_date"]: row for row in rows}

        self.assertEqual(by_date["2022-04-27"]["market_volume_improved_pct"], 100.0)
        self.assertEqual(by_date["2022-04-27"]["stock_macd_repair_improved_pct"], 100.0)
        self.assertEqual(by_date["2022-04-27"]["long_lagging_rate_pct"], 0.0)
        self.assertEqual(by_date["2022-04-27"]["combo_label"], "市场量能改善+个股MACD修复广")
        self.assertEqual(by_date["2022-04-27"]["breadth_verdict"], "量能+MACD广度支持降确信")

        self.assertEqual(by_date["2022-05-10"]["market_volume_improved_pct"], 0.0)
        self.assertEqual(by_date["2022-05-10"]["stock_macd_repair_improved_pct"], 0.0)
        self.assertEqual(by_date["2022-05-10"]["long_lagging_rate_pct"], 100.0)
        self.assertEqual(by_date["2022-05-10"]["combo_label"], "市场量能未改善+个股MACD修复窄")
        self.assertEqual(by_date["2022-05-10"]["breadth_verdict"], "修复广度不足，仍偏60日滞后")

        combo_rows = research_backtest.summarize_repair_breadth_daily_rows(rows)
        combo_by_label = {row["combo_label"]: row for row in combo_rows}
        self.assertEqual(combo_by_label["市场量能改善+个股MACD修复广"]["daily_basket_count"], 1)
        self.assertEqual(combo_by_label["市场量能未改善+个股MACD修复窄"]["long_lagging_rate_pct"], 100.0)

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_target_repair_breadth_pair_rows(self):
        outcomes = []

        def add_pair(stock_code, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_tail_extreme": "弱势低位",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        add_pair(
            "000001",
            {"market_volume_expansion_speed": "速度温和改善", "macd_repair_speed": "速度温和改善"},
            False,
            True,
            3.0,
            -2.0,
        )
        add_pair(
            "000002",
            {"market_volume_expansion_speed": "速度温和改善", "macd_repair_speed": "速度温和改善"},
            True,
            True,
            -1.0,
            -4.0,
        )
        add_pair(
            "000003",
            {"market_volume_expansion_speed": "速度未改善", "macd_repair_speed": "速度温和改善"},
            True,
            False,
            -2.0,
            6.0,
        )
        add_pair(
            "000004",
            {"market_volume_expansion_speed": "速度未改善", "macd_repair_speed": "速度未改善"},
            True,
            False,
            -3.0,
            8.0,
        )

        rows = research_backtest.horizon_stage_mixed_bucket_target_repair_breadth_pair_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_combo = {row["combo_label"]: row for row in rows}

        self.assertEqual(by_combo["市场量能改善+个股MACD修复"]["pair_count"], 2)
        self.assertEqual(by_combo["市场量能改善+个股MACD修复"]["long_lagging_rate_pct"], 0.0)
        self.assertEqual(by_combo["市场量能改善+个股MACD修复"]["pair_verdict"], "量能确认后60日风险兑现")
        self.assertEqual(by_combo["市场量能未改善+个股MACD修复"]["long_lagging_rate_pct"], 100.0)
        self.assertEqual(by_combo["市场量能未改善+个股MACD修复"]["pair_verdict"], "市场量能未确认，60日仍易滞后")
        self.assertEqual(by_combo["市场量能未改善+个股MACD未修复"]["long_lagging_rate_pct"], 100.0)

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_repair_breadth_pair_rows(self):
        outcomes = []

        def add_pair(stock_code, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        target_factors = {
            "market_repair_speed_profile": "速度分化",
            "market_tail_extreme": "弱势低位",
            "market_volume_expansion_speed": "速度温和改善",
            "macd_repair_speed": "速度温和改善",
        }
        broader_mixed_factors = {
            "market_repair_speed_profile": "速度未形成",
            "market_tail_extreme": "极端超卖",
            "market_volume_expansion_speed": "速度未改善",
            "macd_repair_speed": "速度温和改善",
        }
        add_pair("000001", target_factors, False, True, 3.0, -2.0)
        add_pair("000002", broader_mixed_factors, True, False, -2.0, 6.0)

        rows = research_backtest.horizon_stage_mixed_bucket_repair_breadth_pair_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        by_combo = {row["combo_label"]: row for row in rows}

        self.assertEqual(by_combo["市场量能改善+个股MACD修复"]["pair_count"], 1)
        self.assertEqual(by_combo["市场量能未改善+个股MACD修复"]["pair_count"], 1)
        self.assertEqual(by_combo["市场量能未改善+个股MACD修复"]["long_lagging_rate_pct"], 100.0)

    def test_research_backtest_classifies_continuous_stage_tags(self):
        series = []
        for index in range(25):
            series.append(
                {
                    "close": 100 + index * 0.5,
                    "volume_ratio_5": 1.25 if index >= 20 else 0.9,
                    "macd_bar": -0.5 + index * 0.05,
                    "boll_position": "中轨上方" if index >= 22 else "中轨下方",
                    "rsi6": 35 + index,
                    "kdj_j": 15 + index,
                }
            )

        tags = research_backtest.continuous_repair_factor_tags_from_series(series)

        self.assertEqual(tags["volume_persistence"], "量能持续改善")
        self.assertEqual(tags["macd_repair_persistence"], "MACD多头持续")
        self.assertEqual(tags["low_escape"], "低位明显脱离")
        self.assertEqual(tags["rebound_stretch"], "20日反弹过度伸展")

    def test_research_backtest_summarizes_horizon_stage_mixed_bucket_repair_breadth_stage_folds(self):
        outcomes = []

        def add_pair(stock_code, signal_date, factors, medium_hit, long_hit, medium_return, long_return):
            base = {
                "stock_code": stock_code,
                "signal_trade_date": signal_date,
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_decline_speed": "短期修复",
                    "market_tail_repair_signal": "低位空头延续",
                    "market_repair_quality_confirmation": "修复质量恶化",
                    **factors,
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": medium_return,
                    "hit": medium_hit,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": long_return,
                    "hit": long_hit,
                }
            )

        improved_combo = {
            "market_volume_expansion_speed": "速度温和改善",
            "macd_repair_speed": "速度温和改善",
            "market_volume_persistence": "量能持续改善",
            "market_macd_repair_persistence": "MACD连续改善",
            "market_low_escape": "低位明显脱离",
            "market_rebound_stretch": "20日反弹明显",
        }
        not_improved_combo = {
            "market_volume_expansion_speed": "速度未改善",
            "macd_repair_speed": "速度温和改善",
            "market_volume_persistence": "量能持续不足",
            "market_macd_repair_persistence": "MACD改善不连续",
            "market_low_escape": "仍贴近低点",
            "market_rebound_stretch": "20日修复不足",
        }
        add_pair("000001", "2022-03-16", improved_combo, True, False, -1.0, 7.0)
        add_pair("000002", "2022-03-17", improved_combo, True, False, -2.0, 8.0)
        add_pair("000003", "2022-09-27", improved_combo, False, True, 4.0, -3.0)
        add_pair("000004", "2022-09-28", not_improved_combo, True, False, -2.0, 6.0)

        rows = research_backtest.horizon_stage_mixed_bucket_repair_breadth_stage_fold_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        keyed = {
            (row["combo_label"], row["fold_name"], row["fold_value"]): row
            for row in rows
        }

        march = keyed[("市场量能改善+个股MACD修复", "month", "2022-03")]
        self.assertEqual(march["pair_count"], 2)
        self.assertEqual(march["combo_share_pct"], 2 / 3 * 100)
        self.assertEqual(march["long_lagging_rate_pct"], 100.0)
        self.assertEqual(march["stage_fold_verdict"], "量能改善仍滞后，阶段不支持降确信")

        september = keyed[("市场量能改善+个股MACD修复", "month", "2022-09")]
        self.assertEqual(september["long_lagging_rate_pct"], 0.0)
        self.assertEqual(september["stage_fold_verdict"], "量能改善降确信成立")

        decline_speed = keyed[("市场量能未改善+个股MACD修复", "market_decline_speed", "短期修复")]
        self.assertEqual(decline_speed["pair_count"], 1)
        self.assertEqual(decline_speed["stage_fold_verdict"], "缺市场量能，偏60日滞后")

        continuous_rows = research_backtest.horizon_stage_mixed_bucket_repair_breadth_stage_fold_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            factor_names=research_backtest.DEFAULT_REPAIR_BREADTH_CONTINUOUS_STAGE_FACTORS,
            buckets=(),
            min_pair_count=1,
        )
        continuous_keyed = {
            (row["combo_label"], row["fold_name"], row["fold_value"]): row
            for row in continuous_rows
        }
        rebound = continuous_keyed[("市场量能改善+个股MACD修复", "market_rebound_stretch", "20日反弹明显")]
        self.assertEqual(rebound["pair_count"], 3)
        self.assertEqual(rebound["combo_share_pct"], 100.0)

        combo_rows = research_backtest.horizon_stage_mixed_bucket_repair_breadth_continuous_combo_rows(
            outcomes,
            profiles=[("弱势尾部测试", {"market_trend_20d": "下跌"})],
            min_pair_count=1,
        )
        combo_keyed = {
            (row["combo_label"], row["factor_pair"], row["factor_values"]): row
            for row in combo_rows
        }
        combo = combo_keyed[
            (
                "市场量能改善+个股MACD修复",
                "market_volume_persistence + market_rebound_stretch",
                "量能持续改善 + 20日反弹明显",
            )
        ]
        self.assertEqual(combo["pair_count"], 3)
        self.assertEqual(combo["combo_share_pct"], 100.0)

    def test_research_backtest_renders_horizon_stage_mixed_bucket_target_daily_section(self):
        outcomes = []
        for index in range(5):
            base = {
                "stock_code": f"{index:06d}",
                "signal_trade_date": "2022-04-27",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "factors": {
                    "market_trend_20d": "下跌",
                    "market_trend_60d": "下跌",
                    "trend_20d": "下跌",
                    "trend_60d": "下跌",
                    "market_repair_speed_profile": "速度分化",
                    "market_tail_extreme": "弱势低位",
                },
            }
            outcomes.append(
                {
                    **base,
                    "horizon": "medium_term",
                    "window_days": 20,
                    "return_pct": -3.0,
                    "hit": True,
                }
            )
            outcomes.append(
                {
                    **base,
                    "horizon": "long_term",
                    "window_days": 60,
                    "return_pct": -1.0,
                    "hit": True,
                }
            )

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes},
        )

        self.assertIn("## 弱势尾部20/60日速度分化低位日篮验证", report)
        self.assertIn(
            "| 弱势尾部基础 | 2022-04-27 | 2022-04 | 2022-Q2 | 100.00% | 5 | 100.00% | 0.00% | 0.00% | -3.00% | -1.00% | 2.00% | 偏保留20日风控 |",
            report,
        )
        self.assertIn("## 弱势尾部20/60日速度分化低位日篮可见变量对比", report)
        self.assertIn("60日风险兑现，削弱滞后假设", report)
        self.assertIn("## 弱势尾部20/60日速度分化低位修复广度验证", report)
        self.assertIn("## 弱势尾部20/60日混合桶市场量能门槛泛化验证", report)
        self.assertIn("## 弱势尾部20/60日混合桶量能门槛阶段折叠验证", report)
        self.assertIn("## 弱势尾部20/60日混合桶量能门槛连续阶段验证", report)
        self.assertIn("## 弱势尾部20/60日混合桶量能门槛连续组合验证", report)

    def test_research_backtest_renders_neutralize_signal_review_section(self):
        outcomes = [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "horizon": "long_term",
                "window_days": 60,
                "signal_trade_date": "2022-09-01",
                "signal_score": -38,
                "signal_label": "卖出偏向",
                "return_pct": 12.0,
                "max_drawdown_pct": -4.0,
                "hit": False,
                "factors": {"repair_speed_profile": "速度共振明显"},
            }
        ]
        simulations = [
            {
                "rule": {
                    "id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
                    "signal_side": "sell_avoid",
                    "score_adjustment_mode": "neutralize_to_watch",
                    "factor_scope": {"repair_speed_profile": "速度共振明显"},
                    "horizon": "long_term",
                    "window_days": 60,
                },
                "train": {
                    "matched_count": 200,
                    "neutralized_wrong_directional_rate_pct": 75.0,
                },
                "validation": {
                    "matched_count": 120,
                    "neutralized_wrong_directional_rate_pct": 85.0,
                },
                "basket_validation": {
                    "basket_count": 8,
                    "avg_basket_return_pct": 12.0,
                },
            }
        ]

        report = research_backtest.render_markdown_report(
            {},
            metadata={"outcomes": outcomes, "simulations": simulations},
        )

        self.assertIn("## 单信号观察降级复核样本", report)
        self.assertIn(
            "| 000001 平安银行 | 2022-09-01 | 长期 60日 | -38 / 卖出偏向 | 12.00% | 滞后误杀 | -4.00% | 81.00% | 15.00% | 1 | `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 高确信降级观察 |",
            report,
        )

    def test_research_backtest_candidate_rule_can_match_signal_side(self):
        buy_outcome = {
            "horizon": "long_term",
            "window_days": 120,
            "signal_score": 55,
            "signal_label": "强买",
            "factors": {"trend_250d": "下跌"},
        }
        sell_outcome = {
            "horizon": "long_term",
            "window_days": 120,
            "signal_score": -35,
            "signal_label": "卖出偏向",
            "factors": {"trend_250d": "下跌"},
        }
        rule = {
            "id": "sell-risk-only",
            "signal_side": "sell_avoid",
            "factor_name": "trend_250d",
            "factor_value": "下跌",
            "horizon": "long_term",
            "window_days": 120,
            "score_bias": -5,
        }

        self.assertFalse(research_backtest.candidate_rule_matches(buy_outcome, rule))
        self.assertTrue(research_backtest.candidate_rule_matches(sell_outcome, rule))

    def test_research_backtest_builds_candidate_rules_from_signal_side_factors(self):
        outcomes = []
        for _ in range(120):
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": -35,
                    "signal_label": "卖出偏向",
                    "return_pct": -6.0,
                    "hit": True,
                    "factors": {"trend_250d": "下跌"},
                }
            )

        summary = research_backtest.summarize_outcomes(outcomes)
        rules = research_backtest.build_candidate_rules(summary, limit=1)

        self.assertEqual(rules[0]["signal_side"], "sell_avoid")
        self.assertEqual(rules[0]["factor_name"], "trend_250d")
        self.assertEqual(rules[0]["factor_value"], "下跌")
        self.assertEqual(rules[0]["kind"], "risk_constraint")

    def test_research_backtest_candidate_rule_matches_factor_scope(self):
        outcome = {
            "horizon": "medium_term",
            "window_days": 20,
            "signal_score": -35,
            "signal_label": "卖出偏向",
            "factors": {
                "market_refined_regime": "market_bear_continuation|bear_continuation",
                "market_decline_speed": "跌速加快",
                "market_tail_extreme": "极端超卖",
                "weak_tail_extreme": "弱势低位",
            },
        }
        rule = {
            "id": "weak-tail-focus",
            "signal_side": "sell_avoid",
            "horizon": "medium_term",
            "window_days": 20,
            "factor_scope": {
                "market_refined_regime": "market_bear_continuation|bear_continuation",
                "market_decline_speed": "跌速加快",
                "market_tail_extreme": ["极端超卖", "弱势低位"],
                "weak_tail_extreme": ["极端超卖", "弱势低位"],
            },
        }

        self.assertTrue(research_backtest.candidate_rule_matches(outcome, rule))
        self.assertFalse(
            research_backtest.candidate_rule_matches(
                {
                    **outcome,
                    "factors": {
                        **outcome["factors"],
                        "market_tail_extreme": "常规",
                    },
                },
                rule,
            )
        )

    def test_research_backtest_builds_weak_tail_focus_candidate_rules(self):
        rules = research_backtest.weak_tail_focus_candidate_rules()

        self.assertTrue(any(rule["id"] == "weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20" for rule in rules))
        self.assertTrue(any(rule["id"] == "weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60" for rule in rules))
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])

    def test_research_backtest_builds_continuous_repair_focus_candidate_rules(self):
        rules = research_backtest.continuous_repair_focus_candidate_rules()

        self.assertTrue(
            any(rule["id"] == "continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20" for rule in rules)
        )
        self.assertTrue(
            any(rule["id"] == "continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60" for rule in rules)
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertTrue(
                "market_repair_continuity" in rule["factor_scope"]
                or "repair_continuity" in rule["factor_scope"]
            )

    def test_research_backtest_builds_repair_speed_focus_candidate_rules(self):
        rules = research_backtest.repair_speed_focus_candidate_rules()

        self.assertTrue(
            any(rule["id"] == "repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20" for rule in rules)
        )
        self.assertTrue(
            any(rule["id"] == "repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60" for rule in rules)
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertTrue(
                "market_repair_speed" in rule["factor_scope"]
                or "repair_speed" in rule["factor_scope"]
            )

    def test_research_backtest_builds_continuous_speed_focus_candidate_rules(self):
        rules = research_backtest.continuous_speed_focus_candidate_rules()

        self.assertTrue(
            any(rule["id"] == "continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20" for rule in rules)
        )
        self.assertTrue(
            any(rule["id"] == "continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60" for rule in rules)
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertTrue(
                "market_repair_speed_profile" in rule["factor_scope"]
                or "repair_speed_profile" in rule["factor_scope"]
                or "market_macd_repair_speed" in rule["factor_scope"]
                or "macd_repair_speed" in rule["factor_scope"]
            )

    def test_research_backtest_builds_repair_quality_focus_candidate_rules(self):
        rules = research_backtest.repair_quality_focus_candidate_rules()

        self.assertTrue(
            any(rule["id"] == "repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60" for rule in rules)
        )
        self.assertTrue(
            any(
                rule["id"] == "repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20"
                for rule in rules
            )
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertTrue(
                "market_repair_quality_confirmation" in rule["factor_scope"]
                or "repair_quality_confirmation" in rule["factor_scope"]
            )

    def test_research_backtest_builds_repair_quality_sync_focus_candidate_rules(self):
        rules = research_backtest.repair_quality_sync_focus_candidate_rules()

        self.assertTrue(
            any(
                rule["id"] == "repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60"
                for rule in rules
            )
        )
        self.assertTrue(
            any(
                rule["id"] == "repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20"
                for rule in rules
            )
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertIn("repair_quality_sync", rule["factor_scope"])

    def test_research_backtest_builds_repair_quality_failure_focus_candidate_rules(self):
        rules = research_backtest.repair_quality_failure_focus_candidate_rules()

        self.assertTrue(
            any(
                rule["id"] == "repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60"
                for rule in rules
            )
        )
        self.assertTrue(
            any(
                rule["id"] == "repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20"
                for rule in rules
            )
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertIn("repair_quality_sync", rule["factor_scope"])

    def test_research_backtest_builds_repair_quality_defense_pocket_candidate_rules(self):
        rules = research_backtest.repair_quality_defense_pocket_candidate_rules()

        self.assertTrue(
            any(
                rule["id"]
                == "repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60"
                for rule in rules
            )
        )
        self.assertTrue(
            any(
                rule["id"]
                == "repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20"
                for rule in rules
            )
        )
        for rule in rules:
            self.assertEqual(rule["signal_side"], "sell_avoid")
            self.assertEqual(rule["score_adjustment_mode"], "neutralize_to_watch")
            self.assertIn("market_refined_regime", rule["factor_scope"])
            self.assertIn("repair_quality_sync", rule["factor_scope"])
            self.assertTrue(
                "market_macd_repair_speed" in rule["factor_scope"]
                or "volume_expansion_speed" in rule["factor_scope"]
                or "market_repair_quality_confirmation" in rule["factor_scope"]
                or "tail_repair_signal" in rule["factor_scope"]
            )

    def test_research_backtest_builds_mixed_bucket_continuous_combo_candidate_rules(self):
        rules = research_backtest.mixed_bucket_continuous_combo_candidate_rules()

        self.assertEqual(len(rules), 4)
        first = rules[0]
        self.assertTrue(first["id"].startswith("mixed_bucket_continuous_combo:"))
        self.assertEqual(first["signal_side"], "sell_avoid")
        self.assertEqual(first["score_adjustment_mode"], "neutralize_to_watch")
        self.assertEqual(first["factor_scope"]["horizon_stage_category"], "混合继续复核")

        matching_outcome = {
            "horizon": "long_term",
            "window_days": 60,
            "signal_score": -38,
            "signal_label": "卖出偏向",
            "factors": {
                "market_trend_20d": "下跌",
                "market_trend_60d": "下跌",
                "trend_20d": "下跌",
                "trend_60d": "下跌",
                "horizon_stage_category": "混合继续复核",
                "market_volume_expansion_speed": "速度未改善",
                "macd_repair_speed": "速度温和改善",
                "market_volume_persistence": "量能脉冲不连续",
                "market_rebound_stretch": "20日仍下跌",
            },
        }
        self.assertTrue(research_backtest.candidate_rule_matches(matching_outcome, first))

        non_mixed_outcome = {
            **matching_outcome,
            "factors": {
                **matching_outcome["factors"],
                "horizon_stage_category": "60日滞后优先复核",
            },
        }
        self.assertFalse(research_backtest.candidate_rule_matches(non_mixed_outcome, first))

    def test_research_backtest_candidate_rule_lines_include_signal_side(self):
        outcomes = []
        for _ in range(120):
            outcomes.append(
                {
                    "horizon": "long_term",
                    "window_days": 120,
                    "signal_score": -35,
                    "signal_label": "卖出偏向",
                    "return_pct": -6.0,
                    "hit": True,
                    "factors": {"trend_250d": "下跌"},
                }
            )

        summary = research_backtest.summarize_outcomes(outcomes)
        lines = research_backtest.candidate_rule_lines(summary)

        self.assertIn("卖出/回避方向/trend_250d=下跌", "\n".join(lines))
        self.assertIn("风险约束", "\n".join(lines))

    def test_research_backtest_filters_stable_candidate_simulations(self):
        simulations = [
            {
                "rule": {"id": "stable", "score_bias": 6},
                "train": {
                    "matched_count": 120,
                    "hit_rate_delta_pct": 2.0,
                    "directional_avg_return_delta_pct": 1.0,
                    "directional_avg_drawdown_delta_pct": 0.2,
                },
                "validation": {
                    "matched_count": 80,
                    "hit_rate_delta_pct": 0.2,
                    "directional_avg_return_delta_pct": 0.3,
                    "directional_avg_drawdown_delta_pct": 0.1,
                },
            },
            {
                "rule": {"id": "return-degraded", "score_bias": 6},
                "train": {
                    "matched_count": 120,
                    "hit_rate_delta_pct": 2.0,
                    "directional_avg_return_delta_pct": 1.0,
                    "directional_avg_drawdown_delta_pct": 0.2,
                },
                "validation": {
                    "matched_count": 80,
                    "hit_rate_delta_pct": 0.2,
                    "directional_avg_return_delta_pct": -0.3,
                    "directional_avg_drawdown_delta_pct": 0.1,
                },
            },
            {
                "rule": {"id": "no-validation", "score_bias": 6},
                "train": {"matched_count": 120, "hit_rate_delta_pct": 4.0},
                "validation": {"matched_count": 0, "hit_rate_delta_pct": None},
            },
            {
                "rule": {"id": "overfit", "score_bias": -6},
                "train": {"matched_count": 120, "hit_rate_delta_pct": 3.0},
                "validation": {"matched_count": 80, "hit_rate_delta_pct": -0.1},
            },
        ]

        stable = research_backtest.stable_candidate_simulations(
            simulations,
            min_train_samples=100,
            min_validation_samples=50,
            min_train_delta_pct=1.0,
            min_validation_delta_pct=0.0,
        )

        self.assertEqual([item["rule"]["id"] for item in stable], ["stable"])

    def test_research_backtest_filters_stable_neutralize_to_watch_simulations(self):
        simulations = [
            {
                "rule": {"id": "neutralize-stable", "score_adjustment_mode": "neutralize_to_watch"},
                "train": {
                    "matched_count": 566,
                    "neutralized_directional_count": 566,
                    "neutralized_wrong_directional_count": 462,
                    "neutralized_wrong_directional_rate_pct": 81.63,
                    "wrong_directional_count_delta": -462,
                },
                "validation": {
                    "matched_count": 205,
                    "neutralized_directional_count": 205,
                    "neutralized_wrong_directional_count": 205,
                    "neutralized_wrong_directional_rate_pct": 100.0,
                    "wrong_directional_count_delta": -205,
                },
            },
            {
                "rule": {"id": "neutralize-overfit", "score_adjustment_mode": "neutralize_to_watch"},
                "train": {
                    "matched_count": 160,
                    "neutralized_directional_count": 160,
                    "neutralized_wrong_directional_count": 130,
                    "neutralized_wrong_directional_rate_pct": 81.25,
                    "wrong_directional_count_delta": -130,
                },
                "validation": {
                    "matched_count": 80,
                    "neutralized_directional_count": 80,
                    "neutralized_wrong_directional_count": 35,
                    "neutralized_wrong_directional_rate_pct": 43.75,
                    "wrong_directional_count_delta": -35,
                },
            },
        ]

        stable = research_backtest.stable_candidate_simulations(
            simulations,
            min_train_samples=100,
            min_validation_samples=50,
        )

        self.assertEqual([item["rule"]["id"] for item in stable], ["neutralize-stable"])

    def test_research_backtest_summarizes_candidate_rule_rolling_folds(self):
        outcomes = [
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-03",
                "signal_score": -36,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-01-17",
                "signal_score": -30,
                "signal_label": "卖出偏向",
                "return_pct": -4.0,
                "hit": True,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_trade_date": "2025-02-10",
                "signal_score": -28,
                "signal_label": "卖出偏向",
                "return_pct": 6.0,
                "hit": False,
                "factors": {"market_refined_regime": "market_bear_continuation|bear_continuation"},
            },
        ]
        rule = {
            "id": "neutralize-sell",
            "signal_side": "sell_avoid",
            "factor_name": "market_refined_regime",
            "factor_value": "market_bear_continuation|bear_continuation",
            "horizon": "medium_term",
            "window_days": 20,
            "score_adjustment_mode": "neutralize_to_watch",
        }

        folds = research_backtest.rolling_candidate_rule_folds(outcomes, rule, bucket="month")

        self.assertEqual([fold["bucket"] for fold in folds], ["2025-01", "2025-02"])
        self.assertEqual(folds[0]["matched_count"], 2)
        self.assertEqual(folds[0]["neutralized_wrong_directional_count"], 1)
        self.assertEqual(folds[0]["neutralized_wrong_directional_rate_pct"], 50.0)
        self.assertEqual(folds[1]["matched_count"], 1)
        self.assertEqual(folds[1]["neutralized_wrong_directional_rate_pct"], 100.0)

    def test_research_backtest_renders_rolling_fold_stability_section(self):
        simulations = [
            {
                "rule": {
                    "id": "neutralize-sell",
                    "score_adjustment_mode": "neutralize_to_watch",
                },
                "rolling_folds": [
                    {
                        "bucket": "2025-01",
                        "matched_count": 2,
                        "wrong_directional_count_delta": -1,
                        "neutralized_wrong_directional_rate_pct": 50.0,
                        "baseline_hit_rate_pct": 50.0,
                        "neutralized_wrong_directional_count": 1,
                    }
                ],
                "rolling_summary": {
                    "bucket": "month",
                    "fold_count": 1,
                    "folds_with_samples": 1,
                    "max_fold_sample_share_pct": 100.0,
                    "weighted_neutralized_wrong_directional_rate_pct": 50.0,
                },
            }
        ]

        lines = research_backtest.rolling_stability_lines(simulations)

        rendered = "\n".join(lines)
        self.assertIn("候选规则滚动折叠稳定性", rendered)
        self.assertIn("neutralize-sell", rendered)
        self.assertIn("2025-01", rendered)
        self.assertIn("最大单期样本占比 100.00%", rendered)

    def test_research_backtest_summarizes_candidate_rule_stage_factor_folds(self):
        outcomes = [
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_score": -36,
                "signal_label": "卖出偏向",
                "return_pct": 8.0,
                "hit": False,
                "factors": {
                    "market_refined_regime": "market_bear_continuation|bear_continuation",
                    "trend_20d": "上涨",
                },
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_score": -30,
                "signal_label": "卖出偏向",
                "return_pct": -4.0,
                "hit": True,
                "factors": {
                    "market_refined_regime": "market_bear_continuation|bear_continuation",
                    "trend_20d": "上涨",
                },
            },
            {
                "horizon": "medium_term",
                "window_days": 20,
                "signal_score": -28,
                "signal_label": "卖出偏向",
                "return_pct": 6.0,
                "hit": False,
                "factors": {
                    "market_refined_regime": "market_bear_continuation|bear_continuation",
                    "trend_20d": "震荡",
                },
            },
        ]
        rule = {
            "id": "neutralize-sell",
            "signal_side": "sell_avoid",
            "factor_name": "market_refined_regime",
            "factor_value": "market_bear_continuation|bear_continuation",
            "horizon": "medium_term",
            "window_days": 20,
            "score_adjustment_mode": "neutralize_to_watch",
        }

        folds = research_backtest.stage_candidate_rule_folds(outcomes, rule, "trend_20d")

        self.assertEqual([fold["bucket"] for fold in folds], ["trend_20d=上涨", "trend_20d=震荡"])
        self.assertEqual(folds[0]["matched_count"], 2)
        self.assertEqual(folds[0]["neutralized_wrong_directional_rate_pct"], 50.0)
        self.assertEqual(folds[1]["matched_count"], 1)
        self.assertEqual(folds[1]["neutralized_wrong_directional_rate_pct"], 100.0)

    def test_research_backtest_renders_stage_factor_stability_section(self):
        simulations = [
            {
                "rule": {"id": "neutralize-sell"},
                "stage_factor_folds": {
                    "trend_20d": [
                        {
                            "bucket": "trend_20d=上涨",
                            "matched_count": 2,
                            "wrong_directional_count_delta": -1,
                            "neutralized_wrong_directional_rate_pct": 50.0,
                            "baseline_hit_rate_pct": 50.0,
                            "neutralized_wrong_directional_count": 1,
                        }
                    ]
                },
                "stage_factor_summaries": {
                    "trend_20d": {
                        "factor_name": "trend_20d",
                        "folds_with_samples": 1,
                        "total_matched_count": 2,
                        "max_fold_sample_share_pct": 100.0,
                        "weighted_neutralized_wrong_directional_rate_pct": 50.0,
                        "positive_wrong_delta_fold_share_pct": 100.0,
                    }
                },
            }
        ]

        lines = research_backtest.stage_factor_stability_lines(simulations)

        rendered = "\n".join(lines)
        self.assertIn("候选规则阶段因子折叠解释", rendered)
        self.assertIn("trend_20d=上涨", rendered)
        self.assertIn("最大单因子值样本占比 100.00%", rendered)

    def test_research_backtest_parse_args_accepts_long_task_options(self):
        args = research_backtest.parse_args(
            [
                "--codes-file",
                "stock.md",
                "--from-date",
                "2025-06-19",
                "--to-date",
                "2026-06-19",
                "--validation-from",
                "2026-02-19",
                "--max-codes",
                "3",
                "--sample-step",
                "5",
                "--benchmark-index",
                "sh000001",
                "--output",
                "docs/research/custom.md",
            ]
        )

        self.assertEqual(args.codes_file, "stock.md")
        self.assertEqual(args.from_date, dt.date(2025, 6, 19))
        self.assertEqual(args.to_date, dt.date(2026, 6, 19))
        self.assertEqual(args.validation_from, dt.date(2026, 2, 19))
        self.assertEqual(args.max_codes, 3)
        self.assertEqual(args.sample_step, 5)
        self.assertEqual(args.benchmark_index, "sh000001")
        self.assertEqual(args.output, "docs/research/custom.md")

    def test_parse_codes_supports_common_separators_and_deduplication(self):
        self.assertEqual(
            parse_codes(["000001, sh600519，300750 000001"]),
            ["000001", "600519", "300750"],
        )

    def test_load_codes_from_stock_md_style_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            codes_file = Path(tmpdir) / "stock.md"
            codes_file.write_text(
                "\n".join(
                    [
                        "# 观察池",
                        "002466",
                        "",
                        "- 600519",
                        "3. 300750 # 宁德时代",
                        "002466",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(load_codes_from_file(codes_file), ["002466", "600519", "300750"])

    def test_normalize_code_rejects_invalid_code(self):
        with self.assertRaises(ValueError):
            normalize_code("abc")

    def test_pick_metric_prefers_known_financial_column(self):
        source_name, value = pick_metric(
            {
                "日期": "2025-12-31",
                "加权净资产收益率(%)": "12.34",
            },
            "roe",
        )
        self.assertEqual(source_name, "加权净资产收益率(%)")
        self.assertEqual(value, 12.34)

    def test_format_money_uses_yi_for_large_market_cap(self):
        self.assertEqual(format_money(123_456_789), "1.23亿")

    def test_render_markdown_contains_stock_sections(self):
        analysis = StockAnalysis(
            code="000001",
            name="平安银行",
            industry="银行",
            report_date="2025-12-31",
            metrics=[Metric(label="ROE", value=10.0, unit="%", source_name="净资产收益率(%)")],
            strengths=["测试优势"],
            risks=["测试风险"],
        )
        output = render_markdown([analysis])
        self.assertIn("## 000001 平安银行", output)
        self.assertIn("| ROE | 10.00% | 净资产收益率(%) |", output)

    def test_cash_flow_to_profit_ratio_uses_ratio_unit(self):
        units = {key: unit for key, _, unit in DISPLAY_METRICS}
        self.assertEqual(units["ocf_to_profit"], "倍")

        analysis = StockAnalysis(
            code="002466",
            metrics=[Metric(label="经营现金流/净利润", value=0.0912, unit="倍", source_name="经营现金净流量与净利润的比率(%)")],
        )
        evaluate_analysis(analysis)
        output = render_markdown([analysis])

        self.assertIn("| 经营现金流/净利润 | 0.09倍 | 经营现金净流量与净利润的比率(%) |", output)
        self.assertIn("经营现金流/净利润 0.09倍", "\n".join(analysis.risks))
        self.assertNotIn("经营现金流/净利润 0.09%", output)

    def test_calculate_technical_snapshot_from_daily_rows(self):
        rows = []
        for index in range(1, 36):
            rows.append(
                {
                    "日期": f"2026-05-{index:02d}" if index <= 31 else f"2026-06-{index - 31:02d}",
                    "收盘": index,
                    "最高": index + 1,
                    "最低": index - 1,
                    "成交量": index * 100,
                    "成交额": index * 1000,
                    "换手率": index / 10,
                }
            )

        snapshot = sfa.calculate_technical_snapshot(rows)

        self.assertEqual(snapshot.trade_date, "2026-06-04")
        self.assertEqual(snapshot.latest_close, 35)
        self.assertEqual(snapshot.latest_volume, 3500)
        self.assertEqual(snapshot.volume_ratio_5, 3500 / 3300)
        self.assertGreater(snapshot.macd_dif, snapshot.macd_dea)
        self.assertGreater(snapshot.macd_bar, 0)
        self.assertEqual(snapshot.boll_mid, 25.5)
        self.assertEqual(snapshot.rsi6, 100.0)
        self.assertIsNotNone(snapshot.kdj_k)
        self.assertIsNotNone(snapshot.kdj_d)
        self.assertIsNotNone(snapshot.kdj_j)

    def test_fetch_technical_snapshot_respects_as_of_date(self):
        import pandas as pd

        class FakeAk:
            def __init__(self):
                self.kwargs = {}

            def stock_zh_a_daily(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    [
                        {
                            "date": "2026-03-13",
                            "close": 10,
                            "high": 10.5,
                            "low": 9.5,
                            "volume": 10000,
                            "amount": 100000,
                            "turnover": 0.01,
                        },
                        {
                            "date": "2026-03-15",
                            "close": 11,
                            "high": 11.5,
                            "low": 10.5,
                            "volume": 11000,
                            "amount": 121000,
                            "turnover": 0.02,
                        },
                        {
                            "date": "2026-03-16",
                            "close": 12,
                            "high": 12.5,
                            "low": 11.5,
                            "volume": 12000,
                            "amount": 144000,
                            "turnover": 0.03,
                        },
                    ]
                )

        fake_ak = FakeAk()

        snapshot, _, error = sfa.fetch_technical_snapshot(
            fake_ak,
            "002466",
            technical_days=260,
            adjust="qfq",
            as_of_date=dt.date(2026, 3, 15),
        )

        self.assertIsNone(error)
        self.assertEqual(fake_ak.kwargs["end_date"], "20260315")
        self.assertEqual(snapshot.trade_date, "2026-03-15")
        self.assertEqual(snapshot.latest_close, 11)

    def test_fetch_analysis_items_disables_realtime_spot_in_historical_mode(self):
        args = SimpleNamespace(
            codes=["002466"],
            codes_file="stock.md",
            start_year="2021",
            technical_days=260,
            adjust="qfq",
            as_of_date=dt.date(2026, 3, 15),
            quiet=True,
        )
        analysis = StockAnalysis(
            code="002466",
            technical=sfa.TechnicalSnapshot(trade_date="2026-03-15", latest_close=11),
            source_errors=[],
        )

        with (
            patch.dict(sys.modules, {"akshare": SimpleNamespace()}),
            patch.object(mysql_sink.sfa, "resolve_input_codes", return_value=["002466"]),
            patch.object(mysql_sink.sfa, "fetch_spot_snapshot") as spot_mock,
            patch.object(mysql_sink.sfa, "build_analysis", return_value=analysis) as build_mock,
        ):
            items = mysql_sink.fetch_analysis_items(args)

        spot_mock.assert_not_called()
        build_mock.assert_called_once_with(
            SimpleNamespace(),
            "002466",
            "2021",
            {},
            260,
            "qfq",
            dt.date(2026, 3, 15),
        )
        self.assertIn("历史回填模式不使用实时行情/估值快照", items[0]["source_errors"])

    def test_fetch_analysis_items_uses_codes_file_name_when_data_sources_have_no_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            codes_file = Path(tmpdir) / "stock.md"
            codes_file.write_text("002466-天齐锂业\n", encoding="utf-8")
            args = SimpleNamespace(
                codes=[],
                codes_file=str(codes_file),
                start_year="2021",
                technical_days=260,
                adjust="qfq",
                as_of_date=None,
                quiet=True,
            )
            analysis = StockAnalysis(
                code="002466",
                technical=sfa.TechnicalSnapshot(trade_date="2026-06-12", latest_close=62.5),
                source_errors=[],
            )

            with (
                patch.dict(sys.modules, {"akshare": SimpleNamespace()}),
                patch.object(mysql_sink.sfa, "fetch_spot_snapshot", return_value=({}, None)),
                patch.object(mysql_sink.sfa, "build_analysis", return_value=analysis),
            ):
                items = mysql_sink.fetch_analysis_items(args)

        self.assertEqual(items[0]["name"], "天齐锂业")

    def test_fetch_analysis_items_logs_progress_and_source_errors(self):
        args = SimpleNamespace(
            codes=["002466", "600519"],
            codes_file="stock.md",
            start_year="2021",
            technical_days=260,
            adjust="qfq",
            as_of_date=None,
            quiet=False,
        )
        analyses = [
            StockAnalysis(
                code="002466",
                name="天齐锂业",
                technical=sfa.TechnicalSnapshot(trade_date="2026-06-16", latest_close=62.5),
                source_errors=[],
            ),
            StockAnalysis(
                code="600519",
                name="贵州茅台",
                technical=sfa.TechnicalSnapshot(trade_date="2026-06-16", latest_close=1400),
                source_errors=[],
            ),
        ]
        stderr = io.StringIO()

        with (
            patch.dict(sys.modules, {"akshare": SimpleNamespace()}),
            patch.object(mysql_sink.sfa, "resolve_input_codes", return_value=["002466", "600519"]),
            patch.object(
                mysql_sink.sfa,
                "fetch_spot_snapshot",
                return_value=({}, "实时估值快照获取失败：ProxyError"),
            ),
            patch.object(mysql_sink.sfa, "build_analysis", side_effect=analyses),
            contextlib.redirect_stderr(stderr),
        ):
            mysql_sink.fetch_analysis_items(args)

        output = stderr.getvalue()
        self.assertIn("准备分析 2 只股票", output)
        self.assertIn("[1/2] 开始分析 002466", output)
        self.assertIn("[2/2] 完成分析 600519", output)
        self.assertIn("数据源提醒：实时估值快照获取失败：ProxyError", output)

    def test_preflight_checks_runtime_dependencies_codes_and_ingest_health(self):
        args = SimpleNamespace(
            codes=[],
            codes_file="stock.md",
            ingest_url="https://stock.example.com/api/ingest/daily-analysis",
            quiet=False,
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true,"database":"stock_analysis_test"}'

        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse()

        stderr = io.StringIO()
        with (
            patch.dict(sys.modules, {"akshare": SimpleNamespace(__version__="1.18.64")}),
            patch.object(mysql_sink, "load_scorer", return_value=SimpleNamespace()),
            patch.object(mysql_sink.sfa, "resolve_input_codes", return_value=["002466", "600519"]),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = mysql_sink.run_preflight(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["url"], "https://stock.example.com/api/health")
        self.assertEqual(captured["timeout"], 10)
        output = stderr.getvalue()
        self.assertIn("akshare 可导入", output)
        self.assertIn("股票代码文件可读取：2 只", output)
        self.assertIn("生产服务健康检查通过", output)

    def test_parse_args_accepts_historical_backfill_options(self):
        args = mysql_sink.parse_args(
            [
                "002466",
                "--as-of-date",
                "2026-03-15",
                "--backfill-from",
                "2026-03-15",
                "--backfill-to",
                "2026-03-20",
            ]
        )

        self.assertEqual(args.as_of_date, dt.date(2026, 3, 15))
        self.assertEqual(args.backfill_from, dt.date(2026, 3, 15))
        self.assertEqual(args.backfill_to, dt.date(2026, 3, 20))

    def test_parse_args_accepts_skip_eastmoney(self):
        args = mysql_sink.parse_args(["002466", "--skip-eastmoney"])

        self.assertTrue(args.skip_eastmoney)

    def test_backfill_helpers_iterate_dates_and_skip_duplicate_trade_dates(self):
        self.assertEqual(
            mysql_sink.iter_dates(dt.date(2026, 3, 15), dt.date(2026, 3, 17)),
            [dt.date(2026, 3, 15), dt.date(2026, 3, 16), dt.date(2026, 3, 17)],
        )

        seen = set()
        first_pass = mysql_sink.filter_new_trade_date_results(
            [
                {"code": "002466", "raw": {"technical": {"trade_date": "2026-03-13"}}},
                {"code": "002466", "raw": {"technical": {"trade_date": "2026-03-13"}}},
            ],
            seen,
        )
        second_pass = mysql_sink.filter_new_trade_date_results(
            [{"code": "002466", "raw": {"technical": {"trade_date": "2026-03-16"}}}],
            seen,
        )

        self.assertEqual(len(first_pass), 1)
        self.assertEqual(mysql_sink.analysis_trade_date(first_pass[0]), "2026-03-13")
        self.assertEqual(len(second_pass), 1)
        self.assertEqual(mysql_sink.analysis_trade_date(second_pass[0]), "2026-03-16")

    def test_render_markdown_contains_technical_section(self):
        analysis = StockAnalysis(
            code="002466",
            technical=sfa.TechnicalSnapshot(
                trade_date="2026-06-12",
                latest_close=10.0,
                latest_volume=123456,
                volume_ratio_5=1.2,
                macd_dif=0.11,
                macd_dea=0.08,
                macd_bar=0.06,
                boll_mid=9.5,
                boll_upper=10.5,
                boll_lower=8.5,
                kdj_k=70.0,
                kdj_d=60.0,
                kdj_j=90.0,
                rsi6=65.0,
                rsi12=55.0,
                rsi24=50.0,
                signals=["测试技术信号"],
            ),
            metrics=[],
            strengths=["测试优势"],
            risks=["测试风险"],
        )

        output = render_markdown([analysis])

        self.assertIn("### 技术面指标快照（交易日：2026-06-12）", output)
        self.assertIn("| MACD | DIF 0.110 / DEA 0.080 / 柱 0.060 |", output)
        self.assertIn("- 测试技术信号", output)

    def test_latest_rsi_uses_cn_sma_smoothing(self):
        closes = [10, 12, 11, 13, 12, 14, 13, 15]

        self.assertAlmostEqual(sfa.latest_rsi(closes, 6), 82.1922304846794)

    def test_calculate_technical_trend_rates_rising_series_as_strong(self):
        rows = []
        for index in range(1, 281):
            close = 10 + index * 0.2
            rows.append(
                {
                    "日期": f"2025-01-{index:03d}",
                    "收盘": close,
                    "最高": close + 0.5,
                    "最低": close - 0.5,
                    "成交量": 10000 + index * 100,
                    "成交额": close * (10000 + index * 100),
                    "换手率": 1 + index / 1000,
                }
            )

        series = sfa.calculate_technical_series(rows)
        trend = sfa.calculate_technical_trend(series)

        self.assertEqual(trend.rating, "技术趋势偏强")
        self.assertGreaterEqual(trend.score, 4)
        self.assertEqual([window.days for window in trend.windows], [20, 60, 120, 250])
        self.assertGreater(trend.windows[0].return_pct, 0)
        self.assertIn("中长期走势偏强", trend.conclusion)

    def test_render_markdown_contains_technical_trend_section(self):
        analysis = StockAnalysis(
            code="002466",
            technical=sfa.TechnicalSnapshot(trade_date="2026-06-12", signals=["测试技术信号"]),
            technical_trend=sfa.TechnicalTrendAnalysis(
                rating="技术趋势偏强",
                score=5,
                conclusion="中长期走势偏强，回调时更适合结合基本面继续跟踪。",
                windows=[
                    sfa.TrendWindow(
                        days=20,
                        return_pct=12.3,
                        close_vs_ma_pct=4.5,
                        macd_positive_ratio=0.8,
                        boll_mid_above_ratio=0.9,
                    )
                ],
                signals=["测试长期趋势信号"],
            ),
            metrics=[],
            strengths=["测试优势"],
            risks=["测试风险"],
        )

        output = render_markdown([analysis])

        self.assertIn("### 长期技术趋势分析", output)
        self.assertIn("技术趋势偏强", output)
        self.assertIn("| 20日 | 12.30% | 4.50% | 80.00% | 90.00% |", output)
        self.assertIn("- 测试长期趋势信号", output)

    def test_fetch_individual_info_uses_compact_eastmoney_snapshot(self):
        response = SimpleNamespace(
            json=lambda: {
                "rc": 0,
                "data": {
                    "f43": 64.38,
                    "f57": "002466",
                    "f58": "天齐锂业",
                    "f84": 1713218321,
                    "f85": 1475723995,
                    "f116": 110296995505.98,
                    "f117": 95007110798.1,
                    "f127": "能源金属",
                    "f189": 20100831,
                },
            }
        )

        with patch("requests.get", return_value=response) as get_mock:
            info, error = sfa.fetch_individual_info(SimpleNamespace(), "002466")

        self.assertIsNone(error)
        self.assertEqual(info["股票简称"], "天齐锂业")
        self.assertEqual(info["行业"], "能源金属")
        self.assertEqual(info["总股本"], 1713218321)
        get_mock.assert_called_once()

    def test_compact_eastmoney_snapshot_retries_transient_proxy_disconnects(self):
        response = SimpleNamespace(
            json=lambda: {
                "rc": 0,
                "data": {
                    "f43": 12.3,
                    "f57": "000001",
                    "f58": "平安银行",
                },
            }
        )

        with (
            patch("requests.get", side_effect=[RuntimeError("proxy closed"), RuntimeError("proxy closed"), response]),
            patch("time.sleep"),
        ):
            snapshot = sfa.eastmoney_stock_snapshot("000001")

        self.assertEqual(snapshot["名称"], "平安银行")

    def test_fetch_spot_snapshot_uses_compact_eastmoney_snapshot_for_requested_codes(self):
        response = SimpleNamespace(
            json=lambda: {
                "rc": 0,
                "data": {
                    "f43": 64.38,
                    "f50": 1.0,
                    "f57": "002466",
                    "f58": "天齐锂业",
                    "f116": 110296995505.98,
                    "f117": 95007110798.1,
                    "f162": 14.7,
                    "f167": 2.38,
                    "f168": 4.64,
                    "f170": 1.04,
                },
            }
        )

        with patch("requests.get", return_value=response):
            spot, error = sfa.fetch_spot_snapshot(SimpleNamespace(), ["002466"])

        self.assertIsNone(error)
        self.assertEqual(spot["002466"]["名称"], "天齐锂业")
        self.assertEqual(spot["002466"]["市盈率-动态"], 14.7)
        self.assertEqual(spot["002466"]["换手率"], 4.64)

    def test_fetch_spot_snapshot_falls_back_to_sina_realtime_quote(self):
        import pandas as pd

        class FakeAk:
            def stock_zh_a_spot(self):
                return pd.DataFrame(
                    [
                        {
                            "代码": "sz002466",
                            "名称": "天齐锂业",
                            "最新价": 64.04,
                            "涨跌幅": 0.078,
                            "成交量": 70765374.0,
                            "成交额": 4567795653.0,
                        }
                    ]
                )

        with patch.object(sfa, "eastmoney_stock_snapshot", side_effect=RuntimeError("proxy closed")):
            spot, error = sfa.fetch_spot_snapshot(FakeAk(), ["002466"])

        self.assertEqual(spot["002466"]["名称"], "天齐锂业")
        self.assertEqual(spot["002466"]["股票简称"], "天齐锂业")
        self.assertEqual(spot["002466"]["最新价"], 64.04)
        self.assertEqual(spot["002466"]["涨跌幅"], 0.078)
        self.assertEqual(spot["002466"]["数据源"], "新浪实时行情")
        self.assertIn("实时估值快照降级", error)
        self.assertIn("缺少动态市盈率/市净率/市值/股本/行业/上市时间", error)

    def test_fetch_spot_snapshot_stops_eastmoney_after_proxy_failure(self):
        import pandas as pd

        class FakeAk:
            def stock_zh_a_spot(self):
                return pd.DataFrame(
                    [
                        {"代码": "sz002466", "名称": "天齐锂业", "最新价": 64.04},
                        {"代码": "sh600519", "名称": "贵州茅台", "最新价": 1240.0},
                    ]
                )

        with patch.object(sfa, "eastmoney_stock_snapshot", side_effect=RuntimeError("Unable to connect to proxy")) as eastmoney_mock:
            spot, error = sfa.fetch_spot_snapshot(FakeAk(), ["002466", "600519"])

        eastmoney_mock.assert_called_once_with("002466")
        self.assertEqual(set(spot), {"002466", "600519"})
        self.assertEqual(spot["600519"]["名称"], "贵州茅台")
        self.assertIn("已停止继续尝试Eastmoney", error)

    def test_fetch_spot_snapshot_can_skip_eastmoney_directly(self):
        import pandas as pd

        class FakeAk:
            def stock_zh_a_spot(self):
                return pd.DataFrame([{"代码": "sz002466", "名称": "天齐锂业", "最新价": 64.04}])

        with patch.object(sfa, "eastmoney_stock_snapshot") as eastmoney_mock:
            spot, error = sfa.fetch_spot_snapshot(FakeAk(), ["002466"], skip_eastmoney=True)

        eastmoney_mock.assert_not_called()
        self.assertEqual(spot["002466"]["名称"], "天齐锂业")
        self.assertIn("已跳过Eastmoney", error)

    def test_fetch_individual_info_falls_back_to_code_name_table(self):
        import pandas as pd

        class FakeAk:
            def stock_info_a_code_name(self):
                return pd.DataFrame([{"code": "002466", "name": "天齐锂业"}])

        with patch.object(sfa, "eastmoney_stock_snapshot", side_effect=RuntimeError("proxy closed")):
            info, error = sfa.fetch_individual_info(FakeAk(), "002466")

        self.assertEqual(info["股票代码"], "002466")
        self.assertEqual(info["股票简称"], "天齐锂业")
        self.assertEqual(info["名称"], "天齐锂业")
        self.assertEqual(info["数据源"], "A股代码名称表")
        self.assertIn("个股信息降级", error)
        self.assertIn("缺少行业/股本/上市时间/估值字段", error)

    def test_fetch_individual_info_can_skip_eastmoney_directly(self):
        import pandas as pd

        class FakeAk:
            def stock_info_a_code_name(self):
                return pd.DataFrame([{"code": "002466", "name": "天齐锂业"}])

        with patch.object(sfa, "eastmoney_stock_snapshot") as eastmoney_mock:
            info, error = sfa.fetch_individual_info(FakeAk(), "002466", skip_eastmoney=True)

        eastmoney_mock.assert_not_called()
        self.assertEqual(info["股票简称"], "天齐锂业")
        self.assertIn("已跳过Eastmoney", error)

    def test_build_analysis_reuses_spot_snapshot_info_without_second_eastmoney_request(self):
        spot = {
            "002466": {
                "名称": "天齐锂业",
                "股票简称": "天齐锂业",
                "行业": "能源金属",
                "上市时间": 20100831,
                "最新价": 64.38,
                "最新": 64.38,
                "总市值": 110296995505.98,
                "流通市值": 95007110798.1,
                "总股本": 1713218321,
                "流通股": 1475723995,
                "市盈率-动态": 14.7,
                "市净率": 2.38,
                "换手率": 4.64,
                "量比": 1.0,
            }
        }

        with (
            patch.object(sfa, "fetch_individual_info", return_value=({}, "不应调用")) as individual_mock,
            patch.object(sfa, "fetch_financial_indicator", return_value=({}, "", None)),
            patch.object(
                sfa,
                "fetch_technical_snapshot",
                return_value=(sfa.TechnicalSnapshot(trade_date="2026-06-15"), None, None),
            ),
        ):
            analysis = sfa.build_analysis(SimpleNamespace(), "002466", "2021", spot, 260, "qfq")

        individual_mock.assert_not_called()
        self.assertEqual(analysis.name, "天齐锂业")
        self.assertEqual(analysis.industry, "能源金属")
        self.assertEqual(analysis.valuation["市盈率-动态"], 14.7)

    def test_mysql_text_literal_uses_base64_encoding(self):
        literal = mysql_sink.sql_text("紫金's")

        self.assertIn("FROM_BASE64", literal)
        self.assertNotIn("紫金", literal)
        self.assertNotIn("'s", literal)

    def test_generate_final_report_contains_score_and_data_warning(self):
        result = {
            "code": "002466",
            "name": "",
            "score": 5,
            "signal": "观望",
            "confidence": "低",
            "regime": "range",
            "advice": "接近中性，当前更适合观察。",
            "horizon_scores": {
                "short_term": {"label": "短期", "score": -8, "signal": "观望"},
                "medium_term": {"label": "中期", "score": 6, "signal": "观望"},
                "long_term": {"label": "长期", "score": 18, "signal": "买入偏向"},
            },
            "strategy_adjustments": [
                {
                    "id": "macd-kdj-overheat-short-term",
                    "horizon": "short_term",
                    "regime": "trend",
                    "reason": "历史复盘显示短期择时过度奖励 MACD/KDJ 共振。",
                }
            ],
            "parts": [],
            "source_errors": ["实时估值快照获取失败：ProxyError"],
            "raw": {
                "code": "002466",
                "name": "",
                "report_date": "2026-03-31",
                "technical": {
                    "trade_date": "2026-06-12",
                    "latest_close": 62.5,
                    "latest_volume": 990333.98,
                    "latest_amount": 6140893986,
                    "macd": {"dif": -2.12, "dea": -1.93, "bar": -0.39},
                    "boll": {"position": "中轨下方"},
                    "rsi": {"rsi6": 57.77, "rsi12": 47.36, "rsi24": 48.21},
                },
                "technical_trend": {"rating": "技术趋势震荡", "score": 1, "conclusion": "趋势震荡。"},
                "metrics": [
                    {"label": "ROE", "value": 4.31},
                    {"label": "经营现金流/净利润", "value": 0.0912},
                ],
                "strengths": ["营收增长"],
                "risks": ["现金流偏弱"],
            },
        }

        title, report_text, report_json = mysql_sink.generate_final_report(result)

        self.assertIn("002466 2026-06-12 最终分析报告", title)
        self.assertIn("评分：5/100", report_text)
        self.assertIn("短期评分：-8/100（观望）", report_text)
        self.assertIn("中期评分：6/100（观望）", report_text)
        self.assertIn("长期评分：18/100（买入偏向）", report_text)
        self.assertIn("## 复盘与自学习", report_text)
        self.assertIn("短期：macd-kdj-overheat-short-term", report_text)
        self.assertIn("macd-kdj-overheat-short-term", report_text)
        self.assertIn("## 数据提醒", report_text)
        self.assertEqual(report_json["signal"], "观望")
        self.assertEqual(report_json["horizon_scores"]["long_term"]["score"], 18)
        self.assertEqual(report_json["strategy_adjustments"][0]["id"], "macd-kdj-overheat-short-term")

    def test_buy_signal_scorer_returns_three_horizon_scores(self):
        scorer = load_signal_scorer()
        result = scorer.score_item(
            {
                "code": "002466",
                "name": "",
                "valuation": {"市盈率-动态": 24},
                "metrics": [
                    {"label": "ROE", "value": 12},
                    {"label": "营收增长", "value": 12},
                    {"label": "净利润增长", "value": 14},
                    {"label": "资产负债率", "value": 40},
                    {"label": "每股经营现金流", "value": 0.5},
                    {"label": "经营现金流/净利润", "value": 0.8},
                ],
                "technical": {
                    "trade_date": "2026-06-12",
                    "volume_ratio_5": 1.4,
                    "macd": {"dif": 0.2, "dea": 0.1, "bar": 0.2},
                    "boll": {"position": "中轨上方"},
                    "kdj": {"j": 70},
                    "rsi": {"rsi6": 58, "rsi24": 54},
                },
                "technical_trend": {
                    "rating": "技术趋势偏强",
                    "score": 4,
                    "windows": [
                        {"days": 20, "return_pct": 6},
                        {"days": 60, "return_pct": 12},
                        {"days": 120, "return_pct": 18},
                        {"days": 250, "return_pct": 24},
                    ],
                },
                "source_errors": [],
            }
        )

        horizons = result["horizon_scores"]

        self.assertEqual(list(horizons), ["short_term", "medium_term", "long_term"])
        self.assertEqual(horizons["short_term"]["label"], "短期")
        self.assertEqual(horizons["medium_term"]["label"], "中期")
        self.assertEqual(horizons["long_term"]["label"], "长期")
        for horizon in horizons.values():
            self.assertIsInstance(horizon["score"], int)
            self.assertIn(horizon["signal"], ["强买", "买入偏向", "观望", "卖出偏向", "强卖/回避"])
            self.assertTrue(horizon["parts"])

    def test_buy_signal_scorer_applies_active_review_memory_to_horizon_weights(self):
        scorer = load_signal_scorer()
        item = {
            "code": "002466",
            "name": "",
            "valuation": {"市盈率-动态": 24},
            "metrics": [
                {"label": "ROE", "value": 12},
                {"label": "营收增长", "value": 12},
                {"label": "净利润增长", "value": 14},
                {"label": "资产负债率", "value": 40},
                {"label": "每股经营现金流", "value": 0.5},
                {"label": "经营现金流/净利润", "value": 0.8},
            ],
            "technical": {
                "trade_date": "2026-06-12",
                "volume_ratio_5": 1.4,
                "macd": {"dif": 0.2, "dea": 0.1, "bar": 0.2},
                "boll": {"position": "中轨上方"},
                "kdj": {"j": 70},
                "rsi": {"rsi6": 58, "rsi24": 54},
            },
            "technical_trend": {
                "rating": "技术趋势偏强",
                "score": 4,
                "windows": [
                    {"days": 20, "return_pct": 6},
                    {"days": 60, "return_pct": 12},
                    {"days": 120, "return_pct": 18},
                    {"days": 250, "return_pct": 24},
                ],
            },
            "source_errors": [],
        }
        memory = {
            "version": 1,
            "active_adjustments": [
                {
                    "id": "macd-kdj-overheat-short-term",
                    "status": "active",
                    "scope": {"horizons": ["short_term"], "regimes": ["trend"]},
                    "component_weight_multipliers": {"timing": 0.5},
                    "score_bias": -3,
                    "reason": "历史复盘显示趋势行情里短期择时过度奖励 MACD/KDJ 共振。",
                    "evidence": {"sample_count": 12, "hit_rate_delta_pct": -18.5},
                }
            ],
        }

        baseline = scorer.score_item(item, strategy_memory={"version": 1, "active_adjustments": []})
        adjusted = scorer.score_item(item, strategy_memory=memory)

        baseline_short = baseline["horizon_scores"]["short_term"]
        adjusted_short = adjusted["horizon_scores"]["short_term"]
        baseline_timing = next(part for part in baseline_short["parts"] if part["module"] == "短期择时")
        adjusted_timing = next(part for part in adjusted_short["parts"] if part["module"] == "短期择时")

        self.assertAlmostEqual(adjusted_timing["points"], baseline_timing["points"] * 0.5)
        self.assertLess(adjusted_short["score"], baseline_short["score"])
        self.assertIn("复盘 macd-kdj-overheat-short-term 权重 x0.5", adjusted_timing["reason"])
        self.assertTrue(any(part["module"] == "短期复盘校准" and part["points"] == -3 for part in adjusted_short["parts"]))
        self.assertEqual(adjusted["horizon_scores"]["medium_term"]["score"], baseline["horizon_scores"]["medium_term"]["score"])
        self.assertEqual(adjusted["strategy_adjustments"][0]["id"], "macd-kdj-overheat-short-term")
        markdown = scorer.render_markdown([adjusted])
        self.assertIn("### 复盘与自学习", markdown)
        self.assertIn("短期：macd-kdj-overheat-short-term", markdown)

    def test_buy_signal_scorer_can_neutralize_scoped_sell_avoid_signal_to_watch(self):
        scorer = load_signal_scorer()
        item = {
            "code": "002466",
            "name": "",
            "valuation": {"市盈率-动态": -1},
            "metrics": [
                {"label": "ROE", "value": 2},
                {"label": "营收增长", "value": -12},
                {"label": "净利润增长", "value": -18},
                {"label": "资产负债率", "value": 82},
                {"label": "每股经营现金流", "value": -0.2},
                {"label": "经营现金流/净利润", "value": 0.2},
            ],
            "technical": {
                "trade_date": "2026-06-12",
                "volume_ratio_5": 0.6,
                "macd": {"dif": -0.4, "dea": -0.2, "bar": -0.3},
                "boll": {"position": "中轨下方"},
                "kdj": {"j": 45},
                "rsi": {"rsi6": 42, "rsi24": 45},
            },
            "technical_trend": {
                "rating": "技术趋势偏弱",
                "score": -5,
                "windows": [
                    {"days": 20, "return_pct": -8},
                    {"days": 60, "return_pct": -16},
                    {"days": 120, "return_pct": -24},
                    {"days": 250, "return_pct": -32},
                ],
            },
            "strategy_factors": {
                "market_refined_regime": "market_bear_continuation|bear_continuation",
            },
            "source_errors": [],
        }
        memory = {
            "version": 1,
            "active_adjustments": [
                {
                    "id": "neutralize-sell-avoid-market-bear-continuation-bear-continuation-medium-20",
                    "status": "active",
                    "scope": {
                        "horizons": ["medium_term"],
                        "signal_side": "sell_avoid",
                        "factors": {
                            "market_refined_regime": "market_bear_continuation|bear_continuation",
                        },
                    },
                    "score_adjustment_mode": "neutralize_to_watch",
                    "target_score_boundary": -14,
                    "reason": "研究候选：弱势延续交叉状态下，中期卖出/回避信号容易误杀反弹。",
                }
            ],
        }

        baseline = scorer.score_item(item, strategy_memory={"version": 1, "active_adjustments": []})
        adjusted = scorer.score_item(item, strategy_memory=memory)
        mismatched = scorer.score_item(
            {**item, "strategy_factors": {"market_refined_regime": "market_range|bear_continuation"}},
            strategy_memory=memory,
        )

        self.assertLessEqual(baseline["horizon_scores"]["medium_term"]["score"], -15)
        self.assertEqual(adjusted["horizon_scores"]["medium_term"]["score"], -14)
        self.assertEqual(adjusted["horizon_scores"]["medium_term"]["signal"], "观望")
        self.assertTrue(
            any(part["module"] == "中期复盘观察降级" for part in adjusted["horizon_scores"]["medium_term"]["parts"])
        )
        self.assertEqual(adjusted["strategy_adjustments"][0]["id"], memory["active_adjustments"][0]["id"])
        self.assertEqual(
            mismatched["horizon_scores"]["medium_term"]["score"],
            baseline["horizon_scores"]["medium_term"]["score"],
        )
        self.assertEqual(mismatched["strategy_adjustments"], [])

    def test_build_persist_sql_includes_daily_report_upsert(self):
        result = {
            "code": "002466",
            "name": "",
            "score": 5,
            "signal": "观望",
            "confidence": "低",
            "regime": "range",
            "advice": "接近中性，当前更适合观察。",
            "horizon_scores": {
                "short_term": {"label": "短期", "score": -8, "signal": "观望"},
                "medium_term": {"label": "中期", "score": 6, "signal": "观望"},
                "long_term": {"label": "长期", "score": 18, "signal": "买入偏向"},
            },
            "parts": [{"module": "长期趋势", "points": 4, "reason": "测试"}],
            "source_errors": [],
            "raw": {
                "code": "002466",
                "name": "",
                "industry": "",
                "listed_at": "",
                "report_date": "2026-03-31",
                "overview": {},
                "technical": {
                    "trade_date": "2026-06-12",
                    "latest_close": 62.5,
                    "latest_volume": 990333.98,
                    "latest_amount": 6140893986,
                    "turnover_rate": 6.71,
                    "avg_volume_5": 787629.08,
                    "avg_volume_20": 610290.05,
                    "volume_ratio_5": 1.257,
                    "macd": {"dif": -2.12, "dea": -1.93, "bar": -0.39},
                    "boll": {"mid": 63.17, "upper": 70.05, "lower": 56.29, "position": "中轨下方"},
                    "kdj": {"k": 57.32, "d": 37.2, "j": 97.58},
                    "rsi": {"rsi6": 57.77, "rsi12": 47.36, "rsi24": 48.21},
                },
                "technical_trend": {
                    "rating": "技术趋势震荡",
                    "score": 1,
                    "conclusion": "趋势震荡。",
                    "signals": ["测试长期趋势"],
                    "windows": [
                        {
                            "days": 20,
                            "return_pct": -9.56,
                            "close_vs_ma_pct": -1.06,
                            "macd_positive_ratio": 0,
                            "boll_mid_above_ratio": 0,
                            "rsi24": 48.21,
                            "volume_ratio_20": 1.62,
                        }
                    ],
                },
                "metrics": [{"label": "ROE", "value": 4.31}],
                "strengths": [],
                "risks": [],
            },
        }

        sql = mysql_sink.build_persist_sql([result], "qfq")

        self.assertIn("START TRANSACTION", sql)
        self.assertIn("INSERT INTO stock_daily_report", sql)
        self.assertIn("INSERT INTO stock_daily_signal_score", sql)
        self.assertIn("short_term_score", sql)
        self.assertIn("medium_term_score", sql)
        self.assertIn("long_term_score", sql)
        self.assertIn("horizon_scores_json", sql)
        self.assertIn("COMMIT", sql)

    def test_signal_accuracy_creates_outcome_specs_for_each_horizon_window(self):
        result = {
            "code": "002466",
            "score": 5,
            "signal": "观望",
            "horizon_scores": {
                "short_term": {"score": -30, "signal": "卖出偏向"},
                "medium_term": {"score": 11, "signal": "观望"},
                "long_term": {"score": 19, "signal": "买入偏向"},
            },
            "raw": {
                "technical": {
                    "trade_date": "2026-06-12",
                    "latest_close": 62.5,
                }
            },
        }

        specs = signal_accuracy.outcome_specs(result, "qfq")

        self.assertEqual(
            [(spec["horizon"], spec["window_days"]) for spec in specs],
            [
                ("short_term", 1),
                ("short_term", 3),
                ("short_term", 5),
                ("medium_term", 10),
                ("medium_term", 20),
                ("long_term", 60),
                ("long_term", 120),
            ],
        )
        self.assertEqual(specs[0]["signal_score"], -30)
        self.assertEqual(specs[0]["signal_label"], "卖出偏向")
        self.assertEqual(specs[-1]["signal_score"], 19)
        self.assertEqual(specs[-1]["signal_close"], 62.5)

    def test_signal_accuracy_classifies_directional_hits(self):
        self.assertTrue(signal_accuracy.classify_hit("买入偏向", 1.2))
        self.assertFalse(signal_accuracy.classify_hit("买入偏向", -0.1))
        self.assertTrue(signal_accuracy.classify_hit("卖出偏向", -2.4))
        self.assertFalse(signal_accuracy.classify_hit("强卖/回避", 0.5))
        self.assertIsNone(signal_accuracy.classify_hit("观望", 3.0))

    def test_generate_final_report_contains_accuracy_summary(self):
        result = {
            "code": "002466",
            "name": "",
            "score": 5,
            "signal": "观望",
            "confidence": "低",
            "regime": "range",
            "advice": "接近中性，当前更适合观察。",
            "horizon_scores": {
                "short_term": {"label": "短期", "score": -8, "signal": "观望"},
                "medium_term": {"label": "中期", "score": 6, "signal": "观望"},
                "long_term": {"label": "长期", "score": 18, "signal": "买入偏向"},
            },
            "evaluation_summary": {
                "short_term": {
                    5: {
                        "sample_count": 12,
                        "directional_count": 10,
                        "hit_rate_pct": 60.0,
                        "avg_return_pct": 1.25,
                        "avg_excess_return_pct": None,
                        "avg_max_drawdown_pct": -2.1,
                        "avg_max_runup_pct": 4.2,
                    }
                },
                "medium_term": {},
                "long_term": {},
            },
            "parts": [],
            "source_errors": [],
            "raw": {
                "code": "002466",
                "name": "",
                "report_date": "2026-03-31",
                "technical": {"trade_date": "2026-06-12", "latest_close": 62.5},
                "technical_trend": {"rating": "技术趋势震荡", "score": 1, "conclusion": "趋势震荡。"},
                "metrics": [{"label": "ROE", "value": 4.31}],
                "strengths": [],
                "risks": [],
            },
        }

        _, report_text, report_json = mysql_sink.generate_final_report(result)

        self.assertIn("## 历史验证", report_text)
        self.assertIn("短期 5日：高强度样本 12，命中率 60.00%", report_text)
        self.assertIn("平均收益 1.25%", report_text)
        self.assertEqual(report_json["evaluation_summary"]["short_term"][5]["sample_count"], 12)

    def test_fetch_evaluation_summaries_only_counts_high_intensity_signals(self):
        args = SimpleNamespace(password="", database="stock_analysis_test", mysql_bin="mysql", user="root", host="", port=None)
        captured = {}

        def fake_query_mysql(sql, query_args, use_database):
            captured["sql"] = sql
            self.assertIs(query_args, args)
            self.assertTrue(use_database)
            return "002466\tshort_term\t5\t12\t12\t60.0\t1.25\t-2.1\t4.2\n"

        with patch.object(mysql_sink, "query_mysql", side_effect=fake_query_mysql):
            summary = mysql_sink.fetch_evaluation_summaries(args, ["002466"], "qfq")

        self.assertIn("(signal_score > 70 OR signal_score < -70)", captured["sql"])
        self.assertEqual(summary["002466"]["short_term"][5]["sample_count"], 12)
        self.assertEqual(summary["002466"]["short_term"][5]["hit_rate_pct"], 60.0)

    def test_build_persist_sql_includes_signal_outcome_upserts(self):
        result = {
            "code": "002466",
            "name": "",
            "score": 5,
            "signal": "观望",
            "confidence": "低",
            "regime": "range",
            "advice": "接近中性，当前更适合观察。",
            "horizon_scores": {
                "short_term": {"label": "短期", "score": -8, "signal": "观望"},
                "medium_term": {"label": "中期", "score": 6, "signal": "观望"},
                "long_term": {"label": "长期", "score": 18, "signal": "买入偏向"},
            },
            "parts": [],
            "source_errors": [],
            "raw": {
                "code": "002466",
                "name": "",
                "industry": "",
                "listed_at": "",
                "report_date": "2026-03-31",
                "overview": {},
                "technical": {"trade_date": "2026-06-12", "latest_close": 62.5},
                "technical_trend": {"rating": "技术趋势震荡", "score": 1, "windows": []},
                "metrics": [],
                "strengths": [],
                "risks": [],
            },
        }

        sql = mysql_sink.build_persist_sql([result], "qfq")

        self.assertIn("INSERT INTO stock_signal_outcome", sql)
        self.assertIn("short_term", sql)
        self.assertIn("window_days", sql)
        self.assertIn("raw_signal_json", sql)

    def test_build_ai_etf_portfolio_selects_ten_equal_weight_initial_holdings(self):
        results = [make_ai_etf_result(index) for index in range(12)]

        portfolio = mysql_sink.build_ai_etf_portfolio(results, "qfq")

        self.assertEqual(portfolio["portfolioName"], "AI_RECOMMENDED_ETF")
        self.assertEqual(portfolio["tradeDate"], "2026-06-12")
        self.assertEqual(len(portfolio["holdings"]), 10)
        self.assertEqual(sum(holding["targetWeightPct"] for holding in portfolio["holdings"]), 100.0)
        self.assertTrue(all(holding["targetWeightPct"] == 10.0 for holding in portfolio["holdings"]))
        self.assertTrue(all(holding["action"] == "buy" for holding in portfolio["holdings"]))
        self.assertEqual(portfolio["holdings"][0]["stockCode"], "000000")
        self.assertIn("首次", portfolio["selectionRule"])

    def test_build_ai_etf_portfolio_marks_rebalance_actions_from_previous_holdings(self):
        results = [make_ai_etf_result(index) for index in range(12)]
        previous_holdings = [
            {"stock_code": "000000", "target_weight_pct": 8, "reference_price": 9, "simulated_quantity": 8000},
            {"stock_code": "000001", "target_weight_pct": 12, "reference_price": 10, "simulated_quantity": 12000},
            {"stock_code": "999999", "target_weight_pct": 10, "reference_price": 20, "simulated_quantity": 5000},
        ]

        portfolio = mysql_sink.build_ai_etf_portfolio(results, "qfq", previous_holdings=previous_holdings)
        actions = {item["stockCode"]: item["action"] for item in portfolio["rebalance"]}

        self.assertEqual(actions["999999"], "sell")
        self.assertIn(actions["000000"], {"increase", "hold"})
        self.assertIn(actions["000001"], {"reduce", "hold"})
        self.assertTrue(any(item["action"] == "buy" for item in portfolio["rebalance"]))
        self.assertTrue(all("weightDeltaPct" in item for item in portfolio["rebalance"]))

    def test_build_persist_sql_includes_ai_etf_upserts(self):
        results = [make_ai_etf_result(index) for index in range(10)]

        sql = mysql_sink.build_persist_sql(results, "qfq")

        self.assertIn("INSERT INTO stock_ai_etf_snapshot", sql)
        self.assertIn("INSERT INTO stock_ai_etf_holding", sql)
        self.assertIn("INSERT INTO stock_ai_etf_trade", sql)
        self.assertIn("portfolio_name", sql)

    def test_refresh_signal_outcomes_sql_uses_future_trading_day_window(self):
        sql = mysql_sink.refresh_signal_outcomes_sql()

        self.assertIn("ROW_NUMBER() OVER", sql)
        self.assertIn("stock_signal_outcome", sql)
        self.assertIn("stock_daily_quote", sql)
        self.assertIn("max_drawdown_pct", sql)

    def test_refresh_signal_outcomes_sql_recomputes_matured_rows(self):
        sql = mysql_sink.refresh_signal_outcomes_sql()

        self.assertNotIn("outcome_inner.status = 'pending'", sql)
        self.assertIn("outcome_inner.signal_close IS NOT NULL", sql)

    def test_upload_results_posts_json_with_bearer_token(self):
        args = SimpleNamespace(ingest_url="https://stock.example.com/api/ingest/daily-analysis", ingest_token="secret")
        result = {
            "code": "002466",
            "score": 5,
            "signal": "观望",
            "raw": {"technical": {"trade_date": "2026-06-12"}},
        }
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true,"persistedCount":1}'

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = mysql_sink.upload_results([result], args, "qfq")

        self.assertEqual(captured["url"], args.ingest_url)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(captured["payload"], {"adjustType": "qfq", "results": [result], "aiEtf": None})
        self.assertEqual(captured["timeout"], 60)
        self.assertEqual(response["persistedCount"], 1)

    def test_upload_results_posts_ai_etf_payload_when_available(self):
        args = SimpleNamespace(ingest_url="https://stock.example.com/api/ingest/daily-analysis", ingest_token="secret")
        results = [make_ai_etf_result(index) for index in range(10)]
        ai_etf = mysql_sink.build_ai_etf_portfolio(results, "qfq")
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true,"persistedCount":10}'

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mysql_sink.upload_results(results, args, "qfq", ai_etf=ai_etf)

        self.assertEqual(captured["payload"]["aiEtf"]["portfolioName"], "AI_RECOMMENDED_ETF")
        self.assertEqual(len(captured["payload"]["aiEtf"]["holdings"]), 10)
        self.assertEqual(captured["payload"]["aiEtf"]["holdings"][0]["action"], "buy")

    def test_upload_results_uses_default_ingest_token(self):
        args = SimpleNamespace(ingest_url="https://stock.example.com/api/ingest/daily-analysis", ingest_token="")
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true}'

        def fake_urlopen(request, timeout):
            captured["headers"] = dict(request.header_items())
            return FakeResponse()

        with patch.dict("os.environ", {}, clear=True), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mysql_sink.upload_results([], args, "qfq")

        self.assertEqual(
            captured["headers"]["Authorization"],
            "Bearer stock-analysis-ingest-2026-6f8c2d91b7a443e0",
        )

    def test_upload_results_reports_http_error_body(self):
        args = SimpleNamespace(ingest_url="https://stock.example.com/api/ingest/daily-analysis", ingest_token="bad")

        class FakeHttpError(mysql_sink.urllib.error.HTTPError):
            def read(self):
                return b'{"error":"unauthorized"}'

        error = FakeHttpError(args.ingest_url, 401, "Unauthorized", {}, None)

        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "401.*unauthorized"):
                mysql_sink.upload_results([], args, "qfq")

    def test_main_uses_ingest_url_instead_of_local_mysql(self):
        result = {
            "code": "002466",
            "score": 5,
            "signal": "观望",
            "confidence": "低",
            "raw": {"technical": {"trade_date": "2026-06-12"}},
        }
        scorer = SimpleNamespace(score_item=lambda item: result)

        with (
            patch.object(mysql_sink, "load_scorer", return_value=scorer),
            patch.object(mysql_sink, "fetch_analysis_items", return_value=[{"code": "002466"}]),
            patch.object(mysql_sink, "ensure_schema") as ensure_schema_mock,
            patch.object(mysql_sink, "persist_results") as persist_mock,
            patch.object(mysql_sink, "upload_results", return_value={"ok": True}) as upload_mock,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            exit_code = mysql_sink.main(
                [
                    "002466",
                    "--ingest-url",
                    "https://stock.example.com/api/ingest/daily-analysis",
                    "--ingest-token",
                    "secret",
                    "--quiet",
                ]
            )

        self.assertEqual(exit_code, 0)
        ensure_schema_mock.assert_not_called()
        persist_mock.assert_not_called()
        upload_mock.assert_called_once()
        uploaded_results, uploaded_args, adjust_type = upload_mock.call_args.args
        self.assertEqual(uploaded_results, [result])
        self.assertEqual(uploaded_args.ingest_token, "secret")
        self.assertEqual(adjust_type, "qfq")

    def test_main_uploads_results_in_batches_when_batch_size_is_set(self):
        items = [{"code": f"{index:06d}"} for index in range(25)]

        def score_item(item):
            return {
                "code": item["code"],
                "score": 5,
                "signal": "观望",
                "confidence": "低",
                "raw": {"technical": {"trade_date": "2026-06-12"}},
            }

        scorer = SimpleNamespace(score_item=score_item)

        def fetch_batch(args):
            return [{"code": code} for code in args.resolved_codes]

        with (
            patch.object(mysql_sink, "load_scorer", return_value=scorer),
            patch.object(mysql_sink.sfa, "resolve_input_codes", return_value=[item["code"] for item in items]),
            patch.object(mysql_sink, "fetch_analysis_items", side_effect=fetch_batch),
            patch.object(mysql_sink, "ensure_schema") as ensure_schema_mock,
            patch.object(mysql_sink, "persist_results") as persist_mock,
            patch.object(mysql_sink, "upload_results", return_value={"ok": True}) as upload_mock,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            exit_code = mysql_sink.main(
                [
                    "--ingest-url",
                    "https://stock.example.com/api/ingest/daily-analysis",
                    "--batch-size",
                    "10",
                    "--quiet",
                ]
            )

        self.assertEqual(exit_code, 0)
        ensure_schema_mock.assert_not_called()
        persist_mock.assert_not_called()
        uploaded_batches = [call.args[0] for call in upload_mock.call_args_list]
        self.assertEqual([len(batch) for batch in uploaded_batches], [10, 10, 5])
        self.assertEqual(uploaded_batches[0][0]["code"], "000000")
        self.assertEqual(uploaded_batches[-1][-1]["code"], "000024")


if __name__ == "__main__":
    unittest.main()
    load_codes_from_file,
