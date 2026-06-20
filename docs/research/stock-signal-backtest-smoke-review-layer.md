# 股票信号历史回测研究报告

- 生成时间：2026-06-20 18:59:10
- 回测区间：2025-06-19 至 2026-06-19
- 验证段起点：2026-02-19
- 市场基准：sh000001
- 股票数量：1
- 信号样本：3
- 数据边界：每个信号日只使用当日及以前的日线数据；本研究不连接 MySQL，不上报生产接口。
- 基本面边界：第一版不使用实时估值和财务指标，避免历史回看时混入未来财报或当前估值。
- 策略边界：本报告只生成观察和候选规则，不自动修改 active 评分规则。

## 核心发现

- 命中率最高的窗口是 长期 60日：方向样本 2，命中率 100.00%，平均收益 -1.10%。
- 命中率最低的窗口是 短期 1日：方向样本 3，命中率 33.33%，平均收益 0.36%。
- 高强度信号样本暂未达到稳定比较门槛，先保留观察。

## 初步分析理论

- 短期评分主要用于择时，不应单独升级为投资结论；需要结合中期/长期结构确认。
- 中长期窗口更适合检验趋势与质量逻辑，短期窗口更适合检查追涨、超卖和放量信号是否过度奖励。
- 高强度样本只在样本量足够且验证段也改善时，才适合转化为候选权重调整。
- 如果长期窗口平均收益显著高于短期窗口，说明评分器更适合做趋势/配置筛选，而不是高频短线预测。
- 如果短期命中率接近 50%，下一轮应重点复盘 MACD、BOLL、KDJ、RSI 在不同市场状态下的权重。

## 分周期命中统计

| 周期窗口 | 样本 | 方向样本 | 高强度样本 | 命中率 | 高强度命中率 | 平均收益 | 平均回撤 | 平均上冲 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 长期 60日 | 2 | 2 | 0 | 100.00% | 暂无 | -1.10% | -2.82% | 7.72% |
| 长期 120日 | 2 | 2 | 0 | 50.00% | 暂无 | -0.72% | -5.53% | 7.72% |
| 中期 10日 | 2 | 2 | 1 | 50.00% | 100.00% | 3.57% | 1.13% | 4.29% |
| 中期 20日 | 2 | 2 | 1 | 50.00% | 100.00% | 4.28% | 0.86% | 7.72% |
| 短期 1日 | 3 | 3 | 1 | 33.33% | 100.00% | 0.36% | 0.36% | 0.36% |
| 短期 3日 | 2 | 2 | 1 | 50.00% | 100.00% | 1.72% | 1.13% | 1.72% |
| 短期 5日 | 2 | 2 | 1 | 50.00% | 100.00% | 4.20% | 1.13% | 4.29% |

## 市场状态观察

| 状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 |
| --- | ---: | ---: | ---: | ---: |
| downtrend/长期 | 2 | 2 | 100.00% | -1.96% |
| downtrend/中期 | 2 | 2 | 0.00% | 1.32% |
| downtrend/短期 | 3 | 3 | 0.00% | 1.76% |
| mixed/短期 | 1 | 1 | 0.00% | -1.46% |
| trend/长期 | 2 | 2 | 50.00% | 0.14% |
| trend/中期 | 2 | 2 | 100.00% | 6.53% |
| trend/短期 | 3 | 3 | 100.00% | 3.03% |

## 细分市场状态观察

| 细分状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 下跌 `downtrend`/长期 | 2 | 2 | 100.00% | -1.96% | -6.78% |
| 下跌 `downtrend`/中期 | 2 | 2 | 0.00% | 1.32% | 0.82% |
| 下跌 `downtrend`/短期 | 3 | 3 | 0.00% | 1.76% | 1.18% |
| 混合 `mixed`/短期 | 1 | 1 | 0.00% | -1.46% | -1.46% |
| 趋势 `trend`/长期 | 2 | 2 | 50.00% | 0.14% | -1.58% |
| 趋势 `trend`/中期 | 2 | 2 | 100.00% | 6.53% | 1.17% |
| 趋势 `trend`/短期 | 3 | 3 | 100.00% | 3.03% | 1.17% |

## 市场基准状态观察

