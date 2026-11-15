#!/usr/bin/env python3
"""Rerun every scoring portfolio and compare its saved ledgers numerically.

Identity, dates, row order and discrete choices must match exactly. Numeric
cells permit only rounding differences (rtol 1e-12, atol 1e-10), so different
Python float representations do not require rewriting frozen CSV snapshots.
Nothing is written by this check.
"""
import math

from backtest import read_csv, run
from prepare_data import ROOT
from recovery_rules import RecoveryInputs, RecoveryExitPolicy
from run_pillar2 import read_research, build_lam

OUT = ROOT / 'results_recovery_experiments'
REL_TOL = 1e-12
ABS_TOL = 1e-10


def compare_rows(expected, actual, label):
    if len(expected) != len(actual):
        raise AssertionError((label, 'row count', len(expected), len(actual)))
    numeric_differences = 0
    for index, (left, right) in enumerate(zip(expected, actual)):
        for key in set(left) | set(right):
            a, b = left.get(key, ''), right.get(key, '')
            a, b = '' if a is None else str(a), '' if b is None else str(b)
            if a == b:
                continue
            try:
                x, y = float(a), float(b)
            except ValueError:
                raise AssertionError((label, index, key, a, b)) from None
            if not (math.isfinite(x) and math.isfinite(y) and
                    math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL)):
                raise AssertionError((label, index, key, a, b))
            numeric_differences += 1
    return numeric_differences


def main():
    events, _ = read_research()
    lam, registry = build_lam()
    summaries = read_csv(OUT / 'summary.csv')
    inputs = {}
    comparisons = differences = 0
    for reference in summaries:
        key = reference['case'], reference['region']
        if key not in inputs:
            inputs[key] = RecoveryInputs(reference['region'], reference['timing'], reference['definition'],
                                         events, lam, registry)
        inp = inputs[key]
        inp.score_mode = reference['score_mode']
        rule = reference['rule']
        policy = None if rule == 'equal' else RecoveryExitPolicy(reference['exit_mode'])
        result = run(inp, reference['region'], reference['panel'], rule, float(reference['cost_bps']),
                     gate=True, annual_lag=0, start=reference['start'], selection_policy=policy)
        assert result is not None
        for name in ('monthly', 'holdings', 'trades', 'events', 'selection_audit', 'recent_daily'):
            old = read_csv(OUT / reference['run'] / (name + '.csv'))
            differences += compare_rows(old, result[name], reference['run'] + '/' + name)
            comparisons += 1
        # Compare all fields produced by the engine, not reporting-only additions.
        expected = {k: reference[k] for k in result['summary']}
        differences += compare_rows([expected], [result['summary']], reference['run'] + '/summary')
        if reference['variant'] == 'momentum_confirm' and rule == 'q75':
            print('Reproduced', *key, flush=True)
    print(f'PASS: {len(summaries)} portfolios, {comparisons} ledger comparisons; '
          f'{differences} numeric representation differences within rtol={REL_TOL}, atol={ABS_TOL}.')


if __name__ == '__main__':
    main()
