#!/usr/bin/env python3
"""Independent invariants for real-data source arithmetic and portfolio ledgers."""
import csv, datetime as dt, hashlib, json, math
from collections import defaultdict
from pathlib import Path
from backtest import Inputs, read_csv, run
from prepare_data import ROOT, DATA, write_csv

OUT=ROOT/'results_actual'
def check(condition,message):
    if not condition:raise AssertionError(message)
def close(a,b,tol=1e-8):return abs(float(a)-float(b))<=tol

def main():
    checks=[]
    def passed(name,count,detail):checks.append(dict(check=name,records=count,result='PASS',detail=detail))
    records=json.loads((DATA/'actual_dates/observations_normalized.json').read_text())
    ids={r['observation_id']:r for r in records}
    check(len(ids)==len(records),'Duplicate source observation')
    financials=read_csv(DATA/'financials_actual_annual.csv')+read_csv(DATA/'financials_actual_quarterly.csv')
    for r in financials:
        check(r['panel'].startswith('actual_original'),'Vendor fallback')
        for c in r['component_ids'].split('|'):
            check(c in ids,'Unknown component')
            check(ids[c]['published']<=r['availability_date'],'Future aggregation component')
        check(r['period_end']<r['availability_date'],'Non-positive reporting lag')
        check(float(r['total_assets'])>float(r['current_liabilities'])>0,'Invalid balance')
        check(all(math.isfinite(float(r[k])) for k in ('operating_income','net_income','operating_cash_flow')),'Missing flow')
    passed('Dated original components',len(financials),'All five inputs present; every component published by availability; no vendor fallback.')
    reconciliation=[]
    for r in records:
        if 'annual' not in r:continue
        qs=[next((x for x in records if (x['ticker'],x['fiscal_year'],x['fiscal_quarter'])==(r['ticker'],r['fiscal_year'],q)),None) for q in (1,2,3,4)]
        for k,label in enumerate(('operating_income','net_income','operating_cash_flow')):
            if all(x and x.get('quarter',[None]*3)[k] is not None for x in qs):
                total=sum(x['quarter'][k] for x in qs);diff=total-r['annual'][k]
                tol=.0021 if r['ticker'] in ('LRCX','ENPH') else 2.1
                check(abs(diff)<=tol,('Annual/quarter disagreement',r['ticker'],r['fiscal_year'],label,diff))
                reconciliation.append(dict(ticker=r['ticker'],fiscal_year=r['fiscal_year'],field=label,quarter_sum_million=total,reported_annual_million=r['annual'][k],difference_million=diff,tolerance_million=tol))
    write_csv(OUT/'financial_reconciliation.csv',reconciliation)
    passed('Quarter-to-annual reconciliation',len(reconciliation),'Four observed quarters sum to original annual values within source rounding tolerance.')
    frozen=json.loads((ROOT/'baseline_1to9/INPUT_SHA256.json').read_text());n=0
    for r in frozen:
        path=r['path']
        if any(s in path for s in ('prices','/daily/','fx_','universe.json','extension_config.json')):
            check(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==r['sha256'],('Market input changed',path));n+=1
    passed('Frozen prices, FX and universe',n,'Byte-for-byte unchanged against inherited input hashes.')
    summaries=read_csv(OUT/'summary.csv');n_scores=n_months=n_trades=0
    for s in summaries:
        folder=OUT/s['run'];ms=read_csv(folder/'monthly.csv');hs=read_csv(folder/'holdings.csv')
        grouped=defaultdict(list)
        for h in hs:grouped[h['date']].append(h)
        trades=read_csv(folder/'trades.csv');tg=defaultdict(list)
        for t in trades:tg[t['date']].append(t);n_trades+=1
        for m in ms:
            n_months+=1;day=m['date'];hold=grouped[day]
            check(close(sum(float(h['weight']) for h in hold),1),'Weights do not sum to 1')
            check(close(sum(float(h['value']) for h in hold),m['NAV']),'NAV does not equal positions')
            check(close(float(m['PreTradeNAV'])-float(m['Cost']),m['NAV']),'Transaction cost conservation')
            check(close(sum(float(t['cost']) for t in tg[day]),m['Cost']),'Trade costs do not reconcile')
            check(close(float(m['TradedNotional'])*float(s['cost_bps'])/10000,m['Cost']),'Cost rate')
            count=sum(h['ticker']!='CASH' and float(h['value'])>0 for h in hold)
            if s['rule']!='equal':check(1<=count<=9,'Holdings out of bounds')
            check(count==int(m['Holdings']),'Holding count')
        ds=[dt.date.fromisoformat(m['date']) for m in ms]
        check(all((b.year-a.year)*12+b.month-a.month==1 for a,b in zip(ds,ds[1:])),'Monthly gap')
        if s['timing']!='inherited_vendor':
            for sc in read_csv(folder/'scores.csv'):
                n_scores+=1
                check(sc['available_used']<sc['information_cutoff'],'Lookahead at rebalance')
                check(sc['observation_id'] in ids,'Untraceable score')
                check(sc['source_panel'].startswith('actual_original'),'Non-original score input')
                for component in sc['component_ids'].split('|'):
                    check(ids[component]['published']<sc['information_cutoff'],'Future component in score')
                age=(dt.date.fromisoformat(sc['date'])-dt.date.fromisoformat(sc['report_period'])).days
                check(age<=(550 if sc['period_type']=='annual' else 275),'Stale score')
        check(s['latest_end']=='2026-11-02','Incomplete endpoint')
        check(close(float(s['final_NAV'])/100-1,s['total_return']),'Summary return')
    passed('Information cutoff and freshness',n_scores,'Every source component strictly predates the first day of the decision month; 550/275-day age limits.')
    passed('Monthly portfolio accounting',n_months,'No monthly gaps; weights, positions, turnover, costs and 1-9 bounds reconcile.')
    passed('Trade cost ledgers',n_trades,'Costs equal specified bps times actual absolute traded value.')
    # Confirm the implementation change did not alter inherited portfolio mechanics.
    legacy=Inputs();old=read_csv(ROOT/'baseline_1to9/results_final/summary.csv');n=0
    for reg,cost in [('US',10),('EU',15)]:
        for panel in ('annual','hybrid'):
            for rule in ('q75','q50','equal'):
                key=f'{reg}_{panel}_{rule}_{cost}bp_lag180'
                expected=next(s for s in old if s['run']==key);actual=run(legacy,reg,panel,rule,cost)['summary']
                for k in ('final_NAV','total_return','CAGR','max_drawdown_monthly','total_cost_NAV_units'):
                    check(close(actual[k],expected[k]),('Inherited replication changed',key,k))
                n+=1
    passed('Inherited result reproduction',n,'Unmodified baseline financial inputs reproduce prior NAV, return, CAGR, drawdown and costs.')
    (OUT/'validation.json').write_text(json.dumps(dict(checks=checks,run_count=len(summaries),known_limits=[
        'Original-report financial coverage exists for 18 of 31 retrospective candidates.',
        'Some reporters/quarters are missing and 23 observed reports cannot form all required trailing flows.',
        'Numerical source verification is not an independent audit of issuer accounts or vendors.',
        'Actual releases reduce timing bias; they do not remove retrospective-universe or historical experiment-selection bias.',
        'Monthly risk statistics do not capture all intramonth drawdowns.']),indent=2)+'\n')
    print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
