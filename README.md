# Performative Beta Trap: ETF Backtest Replication

Reproduce transparent, accounting-based portfolio selection for US and European thematic equity universes using frozen market data and dated original financial statements.

**Research snapshot:** 4 November 2026. **Market-data endpoint:** 2 November 2026. **Python:** 3.10 or later; the released computation was verified with Python 3.12.14. **License:** [MIT](LICENSE) for project-authored code and documentation.

This repository accompanies MIT LEAD's Research to Trades, ["Performative beta trap"-correcting ETFs](https://mitleadtrades.substack.com/p/performative-beta-trap-correcting), published 3 June 2026. The article proposes using transparent portfolio admission and removal rules to reward corporate execution and improve the allocation of investor attention.

The implemented test measures a specific part of that idea: two accounting signals select and weight stocks from a defined candidate universe. It produces auditable historical portfolio returns, holdings, scores and trades. The article's broader claims about managerial incentives, industrial-policy effectiveness and network spillovers are research hypotheses; this simulation does not identify those causal effects.

## Quick start

**Longer histories and timing repair:** [extended results](results_long_history/REPORT.md)
recover older original annual statements across both full candidate pools.
These are retrospective accounting-score tests. Neither the June 2019 main
start nor the September 2019 matched timing start is justified by a government
programme; the historical Pillar 2 participation gate is not applied.
Run `python3 run_long_history.py`; tests: `python3 -m unittest test_long_history.py test_research_corrections.py`.
The main start dates require complete price, FX and financial coverage for every
then-listed eligible company. The timing sensitivity now extends freshness with
the artificial delay, fixes the source-date control, and lists every coverage
gap. A separate matched timing window also verifies that both equal-weight
controls have identical monthly NAVs. The preceding correction report below
is preserved as a snapshot; its unextended-freshness timing comparison is
superseded by this repair.

**Coverage, timing and concentration corrections:** use the
[corrected comparison](results_research_corrected/REPORT.md) for the follow-up
to the EU/US restorations below. Run `python3 run_research_corrections.py`.
It fills Lam Research's four missing reports, corrects Safran's annual
publication dates, applies a common information-delay sensitivity to all
companies, and reports Bloom attribution, every US leave-one-out test and
monthly active-return uncertainty. Bloom remains in the main universe.
Earlier tables below are preserved research snapshots; their data gaps and
timing conventions are documented in the correction report. Other unverified
earlier earnings-release dates remain conservative filing dates, so compare
both the evidenced-date and common-delay results.

**Additional EU coverage experiment:** [EU restoration results](results_eu_restored/REPORT.md)
restore all seven previously uncovered European candidates using 42 original
annual reports/statements for FY2020–FY2025. Run `python3 run_eu_restoration.py`
to reproduce that separate experiment. Its [method](EU_RESTORATION_METHOD.md),
source evidence, coverage checks and ledgers accompany the results. The
published reproduction described below retains its original inputs and outputs.

**EU interim extension:** [Interim-data results](results_eu_interim/REPORT.md)
add 92 original quarterly or half-year observations for those seven companies.
Run `python3 run_eu_interim.py` to compare the restored pool with and without
these interim updates. The [method](EU_INTERIM_METHOD.md), dated source records,
twelve-month calculations and validation accompany the results.

**US coverage extension:** [US restoration results](results_us_restored/REPORT.md)
restore TSM, FSLR, PLUG, BE, ETN and GEV using annual and quarterly histories.
Run `python3 run_us_restoration.py` to reproduce the original ten-company
control and compare it with the restored pool. The
[method](US_RESTORATION_METHOD.md) preserves the original trading rules and
GE Vernova's listing date, and documents Eaton's derived operating subtotal.

Clone this repository or extract `Actual_Dates_Backtest_Replication.zip`. Open a terminal in the directory containing `run_all.py`, `backtest.py` and `data/`. The ZIP names that directory `Actual_Dates_Backtest`.

