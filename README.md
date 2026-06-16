# Stock Fundamental Analysis

用 AKShare 批量获取 A 股数据，并为输入的股票代码生成基本面 + 技术面分析报告。

## 功能

- 支持输入一串股票代码：`000001,600519 300750`
- 获取公司概要、行情快照、估值指标和财务指标
- 拉取日线行情并计算成交量、MACD、BOLL、KDJ、RSI
- 统计 20/60/120/250 日技术趋势，并给出技术趋势评级
- 输出每只股票的优势观察、风险观察和综合观察
- 支持 Markdown 报告和 JSON 输出
- 单只股票数据源失败时不中断整批分析

## 运行

推荐用 `uv` 运行，AKShare 和 pandas 对 Python 版本比较敏感，建议使用 Python 3.12：

先在项目根目录创建 `stock.md`，一行一个股票代码：

```text
002466
600519
300750
```

然后直接运行：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py
```

也可以临时在命令行指定股票代码：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py "000001,600519,300750"
```

输出到 Markdown 文件：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py "000001,600519,300750" -o report.md
```

输出 JSON：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py "000001,600519,300750" --json
```

指定财务指标起始年份：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py "000001,600519" --start-year 2020
```

指定技术指标日线窗口和复权方式：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python stock_fundamental_analysis.py "002466" --technical-days 180 --adjust qfq
```

`--adjust` 可选：`none` 不复权、`qfq` 前复权、`hfq` 后复权。
长期趋势和 RSI 预热会至少保留 260 根日线；`--technical-days` 大于 260 时会保留更多历史。

## 写入 MySQL

本地测试库默认是 `stock_analysis_test`，schema 在 `sql/schema.sql`。写入每日数据、评分和最终总结报告：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py --user root
```

`stock-buy-signal-analysis` skill 默认也使用这条完整流程：分析、入库、刷新历史验证、再读取最终报告。

也可以临时指定代码覆盖 `stock.md`：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root
```

按历史日期生成当时可见的技术面快照：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root --as-of-date 2026-03-15
```

批量回填一段历史区间：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py "002466" --user root \
  --backfill-from 2026-03-15 --backfill-to 2026-03-20
```

历史模式只使用 `as-of` 日期及以前的日线数据计算 MACD、BOLL、KDJ、RSI 和趋势；不会用今天的实时行情/估值快照，也不会用无法按历史发布日期还原的实时财务指标接口来补分。这些降级会写入 `source_errors_json`，避免后续数据影响当次判断。回填遇到周末、节假日或停牌导致的重复交易日会跳过。

脚本会先幂等创建库表，再把最新交易日的数据 upsert 到：

- `stock_daily_quote`：日线行情和成交量
- `stock_daily_technical`：MACD、BOLL、KDJ、RSI 等技术指标
- `stock_daily_trend` / `stock_daily_trend_window`：20/60/120/250 日趋势
- `stock_daily_signal_score`：总分、短期/中期/长期 `-100..100` 买卖评分、信号和置信度
- `stock_signal_outcome`：历史预测到期验证结果，按短期/中期/长期和未来交易日窗口记录真实收益、回撤、上冲和方向命中
- `stock_daily_report`：最终中文总结报告

已有本地库可单独执行三维评分字段迁移：

```bash
mysql -uroot -D stock_analysis_test < sql/2026-06-14-add-horizon-signal-scores.sql
mysql -uroot -D stock_analysis_test < sql/2026-06-14-create-signal-outcomes.sql
```

脚本正常写库时会自动：

1. 写入当天评分和未来待验证的 `stock_signal_outcome` 快照。
2. 用已入库的未来交易日行情刷新历史 `pending` 样本。
3. 重新生成最终报告，并在 `## 历史验证` 中展示已到期高强度样本的命中率、平均收益、窗口内回撤和上冲。

短期验证窗口是未来第 1/3/5 个交易日，中期是第 10/20 个交易日，长期是第 60/120 个交易日。报告中的历史验证只统计 `signal_score >= 50` 或 `signal_score <= -50` 的高强度信号；普通买入/卖出偏向和观望信号不再计入报告准确率。

查看最终报告：

```bash
mysql -uroot -D stock_analysis_test \
  -e "SELECT report_text FROM stock_daily_report WHERE stock_code='002466' ORDER BY trade_date DESC LIMIT 1\G"
```

如果本机 macOS 系统代理指向 `127.0.0.1:7890` 但代理服务没启动，Eastmoney 的实时概要/估值接口可能会出现 `ProxyError`。这类错误会写入 `source_errors_json` 和最终报告的数据提醒里，日线、技术指标和财务指标能取到时仍会正常入库。

## 数据口径

- 公司概要：`ak.stock_individual_info_em`
- 行情和估值：`ak.stock_zh_a_spot_em`
- 财务指标：`ak.stock_financial_analysis_indicator`
- 技术面日线：`ak.stock_zh_a_daily`
- MACD：`DIF = EMA12 - EMA26`，`DEA = DIF 的 EMA9`，柱体为 `(DIF - DEA) * 2`
- BOLL：20 日均线，上下轨为 `MA20 ± 2 * STD20`
- KDJ：9 日 RSV，K/D 初始值为 50
- RSI：同花顺/通达信常见口径，`SMA(MAX(CLOSE-REF(CLOSE,1),0),N,1) / SMA(ABS(CLOSE-REF(CLOSE,1)),N,1) * 100`，默认输出 RSI6 / RSI12 / RSI24；脚本会保留足够历史日线做预热
- 长期趋势：统计 20/60/120/250 日涨跌幅、当前价格相对对应均线的位置、MACD 柱体为正占比、BOLL 中轨上方占比，并结合 MA20/MA60/MA120/MA250 排列和 RSI24 给出趋势评分
- 买卖评分：保留一个综合总分，同时输出短期（择时主导）、中期（20/60/120 日趋势主导）、长期（基本面与 120/250 日结构主导）三档评分

报告只做自动化筛查和研究辅助，不构成投资建议。

## 数据展示看板

本项目新增了一个本地 VitePress + Express 看板，用来浏览 MySQL 中已经入库的每日分析结果。

安装前端依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

- Express API 默认运行在 `http://127.0.0.1:3210`
- VitePress 默认运行在 `http://127.0.0.1:5173`
- MySQL 默认读取 `stock_analysis_test`，可通过 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 覆盖

常用接口：

```bash
curl http://127.0.0.1:3210/api/dates
curl "http://127.0.0.1:3210/api/analysis?date=2026-06-12"
curl "http://127.0.0.1:3210/api/stocks/002466?date=2026-06-12"
```

生产构建：

```bash
npm run build
npm start
```

构建后 Express 会同时提供 `/api/*` 和 VitePress 静态页面。
