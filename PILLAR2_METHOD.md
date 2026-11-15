# Any prior public support screen

This broad historical extension of the accounting-score experiment uses all
16 US and 15 EU research candidates. It reconstructs dated support relationships
within that retrospective list, not every historical listed recipient.
The rules were developed after earlier ungated returns had been observed.
Methods and results were committed together; no independent preregistration
or untouched holdout is claimed. Existing `pillar2` filenames and API fields
are retained for compatibility, not as a claim of full Pillar 2 replication.

The [article](https://mitleadtrades.substack.com/p/performative-beta-trap-correcting)
discusses confirmed subsidies broadly, but its operational examples name
CHIPS/IRA and EU Chips/IPCEI/France 2030/Green Deal streams and place Infineon
and NXP admission in June 2023. This extension also accepts much earlier
programmes and admits both companies from a 2014 research project. It does
not replicate the article's specified streams, baskets or event dates.
Only 2 of the ledger's 31 earliest direct admissions use those modern streams:
TSMC's CHIPS award and GE Vernova's IRA credits. This is a classification of
the first captured event, not a claim about every later award to a company.

## How much the screen binds

In the common June 2019–October 2026 monthly window, direct admission excludes
79 of 2,614 listed company-months (3.02%); including indirect exposure excludes
2 (0.08%). The denominator counts each listed candidate once per complete
month, before scoring, without duplicating timing treatments or portfolio
rules. The terminal November 2 partial return is not another company-month.
Exclusion means no qualifying event known before the first of that month;
score rejection and missing financial inputs are separate conditions.

| Definition | Region | Listed company-months | Excluded | Excluded companies |
|---|---|---:|---:|---|
| Direct/subsidiary | US | 1,336 | 68 | TSMC 66; Micron 2 |
| Direct/subsidiary | EU | 1,278 | 11 | Alfen 11 |
| Including indirect | US | 1,336 | 2 | Micron 2 |
| Including indirect | EU | 1,278 | 0 | None |

The runner exports `binding_rates.csv` and every excluded observation in
`binding_exclusions.csv`. TSMC's direct exclusions run June 2019–November
2024; Alfen's run June 2019–April 2020. Micron is excluded in June and July
2019, becomes eligible in August, and still waits for the September quarterly
purchase review. This screen separates few observations within the chosen
pool and does not establish discrimination across the wider stock market.

## What qualifies

The main gate requires a named company, controlled subsidiary or attributable
business to have a confirmed public award, approved industrial aid decision,
targeted manufacturing/energy tax credit, subsidized guarantee, or funded
industrial R&D project. Federal, state/local, EU and national programmes are
eligible on the same basis. Earlier programmes count; CHIPS, IRA and the EU
Chips Act are not retroactively imposed on the earlier period.

US candidates require US public support; European candidates require EU/EEA
support (including historical UK support when the UK was a member). The region
refers to the funding authority, not the exchange or ADR location. Record the
supported project's location separately; an EU authority's grant to an EU
company for an overseas demonstration can qualify.
Record the recipient legal entity and any ownership/transfer restriction.
Ordinary procurement, a commercial loan, generic corporate tax deductions,
sector relevance, applications, proposed awards and future potential credits
are not sufficient. A programme's enactment alone does not establish a
particular company's participation. Named industrial R&D grants count, but
generic eligibility for corporate R&D tax deductions does not.

A named award announced by the responsible authority can qualify before cash
is paid, including ordinary delivery, employment or investment conditions.
A mere selection for negotiations, an unapproved legislative appropriation,
or regulatory permission without an award/commitment does not. Dedicated
public roads and university facilities are indirect benefits unless evidence
establishes a direct grant or company-owned supported asset. There is no
minimum award-size threshold: a small targeted research/training grant can
establish the relationship, but does not establish material earnings support.

The main `direct` panel admits confirmed direct/subsidiary recipients. A separate
`with_indirect` sensitivity also admits explicitly evidenced supplier/customer
relationships to supported projects or targeted customer credits. It must
have a dated company-specific link; generic supply-chain exposure is excluded.
This distinction avoids treating indirect beneficiaries as grant recipients.

## Amount evidence

Every event has `award_amount`, `award_currency`, `award_amount_status` and an
explanation. A numeric company amount retains its stated basis: approved
contract, conditional commitment, ceiling, lower bound or recognized tax
credit. Unknown amounts are null, never zero. `project_total_amount`, currency
and basis retain consortium/project figures separately, including the
distinction between total project cost and public funding. These fields do
not enter eligibility, scores or weights; no materiality filter is introduced.
The event ledger and generated `award_amounts.csv` retain source URLs.

Lam's qualifying training contract is USD48,816. TI's TEF commitment is
USD5,124,000, conditional on investment and staffing. EnLight's EUR41.3m is
total project cost across 27 partners, partly publicly funded, not an award
to either Infineon or NXP. Neither individual company amount is established.
Duplicate consortium totals must not be added across participating companies.

Alfen's 2018 prospectus reports EUR968,000 in 2017 government-grant income
for an African solar/storage system without naming the grantor or programme.
The later Dutch DEI ISES record names Alfen and a EUR2,776,119 project grant;
the final-report publication is dated April 13, 2020. The project descriptions
plausibly match, but earlier public identification of the Dutch grantor and
programme remains unresolved. The existing direct boundary is retained, with
the separately documented SDE+ customer link admitted in the indirect panel.
This is an evidence/classification choice, not proof that Alfen had no earlier
support. The final report also says lower project costs reduced the subsidy;
the registry amount is not treated as final cash received or retained earnings.

## Dates and persistence

An event becomes usable only after the latest of the formal event, its captured
public disclosure, and any necessary ownership/transfer date. A later report
describing an older grant is not backdated. Undated current database entries
do not establish historical public availability. Store source URLs, document
dates, factual paraphrases and search/coverage notes for every candidate.

The screen implements **historical confirmed-recipient admission** under the
broad extension defined here. A completed project does not erase past receipt.
This is not a balance of continuing subsidy entitlement, a
claim that money remains available, or a test of subsidy utilization. Preserve
known project end dates separately. When a qualifying commitment is withdrawn
or the relationship ends, apply an evidenced eligibility end no earlier than
its public disclosure; other valid events can still qualify that company.
Do not infer an unreported revocation or a current subsidy balance.
If a relevant business is publicly separated but the individual old award's
transfer cannot be established, stop attributing that event after the known
separation and label this a conservative ownership boundary, not a proven
revocation. Other independently evidenced retained-business events remain valid.

Both financial and policy information must precede the first day of the review
month. Retain quarterly admissions, monthly weighting/eligibility removals,
the Q50/Q75 accounting ranks, Q25 score exit, existing holdings constraints,
10/15bp costs and the 2 November 2026 endpoint. Rank only companies passing
the policy gate. Retain actual listing/spin-off dates and EDF's delisting.

## Starts and comparisons

Choose the earliest quarter-end with at least four scored policy-eligible
companies and complete prices, FX and financial observations for every
then-listed policy-eligible candidate throughout the remaining window.
Policy exclusion and missing captured financial data are separate reasons.
Audit every month back to available benchmark history, list all missing
company-months, and show the exact preceding-quarter blockers. The start is
the intersection of policy evidence and financial/market coverage; it is not
necessarily a programme's enactment date. Do not select it using returns.

For each eligibility definition, show each region's earliest complete start,
a common cross-region start, and a matched financial-timing sensitivity.
Policy dates are never shifted by the financial-delay experiment. Preserve
the repaired financial freshness limits (source 550/275 days; artificial
180/90-day delay with 730/365-day freshness). At the matched timing start,
require the policy-eligible coverage set and equal-weight monthly NAVs to be
identical. Compare each strategy to its same-date, same-policy equal-weight
control. Keep the earlier ungated experiment separately labeled.

Validate source/ownership cutoffs, policy expiry, reranking after exclusion,
listing restrictions, all coverage gaps, costs/holdings/NAV accounting and
unchanged ungated results. Publish the source ledger, all-candidate audit,
monthly eligibility, event links for every holding, results and uncertainty.
Incomplete archival evidence is a limitation, not proof that support did not
exist. No missing participation is filled with an assumed positive status.
