#!/usr/bin/env python3
"""Extract original-accession US annual facts from cached public SEC snapshots.

Only missing periods are added. All five inputs must exist in one original
10-K/20-F accession filed within 180 days of that period end. Later restated
comparatives and amended filings are not substituted into old dates.
"""
import csv,datetime as dt,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data/long_history/us'
CACHE=ROOT.parent/'long_history_source_reports/us'
OLD=ROOT.parent/'us_source_reports'
FIELDS=('operating_income','net_income','operating_cash_flow','total_assets','current_liabilities')
SPECIAL={'BE':OLD/'power/BE_facts.json','ETN':OLD/'power/ETN_facts.json',
'FSLR':OLD/'solar_fuel/FSLR_companyfacts.json','PLUG':OLD/'solar_fuel/PLUG_companyfacts.json',
'TSM':OLD/'tsm_gev/TSM_companyfacts.json'}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 existing=list(csv.DictReader((ROOT/'data/financials_actual_annual.csv').open()))
 existing+=json.loads((ROOT/'data/us_restoration/normalized_inputs.json').read_text())['annual']
 existing+=json.loads((ROOT/'data/research_corrections/lam_inputs.json').read_text())[:1]
 oldkeys={(r['ticker'],r['period_end']) for r in existing}
 qa_rows=json.loads((OUT/'cashflow_mapping_qa.json').read_text())['checks']
 qa={(r['ticker'],r['period_end']):r for r in qa_rows}
 rows=[];registry={};exclusions=[];manifest=[]
 for t in ('AMAT','BE','ENPH','ETN','FSLR','INTC','LIN','LRCX','MCHP','MU','NEE','PLUG','TSM','TXN'):
  path=SPECIAL.get(t,CACHE/(t+'_companyfacts.json'));doc=json.loads(path.read_text());cik=doc['cik']
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
 for name,v in [('normalized_inputs',rows),('source_registry',registry),('exclusions',exclusions),('source_manifest',manifest)]:
  target=OUT/(name+'.json');temp=target.with_suffix('.json.tmp');temp.write_text(json.dumps(v,indent=2)+'\n');temp.replace(target)
 print('Recovered',len(rows),'observations; exclusions',len(exclusions))
 for t in sorted({r['ticker'] for r in rows}):print(t,[(r['period_end'],r['availability_date']) for r in rows if r['ticker']==t])
 print('EXCLUSIONS',exclusions)
if __name__=='__main__':main()
