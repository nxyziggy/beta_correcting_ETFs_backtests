"""Guard against cached ranks and misleading return units in omission checks."""
import unittest

from analyze_recovery_robustness import without_company, wealth_comparison
from backtest import ranks
from check_research_reproduction import compare_rows
from recovery_rules import RecoveryInputs
from run_pillar2 import read_research, build_lam


class RobustnessTests(unittest.TestCase):
    def test_omission_invalidates_warm_feature_cache_and_reranks(self):
        events, _ = read_research(); lam, registry = build_lam()
        original = RecoveryInputs('US', 'source', 'direct', events, lam, registry, 'trend')
        before, _ = original.signals('US', '2024-06-30', 'hybrid')
        self.assertIn('BE', before)
        reduced = without_company(original, 'BE')
        self.assertFalse(reduced.feature_cache)
        after, _ = reduced.signals('US', '2024-06-30', 'hybrid')
        self.assertEqual(set(after), set(before) - {'BE'})
        expected = ranks({t: r['roce'] for t, r in after.items()})
        self.assertEqual({t: r['rank_roce'] for t, r in after.items()}, expected)
        trend = ranks({t: r['delta_roce'] for t, r in after.items() if r['trend_available']})
        quality = ranks({t: r['delta_cash_quality'] for t, r in after.items() if r['trend_available']})
        for ticker in trend:
            self.assertAlmostEqual(after[ticker]['trend_rank'], (trend[ticker] + quality[ticker]) / 2)
        self.assertTrue(any(before[t]['base_score'] != after[t]['base_score'] for t in after))
        again, _ = original.signals('US', '2024-06-30', 'hybrid')
        self.assertEqual(before, again)

    def test_relative_wealth_is_not_return_point_difference(self):
        values = wealth_comparison(300, 200)
        self.assertEqual(values['relative_wealth_pct'], 50)
        self.assertEqual(values['cumulative_return_gap_pp'], 100)

    def test_reproduction_accepts_roundoff_but_rejects_material_change(self):
        expected = [{'date': '2024-06-30', 'NAV': '100.00000000000001'}]
        self.assertEqual(compare_rows(expected, [{'date': '2024-06-30', 'NAV': 100}], 'roundoff'), 1)
        with self.assertRaises(AssertionError):
            compare_rows(expected, [{'date': '2024-06-30', 'NAV': 100.001}], 'changed')

    def test_reproduction_requires_dates_membership_and_row_counts(self):
        original = [{'date': '2024-06-30', 'ticker': 'BE', 'weight': .2}]
        for changed in ([{'date': '2024-07-31', 'ticker': 'BE', 'weight': .2}],
                        [{'date': '2024-06-30', 'ticker': 'INTC', 'weight': .2}], []):
            with self.assertRaises(AssertionError):
                compare_rows(original, changed, 'discrete change')


if __name__ == '__main__':
    unittest.main()
