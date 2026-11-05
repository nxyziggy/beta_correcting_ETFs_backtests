#!/usr/bin/env python3
"""Run frozen actual-date experiments. Standard-library Python, offline."""
import argparse, datetime as dt, json
from pathlib import Path
from backtest import Inputs, read_csv, run
from prepare_data import ROOT, DATA, write_csv

ORIGINAL_NINE={'AMAT','ASML','ENPH','INTC','LIN','MCHP','MU','NEE','TXN'}
PANELS=('annual','original9','expanded')

class ActualInputs(Inputs):
    def __init__(self):
        super().__init__()
        self.annual=read_csv(DATA/'financials_actual_annual.csv')
        self.all_interim=read_csv(DATA/'financials_actual_quarterly.csv')
        self.primary=[];self.quarterly=[]
        assert self.annual and self.all_interim
        assert all(r['panel'].startswith('actual_original') for r in self.annual+self.all_interim)
        self.timing='actual'
    def available(self,record,annual_lag):
        actual=dt.date.fromisoformat(record['availability_date'])
        if self.timing=='delayed':
            lag=180 if record['period_type']=='annual' else 90
            return max(actual,dt.date.fromisoformat(record['period_end'])+dt.timedelta(days=lag))
        return actual
    def signals(self,region,date,panel,gate=False,annual_lag=0):
        self.timing,coverage=panel.split('_',1)
        self.quarterly=[] if coverage=='annual' else [r for r in self.all_interim if coverage=='expanded' or r['ticker'] in ORIGINAL_NINE]
        return super().signals(region,date,'annual' if coverage=='annual' else 'hybrid',False,0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='results_actual');args=ap.parse_args()
    out=Path(args.output);out=out if out.is_absolute() else ROOT/out;out.mkdir(parents=True,exist_ok=True)
    inputs=ActualInputs();runs=[];failures=[]
    baseline=read_csv(ROOT/'baseline_1to9/results_final/summary.csv')
    old_main=[s for s in baseline if s['panel'] in ('annual','hybrid') and s['annual_lag_days']=='180'
        and s['price_policy']=='dated_daily_overlap' and s['documented_policy_gate']=='False'
        and not s['requested_start'] and float(s['cost_bps'])==(10 if s['region']=='US' else 15)]
    def execute(region,panel,rule,cost,start,window):
        try:r=run(inputs,region,panel,rule,cost,annual_lag=0,start=start)
        except ValueError as e:
            failures.append(dict(region=region,panel=panel,rule=rule,start=start or '',window=window,reason=str(e)));return None
        if r:
            r['summary'].update(window=window,timing=panel.split('_')[0],financial_coverage=panel.split('_',1)[1])
            runs.append(r)
        return r
    # Run every predeclared panel; no choice is made using its portfolio return.
    starts={}
    for region,cost in [('US',10),('EU',15)]:
        first=[]
        for timing in ('actual','delayed'):
            for coverage in PANELS:
                for rule in ('q75','q50','equal'):
                    r=execute(region,timing+'_'+coverage,rule,cost,None,'earliest')
                    if r:first.append(r['summary']['start'])
        assert len(first)==18,('An earliest panel was infeasible',failures)
        # Matched date includes the inherited reference's start, preserving comparability.
        start=max(first+[s['start'] for s in old_main if s['region']==region])
        starts[region]=start
        for timing in ('actual','delayed'):
            for coverage in PANELS:
                for rule in ('q75','q50','equal'):
                    execute(region,timing+'_'+coverage,rule,cost,start,'matched')
        # A second common date allows direct cross-region comparisons.
    cross_start=max(starts.values())
    for region,cost in [('US',10),('EU',15)]:
        for coverage in PANELS:
            for rule in ('q75','q50','equal'):
                execute(region,'actual_'+coverage,rule,cost,cross_start,'cross_region')
        for cost_multiplier in (0,2):
            for rule in ('q75','q50','equal'):
                execute(region,'actual_expanded',rule,cost*cost_multiplier,starts[region],'cost_sensitivity')
    legacy=Inputs()
    for region,cost in [('US',10),('EU',15)]:
        for panel in ('annual','hybrid'):
            for rule in ('q75','q50','equal'):
                r=run(legacy,region,panel,rule,cost,start=starts[region])
                r['summary'].update(window='legacy_matched',timing='inherited_vendor',financial_coverage=panel)
                runs.append(r)
    # Run key identifies the full experiment, including an explicitly named window.
    for r in runs:r['summary']['run']+='_'+r['summary']['window']
    summaries=[r['summary'] for r in runs];lookup={s['run']:s for s in summaries}
    for s in summaries:
        c=lookup[s['run'].replace('_'+s['rule']+'_','_equal_')]
        s['covered_universe_return']=c['total_return']
        s['selection_return_ratio']=(1+s['total_return'])/(1+c['total_return'])-1
    for r in runs:
        for kind,rows in r.items():
            if kind!='summary':write_csv(out/r['summary']['run']/(kind+'.csv'),rows)
    write_csv(out/'summary.csv',summaries)
    write_csv(out/'fx_valuation_audit.csv',list(inputs.fx_log.values()))
    write_csv(out/'price_source_bridge.csv',inputs.price_bridge)
    write_csv(out/'daily_observation_audit.csv',[inputs.extension_quotes[k] for k in sorted(inputs.extension_quotes)])
    (out/'run_metadata.json').write_text(json.dumps(dict(as_of=inputs.extension_config['as_of'],
        complete_month_end=inputs.extension_config['complete_month_end'],runs=len(runs),matched_starts=starts,
        cross_region_start=cross_start,original_quarterly_names=sorted(ORIGINAL_NINE),
        timing_control='max(actual publication date, period end + 180 annual / 90 interim days)',
        failures=failures,source_policy='original observed data only; no vendor fallback',
        limits='Reduced two-factor score, retrospective universe, incomplete original-report coverage; not a certified point-in-time investable index.'),indent=2)+'\n')
    assert not failures,failures
    print(json.dumps([s for s in summaries if s['window']=='matched' and s['timing']=='actual' and s['rule']!='equal'],indent=2))

if __name__=='__main__':main()
