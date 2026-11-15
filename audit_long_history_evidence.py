#!/usr/bin/env python3
"""Audit ungated long-history evidence without modifying existing results.

Default: read committed ledgers. --portfolio-sensitivities also reruns the fixed
quarterly starts and all-name omissions in memory. JSON/Markdown goes to stdout;
continuous-position slices and fresh portfolio restarts remain separate.
"""
import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results_long_history'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def active_stats(monthly, control):
    # Initial deployment cost is in total return, but not a monthly observation.
    left, right=monthly[1:],control[1:]
    if [r['date'] for r in left]!=[r['date'] for r in right]:
        raise ValueError('Strategy/control monthly dates differ')
    active=[float(a['PeriodReturn'])-float(b['PeriodReturn']) for a,b in zip(left,right)]
    n=len(active);mean=statistics.mean(active);sd=statistics.stdev(active)
    centered=[value-mean for value in active]
    long_run_variance=sum(value*value for value in centered)/n
    for lag in range(1,4):
        covariance=sum(centered[i]*centered[i-lag] for i in range(lag,n))/n
        long_run_variance+=2*(1-lag/4)*covariance
    standard_error=math.sqrt(max(0,long_run_variance)/(n-1))
    return dict(months=n, mean_monthly_active_pp=100*mean,
                t_iid=mean/(sd/math.sqrt(n)),
                t_newey_west_3=mean/standard_error)


