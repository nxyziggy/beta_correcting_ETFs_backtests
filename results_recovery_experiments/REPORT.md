# Scoring and exit-rule experiments

[Fixed experiment definitions](../RECOVERY_EXPERIMENT_METHOD.md). Run `python3 run_recovery_experiments.py`. The existing strategy remains the default. All eight alternatives and the baseline are disclosed; no parameters were optimized after seeing these runs.

**0 of 8 specified alternatives pass the full-window four-return screen.** There are 7 distinct alternative portfolio paths across the tested cases; recovery_grace matches baseline. These are findings on already-seen history, not a validated replacement strategy.

Removing Bloom before reranking the fundamental-improvement strategy and its baseline changes the Q50/Q75 gains from +511.91pp / +205.69pp to -15.91pp / +19.60pp. Momentum’s positive omission comparisons are US Q50 16/16; US Q75 16/16; EU Q50 1/15; EU Q75 0/15. The omission results and unadjusted statistical evidence below qualify the headline cumulative returns.

The universe uses the broad [any prior public support screen](../results_pillar2/REPORT.md), with named direct/subsidiary support for the main case. It does not replicate the article’s narrower Pillar 2 programme streams or basket weights. The candidate list remains retrospective.

The trend score combines the existing score with a rank of improvement in operating return and cash quality, 50/50. The momentum score combines the existing score with trailing price momentum, also 50/50. Confirmation waits for two consecutive bad quarterly reviews before a score exit. All variants retain mandatory eligibility and capacity exits.

## Full direct-support history: 30 June 2019–2 November 2026

Returns include modeled costs. US in USD; EU in EUR. Equal-weight membership and NAV are unchanged by scoring/exit variants.

| Variant | US Q50 | US Q75 | EU Q50 | EU Q75 |
|---|---:|---:|---:|---:|
| baseline | 378.08% | 389.82% | 286.95% | 338.92% |
| balanced | 487.05% | 279.35% | 358.03% | 315.11% |
| trend | 889.98% | 595.51% | 294.00% | 300.34% |
| momentum | 783.88% | 975.82% | 233.36% | 238.18% |
| confirm_exit | 379.34% | 386.21% | 288.39% | 334.74% |
| recovery_grace | 378.08% | 389.82% | 286.95% | 338.92% |
| no_score_exit | 357.77% | 442.32% | 267.26% | 219.44% |
| trend_confirm | 1023.15% | 577.12% | 295.86% | 286.25% |
| momentum_confirm | 949.11% | 882.02% | 231.18% | 267.40% |
| Equal weight | 699.43% | 699.43% | 132.27% | 132.27% |

## Changes versus the existing strategy

| Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ | Four-return screen | Worst drawdown change |
|---|---:|---:|---:|---:|---|---:|
| balanced | +108.97pp | -110.47pp | +71.08pp | -23.81pp | Fail | -8.48pp |
| trend | +511.91pp | +205.69pp | +7.05pp | -38.58pp | Fail | -0.86pp |
| momentum | +405.81pp | +586.00pp | -53.59pp | -100.74pp | Fail | -3.11pp |
| confirm_exit | +1.27pp | -3.62pp | +1.44pp | -4.18pp | Fail | +0.00pp |
| recovery_grace | +0.00pp | +0.00pp | +0.00pp | +0.00pp | Fail | +0.00pp |
| no_score_exit | -20.30pp | +52.49pp | -19.69pp | -119.47pp | Fail | -2.24pp |
| trend_confirm | +645.07pp | +187.29pp | +8.91pp | -52.67pp | Fail | +0.53pp |
| momentum_confirm | +571.03pp | +492.20pp | -55.77pp | -71.51pp | Fail | -3.11pp |

The screen requires both US returns to improve and neither EU return to decline. It does not establish a robust improvement or eliminate risk/cost tradeoffs. A negative drawdown change means a worse maximum monthly drawdown. `no_score_exit` remains a diagnostic, with capacity and eligibility exits still enforced.

The headline return ranking does not establish a robust improvement. Stock concentration, the timing of gains, monthly uncertainty and different EU effects must be assessed alongside the total returns. The recovery-grace condition triggers 0 times across the tested cases. Its realized path is compared with baseline above; an inactive rule supplies no evidence of effectiveness.

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

## Risk and trading tradeoffs

Each cell is annualized return / maximum monthly drawdown / annualized two-way turnover. Turnover counts purchases plus sales; costs remain 10bp per traded dollar in the US and 15bp in Europe.

| Variant | US Q50 | US Q75 | EU Q50 | EU Q75 |
|---|---:|---:|---:|---:|
| baseline | 23.75% / -28.60% / 1.26x | 24.16% / -32.56% / 1.20x | 20.23% / -33.92% / 1.37x | 22.32% / -35.86% / 1.37x |
| trend | 36.64% / -26.03% / 1.87x | 30.23% / -28.11% / 1.89x | 20.53% / -34.78% / 1.71x | 20.79% / -34.56% / 1.58x |
| momentum | 34.55% / -31.71% / 2.10x | 38.20% / -29.03% / 1.94x | 17.82% / -25.28% / 1.75x | 18.05% / -29.23% / 1.54x |
| confirm_exit | 23.79% / -28.60% / 1.23x | 24.03% / -32.56% / 1.14x | 20.30% / -33.92% / 1.20x | 22.16% / -32.37% / 1.19x |
| trend_confirm | 39.01% / -26.03% / 1.76x | 29.75% / -28.11% / 1.67x | 20.61% / -33.39% / 1.58x | 20.20% / -33.30% / 1.51x |

