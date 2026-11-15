"""Regression tests for policy admission, information dates and universe ranking."""
import unittest
from backtest import ranks
from run_long_history import HistoryInputs, build_lam
from run_pillar2 import PolicyInputs, accepted, active_events, read_research, start_audit


def event(ticker='INTC', relationship='direct', start='2020-02-15', end=''):
    return dict(event_id='test_'+ticker,ticker=ticker,relationship=relationship,
                qualifies=True,eligible_from=start,end_date=end)


class Pillar2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lam,cls.registry=build_lam()

    def test_source_at_cutoff_waits_for_next_month(self):
        e=event(start='2020-03-01')
        self.assertFalse(active_events([e],'INTC','2020-03-31','direct'))
        self.assertTrue(active_events([e],'INTC','2020-04-30','direct'))

    def test_withdrawal_ends_only_that_event(self):
        e=event(end='2020-04-01')
        e['cancellation_public_date']='2020-03-15'
        self.assertTrue(active_events([e],'INTC','2020-03-31','direct'))
        self.assertFalse(active_events([e],'INTC','2020-04-30','direct'))
        e2=event(start='2020-03-15')
        self.assertEqual(active_events([e,e2],'INTC','2020-04-30','direct'),[e2])

    def test_same_cutoff_withdrawal_disclosure_waits(self):
        e=event(end='2020-04-01')
        e['cancellation_public_date']='2020-04-01'
        self.assertTrue(active_events([e],'INTC','2020-04-30','direct'))
        self.assertFalse(active_events([e],'INTC','2020-05-31','direct'))
        inp=PolicyInputs('US','source','direct',[e],self.lam,self.registry)
        self.assertEqual(inp.policy[0]['end_date'],'2020-04-02')

    def test_project_completion_is_not_undone_historical_receipt(self):
        e=event();e['support_end_date']='2021-12-31'
        self.assertTrue(active_events([e],'INTC','2022-03-31','direct'))

    def test_indirect_and_rejected_evidence_stay_distinct(self):
        e=event(relationship='indirect')
        self.assertFalse(accepted(e,'direct'))
        self.assertTrue(accepted(e,'with_indirect'))
        e['qualifies']=False
        self.assertFalse(accepted(e,'with_indirect'))

    def test_history_wrappers_propagate_gate(self):
        inp=HistoryInputs('US','source',self.lam,self.registry)
        inp.policy=[dict(ticker='INTC',start_date='2020-01-01',end_date='')]
        gated,_=inp.signals('US','2022-09-30','hybrid',gate=True)
        ungated,_=inp.signals('US','2022-09-30','hybrid',gate=False)
        self.assertEqual(set(gated),{'INTC'})
        self.assertGreater(len(ungated),1)

    def test_rank_only_policy_eligible_companies(self):
        es=[event(t) for t in ('INTC','MU','TXN','AMAT')]
        inp=PolicyInputs('US','source','direct',es,self.lam,self.registry)
        scores,_=inp.signals('US','2022-09-30','hybrid',gate=True)
        self.assertEqual(set(scores),{e['ticker'] for e in es})
        expected=ranks({t:s['roce'] for t,s in scores.items()})
        self.assertEqual({t:s['rank_roce'] for t,s in scores.items()},expected)

    def test_confirmed_award_does_not_override_spin_off_listing(self):
        inp=PolicyInputs('US','source','direct',[event('GEV',start='2020-01-01')],self.lam,self.registry)
        before,_=inp.signals('US','2024-03-31','hybrid',True)
        during,_=inp.signals('US','2024-04-30','hybrid',True)
        after,_=inp.signals('US','2024-06-30','hybrid',True)
        self.assertNotIn('GEV',before);self.assertNotIn('GEV',during)
        self.assertIn('GEV',after)

    def test_start_must_cover_later_policy_admissions(self):
        rows=[]
        for date in ('2019-03-31','2019-04-30','2019-05-31','2019-06-30'):
            for t in range(4):
                rows.append(dict(date=date,required=True,complete=True,ticker=str(t),
                                 region='US',definition='direct',timing='source'))
        rows.append(dict(date='2019-04-30',required=True,complete=False,ticker='NEW',
                         region='US',definition='direct',timing='source'))
        self.assertEqual(start_audit(rows)[0],'2019-06-30')

    def test_every_candidate_audited_and_no_event_backdated(self):
        events,candidates=read_research()
        self.assertEqual(len(candidates),31)
        for e in events:
            if e['qualifies']:
                self.assertGreaterEqual(e['eligible_from'],e['public_date'])
                self.assertGreaterEqual(e['eligible_from'],e['event_date'])


if __name__=='__main__':unittest.main()
