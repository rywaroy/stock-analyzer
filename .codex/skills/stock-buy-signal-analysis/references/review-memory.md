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

### 2026-06-20 `market_bear_continuation|bear_continuation` 卖出/回避中期观察降级

```json
{
  "id": "neutralize-sell-avoid-market-bear-continuation-bear-continuation-medium-20",
  "status": "candidate",
  "scope": {
    "horizons": ["medium_term"],
    "window_days": [20],
    "signal_side": "sell_avoid",
    "factors": {
      "market_refined_regime": "market_bear_continuation|bear_continuation"
    }
  },
  "score_adjustment_mode": "neutralize_to_watch",
  "target_score_boundary": -14,
  "reason": "Three-year research split shows medium-term sell/avoid signals in market weak-continuation plus stock bear-continuation regimes were mostly false negatives during rebound phases. Candidate action is to downgrade this specific directional sell/avoid signal to watch, not to create a buy signal.",
  "evidence": {
    "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19.md",
    "train_sample_count": 566,
    "train_neutralized_wrong_directional_rate_pct": 81.63,
    "train_wrong_directional_count_delta": -462,
    "validation_sample_count": 205,
    "validation_neutralized_wrong_directional_rate_pct": 100.0,
    "validation_wrong_directional_count_delta": -205,
    "rolling_monthly_evidence": {
      "folds_with_samples": 6,
      "total_matched_count": 771,
      "max_fold_sample_share_pct": 26.98,
      "weighted_neutralized_wrong_directional_rate_pct": 86.51,
      "positive_wrong_delta_fold_share_pct": 100.0,
      "months": ["2023-10", "2023-11", "2023-12", "2024-01", "2024-02", "2024-09"]
    },
    "rolling_quarterly_evidence": {
      "folds_with_samples": 3,
      "total_matched_count": 771,
      "max_fold_sample_share_pct": 50.06,
      "weighted_neutralized_wrong_directional_rate_pct": 86.51,
      "positive_wrong_delta_fold_share_pct": 100.0,
      "quarters": ["2023-Q4", "2024-Q1", "2024-Q3"]
    },
    "stage_factor_evidence": {
      "interpretation": "The candidate is concentrated in extreme weak-alignment states rather than confirmed repair states: market short/medium trends and stock short/medium trends are down, with horizon scores mostly aligned bearish.",
      "market_trend_20d": {"value": "下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51},
      "market_trend_60d": {"value": "下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51},
      "market_trend_120d": {"value": "下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51},
      "trend_20d": {"value": "下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51},
      "trend_60d": {"value": "下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51},
      "horizon_alignment": {"value": "三周期同向偏空", "sample_count": 750, "neutralized_wrong_directional_rate_pct": 86.4},
      "weak_tail_factor_evidence": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-tail.md",
        "decline_duration": [
          {"value": "短中长期同步下跌", "sample_count": 728, "neutralized_wrong_directional_rate_pct": 85.85},
          {"value": "短中期同步下跌", "sample_count": 43, "neutralized_wrong_directional_rate_pct": 97.67}
        ],
        "decline_speed": [
          {"value": "跌速加快", "sample_count": 608, "neutralized_wrong_directional_rate_pct": 86.18},
          {"value": "跌速持平", "sample_count": 144, "neutralized_wrong_directional_rate_pct": 88.19},
          {"value": "跌速放缓", "sample_count": 19, "neutralized_wrong_directional_rate_pct": 84.21}
        ],
        "market_decline_duration": [
          {"value": "短中长期同步下跌", "sample_count": 771, "neutralized_wrong_directional_rate_pct": 86.51}
        ],
        "market_decline_speed": [
          {"value": "跌速加快", "sample_count": 742, "neutralized_wrong_directional_rate_pct": 87.87},
          {"value": "跌速持平", "sample_count": 29, "neutralized_wrong_directional_rate_pct": 51.72}
        ],
        "market_tail_extreme": [
          {"value": "极端超卖", "sample_count": 412, "neutralized_wrong_directional_rate_pct": 89.81},
          {"value": "弱势低位", "sample_count": 359, "neutralized_wrong_directional_rate_pct": 82.73}
        ],
        "weak_tail_extreme": [
          {"value": "弱势低位", "sample_count": 391, "neutralized_wrong_directional_rate_pct": 84.14},
          {"value": "极端超卖", "sample_count": 366, "neutralized_wrong_directional_rate_pct": 89.34},
          {"value": "常规", "sample_count": 14, "neutralized_wrong_directional_rate_pct": 78.57}
        ]
      }
    },
    "weak_tail_focus_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Composite weak-tail scopes confirm the sell-lag explanation but do not resolve horizon drift. Narrower scopes reduce samples and only modestly improve purity in the primary split.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-weak-tail-focus.md",
        "market_fast_stock_tail_medium_20": {
          "train_sample_count": 527,
          "train_neutralized_wrong_directional_rate_pct": 83.3,
          "validation_sample_count": 202,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "quarterly_total_matched_count": 729,
          "quarterly_max_fold_sample_share_pct": 52.4
        },
        "dual_fast_dual_tail_medium_20": {
          "train_sample_count": 433,
          "train_neutralized_wrong_directional_rate_pct": 82.91,
          "validation_sample_count": 153,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "quarterly_total_matched_count": 586,
          "quarterly_max_fold_sample_share_pct": 55.12
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-weak-tail-focus.md",
        "market_fast_stock_tail_long_60": {
          "train_sample_count": 1051,
          "train_neutralized_wrong_directional_rate_pct": 74.12,
          "validation_sample_count": 858,
          "validation_neutralized_wrong_directional_rate_pct": 78.79,
          "quarterly_total_matched_count": 1909,
          "quarterly_max_fold_sample_share_pct": 28.6
        },
        "dual_fast_dual_tail_long_60": {
          "train_sample_count": 801,
          "train_neutralized_wrong_directional_rate_pct": 75.53,
          "validation_sample_count": 710,
          "validation_neutralized_wrong_directional_rate_pct": 79.15,
          "quarterly_total_matched_count": 1511,
          "quarterly_max_fold_sample_share_pct": 27.86
        },
        "medium_20_caution": "The same composite scopes do not pass the neutralized wrong-rate threshold consistently in this split; train rates are around 57% to 59% while validation rates are above 71%."
      },
      "repair_focus_validation": {
        "decision": "repair_and_volume_tags_are_explanatory_not_active",
        "primary_split_2023_2026": {
          "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-focus.md",
          "dual_fast_dual_tail_medium_20": {
            "market_tail_repair_confirmed_sample_count": 94,
            "market_tail_repair_confirmed_neutralized_wrong_rate_pct": 97.87,
            "market_tail_bearish_continuation_sample_count": 492,
            "market_tail_bearish_continuation_neutralized_wrong_rate_pct": 85.37,
            "stock_volume_expansion_sample_count": 39,
            "stock_volume_expansion_neutralized_wrong_rate_pct": 97.44,
            "stock_volume_contraction_sample_count": 47,
            "stock_volume_contraction_neutralized_wrong_rate_pct": 70.21
          }
        },
        "non_overlapping_split_2021_2023": {
          "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-focus.md",
          "dual_fast_dual_tail_long_60": {
            "market_tail_repair_confirmed_sample_count": 334,
            "market_tail_repair_confirmed_neutralized_wrong_rate_pct": 76.95,
            "market_tail_bearish_continuation_sample_count": 1126,
            "market_tail_bearish_continuation_neutralized_wrong_rate_pct": 76.64,
            "stock_volume_expansion_sample_count": 109,
            "stock_volume_expansion_neutralized_wrong_rate_pct": 82.57,
            "stock_volume_contraction_sample_count": 179,
            "stock_volume_contraction_neutralized_wrong_rate_pct": 63.69
          }
        },
        "next_research_need": "Static same-day repair tags are not enough. Validate continuous repair variables such as MACD bar convergence days, RSI/KDJ rebound duration, BOLL lower-band recovery persistence, and volume expansion persistence."
      },
      "continuous_repair_focus_validation": {
        "decision": "continuous_repair_improves_explanation_but_not_active",
        "primary_split_2023_2026": {
          "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-continuous-repair.md",
          "market_continuous_repair_medium_20": {
            "train_sample_count": 203,
            "train_neutralized_wrong_directional_rate_pct": 77.34,
            "validation_sample_count": 70,
            "validation_neutralized_wrong_directional_rate_pct": 100.0,
            "quarterly_total_matched_count": 273,
            "quarterly_max_fold_sample_share_pct": 49.82
          },
          "stock_continuous_repair_medium_20": {
            "train_sample_count": 225,
            "train_neutralized_wrong_directional_rate_pct": 76.89,
            "validation_sample_count": 74,
            "validation_neutralized_wrong_directional_rate_pct": 100.0,
            "quarterly_total_matched_count": 299,
            "quarterly_max_fold_sample_share_pct": 56.52
          },
          "dual_continuous_repair_caution": {
            "train_sample_count": 91,
            "validation_sample_count": 27,
            "note": "Dual-side continuous repair is too narrow in the validation period for active promotion."
          }
        },
        "non_overlapping_split_2021_2023": {
          "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-continuous-repair.md",
          "market_continuous_repair_long_60": {
            "train_sample_count": 751,
            "train_neutralized_wrong_directional_rate_pct": 72.3,
            "validation_sample_count": 487,
            "validation_neutralized_wrong_directional_rate_pct": 73.72,
            "quarterly_total_matched_count": 1238,
            "quarterly_max_fold_sample_share_pct": 31.26
          },
          "stock_continuous_repair_long_60": {
            "train_sample_count": 636,
            "train_neutralized_wrong_directional_rate_pct": 72.33,
            "validation_sample_count": 470,
            "validation_neutralized_wrong_directional_rate_pct": 77.02,
            "quarterly_total_matched_count": 1106,
            "quarterly_max_fold_sample_share_pct": 29.48
          },
          "dual_continuous_repair_long_60": {
            "train_sample_count": 589,
            "train_neutralized_wrong_directional_rate_pct": 72.5,
            "validation_sample_count": 331,
            "validation_neutralized_wrong_directional_rate_pct": 74.32,
            "quarterly_total_matched_count": 920,
            "quarterly_max_fold_sample_share_pct": 32.72
          }
        },
        "conclusion": "Continuous repair variables are better diagnostic factors than static repair tags, but horizon drift remains: primary split leans medium_term 20/long_term 60 while 2021-2023 leans long_term 60. Keep as review/report factor only."
      }
    },
    "basket_level_validation": {
      "decision": "supports_sell_lag_interpretation_but_remains_candidate_only",
      "interpretation": "Same-date matched stocks are evaluated as equal-weight daily baskets to avoid overstating evidence from dense same-day signals. Basket validation supports the sell/avoid lag hypothesis, but effective basket counts are still limited and stage-concentrated.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-basket.md",
        "market_fast_stock_tail_medium_20_validation": {
          "basket_count": 6,
          "stock_signal_count": 202,
          "avg_basket_size": 33.67,
          "avg_basket_return_pct": 29.1,
          "positive_basket_rate_pct": 100.0,
          "worst_basket_date": "2024-09-10",
          "worst_basket_return_pct": 24.48
        },
        "market_fast_stock_tail_long_60_validation": {
          "basket_count": 6,
          "stock_signal_count": 202,
          "avg_basket_size": 33.67,
          "avg_basket_return_pct": 32.01,
          "positive_basket_rate_pct": 100.0,
          "worst_basket_date": "2024-09-12",
          "worst_basket_return_pct": 29.03
        },
        "dual_fast_dual_tail_medium_20_validation": {
          "basket_count": 6,
          "stock_signal_count": 153,
          "avg_basket_size": 25.5,
          "avg_basket_return_pct": 29.51,
          "positive_basket_rate_pct": 100.0,
          "worst_basket_date": "2024-09-10",
          "worst_basket_return_pct": 24.83
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-basket.md",
        "raw_cross_regime_long_60_validation": {
          "basket_count": 22,
          "stock_signal_count": 881,
          "avg_basket_size": 40.05,
          "avg_basket_return_pct": 13.03,
          "positive_basket_rate_pct": 100.0,
          "worst_basket_date": "2022-09-21",
          "worst_basket_return_pct": 1.5
        },
        "market_fast_stock_tail_long_60_validation": {
          "basket_count": 22,
          "stock_signal_count": 858,
          "avg_basket_size": 39.0,
          "avg_basket_return_pct": 13.25,
          "positive_basket_rate_pct": 100.0,
          "worst_basket_date": "2022-09-21",
          "worst_basket_return_pct": 1.5
        }
      },
      "caution": "Basket-level evidence reduces the concern that single-stock samples are inflated by dense signal days, but it also shows candidate evidence is concentrated in a small number of daily baskets. Do not promote to active until future or non-overlapping windows show stable basket-level behavior and horizon drift is resolved."
    },
    "horizon_profile_validation": {
      "decision": "horizon_drift_is_repair_speed_not_fixed_window",
      "interpretation": "Cross-horizon profiling keeps the candidate direction/factor scope fixed and compares 1/3/5/10/20/60/120 day outcomes. The repeated sell-lag pattern appears across windows, but the stable action window changes with repair speed.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-horizon-profile.md",
        "market_fast_stock_tail_validation_avg_return_pct": {
          "short_1": 0.15,
          "short_3": 0.11,
          "short_5": 2.51,
          "medium_10": 27.41,
          "medium_20": 29.2,
          "long_60": 32.06,
          "long_120": 29.21
        },
        "dual_fast_dual_tail_validation_avg_return_pct": {
          "short_1": 0.02,
          "short_3": 0.04,
          "short_5": 2.73,
          "medium_10": 29.1,
          "medium_20": 29.84,
          "long_60": 31.88,
          "long_120": 27.83
        },
        "lesson": "The rebound is already visible by 10-20 trading days and persists to 60 days. Medium-term downgrade is explainable here, although 60-day returns are slightly stronger."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-horizon-profile.md",
        "raw_cross_regime_validation_avg_return_pct": {
          "short_1": 0.09,
          "short_3": 0.22,
          "short_5": 1.21,
          "medium_10": 2.74,
          "medium_20": 5.01,
          "long_60": 12.0,
          "long_120": 29.08
        },
        "market_fast_stock_tail_validation_avg_return_pct": {
          "short_1": 0.09,
          "short_3": 0.22,
          "short_5": 1.2,
          "medium_10": 2.65,
          "medium_20": 4.98,
          "long_60": 12.06,
          "long_120": 28.77
        },
        "market_fast_stock_tail_train_avg_return_pct": {
          "medium_20": 2.9,
          "long_60": 12.95,
          "long_120": 3.44
        },
        "dual_fast_dual_tail_validation_avg_return_pct": {
          "medium_20": 5.47,
          "long_60": 12.85,
          "long_120": 31.63
        },
        "dual_fast_dual_tail_train_avg_return_pct": {
          "medium_20": 3.73,
          "long_60": 14.19,
          "long_120": 4.43
        },
        "lesson": "The 20-day response is weak, 60-day response is stable in both train and validation, and 120-day validation extension is strong but not stable in training. This split supports long_term 60 rather than long_term 120 active promotion."
      },
      "caution": "Do not hard-code medium 20 or long 60 as active until a repair-speed classifier can separate fast rebounds from slow repairs. Cross-horizon profile is now a required candidate validation gate."
    },
    "repair_speed_focus_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Discrete repair-speed labels help explain slow-repair 60-day stability, but fast-repair labels are too sparse to support active rules. Keep repair_speed as a report/stage factor and move next research toward continuous speed metrics.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-speed.md",
        "fast_repair_caution": {
          "market_fast_repair_validation_sample_count": 0,
          "stock_fast_repair_train_sample_count": 7,
          "stock_fast_repair_validation_sample_count": 2,
          "lesson": "Fast-repair definitions are too narrow in this split; they cannot explain the broad 20-day rebound signal."
        },
        "market_gradual_repair": {
          "medium_20_train_sample_count": 98,
          "medium_20_train_neutralized_wrong_directional_rate_pct": 56.12,
          "medium_20_validation_sample_count": 70,
          "medium_20_validation_neutralized_wrong_directional_rate_pct": 100.0,
          "medium_20_validation_basket_count": 2,
          "medium_20_validation_avg_basket_return_pct": 28.52,
          "long_60_train_neutralized_wrong_directional_rate_pct": 66.33,
          "long_60_validation_neutralized_wrong_directional_rate_pct": 100.0,
          "long_60_validation_avg_basket_return_pct": 33.67
        },
        "stock_gradual_repair": {
          "medium_20_train_sample_count": 181,
          "medium_20_train_neutralized_wrong_directional_rate_pct": 79.56,
          "medium_20_validation_sample_count": 58,
          "medium_20_validation_neutralized_wrong_directional_rate_pct": 100.0,
          "medium_20_validation_basket_count": 6,
          "medium_20_validation_avg_basket_return_pct": 29.34,
          "long_60_train_neutralized_wrong_directional_rate_pct": 66.85,
          "long_60_validation_neutralized_wrong_directional_rate_pct": 100.0,
          "long_60_validation_avg_basket_return_pct": 33.5
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-speed.md",
        "market_gradual_repair": {
          "medium_20_train_sample_count": 581,
          "medium_20_train_neutralized_wrong_directional_rate_pct": 60.07,
          "medium_20_validation_sample_count": 487,
          "medium_20_validation_neutralized_wrong_directional_rate_pct": 63.66,
          "medium_20_validation_avg_basket_return_pct": 3.54,
          "long_60_train_neutralized_wrong_directional_rate_pct": 73.67,
          "long_60_validation_neutralized_wrong_directional_rate_pct": 73.72,
          "long_60_validation_avg_basket_return_pct": 9.6,
          "long_120_caution": "Validation extension is strong, but training is weak; do not promote long_120."
        },
        "stock_gradual_repair": {
          "medium_20_train_sample_count": 483,
          "medium_20_train_neutralized_wrong_directional_rate_pct": 59.21,
          "medium_20_validation_sample_count": 399,
          "medium_20_validation_neutralized_wrong_directional_rate_pct": 69.67,
          "medium_20_validation_avg_basket_return_pct": 4.96,
          "long_60_train_neutralized_wrong_directional_rate_pct": 72.05,
          "long_60_validation_neutralized_wrong_directional_rate_pct": 77.44,
          "long_60_validation_avg_basket_return_pct": 13.24,
          "long_120_caution": "Validation extension is strong, but training is weak; do not promote long_120."
        }
      },
      "next_research_need": "Use continuous speed metrics as diagnostic horizon selectors, then validate whether they remain stable on future matured rows and additional non-overlapping splits."
    },
    "continuous_speed_focus_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Continuous speed metrics improve the explanation of sell/avoid lag and strengthen the 60-day slow-repair profile, but they still do not resolve horizon drift enough for active promotion. Treat repair_speed_profile and component speed fields as report/stage factors only.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-continuous-speed.md",
        "market_speed_profile_medium_20": {
          "train_sample_count": 170,
          "train_neutralized_wrong_directional_rate_pct": 86.47,
          "validation_sample_count": 35,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 1,
          "validation_avg_basket_return_pct": 32.56
        },
        "market_speed_profile_long_60": {
          "train_sample_count": 170,
          "train_neutralized_wrong_directional_rate_pct": 73.53,
          "validation_sample_count": 35,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 1,
          "validation_avg_basket_return_pct": 30.72
        },
        "stock_speed_profile_long_60": {
          "train_sample_count": 98,
          "train_neutralized_wrong_directional_rate_pct": 79.59,
          "validation_sample_count": 32,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 33.93
        },
        "caution": "Validation returns are strong but effective basket counts are small, especially for market-level speed profile; do not promote from this split alone."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-continuous-speed.md",
        "market_speed_profile_long_60": {
          "train_sample_count": 637,
          "train_neutralized_wrong_directional_rate_pct": 72.68,
          "validation_sample_count": 199,
          "validation_neutralized_wrong_directional_rate_pct": 84.92,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 17.06
        },
        "stock_speed_profile_long_60": {
          "train_sample_count": 426,
          "train_neutralized_wrong_directional_rate_pct": 72.3,
          "validation_sample_count": 224,
          "validation_neutralized_wrong_directional_rate_pct": 80.8,
          "validation_basket_count": 20,
          "validation_avg_basket_return_pct": 9.65
        },
        "dual_speed_profile_long_60": {
          "train_sample_count": 369,
          "train_neutralized_wrong_directional_rate_pct": 73.71,
          "validation_sample_count": 107,
          "validation_neutralized_wrong_directional_rate_pct": 84.11,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 14.18
        },
        "stock_macd_boll_speed_long_60": {
          "train_sample_count": 395,
          "train_neutralized_wrong_directional_rate_pct": 70.89,
          "validation_sample_count": 188,
          "validation_neutralized_wrong_directional_rate_pct": 84.04,
          "validation_basket_count": 21,
          "validation_avg_basket_return_pct": 11.73
        }
      },
      "conclusion": "Continuous speed factors are better diagnostics than discrete speed labels for explaining 60-day repair, but the primary split still has limited validation baskets and the 20-day versus 60-day choice remains regime-dependent."
    },
    "speed_horizon_selector_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "The deduplicated speed-horizon selector table makes horizon drift explicit: 2021-2023 consistently favors 60-day review across all continuous-speed scopes, while 2023-2026 remains too concentrated to lock a 20-day or 60-day active rule.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-speed-horizon.md",
        "market_speed_profile": {
          "train_20_avg_return_pct": 11.57,
          "train_60_avg_return_pct": 10.72,
          "validation_20_sample_count": 35,
          "validation_20_basket_count": 1,
          "validation_20_avg_return_pct": 32.56,
          "validation_60_sample_count": 35,
          "validation_60_basket_count": 1,
          "validation_60_avg_return_pct": 30.72,
          "selector_verdict": "validation_baskets_insufficient"
        },
        "stock_speed_profile": {
          "train_20_avg_return_pct": 8.44,
          "train_60_avg_return_pct": 9.21,
          "validation_20_sample_count": 32,
          "validation_20_basket_count": 6,
          "validation_20_avg_return_pct": 35.07,
          "validation_60_sample_count": 32,
          "validation_60_basket_count": 6,
          "validation_60_avg_return_pct": 35.82,
          "selector_verdict": "validation_samples_insufficient"
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-speed-horizon.md",
        "market_speed_profile": {
          "train_20_avg_return_pct": 2.41,
          "train_60_avg_return_pct": 11.9,
          "validation_20_avg_return_pct": 6.9,
          "validation_60_avg_return_pct": 16.24,
          "validation_basket_count": 6,
          "selector_verdict": "60_day_more_stable"
        },
        "stock_speed_profile": {
          "train_20_avg_return_pct": 2.82,
          "train_60_avg_return_pct": 12.4,
          "validation_20_avg_return_pct": 5.61,
          "validation_60_avg_return_pct": 11.4,
          "validation_basket_count": 20,
          "selector_verdict": "60_day_more_stable"
        },
        "dual_speed_profile": {
          "train_20_avg_return_pct": 3.43,
          "train_60_avg_return_pct": 13.4,
          "validation_20_avg_return_pct": 7.29,
          "validation_60_avg_return_pct": 14.05,
          "validation_basket_count": 6,
          "selector_verdict": "60_day_more_stable"
        },
        "stock_macd_boll_speed": {
          "train_20_avg_return_pct": 1.7,
          "train_60_avg_return_pct": 10.35,
          "validation_20_avg_return_pct": 5.78,
          "validation_60_avg_return_pct": 12.42,
          "validation_basket_count": 21,
          "selector_verdict": "60_day_more_stable"
        },
        "long_120_caution": "120-day validation returns are high, but training returns are not stable enough to promote a 120-day active rule."
      },
      "conclusion": "Use continuous speed metrics to prioritize manual/research review toward 60-day slow-repair checks. Do not hard-code 20, 60, or 120 days into active adjustments until future matured rows confirm the selector."
    },
    "speed_counterexample_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Counterexample diagnostics split continuous-speed 60-day sell/avoid candidates into effective risk-control cases versus lagging false negatives. Real counterexamples point to repair-quality problems, not to rejecting the 60-day slow-repair thesis.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-speed-counterexample.md",
        "validation_counterexample_summary": {
          "market_speed_profile_effective_risk_count": 0,
          "stock_speed_profile_effective_risk_count": 0,
          "dual_speed_profile_effective_risk_count": 0,
          "stock_macd_boll_speed_effective_risk_count": 0,
          "caution": "Validation segment has strong sell/avoid lag but few baskets; absence of counterexamples here is not enough for active promotion."
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-speed-counterexample.md",
        "market_speed_profile_validation_counterexamples": {
          "tail_repair_unconfirmed": {
            "factor": "tail_repair_signal=低位放量未确认",
            "sample_count": 17,
            "effective_risk_count": 5,
            "lagging_false_negative_count": 12,
            "effective_risk_rate_pct": 29.41
          },
          "volume_expansion_deteriorating": {
            "factor": "volume_expansion_speed=速度恶化",
            "sample_count": 22,
            "effective_risk_count": 6,
            "lagging_false_negative_count": 16,
            "effective_risk_rate_pct": 27.27
          },
          "decline_speed_flat": {
            "factor": "decline_speed=跌速持平",
            "sample_count": 26,
            "effective_risk_count": 6,
            "lagging_false_negative_count": 20,
            "effective_risk_rate_pct": 23.08
          }
        },
        "stock_speed_profile_validation_counterexamples": {
          "market_macd_deteriorating": {
            "factor": "market_macd_repair_speed=速度恶化",
            "sample_count": 28,
            "effective_risk_count": 12,
            "lagging_false_negative_count": 16,
            "effective_risk_rate_pct": 42.86
          },
          "tail_repair_unconfirmed": {
            "factor": "tail_repair_signal=低位放量未确认",
            "sample_count": 12,
            "effective_risk_count": 5,
            "lagging_false_negative_count": 7,
            "effective_risk_rate_pct": 41.67
          },
          "local_volume_expansion_not_enough": {
            "factor": "volume_expansion_speed=速度改善明显",
            "sample_count": 11,
            "effective_risk_count": 4,
            "lagging_false_negative_count": 7,
            "effective_risk_rate_pct": 36.36
          }
        }
      },
      "conclusion": "Before any active neutralize-to-watch rule, require repair-quality confirmation: volume expansion must be persistent, low-position volume must be confirmed rather than unconfirmed, market MACD repair must not be deteriorating, and decline speed should show real deceleration."
    },
    "repair_quality_focus_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Repair-quality confirmation is necessary but not sufficient. It can narrow sell/avoid lag samples, especially on stock-side quality, but single-side confirmation still leaves counterexamples when the other side deteriorates.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-quality.md",
        "stock_quality_confirmed_long_60": {
          "train_sample_count": 26,
          "train_neutralized_wrong_directional_rate_pct": 92.31,
          "validation_sample_count": 15,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 31.44
        },
        "market_quality_confirmed_caution": "Validation has no matched samples; do not promote market-quality confirmation from this split.",
        "dual_quality_confirmed_caution": "Validation has no matched samples and training has only 5 matched long_60 samples."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-quality.md",
        "market_quality_confirmed_long_60": {
          "train_sample_count": 225,
          "train_neutralized_wrong_directional_rate_pct": 69.78,
          "validation_sample_count": 89,
          "validation_neutralized_wrong_directional_rate_pct": 85.39,
          "validation_basket_count": 3,
          "validation_avg_basket_return_pct": 17.15
        },
        "stock_quality_confirmed_long_60": {
          "train_sample_count": 119,
          "train_neutralized_wrong_directional_rate_pct": 73.95,
          "validation_sample_count": 73,
          "validation_neutralized_wrong_directional_rate_pct": 82.19,
          "validation_basket_count": 16,
          "validation_avg_basket_return_pct": 7.49
        },
        "dual_quality_confirmed_long_60": {
          "train_sample_count": 73,
          "train_neutralized_wrong_directional_rate_pct": 76.71,
          "validation_sample_count": 24,
          "validation_neutralized_wrong_directional_rate_pct": 83.33,
          "validation_basket_count": 3,
          "validation_avg_basket_return_pct": 7.07
        },
        "remaining_counterexamples": {
          "market_quality_with_stock_volume_deterioration": {
            "factor": "volume_expansion_speed=速度恶化",
            "sample_count": 19,
            "effective_risk_rate_pct": 31.58
          },
          "market_quality_with_flat_stock_decline_speed": {
            "factor": "decline_speed=跌速持平",
            "sample_count": 8,
            "effective_risk_rate_pct": 25.0
          },
          "stock_quality_with_market_quality_deterioration": {
            "factor": "market_repair_quality_confirmation=修复质量恶化",
            "sample_count": 11,
            "effective_risk_rate_pct": 27.27
          }
        }
      },
      "conclusion": "Require synchronized repair quality before active promotion: one side may confirm, but the other side must at least not deteriorate. Current evidence supports diagnostic gating only."
    },
    "repair_quality_sync_validation": {
      "decision": "diagnostic_gate_only_not_active",
      "interpretation": "Synchronized repair quality is useful as a defense condition: at least one side should confirm repair quality and the other side must not deteriorate. It narrows sell/avoid lag samples in the 2021-2023 slow-repair split, but the 2023-2026 validation sample is too sparse and horizon drift remains unresolved.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-quality-sync.md",
        "sync_non_deteriorating_long_60": {
          "train_sample_count": 34,
          "train_neutralized_wrong_directional_rate_pct": 88.24,
          "validation_sample_count": 1,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 1,
          "validation_avg_basket_return_pct": 21.41
        },
        "dual_sync_confirmed_long_60": {
          "train_sample_count": 5,
          "train_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_sample_count": 0,
          "validation_neutralized_wrong_directional_rate_pct": null,
          "validation_basket_count": 0
        },
        "caution": "The validation period has only one non-deteriorating matched sample and no dual-sync samples; do not promote from this split."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-quality-sync.md",
        "sync_non_deteriorating_long_60": {
          "train_sample_count": 190,
          "train_neutralized_wrong_directional_rate_pct": 69.47,
          "validation_sample_count": 90,
          "validation_neutralized_wrong_directional_rate_pct": 85.56,
          "validation_basket_count": 11,
          "validation_avg_basket_return_pct": 11.15,
          "validation_positive_basket_rate_pct": 90.91
        },
        "single_side_opposite_safe_long_60": {
          "train_sample_count": 117,
          "train_neutralized_wrong_directional_rate_pct": 64.96,
          "validation_sample_count": 66,
          "validation_neutralized_wrong_directional_rate_pct": 86.36,
          "validation_basket_count": 11,
          "validation_avg_basket_return_pct": 12.6,
          "validation_positive_basket_rate_pct": 90.91
        },
        "dual_sync_confirmed_long_60": {
          "train_sample_count": 73,
          "train_neutralized_wrong_directional_rate_pct": 76.71,
          "validation_sample_count": 24,
          "validation_neutralized_wrong_directional_rate_pct": 83.33,
          "validation_basket_count": 3,
          "validation_avg_basket_return_pct": 7.07,
          "validation_positive_basket_rate_pct": 100.0
        }
      },
      "conclusion": "Use repair_quality_sync as a report/review factor and counterexample filter. It can raise review priority for sell/avoid neutralization in slow repair, but it is not enough for active promotion and never implies a buy signal."
    },
    "repair_quality_failure_focus_validation": {
      "decision": "diagnostic_only_not_active_scope",
      "interpretation": "Repair-quality failure is not a binary exclusion from sell/avoid neutralization. Even when sync deteriorates or remains insufficient, most matched sell/avoid signals are still lagging false negatives in the 2021-2023 slow-repair split and nearly all are lagging in the 2023-2026 validation split. The useful next layer is narrower effective-risk pockets, not broad preservation of sell/avoid.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-quality-failure.md",
        "sync_deteriorating_long_60": {
          "train_sample_count": 346,
          "train_neutralized_wrong_directional_rate_pct": 61.85,
          "validation_sample_count": 126,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 5,
          "validation_avg_basket_return_pct": 31.55
        },
        "dual_deteriorating_long_60": {
          "train_sample_count": 254,
          "train_neutralized_wrong_directional_rate_pct": 56.69,
          "validation_sample_count": 111,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 5,
          "validation_avg_basket_return_pct": 30.54
        },
        "sync_insufficient_long_60": {
          "train_sample_count": 147,
          "train_neutralized_wrong_directional_rate_pct": 65.99,
          "validation_sample_count": 75,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 34.37
        }
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-quality-failure.md",
        "sync_deteriorating_long_60": {
          "train_sample_count": 350,
          "train_neutralized_wrong_directional_rate_pct": 76.86,
          "validation_sample_count": 326,
          "validation_neutralized_wrong_directional_rate_pct": 76.38,
          "validation_basket_count": 13,
          "validation_avg_basket_return_pct": 14.54,
          "validation_positive_basket_rate_pct": 100.0
        },
        "dual_deteriorating_long_60": {
          "train_sample_count": 268,
          "train_neutralized_wrong_directional_rate_pct": 79.1,
          "validation_sample_count": 278,
          "validation_neutralized_wrong_directional_rate_pct": 75.54,
          "validation_basket_count": 10,
          "validation_avg_basket_return_pct": 12.93,
          "validation_positive_basket_rate_pct": 100.0
        },
        "sync_insufficient_long_60": {
          "train_sample_count": 511,
          "train_neutralized_wrong_directional_rate_pct": 73.97,
          "validation_sample_count": 442,
          "validation_neutralized_wrong_directional_rate_pct": 79.19,
          "validation_basket_count": 19,
          "validation_avg_basket_return_pct": 11.86,
          "validation_positive_basket_rate_pct": 84.21
        },
        "effective_risk_pockets": {
          "market_macd_not_improving_with_market_speed_divergence": {
            "factors": ["market_macd_repair_speed=速度未改善", "market_repair_speed_profile=速度分化"],
            "validation_sample_count": 22,
            "effective_risk_rate_pct": 50.0
          },
          "dual_deteriorating_with_stock_volume_worse": {
            "factor": "volume_expansion_speed=速度恶化",
            "validation_sample_count": 79,
            "effective_risk_rate_pct": 36.71
          },
          "sync_insufficient_with_market_quality_deterioration": {
            "factor": "market_repair_quality_confirmation=修复质量恶化",
            "validation_sample_count": 98,
            "effective_risk_rate_pct": 29.59
          },
          "sync_insufficient_with_tail_pending": {
            "factor": "tail_repair_signal=低位待确认",
            "validation_sample_count": 6,
            "effective_risk_rate_pct": 66.67,
            "caution": "Too sparse for rule promotion."
          }
        }
      },
      "conclusion": "Do not exclude all repair-quality failure states from neutralize-to-watch research. Instead, test narrower defense pockets around market MACD non-improvement, market speed divergence, stock volume deterioration, and pending low-position repair."
    },
    "repair_quality_defense_pocket_validation": {
      "decision": "diagnostic_risk_discount_only_not_active",
      "interpretation": "Narrow defense pockets did not find stable binary conditions for preserving sell/avoid. Most matched sell/avoid signals remain lagging false negatives, so these pockets should reduce confidence in neutralization and raise manual-review priority rather than exclude samples from neutralize-to-watch research.",
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-repair-quality-defense-pocket.md",
        "market_macd_speed_divergence": {
          "long_60_train_sample_count": 0,
          "long_60_validation_sample_count": 0,
          "note": "No matched samples in this split."
        },
        "stock_volume_deterioration_long_60": {
          "train_sample_count": 77,
          "train_neutralized_wrong_directional_rate_pct": 59.74,
          "validation_sample_count": 41,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 6,
          "validation_avg_basket_return_pct": 36.1
        },
        "market_quality_deterioration_long_60": {
          "train_sample_count": 324,
          "train_neutralized_wrong_directional_rate_pct": 60.19,
          "validation_sample_count": 167,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 5,
          "validation_avg_basket_return_pct": 32.27
        },
        "tail_pending_long_60": {
          "train_sample_count": 36,
          "train_neutralized_wrong_directional_rate_pct": 66.67,
          "validation_sample_count": 24,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 5,
          "validation_avg_basket_return_pct": 28.15
        },
        "market_quality_stock_volume_defense_long_60": {
          "train_sample_count": 28,
          "train_neutralized_wrong_directional_rate_pct": 39.29,
          "validation_sample_count": 33,
          "validation_neutralized_wrong_directional_rate_pct": 100.0,
          "validation_basket_count": 5,
          "validation_avg_basket_return_pct": 36.72
        },
        "lesson": "The validation segment remains dominated by sell/avoid lag even inside quality-deterioration and volume-deterioration pockets."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-repair-quality-defense-pocket.md",
        "market_macd_speed_divergence_long_60": {
          "train_sample_count": 63,
          "train_neutralized_wrong_directional_rate_pct": 57.14,
          "validation_sample_count": 131,
          "validation_neutralized_wrong_directional_rate_pct": 75.57,
          "validation_basket_count": 3,
          "validation_avg_basket_return_pct": 8.35
        },
        "stock_volume_deterioration_long_60": {
          "train_sample_count": 239,
          "train_neutralized_wrong_directional_rate_pct": 69.04,
          "validation_sample_count": 149,
          "validation_neutralized_wrong_directional_rate_pct": 69.8,
          "validation_basket_count": 21,
          "validation_avg_basket_return_pct": 11.56,
          "validation_positive_basket_rate_pct": 90.48
        },
        "market_quality_deterioration_long_60": {
          "train_sample_count": 355,
          "train_neutralized_wrong_directional_rate_pct": 76.34,
          "validation_sample_count": 387,
          "validation_neutralized_wrong_directional_rate_pct": 74.16,
          "validation_basket_count": 10,
          "validation_avg_basket_return_pct": 12.1,
          "validation_positive_basket_rate_pct": 100.0
        },
        "tail_pending_long_60": {
          "train_sample_count": 29,
          "train_neutralized_wrong_directional_rate_pct": 72.41,
          "validation_sample_count": 19,
          "validation_neutralized_wrong_directional_rate_pct": 78.95,
          "validation_basket_count": 9,
          "validation_avg_basket_return_pct": 4.02,
          "validation_positive_basket_rate_pct": 77.78
        },
        "market_quality_stock_volume_defense_long_60": {
          "train_sample_count": 42,
          "train_neutralized_wrong_directional_rate_pct": 61.9,
          "validation_sample_count": 80,
          "validation_neutralized_wrong_directional_rate_pct": 62.5,
          "validation_basket_count": 10,
          "validation_avg_basket_return_pct": 9.63,
          "validation_positive_basket_rate_pct": 90.0
        },
        "relative_defense_signals": {
          "market_quality_stock_volume_defense_validation_rate_pct": 62.5,
          "note": "This is the lowest and most defense-like pocket, but it still contains more lagging false negatives than effective risk-control cases. Treat it as relative caution only."
        }
      },
      "conclusion": "Do not promote defense pockets to active exclusions. Use them as report-level risk discounts and counterexample diagnostics until multiple non-overlapping windows show effective risk-control rates exceeding lagging false-negative rates."
    },
    "neutralize_confidence_validation": {
      "decision": "report_level_ranking_only_not_active",
      "interpretation": "Neutralize confidence converts sell/avoid neutralize-to-watch simulations into a continuous review score. It uses validation lagging false-negative rate as the main signal, subtracts evidence penalties for thin validation samples or baskets, and reports effective risk-control rate as the counterexample discount. This ranks manual review priority but does not adjust scorer output.",
      "scoring_definition": {
        "base_confidence": "0.6 * validation_neutralized_wrong_directional_rate_pct + 0.4 * train_neutralized_wrong_directional_rate_pct when both exist; otherwise validation rate only.",
        "evidence_penalty": "20 points when validation samples < 50 or validation baskets < 3; 10 points when validation samples < 100 or validation baskets < 6; otherwise 0.",
        "effective_risk_rate_pct": "100 - validation_neutralized_wrong_directional_rate_pct",
        "verdicts": {
          "high": "confidence >= 75 and validation evidence is sufficient",
          "medium": "confidence >= 60",
          "low_review_only": "confidence >= 45",
          "preserve_risk_bias": "confidence < 45",
          "thin_sample": "validation samples < 50 or validation baskets < 3"
        }
      },
      "primary_split_2023_2026": {
        "report": "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-neutralize-confidence.md",
        "top_high_confidence": {
          "market_fast_stock_tail_medium_20_confidence_pct": 93.32,
          "market_fast_tail_medium_20_confidence_pct": 93.3,
          "dual_fast_dual_tail_medium_20_confidence_pct": 93.16
        },
        "defense_pocket_examples": {
          "market_quality_deterioration_long_60": {
            "validation_sample_count": 167,
            "validation_basket_count": 5,
            "confidence_pct": 74.07,
            "verdict": "medium_confidence_neutralize"
          },
          "stock_volume_deterioration_long_60": {
            "validation_sample_count": 41,
            "validation_basket_count": 6,
            "confidence_pct": 63.9,
            "verdict": "thin_sample_stage_signal"
          },
          "market_quality_stock_volume_defense_long_60": {
            "validation_sample_count": 33,
            "validation_basket_count": 5,
            "confidence_pct": 55.71,
            "verdict": "thin_sample_stage_signal"
          }
        },
        "lesson": "The primary split remains a strong rebound segment. The confidence table must penalize thin samples; otherwise small defense pockets can look overly strong."
      },
      "non_overlapping_split_2021_2023": {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-neutralize-confidence.md",
        "top_high_confidence": {
          "market_speed_profile_long_60_confidence_pct": 80.03,
          "dual_speed_profile_long_60_confidence_pct": 79.95,
          "stock_macd_boll_speed_long_60_confidence_pct": 78.78,
          "raw_cross_regime_long_60_confidence_pct": 78.01
        },
        "defense_pocket_examples": {
          "market_quality_deterioration_long_60": {
            "validation_sample_count": 387,
            "validation_basket_count": 10,
            "effective_risk_rate_pct": 25.84,
            "confidence_pct": 75.03,
            "verdict": "high_confidence_neutralize"
          },
          "stock_volume_deterioration_long_60": {
            "validation_sample_count": 149,
            "validation_basket_count": 21,
            "effective_risk_rate_pct": 30.2,
            "confidence_pct": 69.49,
            "verdict": "medium_confidence_neutralize"
          },
          "market_macd_speed_divergence_long_60": {
            "validation_sample_count": 131,
            "validation_basket_count": 3,
            "effective_risk_rate_pct": 24.43,
            "confidence_pct": 58.2,
            "verdict": "low_confidence_review_only"
          },
          "market_quality_stock_volume_defense_long_60": {
            "validation_sample_count": 80,
            "validation_basket_count": 10,
            "effective_risk_rate_pct": 37.5,
            "confidence_pct": 52.26,
            "verdict": "low_confidence_review_only"
          }
        },
        "lesson": "Continuous confidence separates the main slow-repair neutralize thesis from relative defense pockets. Defense pockets can reduce neutralization confidence, but they still do not justify active preservation of sell/avoid."
      },
      "conclusion": "Use neutralize_confidence as a report-level continuous diagnostic: high confidence can prioritize manual downgrade-to-watch review, medium confidence stays candidate-only, low confidence is review-only, and thin samples are stage signals. Keep active_adjustments empty."
    },
    "single_signal_review_validation": {
      "decision": "case_review_and_report_drilldown_only_not_active",
      "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-signal-review.md",
      "interpretation": "Single-signal review maps rule-level neutralize_confidence back to individual historical sell/avoid signals. It is useful for case review because each row shows the stock, signal date, horizon/window, original score and signal, later return, drawdown, matched rule count, top matched rule, confidence, and effective risk rate. It does not adjust scorer output.",
      "top_block_observation": {
        "dates": ["2022-03-17", "2022-03-18"],
        "top_rule_id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60",
        "top_rule_confidence_pct": 80.03,
        "top_rule_effective_risk_rate_pct": 15.08,
        "examples": [
          {
            "code": "000001",
            "name": "平安银行",
            "signal_date": "2022-03-17",
            "original_score": -69,
            "original_signal": "强卖/回避",
            "future_return_pct": 0.0,
            "outcome_type": "滞后误杀",
            "drawdown_pct": -3.78,
            "matched_rule_count": 14
          },
          {
            "code": "000625",
            "name": "长安汽车",
            "signal_date": "2022-03-17",
            "original_score": -60,
            "original_signal": "强卖/回避",
            "future_return_pct": 68.46,
            "outcome_type": "滞后误杀",
            "drawdown_pct": -19.4,
            "matched_rule_count": 12
          },
          {
            "code": "002466",
            "name": "天齐锂业",
            "signal_date": "2022-03-17",
            "original_score": -54,
            "original_signal": "强卖/回避",
            "future_return_pct": 39.72,
            "outcome_type": "滞后误杀",
            "drawdown_pct": -30.26,
            "matched_rule_count": 12
          },
          {
            "code": "300015",
            "name": "爱尔眼科",
            "signal_date": "2022-03-17",
            "original_score": -69,
            "original_signal": "强卖/回避",
            "future_return_pct": 35.84,
            "outcome_type": "滞后误杀",
            "drawdown_pct": -4.77,
            "matched_rule_count": 13
          }
        ]
      },
      "daily_summary_observation": {
        "interpretation": "Daily aggregation shows that the single-signal top rows are partly a sort-order artifact. High-confidence downgrade baskets are spread across multiple 2022 slow-repair blocks, not only 2022-03-17/18.",
        "top_daily_baskets": [
          {
            "signal_date": "2022-04-27",
            "signal_count": 55,
            "lagging_false_negative_count": 50,
            "effective_risk_count": 5,
            "avg_return_pct": 23.35,
            "worst_return_pct": -11.9,
            "avg_confidence_pct": 80.03,
            "top_rule_id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60"
          },
          {
            "signal_date": "2022-04-28",
            "signal_count": 49,
            "lagging_false_negative_count": 46,
            "effective_risk_count": 3,
            "avg_return_pct": 22.18,
            "worst_return_pct": -9.36,
            "avg_confidence_pct": 80.03,
            "top_rule_id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60"
          },
          {
            "signal_date": "2022-03-17",
            "signal_count": 52,
            "lagging_false_negative_count": 30,
            "effective_risk_count": 22,
            "avg_return_pct": 4.97,
            "worst_return_pct": -11.63,
            "avg_confidence_pct": 79.91,
            "top_rule_id": "continuous_speed_focus:market-speed-profile:sell_avoid:long_term:60"
          }
        ],
        "stage_blocks": ["2022-03", "2022-04", "2022-05", "2022-10", "2022-11"]
      },
      "stage_block_summary_observation": {
        "interpretation": "Stage-block aggregation checks whether daily baskets are isolated dates or repeated slow-repair blocks. Long-term 60-day evidence is strongest in 2022-Q2 and 2022-Q4, while medium-term 20-day evidence remains horizon-sensitive.",
        "monthly_long_60_examples": [
          {
            "period": "2022-04",
            "daily_basket_count": 9,
            "signal_count": 451,
            "lagging_false_negative_count": 400,
            "effective_risk_count": 51,
            "lagging_false_negative_rate_pct": 88.69,
            "avg_daily_basket_return_pct": 20.82,
            "worst_daily_basket_return_pct": 14.79,
            "effective_risk_dominant_day_share_pct": 0.0
          },
          {
            "period": "2022-10",
            "daily_basket_count": 12,
            "signal_count": 461,
            "lagging_false_negative_count": 408,
            "effective_risk_count": 53,
            "lagging_false_negative_rate_pct": 88.5,
            "avg_daily_basket_return_pct": 18.52,
            "worst_daily_basket_return_pct": 11.25,
            "effective_risk_dominant_day_share_pct": 0.0
          }
        ],
        "quarterly_long_60_examples": [
          {
            "period": "2022-Q2",
            "daily_basket_count": 20,
            "signal_count": 863,
            "lagging_false_negative_count": 723,
            "effective_risk_count": 140,
            "lagging_false_negative_rate_pct": 83.78,
            "avg_daily_basket_return_pct": 15.71,
            "worst_daily_basket_return_pct": 8.17,
            "effective_risk_dominant_day_share_pct": 0.0
          },
          {
            "period": "2022-Q4",
            "daily_basket_count": 13,
            "signal_count": 487,
            "lagging_false_negative_count": 432,
            "effective_risk_count": 55,
            "lagging_false_negative_rate_pct": 88.71,
            "avg_daily_basket_return_pct": 18.96,
            "worst_daily_basket_return_pct": 11.25,
            "effective_risk_dominant_day_share_pct": 0.0
          }
        ],
        "horizon_caution": {
          "period": "2022-Q1",
          "medium_20_lagging_false_negative_rate_pct": 31.65,
          "medium_20_avg_daily_basket_return_pct": -4.8,
          "medium_20_effective_risk_dominant_day_share_pct": 90.0,
          "long_60_lagging_false_negative_rate_pct": 65.29,
          "long_60_avg_daily_basket_return_pct": 7.85,
          "lesson": "The same stage can preserve short-horizon risk control while later proving sell/avoid lag at 60 days. Do not promote a fixed medium-term neutralization rule."
        }
      },
      "stage_factor_profile_observation": {
        "decision": "diagnostic_only_not_active",
        "interpretation": "Stage factor profiles show the strongest 60-day sell/avoid lag often occurs before repair is confirmed. Market and stock trends are still down, decline speed is often accelerating, repair speed is not formed, volume expansion is not improved, and repair quality is insufficient or deteriorating. These states must not be used as broad exclusions from neutralize-to-watch research.",
        "q2_long_60": {
          "market_repair_speed_profile_speed_not_formed": {
            "sample_count": 301,
            "stage_sample_share_pct": 34.88,
            "lagging_false_negative_rate_pct": 88.04,
            "avg_return_pct": 21.27
          },
          "market_repair_quality_deteriorating": {
            "sample_count": 301,
            "stage_sample_share_pct": 34.88,
            "lagging_false_negative_rate_pct": 88.04,
            "avg_return_pct": 21.27
          },
          "repair_quality_sync_insufficient": {
            "sample_count": 460,
            "stage_sample_share_pct": 53.3,
            "lagging_false_negative_rate_pct": 85.43,
            "avg_return_pct": 16.21
          },
          "volume_expansion_speed_not_improved": {
            "sample_count": 408,
            "stage_sample_share_pct": 47.28,
            "lagging_false_negative_rate_pct": 82.11,
            "avg_return_pct": 14.6
          }
        },
        "q4_long_60": {
          "market_decline_speed_accelerating": {
            "sample_count": 487,
            "stage_sample_share_pct": 100.0,
            "lagging_false_negative_rate_pct": 88.71,
            "avg_return_pct": 17.97
          },
          "market_repair_speed_profile_speed_not_formed": {
            "sample_count": 218,
            "stage_sample_share_pct": 44.76,
            "lagging_false_negative_rate_pct": 92.66,
            "avg_return_pct": 21.13
          },
          "repair_quality_sync_insufficient": {
            "sample_count": 255,
            "stage_sample_share_pct": 52.36,
            "lagging_false_negative_rate_pct": 86.27,
            "avg_return_pct": 15.9
          },
          "volume_expansion_speed_not_improved": {
            "sample_count": 248,
            "stage_sample_share_pct": 50.92,
            "lagging_false_negative_rate_pct": 87.9,
            "avg_return_pct": 18.27
          }
        },
        "q1_medium_20_defense": {
          "repair_quality_sync_insufficient": {
            "sample_count": 250,
            "stage_sample_share_pct": 44.96,
            "lagging_false_negative_rate_pct": 30.4,
            "avg_return_pct": -3.67
          },
          "volume_expansion_speed_not_improved": {
            "sample_count": 267,
            "stage_sample_share_pct": 48.02,
            "lagging_false_negative_rate_pct": 26.59,
            "avg_return_pct": -6.42
          },
          "lesson": "Q1 medium-term 20-day sell/avoid still worked as risk control in many cases; the same weak-tail state only becomes lagging at longer horizons or later stage blocks."
        }
      },
      "horizon_selection_direct_validation": {
        "decision": "diagnostic_only_not_active",
        "reports": [
          "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-signal-review.md",
          "docs/research/stock-signal-backtest-2022-06-19-to-2024-06-19-validation-2023-06-19-signal-review.md",
          "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-signal-review.md"
        ],
        "interpretation": "Directly pairing same-stock same-date medium 20-day and long 60-day sell/avoid outcomes quantifies horizon drift. The whole weak-tail sample often leans 60-day sell-lag, but bridge windows and individual quarters remain mixed, so this is a stage diagnostic rather than a fixed active horizon.",
        "weak_tail_base_all": {
          "paired_sample_count": 3314,
          "medium_20_effective_risk_rate_pct": 41.64,
          "long_60_lagging_false_negative_rate_pct": 70.88,
          "long_minus_medium_return_pct": 7.72,
          "verdict": "60_day_lagging_dominant"
        },
        "weak_tail_base_by_quarter": {
          "2022-Q1": {
            "paired_sample_count": 1077,
            "medium_20_effective_risk_rate_pct": 68.43,
            "medium_20_avg_return_pct": -4.5,
            "long_60_lagging_false_negative_rate_pct": 60.35,
            "verdict": "mixed_keep_reviewing_20_day_risk_control"
          },
          "2022-Q2": {
            "paired_sample_count": 1019,
            "medium_20_effective_risk_rate_pct": 20.9,
            "long_60_lagging_false_negative_rate_pct": 81.16,
            "long_minus_medium_return_pct": 7.15,
            "verdict": "60_day_lagging_dominant"
          },
          "2022-Q3": {
            "paired_sample_count": 529,
            "medium_20_effective_risk_rate_pct": 51.04,
            "long_60_lagging_false_negative_rate_pct": 59.92,
            "verdict": "mixed"
          },
          "2022-Q4": {
            "paired_sample_count": 689,
            "medium_20_effective_risk_rate_pct": 23.22,
            "long_60_lagging_false_negative_rate_pct": 80.55,
            "long_minus_medium_return_pct": 7.34,
            "verdict": "60_day_lagging_dominant"
          }
        },
        "market_speed_not_formed_focus": {
          "all_paired_sample_count": 1326,
          "all_long_60_lagging_false_negative_rate_pct": 71.95,
          "2022-Q2_long_60_lagging_false_negative_rate_pct": 87.92,
          "2022-Q4_long_60_lagging_false_negative_rate_pct": 87.23,
          "lesson": "Market speed-not-formed strengthens the Q2/Q4 60-day slow-repair interpretation, but Q1/Q3 still do not justify a fixed active horizon."
        },
        "bridge_split_2022_2024": {
          "weak_tail_base_all": {
            "paired_sample_count": 2261,
            "medium_20_effective_risk_rate_pct": 33.17,
            "long_60_lagging_false_negative_rate_pct": 63.73,
            "long_minus_medium_return_pct": 1.79,
            "verdict": "mixed_continue_review"
          },
          "stage_examples": {
            "2022-Q4": {
              "paired_sample_count": 689,
              "long_60_lagging_false_negative_rate_pct": 80.55,
              "verdict": "60_day_lagging_dominant"
            },
            "2023-Q4": {
              "paired_sample_count": 615,
              "medium_20_effective_risk_rate_pct": 45.04,
              "long_60_lagging_false_negative_rate_pct": 42.6,
              "long_minus_medium_return_pct": -2.06,
              "verdict": "mixed"
            },
            "2024-Q1": {
              "paired_sample_count": 428,
              "medium_20_effective_risk_rate_pct": 10.05,
              "long_60_lagging_false_negative_rate_pct": 71.73,
              "verdict": "60_day_lagging_dominant"
            }
          },
          "factor_interpretation": {
            "decision": "single_factors_are_review_priority_not_active",
            "report_section": "弱势尾部20/60日阶段因子解释",
            "stronger_60_day_lag_pockets": {
              "market_tail_repair_pending": {
                "factor": "market_tail_repair_signal=低位待确认",
                "paired_sample_count": 80,
                "medium_20_effective_risk_rate_pct": 23.75,
                "long_60_lagging_false_negative_rate_pct": 86.25,
                "long_minus_medium_return_pct": 13.2
              },
              "market_fast_tail_repair_confirmed": {
                "scope": "弱势尾部+市场跌速加快",
                "factor": "market_tail_repair_signal=低位修复确认",
                "paired_sample_count": 281,
                "medium_20_effective_risk_rate_pct": 14.59,
                "long_60_lagging_false_negative_rate_pct": 80.07,
                "long_minus_medium_return_pct": 5.48
              },
              "market_fast_quality_initial_confirmed": {
                "scope": "弱势尾部+市场跌速加快",
                "factor": "market_repair_quality_confirmation=修复质量初步确认",
                "paired_sample_count": 239,
                "medium_20_effective_risk_rate_pct": 14.23,
                "long_60_lagging_false_negative_rate_pct": 79.08,
                "long_minus_medium_return_pct": 4.39
              },
              "market_quality_unconfirmed": {
                "factor": "market_repair_quality_confirmation=修复质量未确认",
                "paired_sample_count": 505,
                "medium_20_effective_risk_rate_pct": 30.5,
                "long_60_lagging_false_negative_rate_pct": 73.47,
                "long_minus_medium_return_pct": 2.85
              }
            },
            "risk_control_or_mixed_counter_pockets": {
              "market_decline_speed_flat": {
                "factor": "market_decline_speed=跌速持平",
                "paired_sample_count": 76,
                "medium_20_effective_risk_rate_pct": 59.21,
                "long_60_lagging_false_negative_rate_pct": 21.05,
                "long_minus_medium_return_pct": -5.41
              },
              "market_speed_profile_strong_sync": {
                "factor": "market_repair_speed_profile=速度共振明显",
                "paired_sample_count": 74,
                "medium_20_effective_risk_rate_pct": 40.54,
                "long_60_lagging_false_negative_rate_pct": 36.49,
                "long_minus_medium_return_pct": -3.39
              },
              "market_quality_divergent": {
                "factor": "market_repair_quality_confirmation=修复质量分化",
                "paired_sample_count": 350,
                "medium_20_effective_risk_rate_pct": 41.14,
                "long_60_lagging_false_negative_rate_pct": 55.43,
                "long_minus_medium_return_pct": 0.73
              }
            },
            "lesson": "Bridge-window mixed behavior cannot be explained by one broad factor. Use these pockets to rank manual review and build a multi-factor stage classifier; do not promote any single factor to active."
          },
          "stage_classifier_prototype": {
            "decision": "report_level_diagnostic_only_not_active",
            "report_section": "弱势尾部20/60日多因子阶段分类器雏形",
            "category_labels": {
              "lag_priority": "60日滞后优先复核",
              "counterexample": "反例口袋继续复核",
              "conflict": "冲突继续复核",
              "mixed": "混合继续复核"
            },
            "lag_priority_groups": {
              "market_quality_unconfirmed": {
                "primary_reason": "市场修复质量未确认",
                "paired_sample_count": 466,
                "medium_20_effective_risk_rate_pct": 30.69,
                "long_60_lagging_false_negative_rate_pct": 72.53,
                "long_minus_medium_return_pct": 1.88
              },
              "market_fast_tail_repair_confirmed": {
                "primary_reason": "市场跌速加快+低位修复确认",
                "paired_sample_count": 281,
                "medium_20_effective_risk_rate_pct": 14.59,
                "long_60_lagging_false_negative_rate_pct": 80.07,
                "long_minus_medium_return_pct": 5.48
              },
              "market_tail_repair_pending": {
                "primary_reason": "市场低位待确认",
                "paired_sample_count": 80,
                "medium_20_effective_risk_rate_pct": 23.75,
                "long_60_lagging_false_negative_rate_pct": 86.25,
                "long_minus_medium_return_pct": 13.2
              }
            },
            "risk_control_or_mixed_groups": {
              "market_quality_divergent": {
                "primary_reason": "市场修复质量分化",
                "paired_sample_count": 276,
                "medium_20_effective_risk_rate_pct": 41.3,
                "long_60_lagging_false_negative_rate_pct": 60.51,
                "long_minus_medium_return_pct": 1.83,
                "verdict": "mixed_continue_review"
              },
              "market_decline_speed_flat": {
                "primary_reason": "市场跌速持平",
                "paired_sample_count": 76,
                "medium_20_effective_risk_rate_pct": 59.21,
                "long_60_lagging_false_negative_rate_pct": 21.05,
                "long_minus_medium_return_pct": -5.41
              },
              "market_speed_profile_strong_sync": {
                "primary_reason": "市场速度共振明显",
                "paired_sample_count": 74,
                "medium_20_effective_risk_rate_pct": 40.54,
                "long_60_lagging_false_negative_rate_pct": 36.49,
                "long_minus_medium_return_pct": -3.39
              }
            },
            "unclassified_mixed_group": {
              "paired_sample_count": 1008,
              "medium_20_effective_risk_rate_pct": 35.52,
              "long_60_lagging_false_negative_rate_pct": 59.42,
              "long_minus_medium_return_pct": 0.72
            },
            "cross_split_check": {
              "reports": [
                "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-signal-review.md",
                "docs/research/stock-signal-backtest-2022-06-19-to-2024-06-19-validation-2023-06-19-signal-review.md",
                "docs/research/stock-signal-backtest-2023-06-19-to-2026-06-19-validation-2024-06-19-signal-review.md"
              ],
              "lag_priority_stability": {
                "market_fast_tail_repair_confirmed_long_60_lagging_rate_pct": [74.14, 80.07, 82.55],
                "market_quality_unconfirmed_long_60_lagging_rate_pct": [71.36, 72.53, 77.84],
                "market_tail_repair_pending_long_60_lagging_rate_pct": [86.25, 86.25, 97.87],
                "interpretation": "The lag-priority buckets are stable enough for manual review ordering across the three available splits, but still remain diagnostic-only."
              },
              "counterexample_instability": {
                "market_decline_speed_flat_long_60_lagging_rate_pct": [79.46, 21.05, 60.76],
                "market_quality_divergent_long_60_lagging_rate_pct": [71.36, 60.51, 66.67],
                "market_speed_profile_strong_sync_long_60_lagging_rate_pct": [62.03, 36.49, 49.3],
                "interpretation": "Counterexample buckets are not stable 20-day risk-control rules; they only flag areas where 60-day lag needs more context."
              },
              "unclassified_mixed_bucket": {
                "paired_sample_count": [993, 1008, 856],
                "long_60_lagging_rate_pct": [66.67, 59.42, 70.09],
                "interpretation": "Large unclassified buckets remain, and the latest split can still be 60-day lagging. Split this bucket before considering active changes."
              },
              "mixed_bucket_decomposition": {
                "report_section": "弱势尾部20/60日未命中混合桶拆解",
                "decision": "review_only_not_active",
                "stable_confidence_reducer": {
                  "factor": "market_repair_speed_profile=速度分化",
                  "bucket_share_pct": [12.08, 14.19, 13.55],
                  "long_60_lagging_rate_pct": [55.83, 46.85, 55.17],
                  "interpretation": "Market repair-speed divergence consistently lowers 60-day lagging confidence inside the unclassified mixed bucket. Treat it as a manual review warning, not as a 20-day risk-control rule or buy signal."
                },
                "unstable_or_background_factors": {
                  "repair_speed_profile_speed_not_formed_long_60_lagging_rate_pct": [70.88, 62.89, 69.74],
                  "repair_quality_sync_dual_quality_worsening_long_60_lagging_rate_pct": [68.29, 61.34, 68.8],
                  "tail_repair_signal_bear_continuation_long_60_lagging_rate_pct": [66.59, 59.39, 66.78],
                  "interpretation": "These factors describe the mixed bucket background but do not split it reliably enough for a new classifier rule."
                },
                "second_order_decomposition": {
                  "report_section": "弱势尾部20/60日未命中混合桶二阶组合拆解",
                  "decision": "review_only_not_active",
                  "stable_confidence_reducer": {
                    "factor_pair": "market_repair_speed_profile + market_tail_extreme",
                    "factor_values": "速度分化 + 弱势低位",
                    "paired_sample_count": [120, 143, 94],
                    "bucket_share_pct": [12.08, 14.19, 10.98],
                    "long_60_lagging_rate_pct": [55.83, 46.85, 44.68],
                    "interpretation": "The broad speed-divergence reducer is most stable when the market is weak-low rather than extreme oversold. This is a confidence reducer only."
                  },
                  "supporting_small_sample_reducers": {
                    "speed_divergence_stock_volume_not_improved": {
                      "factor_pair": "market_repair_speed_profile + volume_expansion_speed",
                      "factor_values": "速度分化 + 速度未改善",
                      "paired_sample_count": [55, 74, 56],
                      "long_60_lagging_rate_pct": [56.36, 45.95, 55.36]
                    },
                    "speed_divergence_stock_volume_mild_improvement": {
                      "factor_pair": "market_repair_speed_profile + volume_expansion_speed",
                      "factor_values": "速度分化 + 速度温和改善",
                      "paired_sample_count": [50, 47, 34],
                      "long_60_lagging_rate_pct": [58.0, 51.06, 50.0]
                    }
                  },
                  "unstable_lag_candidate": {
                    "factor_pair": "market_repair_speed_profile + market_volume_expansion_speed",
                    "factor_values": "速度未形成 + 速度未改善",
                    "paired_sample_count": [554, 484, 467],
                    "long_60_lagging_rate_pct": [65.16, 63.84, 85.01],
                    "interpretation": "Strong in the latest split but not stable across earlier windows; keep as a later-stage review clue, not a classifier rule."
                  },
                  "fold_concentration_check": {
                    "report_section": "弱势尾部20/60日速度分化低位折叠验证",
                    "decision": "stage_block_review_only_not_active",
                    "monthly_rows": {
                      "2022-03": {
                        "paired_sample_count": 71,
                        "long_60_lagging_rate_pct": 59.15
                      },
                      "2022-09": {
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 51.02
                      },
                      "2023-10": {
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 22.45
                      },
                      "2023-12": {
                        "paired_sample_count": 45,
                        "long_60_lagging_rate_pct": 68.89
                      }
                    },
                    "quarter_rows": {
                      "2022-Q1": {
                        "paired_sample_count": 71,
                        "long_60_lagging_rate_pct": 59.15
                      },
                      "2022-Q3": {
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 51.02
                      },
                      "2023-Q4": {
                        "paired_sample_count": 94,
                        "long_60_lagging_rate_pct": 44.68
                      }
                    },
                    "interpretation": "The reducer is concentrated in a few stage blocks rather than broadly distributed. 2023-Q4 is internally divergent: 2023-10 is a strong reducer while 2023-12 is near lagging again, so do not generalize this as a stable counterexample rule."
                  },
                  "daily_basket_check": {
                    "report_section": "弱势尾部20/60日速度分化低位日篮验证",
                    "decision": "daily_basket_review_only_not_active",
                    "daily_rows": {
                      "2022-03-16": {
                        "paired_sample_count": 71,
                        "medium_20_effective_risk_rate_pct": 52.11,
                        "long_60_lagging_rate_pct": 59.15,
                        "medium_20_avg_return_pct": 0.0,
                        "long_60_avg_return_pct": 4.85
                      },
                      "2022-09-27": {
                        "paired_sample_count": 49,
                        "medium_20_effective_risk_rate_pct": 55.1,
                        "long_60_lagging_rate_pct": 51.02,
                        "medium_20_avg_return_pct": -1.08,
                        "long_60_avg_return_pct": 1.96
                      },
                      "2023-10-25": {
                        "paired_sample_count": 49,
                        "medium_20_effective_risk_rate_pct": 38.78,
                        "long_60_lagging_rate_pct": 22.45,
                        "medium_20_avg_return_pct": 3.78,
                        "long_60_avg_return_pct": -4.76
                      },
                      "2023-12-21": {
                        "paired_sample_count": 45,
                        "medium_20_effective_risk_rate_pct": 53.33,
                        "long_60_lagging_rate_pct": 68.89,
                        "medium_20_avg_return_pct": -0.95,
                        "long_60_avg_return_pct": 6.19
                      }
                    },
                    "interpretation": "The month/quarter pattern is actually a handful of dense signal-day baskets. 2023-10-25 is a true reducer, while 2023-12-21 is close to lagging again under the same broad factor scope. Further work should compare visible market position, repair slope, and volume persistence before the signal date."
                  },
                  "daily_visible_context_check": {
                    "report_section": "弱势尾部20/60日速度分化低位日篮可见变量对比",
                    "decision": "visible_context_review_only_not_active",
                    "daily_rows": {
                      "2022-03-16": {
                        "paired_sample_count": 71,
                        "long_60_lagging_rate_pct": 59.15,
                        "market_volume_expansion_speed": "速度未改善",
                        "stock_macd_repair_speed_top": "速度未改善",
                        "stock_macd_repair_speed_top_share_pct": 49
                      },
                      "2022-09-27": {
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 51.02,
                        "market_volume_expansion_speed": "速度未改善",
                        "stock_macd_repair_speed_top": "速度未改善",
                        "stock_macd_repair_speed_top_share_pct": 43
                      },
                      "2023-10-25": {
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 22.45,
                        "market_volume_expansion_speed": "速度温和改善",
                        "stock_macd_repair_speed_top": "速度温和改善",
                        "stock_macd_repair_speed_top_share_pct": 55
                      },
                      "2023-12-21": {
                        "paired_sample_count": 45,
                        "long_60_lagging_rate_pct": 68.89,
                        "market_volume_expansion_speed": "速度未改善",
                        "stock_macd_repair_speed_top": "速度温和改善",
                        "stock_macd_repair_speed_top_share_pct": 36
                      }
                    },
                    "interpretation": "Under the same broad speed-divergence + weak-low market bucket, 2023-10-25 differs from 2023-12-21 mainly in pre-signal market volume expansion and stock MACD repair breadth. Treat market volume persistence and stock MACD repair breadth as the next review-only splitter; do not promote it to active scoring."
                  },
                  "repair_breadth_check": {
                    "report_section": "弱势尾部20/60日速度分化低位修复广度验证",
                    "decision": "repair_breadth_review_only_not_active",
                    "daily_rows": {
                      "2022-03-16": {
                        "paired_sample_count": 71,
                        "market_volume_improved_pct": 0.0,
                        "stock_macd_repair_improved_pct": 33.8,
                        "long_60_lagging_rate_pct": 59.15,
                        "long_60_avg_return_pct": 4.85,
                        "combo": "market_volume_not_improved+stock_macd_narrow"
                      },
                      "2022-09-27": {
                        "paired_sample_count": 49,
                        "market_volume_improved_pct": 0.0,
                        "stock_macd_repair_improved_pct": 40.82,
                        "long_60_lagging_rate_pct": 51.02,
                        "long_60_avg_return_pct": 1.96,
                        "combo": "market_volume_not_improved+stock_macd_narrow"
                      },
                      "2023-10-25": {
                        "paired_sample_count": 49,
                        "market_volume_improved_pct": 100.0,
                        "stock_macd_repair_improved_pct": 59.18,
                        "long_60_lagging_rate_pct": 22.45,
                        "long_60_avg_return_pct": -4.76,
                        "combo": "market_volume_improved+stock_macd_broad"
                      },
                      "2023-12-21": {
                        "paired_sample_count": 45,
                        "market_volume_improved_pct": 0.0,
                        "stock_macd_repair_improved_pct": 66.67,
                        "long_60_lagging_rate_pct": 68.89,
                        "long_60_avg_return_pct": 6.19,
                        "combo": "market_volume_not_improved+stock_macd_broad"
                      }
                    },
                    "combo_rows": {
                      "market_volume_improved+stock_macd_broad": {
                        "daily_basket_count": 1,
                        "paired_sample_count": 49,
                        "long_60_lagging_rate_pct": 22.45,
                        "long_60_avg_return_pct": -4.76
                      },
                      "market_volume_not_improved+stock_macd_broad": {
                        "daily_basket_count": 1,
                        "paired_sample_count": 45,
                        "long_60_lagging_rate_pct": 68.89,
                        "long_60_avg_return_pct": 6.19
                      },
                      "market_volume_not_improved+stock_macd_narrow": {
                        "daily_basket_count": 2,
                        "paired_sample_count": 120,
                        "long_60_lagging_rate_pct": 55.83,
                        "long_60_avg_return_pct": 3.41
                      }
                    },
                    "pair_combo_rows": {
                      "non_overlapping_2021_2023": {
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 44,
                          "long_60_lagging_rate_pct": 56.82,
                          "long_60_avg_return_pct": 2.51
                        },
                        "market_volume_not_improved+stock_macd_not_repaired": {
                          "paired_sample_count": 76,
                          "long_60_lagging_rate_pct": 55.26,
                          "long_60_avg_return_pct": 4.34
                        }
                      },
                      "bridge_2022_2024": {
                        "market_volume_improved+stock_macd_repaired": {
                          "paired_sample_count": 29,
                          "long_60_lagging_rate_pct": 10.34,
                          "long_60_avg_return_pct": -9.66
                        },
                        "market_volume_improved+stock_macd_not_repaired": {
                          "paired_sample_count": 20,
                          "long_60_lagging_rate_pct": 40.0,
                          "long_60_avg_return_pct": 2.35
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 50,
                          "long_60_lagging_rate_pct": 64.0,
                          "long_60_avg_return_pct": 4.64
                        },
                        "market_volume_not_improved+stock_macd_not_repaired": {
                          "paired_sample_count": 44,
                          "long_60_lagging_rate_pct": 54.55,
                          "long_60_avg_return_pct": 3.25
                        }
                      },
                      "primary_2023_2026": {
                        "market_volume_improved+stock_macd_repaired": {
                          "paired_sample_count": 29,
                          "long_60_lagging_rate_pct": 10.34,
                          "long_60_avg_return_pct": -9.66
                        },
                        "market_volume_improved+stock_macd_not_repaired": {
                          "paired_sample_count": 20,
                          "long_60_lagging_rate_pct": 40.0,
                          "long_60_avg_return_pct": 2.35
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 30,
                          "long_60_lagging_rate_pct": 73.33,
                          "long_60_avg_return_pct": 6.42
                        },
                        "market_volume_not_improved+stock_macd_not_repaired": {
                          "paired_sample_count": 15,
                          "long_60_lagging_rate_pct": 60.0,
                          "long_60_avg_return_pct": 5.72
                        }
                      }
                    },
                    "broader_mixed_bucket_pair_combo_rows": {
                      "non_overlapping_2021_2023": {
                        "market_volume_improved+stock_macd_repaired": {
                          "paired_sample_count": 39,
                          "long_60_lagging_rate_pct": 71.79,
                          "long_60_avg_return_pct": 10.84
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 174,
                          "long_60_lagging_rate_pct": 53.45,
                          "long_60_avg_return_pct": 3.29
                        }
                      },
                      "bridge_2022_2024": {
                        "market_volume_improved+stock_macd_repaired": {
                          "paired_sample_count": 98,
                          "long_60_lagging_rate_pct": 44.9,
                          "long_60_avg_return_pct": 0.9
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 190,
                          "long_60_lagging_rate_pct": 58.95,
                          "long_60_avg_return_pct": 3.56
                        }
                      },
                      "primary_2023_2026": {
                        "market_volume_improved+stock_macd_repaired": {
                          "paired_sample_count": 79,
                          "long_60_lagging_rate_pct": 44.3,
                          "long_60_avg_return_pct": 3.56
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "paired_sample_count": 202,
                          "long_60_lagging_rate_pct": 87.13,
                          "long_60_avg_return_pct": 20.6
                        }
                      }
                    },
                    "broader_mixed_bucket_stage_fold_rows": {
                      "non_overlapping_2021_2023": {
                        "market_volume_improved+stock_macd_repaired": {
                          "2022-09": {
                            "paired_sample_count": 16,
                            "long_60_lagging_rate_pct": 37.5,
                            "long_60_avg_return_pct": -2.37
                          },
                          "2022-10": {
                            "paired_sample_count": 19,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 22.09
                          },
                          "market_context_all": {
                            "market_decline_speed": "跌速加快",
                            "market_tail_repair_signal": "低位空头延续",
                            "market_repair_quality_confirmation": "修复质量恶化",
                            "paired_sample_count": 39,
                            "long_60_lagging_rate_pct": 71.79,
                            "long_60_avg_return_pct": 10.84
                          }
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "2022-04": {
                            "paired_sample_count": 19,
                            "long_60_lagging_rate_pct": 94.74,
                            "long_60_avg_return_pct": 22.75
                          },
                          "all": {
                            "paired_sample_count": 174,
                            "long_60_lagging_rate_pct": 53.45,
                            "long_60_avg_return_pct": 3.29
                          }
                        }
                      },
                      "bridge_2022_2024": {
                        "market_volume_improved+stock_macd_repaired": {
                          "2022-09": {
                            "paired_sample_count": 16,
                            "long_60_lagging_rate_pct": 37.5,
                            "long_60_avg_return_pct": -2.37
                          },
                          "2022-10": {
                            "paired_sample_count": 19,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 22.09
                          },
                          "2023-10": {
                            "paired_sample_count": 39,
                            "long_60_lagging_rate_pct": 7.69,
                            "long_60_avg_return_pct": -9.85
                          },
                          "2024-Q1": {
                            "paired_sample_count": 24,
                            "long_60_lagging_rate_pct": 66.67,
                            "long_60_avg_return_pct": 3.75
                          }
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "2023-Q4": {
                            "paired_sample_count": 55,
                            "long_60_lagging_rate_pct": 78.18,
                            "long_60_avg_return_pct": 7.69
                          },
                          "2024-Q1": {
                            "paired_sample_count": 41,
                            "long_60_lagging_rate_pct": 73.17,
                            "long_60_avg_return_pct": 8.94
                          }
                        }
                      },
                      "primary_2023_2026": {
                        "market_volume_improved+stock_macd_repaired": {
                          "2023-10": {
                            "paired_sample_count": 39,
                            "long_60_lagging_rate_pct": 7.69,
                            "long_60_avg_return_pct": -9.85
                          },
                          "2024-Q1": {
                            "paired_sample_count": 24,
                            "long_60_lagging_rate_pct": 66.67,
                            "long_60_avg_return_pct": 3.75
                          },
                          "2024-Q3": {
                            "paired_sample_count": 16,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 35.98
                          }
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "2023-Q4": {
                            "paired_sample_count": 55,
                            "long_60_lagging_rate_pct": 78.18,
                            "long_60_avg_return_pct": 7.69
                          },
                          "2024-Q1": {
                            "paired_sample_count": 41,
                            "long_60_lagging_rate_pct": 73.17,
                            "long_60_avg_return_pct": 8.94
                          },
                          "2024-Q3": {
                            "paired_sample_count": 106,
                            "long_60_lagging_rate_pct": 97.17,
                            "long_60_avg_return_pct": 31.81
                          }
                        }
                      }
                    },
                    "broader_mixed_bucket_continuous_combo_rows": {
                      "non_overlapping_2021_2023": {
                        "market_volume_improved+stock_macd_repaired": {
                          "market_volume_mild_persistent+market_20d_still_down": {
                            "paired_sample_count": 21,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 21.28
                          },
                          "market_volume_pulse+market_20d_still_down": {
                            "paired_sample_count": 17,
                            "long_60_lagging_rate_pct": 41.18,
                            "long_60_avg_return_pct": -1.3
                          },
                          "market_volume_mild_persistent+stock_macd_discontinuous": {
                            "paired_sample_count": 13,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 20.95
                          },
                          "market_volume_pulse+stock_macd_continuous": {
                            "paired_sample_count": 10,
                            "long_60_lagging_rate_pct": 20.0,
                            "long_60_avg_return_pct": -5.23
                          }
                        }
                      },
                      "bridge_2022_2024": {
                        "market_volume_improved+stock_macd_repaired": {
                          "market_volume_mild_persistent+market_20d_still_down": {
                            "paired_sample_count": 43,
                            "long_60_lagging_rate_pct": 69.77,
                            "long_60_avg_return_pct": 9.26
                          },
                          "market_volume_mild_persistent+market_20d_repair_insufficient": {
                            "paired_sample_count": 31,
                            "long_60_lagging_rate_pct": 9.68,
                            "long_60_avg_return_pct": -9.62
                          },
                          "market_20d_still_down+stock_macd_discontinuous": {
                            "paired_sample_count": 35,
                            "long_60_lagging_rate_pct": 80.0,
                            "long_60_avg_return_pct": 9.46
                          },
                          "market_20d_repair_insufficient+stock_macd_oscillating": {
                            "paired_sample_count": 22,
                            "long_60_lagging_rate_pct": 13.64,
                            "long_60_avg_return_pct": -8.76
                          }
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "market_volume_pulse+market_20d_still_down": {
                            "paired_sample_count": 34,
                            "long_60_lagging_rate_pct": 79.41,
                            "long_60_avg_return_pct": 11.16
                          },
                          "market_volume_pulse+market_20d_repair_insufficient": {
                            "paired_sample_count": 156,
                            "long_60_lagging_rate_pct": 54.49,
                            "long_60_avg_return_pct": 1.9
                          }
                        }
                      },
                      "primary_2023_2026": {
                        "market_volume_improved+stock_macd_repaired": {
                          "market_volume_mild_persistent+market_20d_repair_insufficient": {
                            "paired_sample_count": 31,
                            "long_60_lagging_rate_pct": 9.68,
                            "long_60_avg_return_pct": -9.62
                          },
                          "market_volume_pulse+market_20d_repair_insufficient": {
                            "paired_sample_count": 16,
                            "long_60_lagging_rate_pct": 100.0,
                            "long_60_avg_return_pct": 35.98
                          },
                          "market_20d_still_down+stock_macd_discontinuous": {
                            "paired_sample_count": 18,
                            "long_60_lagging_rate_pct": 66.67,
                            "long_60_avg_return_pct": 2.7
                          },
                          "market_20d_repair_insufficient+stock_macd_oscillating": {
                            "paired_sample_count": 26,
                            "long_60_lagging_rate_pct": 26.92,
                            "long_60_avg_return_pct": -3.59
                          }
                        },
                        "market_volume_not_improved+stock_macd_repaired": {
                          "market_volume_pulse+market_20d_still_down": {
                            "paired_sample_count": 68,
                            "long_60_lagging_rate_pct": 88.24,
                            "long_60_avg_return_pct": 20.05
                          },
                          "market_volume_pulse+market_20d_repair_insufficient": {
                            "paired_sample_count": 134,
                            "long_60_lagging_rate_pct": 86.57,
                            "long_60_avg_return_pct": 20.88
                          }
                        }
                      }
                    },
                    "interpretation": "Repair breadth refines the visible-context hypothesis: stock MACD breadth alone does not separate reducers from lagging baskets because 2023-12-21 has broad stock MACD repair but still lags at 60 days. Pair-level target-bucket combos support market volume as a review-only gate in 2022-2024 and 2023-2026. Broader mixed-bucket validation weakens active promotion: market volume improvement plus stock MACD repair still lags in 2021-2023, but lowers 60-day lag in the two later windows. Stage-fold validation further tightens the rule: market volume improvement plus stock MACD repair splits by month and quarter, with 2023-10 supporting confidence reduction but 2022-10, 2024-Q1 and 2024-Q3 still lagging at 60 days. Continuous combo validation improves review ordering: market-volume persistence plus insufficient 20-day repair is a strong reducer in 2022-2024 and 2023-2026, while volume pulses or still-falling 20-day market states can remain 60-day lagging. The 2021-2023 split still contradicts a stable active rule, so keep this review-only."
                  }
                }
              }
            },
            "lesson": "Transparent multi-factor buckets improve manual review ordering. Cross-split checks support the lag-priority buckets but downgrade counterexample buckets to review-only diagnostics. Mixed-bucket decomposition identifies market repair-speed divergence, especially speed divergence plus weak-low market position, as a stage-block confidence reducer; fold and daily-basket checks show it is concentrated and internally divergent, so the classifier is not ready for active scoring."
          }
        },
        "primary_split_2023_2026": {
          "weak_tail_base_all": {
            "paired_sample_count": 1745,
            "medium_20_effective_risk_rate_pct": 28.94,
            "long_60_lagging_false_negative_rate_pct": 72.09,
            "long_minus_medium_return_pct": 3.18,
            "verdict": "60_day_lagging_dominant"
          },
          "stage_examples": {
            "2023-Q4": {
              "paired_sample_count": 615,
              "medium_20_effective_risk_rate_pct": 45.04,
              "long_60_lagging_false_negative_rate_pct": 42.6,
              "long_minus_medium_return_pct": -2.06,
              "verdict": "mixed"
            },
            "2024-Q1": {
              "paired_sample_count": 428,
              "medium_20_effective_risk_rate_pct": 10.05,
              "long_60_lagging_false_negative_rate_pct": 71.73,
              "long_minus_medium_return_pct": -2.66,
              "verdict": "60_day_lagging_dominant_but_20_day_already_lagging"
            },
            "2024-Q3": {
              "paired_sample_count": 702,
              "medium_20_effective_risk_rate_pct": 26.35,
              "long_60_lagging_false_negative_rate_pct": 98.15,
              "long_minus_medium_return_pct": 11.32,
              "verdict": "strong_60_day_lagging_dominant"
            }
          },
          "market_speed_not_formed_focus": {
            "paired_sample_count": 899,
            "long_60_lagging_false_negative_rate_pct": 76.86,
            "2024-Q3_long_60_lagging_false_negative_rate_pct": 98.39
          }
        }
      },
      "lesson": "The table makes the slow-repair sell/avoid-lag thesis actionable for manual review. Daily, stage-block, and stage-factor aggregation reduce the independence problem and explain the paradox: repair-quality failure is not a broad exclusion, but horizon drift remains. Keep active_adjustments empty.",
      "next_research_need": "Replace quarter labels with explanatory stage variables in direct 20/60-day pairing: market position, index speed, stock speed, volume persistence, and repair-quality sync. Do not promote a fixed 20-day or 60-day active horizon until those variables explain bridge-window mixed quarters."
    },
    "supplemental_evidence": [
      {
        "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19.md",
        "note": "Same market/stock cross-regime repeated the sell/avoid false-negative pattern, but the stable neutralize-to-watch window shifted to long_term 60 days.",
        "horizon": "long_term",
        "window_days": 60,
        "train_sample_count": 1419,
        "train_neutralized_wrong_directional_rate_pct": 76.53,
        "train_wrong_directional_count_delta": -1086,
        "validation_sample_count": 881,
        "validation_neutralized_wrong_directional_rate_pct": 79.0,
        "validation_wrong_directional_count_delta": -696,
        "rolling_monthly_evidence": {
          "folds_with_samples": 6,
          "total_matched_count": 2300,
          "max_fold_sample_share_pct": 24.17,
          "weighted_neutralized_wrong_directional_rate_pct": 77.48,
          "positive_wrong_delta_fold_share_pct": 100.0,
          "months": ["2022-03", "2022-04", "2022-05", "2022-09", "2022-10", "2022-11"]
        },
        "rolling_quarterly_evidence": {
          "folds_with_samples": 4,
          "total_matched_count": 2300,
          "max_fold_sample_share_pct": 37.52,
          "weighted_neutralized_wrong_directional_rate_pct": 77.48,
          "positive_wrong_delta_fold_share_pct": 100.0,
          "quarters": ["2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4"]
        },
        "stage_factor_evidence": {
          "market_trend_20d": {"value": "下跌", "sample_count": 2300, "neutralized_wrong_directional_rate_pct": 77.48},
          "market_trend_60d": {"value": "下跌", "sample_count": 2300, "neutralized_wrong_directional_rate_pct": 77.48},
          "trend_20d": {"value": "下跌", "sample_count": 2300, "neutralized_wrong_directional_rate_pct": 77.48},
          "trend_60d": {"value": "下跌", "sample_count": 2300, "neutralized_wrong_directional_rate_pct": 77.48},
          "horizon_alignment": {"value": "三周期同向偏空", "sample_count": 2207, "neutralized_wrong_directional_rate_pct": 77.07},
          "weak_tail_factor_evidence": {
            "report": "docs/research/stock-signal-backtest-2021-06-19-to-2023-06-19-validation-2022-06-19-tail.md",
            "decline_duration": [
              {"value": "短中长期同步下跌", "sample_count": 1835, "neutralized_wrong_directional_rate_pct": 77.77},
              {"value": "短中期同步下跌", "sample_count": 465, "neutralized_wrong_directional_rate_pct": 76.34}
            ],
            "decline_speed": [
              {"value": "跌速加快", "sample_count": 1745, "neutralized_wrong_directional_rate_pct": 77.59},
              {"value": "跌速持平", "sample_count": 493, "neutralized_wrong_directional_rate_pct": 77.28},
              {"value": "跌速放缓", "sample_count": 62, "neutralized_wrong_directional_rate_pct": 75.81}
            ],
            "market_decline_duration": [
              {"value": "短中长期同步下跌", "sample_count": 1419, "neutralized_wrong_directional_rate_pct": 76.53},
              {"value": "短中期同步下跌", "sample_count": 881, "neutralized_wrong_directional_rate_pct": 79.0}
            ],
            "market_decline_speed": [
              {"value": "跌速加快", "sample_count": 1972, "neutralized_wrong_directional_rate_pct": 76.42},
              {"value": "跌速持平", "sample_count": 328, "neutralized_wrong_directional_rate_pct": 83.84}
            ],
            "market_tail_extreme": [
              {"value": "弱势低位", "sample_count": 1317, "neutralized_wrong_directional_rate_pct": 76.54},
              {"value": "极端超卖", "sample_count": 816, "neutralized_wrong_directional_rate_pct": 77.7},
              {"value": "常规", "sample_count": 167, "neutralized_wrong_directional_rate_pct": 83.83}
            ],
            "weak_tail_extreme": [
              {"value": "弱势低位", "sample_count": 1452, "neutralized_wrong_directional_rate_pct": 74.38},
              {"value": "极端超卖", "sample_count": 747, "neutralized_wrong_directional_rate_pct": 82.2},
              {"value": "常规", "sample_count": 101, "neutralized_wrong_directional_rate_pct": 87.13}
            ]
          }
        }
      },
      {
        "report": "docs/research/stock-signal-backtest-2022-06-19-to-2024-06-19-validation-2023-06-19.md",
        "note": "Bridge split still shows weak raw sell/avoid outcomes for the same cross-regime, but it did not pass the automatic stable-candidate filter; treat as horizon/regime-drift caution.",
        "raw_sell_avoid_long_term_120_sample_count": 989,
        "raw_sell_avoid_long_term_120_hit_rate_pct": 23.66,
        "raw_sell_avoid_long_term_120_avg_return_pct": 26.1,
        "raw_sell_avoid_medium_term_20_sample_count": 1447,
        "raw_sell_avoid_medium_term_20_hit_rate_pct": 24.67,
        "raw_sell_avoid_medium_term_20_avg_return_pct": 7.01
      },
      {
        "report": "docs/research/stock-signal-backtest-2020-06-19-to-2022-06-19-validation-2021-06-19.md",
        "note": "Earlier split did not produce stable candidates and did not provide enough exact market_bear_continuation|bear_continuation evidence. Keep this as negative evidence against active promotion.",
        "stable_candidate_count": 0,
        "raw_market_bear_continuation_sell_avoid_medium_term_20_sample_count": 2516,
        "raw_market_bear_continuation_sell_avoid_medium_term_20_hit_rate_pct": 37.92,
        "raw_market_bear_continuation_sell_avoid_medium_term_20_avg_return_pct": 3.42
      }
    ]
  },
  "decision": "candidate_only",
  "active_promotion_requirements": [
    "Confirm on another non-overlapping historical split or future matured stock_signal_outcome rows.",
    "Keep scorer support restricted to explicit active_adjustments with matching horizon, signal_side, and factor scope.",
    "Verify the rule does not remove effective risk warnings in non-rebound market regimes.",
    "Resolve horizon drift: 3-year alternate split supports medium_term 20 days, while 2021-2023 supports long_term 60 days, 2022-2024 does not pass the stable-candidate filter, and 2020-2022 has no stable candidate.",
    "Quarterly folds reduce pure date-noise concern but show concentration in a few stage blocks, especially 2024-Q1 for the primary split.",
    "Stage-factor folds show the current evidence is an extreme weak-alignment sell-lag pattern, not a confirmed repair or buy-enhancement pattern.",
    "Weak-tail variables now support the sell-lag interpretation: decline duration, decline speed, and market/stock tail extremes explain the candidate better than date buckets alone.",
    "Narrower weak-tail composite scopes have been tested and should remain diagnostic only because they do not resolve horizon drift or sample concentration.",
    "Before promotion, add confirmation variables for BOLL/RSI/KDJ repair and market volume change, and verify that these variables distinguish repair starts from continued decline.",
    "Require basket-level validation: same-date matches should remain constructive as equal-weight daily baskets, with enough basket count and acceptable worst-basket behavior.",
    "Require cross-horizon profile validation: the same direction/factor scope should show whether the stable effect is 20-day, 60-day, or merely validation-only 120-day extension.",
    "Continuous speed metrics are diagnostic only for now; require more validation baskets and future matured rows before using repair speed for active horizon selection.",
    "Counterexample diagnostics show that repair quality must be confirmed before active promotion: persistent volume expansion, confirmed low-position repair, non-deteriorating market MACD repair, and real decline-speed deceleration are required.",
    "Repair-quality confirmation must be synchronized: market and stock quality cannot diverge, and a single-side confirmed label is not enough for active promotion.",
    "Repair-quality sync is diagnostic only: 2021-2023 supports long_term 60-day review, but 2023-2026 validation is too sparse and this condition does not imply a buy signal.",
    "Repair-quality failure is not a broad exclusion either: failure states still contain many lagging sell/avoid false negatives, so only narrower effective-risk pockets may be used to defend the original sell/avoid signal.",
    "Do not promote while effective months are limited and horizon drift remains unresolved."
  ]
}
```

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
- For `market_bear_continuation|bear_continuation`, the repeated lesson is sell/avoid lag after extreme weak alignment. Next validation should identify weak-tail/reversal variables, not convert the current candidate into a buy signal.
- 2026-06-20 best-strategy summary: the current cross-period optimum is a layered review framework, not an active scoring rule. Use `docs/research/stock-signal-best-strategy.md` as the human-readable strategy note. Stable review priorities are weak-tail sell/avoid lag, 20/60-day horizon pairing, and the three 60-day lag review lines: market decline speeding plus low-position repair confirmation, market repair quality unconfirmed, and market low-position pending confirmation. Market volume persistence plus stock MACD repair is review-only because 2021-2023 conflicts with 2022-2026 evidence. Keep active adjustments empty until horizon drift and stage concentration are resolved.
