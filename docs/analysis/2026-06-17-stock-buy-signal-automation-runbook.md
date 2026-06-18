# 2026-06-17 股票买入信号自动化运行复盘

## 结论

今天的问题分两类：

1. 运行环境问题：Codex 自动化 shell 里最初没有 `uv`，导致命令在进入 Python 前失败。安装 Homebrew 版 `uv 0.11.21` 后，`uv` 自动下载并使用 CPython 3.12.13，生产 ingest 命令可以跑通。
2. 数据源问题：Eastmoney `push2.eastmoney.com` 相关接口在当前网络/系统代理环境下失败，影响 `个股信息获取` 和 `实时估值快照获取`，但主流程仍能用其他数据完成评分和上传，置信度会降为低。

## 今天的关键时间线

- 06:04：首次自动化失败，错误是 `zsh: command not found: uv`，没有进入数据抓取。
- 09:00 左右：安装 `uv`，重新运行生产 ingest 命令。
- 09:12:53：生产服务 `/api/dates` 显示 `2026-06-16` 已更新 110 只股票。
- 20:17：新增并运行环境预检，结果通过。

## 标准运行命令

生产 ingest：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py \
  --ingest-url "http://stock.zzh.cool/api/ingest/daily-analysis"
```

如果 Eastmoney 继续在当前网络下失败，可以直接跳过 Eastmoney，把可用字段从降级源获取：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py \
  --skip-eastmoney \
  --ingest-url "http://stock.zzh.cool/api/ingest/daily-analysis"
```

默认命令现在也有本批次断路器：遇到 `Unable to connect to proxy`、`RemoteDisconnected`、`Max retries exceeded`、`Connection aborted` 这类 Eastmoney 连接错误后，会停止继续逐只请求 Eastmoney，并一次性用新浪实时行情补齐本批次剩余股票的可用字段。

环境预检：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py \
  --preflight \
  --ingest-url "http://stock.zzh.cool/api/ingest/daily-analysis"
```

预检只检查：

- `akshare` 能否导入。
- 评分器能否加载。
- `stock.md` 能否解析。
- 生产服务 `/api/health` 是否可用。

它不会抓取股票数据、不会评分、不会上传、不会写库。

## 预计耗时

- 环境预检：本次约 8 秒。
- 首次安装或依赖冷启动：可能额外 1 到 3 分钟。
- 全量 110 只股票：本次约 14 分钟。网络慢或 AKShare 某些接口重试时，按 12 到 20 分钟估计更稳。
- 单只股票测试：通常几十秒内完成，但取决于 AKShare 和外部数据源响应。

## 新增日志行为

脚本现在会把进度日志写到 stderr，最终结果仍保留在 stdout。自动化日志里应能看到类似内容：

```text
[20:17:00] 开始环境预检
[20:17:08] akshare 可导入：1.18.64
[20:17:08] 股票代码文件可读取：110 只（000001, 002493, 000002, 002555, 000063...）
[20:17:08] 生产服务健康检查通过：http://stock.zzh.cool/api/health，database=stock_analysis_test
[20:17:08] 环境预检通过
```

全量分析时会看到：

```text
[09:00:00] 准备分析 110 只股票
[09:00:00] 开始获取实时估值快照
[09:00:15] 数据源提醒：实时估值快照获取失败：...
[09:00:15] [1/110] 开始分析 000001
[09:00:20] [1/110] 完成分析 000001 2026-06-16，source_errors=2
[09:12:53] 生产 ingest 上报完成，persistedCount=110
[09:12:53] 任务完成：110 条结果，耗时 840.0s
```

如果长时间没有新日志，优先判断卡在哪个阶段：依赖准备、实时快照、逐只分析、评分、生产上报。

## 如何确认生产结果

```bash
curl -fsS http://stock.zzh.cool/api/dates
```

提取最新日期的数据源错误：

```bash
curl -fsS "http://stock.zzh.cool/api/analysis?date=2026-06-16" \
  | jq -r '[.items[].sourceErrors[]] | unique[]'