| 市场状态/周期 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 市场下跌 `market_downtrend`/长期 | 2 | 2 | 50.00% | 0.14% | -1.58% |
| 市场下跌 `market_downtrend`/中期 | 2 | 2 | 100.00% | 6.53% | 1.17% |
| 市场下跌 `market_downtrend`/短期 | 3 | 3 | 100.00% | 3.03% | 1.17% |
| 市场震荡 `market_range`/长期 | 2 | 2 | 100.00% | -1.96% | -6.78% |
| 市场震荡 `market_range`/中期 | 2 | 2 | 0.00% | 1.32% | 0.82% |
| 市场震荡 `market_range`/短期 | 4 | 4 | 0.00% | 0.95% | 0.52% |

## 训练/验证对照

| 数据段 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 训练段 | 长期 60日 | 2 | 2 | 100.00% | -1.10% | -2.82% |
| 训练段 | 长期 120日 | 2 | 2 | 50.00% | -0.72% | -5.53% |
| 训练段 | 中期 10日 | 2 | 2 | 50.00% | 3.57% | 1.13% |
| 训练段 | 中期 20日 | 2 | 2 | 50.00% | 4.28% | 0.86% |
| 训练段 | 短期 1日 | 2 | 2 | 50.00% | 1.27% | 1.27% |
| 训练段 | 短期 3日 | 2 | 2 | 50.00% | 1.72% | 1.13% |
| 训练段 | 短期 5日 | 2 | 2 | 50.00% | 4.20% | 1.13% |
| 验证段 | 短期 1日 | 1 | 1 | 0.00% | -1.46% | -1.46% |

## 买卖方向拆分

| 方向 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 买入方向 | 长期 60日 | 1 | 1 | 100.00% | 1.26% | 0.00% |
| 买入方向 | 长期 120日 | 1 | 1 | 0.00% | -0.99% | -3.15% |
| 买入方向 | 中期 10日 | 1 | 1 | 100.00% | 5.50% | 1.17% |
| 买入方向 | 中期 20日 | 1 | 1 | 100.00% | 7.57% | 1.17% |
| 买入方向 | 短期 1日 | 2 | 2 | 50.00% | -0.15% | -0.15% |
| 买入方向 | 短期 3日 | 1 | 1 | 100.00% | 1.89% | 1.17% |
| 买入方向 | 短期 5日 | 1 | 1 | 100.00% | 6.04% | 1.17% |
| 卖出/回避方向 | 长期 60日 | 1 | 1 | 100.00% | -3.46% | -5.64% |
| 卖出/回避方向 | 长期 120日 | 1 | 1 | 100.00% | -0.45% | -7.92% |
| 卖出/回避方向 | 中期 10日 | 1 | 1 | 0.00% | 1.64% | 1.09% |
| 卖出/回避方向 | 中期 20日 | 1 | 1 | 0.00% | 1.00% | 0.55% |
| 卖出/回避方向 | 短期 1日 | 1 | 1 | 0.00% | 1.36% | 1.36% |
| 卖出/回避方向 | 短期 3日 | 1 | 1 | 0.00% | 1.55% | 1.09% |
| 卖出/回避方向 | 短期 5日 | 1 | 1 | 0.00% | 2.37% | 1.09% |

## 细分状态买卖方向拆分

| 方向 | 细分状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |

## 市场与个股交叉状态归因

| 方向 | 市场状态 | 个股状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |

## 市场状态买卖方向拆分

| 方向 | 市场状态 | 周期窗口 | 样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |

## 因子归因复盘

| 因子 | 取值 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |

## 买卖方向因子归因

| 方向 | 因子 | 取值 | 周期窗口 | 样本 | 方向样本 | 命中率 | 平均收益 | 平均回撤 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |

## 候选规则观察

- 暂无达到样本门槛的候选调整；继续积累样本，避免过早优化。

## 候选优化规则

- 暂无满足样本与效果门槛的候选优化规则；本轮不建议修改 active 权重。

## 候选规则模拟对比

| 规则 | 调整方式 | 数据段 | 匹配样本 | 方向样本变化 | 错误方向变化 | 降级错误率 | 原命中率 | 模拟命中率 | 命中变化 | 方向均收益变化 | 方向均回撤变化 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 推至观察边界 | 训练段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 推至观察边界 | 验证段 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 候选规则组合级验证

- 这一节把同一信号日命中的股票视为一个等权篮子，避免同日密集信号把单票统计放大。

