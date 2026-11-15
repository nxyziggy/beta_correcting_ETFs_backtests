# Restoring the seven excluded European candidates

This extension was specified before calculating its restored-coverage returns.
The user requested that all excluded European companies be added back and
explicitly permitted archived and secondary sources. That request permits a
separately labelled secondary-data experiment beyond ACTUAL_DATES_METHOD.md's
original-only restriction. It does not change the published original-only run.

## Scope

Recover annual observations for Alfen, Nel, ams OSRAM, Orsted, Vestas, Siemens
Energy and Safran, ideally FY2020–FY2025. Use reported consolidated operating
income, net income, operating cash flow, total assets and current liabilities.
Do not substitute adjusted EBIT, EBITDA, segment earnings or free cash flow.
Record exceptional definitions and discontinued-operation/restatement issues.
All values in a row must use the same currency and scale.

Original statements and dated releases are preferred. Later comparative
statements become usable only at their own publication dates. Do not attach
historical release dates to subsequently revised vendor numbers. Where only
the repository's frozen secondary histories are usable, keep their explicit
180-day assumed availability and classify them as revised-history sensitivity
inputs, not verified historical information. Those histories omit FY2020.

## Experiments

Retain the original eight companies' captured inputs. Add only the seven
excluded candidates. Hold prices, FX, dates, Q75/Q50 admission, Q25 exit,
quarterly membership reviews, monthly allocation, 1–9 bounds and 15bp costs
fixed. Use September 30, 2021 through November 2, 2026. Annual reporting for
the recovered names is sufficient for this first extension; absent interim
periods are neither annualized nor invented.

Run Q75, Q50 and equal weight for each of these predeclared panels:

- Published expanded coverage (replication reference).
- Expanded coverage plus recovered primary rows, without vendor fallback.
- Expanded coverage plus recovered rows and explicitly labelled frozen
  secondary annual rows for fiscal periods not recovered from primary sources.
- Original eight companies using annual data only (frequency reference).
- Restored companies plus original eight, all using annual data only, with
  the same explicitly labelled secondary fallback policy.

Report coverage over time, including gaps and the actual first admission of
each restored name. EDF's actual delisting still applies, so 15 candidates
does not imply 15 eligible securities at every date.

## Preservation and verification

Write inputs under data/eu_restoration and outputs under results_eu_restored.
Do not modify the published results_actual, tables_actual, financials_actual
inputs or backtest engine. Verify published EU reference NAVs, source-date
cutoffs, freshness, source IDs, weights, portfolio accounting, trade costs,
holding bounds and source/input hashes. Primary-data verification and
backtest-accounting verification are separate: numerical consistency alone
does not certify a complete point-in-time historical archive.

Changing the covered pool changes both the control holdings and the relative
score ranks. The extension tests the consequences of restored coverage;
it does not isolate each change in reporting frequency or accounting practice.
