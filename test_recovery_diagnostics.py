"""Independent arithmetic and calendar checks for retrospective diagnostics."""
import calendar
import copy
import unittest

from recovery_diagnostics import chronological_rows, first_entry_rows, recovery_exit_rows


def portfolio(variant='baseline',rule='q50',region='US',dates=None,navs=None,final=288):
    dates=dates or ['2019-06-30','2020-06-30','2022-12-31','2023-01-31','2026-10-31']
    navs=navs or [99,120,160,144,240]
    return dict(summary=dict(run=region+'_'+rule+'_'+variant,case='direct_main',variant=variant,
                             region=region,rule=rule,start=dates[0],monthly_end=dates[-1],
                             latest_end='2026-11-02' if dates[-1]=='2026-10-31' else dates[-1],
                             final_NAV=final),
                monthly=[dict(date=d,NAV=n,Cost=1,TradedNotional=100,Turnover=.5) for d,n in zip(dates,navs)],
                holdings=[],events=[],coverage=[])


def hold(result,date,ticker,weight):
    result['holdings'].append(dict(date=date,ticker=ticker,weight=weight,value=100*weight))


class Prices:
    def __init__(self,ticker,prices,delisting=None,fx=None):
        self.prices={ticker:prices}
        self.universe={ticker:dict(delisting_date=delisting)}
        self.fx=fx or {}
        self.calls=[]

    def price(self,ticker,date,region):
        self.calls.append((ticker,date,region))
        return self.prices[ticker][date]*self.fx.get(date,1)


def monthly_portfolio(variant='baseline',region='US'):
    dates=[f'2023-{m:02d}-{calendar.monthrange(2023,m)[1]}' for m in range(1,13)]
    return portfolio(variant,region=region,dates=dates,navs=[100]*12,final=100)


