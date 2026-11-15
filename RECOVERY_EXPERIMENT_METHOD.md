# Scoring and exit-rule experiments

Fixed experiment definitions against commit 6e765ae's frozen results for the
any prior public support screen. The same rules are tested in the US and EU,
and every variant is reported. These are research alternatives; the current
default strategy is not replaced or automatically selected using these results.
Definitions were fixed in the working session before these variant returns
were calculated, but this document is committed alongside the results. It is
not independent preregistration, and the underlying history was already seen.
The broad support screen is not a replication of the article's narrower
Pillar 2 streams, basket weights or event-driven admission examples.

## Fixed variants

| Variant | Score | Score-based exit |
|---|---|---|
| baseline | Existing accounting composite | One quarterly Q25 breach |
| balanced | Geometric mean of ROCE and cash-quality ranks, 50/50 | Baseline |
| trend | Arithmetic 50% baseline + 50% fundamental-improvement rank | Baseline |
| momentum | Arithmetic 50% baseline + 50% price-momentum rank | Baseline |
| confirm_exit | Baseline | Two consecutive quarterly Q25 breaches |
| recovery_grace | Baseline | One-quarter grace when both fundamentals improve |
| no_score_exit | Baseline | No score-based exit; diagnostic only |
| trend_confirm | Trend score | Two-quarter confirmation |
| momentum_confirm | Momentum score | Two-quarter confirmation |

No parameter sweep, stock-specific override or second round of fitting follows
the observed returns. Q50/Q75 entry thresholds, quarterly admissions, monthly
weighting, 1.5pp score tilt, nine-stock cap, policy/listing restrictions, 10/15bp
costs and the frozen market endpoint remain unchanged. Capacity and eligibility
exits still apply to every variant, including the no-score-exit diagnostic.

## Information and factors

The baseline is the existing geometric accounting composite, with weights
0.25/0.37 on the ROCE rank and 0.12/0.37 on cash-quality rank.
Cash quality is negative cash accruals: (operating cash flow - net income) /
total assets. Trend compares these raw measures with the financial snapshot
actually usable at the review 12 months earlier, using that earlier month's
first-day information cutoff and freshness limits. Historical accounts need
not have passed the policy gate then, but must have been public and listed.
Rank each change within the currently policy-eligible names with that feature;
the improvement factor is the arithmetic mean of the two change ranks.
This is change in available fundamentals, not necessarily matching fiscal
quarters, and not change in a company's old percentile rank.

Price momentum uses adjusted investor-currency prices P(end month t-2) /
P(end month t-13) - 1 for execution month t. This implements the prior 2-12
month convention with the repository's first-of-month cutoff: at June 2019
review use April 2019 / May 2018. Both endpoints and FX observations precede
the cutoff; the most recent month is skipped. See the primary definition at
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html.
Actual listing/spin-off restrictions apply to both endpoints; no predecessor
price history supplies an IPO's missing lookback. Prices remain frozen vendor
adjusted histories, not a certified archive of historical signal vintages.

If the required feature is unavailable, that stock retains its baseline score.
Do not assign a neutral factor or remove it from the universe/control. Publish
every fallback and prior observation/price date. Early trend coverage is less
complete in Europe; also report July 2020 onward to expose that asymmetry.

## Exit state

Advance breach counts exactly once per quarterly portfolio review, not during
signal/audit calls. A score at or below Q25 is a breach. Reset on recovery at a
quarterly review or on removal. The two-review variant waits for two consecutive bad reviews, even if
the same annual filing is used; it does not claim two independent new reports.
Recovery grace retains a first-time breaching holding only when both raw
12-month improvements are strictly positive. A second consecutive breach
exits regardless. Missing trend earns no grace. Log deferred exits, breach
counts and capacity/eligibility removals separately. Keep a fresh state for
each portfolio run.

## Comparisons and diagnostics

Run all nine variants for both Q50 and Q75 in each region under four cases:
direct/source from June 2019; direct/source from September 2019;
direct/delayed financial timing from September 2019; and indirect-inclusive
source timing from June 2019. The two September cases use the corrected
730/365-day freshness for delayed fundamentals and 550/275 source limits.
Policy dates and price-feature availability do not receive an artificial delay.
There is one unchanged equal-weight control per case/region. Assert identical
coverage across variants and identical controls between September timings.

Show return/CAGR changes versus baseline and the fixed control, monthly
drawdown, costs, turnover, holding concentration and calendar-year results.
Report continuous-path 2019-2022 and 2023-end subperiods and July 2020-end,
without restarting positions. All these histories have already been examined;
none is a genuinely untouched out-of-sample test.

An improvement flag requires both US Q50/Q75 returns to improve and neither EU
Q50/Q75 return to fall on the full direct/source window. This is a descriptive
four-return screen, not a claim of no risk tradeoff. Separately report robustness
cases, later-period behavior, drawdown and costs. Do not promote a variant just
because it maximizes US total return.

Report first-entry changes for every stock and each baseline score exit's next
six-month stock return, with subsequent baseline/variant exposure. Right-censor
incomplete horizons and disclose delisting handling. Forward returns are
hindsight diagnostics only and never enter the signals or exit decisions.
Validate cutoff isolation, listing lookbacks, fallback coverage, exit-state
transitions, old baseline reproduction, and costs/holdings/NAV reconciliation.
