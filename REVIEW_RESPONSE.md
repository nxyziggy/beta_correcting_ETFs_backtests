# Review response and scope of the revised experiments

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
