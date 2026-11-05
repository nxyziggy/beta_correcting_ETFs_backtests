#!/usr/bin/env python3
"""Parse observed November captures; append new periods without rewriting past history."""
import csv,datetime as dt,hashlib,json,re
from pathlib import Path
from prepare_data import ROOT,DATA,endmonth,vendor_table,get_field,write_csv

AS_OF='2026-11-02'
MONTH_END='2026-10-31'
OLD_END='2026-08-31'
UPDATE=DATA/'updates_20261102'
def read(p):return list(csv.DictReader(p.open()))
def source(p):return p.read_text().splitlines()[0].removeprefix('Source: ')
def main():
    daily=[];by={}
    for p in sorted((UPDATE/'daily').glob('*.txt')):
        ds={}
        for line in p.read_text().splitlines():
            a=[x.strip() for x in line.split('|')]
            if len(a)<6:continue
            try:d=dt.datetime.strptime(a[0],'%b %d, %Y').date().isoformat()
            except ValueError:continue
            if d>AS_OF:continue
            v=[float(x.replace(',','')) for x in a[1:6]]
            assert min(v)>0 and v[1]>=v[2]
            row=dict(ticker=p.stem,date=d,open=v[0],high=v[1],low=v[2],close=v[3],adjusted_close=v[4],source=source(p))
            assert d not in ds
            ds[d]=row;daily.append(row)
        assert AS_OF in ds and OLD_END in ds,(p.name,'missing dated endpoint')
        by[p.stem]=ds
    assert len(by)==34
    write_csv(DATA/'extension_prices_daily.csv',sorted(daily,key=lambda r:(r['ticker'],r['date'])))
    month=[]
    for t,ds in sorted(by.items()):
        for date in (OLD_END,'2026-09-30',MONTH_END):
            observed=max(d for d in ds if d<=date)
            age=(dt.date.fromisoformat(date)-dt.date.fromisoformat(observed)).days
            assert age<=3
            r=ds[observed]
            month.append(dict(ticker=t,date=date,observation_date=observed,adjusted_close=r['adjusted_close'],close=r['close'],age_days=age,source=r['source']))
    write_csv(DATA/'extension_month_end_prices.csv',month)
    # Federal Reserve observations retain the existing quote direction. ECB's
    # Nov 2 EUR crosses are converted algebraically to that direction, with source retained.
    fx=[];mapping={'DENMARK':'DEXDNUS','*EMU MEMBERS':'DEXUSEU','NORWAY':'DEXNOUS','SWITZERLAND':'DEXSZUS'}
    for p in sorted((UPDATE/'fx').glob('2026*.txt')):
        lines=p.read_text().splitlines()
        header=next(x for x in lines if x.startswith('COUNTRY')).split('|')[2:]
        dates=[dt.datetime.strptime(x.strip().replace('.','')+' 2026','%b %d %Y').date().isoformat() for x in header]
        for line in lines:
            parts=[x.strip() for x in line.split('|')]
            if parts[0] not in mapping:continue
            for d,v in zip(dates,parts[2:]):
                if v=='ND':continue
                fx.append(dict(series=mapping[parts[0]],date=d,rate=float(v),source=source(p),basis='Federal Reserve H.10 daily observation'))
    ecb=UPDATE/'fx/ECB_20261102.txt';cross={}
    for line in ecb.read_text().splitlines():
        parts=[x.strip() for x in line.split('|')]
        if parts[0] in ('USD','DKK','CHF','NOK'):cross[parts[0]]=float(parts[2])
    assert set(cross)=={'USD','DKK','CHF','NOK'}
    for currency,series in [('USD','DEXUSEU'),('DKK','DEXDNUS'),('CHF','DEXSZUS'),('NOK','DEXNOUS')]:
        rate=cross[currency] if currency=='USD' else cross[currency]/cross['USD']
        fx.append(dict(series=series,date=AS_OF,rate=rate,source=source(ecb),basis='ECB EUR reference rate' if currency=='USD' else f'ECB {currency}/EUR divided by USD/EUR'))
    oldfx=read(DATA/'fx_daily.csv');known={(r['series'],r['date']):r for r in oldfx}
    for r in fx:
        k=(r['series'],r['date'])
        if k in known:assert abs(float(known[k]['rate'])-r['rate'])<1e-10,(k,'FX revision requires review')
        else:known[k]={k:r[k] for k in ('series','date','rate','source')}
    write_csv(DATA/'fx_daily.csv',[known[k] for k in sorted(known)])
    write_csv(DATA/'extension_fx_observations.csv',fx)
    # Only later report periods are appended. Revised values for existing periods
    # are recorded for review; they cannot be backdated into prior trading decisions.
    oldannual=read(DATA/'financials_vendor.csv');oldq=read(DATA/'financials_quarterly.csv')
    latest={t:max(r['period_end'] for r in oldq if r['ticker']==t) for t in set(r['ticker'] for r in oldq)}
    additions=[];checks=[];revisions=[]
    flds=('operating_income','net_income','operating_cash_flow','total_assets','current_liabilities')
    for t,last in sorted(latest.items()):
        tables=[vendor_table(UPDATE/'financials'/f'{t}_{name}.txt') for name in ('income-statement','balance-sheet','cash-flow-statement')]
        (inc,si,ci),(bal,sb,cb),(cf,sc,cc)=tables
        currencies={c for c in (ci,cb,cc) if c};assert len(currencies)<=1
        periods={}
        for date,fy in sorted(set(inc)|set(bal)|set(cf)):
            m=re.fullmatch(r'Q([1-4]) (\d{4})',fy)
            if not m:continue
            k=(date,fy)
            periods[int(m[2])*4+int(m[1])]=(date,fy,dict(operating_income=get_field(inc.get(k,{}),'Operating Income'),net_income=get_field(cf.get(k,{}),'Net Income'),operating_cash_flow=get_field(cf.get(k,{}),'Operating Cash Flow'),total_assets=get_field(bal.get(k,{}),'Total Assets'),current_liabilities=get_field(bal.get(k,{}),'Total Current Liabilities')))
        checks.append(dict(ticker=t,panel='quarterly',previous_latest=last,observed_latest=max(x[0] for x in periods.values()),source=si))
        for n,(date,fy,v) in sorted(periods.items()):
            win=[periods.get(i) for i in range(n-3,n+1)]
            if any(x is None or any(x[2][f] is None for f in flds[:3]) for x in win) or v['total_assets'] is None or v['current_liabilities'] is None:continue
            values={f:sum(x[2][f] for x in win) for f in flds[:3]};values.update({f:v[f] for f in flds[3:]})
            prev=next((r for r in oldq if r['ticker']==t and r['period_end']==date),None)
            if prev:
                for f in flds:
                    if abs(float(prev[f])-values[f])>1e-6:revisions.append(dict(ticker=t,panel='quarterly',period_end=date,field=f,frozen_value=prev[f],current_value=values[f],action='retain previously captured record'))
            if date<=last:continue
            prior=periods.get(n-4)
            additions.append(dict(ticker=t,period_end=date,fiscal_label='TTM through '+fy,panel='vendor_quarterly_ttm',period_type='trailing',publication_date='',availability_date=(dt.date.fromisoformat(date)+dt.timedelta(days=90)).isoformat(),availability_basis='four observed fiscal quarters; unchanged 90-day lag; new report period captured 2026-11-02',currency=ci or cb or cc,unit='million',**values,prior_total_assets=prior[2]['total_assets'] if prior else '',prior_current_liabilities=prior[2]['current_liabilities'] if prior else '',income_source=si,balance_source=sb,cashflow_source=sc))
    annualadd=[]
    (inc,si,ci),(bal,sb,cb),(cf,sc,cc)=[vendor_table(UPDATE/'financials'/f'MU_annual-{name}.txt') for name in ('income-statement','balance-sheet','cash-flow-statement')]
    last=max(r['period_end'] for r in oldannual if r['ticker']=='MU')
    for k in sorted(set(inc)&set(bal)&set(cf)):
        date,fy=k
        if not fy.startswith('FY ') or date<=last:continue
        values=dict(operating_income=get_field(inc[k],'Operating Income'),net_income=get_field(cf[k],'Net Income'),operating_cash_flow=get_field(cf[k],'Operating Cash Flow'),total_assets=get_field(bal[k],'Total Assets'),current_liabilities=get_field(bal[k],'Total Current Liabilities'))
        assert all(v is not None for v in values.values())
        annualadd.append(dict(ticker='MU',period_end=date,fiscal_label=fy,panel='vendor_end_balance',period_type='annual',publication_date='',availability_date=(dt.date.fromisoformat(date)+dt.timedelta(days=180)).isoformat(),availability_basis='unchanged 180-day annual lag; new report period captured 2026-11-02',currency=ci or cb or cc,unit='million',**values,prior_total_assets='',prior_current_liabilities='',income_source=si,balance_source=sb,cashflow_source=sc))
    for p in sorted((UPDATE/'financials').glob('*_annual-overview.txt')):
        t=p.name.removesuffix('_annual-overview.txt');rows,src,_=vendor_table(p)
        years=[k[0] for k in rows if k[1].startswith('FY ')]
        old=[r['period_end'] for r in oldannual if r['ticker']==t]
        checks.append(dict(ticker=t,panel='annual',previous_latest=max(old,default='original issuer supplement only'),observed_latest=max(years,default='unavailable'),source=src))
    write_csv(DATA/'financials_vendor.csv',oldannual+annualadd)
    write_csv(DATA/'financials_quarterly.csv',oldq+additions)
    write_csv(DATA/'extension_financial_additions.csv',annualadd+additions)
    write_csv(DATA/'extension_financial_review.csv',checks)
    write_csv(DATA/'extension_financial_revisions.csv',revisions)
    assert all(r['availability_date']>='2026-10-01' for r in additions+annualadd),'New record could affect a prior extension trade; review required'
    config=dict(as_of=AS_OF,complete_month_end=MONTH_END,previous_complete_month_end=OLD_END,price_instruments=len(by),new_daily_observations=len(daily),new_month_end_observations=len(month),fx_observations=len(fx),new_annual_records=len(annualadd),new_ttm_records=len(additions),annual_companies_reviewed=30,quarterly_companies_reviewed=9,source_vintage_policy='preserve prior records; append new report periods; chain new dated price ratios from August 31',latest_fx_provider='ECB on 2026-11-02; Federal Reserve H.10 through 2026-10-30')
    (DATA/'extension_config.json').write_text(json.dumps(config,indent=2)+'\n')
    manifest=[]
    for p in sorted(DATA.rglob('*')):
        if p.is_file() and p.suffix in ('.txt','.json') and p.name!='capture_manifest.json':manifest.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
    (DATA/'capture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(config,indent=2))
if __name__=='__main__':main()
