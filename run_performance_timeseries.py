#!/usr/bin/env python3
"""Index-level time series for every main-case scoring portfolio and both comparisons.

Each portfolio becomes an index whose level is 100 at its window's start date, before the
first trade, and then follows the back-tested portfolio value after modeled trading costs,
in the convention of an index fact sheet's historical-performance chart. Levels are taken
at month ends plus the final 2 November 2026 close. The equal-weight control and the ETF
benchmark sit on the same base and dates.

Two windows per region: the long window from 30 June 2019, and the article's own window
(30 September 2022 in the US, 30 September 2021 in Europe), which restarts the same rules
on that date rather than continuing the long-window positions.

Configuration is the main case of results_recovery_experiments: direct public-support
screen, source timing, single-review exits, 10bp (US) / 15bp (Europe) costs.

Run from the repository root:
    python3 run_performance_timeseries.py
Writes results_performance_timeseries/performance_timeseries.csv and input_manifest.json.
Every long-window month-end level must reproduce the committed main-case ledgers exactly.
"""
import csv
import hashlib
import json
import math

from backtest import run
from prepare_data import ROOT
from recovery_rules import RecoveryInputs, RecoveryExitPolicy
from run_pillar2 import read_research, build_lam

OUT = ROOT / 'results_performance_timeseries'
COST = {'US': 10.0, 'EU': 15.0}
STARTS = {'US': (('long', '2019-06-30'), ('article', '2022-09-30')),
          'EU': (('long', '2019-06-30'), ('article', '2021-09-30'))}
MODES = [('equal', 'base', 'equal'), ('baseline', 'base', 'q50'), ('baseline', 'base', 'q75'),
         ('trend', 'trend', 'q50'), ('trend', 'trend', 'q75'),
         ('momentum', 'momentum', 'q50'), ('momentum', 'momentum', 'q75')]
FOLDER = 'results_recovery_experiments/{region}_recovery_direct_main_{variant}_policy_{rule}_{cost}bp_lag0_from2019-06-30'
CODE = ('backtest.py', 'prepare_data.py', 'recovery_rules.py', 'run_pillar2.py', 'run_performance_timeseries.py',
        'run_article_windows.py', 'test_performance_timeseries.py')


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-10)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def main():
    events, _ = read_research()
    lam, registry = build_lam()
    committed = {(r['region'], r['variant'], r['rule']): r
                 for r in read_rows(ROOT / 'results_recovery_experiments/summary.csv') if r['case'] == 'direct_main'}
    rows, references, checked = [], ['results_recovery_experiments/summary.csv'], 0
    for region in ('US', 'EU'):
        for window, start in STARTS[region]:
            bench = None
            for variant, score_mode, rule in MODES:
                inputs = RecoveryInputs(region, 'source', 'direct', events, lam, registry, score_mode)
                policy = None if rule == 'equal' else RecoveryExitPolicy('single')
                result = run(inputs, region, f'recovery_direct_main_{variant}', rule, COST[region], gate=True,
                             annual_lag=0, start=start, selection_policy=policy)
                monthly, last = result['monthly'], result['recent_daily'][-1]
                assert monthly[0]['date'] == start and float(monthly[0]['PreTradeNAV']) == 100.0
                assert last['date'] == result['summary']['latest_end'] == '2026-11-02' > monthly[-1]['date']
                assert close(last['NAV'], 100 * (1 + float(result['summary']['total_return'])))
                points = [(m['date'], float(m['NAV']), float(m['BenchmarkNAV'])) for m in monthly]
                points.append((last['date'], float(last['NAV']), float(last['BenchmarkNAV'])))
                if window == 'long':  # the committed ledgers must be reproduced month by month
                    folder = FOLDER.format(region=region, variant=variant, rule=rule, cost=int(COST[region]))
                    ref = read_rows(ROOT / folder / 'monthly.csv')
                    assert len(ref) == len(monthly)
                    for a, b in zip(ref, monthly):
                        assert a['date'] == b['date'] and close(a['NAV'], b['NAV']) and close(a['BenchmarkNAV'], b['BenchmarkNAV'])
                    assert close(committed[region, variant, rule]['total_return'], result['summary']['total_return'])
                    references += [f'{folder}/monthly.csv', f'{folder}/recent_daily.csv']
                    checked += len(ref)
                series = [(f'{variant}_{rule}' if rule != 'equal' else 'equal_weight', [(d, v) for d, v, _ in points])]
                b = [(d, v) for d, _, v in points]
                if bench is None:
                    bench = b
                    series.append(('etf_benchmark', b))
                else:  # one benchmark path per region and window
                    assert all(x[0] == y[0] and close(x[1], y[1]) for x, y in zip(bench, b))
                for name, pts in series:
                    rows += [dict(region=region, window=window, window_start=start, series=name, date=d,
                                  index_level=repr(v)) for d, v in pts]
                print(f'{region} {window:7} {variant:8} {rule:5} {points[0][0]} -> {points[-1][0]}  '
                      f'{len(points)} points, final level {points[-1][1]:8.2f}', flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'performance_timeseries.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    inputs = sorted(set(CODE) | set(references))
    (OUT / 'input_manifest.json').write_text(
        json.dumps([dict(path=p, sha256=digest(ROOT / p)) for p in inputs], indent=1) + '\n')
    print(f'PASS: {checked} committed month-end values reproduced; {len(rows)} index levels written.')


if __name__ == '__main__':
    main()