| 规则 | 数据段 | 篮子数 | 信号数 | 平均篮子大小 | 等权篮子均收益 | 正收益篮子率 | 等权篮子均回撤 | 最差篮子日期 | 最差篮子收益 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 训练段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 验证段 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 全样本 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 候选规则跨持有期画像

- 这一节忽略候选规则自身的固定持有期，只保留方向和因子 scope，横向比较同一状态在不同窗口的表现，用来定位 horizon 漂移。

| 规则 | 数据段 | 周期窗口 | 信号数 | 方向样本 | 命中率 | 平均收益 | 平均回撤 | 日篮数 | 日篮均收益 | 正收益日篮率 | 最差日篮收益 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 |

## 连续速度持有期选择观察

- 这一节把同一连续速度 scope 去重后横向比较 20/60/120 日，用来判断速度指标是否能解释 horizon 漂移。单元格格式为 `样本 / 平均收益 / 日篮数`。

| 速度 scope | 训练20日 | 训练60日 | 训练120日 | 验证20日 | 验证60日 | 验证120日 | 观察 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `market-speed-profile` | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 样本不足 |
| `stock-speed-profile` | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 样本不足 |
| `dual-speed-profile` | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 样本不足 |
| `market-macd-boll-speed` | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 样本不足 |
| `stock-macd-boll-speed` | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 样本不足 |

## 连续速度反例因子诊断

- 这一节只看连续速度 60 日候选。对 sell/avoid 规则来说，`有效风控` 表示原卖出/回避方向正确，属于降级为观察的反例风险；`滞后误杀` 表示原卖出/回避方向错误，属于降级受益样本。

| 规则 | 数据段 | 因子 | 取值 | 样本 | 有效风控 | 滞后误杀 | 有效风控率 | 有效风控均收益 | 滞后误杀均收益 | 平均回撤 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 |

## 卖出/回避观察降级确信度

- 这一节把 `neutralize_to_watch` 的卖出/回避候选转成连续诊断分数。分数只用于离线复盘和人工复核排序，不写入 active，也不代表买入信号。
- `有效风控率` 约等于验证段里原 sell/avoid 仍然正确的比例；这个比例越高，越应该给观察降级打折。

| 规则 | 周期窗口 | 训练样本 | 验证样本 | 验证日篮 | 训练滞后率 | 验证滞后率 | 有效风控率 | 降级确信度 | 验证日篮均收益 | 观察 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:dual-continuous-repair:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:market-continuous-repair:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_repair_focus:stock-continuous-repair:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:dual-speed-profile:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-macd-boll-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:market-speed-profile:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-macd-boll-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `continuous_speed_focus:stock-speed-profile:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `mixed_bucket_continuous_combo:market-volume-improved-still-down-macd-discontinuous:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `mixed_bucket_continuous_combo:no-market-volume-pulse-still-down:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-macd-speed-divergence:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-deterioration:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:market-quality-stock-volume-defense:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:stock-volume-deterioration:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_defense_pocket:tail-pending:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:dual-deteriorating:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:single-side-opposite-deteriorating:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-deteriorating:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_failure_focus:sync-insufficient:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:dual-quality-confirmed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:market-quality-confirmed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_focus:stock-quality-confirmed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:dual-sync-confirmed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:single-side-opposite-safe:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_quality_sync_focus:sync-non-deteriorating:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:dual-fast-repair-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-fast-repair-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:market-gradual-repair-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-fast-repair-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `repair_speed_focus:stock-gradual-repair-speed:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:dual-fast-dual-tail:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-stock-tail:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:120` | 长期 120日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-tail:sell_avoid:long_term:60` | 长期 60日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |
| `weak_tail_focus:market-fast-tail:sell_avoid:medium_term:20` | 中期 20日 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 无验证样本 |

## 高确信观察降级阶段块汇总

- 这一节把交易日篮继续聚合到月度和季度，检查高确信降级样本是不是只集中在少数交易日。

| 粒度 | 阶段 | 周期窗口 | 日篮 | 样本 | 滞后误杀 | 有效风控 | 滞后率 | 日篮均收益 | 最差日篮 | 最差日篮日期 | 平均确信度 | 有效风控占优日 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 0 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 高确信观察降级阶段因子画像

- 这一节为每个高确信阶段块列出关键因子的主导取值，用来解释阶段差异，而不是生成自动调分规则。

