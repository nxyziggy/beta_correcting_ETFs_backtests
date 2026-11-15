# Scoring concentration, timing and uncertainty

## Dependence on individual stocks

These post-result checks remove one company from the entire candidate pool before reranking both the alternative and its baseline. The main portfolios keep every eligible company. Omission effects include changed ranks, selections and weights; they are not additive stock contributions.

| Region | Existing variant | Rule | Full-pool gain over baseline | Without Bloom | Omission gains > 0 | Range across omissions |
|---|---|---|---:|---:|---:|---:|
| US | trend | Q50 | +511.91pp | -15.91pp | 15/16 | -15.91 to +680.71pp |
| US | trend | Q75 | +205.69pp | +19.60pp | 16/16 | +19.60 to +327.70pp |
| US | momentum | Q50 | +405.81pp | +177.01pp | 16/16 | +177.01 to +632.72pp |
| US | momentum | Q75 | +586.00pp | +252.86pp | 16/16 | +252.86 to +824.30pp |
| US | trend_confirm | Q50 | +645.07pp | +73.78pp | 16/16 | +73.78 to +734.80pp |
| US | trend_confirm | Q75 | +187.29pp | +81.46pp | 16/16 | +55.93 to +306.04pp |
| US | momentum_confirm | Q50 | +571.03pp | +205.56pp | 16/16 | +205.56 to +874.93pp |
| US | momentum_confirm | Q75 | +492.20pp | +269.49pp | 16/16 | +121.75 to +600.43pp |
| EU | trend | Q50 | +7.05pp | n/a | 7/15 | -115.68 to +54.41pp |
| EU | trend | Q75 | -38.58pp | n/a | 4/15 | -177.05 to +60.10pp |
| EU | momentum | Q50 | -53.59pp | n/a | 1/15 | -148.91 to +2.46pp |
| EU | momentum | Q75 | -100.74pp | n/a | 0/15 | -238.47 to -11.69pp |
| EU | trend_confirm | Q50 | +8.91pp | n/a | 5/15 | -137.14 to +28.45pp |
| EU | trend_confirm | Q75 | -52.67pp | n/a | 3/15 | -178.92 to +59.75pp |
| EU | momentum_confirm | Q50 | -55.77pp | n/a | 4/15 | -133.28 to +100.63pp |
| EU | momentum_confirm | Q75 | -71.51pp | n/a | 2/15 | -245.19 to +42.75pp |

For the fundamental-improvement score, the US gain changes from +511.91pp / +205.69pp (Q50/Q75) to -15.91pp / +19.60pp without Bloom. Compare full-pool and omission results before interpreting a gain as broadly distributed. The gain ranges after every other US omission are +261.15 to +680.71pp / +31.56 to +327.70pp.

[Every omission](score_omissions.csv) and [summary](score_omission_summary.csv) include both score variants and their existing two-review exit combinations. No stock is removed from the headline results.

## When the relative gains appeared

**Relative wealth** means variant NAV / baseline NAV − 1. It is a percentage, not the difference between cumulative returns in percentage points. These are continuous portfolio paths, not fresh restarts.

| US variant | Rule | At December 2020 | At May 2024 | At the full endpoint |
|---|---|---:|---:|---:|
| trend | Q50 | +6.80% | +15.57% | +107.08% |
| trend | Q75 | -7.30% | -14.04% | +41.99% |
| momentum | Q50 | +66.01% | +40.94% | +84.88% |
| momentum | Q75 | +72.20% | +64.68% | +119.63% |
| trend_confirm | Q50 | +16.19% | +33.14% | +134.93% |
| trend_confirm | Q75 | -4.01% | -10.67% | +38.24% |
| momentum_confirm | Q50 | +84.58% | +70.58% | +119.44% |
| momentum_confirm | Q75 | +60.78% | +55.02% | +100.49% |

At its first Bloom entry the trend portfolio was +15.83% relative to baseline for Q50 (2024-06-30); -10.86% relative to baseline for Q75 (2025-03-31). Bloom’s adjusted USD price then rose 24.73x over June 2024–June 2026. This stock-price interval starts at Q50’s entry, not Q75’s later entry; it is not the portfolio’s realized return. The milestones distinguish early and later performance; none is a new validation period.

[All milestone NAVs and both return measures](relative_wealth_milestones.csv).

## Statistical uncertainty

Each cell is the monthly active-return **IID t / Newey–West t** (three lags). Deployment costs and the terminal partial month are excluded from these monthly statistics. The baseline is the existing strategy using the same Q50/Q75 rule; equal weight is the unchanged control.

| Region | Alternative | Q50 vs baseline | Q75 vs baseline | Q50 vs equal weight | Q75 vs equal weight |
|---|---|---:|---:|---:|---:|
| US | balanced | +1.05 / +1.04 | -1.99 / -1.81 | -0.90 / -0.85 | -1.76 / -1.67 |
| US | trend | +2.27 / +2.18 | +1.22 / +1.09 | +0.38 / +0.34 | -0.28 / -0.24 |
| US | momentum | +1.65 / +1.72 | +1.90 / +1.86 | +0.47 / +0.51 | +0.85 / +0.90 |
| US | confirm_exit | +0.07 / +0.08 | -0.05 / -0.12 | -1.43 / -1.46 | -1.16 / -1.14 |
| US | recovery_grace | n/a / n/a | n/a / n/a | -1.44 / -1.46 | -1.16 / -1.12 |
| US | no_score_exit | -0.82 / -0.76 | +0.82 / +0.92 | -1.56 / -1.55 | -0.94 / -0.87 |
| US | trend_confirm | +2.66 / +2.68 | +1.23 / +1.11 | +0.76 / +0.71 | -0.47 / -0.42 |
| US | momentum_confirm | +2.02 / +2.21 | +1.74 / +1.91 | +1.06 / +1.17 | +0.65 / +0.69 |
| EU | balanced | +1.09 / +1.13 | -0.43 / -0.54 | +2.73 / +3.13 | +1.75 / +2.19 |
| EU | trend | +0.14 / +0.14 | -0.66 / -0.74 | +1.98 / +2.18 | +1.63 / +1.76 |
| EU | momentum | -0.73 / -0.77 | -1.25 / -1.40 | +1.04 / +1.29 | +1.01 / +1.22 |
| EU | confirm_exit | +0.22 / +0.18 | +0.03 / +0.03 | +1.80 / +2.36 | +1.99 / +2.70 |
| EU | recovery_grace | n/a / n/a | n/a / n/a | +1.61 / +1.88 | +1.78 / +2.23 |
| EU | no_score_exit | -0.36 / -0.36 | -1.15 / -1.06 | +1.69 / +2.05 | +1.41 / +1.50 |
| EU | trend_confirm | +0.16 / +0.16 | -0.88 / -1.16 | +1.98 / +2.32 | +1.49 / +1.63 |
| EU | momentum_confirm | -0.67 / -0.72 | -0.88 / -0.95 | +1.23 / +1.75 | +1.48 / +1.85 |

The largest US t-statistic against equal weight is 1.17. The main case alone contains 32 specified alternative-versus-baseline comparisons, before the additional timing, eligibility and omission analyses. These are unadjusted statistics on already-seen data. Some baseline comparisons exceed two; that does not establish a reliable advantage after selection or against equal weight. Duplicate portfolio paths supply no distinct performance evidence.

[All statistics](active_statistics.csv) · [Diagnostic validation](concentration_validation.json).
