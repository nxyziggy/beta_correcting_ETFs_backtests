"""Regression tests for extended calendars, full coverage and delay/freshness separation."""
import unittest
from backtest import run
from run_long_history import (HistoryInputs, TimingInputs, build_lam, coverage_audit,
                              earliest_complete, is_listed)


class LongHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lam,cls.registry=build_lam()

    def test_default_freshness_stays_unchanged(self):
        inp=TimingInputs('US','interim','common',self.lam,self.registry)
        self.assertEqual(inp.freshness_days({'period_type':'annual'}),550)
        self.assertEqual(inp.freshness_days({'period_type':'trailing'}),275)
        inp.extend_freshness=True
        self.assertEqual(inp.freshness_days({'period_type':'annual'}),730)
        self.assertEqual(inp.freshness_days({'period_type':'trailing'}),365)

    def test_artificial_expiry_gaps_removed(self):
        inp=TimingInputs('US','interim','common',self.lam,self.registry)
        for ticker,date in [('LRCX','2022-12-31'),('LRCX','2023-12-31'),('INTC','2023-06-30')]:
            inp.extend_freshness=False
            old,_=inp.signals('US',date,'hybrid')
            inp.extend_freshness=True
            new,_=inp.signals('US',date,'hybrid')
            self.assertNotIn(ticker,old)
            self.assertIn(ticker,new)
        # Microchip's initial missing filing cannot be solved by extending an absent record.
        scores,_=inp.signals('US','2022-09-30','hybrid')
        self.assertNotIn('MCHP',scores)

    def test_new_annual_reports_fill_veolia_gap(self):
        inp=HistoryInputs('EU','source',self.lam,self.registry)
        for date in ('2021-09-30','2021-12-31','2022-03-31'):
            scores,_=inp.signals('EU',date,'hybrid')
            self.assertIn('VIE.PA',scores)
            self.assertEqual(scores['VIE.PA']['period_end'],'2020-12-31')

    def test_listing_respects_information_cutoff(self):
        inp=HistoryInputs('EU','source',self.lam,self.registry)
        self.assertFalse(is_listed(inp,'ENR.DE','2020-09-30'))
        self.assertTrue(is_listed(inp,'ENR.DE','2020-10-31'))
        scores,_=inp.signals('EU','2020-10-31','hybrid')
        self.assertIn('ENR.DE',scores)
        self.assertGreaterEqual(scores['ENR.DE']['availability_date'],'2020-09-07')

    def test_earliest_start_requires_complete_future_months(self):
        rows=[dict(date=d,listed_at_cutoff=True,complete=ok) for d,ok in
              [('2019-03-31',True),('2019-04-30',False),('2019-05-31',True),('2019-06-30',True)]]
        self.assertEqual(earliest_complete(rows*4),'2019-06-30')

    def test_explicit_pre2020_start_is_honored(self):
        inp=HistoryInputs('US','source',self.lam,self.registry)
        start=earliest_complete(coverage_audit(inp,'US'))
        self.assertLess(start,'2020-01-01')
        r=run(inp,'US','long_test','equal',10,annual_lag=0,start=start)
        self.assertEqual(r['summary']['start'],start)
        self.assertTrue(all(x['covered'] for x in r['coverage'] if is_listed(inp,x['ticker'],x['date'])))


if __name__=='__main__':unittest.main()
