#!/usr/bin/env python3
"""Export requested paper layouts, comparisons and workbook source data."""
import csv, datetime as dt, json
from collections import defaultdict
from pathlib import Path
from backtest import read_csv
from run_actual_dates import ActualInputs
from prepare_data import ROOT, DATA, write_csv

R=ROOT/'results_actual';T=ROOT/'tables_actual'
def typed(rows):
    result=[]
    for row in rows:
        r={}
        for k,v in row.items():
            if v in ('True','False'):r[k]=v=='True'
            elif v=='':r[k]=None
            else:
                try:r[k]=float(v) if any(c in v for c in '.eE') else int(v)
                except (ValueError,TypeError):r[k]=v
        result.append(r)
    return result
def rows(path):return typed(read_csv(path))
def export(name,data):
    write_csv(T/(name+'.csv'),data)
def tex(name,data,percentage=()):
    if not data:return
    esc=lambda s:str(s).replace('&',r'\&').replace('_',r'\_').replace('%',r'\%').replace('#',r'\#')
    def cell(k,v,row):
        if v is None:return 'n.a.'
        is_percent=k in percentage or any(x in row.get('Metric','') for x in ('Return','Alpha','Drawdown'))
        if isinstance(v,(float,int)) and not isinstance(v,bool):return esc(f'{v:.2%}' if is_percent else f'{v:.2f}')
        return esc(v)
    keys=list(data[0]);lines=[r'\begin{longtable}{'+'l'*len(keys)+'}', ' & '.join(map(esc,keys))+r' \\',r'\hline']
    lines+=[' & '.join(cell(k,r.get(k),r) for k in keys)+r' \\' for r in data];lines+=[r'\end{longtable}']
    (T/(name+'.tex')).write_text('\n'.join(lines)+'\n')