| 粒度 | 阶段 | 周期窗口 | 因子 | 主导取值 | 覆盖样本 | 阶段占比 | 滞后误杀 | 有效风控 | 滞后率 | 平均收益 | 平均确信度 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 0 | 0 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日持有期选择验证

- 这一节把同一股票、同一信号日的中期20日和长期60日结果配对，专门检验弱势尾部里 20 日风控是否会在 60 日变成滞后误杀。

| 条件 | 阶段 | 配对样本 | 20日有效风控 | 20日滞后 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 0 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日阶段因子解释

- 这一节把同股同日的 20/60 日配对样本按解释性因子分组，用来替代单纯季度标签，定位哪些状态更像 20 日风控或 60 日滞后。

| 条件 | 因子 | 取值 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日多因子阶段分类器雏形

- 这一节把阶段因子解释里的相对口袋组合成透明分类器，只用于报告诊断和人工复核排序，不自动调整评分。

| 条件 | 分类 | 主导原因 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 60口袋均数 | 反例口袋均数 | 判断 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日未命中混合桶拆解

- 这一节只拆多因子分类器里 `混合继续复核 / 未命中阶段口袋` 的配对样本，寻找下一轮分类器可以继续吸收或排除的因子。

| 条件 | 因子 | 取值 | 混合桶占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日未命中混合桶二阶组合拆解

- 这一节继续拆 `混合继续复核 / 未命中阶段口袋`，只看市场修复速度与量能、尾部位置、尾部修复信号的二阶组合，用于寻找降确信或继续吸收的候选线索。

| 条件 | 因子组合 | 取值组合 | 混合桶占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日速度分化低位折叠验证

- 这一节只看 `混合继续复核 / 未命中阶段口袋` 里的 `market_repair_speed_profile=速度分化` 且 `market_tail_extreme=弱势低位` 样本，按月度和季度折叠，验证降确信线索是否集中在少数阶段块。

| 条件 | 折叠 | 阶段 | 目标占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日速度分化低位日篮验证

- 这一节继续下钻 `market_repair_speed_profile=速度分化` 且 `market_tail_extreme=弱势低位`，按具体信号日聚合，解释同一季度或月份内部为什么会分化。

| 条件 | 信号日 | 月度 | 季度 | 目标占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日速度分化低位日篮可见变量对比

- 这一节只用信号日前已计算出的市场与个股因子，解释同一目标桶在不同信号日为何分化；未来收益只用于右侧结果验证。

| 条件 | 信号日 | 配对样本 | 20日有效风控 | 60日滞后 | 20日均收益 | 60日均收益 | 市场可见状态 | 个股可见状态 | 复盘判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日速度分化低位修复广度验证

- 这一节把目标日篮里的市场量能改善、市场 MACD 修复、个股 MACD 修复和个股量能改善转成覆盖率，验证 `2023-10-25` 与 `2023-12-21` 的分化是否能被信号日前可见的修复广度解释。

### 日篮明细

| 条件 | 信号日 | 配对样本 | 市场量能改善 | 市场MACD改善 | 个股MACD改善 | 个股量能改善 | 20日有效风控 | 60日滞后 | 20日均收益 | 60日均收益 | 组合 | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日混合桶市场量能门槛泛化验证

- 这一节把范围从 `速度分化+弱势低位` 目标桶放宽到整个 `混合继续复核 / 未命中阶段口袋`，检验市场量能改善是否只是少数日篮特例，还是能在更大混合桶里继续解释 20/60 日分化。

| 条件 | 组合 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日混合桶量能门槛阶段折叠验证

- 这一节只看整个 `混合继续复核 / 未命中阶段口袋` 中个股 MACD 已修复的组合，把市场量能改善/未改善分别按月度、季度和市场状态折叠，解释量能门槛为什么跨窗口不稳定。

| 条件 | 组合 | 折叠 | 取值 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日混合桶量能门槛连续阶段验证

- 这一节只看整个 `混合继续复核 / 未命中阶段口袋` 中个股 MACD 已修复的组合，把市场量能持续性、市场 MACD 修复持续性、指数脱离低点程度和 20 日反弹伸展程度纳入复核；这些变量全部只使用信号日前可见序列。

| 条件 | 组合 | 连续变量 | 取值 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 弱势尾部20/60日混合桶量能门槛连续组合验证

