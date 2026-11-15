# Long-history review diagnostics

Reproduce without changing existing result ledgers: `python3 audit_long_history_evidence.py --portfolio-sensitivities --format markdown`. The JSON form retains every individual restart and omission. These checks use the ungated accounting-data experiment, not the separate historical public-support screen.

## Start dates and omitted companies

Ungated source-date inputs; fixed original costs, listing rules and endpoint. Fresh portfolios at each start. Each omission removes the company from both score-ranking universe and equal-weight control.

| Region | Rule | Fresh starts leading / tested | Omission runs leading / tested | Omission excess range |
|---|---|---:|---:|---:|
| US | Q50 | 0/14 | 0/16 | -371.44 to -37.61pp |
| US | Q75 | 0/14 | 1/16 | -348.97 to +22.51pp |
| EU | Q50 | 14/14 | 15/15 | +65.32 to +212.81pp |
| EU | Q75 | 14/14 | 15/15 | +145.05 to +375.73pp |

US omissions producing a lead: Q75 without GEV (+22.51pp).

Starts are the 14 quarter-ends from June 2019 through September 2022. These overlapping tests are sensitivity checks, not 14 independent confirmations. Omitting a company also changes relative ranks; this is not additive return attribution.

| Region | Rule | Fresh December 2020 excess | Continuous post-December 2020 excess |
|---|---|---:|---:|
| US | Q50 | -40.04pp | -42.99pp |
| US | Q75 | -26.34pp | +9.95pp |
| EU | Q50 | +75.93pp | +78.18pp |
| EU | Q75 | +78.32pp | +82.05pp |

The continuous slice retains positions and prior review history; a fresh restart deploys new portfolios. The two answer different questions and can have different signs.

## 2020 and information age

| Region | Q50 in 2020 | Q75 in 2020 | Equal weight in 2020 |
|---|---:|---:|---:|
| US | 41.22% | 47.31% | 115.26% |
| EU | 45.01% | 64.65% | 52.87% |

The 2020 US control included Enphase (571.53%), Plug Power (973.10%) and Bloom (283.67%). These are individual adjusted-price returns, not additive portfolio contributions.

| Region | Score window | Annual share | Median period-end age |
|---|---|---:|---:|
| US | 2019_2020 | 97.37% | 273 days |
| US | 2022_onward | 31.89% | 120 days |
| EU | 2019_2020 | 97.03% | 273 days |
| EU | 2022_onward | 42.94% | 123 days |

Each stock-month score counts once. Age runs from accounting period end to portfolio date, not publication. The 2022-onward median is about four months; the review’s three-month description is not reproduced under this definition.

## Statistics and common reporting delay

| Region | Rule | Monthly iid t | Newey–West t, 3 lags |
|---|---|---:|---:|
| US | Q50 | -1.50 | -1.57 |
| US | Q75 | -0.60 | -0.62 |
| EU | Q50 | +1.39 | +1.61 |
| EU | Q75 | +1.72 | +2.22 |

With the identical matched-window control, delaying reports and extending freshness reduces EU Q75 excess from 215.91pp to 76.45pp; iid t falls from 1.83 to 0.80.

Monthly statistics exclude the deployment row and terminal partial month. They use 88 monthly observations in the main window and 85 in the matched window. These nominal tests do not account for multiple strategies examined or retrospective candidate selection.

## Computational and source provenance

`python3 collect_long_history_us.py --check` rebuilds all 73 released normalized rows from committed accession-level evidence and explicit manual inputs. Full original SEC response bodies are not committed; their reacquisition is not reproduced by this check.

FX has 2,374 saved records, 310 exact overlaps and 2,064 additions. All four manifest entries are failed requests. The saved series-page URLs and overlap consistency do not establish the missing original acquisition chain or independently validate the additions.

No financial inputs, scores, default portfolio rules or published return ledgers are changed by this audit.
