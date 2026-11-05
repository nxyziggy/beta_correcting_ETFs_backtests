#!/usr/bin/env python3
"""Build auditable annual/TTM inputs using only dated original observations.

No annualization, interpolation, mock data, or revised vendor-history fallback.
This program is standard-library-only and works offline.
"""
import csv, datetime as dt, hashlib, json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; AREA=DATA/'actual_dates'
AS_OF='2026-11-02'
FLOW_NAMES=['operating_income','net_income','operating_cash_flow']
CSV_FIELDS=['ticker','period_end','fiscal_label','panel','period_type','publication_date','availability_date','availability_basis','currency','unit',*FLOW_NAMES,'total_assets','current_liabilities','prior_total_assets','prior_current_liabilities','income_source','balance_source','cashflow_source','observation_id','component_ids']

def read_csv(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))

def write_csv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=CSV_FIELDS);w.writeheader();w.writerows(rows)

def identifier(r):
    key='|'.join(str(r.get(k,'')) for k in ['ticker','fiscal_year','fiscal_quarter','period_end','published','source'])
    return hashlib.sha256(key.encode()).hexdigest()[:20]

def load_observations():
    records=json.loads((AREA/'parsed_observations.json').read_text())
    manual=json.loads((AREA/'reviewed_observations.json').read_text())
    for r in manual:
        same=[a for a in records if (a['ticker'],a['fiscal_year'],a['fiscal_quarter'])==(r['ticker'],r['fiscal_year'],r['fiscal_quarter'])]
        if same:
            for k in ['annual','balance','published','period_end']:
                if k in r and k in same[0]:assert r[k]==same[0][k],('Reviewed/parsed disagreement',r['ticker'],k)
        else:records.append(r)
    for r in read_csv(DATA/'financials_supplement.csv'):
        # This inherited Infineon item used an assumed AGM date, not an evidenced release.
        if r['ticker']=='IFX.DE':continue
        y=int(r['fiscal_label'].split()[-1])
        if any(a['ticker']==r['ticker'] and a['fiscal_year']==y and a['fiscal_quarter']==4 for a in records):continue
        records.append(dict(ticker=r['ticker'],fiscal_year=y,fiscal_quarter=4,period_end=r['period_end'],published=r['availability_date'],currency=r['currency'],unit=r['unit'],annual=[float(r[k]) for k in FLOW_NAMES],quarter=[None]*3,balance=[float(r[k]) for k in ['total_assets','current_liabilities']],source=r['income_source'],cashflow_source=r['cashflow_source'],balance_source=r['balance_source'],inherited_original_supplement=True))
    result=[]
    for r in records:
        if r['published']>AS_OF:continue
        assert r['period_end']<r['published'],r
        assert len(r['balance'])==2 and all(v is not None for v in r['balance']),r
        r['observation_id']=identifier(r)
        # A common unit prevents mixing thousands and millions across observations.
        factor={'million':1.0,'thousand':0.001}[r['unit']]
        for k in ['balance','quarter','annual','ytd','prior_ytd','prior_year_quarter','reported_ttm']:
            if k in r:r[k]=[None if v is None else v*factor for v in r[k]]
        r['unit']='million';result.append(r)
    return sorted(result,key=lambda r:(r['ticker'],r['published'],r['period_end']))

