# Longer histories and repaired timing comparison

Run `python3 run_long_history.py`. [Method](../LONG_HISTORY_METHOD.md). Builds on the coverage/timing correction inputs; source-date rules and costs remain unchanged. The method and results were committed together; this is not an independently timestamped preregistration.

**Scope: retrospective accounting-score tests, not a historical Pillar 2 backtest.** No government programme determines the June 2019 main start or September 2019 matched timing start. The dated industrial-policy participation gate is not applied. The separate [any prior public support experiment](../results_pillar2/REPORT.md) applies a broader historical support screen. Neither accounting-data coverage nor that broad screen establishes a full replication of the article’s programme definitions.

All 16 US and 15 EU candidates remain in the retrospective pool. Companies enter the information set only after listing; no predecessor price proxy is used. Every listed/eligible company has prices, FX and a usable original financial observation throughout each main source-date window. These are the earliest complete windows supported by the original reports recovered in this release, not a claim that earlier research is impossible.

Earliest complete starts: US **2019-06-30**, EU **2019-06-30**. Common cross-region start: **2019-06-30**. Endpoint: **2026-11-02**. US returns in USD; EU in EUR; costs 10bp/15bp per traded notional.

| Region | Window | Start | Q50 | Q75 | Equal weight |
|---|---|---|---:|---:|---:|
| US | earliest_complete | 2019-06-30 | 400.06% | 539.17% | 745.21% |
| US | cross_region | 2019-06-30 | 400.06% | 539.17% | 745.21% |
| US | prior_start | 2022-09-30 | 164.25% | 180.32% | 205.59% |
| US | timing_matched | 2019-09-30 | 343.55% | 430.54% | 720.69% |
| EU | earliest_complete | 2019-06-30 | 295.22% | 376.92% | 153.83% |
| EU | cross_region | 2019-06-30 | 295.22% | 376.92% | 153.83% |
| EU | prior_start | 2021-09-30 | 93.37% | 115.23% | 32.18% |
| EU | timing_matched | 2019-09-30 | 257.50% | 343.45% | 127.53% |

Earlier periods use annual reports where complete interim statements were not recovered. Subsequent original interim observations remain available; no annualization of invented quarters is used. Adding previously missing annual facts can also change results at the old start dates; the prior-start rows isolate this data effect from extending the holding period.

The preceding March 2019 review is incomplete: US Bloom/Linde original annual filings miss its March 1 information cutoff; EU ams, Safran, Enel and Nel also lack usable recovered figures at that cutoff. June is the next scheduled review after these original reports become available. Additional older original/pre-IPO archives could extend the boundary further; the audit does not declare such archives nonexistent.

## Timing correction

The earlier common-delay experiment also changed coverage: its unchanged freshness limits could expire a report before the delayed replacement became usable. The new `delay_adjusted` panel keeps the 180/90-day component availability floors but extends annual freshness from 550 to 730 days and interim freshness from 275 to 365 days. Source-date freshness stays 550/275 days. This offset is restricted to the artificial timing experiment.

Every delayed strategy is compared with the **fixed source-date equal-weight control**. Its own delayed-coverage control is reported separately so remaining initial-availability/membership changes stay visible. Extending freshness alone does not guarantee identical coverage, especially at the start or near a listing; only the fixed-control comparison keeps the hurdle unchanged.

First isolate the correction on the same inputs and starts as PR #3 (no newly recovered history):

| Region | Timing | Q50 | Q75 | Own control | Fixed source control | Q50 vs fixed |
|---|---|---:|---:|---:|---:|---:|
| US | source | 164.25% | 180.32% | 205.59% | 205.59% | -41.33pp |
| US | delay_legacy | 186.78% | 176.50% | 194.11% | 205.59% | -18.81pp |
| US | delay_adjusted | 209.86% | 165.57% | 203.47% | 205.59% | +4.28pp |
| EU | source | 85.81% | 115.23% | 30.89% | 30.89% | +54.92pp |
| EU | delay_legacy | 91.41% | 87.00% | 31.77% | 30.89% | +60.52pp |
| EU | delay_adjusted | 82.61% | 79.04% | 31.77% | 30.89% | +51.71pp |

