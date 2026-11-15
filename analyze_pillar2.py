#!/usr/bin/env python3
"""Reconcile every stock's contribution to the six direct-gate headline returns."""
import json
from collections import defaultdict

from backtest import read_csv
from prepare_data import ROOT
from run_pillar2 import OUT, PolicyInputs, read_research, build_lam
from run_research_corrections import close, digest, save, write_csv

SEMIS={'INTC','TSM','MU','GFS','TXN','AMAT','LRCX','MCHP',
       'STMPA.PA','IFX.DE','NXPI','ASML','AMS.SW'}


def stock_attribution(s, inp):
    path=OUT/s['run']
    holdings=read_csv(path/'holdings.csv');trades=read_csv(path/'trades.csv')
    events=read_csv(path/'events.csv');months=read_csv(path/'monthly.csv')
    end,anchor=s['latest_end'],s['monthly_end']
    terminal={};purchases=defaultdict(float);costs=defaultdict(float);redemptions=defaultdict(float)
    for h in holdings:
        t=h['ticker']
        if h['date']==anchor and t!='CASH':
            factor=(inp.daily_price(t,end)/inp.daily_price(t,anchor)
                    *inp.conversion(t,end,s['region'])/inp.conversion(t,anchor,s['region'])) if end!=anchor else 1
            terminal[t]=float(h['value'])*factor
    for t in trades:
        purchases[t['ticker']]+=float(t['trade_value']);costs[t['ticker']]+=float(t['cost'])
    for event in events:
        if event['event']!='CASH_DELIST':continue
        date,t=event['date'],event['ticker']
        prior=max(h['date'] for h in holdings if h['ticker']==t and h['date']<date)
        old=next(h for h in holdings if h['ticker']==t and h['date']==prior)
        redemptions[t]+=float(old['value'])*inp.price(t,date,s['region'])/inp.price(t,prior,s['region'])
    rows=[]
    for t,u in inp.universe.items():
        if u['region']!=s['region']:continue
        hs=[h for h in holdings if h['ticker']==t]
        rows.append(dict(run=s['run'],region=s['region'],rule=s['rule'],ticker=t,
                         contribution_pp=terminal.get(t,0)+redemptions[t]-purchases[t]-costs[t],
                         trading_cost_pp=costs[t],delisting_cash=redemptions[t],
                         average_weight=sum(float(h['weight']) for h in hs)/len(months),
                         first_held=min((h['date'] for h in hs),default=''),months_held=len(hs)))
    close(sum(r['contribution_pp'] for r in rows),100*float(s['total_return']))
    return rows


