"""Read-only, hindsight diagnostics for the fixed scoring/exit experiments.

No value returned here enters portfolio selection. Returns are decimal fractions;
relative return differences are percentage points. ``days_shift`` and
``exit_shift_days`` are negative for an earlier variant action.
"""
import calendar
import datetime as dt
import math
from collections import defaultdict


def _identity(result):
    s=result['summary']
    return {k:s[k] for k in ('run','case','variant','region','rule')}


def _comparable(result, baseline, control=None):
    s,b=result['summary'],baseline['summary']
    for key in ('case','region','rule','start','latest_end'):
        assert s[key]==b[key],('Unmatched baseline',key,s[key],b[key])
    assert b['variant']=='baseline'
    dates=[r['date'] for r in result['monthly']]
    assert dates==[r['date'] for r in baseline['monthly']]
    if control is not None:
        c=control['summary']
        for key in ('case','region','start','latest_end'):
            assert s[key]==c[key],('Unmatched control',key,s[key],c[key])
        assert c['rule']=='equal'
        assert dates==[r['date'] for r in control['monthly']]


def _month_end(date, offset=0):
    d=dt.date.fromisoformat(date)
    year,month0=divmod(d.year*12+d.month-1+offset,12)
    month=month0+1
    return dt.date(year,month,calendar.monthrange(year,month)[1]).isoformat()


def _period_numbers(result, anchor, end):
    """Keep the existing position path; an anchor is valued after its own trades."""
    monthly={r['date']:r for r in result['monthly']}
    s=result['summary']
    if anchor is not None and anchor not in monthly:return None
    if end!=s['latest_end'] and end not in monthly:return None
    start_nav=100.0 if anchor is None else float(monthly[anchor]['NAV'])
    end_nav=float(s['final_NAV']) if end==s['latest_end'] else float(monthly[end]['NAV'])
    selected=[r for r in result['monthly'] if (anchor is None or r['date']>anchor) and r['date']<=end]
    peak=start_nav;drawdown=0.0
    for r in selected:
        nav=float(r['NAV']);peak=max(peak,nav);drawdown=min(drawdown,nav/peak-1)
    costs=sum(float(r['Cost']) for r in selected)
    traded=sum(float(r['TradedNotional']) for r in selected)
    return dict(total_return=end_nav/start_nav-1,start_NAV=start_nav,end_NAV=end_nav,
                max_drawdown_monthly=drawdown,monthly_observations=len(selected),
                costs_NAV_units=costs,costs_pct_start_NAV=100*costs/start_nav,
                traded_notional_NAV_units=traded,traded_multiple_start_NAV=traded/start_nav,
                turnover_sum=sum(float(r['Turnover']) for r in selected))


def chronological_rows(result, baseline, control):
    """Four continuous-path slices; partial final mark affects returns, not monthly DD.

    Full and early slices include the initial deployment cost. Late and common
    trend-coverage slices start from the prior month-end's actual after-trade NAV
    and therefore exclude costs already paid at that anchor. Missing exact
    anchors produce an explicit unavailable row, never a nearby-date substitute.
    """
    _comparable(result,baseline,control)
    s=result['summary'];identity=_identity(result)
    periods=(('full',s['start'],None,s['latest_end']),
             ('early',s['start'],None,'2022-12-31'),
             ('late','2023-01-01','2022-12-31',s['latest_end']),
             ('common_trend_coverage','2020-07-01','2020-06-30',s['latest_end']))
    rows=[]
    number_keys=('total_return','start_NAV','end_NAV','max_drawdown_monthly','monthly_observations',
                 'costs_NAV_units','costs_pct_start_NAV','traded_notional_NAV_units',
                 'traded_multiple_start_NAV','turnover_sum')
    for period,start,anchor,end in periods:
        row=dict(**identity,period=period,start=start,end=end,anchor_date=anchor or '',status='complete')
        own=_period_numbers(result,anchor,end)
        base=_period_numbers(baseline,anchor,end)
        equal=_period_numbers(control,anchor,end)
        if start>s['latest_end'] or end<s['start'] or any(x is None for x in (own,base,equal)):
            row.update(status='unavailable_exact_anchor_or_endpoint')
            row.update({k:None for k in number_keys})
            row.update(baseline_return=None,control_return=None,delta_vs_baseline_pp=None,
                       delta_vs_control_pp=None,baseline_max_drawdown_monthly=None,
                       control_max_drawdown_monthly=None)
        else:
            row.update(own)
            row.update(baseline_return=base['total_return'],control_return=equal['total_return'],
                       delta_vs_baseline_pp=100*(own['total_return']-base['total_return']),
                       delta_vs_control_pp=100*(own['total_return']-equal['total_return']),
                       baseline_max_drawdown_monthly=base['max_drawdown_monthly'],
                       control_max_drawdown_monthly=equal['max_drawdown_monthly'])
        rows.append(row)
    return rows


