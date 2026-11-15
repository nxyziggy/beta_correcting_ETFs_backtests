# Coverage, timing and concentration corrections

Run `python3 run_research_corrections.py`. Method: [predeclared corrections](../RESEARCH_CORRECTIONS_METHOD.md).

The main candidate universe retains Bloom Energy. Corrected source-date runs and a common timing policy are both shown; neither is selected for its performance. These are historical simulations through 2 November 2026, not evidence of a persistent selection advantage.

## Results bridge

Annual/interim labels describe the restored names. The original names retain their original annual and interim inputs in every row. Returns include US 10bp / EU 15bp trading costs. US starts 30 September 2022; EU starts 30 September 2021. Prices, FX, scoring, quarterly entry/exit reviews and monthly reweighting are unchanged.

| Region | Restored data / correction | Q75 | Q50 | Equal weight |
|---|---|---:|---:|---:|
| US | reference_released | 173.32% | 189.52% | 148.75% |
| US | reference_lam | 191.69% | 204.81% | 158.74% |
| US | reference_common | 111.68% | 154.64% | 145.29% |
| US | annual_released | 186.82% | 171.43% | 201.55% |
| US | annual_lam | 202.26% | 169.81% | 205.59% |
| US | annual_common | 166.53% | 207.85% | 194.11% |
| US | interim_released | 164.71% | 157.08% | 201.55% |
| US | interim_lam | 180.32% | 164.25% | 205.59% |
| US | interim_common | 176.50% | 186.78% | 194.11% |
| EU | annual_released | 142.50% | 81.06% | 30.89% |
| EU | annual_evidenced | 128.88% | 106.60% | 30.89% |
| EU | annual_common | 115.30% | 67.20% | 31.77% |
| EU | interim_released | 119.59% | 86.21% | 30.89% |
| EU | interim_evidenced | 115.23% | 85.81% | 30.89% |
| EU | interim_common | 87.00% | 91.41% | 31.77% |

`released` exactly reproduces the old snapshot; `lam` adds the four real Lam observations; `evidenced` corrects Safran annual dates; `common` includes these repairs and applies the same timing floor to every company and every source component.

## Lam Research: repair the missing facts

Added the original GAAP FY2024 release and FY2025 Q1–Q3 releases. TTM flows use FY2024 + current fiscal YTD − prior fiscal YTD; quarter-end balance sheets supply capital denominators. No expired filing is carried forward and no freshness threshold is relaxed.

[Source facts and original release URLs](../data/research_corrections/lam_sources.json) · [TTM arithmetic](../data/research_corrections/lam_arithmetic.json) · [monthly coverage and holdings](lam_monthly_coverage_and_holdings.csv).

- Released q75: 7 uncovered month-end observations (2025-01-31, 2025-02-28, 2025-03-31, 2025-04-30, 2025-05-31, 2025-06-30, 2025-07-31); 8 month-end holdings without Lam from January through August 2025. September 30 is the re-entry date, not a ninth absent month.
- Released q50: 7 uncovered month-end observations (2025-01-31, 2025-02-28, 2025-03-31, 2025-04-30, 2025-05-31, 2025-06-30, 2025-07-31); 8 month-end holdings without Lam from January through August 2025. September 30 is the re-entry date, not a ninth absent month.
- Released equal: 7 uncovered month-end observations (2025-01-31, 2025-02-28, 2025-03-31, 2025-04-30, 2025-05-31, 2025-06-30, 2025-07-31); 8 month-end holdings without Lam from January through August 2025. September 30 is the re-entry date, not a ninth absent month.

Lam has usable inputs at every monthly observation in the repaired source-date runs, with zero coverage exits. Score-based exits remain possible. The common-delay scenario closes the 2025 gap too, but has two older coverage gaps (December 2022 and December 2023): its artificial delay plus the unchanged first-of-month cutoff/freshness limit makes older reports expire before replacements become usable. These are separate timing-sensitivity effects, not missing FY2024/25 observations. The user-provided carry-forward figures are a different counterfactual; the corrected runs use newly recovered financial facts.

