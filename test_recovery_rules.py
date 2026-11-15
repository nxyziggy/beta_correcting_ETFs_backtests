"""Information-isolation and feature-fallback tests for the predefined score changes."""
import unittest
from recovery_rules import RecoveryInputs,shifted_month_end
from run_pillar2 import read_research,build_lam,active_events


class RecoverySignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events,_=read_research();cls.lam,cls.registry=build_lam()

    def inputs(self,region='US',score='base',timing='source'):
        return RecoveryInputs(region,timing,'direct',self.events,self.lam,self.registry,score)

    def test_month_end_and_momentum_endpoints(self):
        self.assertEqual(shifted_month_end('2020-03-31',-1),'2020-02-29')
        sc,_=self.inputs().signals('US','2019-06-30','hybrid')
        self.assertEqual(sc['INTC']['momentum_start'],'2018-05-31')
        self.assertEqual(sc['INTC']['momentum_end'],'2019-04-30')

    def test_missing_history_falls_back_without_changing_coverage(self):
        inp=self.inputs(score='trend');trend,_=inp.signals('US','2019-06-30','hybrid')
        inp.score_mode='base';base,_=inp.signals('US','2019-06-30','hybrid')
        self.assertEqual(set(base),set(trend))
        for ticker in ('LIN','BE'):
            self.assertTrue(trend[ticker]['feature_fallback'])
            self.assertEqual(trend[ticker]['score'],base[ticker]['score'])
            self.assertFalse(trend[ticker]['improving_both'])

    def test_predecessor_prices_cannot_supply_ipo_lookback(self):
        inp=self.inputs(score='momentum');sc,_=inp.signals('US','2019-06-30','hybrid')
        self.assertIn('2018-05-31',inp.prices['LIN'])
        self.assertFalse(sc['LIN']['momentum_available'])
        self.assertTrue(sc['LIN']['feature_fallback'])

    def test_policy_newcomer_can_use_older_public_accounts(self):
        inp=self.inputs(score='trend');sc,_=inp.signals('US','2024-12-31','hybrid')
        self.assertFalse(active_events(self.events,'TSM','2023-12-31','direct'))
        self.assertTrue(sc['TSM']['trend_available'])
        self.assertLess(sc['TSM']['prior_available_used'],'2023-12-01')

    def test_future_accounts_and_skipped_month_cannot_change_signal(self):
        inp=self.inputs(score='momentum');before,_=inp.signals('US','2022-06-30','hybrid')
        for r in inp.annual+inp.quarterly:
            if r['availability_date']>='2022-06-01':r['operating_income']=float(r['operating_income'])*1000
        inp.prices['INTC']['2022-05-31']*=100
        inp.prices['INTC']['2022-06-30']*=100
        inp.feature_cache.clear();after,_=inp.signals('US','2022-06-30','hybrid')
        self.assertEqual(before,after)
        # Positive control ensures this is not simply a cache test.
        inp.prices['INTC']['2022-04-30']*=2
        inp.feature_cache.clear();changed,_=inp.signals('US','2022-06-30','hybrid')
        self.assertNotEqual(before['INTC']['momentum_return'],changed['INTC']['momentum_return'])

    def test_european_momentum_uses_eur(self):
        inp=self.inputs('EU','momentum');sc,_=inp.signals('EU','2022-06-30','hybrid')
        r=sc['NXPI'];a,b=r['momentum_start'],r['momentum_end']
        expected=inp.price('NXPI',b,'EU')/inp.price('NXPI',a,'EU')-1
        self.assertAlmostEqual(r['momentum_return'],expected)
        usd=inp.prices['NXPI'][b]/inp.prices['NXPI'][a]-1
        self.assertNotAlmostEqual(expected,usd)

    def test_factor_modes_do_not_mutate_cached_base(self):
        inp=self.inputs();a,_=inp.signals('US','2023-06-30','hybrid')
        inp.score_mode='trend';inp.signals('US','2023-06-30','hybrid')
        inp.score_mode='base';b,_=inp.signals('US','2023-06-30','hybrid')
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