def _weight_lookup(result):
    weights={}
    for h in result['holdings']:
        if h['ticker']=='CASH':continue
        key=(h['date'],h['ticker'])
        assert key not in weights,('Duplicate holdings observation',key)
        weights[key]=float(h['weight'])
    return weights


def first_entry_rows(results):
    """Audit all candidate stocks, including names never held by either portfolio."""
    groups=defaultdict(list)
    for result in results:
        s=result['summary']
        if s['rule']=='equal':continue
        groups[s['case'],s['region'],s['rule']].append(result)
    rows=[]
    for _,group in sorted(groups.items()):
        baselines=[r for r in group if r['summary']['variant']=='baseline']
        assert len(baselines)==1,'Exactly one baseline is required per case/region/rule'
        assert len({r['summary']['variant'] for r in group})==len(group),'Duplicate variant'
        baseline=baselines[0]
        candidates={r['ticker'] for result in group for r in result.get('coverage',[]) if r['ticker']!='CASH'}
        candidates|={h['ticker'] for result in group for h in result['holdings'] if h['ticker']!='CASH'}
        def dates(result,ticker):
            return sorted({h['date'] for h in result['holdings'] if h['ticker']==ticker and float(h['weight'])>0})
        for result in sorted(group,key=lambda r:r['summary']['variant']):
            _comparable(result,baseline)
            for ticker in sorted(candidates):
                a,b=dates(result,ticker),dates(baseline,ticker)
                first,original=(a[0] if a else ''),(b[0] if b else '')
                status=('held_by_both' if a and b else 'new_entrant' if a else
                        'missed_baseline' if b else 'never_held_by_either')
                shift=(dt.date.fromisoformat(first)-dt.date.fromisoformat(original)).days if a and b else None
                rows.append(dict(**_identity(result),ticker=ticker,baseline_first_entry=original,
                                 variant_first_entry=first,days_shift=shift,status=status,
                                 new_entrant=bool(a and not b),missed_baseline=bool(b and not a),
                                 baseline_months_held=len(b),variant_months_held=len(a)))
    return rows


def _forward_stock_return(inputs,ticker,region,exit_date,horizon):
    """Exact monthly observations, with the engine's documented EDF cash recovery."""
    u=inputs.universe[ticker]
    delisting=u.get('delisting_date')
    terminal=horizon;cash_date=''
    if delisting and exit_date>=delisting:
        return None,'exit_not_in_listed_history',''
    if delisting and delisting<=horizon:
        # This is the only verified cash delisting supported by the frozen engine.
        if ticker!='EDF.PA' or _month_end(delisting)!='2023-06-30':
            return None,'delisting_cash_proceeds_unavailable',''
        cash_date=terminal='2023-06-30'
        raw=inputs.prices[ticker].get(cash_date)
        if raw is None or not math.isclose(float(raw),12.0,rel_tol=0,abs_tol=1e-10):
            return None,'verified_EDF_cash_quote_missing',''
    needed=[exit_date]+[_month_end(exit_date,i) for i in range(1,7) if _month_end(exit_date,i)<=terminal]
    for date in needed:
        if inputs.prices[ticker].get(date) is None or float(inputs.prices[ticker][date])<=0:
            return None,'missing_exact_monthly_price:'+date,cash_date
    try:
        value=inputs.price(ticker,terminal,region)/inputs.price(ticker,exit_date,region)-1
    except (ValueError,KeyError) as exc:
        return None,'market_or_FX_data_unavailable:'+str(exc),cash_date
    return value,'cash_redemption_carried_at_zero_return' if cash_date else 'observed_stock_return',cash_date