def audit(include_portfolios=False):
    summaries=read_csv(RESULTS/'summary.csv')
    def select(region,rule,window='cross_region',timing='source'):
        matches=[r for r in summaries if r['region']==region and r['rule']==rule
                 and r['window']==window and r['timing']==timing]
        if len(matches)!=1:
            raise ValueError(('Ambiguous or absent run',region,rule,window,timing))
        return matches[0]
    cache={}
    def ledger(summary,name):
        key=summary['run'],name
        if key not in cache:
            cache[key]=read_csv(RESULTS/summary['run']/(name+'.csv'))
        return cache[key]
    main=[];annual=[];age=[];timing=[];continuous=[]
    for region in ('US','EU'):
        control=select(region,'equal');control_monthly=ledger(control,'monthly')
        for rule in ('q50','q75','equal'):
            row=select(region,rule);monthly=ledger(row,'monthly')
            main.append(dict(region=region,rule=rule,run=row['run'],start=row['start'],end=row['latest_end'],
                             return_pct=100*float(row['total_return']),
                             excess_control_pp=100*(float(row['total_return'])-float(control['total_return'])),
                             sector_etf_benchmark_return_pct=100*float(row['benchmark_return']),
                             **(active_stats(monthly,control_monthly) if rule!='equal' else {})))
            for year in ('2020',):
                value=math.prod(1+float(m['PeriodReturn']) for m in monthly if m['date'].startswith(year))
                annual.append(dict(region=region,rule=rule,year=year,return_pct=100*(value-1)))
            anchor='2020-12-31'
            anchor_nav=next(float(m['NAV']) for m in monthly if m['date']==anchor)
            control_anchor_nav=next(float(m['NAV']) for m in control_monthly if m['date']==anchor)
            value=100*(float(row['final_NAV'])/anchor_nav-1)
            control_value=100*(float(control['final_NAV'])/control_anchor_nav-1)
            continuous.append(dict(region=region,rule=rule,anchor=anchor,end=row['latest_end'],
                                   return_pct=value,control_return_pct=control_value,
                                   excess_control_pp=value-control_value,
                                   interpretation='Continuous-position slice; not a fresh portfolio restart'))
        # Scores are independent of Q50/Q75 holdings; count each stock-month once.
        scores=ledger(select(region,'q50'),'scores')
        if len({(r['date'],r['ticker']) for r in scores})!=len(scores):
            raise ValueError('Duplicate score observations')
        for label,start,end in [('2019_2020','2019-01-01','2020-12-31'),
                                ('2022_onward','2022-01-01','9999-12-31')]:
            subset=[r for r in scores if start<=r['date']<=end]
            ages=[int(r['report_age_days']) for r in subset]
            for r in subset:
                expected=(dt.date.fromisoformat(r['date'])-dt.date.fromisoformat(r['report_period'])).days
                if int(r['report_age_days'])!=expected:
                    raise ValueError('Report age is not measured from accounting period end')
            age.append(dict(region=region,period=label,stock_month_score_observations=len(subset),
                            annual_share_pct=100*sum(r['period_type']=='annual' for r in subset)/len(subset),
                            median_period_end_age_days=statistics.median(ages),
                            age_definition='Portfolio date minus accounting period end, not time since publication'))
        for timing_name in ('source','delay_adjusted'):
            control=select(region,'equal','timing_matched',timing_name)
            for rule in ('q50','q75'):
                row=select(region,rule,'timing_matched',timing_name)
                timing.append(dict(region=region,rule=rule,timing=timing_name,start=row['start'],
                                   return_pct=100*float(row['total_return']),
                                   control_return_pct=100*float(control['total_return']),
                                   excess_control_pp=100*(float(row['total_return'])-float(control['total_return'])),
                                   **active_stats(ledger(row,'monthly'),ledger(control,'monthly'))))
    fx_area=ROOT/'data/long_history/prices'
    capture=json.loads((fx_area/'fx_web_capture.json').read_text())
    additions=read_csv(fx_area/'fx_additions.csv')
    manifest=json.loads((fx_area/'fx_download_manifest.json').read_text())
    captured={(r['series'],r['date']):r['rate'] for r in capture}
    if len(captured)!=len(capture):
        raise ValueError('Duplicate FX capture keys')
    for row in additions:
        if float(row['rate'])!=captured[row['series'],row['date']]:
            raise ValueError('FX supplement differs from capture')
    # Inputs uses the preserved original rates, without the long-history append.
    from backtest import Inputs
    inputs=Inputs();overlap=[]
    for row in capture:
        old=inputs.fx[row['series']].get(row['date'])
        if old is not None:
            if old!=row['rate']:
                raise ValueError('FX overlap differs from frozen original')
            overlap.append(row)
    if len(capture)!=len(additions)+len(overlap):
        raise ValueError('FX addition/overlap counts do not reconcile')
    stock_2020=[dict(ticker=t,start='2019-12-31',end='2020-12-31',
                     return_pct=100*(inputs.price(t,'2020-12-31','US')/inputs.price(t,'2019-12-31','US')-1),
                     source='Frozen adjusted monthly vendor prices') for t in ('ENPH','PLUG','BE')]
    result=dict(scope='Audit of released ungated long-history ledgers; no existing result files modified',
                main_returns_and_active_statistics=main,calendar_2020_returns=annual,
                stock_2020_returns=stock_2020,information_age=age,
                matched_reporting_timing=timing,post_2020_continuous_slices=continuous,
                fx=dict(saved_records=len(capture),new_records=len(additions),matching_original_overlap=len(overlap),
                        first_date=min(r['date'] for r in capture),last_date=max(r['date'] for r in capture),
                        manifest_entries=len(manifest),manifest_failed_entries=sum('error' in r for r in manifest),
                        saved_capture_sha256=hashlib.sha256((fx_area/'fx_web_capture.json').read_bytes()).hexdigest(),
                        limitation='Saved values and attributed FRED URLs do not establish the undocumented original acquisition chain'),
                statistical_limit='Nominal t statistics; no adjustment for multiple variants or hindsight in candidate selection',
                not_verified=['Fourteen fresh quarterly starts','All-name leave-one-out fresh portfolio runs',
                              'December 2020 fresh restart claims'])
    if include_portfolios:
        result['portfolio_sensitivities']=portfolio_sensitivities()
        result['not_verified']=[]
    return result