Check Python:

```bash
python3 --version
```

Run the complete replication:

```bash
python3 run_all.py
```

No API key, paid database, internet connection or third-party Python package is required for the core replication. On Windows, use `py -3` in place of `python3` if that is how Python is installed.

The command rebuilds the financial inputs, calculates the packaged experiments, validates the results and writes CSV/LaTeX tables. It exits with a nonzero status if a stage fails. Successful completion ends with:

> Finished. See results_actual/ and tables_actual/. No network or API key was used.

**Rerunning overwrites the generated inputs and result/table files.** Keep an untouched extraction or Git commit for comparison. Use `run_all.py` as the entry point: it selects the actual-publication-date input pipeline used by the results documented here.

### Check file integrity

From the same directory, the following command checks the size and SHA-256 digest of every file listed in the input and result manifests. It works both before and after reproduction and exits nonzero on a mismatch.

```bash
python3 -c 'import hashlib,json,sys; from pathlib import Path; rows=[r for name in ("INPUT_MANIFEST.json","RESULT_MANIFEST.json") for r in json.loads(Path(name).read_text())]; bad=[r["path"] for r in rows if not Path(r["path"]).is_file() or not (Path(r["path"]).stat().st_size == r["bytes"] and hashlib.sha256(Path(r["path"]).read_bytes()).hexdigest() == r["sha256"])]; print("FAIL: " + ", ".join(bad) if bad else "PASS: all " + str(len(rows)) + " manifest entries match"); sys.exit(bool(bad))'
```

The release contains **489 input-manifest entries and 1,138 result-manifest entries**. [REPLICATION_VERIFICATION.json](REPLICATION_VERIFICATION.json) records an exact match of all 1,138 generated result/table files after a clean extraction and rerun. These manifests check the listed data and output bytes; they do not cover every source-code or documentation file. Preserve the Git commit when citing or extending a run.

## Results reproduced here

The headline specification is `panel=actual_expanded`, `window=matched`, `rule=q75` or `q50`, with trading costs of 10 basis points in the US and 15 in Europe. "Expanded" is the code's name for the panel admitting all complete annual and interim/TTM observations supplied in this snapshot.

US portfolios run from **30 September 2022 to 2 November 2026**, in USD. European portfolios run from **30 September 2021 to 2 November 2026**, in EUR. Within each region, the strategies and their controls share the same dates. The regional windows differ, so these are not like-for-like US-versus-Europe comparisons.

| Metric | US Q75 | US Q50 | EU Q75 | EU Q50 |
| --- | ---: | ---: | ---: | ---: |
| Strategy cumulative return | 173.32% | 189.52% | 57.07% | 71.38% |
| Strategy annualized return (CAGR) | 27.87% | 29.68% | 9.28% | 11.16% |
| ETF benchmark cumulative return | 139.63% | 139.63% | 10.18% | 10.18% |
| ETF benchmark CAGR | 23.82% | 23.82% | 1.92% | 1.92% |
| Covered-stock equal-weight control return | 148.75% | 148.75% | 89.02% | 89.02% |
| Maximum drawdown, monthly observations | -34.89% | -28.45% | -33.79% | -31.47% |
| Observed number of holdings | 3-6 | 5-7 | 2-4 | 3-5 |
| Final number of holdings | 6 | 7 | 4 | 5 |
| Final wealth from 100 units of starting capital | 273.32 | 289.52 | 157.07 | 171.38 |

Source: [results_actual/summary.csv](results_actual/summary.csv), using the filters above, and [Paper_Summary_expanded.csv](tables_actual/Paper_Summary_expanded.csv). Returns include modeled strategy/control trading costs; the ETF mixes are frictionless comparisons.

Both US strategies outperform both controls over their specified window. Both European strategies outperform the ETF mix but underperform the covered-stock equal-weight control. Q50 returns exceed Q75 by 16.20 percentage points in the US and 14.30 points in Europe. These comparisons describe this historical sample, not an established advantage in unseen data.