The complete timing comparison starts **2019-09-30**, the earliest common quarter-end with full coverage under both timing policies. The June 2019 EU delayed panel has too few usable reports to run; it is not silently advanced or compared with a different source-date start. Both equal-weight controls have identical monthly NAVs throughout this matched window:

| Region | Timing | Q50 | Q75 | Own control | Fixed source control |
|---|---|---:|---:|---:|---:|
| US | source | 343.55% | 430.54% | 720.69% | 720.69% |
| US | delay_adjusted | 401.86% | 369.03% | 720.69% | 720.69% |
| EU | source | 257.50% | 343.45% | 127.53% | 127.53% |
| EU | delay_adjusted | 206.51% | 203.99% | 127.53% | 127.53% |

Reporting timing materially changes the EU result even with the control fixed: Q75's lead falls from 215.91pp to 76.45pp, and its monthly iid t-statistic falls from 1.83 to 0.80. The return ordering survives, but the size and statistical strength of the apparent advantage depend on the information-timing assumption.

## What the longer window shows

The [review diagnostics](REVIEW_DIAGNOSTICS.md) and [full evidence audit](evidence_audit.json), reproduced with `python3 audit_long_history_evidence.py --portfolio-sensitivities`, check the saved ledgers and rerun fixed quarterly starts and all-name omissions in memory. They do not change existing portfolio ledgers.

| Region | Rule | Monthly active t (iid) | Newey–West t (3 lags) |
|---|---|---:|---:|
| US | Q50 | -1.50 | -1.57 |
| US | Q75 | -0.60 | -0.62 |
| EU | Q50 | +1.39 | +1.61 |
| EU | Q75 | +1.72 | +2.22 |

These are nominal statistics over the completed monthly returns, with initial deployment and the terminal partial month excluded. Only EU Q75 exceeds 2 on the three-lag Newey–West version; none exceeds 2 on the iid version. They are not adjusted for the many variants examined or hindsight in the candidate list.

Much of the US divergence accumulated in 2020: equal weight returned 115.26%, versus 41.22% for Q50 and 47.31% for Q75. The control included Enphase (571.53%), Plug Power (973.10%) and Bloom Energy (283.67%) that year. Those are individual adjusted-price returns, not additive portfolio contributions.

From the December 2020 NAV through the endpoint, retaining the positions and history already established, US Q50 trails equal weight by 42.99pp while Q75 leads by 9.95pp. These continuous-position slices differ from starting new portfolios in December 2020; they must not be substituted for the external review’s restart figures.

| Region | Score window | Annual observations | Median period-end age |
|---|---|---:|---:|
| US | 2019_2020 | 97.37% | 273 days |
| US | 2022_onward | 31.89% | 120 days |
| EU | 2019_2020 | 97.03% | 273 days |
| EU | 2022_onward | 42.94% | 123 days |

Each stock-month score is counted once. Age is measured from accounting period end to the portfolio date, not from publication. The early history relies almost entirely on annual figures about nine months old, compared with about four months in the later observations; it is a different information regime, not simply more years of equivalent quarterly data.

The US equal-weight candidate pool returns 745.21% against 329.18% for the repository's sector-ETF blend. This gap reinforces the limitation of choosing today's candidate list retrospectively; it does not establish that the candidate list could have been selected prospectively.

## Every coverage gap

[All gaps](all_gaps.csv) lists each company/month, including a flag that separates listed candidates from prelisting/delisted cases. [Gap summary](gap_summary.csv) gives counts and exact dates. [Full pre-start coverage audit](coverage_audit.csv) includes every candidate each month and explains why earlier dates fail. None is silently removed to obtain an earlier main start.