def _comparison_exit(baseline,variant,ticker,date,variant_weights):
    events=[e for e in variant['events'] if e['ticker']==ticker and
            (e['event'].startswith('EXIT') or e['event']=='CASH_DELIST')]
    same=[e for e in events if e['date']==date]
    if same:return same[0],'same_date_exit'
    if variant_weights.get((date,ticker),0)>0:
        future=sorted((e for e in events if e['date']>date),key=lambda e:e['date'])
        return (future[0],'held_at_baseline_exit_then_exited') if future else (None,'held_at_baseline_exit_no_later_exit')
    earlier_baseline=[e['date'] for e in baseline['events'] if e['ticker']==ticker
                      and e['event'].startswith('EXIT') and e['date']<date]
    previous=max(earlier_baseline,default='')
    episode=[h['date'] for h in baseline['holdings'] if h['ticker']==ticker and float(h['weight'])>0
             and previous<h['date']<date]
    if episode:
        earlier=[e for e in events if min(episode)<=e['date']<date]
        if earlier:return max(earlier,key=lambda e:e['date']),'earlier_exit_during_baseline_holding_episode'
    return None,'not_held_at_baseline_exit_no_matching_exit'


def recovery_exit_rows(baseline, variant, inputs):
    """Every baseline score exit, with six-month hindsight returns and actual exposure.

    Exposure uses the post-trade weights at the START of each following monthly
    return interval (exit month through month +5). It never credits a purchase
    at the final horizon close with the preceding month's recovery. Censored
    rows retain observed exposure counts, whose denominator is explicitly shown.
    """
    _comparable(variant,baseline)
    vw,bw=_weight_lookup(variant),_weight_lookup(baseline)
    monthly_dates={r['date'] for r in baseline['monthly']}
    endpoint=baseline['summary']['monthly_end']
    coverage={(r['date'],r['ticker']):str(r['covered']).lower()=='true' for r in baseline.get('coverage',[])}
    rows=[]
    for event in baseline['events']:
        if not event['event'].startswith('EXIT_BOTTOM_QUARTILE'):continue
        date,ticker=event['date'],event['ticker']
        assert date==_month_end(date),'Recovery events must use calendar month-end labels'
        horizon=_month_end(date,6)
        following=[_month_end(date,i) for i in range(1,7)]
        observed=[d for d in following if d in monthly_dates]
        starts=[_month_end(d,-1) for d in observed]
        complete=horizon<=endpoint and len(observed)==6
        censored=horizon>endpoint
        stock_return=reason=cash_date=None
        if censored:status,reason='right_censored','six_month_horizon_after_monthly_endpoint'
        elif not complete:status,reason='unavailable','missing_exact_portfolio_month'
        else:
            stock_return,reason,cash_date=_forward_stock_return(inputs,ticker,variant['summary']['region'],date,horizon)
            status='complete' if stock_return is not None else 'unavailable'
        ve,match=_comparison_exit(baseline,variant,ticker,date,vw)
        exit_shift=(dt.date.fromisoformat(ve['date'])-dt.date.fromisoformat(date)).days if ve else None
        valid=[coverage.get((d,ticker)) for d in observed]
        n=len(starts)
        rows.append(dict(**_identity(variant),ticker=ticker,baseline_exit_date=date,
                         baseline_exit_event=event['event'],horizon_date=horizon,status=status,
                         right_censored=censored,reason=reason,six_month_stock_return=stock_return,
                         cash_redemption_date=cash_date or '',forward_months_observed=n,
                         exposure_start_dates='|'.join(starts),
                         variant_months_exposed=sum(vw.get((d,ticker),0)>0 for d in starts),
                         baseline_months_exposed=sum(bw.get((d,ticker),0)>0 for d in starts),
                         variant_average_weight=sum(vw.get((d,ticker),0) for d in starts)/n if n else None,
                         baseline_average_weight=sum(bw.get((d,ticker),0) for d in starts)/n if n else None,
                         baseline_eligible_followup_months=sum(valid) if all(v is not None for v in valid) else None,
                         variant_exit_date=ve['date'] if ve else '',variant_exit_event=ve['event'] if ve else '',
                         exit_shift_days=exit_shift,exit_comparison_status=match))
    return rows