Return, drawdown and trading frequency can move in different directions. The four-return screen therefore is not a complete risk-adjusted ranking.

## Timing and eligibility robustness

The [complete comparison](comparisons.csv) includes direct/source and delayed financial timing from September 2019, plus indirect-inclusive eligibility from June 2019. Source and delayed controls have identical monthly NAVs. The [chronological readout](chronological_results.csv) splits continuous portfolio paths into 2019–2022, 2023–end and July 2020–end. These periods have already been observed and are not untouched holdouts.

| Case | Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ |
|---|---|---:|---:|---:|---:|
| direct_timing_source | balanced | +31.99pp | -51.35pp | +64.10pp | -50.69pp |
| direct_timing_source | trend | +428.14pp | +199.08pp | +6.36pp | -36.92pp |
| direct_timing_source | momentum | +318.82pp | +551.13pp | -34.27pp | -64.78pp |
| direct_timing_source | confirm_exit | +1.15pp | -1.51pp | +1.30pp | -4.00pp |
| direct_timing_source | recovery_grace | +0.00pp | +0.00pp | +0.00pp | +0.00pp |
| direct_timing_source | no_score_exit | -18.35pp | +42.79pp | -17.76pp | -114.34pp |
| direct_timing_source | trend_confirm | +543.87pp | +183.62pp | +8.03pp | -50.41pp |
| direct_timing_source | momentum_confirm | +350.71pp | +469.57pp | -10.32pp | -26.13pp |
| direct_timing_delayed | balanced | -57.42pp | -95.24pp | +123.80pp | +1.89pp |
| direct_timing_delayed | trend | +295.34pp | +71.16pp | -4.69pp | +132.34pp |
| direct_timing_delayed | momentum | +259.72pp | +544.25pp | +25.77pp | +38.54pp |
| direct_timing_delayed | confirm_exit | +11.20pp | +19.05pp | +11.36pp | +19.06pp |
| direct_timing_delayed | recovery_grace | +0.00pp | +0.00pp | +0.00pp | +0.00pp |
| direct_timing_delayed | no_score_exit | -22.87pp | +53.06pp | -13.41pp | -43.67pp |
| direct_timing_delayed | trend_confirm | +259.16pp | +22.23pp | -3.68pp | +43.70pp |
| direct_timing_delayed | momentum_confirm | +320.27pp | +478.34pp | +19.29pp | +57.51pp |
| indirect_main | balanced | +144.77pp | -118.12pp | +80.69pp | -39.42pp |
| indirect_main | trend | +552.76pp | +196.14pp | +10.66pp | -18.06pp |
| indirect_main | momentum | +450.41pp | +588.54pp | -39.33pp | -135.53pp |
| indirect_main | confirm_exit | +2.09pp | -9.91pp | +1.47pp | -4.57pp |
| indirect_main | recovery_grace | +0.00pp | +0.00pp | +0.00pp | +0.00pp |
| indirect_main | no_score_exit | +7.40pp | +56.89pp | -20.11pp | -129.84pp |
| indirect_main | trend_confirm | +631.30pp | +157.68pp | +5.97pp | -44.85pp |
| indirect_main | momentum_confirm | +449.39pp | +576.47pp | -40.38pp | -109.56pp |

Timing can change a relative verdict through the baseline as well as the alternative. For EU Q75, momentum returns 255.27% under source timing and 261.40% under delayed timing, while their baselines return 320.05% and 222.87%. A positive delayed comparison does not erase the loss relative to the main source-date baseline.

## Entries and missed recoveries

Examples of first US admissions (all candidates are retained in the linked audit):

| Score/exit variant | Rule | Bloom | First Solar | GE Vernova |
|---|---|---|---|---|
| baseline | q50 | 2026-09-30 | 2026-03-31 | 2025-12-31 |
| baseline | q75 | 2026-09-30 | 2026-06-30 | Never held |
| trend | q50 | 2024-06-30 | 2022-06-30 | 2025-06-30 |
| trend | q75 | 2025-03-31 | 2026-06-30 | 2026-09-30 |
| momentum | q50 | 2020-09-30 | 2020-12-31 | 2025-06-30 |
| momentum | q75 | 2021-03-31 | 2022-09-30 | 2025-06-30 |
| confirm_exit | q50 | 2026-09-30 | 2026-03-31 | 2025-12-31 |
| confirm_exit | q75 | 2026-09-30 | 2026-06-30 | Never held |
| trend_confirm | q50 | 2024-06-30 | 2022-06-30 | 2025-06-30 |
| trend_confirm | q75 | 2025-03-31 | 2026-06-30 | 2026-09-30 |

