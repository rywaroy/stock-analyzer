# Stock Signal Backtest Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, no-upload research runner that backtests the existing A-share signal scorer across the stock watchlist and writes a Chinese research report.

**Architecture:** Add a standalone `research_signal_backtest.py` module that reuses `stock_fundamental_analysis.py` technical calculations and the existing scorer. The runner fetches each stock's historical daily data once, slices the series by signal date to avoid future leakage, scores each slice, evaluates later returns by horizon windows, and renders a Markdown report under `docs/research/`.

**Tech Stack:** Python 3.12, AKShare, existing `stock_fundamental_analysis.py`, existing `.codex/skills/stock-buy-signal-analysis/scripts/analyze_stock.py`, `unittest`.

---

### Task 1: No-Future Data Slicing And Outcome Evaluation

**Files:**
- Create: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write the failing test**

Add tests that call `build_scoring_item_from_series()` and `evaluate_result_windows()` with synthetic daily data. The tests assert the scoring item uses the requested signal date as its latest technical snapshot, and future returns use only rows after the signal date.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 --with-requirements requirements.txt python -m unittest tests.test_stock_fundamental_analysis.StockFundamentalAnalysisTest.test_research_backtest_builds_scoring_item_without_future_rows -v`

Expected: FAIL because `research_signal_backtest` does not exist yet.

- [x] **Step 3: Write minimal implementation**

Create focused helpers:

```python
def build_scoring_item_from_series(code, name, series, signal_index):
    visible = series[: signal_index + 1]
    snapshot = sfa.technical_snapshot_from_series(visible)
    trend = sfa.calculate_technical_trend(visible)
    return {
        "code": code,
        "name": name,
        "technical": sfa.technical_to_jsonable(snapshot),
        "technical_trend": sfa.technical_trend_to_jsonable(trend),
        "metrics": [],
        "valuation": {},
        "source_errors": ["历史研究模式未使用实时估值和财务指标，避免未来函数"],
    }
```

Evaluate future windows by positional future trading days, not calendar days.

- [x] **Step 4: Run test to verify it passes**

Run the same targeted unittest. Expected: PASS.

### Task 2: Aggregation And Markdown Research Report

**Files:**
- Modify: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write failing tests**

Add tests for `summarize_outcomes()` and `render_markdown_report()`: summary must include horizon/window sample counts, directional hit rate, average return, average drawdown/runup, and the report must explicitly state no active scoring rules were changed.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 --with-requirements requirements.txt python -m unittest tests.test_stock_fundamental_analysis.StockFundamentalAnalysisTest.test_research_backtest_summarizes_outcomes_and_renders_chinese_report -v`

Expected: FAIL because aggregation/report functions are not implemented.

- [x] **Step 3: Implement aggregation/report**

Group outcomes by horizon and window. Track all matured samples, directional samples, high-intensity samples where `abs(signal_score) >= 70`, hit rate, average return, average max drawdown, and average max runup. Render Chinese Markdown with sections for scope, data hygiene, horizon accuracy, regime observations, candidate rule observations, and next steps.

- [x] **Step 4: Run test to verify it passes**

Run the targeted unittest. Expected: PASS.

### Task 3: CLI Runner For The Long Local Job

**Files:**
- Modify: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write failing tests**

Add tests for CLI argument parsing and default output path. Confirm `--max-codes`, `--sample-step`, `--from-date`, `--to-date`, and `--output` are accepted.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 --with-requirements requirements.txt python -m unittest tests.test_stock_fundamental_analysis.StockFundamentalAnalysisTest.test_research_backtest_parse_args_accepts_long_task_options -v`

Expected: FAIL until parser exists.

- [x] **Step 3: Implement CLI**

Add `main()` that loads codes from `stock.md`, fetches AKShare daily data once per stock, scores local slices, aggregates outcomes, and writes the report. The CLI must never call MySQL or the production ingest endpoint.

- [x] **Step 4: Run test to verify it passes**

Run targeted unittest. Expected: PASS.

### Task 4: Verification And Smoke Run

**Files:**
- Modify: `docs/research/stock-signal-backtest-*.md`

- [x] **Step 1: Run focused tests**

Run: `uv run --python 3.12 --with-requirements requirements.txt python -m unittest tests.test_stock_fundamental_analysis -v`

Expected: PASS.

- [x] **Step 2: Run a small smoke research job**

Run: `uv run --python 3.12 --with-requirements requirements.txt python research_signal_backtest.py --from-date 2026-01-01 --to-date 2026-03-31 --max-codes 3 --sample-step 5 --output docs/research/stock-signal-backtest-smoke.md`

Expected: exits 0 and writes a Chinese report. Network/data-source failures should be visible in the report instead of hidden.

- [x] **Step 3: Start or document the long run**

If smoke passes, start the full job or provide the exact command for the one-year 110-stock run:

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python research_signal_backtest.py \
  --from-date 2025-06-19 --to-date 2026-06-19 \
  --output docs/research/stock-signal-backtest-2025-06-19-to-2026-06-19.md
```

---

## Self-Review

- Spec coverage: covers local historical scoring, no production upload, no direct active rule mutation, Chinese report, and long-run readiness.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: helper names and CLI options are consistent across tasks.
