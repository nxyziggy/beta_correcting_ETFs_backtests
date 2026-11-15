"""Regression checks for information cutoffs and missing-data repairs."""
import copy
import math
import unittest

from run_research_corrections import CorrectedInputs, active_stats, build_lam, common_date


class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lam, cls.registry = build_lam()
        cls.original = CorrectedInputs('US', 'reference', 'released', cls.lam, cls.registry)
        cls.repaired = CorrectedInputs('US', 'reference', 'lam', cls.lam, cls.registry)

    def test_lam_gap_closed_without_expired_filing(self):
        for date in ('2025-01-31', '2025-02-28', '2025-03-31', '2025-04-30',
                     '2025-05-31', '2025-06-30', '2025-07-31'):
            before, _ = self.original.signals('US', date, 'hybrid')
            after, _ = self.repaired.signals('US', date, 'hybrid')
            self.assertNotIn('LRCX', before)
            self.assertIn('LRCX', after)
            self.assertGreaterEqual(after['LRCX']['period_end'], '2024-09-29')

    def test_earnings_release_waits_for_information_cutoff(self):
        january, _ = self.repaired.signals('US', '2025-01-31', 'hybrid')
        february, _ = self.repaired.signals('US', '2025-02-28', 'hybrid')
        self.assertEqual(january['LRCX']['period_end'], '2024-09-29')
        self.assertEqual(february['LRCX']['period_end'], '2024-12-29')
        # Independently calculated from the three original GAAP YTD columns, USD million.
        self.assertAlmostEqual(float(february['LRCX']['operating_income']), 4781.753)
        self.assertAlmostEqual(float(february['LRCX']['net_income']), 4293.570)
        self.assertAlmostEqual(float(february['LRCX']['operating_cash_flow']), 4557.679)

    def test_safran_earlier_statement_changes_march_availability(self):
        old = CorrectedInputs('EU', 'annual', 'released', self.lam, self.registry)
        new = CorrectedInputs('EU', 'annual', 'evidenced', self.lam, self.registry)
        a, _ = old.signals('EU', '2022-03-31', 'hybrid')
        b, _ = new.signals('EU', '2022-03-31', 'hybrid')
        self.assertEqual(a['SAF.PA']['period_end'], '2020-12-31')
        self.assertEqual(b['SAF.PA']['period_end'], '2021-12-31')
        self.assertEqual(b['SAF.PA']['available_used'], '2022-02-24')

    def test_common_delay_preserves_later_real_release(self):
        r = dict(period_end='2023-12-31', period_type='annual', availability_date='2024-02-01')
        self.assertEqual(common_date(r), '2024-06-28')
        r['availability_date'] = '2024-08-01'
        self.assertEqual(common_date(r), '2024-08-01')

    def test_common_delay_checks_components(self):
        inp = CorrectedInputs('US', 'interim', 'common', self.lam, self.registry)
        for r in inp.annual + inp.quarterly:
            for cid in r['component_ids'].split('|'):
                self.assertGreaterEqual(r['availability_date'], common_date(inp.registry[cid]))

    def test_active_statistics_exclude_deployment(self):
        # Four complete returns have mean 2%, sample SD sqrt(2/3)%, and IID t=sqrt(24).
        monthly = [dict(date='initial', PeriodReturn=-.001)] + [
            dict(date=str(i), PeriodReturn=x) for i,x in enumerate((.01,.02,.03,.02))]
        strategy = dict(monthly=monthly)
        control = copy.deepcopy(strategy)
        for r in control['monthly'][1:]:
            r['PeriodReturn'] = 0
        result = active_stats(strategy, control)
        self.assertEqual(result['months'], 4)
        self.assertAlmostEqual(result['mean_monthly_active_pp'], 2)
        self.assertAlmostEqual(result['t_iid'], math.sqrt(24))
        # Bartlett lag-3 long-run variance = 0.000025; finite-sample mean variance /3.
        self.assertAlmostEqual(result['t_newey_west_3'], .02/math.sqrt(.000025/3))


if __name__ == '__main__':
    unittest.main()
