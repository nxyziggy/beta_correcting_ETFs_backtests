#!/usr/bin/env python3
"""Parse the frozen public numeric captures. Standard library only; no networking."""
import calendar, csv, datetime as dt, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'

def endmonth(year, month):
    return dt.date(year, month, calendar.monthrange(year, month)[1])

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fields is None:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader(); w.writerows(rows)

def vendor_table(path):
    rows = {}
    periods = []
    fiscal = []
    if not path.exists(): return {}, '', ''
    raw = path.read_text()
    source = raw.splitlines()[0].removeprefix('Source: ')
    currency = re.search(r'Financials in millions (\w+)', raw)
    for line in raw.splitlines():
        parts = [s.strip() for s in line.split('|')]
        if len(parts) < 2: continue
        label = parts[0]
        if label in ('Fiscal Year','Fiscal Quarter'):
            fiscal = parts[1:]
        elif label == 'Period Ending':
            periods = parts[1:]
        elif periods and label != '---':
            if len(parts)-1 != len(periods):
                raise ValueError(f'Column mismatch {path.name}: {line}')
            for p, fy, value in zip(periods, fiscal, parts[1:]):
                if fy not in ('TTM', 'Current') and not fy.startswith('FY ') and not re.fullmatch(r'Q[1-4] \d{4}',fy): continue
                if value in ('-', '', 'Upgrade', 'Pro'): continue
                val = value.replace(',', '').replace('%','')
                if not re.fullmatch(r'-?\d+(?:\.\d+)?', val): continue
                m = re.fullmatch(r"([A-Za-z]{3}) '(\d\d)", p)
                if not m: continue
                date = endmonth(2000+int(m[2]), dt.datetime.strptime(m[1], '%b').month)
                key = (date.isoformat(), fy)
                rows.setdefault(key, {})[label] = float(val)
    return rows, source, currency[1] if currency else ''

def get_field(row, label):
    if label in row: return row[label]
    matches = [v for k,v in row.items() if k.startswith(label+' ')]
    if len(matches) == 1: return matches[0]
    return None

