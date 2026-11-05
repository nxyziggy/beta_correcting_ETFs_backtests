> Current holding-range override: use minimum 1 and maximum 9, as recorded in HOLDINGS_RULE_CHANGE.md. The original 3-7 specification below is retained as historical context; all other conventions remain applicable.

# Concentrated strategy: 3 to 7 holdings

Rule recorded before computing this revision's returns. The user requested more restrictive entry and 3-7 stock holdings at any point. The underlying 16 September 2026 data snapshot is unchanged.

## Primary specification

- Normal entry and reentry require a composite score strictly above the cross-sectional 75th percentile (Q75). One qualifying calendar quarter end suffices.
- Existing holdings remain until a quarter-end score at or below Q25, loss of coverage/eligibility, actual delisting, or removal to satisfy the seven-stock cap.
- At each quarter end, combine retained holdings above Q25 with all normal entry candidates. If there are more than seven, retain the seven highest composite scores. Exact ties are resolved by ticker, ascending.
- If fewer than three stocks remain, add the highest-scoring remaining eligible stocks strictly above Q25 until there are three. Every such admission is explicitly logged as ENTER_FLOOR. The three-stock minimum therefore takes precedence over the stricter entry gate; it never licenses missing data or a fabricated score.
- Between quarter ends, preserve membership except for forced removal due to actual delisting or lost/expired coverage. If a forced removal leaves fewer than three, restore three at the next modeled monthly rebalance using the same disclosed floor rule. This maintenance exception may occur outside quarter ends. Normal entries still wait for quarter ends.
- Stop with an explicit infeasibility error if three permissible, observed stocks cannot be held. Do not substitute cash, fabricated observations or missing-data defaults while claiming compliance.
- Initial deployment waits for a quarter end with at least four covered stocks, as before. Monthly valuation, equal-weight rebalancing with the original 1.5-percentage-point top-quartile tilt, information lags, costs and FX rules remain unchanged.
- A median-entry (Q50) sensitivity uses the same 3-7 bounds, Q25 exits and one-quarter timing. Q75 is designated the primary rule before returns are viewed; it will not be selected or replaced using its realized performance.

## Why a minimum-holdings exception is necessary

Coverage inspection, without calculating new strategy returns, found only four covered European companies in the early sample. A pure Q75 screen admits one company there. A strict Q75 gate and three-stock minimum cannot both hold at those dates. The floor explicitly admits the next strongest companies above Q25. Across all inherited monthly cohorts, at least three companies have scores above Q25, so this rule is feasible for the captured sample.

## What the bound means in this backtest

The number of stock positions, excluding cash, must be 3-7 after every modeled rebalance and at every exported monthly/recent-daily valuation. Holdings do not change between modeled trades. The known EDF delisting is additionally checked against the previous month's positions to test whether its removal could cause an intramonth breach. The source archive is not a full historical daily corporate-action or execution tape, so the study does not certify every unobserved intraday state or claim live automation.

## Comparisons and labels

- `q75`: top-quartile normal entry/reentry, primary constrained rule.
- `q50`: median normal entry/reentry, constrained sensitivity.
- `equal`: unchanged, unconstrained equal-weight control of the covered stock universe. The 3-7 requirement applies to the proposed ETF strategies, not this comparator.
- Every non-entry assumption and all 31 inherited case configurations are retained, yielding 62 constrained runs and 31 equal-weight controls.
- The previous quarter-end one-quarter Q25/Q50 strategies are preserved under `baseline/`. Same-window comparisons show the effect of the whole new selection policy, including entry thresholds, floor and cap; they do not isolate the cap alone.
- New Q50/Q75 labels refer to both normal first admission and reentry. They are not the old Q25/Q50 reentry-only definitions.

All inputs remain sourced observations. Revised vendor histories and the retrospective universe still prevent certification as point-in-time or full-factor performance. Missing paper factors are not reconstructed or imputed. See baseline/previous_method.md and the source evidence for inherited conventions.