To print the four headline rows directly from the computed summary:

```bash
python3 -c 'import csv; rows=csv.DictReader(open("results_actual/summary.csv",newline="")); [print(r["region"],r["rule"].upper(),"return="+format(float(r["total_return"]),".2%"),"CAGR="+format(float(r["CAGR"]),".2%"),"monthly_drawdown="+format(float(r["max_drawdown_monthly"]),".2%")) for r in rows if r["panel"] == "actual_expanded" and r["window"] == "matched" and r["rule"] in ("q75","q50")]'
```

### Exact result directories

Each linked directory contains the ledgers for one headline portfolio.

| Portfolio | Result directory |
| --- | --- |
| US Q75 | [US_actual_expanded_q75_10bp_lag0_from2022-09-30_matched](results_actual/US_actual_expanded_q75_10bp_lag0_from2022-09-30_matched/) |
| US Q50 | [US_actual_expanded_q50_10bp_lag0_from2022-09-30_matched](results_actual/US_actual_expanded_q50_10bp_lag0_from2022-09-30_matched/) |
| EU Q75 | [EU_actual_expanded_q75_15bp_lag0_from2021-09-30_matched](results_actual/EU_actual_expanded_q75_15bp_lag0_from2021-09-30_matched/) |
| EU Q50 | [EU_actual_expanded_q50_15bp_lag0_from2021-09-30_matched](results_actual/EU_actual_expanded_q50_15bp_lag0_from2021-09-30_matched/) |

