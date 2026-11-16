"""Checks for results_performance_timeseries: shape, agreement with the committed main-case
ledgers, end points equal to the reported window returns, and a recomputation of two
article-window paths with the engine."""
import csv
import math
import unittest

from prepare_data import ROOT

OUT = ROOT / 'results_performance_timeseries'
COST = {'US': 10, 'EU': 15}
STARTS = {('US', 'long'): '2019-06-30', ('EU', 'long'): '2019-06-30',
          ('US', 'article'): '2022-09-30', ('EU', 'article'): '2021-09-30'}
SERIES = {'equal_weight': ('equal', 'equal'), 'baseline_q50': ('baseline', 'q50'), 'baseline_q75': ('baseline', 'q75'),
          'trend_q50': ('trend', 'q50'), 'trend_q75': ('trend', 'q75'),
          'momentum_q50': ('momentum', 'q50'), 'momentum_q75': ('momentum', 'q75')}
FOLDER = 'results_recovery_experiments/{region}_recovery_direct_main_{variant}_policy_{rule}_{cost}bp_lag0_from2019-06-30'


def read_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def close(a, b, rel=1e-12):
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=1e-10)


class PerformanceTimeseriesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = {}
        for r in read_rows(OUT / 'performance_timeseries.csv'):
            cls.series.setdefault((r['region'], r['window'], r['series']), []).append((r['date'], float(r['index_level'])))
        cls.windows = {(r['region'], r['window'], r['variant'], r['rule']): r
                       for r in read_rows(OUT / 'article_windows.csv')}

    def test_every_series_has_the_window_dates(self):
        self.assertEqual(len(self.series), 32)
        for (region, window), start in STARTS.items():
            panel = {name: pts for (r, w, name), pts in self.series.items() if (r, w) == (region, window)}
            self.assertEqual(sorted(panel), sorted([*SERIES, 'etf_benchmark']))
            dates = [d for d, _ in panel['etf_benchmark']]
            self.assertEqual((dates[0], dates[-1]), (start, '2026-11-02'))
            for pts in panel.values():
                self.assertEqual([d for d, _ in pts], dates)

    def test_long_window_equals_committed_ledgers(self):
        for region in ('US', 'EU'):
            for name, (variant, rule) in SERIES.items():
                folder = ROOT / FOLDER.format(region=region, variant=variant, rule=rule, cost=COST[region])
                ledger = read_rows(folder / 'monthly.csv') + read_rows(folder / 'recent_daily.csv')
                for column, series in (('NAV', name), ('BenchmarkNAV', 'etf_benchmark')):
                    pts = self.series[region, 'long', series]
                    self.assertEqual([r['date'] for r in ledger], [d for d, _ in pts])
                    for r, (_, level) in zip(ledger, pts):
                        self.assertTrue(close(r[column], level), (region, name, column, r['date']))

    def test_end_levels_equal_window_returns(self):
        for (region, window, variant, rule), w in self.windows.items():
            name = 'equal_weight' if variant == 'equal' else f'{variant}_{rule}'
            self.assertEqual(w['start'], STARTS[region, window])
            self.assertTrue(close(self.series[region, window, name][-1][1], 100 * (1 + float(w['total_return']))))
            self.assertTrue(close(self.series[region, window, 'etf_benchmark'][-1][1], 100 * (1 + float(w['benchmark_return']))))

    def test_article_window_paths_recompute(self):
        from backtest import run
        from recovery_rules import RecoveryInputs, RecoveryExitPolicy
        from run_pillar2 import read_research, build_lam
        events, _ = read_research()
        lam, registry = build_lam()
        for region, variant, mode, rule in (('US', 'baseline', 'base', 'q50'), ('EU', 'trend', 'trend', 'q75')):
            inputs = RecoveryInputs(region, 'source', 'direct', events, lam, registry, mode)
            result = run(inputs, region, f'recovery_direct_main_{variant}', rule, float(COST[region]), gate=True,
                         annual_lag=0, start=STARTS[region, 'article'], selection_policy=RecoveryExitPolicy('single'))
            path = [float(m['NAV']) for m in result['monthly']] + [float(result['recent_daily'][-1]['NAV'])]
            saved = [v for _, v in self.series[region, 'article', f'{variant}_{rule}']]
            self.assertEqual(len(path), len(saved))
            for a, b in zip(path, saved):
                self.assertTrue(close(a, b, rel=1e-10), (region, variant, rule))


if __name__ == '__main__':
    unittest.main()
