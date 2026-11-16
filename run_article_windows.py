#!/usr/bin/env python3
"""Rerun the main-case portfolios from the article's own start dates.

The same seven portfolios per region as the main case of results_recovery_experiments
(direct public-support screen, source timing, single-review exits) restart on 30 September
2022 (US) and 30 September 2021 (Europe). The engine is first checked against the
committed 30 June 2019 runs, which it must reproduce exactly.

Run from the repository root:
    python3 run_article_windows.py
Writes results_performance_timeseries/article_windows.csv: total return and CAGR for each
portfolio and window, with the ETF benchmark over the same dates. Nothing else is modified.
"""
import csv
import math

from backtest import run
from prepare_data import ROOT
from recovery_rules import RecoveryInputs, RecoveryExitPolicy
from run_pillar2 import read_research, build_lam

OUT = ROOT / 'results_performance_timeseries'
COST = {'US': 10.0, 'EU': 15.0}
ARTICLE_START = {'US': '2022-09-30', 'EU': '2021-09-30'}
MODES = [('equal', 'base', 'equal'), ('baseline', 'base', 'q50'), ('baseline', 'base', 'q75'),
         ('trend', 'trend', 'q50'), ('trend', 'trend', 'q75'),
         ('momentum', 'momentum', 'q50'), ('momentum', 'momentum', 'q75')]
FIELDS = ['region', 'window', 'variant', 'rule', 'requested_start', 'start', 'latest_end', 'total_return', 'CAGR',
          'benchmark_return', 'benchmark_CAGR', 'max_drawdown_monthly', 'final_holdings', 'exits', 'reentries']


def portfolios(events, lam, registry, region, start):
    for variant, score_mode, rule in MODES:
        inputs = RecoveryInputs(region, 'source', 'direct', events, lam, registry, score_mode)
        policy = None if rule == 'equal' else RecoveryExitPolicy('single')
        result = run(inputs, region, f'recovery_direct_main_{variant}', rule, COST[region], gate=True,
                     annual_lag=0, start=start, selection_policy=policy)
        yield variant, rule, result['summary']


def read_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def main():
    events, _ = read_research()
    lam, registry = build_lam()
    committed = {(r['region'], r['variant'], r['rule']): r
                 for r in read_rows(ROOT / 'results_recovery_experiments/summary.csv') if r['case'] == 'direct_main'}
    rows = []
    for region in ('US', 'EU'):
        for window, start in (('long', '2019-06-30'), ('article', ARTICLE_START[region])):
            for variant, rule, summary in portfolios(events, lam, registry, region, start):
                row = {k: summary.get(k, '') for k in FIELDS}
                row.update(region=region, window=window, variant=variant, rule=rule, requested_start=start)
                if window == 'long':  # the engine must reproduce the committed main case exactly
                    ref = committed[region, variant, rule]
                    for k in ('total_return', 'CAGR', 'benchmark_return', 'benchmark_CAGR'):
                        assert math.isclose(float(summary[k]), float(ref[k]), rel_tol=1e-12, abs_tol=1e-12), (region, variant, rule, k)
                assert summary['start'] == start, (summary['start'], start)
                rows.append(row)
                print(f"{region} {window:7} {variant:8} {rule:5} start {summary['start']}  "
                      f"{100 * float(summary['total_return']):8.2f}%  {100 * float(summary['CAGR']):6.2f}%  "
                      f"benchmark {100 * float(summary['benchmark_return']):7.2f}% {100 * float(summary['benchmark_CAGR']):6.2f}%",
                      flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'article_windows.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print('PASS: the 14 long-window portfolios reproduce the committed main case.')


if __name__ == '__main__':
    main()