Earlier first admission does not imply uninterrupted exposure to every later rally. Capacity removals can still occur under every exit variant.

[Every stock’s first-entry changes](first_entries.csv) includes earlier, later, new and missed entries. [Six-month outcomes after every baseline score exit](recovery_exit_diagnostics.csv) show subsequent baseline/variant exposure, with incomplete horizons right-censored. [Recovery counts](recovery_summary.csv) report both positive and nonpositive outcomes, including extra exposure to subsequent losses. These forward returns are hindsight diagnostics only; they do not enter any signal. [Exit review ledger](exit_reviews.csv) distinguishes attempted deferrals, actual retained positions, score exits and capacity removal.

| US rule | Variant | Positive six-month outcomes with more exposure | Nonpositive outcomes with more exposure |
|---|---|---:|---:|
| q50 | trend | 0 / 4 | 1 / 2 |
| q50 | confirm_exit | 2 / 4 | 1 / 2 |
| q75 | trend | 0 / 2 | 0 / 1 |
| q75 | confirm_exit | 2 / 2 | 1 / 1 |

These are outcomes after baseline score exits, with extra exposure measured by the number of subsequent monthly intervals held. Q50 and Q75 events can overlap and are not independent observations. The counts distinguish earlier selection from retaining stocks through subsequent recoveries or losses.

## Chronological sensitivity for the main scoring alternatives

Changes versus the matching baseline over each continuous-position subperiod. These windows were fixed in advance of the variant runs; the July 2020 boundary follows the recorded fundamental-feature coverage. Positions are not restarted at a boundary.

| Period | Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ |
|---|---|---:|---:|---:|---:|
| early | trend | +22.51pp | -29.24pp | -12.06pp | -30.34pp |
| early | momentum | +109.90pp | +174.05pp | +4.12pp | -32.59pp |
| early | trend_confirm | +44.70pp | -18.47pp | -8.29pp | -24.48pp |
| late | trend | +210.51pp | +175.80pp | +21.71pp | +17.61pp |
| late | momentum | +44.53pp | +37.32pp | -36.04pp | -17.04pp |
| late | trend_confirm | +223.85pp | +137.62pp | +17.08pp | +1.19pp |
| common_trend_coverage | trend | +299.05pp | +145.32pp | +15.82pp | +2.84pp |
| common_trend_coverage | momentum | +225.67pp | +297.98pp | -36.97pp | -32.04pp |
| common_trend_coverage | trend_confirm | +387.78pp | +131.70pp | +13.22pp | -15.14pp |

Fundamental trend improves 4 of four returns after July 2020 and 4 of four in the later 2023–2026 slice. Subperiod comparisons expose sensitivity to the early period and feature activation; they do not establish that missing early inputs are the sole cause.

## Feature coverage

Missing features retain the baseline score and never remove a stock. Early European fundamental-trend coverage is weaker than US coverage. The July 2020 boundary marks improved coverage for established names; IPO-related missingness remains, and continuous portfolio paths retain earlier position effects. This is not identical feature coverage or a fresh-start experiment. The raw [signal ledger](signal_features.csv) contains each current/prior observation, cutoff, price endpoint, factor and missing-feature reason.

| Case | Region | Company-months | Missing fundamental trend | Missing momentum |
|---|---|---:|---:|---:|
| direct_main | US | 1268 | 44 | 31 |
| direct_main | EU | 1267 | 130 | 12 |
| direct_timing_source | US | 1231 | 38 | 26 |
| direct_timing_source | EU | 1228 | 91 | 12 |
| direct_timing_delayed | US | 1231 | 44 | 26 |
| direct_timing_delayed | EU | 1228 | 141 | 12 |
| indirect_main | US | 1334 | 44 | 31 |
| indirect_main | EU | 1278 | 139 | 12 |

## Validation and limits

152 runs, 24 exact monthly baseline/control reproductions, and 3551 prior input/result files preserved byte-for-byte. Coverage, source dates, price endpoints, IPO history, costs, holdings and NAVs are checked. Selection state advances only on scheduled reviews; policy/data/delisting restrictions remain mandatory.

The candidate universe and adjusted-price histories retain their earlier retrospective-data limitations. Testing several informed alternatives on already-seen history creates selection risk even without a parameter sweep. The fixed method is committed alongside its outputs, not independently preregistered. Monthly drawdown omits intramonth losses; the historical timing tests are sensitivities, not proof of future performance.

Generated with Python 3.14.7. Hashes identify the committed snapshot; other Python/platform combinations may change the last floating-point digits of ledger text without a meaningful return change.

[Full summary and risk/cost metrics](summary.csv) · [Monthly active-return uncertainty](active_statistics.csv) · [Year returns](year_returns.csv) · [Validation](validation.json) · [Input hashes](input_manifest.json) · [Ledger replay and cutoff checks](independent_audit.json). Reproduce the latter with `python3 audit_recovery_experiments.py`. It reuses the input classes under test; it is not an independent implementation. The legacy output filename is retained for compatibility.