class RecoveryDiagnosticTests(unittest.TestCase):
    def test_period_returns_use_actual_nav_anchors_and_partial_final_mark(self):
        baseline=portfolio();variant=portfolio('trend');control=portfolio('equal','equal',final=240)
        rows={r['period']:r for r in chronological_rows(variant,baseline,control)}
        self.assertAlmostEqual(rows['full']['total_return'],1.88)
        self.assertAlmostEqual(rows['early']['total_return'],.60)
        self.assertAlmostEqual(rows['late']['total_return'],.80)
        self.assertAlmostEqual(rows['common_trend_coverage']['total_return'],1.40)
        self.assertAlmostEqual(rows['late']['delta_vs_control_pp'],30)
        self.assertEqual(rows['late']['start_NAV'],160)
        self.assertEqual(rows['late']['costs_NAV_units'],2)
        self.assertEqual(rows['early']['costs_NAV_units'],3)
        self.assertEqual(rows['full']['costs_NAV_units'],5)
        self.assertAlmostEqual(rows['late']['max_drawdown_monthly'],-.1)

    def test_initial_deployment_cost_enters_full_drawdown(self):
        dates=['2019-06-30','2020-06-30','2022-12-31','2023-01-31','2026-10-31']
        b=portfolio(dates=dates,navs=[99,110,120,130,140],final=150)
        v=copy.deepcopy(b);v['summary']['variant']='balanced'
        c=copy.deepcopy(b);c['summary']['rule']='equal'
        rows={r['period']:r for r in chronological_rows(v,b,c)}
        self.assertAlmostEqual(rows['full']['max_drawdown_monthly'],-.01)
        self.assertEqual(rows['late']['max_drawdown_monthly'],0)

    def test_exact_anchor_is_not_replaced_by_nearby_observation(self):
        b=portfolio();v=portfolio('trend');c=portfolio('equal','equal')
        for r in (b,v,c):r['monthly'][1]['date']='2020-05-31'
        row=next(r for r in chronological_rows(v,b,c) if r['period']=='common_trend_coverage')
        self.assertEqual(row['status'],'unavailable_exact_anchor_or_endpoint')
        self.assertIsNone(row['total_return'])

    def test_all_candidate_first_entries_include_new_missed_and_never_held(self):
        b=monthly_portfolio();v=monthly_portfolio('trend')
        for result in (b,v):result['coverage']=[dict(ticker=t) for t in ('A','B','C','D')]
        hold(b,'2023-01-31','A',.5);hold(b,'2023-02-28','B',.5)
        hold(v,'2023-02-28','A',.5);hold(v,'2023-01-31','C',.5)
        hold(v,'2023-01-31','CASH',0)
        rows={r['ticker']:r for r in first_entry_rows([b,v]) if r['variant']=='trend'}
        self.assertEqual(set(rows),{'A','B','C','D'})
        self.assertEqual(rows['A']['days_shift'],28)
        self.assertTrue(rows['B']['missed_baseline'])
        self.assertTrue(rows['C']['new_entrant'])
        self.assertEqual(rows['D']['status'],'never_held_by_either')

    def test_recovery_exposure_uses_start_of_return_interval_weights(self):
        b=monthly_portfolio();v=monthly_portfolio('confirm_exit')
        hold(b,'2023-01-31','A',.2);hold(b,'2023-02-28','A',.2)
        b['events']=[dict(date='2023-03-31',ticker='A',event='EXIT_BOTTOM_QUARTILE')]
        for d,w in [('2023-03-31',.2),('2023-04-30',.3),('2023-05-31',.4),('2023-09-30',1)]:hold(v,d,'A',w)
        # Baseline's purchase at the horizon close earned none of the preceding six months.
        hold(b,'2023-09-30','A',1)
        v['events']=[dict(date='2023-06-30',ticker='A',event='EXIT_BOTTOM_QUARTILE')]
        ps={r['date']:100 for r in b['monthly']};ps['2023-09-30']=150
        row=recovery_exit_rows(b,v,Prices('A',ps))[0]
        self.assertAlmostEqual(row['six_month_stock_return'],.5)
        self.assertEqual(row['horizon_date'],'2023-09-30')
        self.assertEqual(row['variant_months_exposed'],3)
        self.assertAlmostEqual(row['variant_average_weight'],.15)
        self.assertEqual(row['baseline_months_exposed'],0)
        self.assertEqual(row['exit_shift_days'],91)

    def test_censored_horizon_ignores_prices_after_portfolio_endpoint(self):
        b=monthly_portfolio();v=monthly_portfolio('confirm_exit')
        b['events']=[dict(date='2023-09-30',ticker='A',event='EXIT_BOTTOM_QUARTILE')]
        ps={r['date']:100 for r in b['monthly']};ps['2024-03-31']=1000
        row=recovery_exit_rows(b,v,Prices('A',ps))[0]
        self.assertEqual(row['horizon_date'],'2024-03-31')
        self.assertEqual(row['status'],'right_censored')
        self.assertIsNone(row['six_month_stock_return'])
        self.assertEqual(row['forward_months_observed'],3)

    def test_month_end_is_calendar_based_and_euro_return_uses_converted_prices(self):
        b=monthly_portfolio(region='EU');v=monthly_portfolio('trend',region='EU')
        b['events']=[dict(date='2023-01-31',ticker='A',event='EXIT_BOTTOM_QUARTILE')]
        ps={r['date']:100 for r in b['monthly']};ps['2023-07-31']=120
        row=recovery_exit_rows(b,v,Prices('A',ps,fx={'2023-01-31':.8,'2023-07-31':.9}))[0]
        self.assertEqual(row['horizon_date'],'2023-07-31')
        self.assertAlmostEqual(row['six_month_stock_return'],.35)

    def test_delisting_uses_documented_cash_and_no_post_delisting_quote(self):
        b=monthly_portfolio(region='EU');v=monthly_portfolio('confirm_exit',region='EU')
        b['events']=[dict(date='2023-03-31',ticker='EDF.PA',event='EXIT_BOTTOM_QUARTILE')]
        prices=Prices('EDF.PA',{'2023-03-31':10,'2023-04-30':11,'2023-05-31':11.5,'2023-06-30':12},'2023-06-08')
        row=recovery_exit_rows(b,v,prices)[0]
        self.assertEqual(row['status'],'complete')
        self.assertEqual(row['cash_redemption_date'],'2023-06-30')
        self.assertAlmostEqual(row['six_month_stock_return'],.2)
        self.assertFalse(any(date>'2023-06-30' for _,date,_ in prices.calls))

    def test_missing_horizon_price_is_not_forward_filled(self):
        b=monthly_portfolio();v=monthly_portfolio('trend')
        b['events']=[dict(date='2023-03-31',ticker='A',event='EXIT_BOTTOM_QUARTILE')]
        ps={r['date']:100 for r in b['monthly']};ps.pop('2023-09-30');ps['2023-09-29']=150
        row=recovery_exit_rows(b,v,Prices('A',ps))[0]
        self.assertEqual(row['status'],'unavailable')
        self.assertIsNone(row['six_month_stock_return'])
        self.assertIn('2023-09-30',row['reason'])

    def test_non_score_exits_do_not_enter_recovery_diagnostic(self):
        b=monthly_portfolio();v=monthly_portfolio('trend')
        b['events']=[dict(date='2023-03-31',ticker='A',event='EXIT_COVERAGE_OR_ELIGIBILITY')]
        self.assertEqual(recovery_exit_rows(b,v,Prices('A',{})),[])


if __name__=='__main__':unittest.main()