def main():
    events,_=read_research();lam,registry=build_lam()
    summaries=[s for s in read_csv(OUT/'summary.csv') if s['definition']=='direct' and s['window']=='earliest_complete']
    assert len(summaries)==6
    rows=[];inputs=[ROOT/'analyze_pillar2.py',OUT/'summary.csv',OUT/'input_manifest.json',OUT/'preserved_manifest.json']
    for region in ('US','EU'):
        inp=PolicyInputs(region,'source','direct',events,lam,registry)
        for s in summaries:
            if s['region']!=region:continue
            rows+=stock_attribution(s,inp)
            inputs += [OUT/s['run']/(name+'.csv') for name in ('holdings','trades','events','monthly')
                       if (OUT/s['run']/(name+'.csv')).exists()]
    relative=[];weights=[]
    for region in ('US','EU'):
        control={r['ticker']:r for r in rows if r['region']==region and r['rule']=='equal'}
        for rule in ('q50','q75','equal'):
            own=[r for r in rows if r['region']==region and r['rule']==rule]
            weights.append(dict(region=region,rule=rule,semiconductor_average_weight=sum(r['average_weight'] for r in own if r['ticker'] in SEMIS)))
            if rule=='equal':continue
            for r in own:
                relative.append(dict(region=region,rule=rule,ticker=r['ticker'],
                                     difference_pp=r['contribution_pp']-control[r['ticker']]['contribution_pp']))
            s=next(s for s in summaries if s['region']==region and s['rule']==rule)
            close(sum(r['difference_pp'] for r in relative if r['region']==region and r['rule']==rule),
                  float(s['vs_fixed_policy_control_pp']))
    write_csv(OUT/'stock_attribution.csv',rows);write_csv(OUT/'relative_stock_attribution.csv',relative)
    write_csv(OUT/'semiconductor_weights.csv',weights)
    first=min(s['start'] for s in summaries);last=max(s['latest_end'] for s in summaries)
    by_stock={(r['region'],r['rule'],r['ticker']):r for r in rows}
    bloom=[by_stock['US',rule,'BE'] for rule in ('equal','q50','q75')]
    def contributors(region,positive):
        candidates=[r for r in relative if r['region']==region and r['rule']=='q75'
                    and (r['difference_pp']>0 if positive else r['difference_pp']<0)]
        largest=sorted(candidates,key=lambda r:abs(r['difference_pp']),reverse=True)[:3]
        return ', '.join(f"{r['ticker']} ({r['difference_pp']:+.2f}pp)" for r in largest) or 'none'
    lines=['# Why the US and EU selection results differ','',
           f'Any prior public support screen, direct/subsidiary definition; {first}–{last}. '
           'The same accounting screen produces different exposure and timing in two different company pools.','',
           '## US','',
           'Bloom’s additive profit contributions are '+
           ', '.join(f"{r['rule'].upper()} {r['contribution_pp']:+.2f}pp" for r in bloom)+
           '. Its first holding dates are '+
           ', '.join(f"{r['rule'].upper()} {r['first_held'] or 'never held'}" for r in bloom)+'. '
           'The largest negative US Q75/control differences are '+contributors('US',False)+'. '
           'These numbers describe the existing accounting strategy, not the alternative trend or momentum scores.','',
           '## EU','',
           'The largest positive EU Q75/control differences are '+contributors('EU',True)+
           '; the largest negative differences are '+contributors('EU',False)+'. '
           'The contribution table reflects selection, weights, timing and the wealth already accumulated by each portfolio.','',
           '## Largest stock contributions to each regional Q75/control gap','',
           'Positive numbers favor the strategy; negative numbers favor equal weight. Q50 is shown for the same names.','',
           '| Region | Stock | Q50 minus equal weight | Q75 minus equal weight |','|---|---|---:|---:|']
    for region in ('US','EU'):
        leaders=sorted((r for r in relative if r['region']==region and r['rule']=='q75'),
                       key=lambda r:abs(r['difference_pp']),reverse=True)[:5]
        for r in leaders:
            q50=next(x for x in relative if x['region']==region and x['rule']=='q50' and x['ticker']==r['ticker'])
            lines.append(f"| {region} | {r['ticker']} | {q50['difference_pp']:+.2f}pp | {r['difference_pp']:+.2f}pp |")
    lines+=['','## Concentration','',
            '| Region | Q50 mean semiconductor weight | Q75 | Equal weight |','|---|---:|---:|---:|']
    for region in ('US','EU'):
        w={r['rule']:r['semiconductor_average_weight'] for r in weights if r['region']==region}
        lines.append(f"| {region} | {w['q50']:.1%} | {w['q75']:.1%} | {w['equal']:.1%} |")
    lines+=['','The score is based on reported operating profitability and cash earnings quality, not a forecast '
            'of the next share-price recovery. A stock can appreciate before those accounts improve. '
            'Concentration makes those selection and timing differences larger. These results do not establish '
            'a durable geographic advantage for the rule.','',
            '## Accounting and interpretation','',
            'For each stock: terminal value plus delisting cash proceeds minus net purchases minus its trading costs. '
            'Starting NAV is 100, so one NAV unit is one return percentage point. Euro portfolios include the final '
            'currency conversion; EDF delisting proceeds are included explicitly. Contributions sum to each '
            'portfolio return, and their differences sum to each strategy/control gap.','',
            'These are additive profit contributions along the actual portfolio paths. They include allocation, '
            'entry/exit timing and the effect of different portfolio wealth over time. They are not isolated '
            'causal effects or the result of rerunning without a stock. Average weights include zero exposure '
            'in months when a stock was not held and include initial deployment.','',
            '[All stock contributions](stock_attribution.csv) · [Relative contributions](relative_stock_attribution.csv) · '
            '[Weights](semiconductor_weights.csv) · [Main results](REPORT.md).','']
    (OUT/'ATTRIBUTION.md').write_text('\n'.join(lines))
    save(OUT/'attribution_validation.json',dict(status='PASS',portfolio_return_reconciliations=6,
         relative_gap_reconciliations=4,inputs=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in inputs]))
    print('PASS: all six portfolio returns and four strategy/control gaps reconcile by stock')


if __name__=='__main__':main()
