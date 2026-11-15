"""Independent state-transition checks for the experimental exit rules."""
import unittest

from backtest import constrained_selection
from recovery_rules import RecoveryExitPolicy


def scores(a=.1, improving=False):
    return {t:dict(score=v,improving_both=improving if t=='A' else False)
            for t,v in {'A':a,'B':.4,'C':.7,'D':.9}.items()}


def choose(policy,sc,active,date,quarter=True,rule='q75',maximum=9):
    return policy.select(sc,set(active),rule,quarter,1,maximum,date)


class RecoveryExitStateTests(unittest.TestCase):
    def test_confirmation_counts_reviews_not_intervening_months(self):
        p=RecoveryExitPolicy('confirm')
        active=choose(p,scores(),{'A'},'2020-06-30')[0]
        self.assertIn('A',active);self.assertEqual(p.streaks['A'],1)
        for date in ('2020-07-31','2020-08-31'):
            active=choose(p,scores(),active,date,quarter=False)[0]
            self.assertIn('A',active);self.assertEqual(p.streaks['A'],1)
        active=choose(p,scores(),active,'2020-09-30')[0]
        self.assertNotIn('A',active)
        self.assertEqual(p.exit_reason('A'),'EXIT_BOTTOM_QUARTILE_CONFIRMED')
        self.assertEqual(p.exit_streak('A'),2)
        self.assertEqual([r['date'] for r in p.review_log if r['ticker']=='A'],
                         ['2020-06-30','2020-09-30'])

    def test_quarterly_recovery_resets_confirmation(self):
        p=RecoveryExitPolicy('confirm')
        active=choose(p,scores(),{'A'},'2020-06-30')[0]
        active=choose(p,scores(a=.95),active,'2020-09-30')[0]
        self.assertEqual(p.streaks['A'],0)
        active=choose(p,scores(),active,'2020-12-31')[0]
        self.assertIn('A',active);self.assertEqual(p.streaks['A'],1)
        active=choose(p,scores(),active,'2021-03-31')[0]
        self.assertNotIn('A',active)

    def test_lost_coverage_forces_exit_and_erases_streak(self):
        p=RecoveryExitPolicy('confirm')
        active=choose(p,scores(),{'A'},'2020-06-30')[0]
        unavailable=scores();del unavailable['A'];unavailable['E']=dict(score=.1)
        selected,_,cap_removed,_,_=choose(p,unavailable,active,'2020-07-31',quarter=False)
        self.assertNotIn('A',selected)
        self.assertNotIn('A',cap_removed)
        self.assertNotIn('A',p.streaks)
        # The engine, rather than the policy, supplies the coverage/policy exit label.
        self.assertNotIn('A',p.last_exits)
        active=choose(p,scores(a=.95),selected,'2020-09-30')[0]
        self.assertIn('A',active)
        active=choose(p,scores(),active,'2020-12-31')[0]
        self.assertIn('A',active);self.assertEqual(p.streaks['A'],1)

    def test_capacity_removal_is_not_reported_as_actual_deferral(self):
        p=RecoveryExitPolicy('confirm')
        selected,_,removed,_,audit=choose(p,scores(),{'A','B','C'},'2020-06-30',maximum=3)
        self.assertEqual(selected,{'B','C','D'});self.assertEqual(removed,{'A'})
        row=next(r for r in p.review_log if r['ticker']=='A')
        self.assertFalse(row['score_exit']);self.assertFalse(row['held_after'])
        self.assertTrue(row['capacity_removed'])
        self.assertEqual(audit['attempted_score_deferrals'],1)
        self.assertEqual(audit['deferred_score_exits'],0)
        self.assertNotIn('A',p.streaks)

    def test_no_score_exit_still_respects_capacity_and_coverage(self):
        p=RecoveryExitPolicy('none')
        selected,_,removed,_,audit=choose(p,scores(),{'A','B','C','D'},'2020-06-30',maximum=2)
        self.assertEqual(selected,{'C','D'});self.assertEqual(removed,{'A','B'})
        self.assertFalse(any(r['score_exit'] for r in p.review_log))
        self.assertEqual(audit['deferred_score_exits'],0)
        unavailable=scores();del unavailable['D'];unavailable['E']=dict(score=.8)
        selected=choose(p,unavailable,selected,'2020-07-31',quarter=False,maximum=2)[0]
        self.assertNotIn('D',selected)

    def test_grace_only_protects_one_consecutive_breach(self):
        p=RecoveryExitPolicy('grace')
        active=choose(p,scores(improving=True),{'A'},'2020-06-30')[0]
        self.assertIn('A',active)
        first=next(r for r in p.review_log if r['ticker']=='A')
        self.assertTrue(first['grace']);self.assertFalse(first['score_exit'])
        active=choose(p,scores(improving=True),active,'2020-09-30')[0]
        self.assertNotIn('A',active)
        self.assertEqual(p.exit_reason('A'),'EXIT_BOTTOM_QUARTILE_AFTER_GRACE')
        self.assertEqual(p.exit_streak('A'),2)

    def test_missing_or_non_improving_trend_does_not_grant_grace(self):
        for missing in (False,True):
            with self.subTest(missing=missing):
                p=RecoveryExitPolicy('grace');sc=scores()
                if missing:del sc['A']['improving_both']
                selected=choose(p,sc,{'A'},'2020-06-30')[0]
                self.assertNotIn('A',selected)
                self.assertEqual(p.exit_reason('A'),'EXIT_BOTTOM_QUARTILE_NO_RECOVERY')
                self.assertEqual(p.exit_streak('A'),1)

    def test_independent_q50_q75_instances_do_not_share_state(self):
        p50,p75=RecoveryExitPolicy('confirm'),RecoveryExitPolicy('confirm')
        a50=choose(p50,scores(),{'A'},'2020-06-30',rule='q50')[0]
        a75=choose(p75,scores(),{'A'},'2020-06-30',rule='q75')[0]
        self.assertEqual(p50.streaks['A'],1);self.assertEqual(p75.streaks['A'],1)
        choose(p50,scores(),a50,'2020-09-30',rule='q50')
        self.assertEqual(p50.exit_streak('A'),2)
        self.assertEqual(p75.last_date,'2020-06-30')
        self.assertEqual(p75.streaks['A'],1);self.assertFalse(p75.last_exits)
        self.assertNotIn('A',choose(p75,scores(),a75,'2020-09-30',rule='q75')[0])

    def test_single_exit_matches_existing_selector(self):
        for rule in ('q50','q75'):
            p=RecoveryExitPolicy('single')
            for date,quarter,active in [('2020-03-31',True,set()),('2020-04-30',False,{'A','B','D'}),
                                        ('2020-06-30',True,{'A','B','D'})]:
                expected=constrained_selection(scores(),active,rule,quarter,1,3)
                actual=choose(p,scores(),active,date,quarter=quarter,rule=rule,maximum=3)
                self.assertEqual(actual[:4],expected[:4])
                self.assertEqual({k:actual[4][k] for k in expected[4]},expected[4])

    def test_repeated_or_backward_review_is_rejected(self):
        p=RecoveryExitPolicy('confirm')
        choose(p,scores(),{'A'},'2020-06-30')
        for date in ('2020-06-30','2020-03-31'):
            with self.assertRaisesRegex(AssertionError,'once or out of order'):
                choose(p,scores(),{'A'},date)


if __name__=='__main__':unittest.main()
