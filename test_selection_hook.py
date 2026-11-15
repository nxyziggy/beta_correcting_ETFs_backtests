"""Selection-hook integration: unchanged defaults and auditable delayed exits."""
import unittest
from collections import defaultdict

from backtest import constrained_selection, read_csv, run
from prepare_data import ROOT
from run_pillar2 import PolicyInputs, read_research, build_lam


class ToyInputs:
    """Four scored securities plus a fifth replacement for coverage tests."""
    dates=('2020-03-31','2020-04-30','2020-05-31','2020-06-30',
           '2020-07-31','2020-08-31','2020-09-30')
    price_policy='monthly_vendor_only'

    def __init__(self,lose_a=False):
        self.lose_a=lose_a
        self.universe={t:dict(region='US') for t in 'ABCDE'}
        self.prices={t:{d:100. for d in self.dates} for t in ('A','B','C','D','E','SOXX','ICLN')}
        self.extension_config=dict(complete_month_end=self.dates[-1],as_of=self.dates[-1])
        self.extension_daily=defaultdict(dict)

    def signals(self,region,date,panel,gate,annual_lag):
        values={'A':.9,'B':.7,'C':.5,'D':.1} if date<'2020-06-01' else {'A':.1,'B':.9,'C':.7,'D':.5}
        reasons={}
        if self.lose_a and date>='2020-06-01':
            del values['A'];values['E']=.1;reasons['A']='lost policy eligibility'
        result={}
        for t,score in values.items():
            result[t]=dict(score=score,roce=score,cash_accruals=0,rank_roce=score,rank_quality=score,
                           period_end='2019-12-31',period_type='annual',available_used='2020-02-01',
                           report_age_days=180,panel='test',income_source='test',balance_source='test',cashflow_source='test')
        return result,reasons

    def price(self,ticker,date,region):return self.prices[ticker][date]

    def daily_price(self,ticker,date,required=True):return None


class DelayedToyPolicy:
    score_exit_qualifying_quarters=2

    def __init__(self):self.calls=[]

    def select(self,sc,active,rule,quarter_end,minimum,maximum,date):
        self.calls.append((date,quarter_end))
        selected,floor,removed,threshold,audit=constrained_selection(sc,active,rule,quarter_end,minimum,maximum)
        # Integration fixture: keep the known June bottom-quartile holding through
        # the following two non-review months, and let September's exit proceed.
        if date<'2020-09-01' and 'A' in active and 'A' in sc:selected.add('A')
        audit['final_holdings']=len(selected)
        return selected,floor,removed,threshold,audit

    def exit_reason(self,ticker):return 'EXIT_CONFIRMED_BOTTOM_QUARTILE'

    def exit_streak(self,ticker):return 2


class SelectionHookTests(unittest.TestCase):
    def execute(self,policy=None,lose_a=False):
        return run(ToyInputs(lose_a),'US','test','q75',10,start='2020-03-31',selection_policy=policy)

    def test_omitted_policy_is_exactly_explicit_none(self):
        implicit=run(ToyInputs(),'US','test','q75',10,start='2020-03-31')
        self.assertEqual(implicit,self.execute(None))
        exits=[e for e in implicit['events'] if e['event'].startswith('EXIT_')]
        self.assertEqual([(e['date'],e['ticker'],e['event']) for e in exits],
                         [('2020-06-30','A','EXIT_BOTTOM_QUARTILE')])
        self.assertTrue(all('score_exit_streak' not in e for e in implicit['events']))

    def test_policy_can_retain_bottom_quartile_until_later_review(self):
        policy=DelayedToyPolicy();result=self.execute(policy)
        self.assertIn(('2020-06-30',True),policy.calls)
        self.assertIn(('2020-07-31',False),policy.calls)
        hs={(h['date'],h['ticker']) for h in result['holdings']}
        self.assertIn(('2020-06-30','A'),hs);self.assertIn(('2020-08-31','A'),hs)
        self.assertNotIn(('2020-09-30','A'),hs)
        exit_row=next(e for e in result['events'] if e['event'].startswith('EXIT_'))
        self.assertEqual(exit_row['event'],'EXIT_CONFIRMED_BOTTOM_QUARTILE')
        self.assertEqual(exit_row['date'],'2020-09-30')
        self.assertEqual(exit_row['score_exit_streak'],2)
        self.assertEqual(result['summary']['score_exit_qualifying_quarters'],2)
        self.assertEqual(len({tuple(e) for e in result['events']}),1)

    def test_coverage_exit_cannot_be_reclassified_by_custom_rule(self):
        result=self.execute(DelayedToyPolicy(),lose_a=True)
        row=next(e for e in result['events'] if e['event'].startswith('EXIT_'))
        self.assertEqual(row['event'],'EXIT_COVERAGE_OR_ELIGIBILITY')
        self.assertEqual(row['date'],'2020-06-30')

    def test_uncovered_custom_holding_is_rejected(self):
        class InvalidPolicy:
            def select(self,sc,active,rule,quarter_end,minimum,maximum,date):
                selected,floor,removed,threshold,audit=constrained_selection(sc,active,rule,quarter_end,minimum,maximum)
                selected.add('UNAVAILABLE')
                return selected,floor,removed,threshold,audit
        with self.assertRaisesRegex(AssertionError,'uncovered/ineligible'):
            self.execute(InvalidPolicy())

    def test_custom_score_exit_defaults_to_neutral_label(self):
        class Passthrough:
            def select(self,sc,active,rule,quarter_end,minimum,maximum,date):
                return constrained_selection(sc,active,rule,quarter_end,minimum,maximum)
        result=self.execute(Passthrough())
        row=next(e for e in result['events'] if e['event'].startswith('EXIT_'))
        self.assertEqual(row['event'],'EXIT_SCORE_RULE')
        self.assertEqual(result['monthly'],self.execute()['monthly'])

    def test_custom_rule_cannot_fake_capacity_exit(self):
        class IncorrectLabel(DelayedToyPolicy):
            def exit_reason(self,ticker):return 'EXIT_CAPACITY'
        with self.assertRaisesRegex(AssertionError,'Reserved engine exit label'):
            self.execute(IncorrectLabel())

    def test_equal_weight_ignores_selection_policy(self):
        class MustNotRun:
            def select(self,**kwargs):raise AssertionError('Equal weight invoked score selection')
        old=run(ToyInputs(),'US','test','equal',10,start='2020-03-31')
        new=run(ToyInputs(),'US','test','equal',10,start='2020-03-31',selection_policy=MustNotRun())
        self.assertEqual(old,new)

    def test_default_reproduces_frozen_real_monthly_ledger(self):
        events,_=read_research();lam,registry=build_lam()
        reference=next(s for s in read_csv(ROOT/'results_pillar2/summary.csv')
                       if s['definition']=='direct' and s['region']=='US' and s['rule']=='q75'
                       and s['window']=='earliest_complete')
        inp=PolicyInputs('US','source','direct',events,lam,registry)
        result=run(inp,'US','reproduction','q75',10,gate=True,annual_lag=0,start=reference['start'])
        expected=read_csv(ROOT/'results_pillar2'/reference['run']/'monthly.csv')
        self.assertEqual([{k:str(v) for k,v in r.items()} for r in result['monthly']],expected)


if __name__=='__main__':unittest.main()
