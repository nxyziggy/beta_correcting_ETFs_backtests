# Review response and scope of the revised experiments

## Follow-up review of the scoring experiments

The follow-up review found no new implementation defect and confirmed the
earlier repairs. Its concentration criticism is valid: calling the trend score
the "clearest compromise" overstated the evidence. That wording is removed.

Reproducible omissions now remove each of the 31 companies before reranking
baseline, trend, momentum and the two existing confirmation combinations.
These 330 diagnostic runs include 20 full-pool reproductions and 310 reduced-pool
runs. Main portfolios and controls retain every eligible company.

| US gain over the matching baseline | Full pool Q50 / Q75 | Without Bloom Q50 / Q75 |
|---|---:|---:|
| Fundamental improvement | +511.91pp / +205.69pp | −15.91pp / +19.60pp |
| Price momentum | +405.81pp / +586.00pp | +177.01pp / +252.86pp |
| Fundamental improvement + confirmation | +645.07pp / +187.29pp | +73.78pp / +81.46pp |
| Price momentum + confirmation | +571.03pp / +492.20pp | +205.56pp / +269.49pp |

Omissions change ranks and positions throughout the portfolio. The difference
is not an additive Bloom contribution or a reason to remove Bloom. Momentum
survives every US omission, but underperforms baseline in 14/15 EU Q50 omissions
and all 15 EU Q75 omissions. Relative-wealth milestones confirm substantial
momentum advantages already by December 2020. Relative wealth percentages are
kept separate from cumulative-return differences in percentage points.

The main report now shows all monthly IID/Newey–West t-statistics and discloses
32 specified alternative-versus-baseline comparisons in the main case. The
largest US t against equal weight is 1.17; baseline t-statistics above two do
not resolve multiple testing or the already-observed evaluation period.

Eight specified alternatives produce seven distinct alternative portfolio
paths: recovery grace never activates. The former "independent audit" is now
labeled ledger replay; it imports production input classes. The legacy filename
is retained for compatibility. The README shows both direct-screen and ungated
results and explicitly states that direct admission excludes TSMC until
December 2024. Narrative numbers in attribution and experiment reports now
come from their generated tables instead of literal performance claims.