```

今天的生产结果：

- `tradeDate=2026-06-16`
- `stockCount=110`
- `sourceErrorCount=220`
- `highConfidenceCount=0`

## Eastmoney 代理失败分析

本机 macOS 系统代理配置：

```text
HTTPProxy=127.0.0.1
HTTPPort=7890
HTTPSProxy=127.0.0.1
HTTPSPort=7890
SOCKSProxy=127.0.0.1
SOCKSPort=7890
```

Python 里 `urllib.request.getproxies()` 会读到这些系统代理配置，所以 `requests` 访问 Eastmoney 时会走代理。今天复现到的错误是：

```text
ProxyError: Unable to connect to proxy; host=push2.eastmoney.com
```

即使在测试中绕过系统代理，`push2.eastmoney.com/api/qt/stock/get` 对当前网络出口仍返回 `RemoteDisconnected`。这说明问题不是单纯的环境变量代理，而是 Eastmoney `push2` API 对当前网络路径不稳定。

## 两个失败数据源的用途

`个股信息获取` 使用 `eastmoney_stock_snapshot()`，访问：

```text
https://push2.eastmoney.com/api/qt/stock/get
```

主要字段：

- `f57/f58`：股票代码、名称。
- `f127`：行业。
- `f84/f85`：总股本、流通股。
- `f116/f117`：总市值、流通市值。
- `f189`：上市时间。

`实时估值快照获取` 也使用同一个 Eastmoney compact snapshot，主要补：

- 最新价、涨跌幅。
- 动态市盈率、市净率。
- 换手率、量比。
- 市值、流通市值。

这些数据用于基本面概览、估值约束和报告展示。缺失后，技术面和财务指标仍可评分，但置信度会降低。

## 替代方案

短期可用方案：

- 保留当前降级逻辑：Eastmoney 失败时继续跑完整流程，把缺失源写入 `source_errors_json`，避免自动化完全中断。
- 在任务开始前跑 `--preflight`：快速确认 Python、依赖、代码文件和生产服务可用。
- 在网络层处理代理：让 `127.0.0.1:7890` 服务稳定运行，或在代理软件中给 `*.eastmoney.com`、`push2.eastmoney.com` 配置合适规则。注意：今天直接绕过代理也失败，所以这只能作为排查路径，不保证解决。

可实现的数据源 fallback：

- `ak.stock_zh_a_spot()`：新浪实时 A 股行情，本次测试可用。能提供代码、名称、最新价、涨跌幅、成交量、成交额，但缺少 PE/PB、市值、行业、上市时间。已接入为 `实时估值快照` fallback。
- `ak.stock_info_a_code_name()`：A 股代码名称表，本次测试可用。可作为股票名称 fallback。已接入为 `个股信息` fallback。
- `ak.stock_zh_a_hist_tx()`：腾讯日线，本次测试可用。可作为日线行情备用源，但不能补估值。
- 生产 MySQL 历史缓存：可复用上次成功保存的股票名称、行业、上市时间、股本等低频静态数据，减少 Eastmoney 短时故障影响。

不建议直接替代的方案：

- `ak.stock_zh_a_spot_em()` 和 `ak.stock_individual_info_em()`：它们同样走 Eastmoney `push2/82.push2`，今天测试也失败。
- 盲目用空值兜底：这会让报告看起来完整但实际缺数据，应继续显式写入 `source_errors_json`。

## 建议的下一步改进

1. 对估值、市值、行业、上市时间继续保留明确 source error，直到有可靠替代源或历史缓存。
2. 后续如果生产服务开放只读元数据接口，本地分析可以在 Eastmoney 失败时读取上次成功静态信息。
3. 继续观察新浪实时行情的稳定性。AKShare 文档提示重复运行 `stock_zh_a_spot()` 可能被新浪临时封 IP，因此不宜在同一次流程内频繁重复调用。
4. 如果连续几天 Eastmoney 都不可用，自动化命令可以临时加入 `--skip-eastmoney`，用速度更稳定的降级路径完成日报，但报告仍应显示估值和静态字段缺失。

## 2026-06-17 fallback 修复验证

已实现：

- `fetch_spot_snapshot()`：Eastmoney `push2` 失败后，使用 `ak.stock_zh_a_spot()` 补名称、最新价、涨跌幅、成交量、成交额。
- `fetch_individual_info()`：Eastmoney `push2` 失败后，使用 `ak.stock_info_a_code_name()` 补代码和名称。

不上报、不写库的直接复测结果：

```text
[个股信息获取]
has_data=True
error=个股信息降级：Eastmoney失败（ProxyError: Unable to connect to proxy; host=push2.eastmoney.com）；已使用A股代码名称表；缺少行业/股本/上市时间/估值字段

[实时估值快照获取]
has_data=True
error=实时估值快照降级：Eastmoney失败（000001: ProxyError: Unable to connect to proxy; host=push2.eastmoney.com）；已使用新浪实时行情补充可用字段；缺少动态市盈率/市净率/市值/股本/行业/上市时间
```

这表示两个数据源已从“取数失败”降级为“可取部分字段并明确提示缺失字段”。后续生产报告仍应保留 source error，避免把缺失估值和静态资料伪装成完整数据。

## 2026-06-17 快速降级与断路器修复

已进一步实现：

- `--skip-eastmoney`：命令级开关，直接绕过 Eastmoney `push2`，避免每天在同一个网络问题上重复等待。
- Eastmoney 断路器：默认路径仍会先尝试 Eastmoney；一旦识别到代理/连接类错误，本批次停止继续尝试 Eastmoney，改用新浪实时行情补剩余股票。
- 降级警告继续保留：不会把新浪实时行情或 A 股代码名称表伪装成完整估值源，仍明确提示缺少 PE/PB、市值、股本、行业、上市时间。

不上报、不写库的验证命令：

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python save_daily_to_mysql.py 000001 --skip-eastmoney --dry-run
```

验证结果摘要：

```text
开始获取新浪实时行情降级源
数据源提醒：实时估值快照降级：已跳过Eastmoney；已使用新浪实时行情补充可用字段；缺少动态市盈率/市净率/市值/股本/行业/上市时间
000001 生成了 dry-run SQL，未上报、未写库
```

直接函数验证结果：

```text
fetch_individual_info(..., "000001", skip_eastmoney=True)
has_data=True
source=A股代码名称表

fetch_spot_snapshot(..., ["000001", "600519"])
Eastmoney 只失败 1 次后停止继续尝试，000001/600519 均由新浪实时行情返回可用字段
```
