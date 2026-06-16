import importlib.util
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import stock_fundamental_analysis as sfa
import save_daily_to_mysql as mysql_sink
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


def load_signal_scorer():
    spec = importlib.util.spec_from_file_location("stock_buy_signal_scorer", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载评分脚本：{SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StockFundamentalAnalysisTest(unittest.TestCase):
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
        self.assertIn("## 数据提醒", report_text)
        self.assertEqual(report_json["signal"], "观望")
        self.assertEqual(report_json["horizon_scores"]["long_term"]["score"], 18)

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


if __name__ == "__main__":
    unittest.main()
    load_codes_from_file,
