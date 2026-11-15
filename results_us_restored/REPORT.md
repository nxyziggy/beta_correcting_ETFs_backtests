# US coverage restoration results

USD total returns, 30 September 2022 through 2 November 2026, after modeled 10bp trading costs.

| Financial coverage | Q75 | Q50 | Equal weight |
| --- | ---: | ---: | ---: |
| Published ten-company coverage | 173.32% | 189.52% | 148.75% |
| Six companies restored with annual reports | 186.82% | 171.43% | 201.55% |
| Six companies restored with annual and interim reports | 164.71% | 157.08% | 201.55% |

The original ten companies retain their existing histories. Candidate identities, prices, FX, costs, score rules and dates are fixed. Restoring financial coverage changes the stock pool and ranks. Quarterly updates can then change scores and trades within that restored pool.

## Restored company coverage

| Company | Months covered | First covered | First equal-weight holding | Annual score months | TTM score months |
| --- | ---: | --- | --- | ---: | ---: |
| BE | 50/50 | 2022-09-30 | 2022-09-30 | 10 | 40 |
| ETN | 50/50 | 2022-09-30 | 2022-09-30 | 11 | 39 |
| FSLR | 50/50 | 2022-09-30 | 2022-09-30 | 9 | 41 |
| GEV | 31/50 | 2024-04-30 | 2024-06-30 | 6 | 25 |
| PLUG | 50/50 | 2022-09-30 | 2022-09-30 | 9 | 41 |
| TSM | 50/50 | 2022-09-30 | 2022-09-30 | 12 | 38 |

Recovered 29/29 targeted annual observations and 73/73 usable interim observations. Exclusions or gaps: 0; see the [exclusion ledger](../data/us_restoration/exclusions.json).

GE Vernova remains ineligible before its 2 April 2024 listing. The control admits eligible new names at quarter-ends. Sixteen covered companies therefore does not mean sixteen holdings throughout the historical window.

The existing ten companies are unchanged, including inherited gaps in scored financial coverage: LRCX: 7 months, 2025-01-31 through 2025-07-31. Full monthly dates and reasons are in the run coverage ledgers.

The annual-restored and interim-restored equal-weight coverage and monthly ledgers are identical.

## Sources, timing and limits

New flows use original annual figures or comparable prior annual + current YTD − prior YTD; balance sheets are current. Every calculation records the source components. SEC facts retain accession and filing dates, and issuer reports supply missing disclosures. Full filing dates can be later than earnings announcements. A later published restatement is not available retroactively.

Eaton operating profit is a derived subtotal: sales less cost of products sold, selling/administrative expenses and research/development. It excludes separately reported financing, disposal and other income/expense lines. The component facts are documented; this is not an issuer-reported operating-income line, and the mixed other-income/expense line limits comparability.

TSMC annual and interim inputs consistently use Taiwan-endorsed IFRS consolidated statements filed on Form 6-K. They are not mixed with the IASB-IFRS 20-F annual series, whose tax-recognition timing can change net income and liabilities. Accounting-basis evidence and an example reconciliation are retained in the source records.

The last rebalance uses information published strictly before 1 October 2026. Later Q3 results cannot affect this fixed window. The inherited market data, retrospective universe, accounting comparability across companies and future performance are not independently established by this extension.

## Reproduce and audit

Run `python3 run_us_restoration.py` from the repository root; the calculation is offline and uses the Python standard library.

- [Method specified before returns](../US_RESTORATION_METHOD.md)
- [Annual inputs](../data/us_restoration/financials_annual.csv) and [interim inputs](../data/us_restoration/financials_interim.csv)
- [Source registry](../data/us_restoration/source_registry.json) and [arithmetic audit](../data/us_restoration/arithmetic_audit.json)
- [Summary](summary.csv) and [coverage](restored_company_coverage.csv)
- [Validation](validation.json), [input hashes](input_manifest.json) and [preserved-file hashes](preserved_file_manifest.json)

Validated 219 TTM flow calculations and all nine runs, including reproduction of all three published US reference runs. Source timing, latest-period selection, freshness, listing eligibility, holdings, NAV and costs passed. 2088 prior files remain unchanged.
