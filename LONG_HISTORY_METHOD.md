# Longer histories with complete eligible-company coverage

This document describes the released longer-history accounting-score experiment.
It is not an independently timestamped preregistration: the method and results
were committed together, and the earlier results were already known.

The retrospective universe contains all 16 US and 15 EU candidates, subject to
real listing/spin-off dates and EDF's delisting. Extending this fixed candidate
list backward does not remove survivorship/selection bias or reconstruct the
investable thematic universe at those earlier dates.

This experiment does not apply a dated government-program eligibility gate.
Government programs determine neither its main start nor its matched timing
start. The separate historical public-support experiment is described in
`PILLAR2_METHOD.md`; its eligibility assumptions do not establish eligibility
for this accounting-data experiment retrospectively.

The extension adds missing original financial reports and publication evidence,
prioritizing annual observations and retaining available interim observations.
It does not invent quarters, backdate revised comparative figures, or use
pre-merger predecessors as price proxies. Frozen prices, previous financial
observations, strategy rules, position limits, transaction costs and the
2 November 2026 endpoint remain the basis of the comparison. Earlier FX
observations supplement missing dates without replacing existing rates.

Starts follow the recorded data-availability audit, rather than a search over
returns. A main history includes every then-listed candidate with usable prices,
FX and dated financial inputs throughout its window. The audit reports blocking
names and periods; an unrecovered report does not remove a company from the
candidate pool. This establishes the earliest complete window in the recovered
dataset, not proof that every earlier archive was exhausted. The source-date
panel uses the first-of-month cutoff and 550-day annual/275-day interim freshness
limits, with no indefinite stale carry-forward. Listings after the cutoff enter
the next information set.

Results compare Q50, Q75 and equal weight from the earliest complete source-date
history, a common cross-region start, and the prior matched starts with added
historical facts. These separate new observations from a longer holding period.
The common timing sensitivity imposes a 180-day annual/90-day interim floor on
all inputs and their components, never making a source available before its
actual publication. Its freshness limits increase by the same delays, to
730/365 days. The old delayed/unextended treatment is retained as a diagnostic.
Every missing company-month is listed. Delayed strategies are compared with
both the fixed source-date control and their own eligible-coverage control;
a changing coverage set is not a pure timing test. In the complete matched
window the source-date and adjusted-delay control paths are identical.

Reporting includes annualized returns, monthly drawdown and volatility, calendar
year returns, holdings, coverage, provenance and validation. The oldest usable
observations recovered and remaining archive gaps are disclosed. Vendor monthly
prices are not a certified point-in-time total-return archive; independent dated
daily validation begins in July 2026.

## Portable financial-input rebuild

`python3 collect_long_history_us.py --check` replays the committed SEC
accession-level evidence in `data/long_history/us/source_registry.json`, including
the documented operating-income and cash-flow arithmetic, and compares all
73 observations with the released normalized inputs without writing files.
The two separately captured GlobalFoundries observations come from the committed
manual input and source files. The default command without `--check` rebuilds
only `normalized_inputs.json`; `--output-dir DIRECTORY` writes that file elsewhere.
It does not overwrite the frozen source evidence or capture manifest.

This reproduces normalization, not the acquisition of the complete SEC responses.
Those original companyfacts response bodies are absent from the repository;
their filenames, URLs and hashes are recorded in `source_manifest.json`.
Re-extraction from independently supplied snapshots requires the explicit command
`python3 collect_long_history_us.py --source sec --sec-cache-dir DIRECTORY`.
The collector no longer searches private folders outside the clone. Current
SEC responses can differ from the original snapshots as filings accumulate.

## FX provenance limitation

`data/long_history/prices/fx_web_capture.json` contains 2,374 saved rate records
attributed to the FRED series pages, dated 2 January 2018 through 22 May 2020.
The offline normalization checks that 310 overlapping records equal the frozen
rates and appends the remaining 2,064 records. This consistency check does not
independently validate the newly added rates.

The accompanying `fx_download_manifest.json` records four failed requests. It
contains no successful acquisition record for the saved capture, and the repo
has no acquisition timestamp or original response body tying that capture to
those FRED pages. The supplement is computationally reproducible from the saved
values, but its original acquisition chain is incomplete. No successful download
or source-capture evidence has been reconstructed or inferred from the URLs.