CI now includes Python 3.13 and recomputes all 152 experiment portfolios,
comparing all six ledgers and engine summary fields numerically with saved
results. Dates and discrete choices must match; only numeric roundoff is
allowed (relative tolerance 1e-12, absolute 1e-10). Frozen CSVs keep their bytes.
The earlier [d0cd812 PR CI run](https://github.com/nxyziggy/beta_correcting_ETFs_backtests/actions/runs/43690935192)
is confirmed successful through the GitHub API. Merge/base changes and history
rewrites remain separate decisions; neither PR is merged or retargeted here.

Two remaining review details also check out. From 2022, report-age medians are
92 days when restricted to quarter-end reviews in each region (295 US and
271 EU scored observations), versus 120–123 days across all months. Both
measurements are valid and use different samples. Only 10 of 31 first admissions
have a company-level award amount; a comprehensive materiality test still needs
more evidence. FX acquisition provenance and duplicated historical folders
remain documented limitations, not newly resolved items.

[Concentration, timing and uncertainty diagnostics](results_recovery_experiments/CONCENTRATION.md)
include every omitted company and both regions. These additions diagnose the
existing specifications; no new scoring parameter or selected winner is introduced.

## Earlier review

The external review examined the earlier longer-history and public-support
commits. Its central distinction is valid: the broad historical support
screen is not a replication of the article's specified Pillar 2 programme
streams, sector baskets or entry examples. The longer accounting histories
and the new scoring experiments remain separate research exercises.

## Corrections incorporated

- Rename the human-facing historical gate to **any prior public support
  screen**. Keep `pillar2` filenames and APIs for compatibility. Put its binding
  rate in the report and README: direct support excludes 79/2,614 listed
  company-months (3.02%); indirect-inclusive support excludes 2 (0.08%). Low
  exclusion frequency does not imply a small portfolio effect: TSMC and Alfen
  admission choices materially change the results.
- Add award-amount evidence to every event, preserving unknown company amounts
  as null and keeping consortium/project totals separate. Amounts do not
  change eligibility or scores. The USD48,816 Lam training contract and
  conditional USD5,124,000 TI commitment illustrate how broad the rule is.
  EnLight's EUR41.3m project cost is not an award to each participating company.
- Repair historical runners' code-hash checks while retaining exact checks
  for captured data and results and numerical baseline reproduction. Separate
  versioned implementation provenance from immutable research artifacts. Fix
  the correction runner's upstream scope so later studies do not change its
  preserved-file count.
- Refresh dependent manifests in upstream-to-downstream order. Keep the
  previously published portfolio calculations separate from metadata and
  explanatory changes.
- Make the US financial collector replay committed accession-level evidence
  by default. Full SEC-snapshot re-extraction is an explicit optional mode;
  the clone no longer needs private sibling folders for normalization.
- Remove task-management instructions from method documents and disclose that
  methods and outputs were committed together. No independent preregistration
  or untouched evaluation period is claimed.
- Put the current full-pool comparison above the clearly marked original
  limited-coverage snapshot in the README. Add automated tests and an audit of
  the committed scoring-experiment ledgers.

The PR description had already been updated after the reviewed policy commit;
it is updated again for the complete current scope. The PR remains stacked on
the unmerged correction PR. Neither PR is merged or automatically retargeted.

## Findings that need qualification

The sparse original policy ledger first supplies enough names for a quarterly
review in March 2025 for the US (five names) and December 2023 for Europe
(four, not five). Europe's first five-name review is December 2024. That ledger
also includes preliminary/pending national-grant statuses: its date diagnostic
does not constitute a newly verified reconstruction of the article's confirmed
programme streams. See the [exact eligibility audit](results_pillar2/original_ledger_start_audit.json).

Alfen's 2018 prospectus discloses government-grant income for an overseas
solar/storage project without naming the grantor or programme. Its connection
to the later named Dutch ISES award is plausible but unresolved. The direct
boundary remains a conservative evidence choice, not proof that earlier support
did not exist. The [support report](results_pillar2/REPORT.md) exposes that choice
and the indirect-inclusive sensitivity.

The 2020 US gap and the large EU sensitivity to financial-report timing are
confirmed from the stored ledgers. Early report age is about nine months;
from 2022 onward the score-weighted median is about four months when measured
from accounting period end to portfolio date. A continuous portfolio's return
after December 2020 differs from a portfolio freshly initialized on that date.
See [the evidence audit](results_long_history/REVIEW_DIAGNOSTICS.md) for definitions
and the independently recalculated comparisons.

Fresh portfolio reruns confirm all 14 quarterly-start comparisons: both US
strategies trail and both EU strategies lead their matched control. Across
whole-universe single-company omissions, both EU leads survive every omission;
US Q50 always trails, while US Q75 leads only when GE Vernova is omitted.
These are sensitivities on the ungated long-history panel, not independent
samples or reasons to delete those companies from the main results.

## Remaining limits

The historical candidate list is retrospective. A gate that accepts any small
earlier public award does not validate the article's more specific industrial
policy thesis or establish material continuing earnings support. Many individual
award amounts remain unknown; a materiality filter would require a separately
specified sensitivity and better amount coverage.

The FX supplement is reproducible from its saved values, and its overlapping
observations match the earlier dataset. Its original successful acquisition
record and response capture are missing; the four failed requests are not proof
of acquisition. The complete original SEC companyfacts response bodies are also
absent, although the normalized source evidence needed for offline replay is
included. These limits are documented rather than filled with invented provenance.

Byte hashes identify a particular snapshot. Other Python/platform combinations
can alter the final floating-point digits of ledger text. This update does not
rewrite every historical ledger with a new rounding convention or deduplicate
the historical output folders. Earlier financial-release dates still require
source-by-source verification; common-delay panels are sensitivities, not a
certification that every earliest release has been recovered.

The new [scoring and exit experiments](results_recovery_experiments/REPORT.md)
test a fixed set of eight alternatives in both regions. Their improvements and
drawbacks are reported on already-seen history; none is automatically promoted
to the default strategy.
