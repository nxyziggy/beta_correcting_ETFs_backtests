"""Extract accession-specific SEC facts; never substitute a later filing's facts."""
import json,hashlib
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[4]
AREA=ROOT/'data/us_restoration'
SOURCE=ROOT.parent/'us_source_reports/power'
DEST=AREA/'sources/power'
FLOW=('operating_income','net_income','operating_cash_flow')
class Tables(HTMLParser):
 def __init__(self):super().__init__();self.tables=[];self.buf=None;self.depth=0
 def handle_starttag(self,t,a):
  if t=='table':
   if self.depth==0:self.buf=[]
   self.depth+=1
  elif t=='tr' and self.buf is not None:self.buf.append('\n')
  elif t in ('td','th') and self.buf is not None:self.buf.append(' | ')
 def handle_endtag(self,t):
  if t=='table':
   self.depth-=1
   if self.depth==0:self.tables.append(''.join(self.buf));self.buf=None
 def handle_data(self,s):
  if self.buf is not None:self.buf.append(s)

def main():
 annual=[];interim=[];evidence=[];dates=[];comparison=[];hashes=[]
 for ticker,cik in [('BE','1664703'),('ETN','1551182')]:
  doc=json.loads((SOURCE/f'{ticker}_facts.json').read_text());facts=doc['facts']['us-gaap']
  sub=json.loads((SOURCE/f'{ticker}_submissions.json').read_text())['filings']['recent']
  filings={}
  for i,form in enumerate(sub['form']):
   if form in ('10-K','10-Q'):
    end=sub['reportDate'][i]
    r={k:sub[k][i] for k in ('accessionNumber','filingDate','reportDate','primaryDocument','form')}
    r['url']=f'https://www.sec.gov/Archives/edgar/data/{cik}/{r["accessionNumber"].replace("-","")}/{r["primaryDocument"]}'
    if end not in filings or r['filingDate']<filings[end]['filingDate']:filings[end]=r
  def fact(tag,start,end,filing):
   rs=[r for r in facts[tag]['units']['USD'] if r['accn']==filing['accessionNumber'] and r['end']==end and r.get('start')==start]
   vals={r['val'] for r in rs}
   assert len(vals)==1,(ticker,tag,start,end,filing,rs)
   f=rs[0]
   evidence.append(dict(ticker=ticker,concept='us-gaap:'+tag,unit='USD',source=filing['url'],**f))
   return next(iter(vals))/1e6
  def flows(start,end,filing):
   if ticker=='BE':op=fact('OperatingIncomeLoss',start,end,filing)
   else:
    components={tag:fact(tag,start,end,filing) for tag in ['RevenueFromContractWithCustomerExcludingAssessedTax','CostOfRevenue','SellingGeneralAndAdministrativeExpense','ResearchAndDevelopmentExpense']}
    op=components['RevenueFromContractWithCustomerExcludingAssessedTax']-sum(components[k] for k in list(components)[1:])
    pretax=fact('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',start,end,filing)
    itag=next(tag for tag in ['InterestExpenseNonoperating','InterestExpense','InterestExpenseOperating','InterestIncomeExpenseNet'] if any(r['accn']==filing['accessionNumber'] and r.get('start')==start and r['end']==end for r in facts.get(tag,{}).get('units',{}).get('USD',[])))
    interest=fact(itag,start,end,filing)*(-1 if itag=='InterestIncomeExpenseNet' else 1)
    evidence.append(dict(ticker=ticker,field='alternative_ebit_not_used',method='reported income before taxes plus net interest expense; includes separately reported business-disposal gains and other income/expense net',value=pretax+interest,unit='million USD',start=start,end=end,accn=filing['accessionNumber'],filed=filing['filingDate'],source=filing['url'],components=dict(pretax=pretax,net_interest_expense=interest)))
    evidence.append(dict(ticker=ticker,field='operating_income',method='reported net sales - cost of products sold - selling/administrative expense - research/development expense',value=op,unit='million USD',start=start,end=end,accn=filing['accessionNumber'],filed=filing['filingDate'],source=filing['url'],components=components))
   return dict(operating_income=op,net_income=fact('ProfitLoss',start,end,filing),operating_cash_flow=fact('NetCashProvidedByUsedInOperatingActivities',start,end,filing))
  def base(end):
   f=filings[end]
   notes=['Source availability is the actual SEC filing date, conservatively later than any earlier earnings release.','Net income is consolidated ProfitLoss before attribution to noncontrolling interests.']
   if ticker=='ETN':notes.append('Eaton does not report a consolidated operating-income subtotal. Operating income is derived as reported net sales less cost of products sold, selling/administrative expense and research/development expense. Separate net interest, business-disposal gains and other expense/income net are excluded. Other expense/income contains mixed operating and nonoperating items, so this mapping is a disclosed comparability limitation; no vendor/segment adjusted-profit measure is used.')
   return dict(ticker=ticker,period_end=end,publication_date=f['filingDate'],availability_date=f['filingDate'],currency='USD',unit='million',total_assets=fact('Assets',None,end,f),current_liabilities=fact('LiabilitiesCurrent',None,end,f),income_source=f['url'],balance_source=f['url'],cashflow_source=f['url'],date_source=f'https://www.sec.gov/Archives/edgar/data/{cik}/{f["accessionNumber"].replace("-","")}/{f["accessionNumber"]}-index.html',notes=notes)
  targets=[f'{y}-12-31' for y in range(2021,2026)]+['2022-06-30','2022-09-30']+[f'{y}-{m}' for y in range(2023,2026) for m in ('03-31','06-30','09-30')]+['2026-03-31','2026-06-30']
  for end in sorted(targets):
   y=int(end[:4]);q=int(end[5:7])//3;f=filings[end];r=base(end)
   assert f['filingDate']<'2026-10-01'
   if q==4:
    r.update(flows(f'{y}-01-01',end,f));r['period_type']='annual';r['fiscal_year']=y;annual.append(r)
   else:
    prior_end=f'{y-1}-12-31';prev=filings[prior_end]
    prior=flows(f'{y-1}-01-01',prior_end,prev)
    prior.update(period_end=prior_end,publication_date=prev['filingDate'],availability_date=prev['filingDate'],source=prev['url'])
    r.update(fiscal_year=y,fiscal_quarter=q,ytd=flows(f'{y}-01-01',end,f),prior_ytd=flows(f'{y-1}-01-01',f'{y-1}'+end[4:],f),prior_annual=prior,ttm_compatible=True)
    old=filings.get(f'{y-1}'+end[4:])
    if old:
     orig=flows(f'{y-1}-01-01',f'{y-1}'+end[4:],old)
     changes={k:dict(original=orig[k],comparative=r['prior_ytd'][k]) for k in FLOW if orig[k]!=r['prior_ytd'][k]}
     comparison.append(dict(ticker=ticker,period_end=end,compared_to=old['url'],differences=changes))
     if changes:
      assert ticker=='BE' and end=='2022-09-30' and list(changes)==['operating_cash_flow'],changes
      r['notes'].append('2021 nine-month cashflow comparative is -107.956 million versus -107.907 million in the original 2021 Q3 filing. Use the contemporaneous 2022 Q3 comparative; the 2021 audited annual cashflow (-60.681 million), published after original Q3, is unchanged in subsequent annual comparisons. The current filing states prior-period amounts were reclassified to conform to current presentation. The 0.049 million interim correction is not retroactively applied to any earlier score.')
    interim.append(r)
   dates.append(dict(ticker=ticker,**f))
   html=SOURCE/f['primaryDocument'];assert html.is_file(),html
   hashes.append(dict(file=f['primaryDocument'],sha256=hashlib.sha256(html.read_bytes()).hexdigest(),source=f['url']))
   p=Tables();p.feed(html.read_text())
   def selected(tab):
    low=tab.lower()
    return (('net sales' in low and 'income before income taxes' in low and 'research and development' in low) or ('from operations' in low and 'total revenue' in low and 'research' in low) or ('total assets' in low and 'total current liabilities' in low) or ('cash flows from operating activities' in low and ('net cash' in low or 'cash provided by' in low)))
   tabs=[t for t in p.tables if selected(t)]
   (DEST/(ticker+'_'+end+'_statement_excerpt.txt')).write_text(f['url']+'\nFiled '+f['filingDate']+'\n'+ '\n\n'.join(tabs)+'\n')
 unique={json.dumps(r,sort_keys=True):r for r in evidence}
 for name,rows in [('research_power_annual',annual),('research_power_interim',interim)]:
  (AREA/(name+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
 for name,rows in [('facts',list(unique.values())),('filing_dates',dates),('comparative_checks',comparison),('document_hashes',hashes)]:
  (DEST/(name+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
 print('annual',len(annual),'interim',len(interim),'evidence',len(unique),'comparative checks',len(comparison))
if __name__=='__main__':main()
