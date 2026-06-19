---
name: stock-buy-signal-analysis
description: Use when analyzing A-share stocks in this project to decide buy/sell/watch signals, persist the analysis to MySQL, refresh historical signal accuracy, produce horizon scores, or build and track an AI-recommended 10-stock ETF portfolio.
---

# Stock Buy Signal Analysis

## Overview

Act as a senior stock analyst, but keep the decision data-driven. The default workflow is persistent: fetch stock fundamentals and technical trend data, write the daily snapshot to MySQL, refresh historical signal accuracy, build/update the AI recommended ETF portfolio, then read the final report. Scores use `-100..100` where positive means buy bias, negative means sell bias, and near zero means watch.

Always separate the time horizon:

- 短期：择时主导，重点看 MACD、BOLL、KDJ、RSI、成交量和 20 日趋势。
- 中期：趋势主导，重点看 20/60/120 日趋势、均线结构和基本面支撑。
- 长期：质量主导，重点看 ROE、成长、现金流、估值和 120/250 日趋势。
- 总分：保留为跨周期综合判断，不替代三档评分。

This skill is local to this project. Always work from the project root: `/Users/zhangzhihao/Documents/GitHub/stock-analyzer`.

## Required Workflow

1. Run the full MySQL workflow. With no explicit code, it reads `stock.md`; with explicit codes, pass them as positional args.

`stock.md` uses one `股票代码-股票名称` entry per line, for example `002466-天齐锂业`. When reading `stock.md`, parse each non-empty, non-comment line first: strip list markers and inline comments, split on the first `-`, normalize the left side to the six-digit stock code, and pass only that code into the analysis workflow.

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py --user root
```

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root
```

For honest historical backfill, pass an as-of date or a date range. The scorer must only use data visible at that as-of date:

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root --as-of-date 2026-03-15
```

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root \
  --backfill-from 2026-03-15 --backfill-to 2026-03-20
```

In historical mode, technical daily data is cut off at the as-of date. Do not use today's realtime spot/valuation snapshot or financial indicator endpoint to fill historical fundamentals; the workflow records those omissions in `source_errors_json` and lowers confidence instead.

For online reporting, post the analysis results to the production ingest endpoint:

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py \
  --ingest-url "http://stock.zzh.cool/api/ingest/daily-analysis"
```

When `--ingest-url` is provided, the local workflow still fetches AKShare data and scores the stocks, then uploads structured results to the online Express service. The online service is responsible for MySQL upsert, historical signal accuracy refresh, and final report regeneration.

For Codex automation, schedule this skill every Monday to Friday at 06:00 Asia/Shanghai. The automation should run the full workflow and use the production ingest endpoint above for online reporting.

Automation command:

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py \
  --ingest-url "http://stock.zzh.cool/api/ingest/daily-analysis"
```

If Eastmoney `push2` is unavailable in the current network, first run the same command with `--preflight` to verify the environment and production service. For a production run that should bypass Eastmoney immediately and use fallback sources for available quote/name fields, add `--skip-eastmoney`. Keep source errors visible because fallback data does not replace PE/PB, market cap, share capital, industry, or listed date.

2. Build or update the AI recommended ETF after the stock analysis has been persisted.

Use the latest saved `stock_daily_signal_score` rows for the current run or latest trade date as the candidate pool. Recommend exactly 10 stocks when at least 10 valid candidates exist. If there is no prior AI ETF portfolio or no usable portfolio performance history, pick 10 candidates from the current analysis and assign each `10%` weight. If prior portfolio/performance data exists, choose holdings from the candidate pool using short-term, medium-term, and long-term scores, with ETF-style stability:

- Prefer stocks with positive medium-term and long-term scores, acceptable short-term timing, non-low confidence, and no critical missing data in `source_errors_json`.
- Rank candidates with a horizon blend suitable for a simulated ETF: short-term timing `20%`, medium-term trend `35%`, long-term quality/trend `35%`, overall score `10%`.
- Keep existing holdings that still pass the filter to reduce churn; replace holdings whose medium/long scores deteriorate, confidence falls to low, or source errors make the thesis unreliable.
- When performance history exists, let weights reflect conviction and realized/unrealized behavior, but keep position sizing diversified. Use `5%..15%` per stock unless the user asks for another constraint, and make weights sum to `100%`.
- When a holding changes, explicitly mark the rebalance action. Use `buy` for new holdings, `sell` for removed holdings, `increase` for higher target weight, `reduce` for lower target weight, and `hold` for unchanged target weight. Include previous weight, new weight, weight delta, reference price, and the reason for every non-hold action.
- When fewer than 10 valid candidates exist, say so clearly and do not invent stocks outside the analyzed universe unless the user explicitly expands the universe.

Persist the recommendation to MySQL. If the portfolio tables or ingest endpoint are not implemented yet, add them before claiming the ETF workflow is complete. Keep the schema capable of storing:

- portfolio snapshot: portfolio name such as `AI_RECOMMENDED_ETF`, trade date, stock code/name, weight, action (`buy`/`hold`/`reduce`/`sell`/`watch`), all four scores, signal labels, confidence, rationale, and source errors.
- trade/price tracking: simulated buy price, sell price, reference close, trade date, virtual quantity or notional amount, realized P&L, unrealized P&L, return percentage, and raw calculation JSON.
- portfolio performance: total notional/NAV, daily return, cumulative return, drawdown, turnover, and benchmark fields if a benchmark is available.