## Publication timing

Safran FY2020–24 now uses the original consolidated results attachments on 25 February 2021, 24 February 2022, 17 February 2023, 15 February 2024 and 14 February 2025. All 25 financial values match the original-year annual-report values already modeled; FY2025 already used results day. [Date/source evidence](../data/research_corrections/safran_date_corrections.json).

For broader comparability, `common` uses max(evidenced availability, period end +180 days for annual / +90 days for interim), including every component of a TTM input. Both original and restored names follow this rule. A genuinely later source remains later. This conservative scenario is not an estimate of the true earliest information date.

Other SEC/annual-report dates remain conservative evidence dates where earlier complete statements have not been verified. Safran interim dates also remain at their captured report dates. The source-date runs therefore still contain residual differences in source timing; use the common-policy rows to assess that sensitivity. This change does not certify an exhaustive earliest-release archive.

| Region / panel | Group | Annual observations | Median source lag | Median effective lag | Later than 180d |
|---|---|---:|---:|---:|---:|
| EU / interim_common | original | 46 | 43.5d | 180d | 0 |
| EU / interim_common | restored | 42 | 48d | 180d | 0 |
| EU / interim_released | original | 46 | 43.5d | 43.5d | 0 |
| EU / interim_released | restored | 42 | 58d | 58d | 0 |
| US / interim_common | original | 58 | 31d | 180d | 0 |
| US / interim_common | restored | 29 | 58d | 180d | 1 |
| US / interim_released | original | 57 | 31d | 31d | 0 |
| US / interim_released | restored | 29 | 58d | 58d | 1 |

Lag summaries include all annual input rows supplied to each panel, including pre-start history; they are not restricted to filings ultimately selected. The one annual exception beyond 180 days is GE Vernova FY2022, first captured in its March 2024 pre-listing registration statement. Its real filing date and April 2024 listing restriction are retained. [Every input and component ID](timing_audit.csv) and [annual lag summary](annual_lag_summary.csv) expose the sample and exceptions.

## Bloom and concentration

Removing the realized winner is an ex-post diagnostic, not a repaired investable strategy. Two tests are kept separate: remove a company from the control only (the strategies stay fixed), or remove it from the full scoring universe and rerun every rule. Every one of the 16 US candidates is omitted in turn, including companies that were not the winner.

| Panel | Omit Bloom from | Rule | Strategy | Control | Difference |
|---|---|---|---:|---:|---:|
| annual_released | control_only | q75 | 186.82% | 149.59% | +37.23pp |
| annual_released | control_only | q50 | 171.43% | 149.59% | +21.84pp |
| annual_released | whole_universe | q75 | 191.14% | 149.59% | +41.55pp |
| annual_released | whole_universe | q50 | 195.52% | 149.59% | +45.93pp |
| interim_released | control_only | q75 | 164.71% | 149.59% | +15.12pp |
| interim_released | control_only | q50 | 157.08% | 149.59% | +7.49pp |
| interim_released | whole_universe | q75 | 178.99% | 149.59% | +29.40pp |
| interim_released | whole_universe | q50 | 197.59% | 149.59% | +48.00pp |
| annual_lam | control_only | q75 | 202.26% | 154.67% | +47.59pp |
| annual_lam | control_only | q50 | 169.81% | 154.67% | +15.14pp |
| annual_lam | whole_universe | q75 | 206.81% | 154.67% | +52.14pp |
| annual_lam | whole_universe | q50 | 216.21% | 154.67% | +61.54pp |
| interim_lam | control_only | q75 | 180.32% | 154.67% | +25.65pp |
| interim_lam | control_only | q50 | 164.25% | 154.67% | +9.58pp |
| interim_lam | whole_universe | q75 | 194.18% | 154.67% | +39.51pp |
| interim_lam | whole_universe | q50 | 220.15% | 154.67% | +65.48pp |
| annual_common | control_only | q75 | 166.53% | 145.15% | +21.38pp |
| annual_common | control_only | q50 | 207.85% | 145.15% | +62.70pp |
| annual_common | whole_universe | q75 | 152.00% | 145.15% | +6.85pp |
| annual_common | whole_universe | q50 | 197.85% | 145.15% | +52.70pp |
| interim_common | control_only | q75 | 176.50% | 145.15% | +31.35pp |
| interim_common | control_only | q50 | 186.78% | 145.15% | +41.63pp |
| interim_common | whole_universe | q75 | 177.36% | 145.15% | +32.21pp |
| interim_common | whole_universe | q50 | 183.78% | 145.15% | +38.63pp |

