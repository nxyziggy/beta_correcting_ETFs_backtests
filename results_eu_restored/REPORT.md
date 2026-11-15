# EU coverage restoration results

Historical window: 30 September 2021–2 November 2026, EUR, after 15bp trading costs.

| Data panel | Q75 total return | Q50 total return | Equal-weight total return |
| --- | ---: | ---: | ---: |
| Published eight-company coverage | 57.07% | 71.38% | 89.02% |
| Restored primary reports | 142.50% | 81.06% | 30.89% |
| Restored, secondary fallback allowed | 142.50% | 81.06% | 30.89% |
| Original coverage, annual only | 63.68% | 53.64% | 89.02% |
| Restored coverage, annual only | 119.70% | 102.11% | 30.89% |

Restoring the seven companies reverses the ordering in this historical window: both score strategies outperform the broader equal-weight control. The annual-only restored comparison also has both strategies ahead.

The extra candidates change relative score percentiles as well as control holdings. For example, in the restored expanded runs Infineon is retained through the endpoint, whereas the original runs sold it in December 2025. STMicroelectronics exits in March 2026 rather than September 2025. No entry or exit threshold was retuned.

## Recovered observations

Recovered 42 primary annual observations. The mixed panel has 0 secondary fallback observations.

| Company ticker | Primary annual rows | First fiscal period | Last fiscal period | Restored coverage |
| --- | ---: | --- | --- | --- |
| ALFEN.AS | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |
| AMS.SW | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |
| ENR.DE | 6 | 2020-09-30 | 2025-09-30 | 62/62 months |
| NEL.OL | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |
| ORSTED.CO | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |
| SAF.PA | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |
| VWS.CO | 6 | 2020-12-31 | 2025-12-31 | 62/62 months |

Each of the seven names was added to the existing candidate pool. Eligibility, score thresholds and EDF delisting still apply. Adding a company to the pool does not require Q75/Q50 to hold it.

## What this comparison measures

The original eight companies retain their annual and interim observations in the expanded experiments. The seven restored companies have annual observations only. The annual-only pair compares both groups at annual frequency. Changing the pool also changes score percentiles and hence entries/exits; the difference is not only the return of seven additional holdings.

Reported consolidated operating profit is used for restored companies. Several frozen vendor observations instead match adjusted profit or later restatements. The source research files document those differences. The original eight companies were not re-audited as part of this extension.

Some selected annual-report dates are later than preliminary earnings releases; this uses evidenced conservative availability rather than claiming the earliest possible release. Safran FY2025 uses original full-year consolidated statements released on 13 February 2026; audit procedures were complete but the formal audit report was still pending. Nel FY2024 reports continuing-operation operating profit while group net profit and operating cash flow include discontinued operations. Separately displayed held-for-sale liabilities are excluded from literal reported current-liability subtotals. These accounting comparability limits remain explicit.

Historical prices, FX, candidate identities and all portfolio rules are inherited unchanged. This is not a new price-data or corporate-action audit. Original statement recovery does not remove retrospective candidate selection or prove future investment performance.

## Reproduction and evidence

Run `python3 run_eu_restoration.py` from the repository root. It is offline and uses only the Python standard library. Generated extension outputs are overwritten on rerun; published outputs remain untouched.

- [Method specified before restored returns](../EU_RESTORATION_METHOD.md)
- [Financial values and source links](../data/eu_restoration/restored_financials.csv)
- [Detailed normalized primary records](../data/eu_restoration/primary_inputs.json)
- [Wind-company source research](../data/eu_restoration/research_wind.json)
- [Alfen/Nel source research](../data/eu_restoration/research_energy.json)
- [Industrial-company source research](../data/eu_restoration/research_industry.json)
- [Monthly company coverage](restored_company_coverage.csv)
- [Performance summaries](summary.csv)
- [Validation checks](validation.json)
- [Input/source SHA-256 manifest](input_manifest.json)

Validation reproduced six published reference runs and confirmed that all 1627 manifested original input/result files remain unchanged. Each new run passed timing, freshness, observation-link, portfolio accounting, trading-cost and holding-bound checks.
