#!/usr/bin/env python3
"""Recover accession-specific SEC annual/YTD facts for FSLR and PLUG.

Offline input: sibling us_source_reports/solar_fuel/{ticker}_{companyfacts,submissions}.json.
Only original form 10-K/10-Q current-period filings enter this panel.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT.parent/'us_source_reports'/'solar_fuel'
AREA=ROOT/'data'/'us_restoration'
FLOWS=('operating_income','net_income','operating_cash_flow')
TAGS={'operating_income':'OperatingIncomeLoss','operating_cash_flow':'NetCashProvidedByUsedInOperatingActivities','total_assets':'Assets','current_liabilities':'LiabilitiesCurrent'}
annual=[];interim=[];evidence=[];checks=[];source_files=[]
for t,cik in [('FSLR',1274494),('PLUG',1093691)]:
    facts_path=RAW/(t+'_companyfacts.json');subs_path=RAW/(t+'_submissions.json')
    data=json.loads(facts_path.read_text())['facts']['us-gaap']
    subs=json.loads(subs_path.read_text())['filings']['recent']
    for p,url in [(facts_path,f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'),(subs_path,f'https://data.sec.gov/submissions/CIK{cik:010d}.json')]:
        source_files.append(dict(ticker=t,filename=p.name,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    filings=[{k:subs[k][i] for k in ['form','reportDate','filingDate','accessionNumber','primaryDocument']} for i in range(len(subs['form'])) if subs['form'][i] in ('10-K','10-Q')]
    def filing(end,form):
        choices=sorted([r for r in filings if r['reportDate']==end and r['form']==form],key=lambda r:r['filingDate'])
        assert choices,(t,end,form)
        return choices[0]
    def fact(field,f,end,start=None):
        tags=(['ProfitLoss','NetIncomeLoss'] if t=='PLUG' else ['NetIncomeLoss']) if field=='net_income' else [TAGS[field]]
        for tag in tags:
            rs=[r for r in data.get(tag,{}).get('units',{}).get('USD',[]) if r['accn']==f['accessionNumber'] and r['end']==end and r.get('start')==start]
            if rs:
                assert len({r['val'] for r in rs})==1,(t,field,f,rs)
                r=rs[0];assert r['filed']==f['filingDate']
                e=dict(field=field,concept='us-gaap:'+tag,unit='USD',**r)
                return r['val']/1e6,e
        raise ValueError((t,field,f,end,start))
    def flows(f,end):
        a={};ev={}
        for field in FLOWS:
            a[field],ev[field]=fact(field,f,end,end[:4]+'-01-01')
        return a,ev
    def meta(f):
        url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accessionNumber'].replace('-','')}/{f['primaryDocument']}"
        index=f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accessionNumber']}-index.html"
        return dict(ticker=t,period_end=f['reportDate'],publication_date=f['filingDate'],availability_date=f['filingDate'],currency='USD',unit='million',income_source=url,balance_source=url,cashflow_source=url,date_source=index,accession=f['accessionNumber'],availability_basis='Conservative original SEC 10-K/10-Q filing date; no earlier earnings-release timing assumed')
    aa={}
    for y in range(2021,2026):
        f=filing(f'{y}-12-31','10-K');r=meta(f);v,ev=flows(f,f['reportDate']);r.update(v)
        for field in ['total_assets','current_liabilities']:r[field],ev[field]=fact(field,f,f['reportDate'])
        r['notes']=['Accession-specific current-period facts from original 10-K; subsequent comparative values are not backdated.']
        if t=='PLUG':r['notes'].append('Group net income uses ProfitLoss where noncontrolling interests exist. FY2021 NetIncomeLoss equals group net loss; the original 2021 statement has no separate noncontrolling-interest result, corroborated by the FY2022 group comparative.')
        else:r['notes'].append('NetIncomeLoss is the consolidated net-income line; no separate noncontrolling-interest allocation is reported.')
        r['evidence']=ev;annual.append(r);aa[y]=r
        evidence.append(dict(ticker=t,period_end=f['reportDate'],filing=f,facts=ev))
    periods=[(2022,2),(2022,3)]+[(y,q) for y in range(2023,2026) for q in (1,2,3)]+[(2026,1),(2026,2)]
    for y,q in periods:
        suffix={1:'03-31',2:'06-30',3:'09-30'}[q];end=f'{y}-{suffix}';prior_end=f'{y-1}-{suffix}'
        f=filing(end,'10-Q');r=meta(f);r.update(fiscal_year=y,fiscal_quarter=q,ttm_compatible=True)
        r['ytd'],ev=flows(f,end);r['prior_ytd'],prior_ev=flows(f,prior_end)
        old=filing(prior_end,'10-Q');oldflows,old_ev=flows(old,prior_end)
        assert oldflows==r['prior_ytd'],(t,end,'Comparative basis changed',oldflows,r['prior_ytd'])
        base=aa[y-1]
        r['prior_annual']={k:base[k] for k in [*FLOWS,'period_end','publication_date','availability_date']}
        r['prior_annual'].update(source=base['income_source'],evidence={k:base['evidence'][k] for k in FLOWS})
        for field in ['total_assets','current_liabilities']:r[field],ev[field]=fact(field,f,end)
        r['notes']=['Current and comparative YTD flows selected from the same original 10-Q accession; all three comparative YTD values reconcile to their original prior-year filings.', 'Prior annual uses the already-filed original preceding-year 10-K. No accounting-basis adjustment is required for these selected flows.']
        if t=='PLUG':r['notes'].append('Net income includes noncontrolling interests (ProfitLoss). Prior-year 2021 group comparatives equal original NetIncomeLoss values.')
        r['evidence']=dict(current=ev,prior_ytd=prior_ev,prior_ytd_original=old_ev)
        assert r['period_end']<r['publication_date']<'2026-10-01'
        assert r['total_assets']>r['current_liabilities']>0
        assert base['availability_date']<=r['availability_date']
        interim.append(r);evidence.append(dict(ticker=t,period_end=end,filing=f,facts=r['evidence']))
        checks.append(dict(ticker=t,period_end=end,prior_ytd_original_reconciled=True,flow_fields_checked=3))
    # Confirm subsequent annual comparative flows match original annual values; validation only, never a backdated input.
    for y in range(2021,2025):
        current=filing(f'{y+1}-12-31','10-K');vals,ev=flows(current,f'{y}-12-31')
        assert vals=={k:aa[y][k] for k in FLOWS},(t,y,'Annual comparative changed')
        checks.append(dict(ticker=t,period_end=f'{y}-12-31',later_annual_comparative_matches_original=True,flow_fields_checked=3,validation_only_source=current))
for name,obj in [('research_solar_fuel_annual',annual),('research_solar_fuel_interim',interim)]:
    (AREA/(name+'.json')).write_text(json.dumps(obj,indent=2)+'\n')
S=AREA/'sources'/'solar_fuel'
(S/'selected_sec_facts.json').write_text(json.dumps(evidence,indent=2)+'\n')
(S/'comparative_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(S/'source_manifest.json').write_text(json.dumps(source_files,indent=2)+'\n')
research=dict(status='complete_source_qa_passed',annual_rows=len(annual),interim_rows=len(interim),tickers=['FSLR','PLUG'],gaps=[],method='Original accession-specific SEC companyfacts, conservative filing dates from SEC submissions; USD scaled to millions.',source_timing='Current retrieval retains filing accession and filed date; no latest comparative value replaces an original observation retroactively.',comparative_check_fields=sum(c['flow_fields_checked'] for c in checks),notes=['PLUG historical restatements preceding FY2021 do not alter the selected FY2021 onward flow values. All targeted interim comparative triples reconcile to their original filings.','First Solar uses reported operating income, including disposal gains/charges where GAAP operating income includes them. No adjusted earnings substitution.','Full SEC snapshots retained outside repository in sibling us_source_reports/solar_fuel; compact selected tagged facts and source hashes are committed.'])
(AREA/'research_solar_fuel.json').write_text(json.dumps(research,indent=2)+'\n')
print(json.dumps(research,indent=2))