- 这一节在连续阶段变量上做二阶组合，验证单变量无法解释的量能门槛分裂是否来自“量能持续性 + 市场反弹状态”或“量能持续性 + 个股 MACD 持续性”的交互。

| 条件 | 组合 | 连续变量组合 | 取值组合 | 组合占比 | 配对样本 | 20日有效风控 | 60日滞后 | 20风控转60滞后 | 20日均收益 | 60日均收益 | 60-20收益差 | 判断 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 高确信观察降级交易日汇总

- 这一节把单信号复核样本按交易日聚合，避免把同一天密集触发的股票误读成彼此独立证据。

| 信号日 | 周期窗口 | 样本 | 滞后误杀 | 有效风控 | 滞后率 | 平均收益 | 最差收益 | 平均回撤 | 平均确信度 | 主导规则 | 主导规则样本 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 暂无 | 暂无 | 0 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 |

## 单信号观察降级复核样本

- 这一节把规则级降级确信度映射回具体历史信号，只列复核优先级最高的样本；它使用未来收益判断历史结果，因此只用于离线复盘。

| 股票 | 信号日 | 周期窗口 | 原分数/信号 | 后续收益 | 结果类型 | 最大回撤 | 降级确信度 | 有效风控率 | 命中规则数 | 最高确信规则 | 观察 |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 0 | 暂无 | 暂无 |

## 研究复核层新旧对照回放

- 这一节把 Skill 中的研究复核层转成离线标签，只模拟观察降级，不写入 active 调分；它用于判断新逻辑是否整体减少错误方向。

| 区间 | 复核标签 | 动作 | 周期窗口 | 样本 | 原方向样本 | 新方向样本 | 原命中率 | 新命中率 | 命中率变化 | 错误方向变化 | 被降级方向样本 | 被降级错误率 | 日篮 | 日篮均收益 | 最差日篮 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 训练段 | `mixed_review_only` | 仅复核 | 短期 1日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.36% | 1.36% |
| 训练段 | `mixed_review_only` | 仅复核 | 短期 3日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.55% | 1.55% |
| 训练段 | `mixed_review_only` | 仅复核 | 短期 5日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 2.37% | 2.37% |
| 训练段 | `mixed_review_only` | 仅复核 | 中期 10日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.64% | 1.64% |
| 训练段 | `mixed_review_only` | 仅复核 | 中期 20日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.00% | 1.00% |
| 训练段 | `mixed_review_only` | 仅复核 | 长期 60日 | 1 | 1 | 1 | 100.00% | 100.00% | 0.00% | 0 | 0 | 暂无 | 1 | -3.46% | -3.46% |
| 训练段 | `mixed_review_only` | 仅复核 | 长期 120日 | 1 | 1 | 1 | 100.00% | 100.00% | 0.00% | 0 | 0 | 暂无 | 1 | -0.45% | -0.45% |
| 全样本 | `mixed_review_only` | 仅复核 | 短期 1日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.36% | 1.36% |
| 全样本 | `mixed_review_only` | 仅复核 | 短期 3日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.55% | 1.55% |
| 全样本 | `mixed_review_only` | 仅复核 | 短期 5日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 2.37% | 2.37% |
| 全样本 | `mixed_review_only` | 仅复核 | 中期 10日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.64% | 1.64% |
| 全样本 | `mixed_review_only` | 仅复核 | 中期 20日 | 1 | 1 | 1 | 0.00% | 0.00% | 0.00% | 0 | 0 | 暂无 | 1 | 1.00% | 1.00% |
| 全样本 | `mixed_review_only` | 仅复核 | 长期 60日 | 1 | 1 | 1 | 100.00% | 100.00% | 0.00% | 0 | 0 | 暂无 | 1 | -3.46% | -3.46% |
| 全样本 | `mixed_review_only` | 仅复核 | 长期 120日 | 1 | 1 | 1 | 100.00% | 100.00% | 0.00% | 0 | 0 | 暂无 | 1 | -0.45% | -0.45% |

## 历史基本面覆盖度与缺口

