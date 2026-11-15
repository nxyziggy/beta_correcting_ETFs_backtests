#!/usr/bin/env python3
"""Rebuild US long-history inputs from committed accession-level evidence.

The default is offline and portable. --source sec --sec-cache-dir DIRECTORY
repeats the original extraction from user-supplied SEC companyfacts snapshots;
those complete response bodies are not included in this repository.

Only missing periods are added. All five inputs must exist in one original
10-K/20-F accession filed within 180 days of that period end. Later restated
comparatives and amended filings are not substituted into old dates.
"""
import argparse,csv,datetime as dt,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data/long_history/us'
FIELDS=('operating_income','net_income','operating_cash_flow','total_assets','current_liabilities')
TICKERS=('AMAT','BE','ENPH','ETN','FSLR','INTC','LIN','LRCX','MCHP','MU','NEE','PLUG','TSM','TXN')


def sec_snapshot_path(directory, ticker):
 """Use only an explicitly supplied cache; never probe personal sibling paths."""
 paths=sorted({p for name in (ticker+'_companyfacts.json',ticker+'_facts.json')
               for p in directory.rglob(name) if p.is_file()})
 if len(paths)!=1:
  raise ValueError(f'{ticker}: expected one SEC snapshot under {directory}, found {len(paths)}')
 return paths[0]


def normalize_annual(source_id, raw, values):
 t=raw['ticker'];end=raw['period_end'];url=raw['source']
 return dict(ticker=t,period_end=end,fiscal_label='FY ending '+end,panel='long_history_original_annual',period_type='annual',publication_date=raw['publication_date'],availability_date=raw['availability_date'],availability_basis='Original annual SEC accession; conservative actual filing date',currency=raw['currency'],unit='million',**values,prior_total_assets='',prior_current_liabilities='',income_source=url,balance_source=url,cashflow_source=url,source_class='original_accession_annual',component_ids=source_id,observation_id='long_us_input_'+t+'_'+end,notes=raw['notes'])


def evidence_value(evidence, raw, flow):
 """Replay arithmetic using captured raw SEC facts, checking accession and dates."""
 if 'val' in evidence:
  expected_start=raw['period_start'] if flow else None
  if (evidence['accn']!=raw['accession'] or evidence['end']!=raw['period_end']
      or evidence.get('start')!=expected_start or evidence['unit']!=raw['currency']
      or evidence['filed']!=raw['publication_date']):
   raise ValueError(f"Evidence accession/date/unit mismatch: {raw['ticker']} {raw['period_end']}")
  value=float(evidence['val'])/1e6
 elif 'gross_profit' in evidence and 'operating_expenses' in evidence:
  value=evidence_value(evidence['gross_profit'],raw,True)-evidence_value(evidence['operating_expenses'],raw,True)
 elif 'continuing_operations' in evidence and 'discontinued_operations' in evidence:
  value=evidence_value(evidence['continuing_operations'],raw,True)+evidence_value(evidence['discontinued_operations'],raw,True)
 elif 'components' in evidence:
  # Eaton's derived subtotal: the normalized component copies are not inputs.
  parts={key:evidence_value(raw['evidence'][key],raw,True) for key in ('revenue','cost','sga','rd')}
  value=parts['revenue']-parts['cost']-parts['sga']-parts['rd']
 else:
  raise ValueError(f"Unsupported captured SEC arithmetic: {raw['ticker']} {raw['period_end']}")
 if not math.isfinite(value):
  raise ValueError('Nonfinite SEC financial value')
 qa=evidence.get('statement_qa')
 if qa and abs(value-qa['normalized_group_cfo'])>1e-6:
  raise ValueError(f"Captured CFO statement QA mismatch: {raw['ticker']} {raw['period_end']}")
 return value


def rebuild_frozen(source_dir=OUT):
 """Recompute SEC rows; append separately captured manual GFS rows unchanged.

 The registry is a frozen input in this mode. This reproduces normalization,
 not the acquisition of the uncommitted full SEC companyfacts responses.
 """
 registry=json.loads((source_dir/'source_registry.json').read_text())
 manual_registry=json.loads((source_dir/'manual_source_registry.json').read_text())
 manual_rows=json.loads((source_dir/'manual_inputs.json').read_text())
 rows=[]
 for sid,raw in registry.items():
  if sid in manual_registry:
   if raw!=manual_registry[sid]:
    raise ValueError(f'Manual registry mismatch: {sid}')
   continue
  values={field:evidence_value(raw['evidence'][field],raw,field in FIELDS[:3]) for field in FIELDS}
  for field,value in values.items():
   if value!=raw[field]:
    raise ValueError(f'Frozen normalized field differs from captured facts: {sid} {field}')
  rows.append(normalize_annual(sid,raw,values))
 if set(manual_registry)-set(registry):
  raise ValueError('Manual source missing from frozen registry')
 rows+=manual_rows
 return rows


