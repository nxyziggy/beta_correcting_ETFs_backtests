# Longer histories with complete eligible-company coverage

Specified before evaluating the extended portfolio returns. This extension
builds on the unmerged coverage/timing corrections in PR #3. Keep both PRs open.

Keep all 16 US and 15 EU candidates in the retrospective universe. Respect real
listing/spin-off dates and EDF's delisting. The candidate list was selected
retrospectively; extending it backward does not remove survivorship/selection
bias or reconstruct the investable thematic universe at those earlier dates.

Scope clarification: these are retrospective accounting-score experiments,
not a historical implementation of Pillar 2 industrial-policy eligibility.
No government programme determines either the main start or the matched timing
start. The optional dated participation gate in backtest.py is not enabled.
The captured policy_eligibility.csv ledger has no event before 2022; it is an
incomplete evidence inventory, not proof that no earlier programmes existed.
A Pillar 2 test requires a separately reconstructed, dated company-eligibility
history. Availability of 2019 accounting data does not establish that history.

Recover missing original financial reports and publication evidence backward,
prioritizing annual observations; retain available interim observations without
inventing quarters or backdating revised comparatives. Preserve all frozen
prices, previous financial observations, strategy rules, position limits,
transaction costs and the 2 November 2026 endpoint. Add official FX observations
only where the earlier window lacks them; never overwrite an existing rate.
Do not use another company or pre-merger predecessor as a price proxy.

Select starts by data availability, never by returns. Audit every month from
available market-history bounds. A main history must include every then-listed
candidate with usable prices, FX and dated financial inputs throughout its
window. Missing source capture is not a reason to redefine a company out of
the candidate pool. If a strict all-listed-name history cannot begin earlier,
report the exact blocking names/periods and distinguish a labeled coverage
sensitivity from the main result. Reports retain the first-of-month cutoff and
550-day annual/275-day interim freshness limits. No stale carry-forward.

Show Q50, Q75 and equal weight for the earliest complete source-date history,
a common cross-region start, and the prior matched starts with added historical
facts, so effects of new data can be separated from the longer holding period.
Listing eligibility is evaluated at the first-of-month information cutoff;
a company listing later in that month first enters the next information set.
Include the common 180/90-day timing policy for all inputs and components as a
sensitivity. Following the user's additional correction, extend its annual
freshness limit from 550 to 730 days and interim limit from 275 to 365 days.
The source-date panel retains 550/275 days. No source is made usable before its
real publication. Retain the old delayed/unextended panel only as a diagnostic,
list every company-month gap in both treatments, and compare delayed strategies
against the fixed source-date equal-weight control as well as their own
eligible-coverage control. Do not describe a changing-coverage comparison as
a pure timing test.
Include annualized return, monthly drawdown/volatility, year returns, holdings,
coverage, original-data provenance and validation. Document the actual oldest
usable data recovered, and remaining archive gaps; do not claim that an
unsearched earlier period is impossible or that the vendor price history is a
certified point-in-time archive.