| 项目 | 当前状态 | 影响 | 下一步 |
| --- | --- | --- | --- |
| 历史技术数据 | 已按信号日截断，覆盖 3 个评分快照 | 可用于短中期择时与趋势回放 | 继续保持无未来函数 |
| 历史估值与财务指标 | 本离线回放暂不读取实时估值、财务指标和当前财报 | 长期质量分只能作为低置信度边界，不能据此训练长期买入规则 | 按财报披露日接入 ROE、现金流、增速、估值分位 |
| 数据源错误记录 | 历史模式在 scoring item 中写入 source_errors | 提醒分析时降低长期结论确信度 | 后续把 source_errors 聚合进 outcome 级覆盖统计 |

## 研究复核层组合级验证

- 这一节按交易日构造最多 10 只股票的等权日篮，用来检查单股信号是否能转化为组合层面的稳定性；当前不模拟换手和交易成本。

| 场景 | 周期窗口 | 日篮 | 信号 | 平均篮子大小 | 日篮均收益 | 正收益日篮率 | 平均回撤 | 最差日篮日 | 最差日篮收益 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| AI ETF买入候选中期20日 | 中期 20日 | 1 | 1 | 1.00 | 7.57% | 100.00% | 1.17% | 2025-06-19 | 7.57% |
| AI ETF买入候选长期60日 | 长期 60日 | 1 | 1 | 1.00 | 1.26% | 100.00% | 0.00% | 2025-06-19 | 1.26% |
| 复核降级观察机会篮长期60日 | 长期 60日 | 0 | 0 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 | 暂无 |

## 股票池扩展与泛化验证

- 当前回放股票池：`stock.md`，实际股票数 1，`--max-codes` 为 1。
- 当前结论只证明这组观察池内的历史表现，不等同于全 A 股泛化能力。
- 后续泛化入口已经保留为 `--codes-file`：可分别准备沪深300、中证500、中证1000、行业分组和剔除/不剔除 ST 小市值的代码文件，然后用同一脚本回放。

```bash
uv run --python 3.12 --with-requirements requirements.txt \
  python research_signal_backtest.py --codes-file docs/research/stock-pool-hs300.md \
  --from-date 2023-06-19 --to-date 2026-06-19 \
  --validation-from 2024-06-19 --output docs/research/stock-signal-backtest-hs300.md
```

## 研究复核层失败案例库

- 这一节优先列出会伤害策略稳定性的反例：错误降级、漏掉卖出滞后、以及仅复核但仍不足的样本。

| 类型 | 股票 | 信号日 | 周期窗口 | 复核标签 | 动作 | 后续收益 | 最大回撤 | 阶段原因 |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| 复核不足：仅复核但原方向错误 | 000001 平安银行 | 2025-12-12 | 短期 5日 | `mixed_review_only` | 仅复核 | 2.37% | 1.09% | 市场修复质量分化 |
| 复核不足：仅复核但原方向错误 | 000001 平安银行 | 2025-12-12 | 中期 10日 | `mixed_review_only` | 仅复核 | 1.64% | 1.09% | 市场修复质量分化 |
| 复核不足：仅复核但原方向错误 | 000001 平安银行 | 2025-12-12 | 短期 3日 | `mixed_review_only` | 仅复核 | 1.55% | 1.09% | 市场修复质量分化 |
| 复核不足：仅复核但原方向错误 | 000001 平安银行 | 2025-12-12 | 短期 1日 | `mixed_review_only` | 仅复核 | 1.36% | 1.36% | 市场修复质量分化 |
| 复核不足：仅复核但原方向错误 | 000001 平安银行 | 2025-12-12 | 中期 20日 | `mixed_review_only` | 仅复核 | 1.00% | 0.55% | 市场修复质量分化 |

## 稳定候选筛选

- 暂无规则同时满足训练段改善、验证段不退化和样本数门槛；本轮不写入 active。

## 候选规则滚动折叠稳定性

- 这一节按信号日期折叠候选规则，检查错误方向减少是否集中在少数月份/季度；集中度越高，越不适合直接 active。
- 暂无滚动折叠数据。

## 候选规则阶段因子折叠解释

- 这一节按非日期因子折叠候选规则，用来判断候选是否能被市场/个股阶段解释，而不是只靠月份或季度聚类。
- 暂无阶段因子折叠数据。

## 下一步

- 用训练段发现候选规则，再用验证段复查，避免把单一年份噪声写成长期规则。
- 只有重复样本支持的规则，才考虑进入 `review-memory.md` 的 candidate；active 调整需要更严格证据。
