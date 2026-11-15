# EU interim-data results

EUR total returns, 30 September 2021 through 2 November 2026, after modeled 15bp trading costs.

| Financial inputs for the seven restored companies | Q75 | Q50 | Equal weight |
| --- | ---: | ---: | ---: |
| Annual restoration reference | 142.50% | 81.06% | 30.89% |
| Annual plus recovered interim reports | 119.59% | 86.21% | 30.89% |

The original eight companies retain their existing financial histories. The pool, prices, FX, costs and trading rules are fixed. The equal-weight control has identical eligibility and monthly NAV in both experiments; only the score portfolios respond to the newly available financial information.

## Coverage

| Ticker | Expected interims | Recovered | Valid TTM | Months scored using TTM | Months scored using annual |
| --- | ---: | ---: | ---: | ---: | ---: |
| ALFEN.AS | 6 | 6 | 6 | 32 | 30 |
| AMS.SW | 16 | 16 | 16 | 57 | 5 |
| ENR.DE | 16 | 16 | 16 | 52 | 10 |
| NEL.OL | 16 | 16 | 16 | 53 | 9 |
| ORSTED.CO | 16 | 16 | 16 | 48 | 14 |
| SAF.PA | 6 | 6 | 6 | 38 | 24 |
| VWS.CO | 16 | 16 | 16 | 47 | 15 |

Quarterly financial statements are used for Nel, Vestas, Orsted, ams OSRAM and Siemens Energy. Alfen and Safran supply half-year statements. Annual-score months are normal when a year-end report is the latest eligible fiscal period; they are not necessarily collection gaps.

There are 0 excluded or unrecovered observations; see [exclusion details](../data/eu_interim/exclusions.json).

## Construction and limits

Flow measures use observed prior annual + current YTD - comparative prior YTD; current balance-sheet figures are used directly. The arithmetic audit records every component. Contemporary restated annual comparatives or evidenced reclassifications are used where needed, with their actual availability dates. Original annual-score observations remain unchanged.

Some continuing/discontinued-operation and interest-classification conventions differ across issuers. These are documented in the company research files. Historical annual publication choices remain as in the earlier restoration; Q4 preliminary announcements have not been used to bring those annual observations forward. Some Safran availability dates conservatively use the full interim-report publication rather than the earliest preliminary release.

The October 31, 2026 rebalance uses information published strictly before October 1. The November 2 endpoint is a price mark without another rebalance. Later Q3 reports cannot affect this test. Future returns, a complete historical investable universe and original price/corporate-action accuracy are not established by this extension.

## Reproduce and inspect

Run `python3 run_eu_interim.py` from the repository root. The run is offline and uses the Python standard library.

- [Method fixed before results](../EU_INTERIM_METHOD.md)
- [Recovered TTM financial inputs and source links](../data/eu_interim/financials_interim.csv)
- [Source registry](../data/eu_interim/source_registry.json)
- [Component arithmetic](../data/eu_interim/arithmetic_audit.json)
- [Performance summary](summary.csv)
- [Coverage and source usage](interim_coverage.csv)
- [Validation](validation.json)
- [Input hashes](input_manifest.json)

Verified 276 TTM flow calculations and reproduced all three annual-restoration reference runs. Source timing, freshness, holdings, NAV and trading costs passed; 1823 prior files are unchanged.