def main():
    universe = json.loads((DATA/'universe.json').read_text())
    supplements=[]
    if (DATA/'supplement_source_facts.json').exists():
        for s in json.loads((DATA/'supplement_source_facts.json').read_text()):
            supplements.append(dict(ticker=s['t'],period_end=s.get('period_end',f"{s['y']}-12-31"),fiscal_label=f"FY {s['y']}",
                panel='primary_release_supplement',period_type='annual',publication_date=s['pub'],availability_date=s.get('availability_date',s['pub']),
                availability_basis=s.get('availability_basis','original dated issuer release'),currency=s.get('currency','EUR'),unit='million',
                operating_income=s['oi'],net_income=s['ni'],operating_cash_flow=s['cfo'],total_assets=s['a'],current_liabilities=s['cl'],
                prior_total_assets=s['pa'],prior_current_liabilities=s['pcl'],income_source=s['url'],balance_source=s['url'],cashflow_source=s['url']))
        write_csv(DATA/'financials_supplement.csv',supplements)
    observations=[]; missing=[]
    for u in universe:
        ticker=u['ticker']
        inc, si, ci=vendor_table(DATA/'vendor'/f'{ticker}_income-statement.txt')
        if not inc: inc,si,ci=vendor_table(DATA/'vendor'/f'{ticker}_overview.txt')
        bal,sb,cb=vendor_table(DATA/'vendor'/f'{ticker}_balance-sheet.txt')
        cf,sc,cc=vendor_table(DATA/'vendor'/f'{ticker}_cash-flow-statement.txt')
        currencies = {c for c in (ci,cb,cc) if c}
        if len(currencies)>1: raise ValueError(f'Financial currency mismatch {ticker}: {currencies}')
        for key in sorted(set(inc)|set(bal)|set(cf)):
            if not key[1].startswith('FY '): continue
            fields={'operating_income':get_field(inc.get(key,{}),'Operating Income'),
                    'net_income':get_field(cf.get(key,{}),'Net Income'),
                    'operating_cash_flow':get_field(cf.get(key,{}),'Operating Cash Flow'),
                    'total_assets':get_field(bal.get(key,{}),'Total Assets'),
                    'current_liabilities':get_field(bal.get(key,{}),'Total Current Liabilities')}
            absent=[k for k,v in fields.items() if v is None]
            if absent:
                missing.append({'ticker':ticker,'period_end':key[0],'fiscal_label':key[1],'reason':'missing '+','.join(absent)})
                continue
            end=dt.date.fromisoformat(key[0]); annual=key[1].startswith('FY ')
            observations.append({'ticker':ticker,'period_end':key[0],'fiscal_label':key[1],
                                 'panel':'vendor_end_balance','period_type':'annual' if annual else 'trailing',
                                 'publication_date':'','availability_date':(end+dt.timedelta(days=180 if annual else 90)).isoformat(),
                                 'availability_basis':'assumed 180d annual / 90d trailing; current revised vendor history',
                                 'currency':next(iter(currencies),''),'unit':'million',**fields,
                                 'prior_total_assets':'','prior_current_liabilities':'',
                                 'income_source':si,'balance_source':sb,'cashflow_source':sc})
    write_csv(DATA/'financials_vendor.csv',observations)
    quarterly=[]
    for u in universe:
        t=u['ticker']
        inc,si,ci=vendor_table(DATA/'quarterly'/f'{t}_income-statement.txt')
        if not inc: inc,si,ci=vendor_table(DATA/'quarterly'/f'{t}_overview.txt')
        bal,sb,cb=vendor_table(DATA/'quarterly'/f'{t}_balance-sheet.txt')
        cf,sc,cc=vendor_table(DATA/'quarterly'/f'{t}_cash-flow-statement.txt')
        periods={}
        for date,fy in sorted(set(inc)|set(bal)|set(cf)):
            m=re.fullmatch(r'Q([1-4]) (\d{4})',fy)
            if not m: continue
            key=(date,fy)
            periods[int(m[2])*4+int(m[1])] = (date,fy,{
                'operating_income':get_field(inc.get(key,{}),'Operating Income'),
                'net_income':get_field(cf.get(key,{}),'Net Income'),
                'operating_cash_flow':get_field(cf.get(key,{}),'Operating Cash Flow'),
                'total_assets':get_field(bal.get(key,{}),'Total Assets'),
                'current_liabilities':get_field(bal.get(key,{}),'Total Current Liabilities')})
        for ordinal,(date,fy,values) in sorted(periods.items()):
            win=[periods.get(k) for k in range(ordinal-3,ordinal+1)]
            if any(r is None or any(r[2][f] is None for f in ('operating_income','net_income','operating_cash_flow')) for r in win): continue
            if values['total_assets'] is None or values['current_liabilities'] is None: continue
            data={f:sum(r[2][f] for r in win) for f in ('operating_income','net_income','operating_cash_flow')}
            data.update({f:values[f] for f in ('total_assets','current_liabilities')})
            prior=periods.get(ordinal-4)
            end=dt.date.fromisoformat(date)
            quarterly.append({'ticker':t,'period_end':date,'fiscal_label':'TTM through '+fy,
                'panel':'vendor_quarterly_ttm','period_type':'trailing','publication_date':'',
                'availability_date':(end+dt.timedelta(days=90)).isoformat(),
                'availability_basis':'four observed consecutive fiscal quarters; assumed 90d; current revised history',
                'currency':ci or cb or cc,'unit':'million',**data,
                'prior_total_assets':prior[2]['total_assets'] if prior else '',
                'prior_current_liabilities':prior[2]['current_liabilities'] if prior else '',
                'income_source':si,'balance_source':sb,'cashflow_source':sc})
    write_csv(DATA/'financials_quarterly.csv',quarterly,list(observations[0]))
    write_csv(DATA/'financial_missing.csv',missing, ['ticker','period_end','fiscal_label','reason'])
    fx={}
    for path in sorted((DATA/'fx').glob('*.txt')):
        series=path.name.split('_')[0].split('.')[0]
        text=path.read_text();source=text.splitlines()[0].removeprefix('Source: ')
        pairs=re.findall(r'(20\d{2}-\d\d-\d\d)\s*\|\s*(\d+(?:\.\d+)?)',text)
        pairs += [(dt.datetime.strptime(d,'%d-%b-%y').date().isoformat(),v) for d,v in re.findall(r'(\d{1,2}-[A-Z]{3}-\d{2})\s*\|\s*(\d+(?:\.\d+)?)',text)]
        for d,v in pairs:
            value=float(v)
            old=fx.setdefault(series,{}).get(d)
            if old and abs(old[0]-value)>1e-10: raise ValueError(f'Conflicting FX {series} {d}: {old} vs {value}')
            fx[series][d]=(value,source)
    fxrows=[]
    for s,ds in sorted(fx.items()):
        for d,(v,source) in sorted(ds.items()):
            fxrows.append({'series':s,'date':d,'rate':v,'source':source})
    write_csv(DATA/'fx_daily.csv',fxrows)
    prices=[]
    for path in sorted((DATA/'prices').glob('*.txt')):
        ticker=path.stem;raw=path.read_text(); source=raw.splitlines()[0].removeprefix('Source: ')
        for line in raw.splitlines():
            m=re.match(r'([A-Za-z]+) (\d{4})\s*\|\s*[^\d]*([\d,.]+)\s*\|\s*[^\d]*([\d,.]+)',line)
            if not m: continue
            d=endmonth(int(m[2]),dt.datetime.strptime(m[1],'%B').month)
            status='complete'
            if d > dt.date(2026,8,31): status='partial_month_excluded'
            if ticker=='EDF.PA' and d>dt.date(2023,6,30): status='stale_after_delisting_excluded'
            if ticker=='GEV' and d<dt.date(2024,4,2): status='when_issued_excluded'
            prices.append({'ticker':ticker,'date':d.isoformat(),'adjusted_close':float(m[3].replace(',','')),
                           'unadjusted_close':float(m[4].replace(',','')),'status':status,'source':source})
    write_csv(DATA/'prices_monthly.csv',sorted(prices,key=lambda r:(r['ticker'],r['date'])))
    manifest=[]
    for p in sorted(DATA.rglob('*')):
        if p.is_file() and p.suffix in ('.txt','.json') and p.name != 'capture_manifest.json':
            manifest.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    (DATA/'capture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'financial_rows':len(observations),'financial_companies':len(set(r['ticker'] for r in observations)),
                      'quarterly_ttm_rows':len(quarterly),'quarterly_companies':sorted(set(r['ticker'] for r in quarterly)),
                      'missing_rows':len(missing),'monthly_prices':len(prices),'fx_observations':len(fxrows)},indent=2))

if __name__=='__main__': main()
