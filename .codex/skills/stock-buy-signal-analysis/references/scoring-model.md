# Scoring Model

Use this reference when explaining or adjusting the buy/sell score.

## Score Meaning

Apply the same meaning to the overall score and to each time-horizon score.

| Score | Meaning |
| ---: | --- |
| `50..100` | Strong buy bias. Technical and fundamental evidence broadly align. |
| `15..49` | Buy bias. Prefer staged entry or confirmation if short-term timing is weak. |
| `-14..14` | Watch. Evidence is mixed or incomplete. |
| `-49..-15` | Sell/avoid bias. Risk or trend weakness dominates. |
| `-100..-50` | Strong sell/avoid bias. Multiple major signals are negative. |

## Time Horizons

The scorer returns `horizon_scores` in addition to the overall score:

- `short_term`: short-term timing score. MACD, BOLL, KDJ, RSI, volume, and the 20-day setup dominate; fundamentals only constrain obvious low-quality risk.
- `medium_term`: medium-term swing score. 20/60/120-day trend, moving averages, trend persistence, and fundamental support dominate.
- `long_term`: long-term allocation score. ROE, growth, cash conversion, valuation, and 120/250-day structure dominate; short-term timing only affects entry rhythm.

Use disagreement between horizons as the main action guide:

- Short strong, medium/long weak: trading-only signal; avoid treating it as investment conviction.
- Medium/long strong, short weak: watch for confirmation, staged entry, or pullback entry.
- All three aligned positive: highest-quality buy bias.
- All three aligned negative: avoid or reduce exposure.

## Historical Validation

Use `stock_signal_outcome` to evaluate saved signals after enough future trading days exist:

- Short-term windows: future trading day `1/3/5`.
- Medium-term windows: future trading day `10/20`.
- Long-term windows: future trading day `60/120`.

For buy-bias signals, positive future return is a directional hit. For sell/avoid signals, negative future return is a directional hit. Watch signals are not directional samples, but they still count toward average return and risk statistics.

Never recompute old scores with current data when judging accuracy. Use the score snapshot saved on the signal date and compare it with later quote data.

## Review Memory

Use `references/review-memory.md` to turn historical validation into controlled strategy learning.

The scorer reads the machine-readable JSON block in that file:

- Only `active_adjustments` are applied automatically.
- `scope.horizons` limits the rule to `short_term`, `medium_term`, or `long_term`.
- `scope.regimes` limits the rule to `trend`, `range`, `downtrend`, or `mixed`.
- `component_weight_multipliers` changes horizon component weights such as `timing`, `trend`, `fundamental`, or `data_penalty`.
- `score_bias` adds a small horizon-specific calibration part.

Keep observations and candidate rules outside the active JSON block until enough matured samples support them. This prevents one mistaken stock call from overfitting the scoring model.

Example adjustment types:

- MACD/KDJ over-reward in short-term trend regimes: reduce `timing` weight or add a small negative short-term bias.
- BOLL lower-band repair in range regimes: test a small `timing` weight increase only if drawdown improves.
- Oversold bounce in downtrends: keep KDJ/RSI positive points small unless MACD and 20-day trend also improve.
- Strong medium/long structure with weak short-term timing: reduce short-term pullback penalty only if later returns validate the thesis.

## Components

### Fundamentals

Reward durable quality: ROE, revenue/profit growth, low debt, positive operating cash flow, reasonable valuation.

Penalize:

- ROE below 5%.
- Revenue and profit both shrinking.
- Operating cash flow to net profit below 0.5x.
- Debt ratio above 70% for non-financial companies.
- Negative or extreme PE when available.

### Long-Term Trend

Use the 20/60/120/250-day trend table:

- 20-day window captures current pullback or breakout.
- 60/120-day windows capture swing trend.
- 250-day window captures long-term regime.
- If long-term return is strong but 20-day momentum is weak, prefer watch/staged entry.

Use MA order:

- `MA20 > MA60 > MA120`: short/mid-term trend alignment.
- `MA60 > MA120 > MA250`: long-term structure remains strong.
- Mixed MA order means the trend is not clean.

### Timing Indicators

Use MACD, BOLL, KDJ, RSI, and volume adaptively:

- Trend regime: MACD, moving averages, and volume expansion carry more weight.
- Range regime: BOLL, RSI, and KDJ carry more weight.
- Downtrend regime: oversold RSI/KDJ is only a rebound clue, not a buy signal by itself.

RSI uses the common Tonghuashun/Tongdaxin formula:

```text
SMA(MAX(CLOSE - REF(CLOSE,1), 0), N, 1)
/ SMA(ABS(CLOSE - REF(CLOSE,1)), N, 1) * 100
```

### Confidence

Lower confidence when:

- company overview or valuation source fails,
- technical data is missing,
- fundamentals and trend sharply conflict,
- score is close to zero.