def main():
    T.mkdir(exist_ok=True);ss=rows(R/'summary.csv');meta=json.loads((R/'run_metadata.json').read_text())
    lookup={(s['region'],s['panel'],s['rule'],s['window'],s['cost_bps']):s for s in ss}
    def get(region,panel,rule,window='matched',cost=None):return lookup[(region,panel,rule,window,cost if cost is not None else (10 if region=='US' else 15))]
    mainrows=[s for s in ss if s['window']=='matched' and s['timing']=='actual' and s['rule']!='equal']
    compact=[]
    for s in mainrows:
        ms=rows(R/s['run']/'monthly.csv')
        compact.append(dict(Region=s['region'],Panel=s['financial_coverage'],Entry=s['rule'].upper(),Start=s['start'],End=s['latest_end'],
            Total_return=s['total_return'],CAGR=s['CAGR'],Monthly_drawdown=s['max_drawdown_monthly'],
            ETF_benchmark=s['benchmark_return'],Covered_universe_control=s['covered_universe_return'],
            Minimum_holdings=s['min_observed_holdings'],Maximum_holdings=s['max_observed_holdings'],Final_holdings=s['final_holdings'],
            Minimum_coverage=min(m['CoveredUniverse'] for m in ms),Maximum_coverage=max(m['CoveredUniverse'] for m in ms)))
    export('01_Matched_Performance',compact)
    export('02_All_Experiments',ss)
    metrics=[('ETF Total Return','total_return'),('Benchmark Total Return','benchmark_return'),('Cumulative Alpha (relative wealth)','relative_alpha'),
        ('Annualized ETF Return','CAGR'),('Annualized Benchmark Return','benchmark_CAGR'),('Sharpe (arithmetic, rf=0)','Sharpe_rf0_monthly'),
        ('Paper Sharpe (CAGR/volatility)','Paper_CAGR_div_vol'),('Maximum Drawdown (monthly)','max_drawdown_monthly'),
        ('Final ETF NAV','final_NAV'),('Final Benchmark NAV','final_benchmark_NAV'),('Final Holdings','final_holdings')]
    papers=[]
    for panel in ('annual','original9','expanded'):
        a=[s for s in mainrows if s['financial_coverage']==panel]
        data=[dict(Metric=label,**{s['region']+' '+s['rule'].upper():s[k] for s in a}) for label,k in metrics]
        export('Paper_Summary_'+panel,data);tex('Paper_Summary_'+panel,data)
        papers+= [dict(Panel=panel,**d) for d in data]
    export('03_Paper_Summary',papers)
    timing=[];coverage=[];legacy=[]
    for reg in ('US','EU'):
        for rule in ('q75','q50'):
            for panel in ('annual','original9','expanded'):
                a=get(reg,'actual_'+panel,rule);b=get(reg,'delayed_'+panel,rule)
                timing.append(dict(Region=reg,Panel=panel,Entry=rule.upper(),Start=a['start'],Delayed_return=b['total_return'],Actual_date_return=a['total_return'],
                    Change_percentage_points=100*(a['total_return']-b['total_return']),Relative_wealth_change=(1+a['total_return'])/(1+b['total_return'])-1))
            a=get(reg,'actual_original9',rule);b=get(reg,'actual_expanded',rule)
            coverage.append(dict(Region=reg,Entry=rule.upper(),Start=a['start'],Original9_return=a['total_return'],Expanded_return=b['total_return'],
                Change_percentage_points=100*(b['total_return']-a['total_return']),Relative_wealth_change=(1+b['total_return'])/(1+a['total_return'])-1))
            for old,new in [('annual','annual'),('hybrid','expanded')]:
                a=get(reg,old,rule,'legacy_matched');b=get(reg,'actual_'+new,rule)
                legacy.append(dict(Region=reg,Panel=old,Entry=rule.upper(),Start=b['start'],Prior_method_return=a['total_return'],Original_data_return=b['total_return'],
                    Change_percentage_points=100*(b['total_return']-a['total_return']),
                    Interpretation='Joint source, timing and coverage changes; not an isolated timing effect.'))
    export('04_Timing_Effect',timing);export('05_Coverage_Effect',coverage);export('06_Prior_Method_Comparison',legacy)
    quarter=[];monthly=[];scores=[];events=[];holdings=[];attribution=[]
    inp=ActualInputs()
    for s in ss:
        tag=dict(Run=s['run'],Region=s['region'],Panel=s['panel'],Entry=s['rule'].upper(),Window=s['window'])
        qs=rows(R/s['run']/'quarterly.csv')
        paperq=[dict(Quarter=r['quarter'],Date=r['date'],ETF_NAV=r['NAV'],ETF_Cum_Return=r['ETFCumulativeReturn'],
            Bench_NAV=r['BenchmarkNAV'],Bench_Cum_Return=r['BenchCumulativeReturn'],Alpha_ETF_div_Bench_minus1=r['AlphaRatio'],
            Bench_Alpha=0.0,Holdings=r['Holdings'],Partial_quarter=r['partial_quarter']) for r in qs]
        quarter.extend(dict(tag,**r) for r in paperq)
        if s in mainrows:
            name='Paper_Quarterly_'+s['region']+'_'+s['financial_coverage']+'_'+s['rule']
            export(name,paperq);tex(name,paperq,('ETF_Cum_Return','Bench_Cum_Return','Alpha_ETF_div_Bench_minus1','Bench_Alpha'))
            hh=rows(R/s['run']/'holdings.csv');hm=defaultdict(dict)
            for h in hh:hm[h['date']][h['ticker']]=h
            for h in hm[s['monthly_end']].values():
                t=h['ticker'];v=h['value']
                if t!='CASH':v*=inp.daily_price(t,s['latest_end'])/inp.daily_price(t,s['monthly_end'])*inp.conversion(t,s['latest_end'],s['region'])/inp.conversion(t,s['monthly_end'],s['region'])
                holdings.append(dict(tag,Date=s['latest_end'],Ticker=t,Weight=v/s['final_NAV'],Value=v,Last_trade=s['monthly_end']))
            if s['financial_coverage']=='expanded':
                ms=rows(R/s['run']/'monthly.csv');monthly.extend(dict(tag,**r) for r in ms)
                sc=rows(R/s['run']/'scores.csv')
                scores.extend(dict(tag,**r) for r in sc if int(r['date'][5:7]) in (3,6,9,12) or r['date']==s['monthly_end'])
                events.extend(dict(tag,**r) for r in rows(R/s['run']/'events.csv'))
                pnl=defaultdict(float)
                for prev,cur in zip(ms,ms[1:]):
                    for t,h in hm[prev['date']].items():
                        if t!='CASH':pnl[t]+=h['value']*(inp.price(t,cur['date'],s['region'])/inp.price(t,prev['date'],s['region'])-1)
                for t,h in hm[s['monthly_end']].items():
                    if t!='CASH':pnl[t]+=h['value']*(inp.daily_price(t,s['latest_end'])/inp.daily_price(t,s['monthly_end'])*inp.conversion(t,s['latest_end'],s['region'])/inp.conversion(t,s['monthly_end'],s['region'])-1)
                pnl['TRANSACTION_COSTS']=-s['total_cost_NAV_units']
                assert abs(sum(pnl.values())-(s['final_NAV']-100))<1e-8
                attribution.extend(dict(Region=s['region'],Entry=s['rule'].upper(),Ticker=t,Contribution_percentage_points=v) for t,v in sorted(pnl.items(),key=lambda x:-x[1]))
    export('07_All_Quarterly_Performance',quarter);export('08_Expanded_Monthly',monthly);export('09_Expanded_Quarterly_Scores',scores)
    export('10_Expanded_Events',events);export('11_Final_Holdings',holdings);export('12_Expanded_Return_Attribution',attribution)
    financials=rows(DATA/'financials_actual_annual.csv')+rows(DATA/'financials_actual_quarterly.csv')
    counts=json.loads((DATA/'actual_dates/coverage_counts.json').read_text());cov=[]
    for t,u in inp.universe.items():
        c=counts.get(t,{})
        cov.append(dict(Ticker=t,Company=u['name'],Region=u['region'],Original_reports=c.get('original_reports',0),
            Annual_inputs=c.get('annual',0),TTM_inputs=c.get('trailing',0),First_period=c.get('first'),Latest_period=c.get('latest'),
            Status='Verified original inputs captured' if c else 'No complete original dated inputs verified in this reconstruction'))
    export('13_Company_Coverage',cov);export('14_Financial_Inputs',financials)
    validation=json.loads((R/'validation.json').read_text());export('15_Validation',validation['checks'])
    dates=[]
    for r in financials:
        p=dt.date.fromisoformat(r['period_end']);a=dt.date.fromisoformat(r['availability_date']);lag=180 if r['period_type']=='annual' else 90
        delayed=max(a,p+dt.timedelta(days=lag))
        dates.append(dict(Ticker=r['ticker'],Period_end=r['period_end'],Period_type=r['period_type'],Original_publication=r['publication_date'],Actual_availability=a.isoformat(),
            Delayed_availability=delayed.isoformat(),Days_earlier=(delayed-a).days,Source=r['income_source'],Observation_ID=r['observation_id']))
    export('16_Availability_Dates',dates)
    # Every published input is factual. No release narrative or guessed values are bundled.
    observations=json.loads((DATA/'actual_dates/observations_normalized.json').read_text())
    obsflat=[]
    for r in observations:
        f=dict(Ticker=r['ticker'],Fiscal_year=r['fiscal_year'],Fiscal_quarter=r['fiscal_quarter'],Period_end=r['period_end'],Published=r['published'],Currency=r['currency'],Unit=r['unit'])
        for group in ('quarter','annual','ytd','prior_ytd','prior_year_quarter','reported_ttm'):
            for i,key in enumerate(('Operating_income','Net_income','Operating_cash_flow')):f[group+'_'+key]=r.get(group,[None]*3)[i]
        f.update(Total_assets=r['balance'][0],Current_liabilities=r['balance'][1],Source=r['source'],Date_source=r.get('date_source',r['source']),Observation_ID=r['observation_id'])
        obsflat.append(f)
    export('17_Original_Observations',obsflat)
    wb=dict(summary=compact,paper_summary=papers,all_experiments=ss,timing=timing,coverage_effect=coverage,legacy=legacy,
        quarterly=[q for q in quarter if q['Window']=='matched' and q['Panel'].startswith('actual_') and q['Entry']!='EQUAL'],
        monthly=monthly,scores=scores,events=events,holdings=holdings,attribution=attribution,coverage=cov,financials=financials,
        observations=obsflat,dates=dates,validation=validation['checks'],metadata=meta)
    (T/'workbook_data.json').write_text(json.dumps(wb,indent=2)+'\n')
    print(json.dumps(dict(tables=len(list(T.glob('*.csv'))),strategies=len(mainrows),financials=len(financials),source_reports=len(observations),coverage=coverage),indent=2))
if __name__=='__main__':main()