def extract_sec(sec_cache_dir):
 existing=list(csv.DictReader((ROOT/'data/financials_actual_annual.csv').open()))
 existing+=json.loads((ROOT/'data/us_restoration/normalized_inputs.json').read_text())['annual']
 existing+=json.loads((ROOT/'data/research_corrections/lam_inputs.json').read_text())[:1]
 oldkeys={(r['ticker'],r['period_end']) for r in existing}
 qa_rows=json.loads((OUT/'cashflow_mapping_qa.json').read_text())['checks']
 qa={(r['ticker'],r['period_end']):r for r in qa_rows}
 rows=[];registry={};exclusions=[];manifest=[]
 for t in TICKERS:
  path=sec_snapshot_path(sec_cache_dir,t);doc=json.loads(path.read_text());cik=doc['cik']
  namespace='ifrs-full' if t=='TSM' else 'us-gaap';facts=doc['facts'][namespace];unit='TWD' if t=='TSM' else 'USD'
  manifest.append(dict(ticker=t,url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),capture_file=path.name))
  tags=({'operating_income':['ProfitLossFromOperatingActivities'],'net_income':['ProfitLoss'],'operating_cash_flow':['CashFlowsFromUsedInOperatingActivities'],'total_assets':['Assets'],'current_liabilities':['CurrentLiabilities']} if namespace=='ifrs-full' else {'operating_income':['OperatingIncomeLoss'],'net_income':['ProfitLoss','NetIncomeLoss'],'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'],'total_assets':['Assets'],'current_liabilities':['LiabilitiesCurrent']})
  def pick(tag_options,accn,end,start):
   for tag in tag_options:
    rr=[r for r in facts.get(tag,{}).get('units',{}).get(unit,[]) if r['accn']==accn and r['end']==end and r.get('start')==start]
    if rr:
     vals={r['val'] for r in rr}
     if len(vals)!=1:raise ValueError(('Ambiguous same-accession fact',t,tag,accn,end,rr))
     return next(iter(vals))/1e6,dict(concept=namespace+':'+tag,unit=unit,**rr[0])
   raise KeyError((t,tag_options,accn,end,start))
  candidates={}
  for r in [r for tag in tags['operating_cash_flow'] for r in facts.get(tag,{}).get('units',{}).get(unit,[])]:
   if 'start' not in r or r['form'] not in ('10-K','20-F'):continue
   end=dt.date.fromisoformat(r['end']);start=dt.date.fromisoformat(r['start']);filed=dt.date.fromisoformat(r['filed'])
   if not 330 <= (end-start).days <=380 or not 0<(filed-end).days<=180:continue
   if not '2015-01-01'<=r['end']<='2021-12-31' or (t,r['end']) in oldkeys:continue
   if t=='LIN' and r['end']<'2018-10-31':continue
   candidates.setdefault(r['end'],{})[r['accn']]=r
  for end,choices in sorted(candidates.items()):
   chosen=None
   # The earliest unamended original annual accession is mandatory. Do not skip
   # a missing concept in it in favor of a later comparative/restatement.
   candidate=min(choices.values(),key=lambda r:(r['filed'],r['accn']))
   accn=candidate['accn'];start=candidate['start'];date=candidate['filed'];evidence={};values={}
   try:
    for f in FIELDS:
     if t=='ETN' and f=='operating_income':
      components={}
      for name,opts in [('revenue',['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','Revenues']),('cost',['CostOfRevenue','CostOfGoodsAndServicesSold']),('sga',['SellingGeneralAndAdministrativeExpense']),('rd',['ResearchAndDevelopmentExpense'])]:
       components[name],evidence[name]=pick(opts,accn,end,start)
      values[f]=components['revenue']-components['cost']-components['sga']-components['rd']
      evidence[f]=dict(method='Net sales less cost of products sold, selling/administrative and R&D, consistent with existing Eaton mapping',components=components)
     elif t=='ENPH' and f=='operating_income':
      try:values[f],evidence[f]=pick(tags[f],accn,end,start)
      except KeyError:
       gross,ge=pick(['GrossProfit'],accn,end,start);opex,oe=pick(['OperatingExpenses'],accn,end,start)
       values[f]=gross-opex;evidence[f]=dict(method='GAAP gross profit less operating expenses',gross_profit=ge,operating_expenses=oe)
     else:
      values[f],evidence[f]=pick(tags[f],accn,end,start if f in FIELDS[:3] else None)
      if f=='operating_cash_flow' and evidence[f]['concept'].endswith('ContinuingOperations'):
       checked=qa.get((t,end))
       if checked:
        if checked['method']=='validated_separate_discontinued_sum':
         discontinued,de=pick(['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations'],accn,end,start)
         subtotal,subtotal_evidence=values[f],evidence[f]
         values[f]=subtotal+discontinued
         evidence[f]=dict(method='Verified group CFO: continuing subtotal plus separately presented discontinued CFO',continuing_operations=subtotal_evidence,discontinued_operations=de)
        if abs(values[f]-checked['normalized_group_cfo'])>1e-6:raise ValueError(('CFO statement QA mismatch',t,end,values[f],checked))
        evidence[f]['statement_qa']=checked
       elif end>='2018-01-01':
        raise ValueError(('Missing direct statement QA for continuing-operations tag',t,end))
       else:
        evidence[f]['mapping_note']='Earlier archival observation, outside the supported 2019-onward extension; original accession subtotal retained. No automatic addition of discontinued cash flow.'
   except KeyError as e:
    exclusions.append(dict(ticker=t,period_end=end,accession=accn,reason=str(e)));continue
   url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace("-","")}/{accn}-index.html'
   notes=['Five consolidated financial fields from the same original annual accession; source-file SHA and accession-specific tags retained. Conservative actual filing date, not assumed earnings day. Later amended/restated comparisons never backdated.']
   if t in ('BE','PLUG'):notes.append('Historical original facts may subsequently be restated. This observation represents the filing as then known; later annual reports supply new periods at their own publication dates.')
   if t=='TSM':notes.append('Standalone IASB-IFRS annual 20-F, TWD millions, at actual 20-F filing date. Earlier than restored Taiwan-IFRS 6-K series; no TTM arithmetic mixes these bases. This is a disclosed reporting-basis/precision transition.')
   if t=='ETN':notes.append('Operating subtotal derived with the same mapping used in the restored series; separately reported business-disposal gains and other income/expense excluded.')
   sid=f'long_us_source_{t}_{end}'
   raw=dict(ticker=t,period_end=end,period_start=start,publication_date=date,availability_date=date,fiscal_quarter=4,period_type='annual',currency=unit,unit='million',source=url,date_source=url,accession=accn,**values,evidence=evidence,notes=notes)
   registry[sid]=raw
   rows.append(dict(ticker=t,period_end=end,fiscal_label='FY ending '+end,panel='long_history_original_annual',period_type='annual',publication_date=date,availability_date=date,availability_basis='Original annual SEC accession; conservative actual filing date',currency=unit,unit='million',**values,prior_total_assets='',prior_current_liabilities='',income_source=url,balance_source=url,cashflow_source=url,source_class='original_accession_annual',component_ids=sid,observation_id='long_us_input_'+t+'_'+end,notes=notes))
 if (OUT/'manual_inputs.json').exists():
  rows+=json.loads((OUT/'manual_inputs.json').read_text());registry.update(json.loads((OUT/'manual_source_registry.json').read_text()));manifest+=json.loads((OUT/'manual_source_manifest.json').read_text())
 return dict(normalized_inputs=rows,source_registry=registry,exclusions=exclusions,source_manifest=manifest)


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',choices=('frozen','sec'),default='frozen',help='frozen: replay committed accession evidence; sec: extract supplied full snapshots')
 parser.add_argument('--sec-cache-dir',type=Path,help='explicit directory containing SEC snapshots (required with --source sec)')
 parser.add_argument('--output-dir',type=Path,default=OUT,help='output directory; frozen mode writes normalized_inputs.json only')
 parser.add_argument('--check',action='store_true',help='compare rebuilt records with committed normalized inputs without writing files')
 args=parser.parse_args()
 if args.source=='sec' and (args.sec_cache_dir is None or not args.sec_cache_dir.is_dir()):
  parser.error('--source sec requires an existing --sec-cache-dir')
 if args.source=='frozen' and args.sec_cache_dir is not None:
  parser.error('--sec-cache-dir applies only to --source sec')
 outputs=(dict(normalized_inputs=rebuild_frozen()) if args.source=='frozen' else extract_sec(args.sec_cache_dir))
 if args.check:
  for name,value in outputs.items():
   committed=json.loads((OUT/(name+'.json')).read_text())
   if value!=committed:
    raise ValueError(f'Rebuilt {name} differs from committed records')
  print(f"Verified {len(outputs['normalized_inputs'])} observations from {args.source} inputs; no files written")
  return
 args.output_dir.mkdir(parents=True,exist_ok=True)
 for name,value in outputs.items():
  target=args.output_dir/(name+'.json');temp=target.with_suffix('.json.tmp')
  temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(target)
 print(f"Rebuilt {len(outputs['normalized_inputs'])} observations from {args.source} inputs")
 if args.source=='frozen':
  print('Frozen registry, exclusions and original capture manifest left unchanged; full SEC response acquisition was not replayed')


if __name__=='__main__':main()