def portfolio_sensitivities():
    """Fixed starts and whole-universe omissions; no parameter selection or writes."""
    from run_long_history import HistoryInputs,execute
    source_area=ROOT/'data/research_corrections'
    lam=json.loads((source_area/'lam_inputs.json').read_text())
    registry={'lam_source_'+r['period_end']:r for r in json.loads((source_area/'lam_sources.json').read_text())}
    starts=[f'{year}-{suffix}' for year in range(2019,2023)
            for suffix in ('03-31','06-30','09-30','12-31')
            if '2019-06-30'<=f'{year}-{suffix}'<='2022-09-30']
    start_rows=[];omission_rows=[]
    for region in ('US','EU'):
        inputs=HistoryInputs(region,'source',lam,registry)
        def run_rules(dataset,start):
            values={}
            for rule in ('q50','q75','equal'):
                result=execute(dataset,region,'review_sensitivity',rule,start,'in_memory_only')
                if result['summary']['start']!=start:
                    raise ValueError('Sensitivity silently changed requested start')
                values[rule]=100*result['summary']['total_return']
            return values
        for start in starts:
            values=run_rules(inputs,start)
            for rule in ('q50','q75'):
                start_rows.append(dict(region=region,rule=rule,start=start,
                                       return_pct=values[rule],control_return_pct=values['equal'],
                                       excess_control_pp=values[rule]-values['equal']))
        for ticker in sorted(t for t,u in inputs.universe.items() if u['region']==region):
            reduced=copy.copy(inputs)
            reduced.universe={t:u for t,u in inputs.universe.items() if t!=ticker}
            values=run_rules(reduced,'2019-06-30')
            for rule in ('q50','q75'):
                omission_rows.append(dict(region=region,rule=rule,omitted=ticker,
                                          return_pct=values[rule],control_return_pct=values['equal'],
                                          excess_control_pp=values[rule]-values['equal']))
    return dict(definition='Ungated source-date inputs; fixed original costs, listing rules and endpoint. Fresh portfolios at each start. Each omission removes the company from both score-ranking universe and equal-weight control.',
                fresh_quarterly_starts=start_rows,whole_universe_leave_one_out=omission_rows)


