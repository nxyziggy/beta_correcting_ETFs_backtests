# EU interim-data extension

Specified before calculating this extension's portfolio returns.

The user approved recovering finer financial histories for the seven restored
EU candidates. Target genuine quarterly statements for Nel, Vestas, Orsted,
ams OSRAM and Siemens Energy, and half-year statements for Alfen and Safran.
Recover observations needed from the September 2021 start through the fixed
2 November 2026 endpoint. The last membership/weight rebalance is October 31,
with an information cutoff of October 1; reports published after September 30
cannot affect this frozen backtest, even if their fiscal period ends earlier.

Keep the original eight companies' financial inputs, all 42 recovered annual
observations, the candidate pool, prices, FX, trading rules, 15bp costs and
start/end dates fixed. Preserve results_actual and results_eu_restored.

## Constructing observations

Each source observation records the actual publication date, period end,
reported consolidated operating profit and total net profit, operating cash
flow, total assets and current liabilities. Use IFRS reported profits rather
than adjusted EBIT/EBITDA or free cash flow. Preserve units, currency, current
and comparative columns, URLs, source-page evidence and important notes.

Twelve-month flows are previous annual + current year-to-date - comparable
prior-year year-to-date. Balance-sheet values come from the current interim
statement. Use issuer-reported twelve-month values if directly provided.
Use a contemporaneously available comparable prior annual column when a
restatement requires it; record its source/date and explicit arithmetic.
Known unresolved reporting-scope mismatches are excluded, not silently mixed.
No quarter/half-year is multiplied into an invented annual figure. A later
restated number becomes available only on the later source's publication date.
Every source component must precede the existing month-start information cutoff.

The engine's annual 550-day and trailing 275-day freshness limits remain.
If a valid interim observation is unavailable, the existing latest usable
annual observation can remain under those rules. Report these fallbacks and
unresolved gaps explicitly. Do not optimize data choices against returns.

## Fixed comparison

Run Q75, Q50 and equal weight for:

1. The annual restoration reference, retaining the original eight companies'
   existing interim data and annual data for the seven restored companies.
2. The same pool with all newly recovered valid interim observations added.

The equal-weight control should remain unchanged if eligibility coverage is
unchanged. Differences in strategy returns reflect changed information and
resulting score ranks/trades under fixed rules. This does not establish future
performance or repair inherited price/corporate-action or retrospective-pool
limitations. No source date or rule will be chosen by its realized return.

## Artifacts and validation

Raw observations, arithmetic audit, exclusions and normalized inputs go under
data/eu_interim; results and ledgers under results_eu_interim. Keep full source
documents outside Git in the sibling eu_source_reports directory, retaining
compact factual excerpts and source hashes/URLs in the repository.
Reproduce the prior annual-restoration results, verify source arithmetic and
timing, input freshness, weights, NAV, trade costs, coverage and holding bounds.
Check hashes before and after to confirm prior inputs/results are preserved.