| Region | Window | Timing | Company | Missing months | Dates |
|---|---|---|---|---:|---|
| EU | timing_repair | delay_adjusted | VIE.PA | 10 | 2021-09-30, 2021-10-31, 2021-11-30, 2021-12-31, 2022-01-31, 2022-02-28, 2022-03-31, 2022-04-30, 2022-05-31, 2022-06-30 |
| EU | timing_repair | delay_legacy | VIE.PA | 10 | 2021-09-30, 2021-10-31, 2021-11-30, 2021-12-31, 2022-01-31, 2022-02-28, 2022-03-31, 2022-04-30, 2022-05-31, 2022-06-30 |
| EU | timing_repair | source | VIE.PA | 7 | 2021-09-30, 2021-10-31, 2021-11-30, 2021-12-31, 2022-01-31, 2022-02-28, 2022-03-31 |
| US | timing_repair | delay_adjusted | MCHP | 1 | 2022-09-30 |
| US | timing_repair | delay_legacy | INTC | 1 | 2023-06-30 |
| US | timing_repair | delay_legacy | LRCX | 2 | 2022-12-31, 2023-12-31 |
| US | timing_repair | delay_legacy | MCHP | 1 | 2022-09-30 |

## Data limits and checks

The universe was selected retrospectively. Longer histories do not remove survivor/selection bias or include companies absent from the research candidate list. Monthly dividend/split-adjusted prices are the same frozen vendor series used in the earlier study; independent dated daily overlap is limited to the recent window. They are not a certified historical investable index. Listing overrides exclude pre-merger Linde/Praxair and pre-spin-off GE Vernova proxies.

Added 101 financial observations (100 annual and one GFS trailing observation): [observation inventory](added_observations.csv). Older original source facts, publication dates, component IDs, accession evidence and downloaded-source hashes are under [data/long_history](../data/long_history). The saved FX capture attributes its observations to FRED series pages and preserves every existing rate; the original acquisition chain is incomplete, as detailed below. Later comparative facts are not backdated to earlier reports.

Older TSM observations are standalone IASB-IFRS annual 20-Fs in TWD at their actual filing dates; later restored observations use the already documented Taiwan-IFRS series. No TTM calculation combines these bases. Linde 2018/2019 group operating cashflow explicitly includes the separately reported discontinued-operation cashflows; the source audit retains both rows and the arithmetic.

The US financial collector now rebuilds all 73 normalized observations from committed accession-level evidence with `python3 collect_long_history_us.py --check`, without private sibling directories. The two manual GlobalFoundries records remain explicit frozen inputs. This reproduces normalization, not acquisition of the complete SEC companyfacts responses, which are absent from the clone. Original response filenames, URLs and hashes remain in the manifest; re-extraction requires an explicitly supplied `--source sec --sec-cache-dir DIRECTORY`.

The FX capture has 2,374 saved observations: 310 match overlapping frozen rates and 2,064 supplement missing dates. The download manifest contains four timeouts and no successful capture record. No acquisition timestamp or original response body establishes how the saved values were obtained. The overlap check is useful internal consistency evidence, not independent verification of the 2,064 additions or a replacement for that missing provenance.

The engine honors explicitly requested starts before 2020 and exposes a freshness policy hook. Its original defaults remain unchanged. Historical source/code manifests are refreshed for the current checkout; validation distinguishes that metadata refresh from preserved data/result bytes and unchanged portfolio numbers.

Validation: 54 runs, 12 PR #3 reproductions, all selected source/component cutoffs, policy-specific freshness, full source-date coverage, listing restrictions, cost/holdings/NAV reconciliation, and 2512 prior data/result files preserved byte-for-byte.

Tests: `python3 -m unittest test_long_history.py test_research_corrections.py test_collect_long_history_us.py`. The portable collector tests include a replay of every released observation and rejection of mismatched accessions, dates and units.

[Summary including CAGR, volatility and drawdown](summary.csv) · [Calendar-year returns](year_returns.csv) · [Monthly active statistics](active_statistics.csv) · [Validation](validation.json) · [Input manifest](input_manifest.json).