def build(records):
    by_t=defaultdict(list)
    for r in records:by_t[r['ticker']].append(r)
    rows=[];audit=[];missing=[]
    for current in records:
        t=current['ticker'];y=current['fiscal_year'];q=current['fiscal_quarter']
        known=[r for r in by_t[t] if r['published']<=current['published']]
        annual=[r for r in known if r['fiscal_year']==y-1 and 'annual' in r]
        prev=max(annual,key=lambda r:r['published']) if annual else None
        # Same reporting currency is required within every aggregation.
        assert all(r['currency']==current['currency'] for r in known),t
        details=[];values=[];used={current['observation_id']:current}
        if 'annual' in current:
            values=current['annual'];kind='annual'
            details=[dict(field=f,method='original annual figure',value=v,components=[current['observation_id']]) for f,v in zip(FLOW_NAMES,values)]
        else:
            kind='trailing'
            for k,name in enumerate(FLOW_NAMES):
                value=None;components=[];method=''
                if current.get('reported_ttm',[None]*3)[k] is not None:
                    value=current['reported_ttm'][k];components=[current];method='issuer-reported trailing twelve months'
                elif prev and current.get('ytd',[None]*3)[k] is not None and current.get('prior_ytd',[None]*3)[k] is not None:
                    value=prev['annual'][k]+current['ytd'][k]-current['prior_ytd'][k];components=[prev,current];method='prior annual + current YTD - prior-year YTD'
                elif prev:
                    year_quarters=[]
                    for qq in range(1,q+1):
                        candidates=[r for r in known if r['fiscal_year']==y and r['fiscal_quarter']==qq and r.get('quarter',[None]*3)[k] is not None and r.get('prior_year_quarter',[None]*3)[k] is not None]
                        if candidates:year_quarters.append(max(candidates,key=lambda r:r['published']))
                    if len(year_quarters)==q:
                        value=prev['annual'][k]+sum(r['quarter'][k]-r['prior_year_quarter'][k] for r in year_quarters)
                        components=[prev,*year_quarters];method='prior annual + observed current quarters - contemporaneous comparative quarters'
                if value is None:
                    seq=[]
                    for index in range(y*4+q-3,y*4+q+1):
                        fy,fq=divmod(index-1,4);fq+=1
                        candidates=[r for r in known if (r['fiscal_year'],r['fiscal_quarter'])==(fy,fq) and r.get('quarter',[None]*3)[k] is not None]
                        if candidates:seq.append(max(candidates,key=lambda r:r['published']))
                    if len(seq)==4:
                        value=sum(r['quarter'][k] for r in seq);components=seq;method='four observed consecutive fiscal quarters'
                values.append(value)
                details.append(dict(field=name,method=method or 'unavailable',value=value,components=[r['observation_id'] for r in components]))
                used.update({r['observation_id']:r for r in components})
            if any(v is None for v in values):
                missing.append(dict(observation_id=current['observation_id'],ticker=t,period_end=current['period_end'],published=current['published'],missing_fields=[f for f,v in zip(FLOW_NAMES,values) if v is None]))
                continue
        available=max(r['published'] for r in used.values())
        assert available==current['published'],('Aggregation used future information',current)
        prior_balance=[r for r in known if (r['fiscal_year'],r['fiscal_quarter'])==(y-1,q)]
        pb=max(prior_balance,key=lambda r:r['published'])['balance'] if prior_balance else [None,None]
        row=dict(ticker=t,period_end=current['period_end'],fiscal_label=f'FY {y}' if kind=='annual' else f'TTM through fiscal Q{q} {y}',panel='actual_original_'+kind,period_type=kind,publication_date=current['published'],availability_date=available,availability_basis='evidenced original release; latest date of every arithmetic component',currency=current['currency'],unit='million',**dict(zip(FLOW_NAMES,values)),total_assets=current['balance'][0],current_liabilities=current['balance'][1],prior_total_assets=pb[0] if pb[0] is not None else '',prior_current_liabilities=pb[1] if pb[1] is not None else '',income_source=current['source'],balance_source=current.get('balance_source',current['source']),cashflow_source=current.get('cashflow_source',current['source']),observation_id=current['observation_id'],component_ids='|'.join(sorted(used)))
        rows.append(row)
        audit.append(dict(observation_id=current['observation_id'],ticker=t,period_end=current['period_end'],available=available,calculations=details,balance_source_id=current['observation_id']))
    return rows,audit,missing

def main():
    records=load_observations();rows,audit,missing=build(records)
    write_csv(DATA/'financials_actual_annual.csv',[r for r in rows if r['period_type']=='annual'])
    write_csv(DATA/'financials_actual_quarterly.csv',[r for r in rows if r['period_type']=='trailing'])
    for name,value in [('observations_normalized',records),('calculation_audit',audit),('ttm_exclusions',missing)]:
        (AREA/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    counts={}
    for t in sorted({r['ticker'] for r in records}):
        a=[r for r in rows if r['ticker']==t]
        counts[t]=dict(original_reports=sum(r['ticker']==t for r in records),annual=sum(r['period_type']=='annual' for r in a),trailing=sum(r['period_type']=='trailing' for r in a),first=min((r['period_end'] for r in a),default=None),latest=max((r['period_end'] for r in a),default=None))
    (AREA/'coverage_counts.json').write_text(json.dumps(counts,indent=2)+'\n')
    print(json.dumps(dict(original_reports=len(records),complete_financial_observations=len(rows),incomplete_trailing_calculations=len(missing),coverage=counts),indent=2))

if __name__=='__main__':main()
