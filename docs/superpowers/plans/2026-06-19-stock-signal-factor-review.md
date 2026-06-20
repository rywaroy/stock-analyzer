# Stock Signal Factor Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the local no-upload backtest into a factor attribution review that separates train/validation evidence and produces a Chinese optimization research report.

**Architecture:** Keep all work in `research_signal_backtest.py` and its existing unit tests. Each scored historical signal gets deterministic factor tags from the visible technical snapshot and horizon scores; summaries group outcomes by factor, horizon, window, and train/validation period; Markdown rendering adds factor review and candidate rule sections without changing the active scorer.

**Tech Stack:** Python 3.12, existing technical JSON from `stock_fundamental_analysis.py`, existing scorer result format, `unittest`.

---

### Task 1: Factor Tags

**Files:**
- Modify: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write failing tests**

Add a test for `extract_factor_tags(result)` using a scorer-like payload with MACD, BOLL, KDJ, RSI, volume, trend windows, and horizon scores.

- [x] **Step 2: Run the focused test**

Run: `uv run --python 3.12 --with-requirements requirements.txt python -m unittest tests.test_stock_fundamental_analysis.StockFundamentalAnalysisTest.test_research_backtest_extracts_factor_tags_from_visible_snapshot -v`

Expected: FAIL until the helper exists.

- [x] **Step 3: Implement factor extraction**

Add deterministic labels for MACD state, BOLL position, KDJ-J zone, RSI6 zone, volume state, 20/60/120/250 day trend buckets, and horizon alignment.

- [x] **Step 4: Run the focused test**

Expected: PASS.

### Task 2: Train/Validation And Factor Summary

**Files:**
- Modify: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write failing tests**

Add a test that outcomes with `signal_trade_date` before `validation_from` are grouped into train, and later outcomes into validation. Confirm factor summaries include hit rate and average return per factor value.

- [x] **Step 2: Run the focused test**

Expected: FAIL until summary accepts `validation_from`.

- [x] **Step 3: Implement summary grouping**

Add `period_for_date()`, `summarize_outcomes(..., validation_from=None)`, `by_period_horizon_window`, and `by_factor`.

- [x] **Step 4: Run the focused test**

Expected: PASS.

### Task 3: Factor Review Report And CLI Options

**Files:**
- Modify: `research_signal_backtest.py`
- Modify: `tests/test_stock_fundamental_analysis.py`

- [x] **Step 1: Write failing tests**

Add assertions that report output contains `训练/验证对照`, `因子归因复盘`, and `候选优化规则`; add parser assertions for `--validation-from`.

- [x] **Step 2: Run the focused tests**

Expected: FAIL until renderer and parser are updated.

- [x] **Step 3: Implement renderer and CLI metadata**

Expose `--validation-from`; default it to the final third of the backtest interval. Render train/validation tables and factor observations. Keep candidate rules as prose only.

- [x] **Step 4: Run focused tests and full tests**

Expected: PASS.

### Task 4: Regenerate Research Reports

**Files:**
- Modify: `docs/research/stock-signal-backtest-smoke.md`
- Modify: `docs/research/stock-signal-backtest-2025-06-19-to-2026-06-19.md`

- [x] **Step 1: Run smoke report**

Run the 3-stock smoke command with `--validation-from 2026-03-01`.

- [x] **Step 2: Run full one-year report**

Run the 110-stock one-year command with `--validation-from 2026-02-19`.

- [x] **Step 3: Inspect report excerpts**

Confirm the generated reports include factor review and do not claim active strategy changes.

---

## Self-Review

- Spec coverage: covers factor attribution, train/validation split, report output, and no active rule mutation.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: helper names and CLI option names are consistent.
