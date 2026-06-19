# Review Memory

This file stores post-analysis reviews for the stock signal skill. Use it to record where the model was inaccurate, what evidence explains the miss, and which small scoring adjustments should be applied in later runs.

## Rules

- Update this file only after comparing saved signal snapshots with matured `stock_signal_outcome` rows or a clearly dated later quote.
- Do not promote a one-stock miss directly to an active adjustment. Record it as an observation first.
- Promote an adjustment to `active_adjustments` only when the pattern is repeated across enough comparable samples. Prefer at least 10 matured directional samples for active rules, or keep it as `candidate` below.
- Segment every lesson by horizon, market regime, indicator, and data quality. A MACD/KDJ lesson in a short-term trend setup should not automatically affect medium-term or long-term scoring.
- Keep every adjustment small and reversible. Prefer weight multipliers between `0.85` and `1.15`, or a score bias between `-5` and `5`.
- Never recompute old scores with current data when judging accuracy. Use saved score snapshots and later quotes only.

## Active Strategy Memory

The scorer reads only the JSON block between the markers below. `active_adjustments` are applied automatically to horizon scores. Observations and candidate rules outside this block are for human/Codex review only.

<!-- strategy-memory-json:start -->
```json
{
  "version": 1,
  "active_adjustments": []
}
```
<!-- strategy-memory-json:end -->

## Review Log

Add newest entries at the top.

### YYYY-MM-DD `股票代码` `股票名称`

- Original signal date:
- Original score / horizons:
- Expected thesis:
- Matured outcome:
- Error type: false positive / false negative / horizon mismatch / timing mismatch / data quality
- Regime:
- Indicator lesson:
- Evidence:
- Decision: observation / candidate / active / retired
- Proposed adjustment:
- Follow-up validation:

## Candidate Adjustments

Keep candidates here until they have enough evidence to move into the JSON block.

### Example Template

```json
{
  "id": "short-term-trend-macd-kdj-overreward",
  "status": "candidate",
  "scope": {
    "horizons": ["short_term"],
    "regimes": ["trend"]
  },
  "component_weight_multipliers": {
    "timing": 0.9
  },
  "score_bias": -2,
  "reason": "Trend-regime short-term signals overrewarded MACD/KDJ when later returns failed to follow through.",
  "evidence": {
    "sample_count": 0,
    "hit_rate_delta_pct": 0,
    "avg_return_delta_pct": 0
  }
}
```

## Ideas To Validate

- In downtrends, keep RSI/KDJ oversold as a rebound clue but avoid converting it into a buy-bias signal unless MACD and 20-day trend also improve.
- In range-bound regimes, BOLL lower-band repair may deserve more weight than MACD continuation, but only if drawdown statistics improve.
- For high-valuation stocks, cap short-term enthusiasm when MACD/KDJ turn positive but medium/long-term scores remain weak.
- Track false negatives separately: if strong medium/long-term structure repeatedly rises after a weak short-term timing score, reduce the penalty for short-term pullbacks.