Bloom's frozen adjusted-price return across the US window is 881.74%. Its contribution depends on when and how much each portfolio held, so it is not its stock return multiplied by a single initial weight.

| Panel | Rule | First held | Months held | Mean weight | Bloom net contribution |
|---|---|---|---:|---:|---:|
| annual_released | q75 | Never | 0 | 0.00% | 0.00pp |
| annual_released | q50 | Never | 0 | 0.00% | 0.00pp |
| annual_released | equal | 2022-09-30 | 50 | 6.49% | 47.25pp |
| annual_lam | q75 | Never | 0 | 0.00% | 0.00pp |
| annual_lam | q50 | Never | 0 | 0.00% | 0.00pp |
| annual_lam | equal | 2022-09-30 | 50 | 6.42% | 46.56pp |
| annual_common | q75 | Never | 0 | 0.00% | 0.00pp |
| annual_common | q50 | 2026-03-31 | 3 | 0.63% | 27.53pp |
| annual_common | equal | 2022-09-30 | 50 | 6.54% | 44.55pp |
| interim_released | q75 | 2026-09-30 | 2 | 0.60% | -13.86pp |
| interim_released | q50 | 2026-09-30 | 2 | 0.48% | -10.07pp |
| interim_released | equal | 2022-09-30 | 50 | 6.49% | 47.25pp |
| interim_lam | q75 | 2026-09-30 | 2 | 0.60% | -14.68pp |
| interim_lam | q50 | 2026-09-30 | 2 | 0.48% | -10.35pp |
| interim_lam | equal | 2022-09-30 | 50 | 6.42% | 46.56pp |
| interim_common | q75 | Never | 0 | 0.00% | 0.00pp |
| interim_common | q50 | Never | 0 | 0.00% | 0.00pp |
| interim_common | equal | 2022-09-30 | 50 | 6.54% | 44.55pp |

In the released interim panel, omitting Bloom from the full universe reproduces the reported +29.40pp / +48.00pp Q75/Q50 leads. With the strategies held fixed instead, omitting Bloom from the control gives +15.12pp / +7.49pp. The difference is caused by reranking and the ensuing changes to holdings. The diagnostic supports concentration sensitivity; it does not justify deleting Bloom from the main universe.

Across the 16 control-only omissions, Bloom has the largest effect on the control in the released and repaired interim panels. Removing Micron also reverses Q75’s gap; only removing Bloom reverses Q50’s gap under these source-date panels. Thus “one stock” is a useful explanation of much of the US result, not a literal claim that no other constituent matters.

[All leave-one-out results](us_leave_one_out.csv) · [monthly sensitivity NAVs](us_leave_one_out_monthly.csv) · [all-stock contribution accounting](us_attribution.csv). Contributions are final holding value minus net purchases minus that stock’s trading costs; they sum to the portfolio return on starting NAV 100. Mean weights are equally weighted month-end snapshots, including the initial deployment.

## Uncertainty

These statistics compare Q75/Q50 with their matched equal-weight control, not the ETF benchmark. They use complete monthly simple-return differences, exclude initial deployment and the partial final mark, and report both IID and Newey–West t-statistics (fixed three monthly lags, Bartlett weights, n/(n−1) finite-sample adjustment). Tracking error is annualized. Confidence intervals in the CSV use the large-sample 1.96 multiplier and are descriptive, not a multiple-testing correction.