def markdown_report(result):
    lines=['# Long-history review diagnostics','',
           'Reproduce without changing existing result ledgers: `python3 audit_long_history_evidence.py --portfolio-sensitivities --format markdown`. The JSON form retains every individual restart and omission. These checks use the ungated accounting-data experiment, not the separate historical public-support screen.','',
           '## Start dates and omitted companies','']
    sensitivities=result.get('portfolio_sensitivities')
    if sensitivities:
        lines += [sensitivities['definition'],'',
                  '| Region | Rule | Fresh starts leading / tested | Omission runs leading / tested | Omission excess range |',
                  '|---|---|---:|---:|---:|']
        for region in ('US','EU'):
            for rule in ('q50','q75'):
                starts=[r for r in sensitivities['fresh_quarterly_starts'] if r['region']==region and r['rule']==rule]
                omitted=[r for r in sensitivities['whole_universe_leave_one_out'] if r['region']==region and r['rule']==rule]
                values=[r['excess_control_pp'] for r in omitted]
                lines.append(f"| {region} | {rule.upper()} | {sum(r['excess_control_pp']>0 for r in starts)}/{len(starts)} | {sum(v>0 for v in values)}/{len(values)} | {min(values):+.2f} to {max(values):+.2f}pp |")
        us_flips=[r for r in sensitivities['whole_universe_leave_one_out'] if r['region']=='US' and r['excess_control_pp']>0]
        if us_flips:
            lines += ['', 'US omissions producing a lead: '+', '.join(f"{r['rule'].upper()} without {r['omitted']} ({r['excess_control_pp']:+.2f}pp)" for r in us_flips)+'.']
        lines += ['', 'Starts are the 14 quarter-ends from June 2019 through September 2022. These overlapping tests are sensitivity checks, not 14 independent confirmations. Omitting a company also changes relative ranks; this is not additive return attribution.','',
                  '| Region | Rule | Fresh December 2020 excess | Continuous post-December 2020 excess |',
                  '|---|---|---:|---:|']
        for continuous in result['post_2020_continuous_slices']:
            if continuous['rule']=='equal':
                continue
            fresh=next(r for r in sensitivities['fresh_quarterly_starts'] if r['region']==continuous['region'] and r['rule']==continuous['rule'] and r['start']=='2020-12-31')
            lines.append(f"| {fresh['region']} | {fresh['rule'].upper()} | {fresh['excess_control_pp']:+.2f}pp | {continuous['excess_control_pp']:+.2f}pp |")
    else:
        lines += ['Fresh-start and leave-one-out claims were not checked in this ledger-only invocation.']
    lines += ['', 'The continuous slice retains positions and prior review history; a fresh restart deploys new portfolios. The two answer different questions and can have different signs.','',
              '## 2020 and information age','',
              '| Region | Q50 in 2020 | Q75 in 2020 | Equal weight in 2020 |','|---|---:|---:|---:|']
    for region in ('US','EU'):
        values={r['rule']:r['return_pct'] for r in result['calendar_2020_returns'] if r['region']==region}
        lines.append(f"| {region} | {values['q50']:.2f}% | {values['q75']:.2f}% | {values['equal']:.2f}% |")
    stocks={r['ticker']:r['return_pct'] for r in result['stock_2020_returns']}
    lines += ['',f"The 2020 US control included Enphase ({stocks['ENPH']:.2f}%), Plug Power ({stocks['PLUG']:.2f}%) and Bloom ({stocks['BE']:.2f}%). These are individual adjusted-price returns, not additive portfolio contributions.",'',
              '| Region | Score window | Annual share | Median period-end age |','|---|---|---:|---:|']
    for row in result['information_age']:
        lines.append(f"| {row['region']} | {row['period']} | {row['annual_share_pct']:.2f}% | {row['median_period_end_age_days']:.0f} days |")
    lines += ['', 'Each stock-month score counts once. Age runs from accounting period end to portfolio date, not publication. The 2022-onward median is about four months; the review’s three-month description is not reproduced under this definition.','',
              '## Statistics and common reporting delay','',
              '| Region | Rule | Monthly iid t | Newey–West t, 3 lags |','|---|---|---:|---:|']
    for row in result['main_returns_and_active_statistics']:
        if row['rule']!='equal':
            lines.append(f"| {row['region']} | {row['rule'].upper()} | {row['t_iid']:+.2f} | {row['t_newey_west_3']:+.2f} |")
    pair={r['timing']:r for r in result['matched_reporting_timing'] if r['region']=='EU' and r['rule']=='q75'}
    lines += ['',f"With the identical matched-window control, delaying reports and extending freshness reduces EU Q75 excess from {pair['source']['excess_control_pp']:.2f}pp to {pair['delay_adjusted']['excess_control_pp']:.2f}pp; iid t falls from {pair['source']['t_iid']:.2f} to {pair['delay_adjusted']['t_iid']:.2f}.",'',
              'Monthly statistics exclude the deployment row and terminal partial month. They use 88 monthly observations in the main window and 85 in the matched window. These nominal tests do not account for multiple strategies examined or retrospective candidate selection.','',
              '## Computational and source provenance','',
              '`python3 collect_long_history_us.py --check` rebuilds all 73 released normalized rows from committed accession-level evidence and explicit manual inputs. Full original SEC response bodies are not committed; their reacquisition is not reproduced by this check.','',
              f"FX has {result['fx']['saved_records']:,} saved records, {result['fx']['matching_original_overlap']:,} exact overlaps and {result['fx']['new_records']:,} additions. All four manifest entries are failed requests. The saved series-page URLs and overlap consistency do not establish the missing original acquisition chain or independently validate the additions.",'',
              'No financial inputs, scores, default portfolio rules or published return ledgers are changed by this audit.','']
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portfolio-sensitivities',action='store_true')
    parser.add_argument('--format',choices=('json','markdown'),default='json')
    args=parser.parse_args()
    result=audit(include_portfolios=args.portfolio_sensitivities)
    print(markdown_report(result) if args.format=='markdown' else json.dumps(result,indent=2))
