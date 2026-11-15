# US financial coverage restoration

Specified before calculating the restored portfolios' returns.

Restore TSM, FSLR, PLUG, BE, ETN and GEV to the original-statement US
candidate pool. Preserve the existing ten companies' financial inputs,
prices, FX, listing dates, score rules, quarterly membership schedule,
monthly weighting, nine-stock strategy cap and 10bp trading costs.
Compare 30 September 2022 through 2 November 2026, the published US matched
window. The last rebalance is October 31; its information cutoff is October 1.

## Sources and timing

Prefer original issuer statements and SEC filing facts identified by their
accession, financial period and filing date. Historical facts extracted from
the SEC companyfacts API retain their original accession and filed date;
do not silently substitute a later restatement. Conservative full-filing dates
are acceptable and must be labeled. Earlier earnings releases and Q4
preliminary releases are not separately optimized for availability.

Eaton does not report a consolidated operating-income subtotal in the target
periods. Derive a consistent subtotal from reported net sales minus cost of
products sold, selling/administrative expenses and research/development.
Retain the component facts and label this as derived, not issuer-reported
operating profit. Separately presented interest, business-disposal gains and
other income/expense are excluded. The mixed nature of that last line is an
accounting-comparability limitation; do not choose a definition by returns.

TSMC annual and interim inputs consistently use the original consolidated
6-K statements under Taiwan-endorsed IFRS. Do not mix their net income or
balance sheets with the IASB-IFRS annual 20-F series: tax-recognition timing
can differ. Retain the issuer's accounting-basis disclosure and comparison
evidence, and flag this comparability limit in the results.

For TSM, FSLR, PLUG, BE and ETN, target annual FY2021–2025 and interims
H1/Q3 2022, Q1/H1/Q3 2023–2025, and Q1/H1 2026. For GEV, recover the
FY2022/2023 history released in the spin-off registration plus FY2024/2025,
and Q1/H1/Q3 2024–2025 and Q1/H1 2026. Prelisting financial statements
cannot make GEV investable before its existing 2 April 2024 listing date.

Each observation needs operating income, total group net income, operating
cash flow, total assets and current liabilities, with consistent units and
currency. Quarterly updates use twelve-month flows: previous annual plus
current year-to-date minus comparable prior-year year-to-date. Use the
current balance sheet. Document contemporary restatements and changes in
accounting basis; exclude unresolved combinations. No quarter is multiplied
by four and no missing figures are interpolated. Each calculation records its
source components and becomes usable only after every component is available.
The existing 550-day annual and 275-day interim freshness limits apply.

## Fixed experiments

Run Q75, Q50 and equal weight on three panels:

1. Published ten-company financial coverage, to reproduce the original result.
2. The same inputs plus recovered annual observations for all six companies.
3. The same restored pool plus recovered quarterly observations.

Report coverage and entry dates, especially GEV, rather than claiming all
16 were investable throughout the window. The equal-weight control should
change when companies return to the pool. Compare its annual and interim
versions separately to detect changes caused by data availability.

## Preservation and validation

Write new inputs under `data/us_restoration` and new runs under
`results_us_restored`. Preserve released inputs/results and both EU extensions.
Store compact source facts, dates, URLs, accession evidence and arithmetic;
keep full source downloads in the sibling `us_source_reports` directory.
Validate source timing and freshness, latest-period selection, arithmetic,
listing eligibility, holdings, NAV, costs and reproduction of the three
published US reference runs. Freeze file hashes before/after execution.

This extension does not change the retrospective candidate universe or
independently establish inherited market-data accuracy or future performance.