The `lag0` identifier means no extra fixed lag is added to the evidenced publication date. It does **not** mean information is available at fiscal period-end or tradable immediately on publication. The [information cutoff](#information-timing) still applies.

The corresponding equal-weight control uses the same directory name with `q75` or `q50` replaced by `equal`.

## How this connects to the article

The article supplies the economic motivation. This table connects its named concepts to the implemented constructs and their limits. Section links use browser text fragments; the full article remains available through the title link above.

| Article concept | Implementation in this repository |
| --- | --- |
| [Inattention and performative beta traps][article-problem] | Motivates examining a transparent allocation rule. The code does not estimate investors' attention, corporate hype or an economy-wide change in beta. |
| [Competition through portfolio admission and removal][article-solution] | `constrained_selection()` in [backtest.py](backtest.py) applies observable score thresholds at scheduled reviews. Event and selection ledgers make the decisions inspectable. |
| [Pillar 1: KPI scoring][article-kpi] | `Inputs.signals()` computes a reduced score from operating returns on capital employed and cash earnings quality. It does not implement all six proposed KPI dimensions. |
| [Pillar 2: Industrial policy][article-policy] | [universe.json](data/universe.json) supplies 31 retrospective candidates. Listing status, observed prices and usable financial inputs determine eligibility. A dated subsidy-event gate is not applied to the headline portfolios. |
| [Pillar 3: Competition and collaboration][article-network] | Network centrality, patent spillovers and geographic-cluster effects are unmeasured. They contribute no fabricated score or weight. |
| [Interaction of the three pillars][article-interaction] | The implemented composite combines two accounting ranks. Position weights are equal weights with a small financial-score tilt; they do not measure a collaboration premium or time-varying pillar interactions. |
| [Reproducible backtests][article-replication] | [run_all.py](run_all.py), frozen inputs, source records, validation and file manifests provide a computational audit trail. |

[article-problem]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Part%201%20-%20the%20Problem
[article-solution]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Part%202%20-%20The%20Solution
[article-kpi]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Scoring%20pillar%201%3A%20KPI%20scoring%20filtering%20performance
[article-policy]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Scoring%20pillar%202%3A%20Industrial%20Policy
[article-network]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Scoring%20pillar%203%3A%20Competition%20and%20Collaboration
[article-interaction]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=How%20the%20Three%20Scoring%20Pillars%20Interact
[article-replication]: https://mitleadtrades.substack.com/p/performative-beta-trap-correcting#:~:text=Easily%20reproducible%20backtests

For a concrete illustration of the admission/removal mechanism, Intel enters the US Q50 portfolio on 30 September 2022 and exits on 31 March 2023, when its composite score is approximately 0.102 against a Q25 threshold of 0.340. It is never held by US Q75. This is an accounting-score result; it does not measure Intel's subsidy utilization or project execution. Inspect the US Q50 [event ledger](results_actual/US_actual_expanded_q50_10bp_lag0_from2022-09-30_matched/events.csv) and [score ledger](results_actual/US_actual_expanded_q50_10bp_lag0_from2022-09-30_matched/scores.csv).

## Strategy specification

### Financial signals and composite score

Each usable company observation requires operating income, net income, operating cash flow, total assets and current liabilities, with source and publication-date evidence.

The two raw signals are:

- **Operating return on capital employed:** operating income divided by closing total assets minus closing current liabilities.
- **Cash accruals:** net income minus operating cash flow, divided by closing total assets. Lower cash accruals receive higher quality ranks.

In formulas, with parentheses fixing the denominators:

$$
\mathrm{ROCE}=\frac{\mathrm{Operating\ income}}{\mathrm{Total\ assets}-\mathrm{Current\ liabilities}},
\qquad
\mathrm{Accruals}=\frac{\mathrm{Net\ income}-\mathrm{Operating\ cash\ flow}}{\mathrm{Total\ assets}}.
$$

Rank ROCE and negative cash accruals within the eligible, financially covered companies in the same region at that review. If `r_ROCE` and `r_quality` are those percentile ranks, the composite is:

$$
S=\exp\left(\frac{0.25\log(r_{\mathrm{ROCE}})+0.12\log(r_{\mathrm{quality}})}{0.37}\right).
$$

For exact replication, `ranks()` assigns `(number below + 0.5 * number equal) / number of companies`. Thus tied raw values receive the same positive midrank. `percentile()` computes the Q25/Q50/Q75 thresholds by linear interpolation at position `(n - 1) * q` in the sorted composite scores.

ROCE here uses closing balance-sheet capital, not average capital or ROIC minus WACC. Cash accruals are an earnings-quality proxy, not a direct estimate of narrative salience.

### Membership and weights

| Rule | Exact behavior |
| --- | --- |
| Review schedule | Normal additions, score exits and reentries occur at March, June, September and December month-ends. Scores, target weights and NAV update monthly. |
| Q75 admission | A company qualifies when its composite is strictly above the regional Q75 threshold at one quarter-end review. |
| Q50 admission | A company qualifies when its composite is strictly above the regional median at one quarter-end review. |
| Score exit | An existing holding exits at a quarter-end review if its score is at or below Q25. An incumbent can remain below its admission threshold while still above Q25. |
| Data/eligibility exit | Loss of usable data or eligibility can remove a holding at a monthly review, including outside quarter-end. This is logged separately from a score exit. |
| Holding bounds | Between 1 and 9 stocks. If the survivor/qualifier set exceeds 9, retain the highest scores, with ticker order breaking exact score ties. |
| Minimum fallback | If needed, admit the highest-scoring available company above Q25 to meet the one-stock minimum; log the exception. No such admission occurs in the four headline runs. |
| Coverage requirement | At least four eligible, scored companies are required for the simulation to continue, even though the portfolio may hold fewer. Insufficient coverage raises an error. |
| Monthly allocation | Start each holding at `1 / number_of_holdings`; add 0.015 to a holding whose score is at or above regional Q75; normalize the weights once to sum to one. |

The strategy is long-only and fully invested apart from numerical cash residuals. It has no leverage, short positions or tactical cash allocation. The 60/40 and 50/50 splits below apply to the ETF benchmarks, not to sector quotas in the selected stock portfolios.

### Information timing

An input is usable only when its complete availability date is **strictly before the first calendar day of the rebalance month**. For example, a report released during October can first affect the November month-end rebalance. It cannot change October's holdings.

The panel selects the latest eligible fiscal-period observation for each company from the supplied annual and trailing-twelve-month (TTM) records. Annual observations remain usable for up to 550 days from fiscal period-end; interim/TTM observations for up to 275 days. These age limits are measured at the modeled review date.

[build_actual_financials.py](build_actual_financials.py) constructs trailing flows using issuer-reported TTM values, annual plus current year-to-date minus comparable prior-year year-to-date values, compatible observed quarter differences, or four observed consecutive fiscal quarters. Each calculation records its components. Availability is the latest publication date among those components. Later-published comparative figures become available when published, not retroactively.

No quarter is multiplied by four, and missing periods are not interpolated. Annual and half-year reporting are retained where appropriate.

### Benchmarks, costs and valuation

| Region | Reporting currency | ETF comparison, rebalanced monthly | Strategy and stock-control trading cost |
| --- | --- | --- | --- |
| US | USD | 60% SOXX + 40% ICLN | 10 basis points per dollar bought or sold |
| Europe | EUR | 50% EXV3.DE + 50% IQQH.DE | 15 basis points per euro bought or sold |

The **covered-stock equal-weight control** holds every eligible company with usable financial data in the region. It admits companies at quarter-ends, removes coverage/eligibility losses monthly and reweights equally each month. It has no nine-stock cap and no score tilt. It tests the additional effect of selection and weighting relative to holding the available candidate pool.

Both stock portfolios and stock controls pay costs on absolute traded value, including initial deployment. `rebalance()` solves post-trade NAV and target positions consistently with those costs. ETF benchmark rebalancing is frictionless. Returns exclude management fees, investor taxes and additional market impact.

The engine uses frozen observed adjusted prices and observed FX. When combining price sources, it chains observed returns rather than splicing incompatible adjusted-price levels. The EDF delisting is represented by the documented EUR 12 cash consideration. Source-selection and valuation audits are included.

The last complete monthly valuation is labeled **31 October 2026**, using the observed last trading close. Holdings are then marked through **2 November 2026** without an additional membership rebalance. The endpoint is fixed; rerunning on a later date does not fetch new observations.

## Data and provenance

There are **333 original financial observations**, yielding **310 complete scoring inputs: 103 annual and 207 TTM**. Twenty-three observations lack components required to form complete scoring inputs. Complete records exist for **18 of the 31 candidates**, comprising 10 US and 8 European companies.

| Coverage in the supplied financial records | Companies |
| --- | --- |
| US, annual and interim/TTM | AMAT, ENPH, GFS, INTC, LIN, LRCX, MCHP, MU, NEE, TXN |
| Europe, annual and interim/TTM | AIR.PA, ASML, IFX.DE, NXPI, STMPA.PA |
| Europe, annual only | EDF.PA, ENEL.MI, VIE.PA |

Coverage across the dataset does not imply continuous eligibility or a portfolio position on every date. The other 13 candidates receive no neutral score, zero-filled inputs or vendor-financial fallback in the headline specification. An exclusion for missing captured data is not evidence that the issuer failed to report.

| Evidence | Location |
| --- | --- |
| Candidate identities, region, currencies and listing dates | [data/universe.json](data/universe.json) |
| Original-period facts, publication dates, source URLs and extraction references | [parsed_observations.json](data/actual_dates/parsed_observations.json), [reviewed_observations.json](data/actual_dates/reviewed_observations.json), [financials_supplement.csv](data/financials_supplement.csv) |
| Unit-normalized observations | [observations_normalized.json](data/actual_dates/observations_normalized.json) |
| Component-by-component trailing arithmetic | [calculation_audit.json](data/actual_dates/calculation_audit.json) |
| Incomplete trailing inputs | [ttm_exclusions.json](data/actual_dates/ttm_exclusions.json) |
| Captured factual financial-table excerpts | [financial_excerpts.json](data/actual_dates/financial_excerpts.json) |
| Model-ready annual and trailing inputs | [financials_actual_annual.csv](data/financials_actual_annual.csv), [financials_actual_quarterly.csv](data/financials_actual_quarterly.csv) |
| Monthly/daily market observations and FX | [data/](data/), including `prices_monthly.csv`, `extension_prices_daily.csv`, `extension_month_end_prices.csv` and `fx_daily.csv` |
| Fixed endpoint and valuation configuration | [extension_config.json](data/extension_config.json) |
| Company-level coverage table | [13_Company_Coverage.csv](tables_actual/13_Company_Coverage.csv) |

Follow the source URLs and observation/component identifiers to audit a value back to its evidence. The core run starts from the supplied factual records; collecting or re-extracting the underlying issuer documents is a separate task.

## Code and output guide

### Computation pipeline

| File | Responsibility |
| --- | --- |
| [run_all.py](run_all.py) | Runs the following four stages in order, using the same Python interpreter. |
| [build_actual_financials.py](build_actual_financials.py) | Normalizes source facts and builds dated annual/TTM financial inputs and calculation audits. |
| [run_actual_dates.py](run_actual_dates.py) | Configures and calculates the packaged experiment set. |
| [validate_actual.py](validate_actual.py) | Checks source arithmetic, timing, freshness, frozen market inputs, portfolio accounting and costs. |
| [make_actual_tables.py](make_actual_tables.py) | Produces CSV and LaTeX tables, including the headline summaries and quarterly histories. |
| [backtest.py](backtest.py) | Shared scoring, selection, FX, valuation, rebalancing and performance calculations. |

The full command generates 114 experiment summaries. To identify the results documented in this README, use the explicit `actual_expanded` / `matched` / `q75,q50` filters, rather than selecting rows by their position in a file.

### Inspect the results

| Output | Contents |
| --- | --- |
| [summary.csv](results_actual/summary.csv) | Run identifiers, parameters, dates, cumulative returns, CAGR, risk statistics, costs and controls. |
| [Paper_Summary_expanded.csv](tables_actual/Paper_Summary_expanded.csv) and [.tex](tables_actual/Paper_Summary_expanded.tex) | Headline four-portfolio performance table. |
| [08_Expanded_Monthly.csv](tables_actual/08_Expanded_Monthly.csv) | Monthly portfolio and benchmark histories. |
| [09_Expanded_Quarterly_Scores.csv](tables_actual/09_Expanded_Quarterly_Scores.csv) | Quarter-end company scores and threshold information. |
| [10_Expanded_Events.csv](tables_actual/10_Expanded_Events.csv) | Admissions, exits and reentries. |
| [11_Final_Holdings.csv](tables_actual/11_Final_Holdings.csv) | Holdings at the fixed endpoint. |
| [12_Expanded_Return_Attribution.csv](tables_actual/12_Expanded_Return_Attribution.csv) | Stock-level return contributions and trading costs. |
| [validation.json](results_actual/validation.json) | Machine-readable checks and outcomes. |

Within each result directory, `monthly.csv` records NAV and rebalancing; `quarterly.csv` records quarterly performance; `scores.csv` records input dates, signals and thresholds; `holdings.csv` records positions and weights; `trades.csv` records traded value and costs; `events.csv` records membership decisions; `coverage.csv` records eligibility exclusions; and `selection_audit.csv` records count constraints. Daily valuation files provide the available daily observations near the endpoint.

Most CSV return fields are **fractions**, so `1.733194...` means a 173.3194% return. Starting capital is 100 NAV units.

- `total_return`: final NAV / 100 - 1, including initial deployment costs.
- `CAGR`: annualized return using elapsed days divided by 365.2425.
- `max_drawdown_monthly`: peak-to-trough drawdown over the monthly NAV observations, with an initial peak of 100.
- `Sharpe_rf0_monthly`: arithmetic mean monthly return divided by monthly standard deviation, annualized, assuming a zero risk-free rate; the initial deployment row is excluded.
- `Paper_CAGR_div_vol`: CAGR divided by annualized monthly volatility, a separate statistic from the arithmetic Sharpe ratio.
- `relative_alpha` / `AlphaRatio`: strategy NAV / benchmark NAV - 1; this is relative wealth, not factor-adjusted alpha.
- `active_return_pp`: strategy cumulative return minus benchmark cumulative return in fractional units; multiply by 100 for percentage points.

Monthly risk statistics stop at the complete month-end; the total-return/CAGR endpoint includes the 2 November mark. Initial and unfinished quarters are explicitly flagged as partial in `quarterly.csv`.

## Validation and interpretation

The packaged checks cover 310 complete dated inputs, 140 quarter-to-annual reconciliations, 49,149 score-row timing/freshness checks, 6,600 monthly portfolio accounts and 39,120 trade-cost rows across the computation. Exact reproduction establishes that the supplied inputs and code generate the recorded outputs.

It does not establish a complete historical investable index. The candidate universe is retrospective, financial coverage is incomplete, and accounting definitions and restatements across issuers are not comprehensively harmonized. Source dates are evidenced, but the package is not a certified archive of every first-published document version. Public price histories can contain errors or retrospective corporate-action adjustments.

The portfolios are concentrated and materially exposed to semiconductors. Monthly drawdown statistics can miss larger intramonth losses. No out-of-sample or causal test establishes that the selection rules improve future returns or corporate behavior. Unmeasured subsidy utilization, CapEx delivery, WACC, governance, lobbying, analyst expectations and network factors remain unavailable. Adding such factors could improve or reduce performance.

This is a research replication package, not a live data service, a traded ETF or a trading execution system.

## Contributing and extending the research

Reproduce the snapshot first. For a correction or extension, open a GitHub issue or pull request with the affected ticker/period or run identifier, the source evidence, the expected behavior and the observed difference.

Keep changes reviewable:

1. Preserve source URLs, fiscal dates, units and actual publication dates for new financial facts. Record all arithmetic components and explicit missingness.
2. Use observed price/FX data and retain their dates, adjustment conventions and provenance.
3. Specify changes to the universe, scoring or portfolio rules before interpreting their returns.
4. Update the endpoint in both `data/extension_config.json` and `build_actual_financials.py` when extending the data horizon; supply the required observations and review the fixed-date expectations in `validate_actual.py`.
5. Rerun the pipeline, inspect accounting and timing checks, and publish new manifests and verification evidence with the changed snapshot.

The supplied source-processing and report-export helpers are not required for the core command. Optional report rendering has additional Python dependencies; no installation of those packages is needed to reproduce the CSV results.

## Citation

Please cite the article for the conceptual framework:

> MIT LEAD's Research to Trades. (2026, June 3). *"Performative beta trap"-correcting ETFs: Going beyond headlines with Mechanism Design to cultivate crowd wisdom, at scale.* [Substack](https://mitleadtrades.substack.com/p/performative-beta-trap-correcting).

For numerical replication, also identify **Performative Beta Trap: ETF Backtest Replication, research snapshot 4 November 2026, market-data endpoint 2 November 2026**, and include the repository URL, exact Git commit and run identifier used. Retain the input/result manifests with any reported replication.

Citation is requested for research attribution; it is not an additional condition of the MIT license.

## License

Project-authored code and documentation are available under the [MIT License](LICENSE); the [Open Source Initiative's MIT license page](https://opensource.org/license/mit) provides the standard license text.

The MIT license does not relicense third-party issuer materials, market-data captures, the referenced article or third-party names and marks. Their respective rights and terms continue to apply. Retain source attribution and assess applicable source terms when redistributing those materials.

The software is provided without warranty, as set out in [LICENSE](LICENSE).