Use the latest saved close price as the simulated buy/sell reference for live recommendations. In historical/as-of mode, use only prices visible at the as-of date; never use future prices to choose holdings. On each later run, refresh open positions with the latest close, close removed holdings at the rebalance close, calculate realized/unrealized profit or loss, and use the result to judge whether the AI recommended ETF is improving.

For VitePress/online dashboard reporting, give the AI recommended ETF a dedicated top-level area instead of burying it inside a single-stock detail page. The ETF view should show current holdings, weight changes, buy/sell/increase/reduce/hold badges, simulated NAV/return, realized and unrealized P&L, rebalance history, and risk concentration. Keep the single-stock pages focused on individual signal explanations, but link each ETF holding back to its stock detail.

3. Read the latest final report from `stock_daily_report`:

```bash
mysql -uroot -D stock_analysis_test \
  -e "SELECT report_text FROM stock_daily_report ORDER BY trade_date DESC, updated_at DESC LIMIT 1"
```

4. Confirm `stock_signal_outcome` has the expected pending or matured rows for the analyzed stock/date when discussing historical validation.
5. Read `source_errors` from the report or `stock_daily_signal_score.source_errors_json`. If a data source failed, say which data is missing and reduce confidence instead of inventing values.
6. Explain the short-term, medium-term, long-term, and overall scores using fundamentals, trend, timing, historical validation, and risk controls.
7. Make a clear call for each score:
   - `>= 50`: strong buy bias
   - `15..49`: buy bias, prefer staged entry
   - `-14..14`: watch
   - `-49..-15`: sell/avoid bias
   - `<= -50`: strong sell/avoid bias

## Analyst Logic

Use the scoring model in `references/scoring-model.md` when you need details. The built-in scorer applies the same model.

Core principles:

- Technical indicators lag price. Treat them as confirmation and risk control, not prophecy.
- In short-term analysis, give more weight to MACD, BOLL position, RSI/KDJ heat, volume confirmation, and the 20-day window.
- In medium-term analysis, give more weight to moving averages, 20/60/120-day returns, MACD persistence, and volume confirmation.
- In long-term analysis, give more weight to fundamentals, 120/250-day trend, MA60/120/250 structure, and cash conversion.
- In range-bound markets, short-term BOLL/RSI/KDJ signals matter more, but they should not override a weak medium/long-term structure.
- In downtrends, negative technical evidence carries more weight than positive oversold signals.
- Fundamentals can support a buy thesis, but poor cash conversion or weak ROE should cap enthusiasm.
- Strong medium/long-term trend plus weak short-term timing usually means "watch for confirmation", not automatic buy.
- Historical validation must be based on saved signal snapshots and later quotes only. Do not recompute old scores with today's data.
- The AI recommended ETF is a simulated portfolio. Treat it as a research and tracking artifact, not an investment product. Its value comes from consistent selection rules, price recording, and honest P&L attribution.

## Output Format

Answer in Chinese with this structure:

```markdown
✅ 结论：一句话说明买/卖/观望和分数

📊 评分：
- 股票：代码/名称
- 总分：X/100，信号：强买 / 买入偏向 / 观望 / 卖出偏向 / 强卖
- 短期：X/100，信号：...
- 中期：X/100，信号：...
- 长期：X/100，信号：...
- 置信度：高 / 中 / 低

🧠 核心依据：
1. 基本面
2. 短期择时
3. 中期趋势
4. 长期质量与趋势
5. 风险点
6. 历史验证：高强度样本数、命中率、平均收益、窗口内回撤/上冲。只使用 `signal_score > 70` 或 `signal_score < -70` 的样本统计准确率。

🛠️ 操作建议：
分别说明短期是否适合试仓/等待，中期是否适合分批，长期是否适合纳入配置观察池。

🧺 AI 推荐 ETF：
- 组合日期：YYYY-MM-DD
- 选股规则：说明是否为首次等权，或基于历史组合表现和三周期评分调仓
- 持仓：10 只股票，列出代码/名称/原权重/新权重/权重变化/动作/参考价格/短中长期分数/选择理由
- 调仓与盈亏：明确列出买入、卖出、加仓、减仓、保留；列出可得的模拟买入价、卖出价、已实现盈亏、未实现盈亏和组合累计收益
- 看板展示：如果输出到 VitePress，应展示在独立的 AI 推荐 ETF 区域，并从持仓链接到个股详情
- 风险提醒：说明集中行业、数据缺失、低置信度、短期过热或趋势破位等风险
```

Avoid guarantees, price targets without data, and investment-advice language. Say "买入偏向/卖出偏向/观察" rather than "一定买/一定卖".

## Tools

- Use `save_daily_to_mysql.py` as the default entrypoint. It performs analysis, schema/migration sync, MySQL upsert, historical accuracy refresh, and final report regeneration.
- Use `scripts/analyze_stock.py` only when the user explicitly asks for no database writes, MySQL is unavailable, or you are debugging raw scoring output.
- Use `stock_fundamental_analysis.py --json` directly only when debugging raw data.
- Use `--json` on the scorer when another script or table needs structured output.

No-database debug example:

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python .codex/skills/stock-buy-signal-analysis/scripts/analyze_stock.py \
  "002466,600519" --json
```