| Region / panel | Rule | Months | Mean active / month | Tracking error | IID t | NW(3) t |
|---|---|---:|---:|---:|---:|---:|
| US / annual_released | q75 | 49 | -0.029pp | 17.12% | -0.04 | -0.04 |
| US / annual_released | q50 | 49 | -0.306pp | 15.00% | -0.49 | -0.53 |
| US / annual_lam | q75 | 49 | +0.055pp | 16.86% | +0.08 | +0.08 |
| US / annual_lam | q50 | 49 | -0.353pp | 14.78% | -0.58 | -0.62 |
| US / annual_common | q75 | 49 | -0.140pp | 17.89% | -0.19 | -0.21 |
| US / annual_common | q50 | 49 | +0.010pp | 14.20% | +0.02 | +0.02 |
| US / interim_released | q75 | 49 | -0.189pp | 16.85% | -0.27 | -0.28 |
| US / interim_released | q50 | 49 | -0.425pp | 15.19% | -0.68 | -0.74 |
| US / interim_lam | q75 | 49 | -0.095pp | 16.57% | -0.14 | -0.14 |
| US / interim_lam | q50 | 49 | -0.396pp | 14.61% | -0.66 | -0.74 |
| US / interim_common | q75 | 49 | -0.062pp | 17.87% | -0.08 | -0.09 |
| US / interim_common | q50 | 49 | -0.165pp | 15.70% | -0.25 | -0.28 |
| EU / annual_released | q75 | 61 | +1.087pp | 15.17% | +1.94 | +3.21 |
| EU / annual_released | q50 | 61 | +0.486pp | 11.43% | +1.15 | +1.53 |
| EU / annual_evidenced | q75 | 61 | +0.976pp | 14.63% | +1.81 | +2.79 |
| EU / annual_evidenced | q50 | 61 | +0.697pp | 11.32% | +1.67 | +2.08 |
| EU / annual_common | q75 | 61 | +0.895pp | 15.22% | +1.59 | +2.74 |
| EU / annual_common | q50 | 61 | +0.362pp | 10.70% | +0.91 | +1.34 |
| EU / interim_released | q75 | 61 | +0.868pp | 13.78% | +1.71 | +2.25 |
| EU / interim_released | q50 | 61 | +0.523pp | 11.92% | +1.19 | +1.36 |
| EU / interim_evidenced | q75 | 61 | +0.844pp | 13.80% | +1.65 | +2.20 |
| EU / interim_evidenced | q50 | 61 | +0.519pp | 11.92% | +1.18 | +1.36 |
| EU / interim_common | q75 | 61 | +0.576pp | 14.96% | +1.04 | +1.36 |
| EU / interim_common | q50 | 61 | +0.601pp | 10.90% | +1.49 | +2.08 |

A large cumulative return gap can coexist with a small monthly t-statistic. The short, concentrated, retrospectively examined sample cannot establish a stable stock-selection edge or infer that one scoring rule is generally inferior. Timing and constituent sensitivity are part of the result.

## Validation and preservation

Reproduced 15 released runs; checked 4 Lam sources, 9 TTM flow calculations, 25 Safran value matches, every selected source cutoff, freshness, holdings/NAV/cost reconciliation, zero Lam coverage gaps under evidenced dates and closure of the 2025 gap under common timing, and 288 leave-one-out reruns. All 2202 captured prior data/result files remained byte-for-byte unchanged.

Run `python3 -m unittest test_research_corrections.py` for six regression tests covering the missing months, January release cutoff, independently calculated Lam TTM values, Safran March availability, component delays and the statistical formulas.

[Validation](validation.json) · [input hashes](input_manifest.json) · [preserved snapshot hashes](preserved_file_manifest.json) · [full summary](summary.csv) · [active-return statistics](active_statistics.csv). The legacy engine argument `annual_lag_days=0` is retained in run names; the added `information_timing_policy` and annual/interim minimum-delay columns explicitly identify the common scenario’s effective delays.

Direct retrieval of Safran PDFs returned HTTP403; issuer PDF text and dated archive links were verified through web retrieval. The evidence JSON records that limitation, rather than inventing a downloaded-PDF hash. Lam release downloads have SHA-256 hashes and compact table evidence.
