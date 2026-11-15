"""Transcribe verified current-year consolidated annual-report columns.

All values below are directly reported, never inferred from vendor records.
The source PDF pages are retained locally and their SHA256 hashes are recorded.
"""
from pathlib import Path
import json,hashlib,csv
from recover import URLS,ARCHIVE
ROOT=Path(__file__).parent
DEST=ROOT.parent.parent
# year: (release date, EBIT after special items, group net profit, operating cash flow,
#        total assets, reported current-liabilities subtotal, PDF page numbers)
DATA={
'VWS.CO':{
2020:('2021-02-10',698,771,743,18160,11232,[33,34,35]),
2021:('2022-02-10',322,176,996,19712,12700,[69,70,74]),
2022:('2023-02-08',-1596,-1572,-195,20090,13513,[74,75,79]),
2023:('2024-02-07',292,78,1027,22514,14020,[51,52,56]),
2024:('2025-02-05',794,494,2332,24644,15480,[137,138,142]),
2025:('2026-02-05',1015,780,2286,25732,16847,[135,136,138])},
'ORSTED.CO':{
2020:('2021-02-03',9010,15537,16466,196719,34408,[77,79,81]),
2021:('2022-02-02',16195,10887,12148,270385,86968,[73,75,77]),
2022:('2023-02-01',19774,14996,11924,314142,74868,[71,73,75]),
2023:('2024-02-07',-17853,-20182,28532,281136,59201,[144,145,147]),
2024:('2025-02-06',6171,16,18356,298786,53752,[159,160,162]),
2025:('2026-02-06',8620,3165,23741,367922,65277,[117,118,120])}}
DATE_SOURCES={
'VWS.CO':{
2020:'https://www.vestas.com/en/media/company-news/2021/vestas-annual-report-2020---continued-leadership-in-a-c-c3283502',
2021:'https://www.vestas.com/en/media/company-news/2022/vestas-annual-report-2021---resilience-and-determinatio-c3503915',
2022:'https://www.vestas.com/en/media/company-news/2023/vestas-annual-report-2022---a-challenging-year-with-neg-c3710817',
2023:'https://www.vestas.com/en/media/company-news/2024/vestas-annual-report-2023---a-return-to-profitability-c3923785',
2024:'https://www.vestas.com/en/media/company-news/2025/vestas-annual-report-2024---progress-in-a-challenging-y-c4100723',
2025:'https://www.vestas.com/en/media/company-news/2026/vestas-annual-report-2025---generating-value-amidst-gro-c4302973'},
'ORSTED.CO':{
2020:'https://orsted.com/en/company-announcement-list/2021/02/2168747',
2021:'https://orsted.com/en/company-announcement-list/2022/02/2022020247511',
2022:'https://orsted.com/en/company-announcement-list/2023/02/2023020162371',
2023:'https://orsted.com/en/company-announcement-list/2024/02/annual-report-for-2023--strong-underlying-results--82041',
2024:'https://orsted.com/en/company-announcement-list/2025/02/delivering-operational-earnings-in-line-with-expec-142508951',
2025:'https://orsted.com/en/company-announcement-list/2026/02/a-stronger-and-morecompetitiveorstedafter-a-defini-147853101'}}
rows=[];evidence=[]
for ticker,years in DATA.items():
 for year,(date,oi,ni,cfo,a,cl,pages) in years.items():
  key=ticker.split('.')[0]+'_'+str(year);url=URLS[key];pdf=ARCHIVE/(key+'.pdf')
  obs=hashlib.sha256((ticker+str(year)+date+url).encode()).hexdigest()[:20]
  rows.append(dict(ticker=ticker,period_end=f'{year}-12-31',fiscal_label=f'FY {year}',panel='restored_original_annual',period_type='annual',publication_date=date,availability_date=date,availability_basis='dated original issuer annual report; current-year consolidated figures; release evidence in research_wind.json',currency='EUR' if ticker=='VWS.CO' else 'DKK',unit='million',operating_income=oi,net_income=ni,operating_cash_flow=cfo,total_assets=a,current_liabilities=cl,prior_total_assets='',prior_current_liabilities='',income_source=url,balance_source=url,cashflow_source=url,observation_id=obs,component_ids=obs))
  full=json.loads((ARCHIVE/(key+'.json')).read_text())
  excerpts={str(p):full[p-1] for p in pages}
  excerpt_path=ROOT/(key+'_verified_pages.json')
  excerpt_path.write_text(json.dumps(excerpts,indent=2)+'\n')
  evidence.append(dict(ticker=ticker,fiscal_year=year,publication_date=date,publication_date_source=DATE_SOURCES[ticker][year],financial_source=url,source_class='original_issuer_annual_report',local_pdf=str(pdf),sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),bytes=pdf.stat().st_size,pdf_pages=pages,extraction_file=str(excerpt_path.relative_to(DEST.parent.parent)),field_definitions={'operating_income':'reported consolidated EBIT after special items, including impairments; IFRS column for Orsted FY2020','net_income':'total consolidated profit/loss for the year including non-controlling interests and hybrid capital owners','operating_cash_flow':'reported consolidated cash flows from operating activities','total_assets':'reported consolidated total assets','current_liabilities':'reported current-liabilities subtotal; separately presented liabilities relating to assets held for sale are not added'}))
vendor=list(csv.DictReader((DEST.parent/'financials_vendor.csv').open()))
differences=[]
for r in rows:
 old=next((v for v in vendor if v['ticker']==r['ticker'] and v['period_end']==r['period_end']),None)
 if old:
  for f in ['operating_income','net_income','operating_cash_flow','total_assets','current_liabilities']:
   if float(old[f])!=r[f]:differences.append(dict(ticker=r['ticker'],period_end=r['period_end'],field=f,original_report_value=r[f],inherited_vendor_value=float(old[f])))
report=dict(status='complete_original_annual_coverage',scope='Vestas and Orsted, FY2020–FY2025, annual observations only',rows=12,source_policy='Current-year figures from each original annual report; no retrospective use of later comparative figures; real release dates from issuer announcements; no vendor fallback required for these two companies.',archives={'VWS.CO':'https://www.vestas.com/en/investor/reports-and-presentations/vestas-reporting','ORSTED.CO':'https://orsted.com/en/investors/financial-reports'},evidence=evidence,vendor_differences=differences,concerns=['Annual restoration has lower update frequency than the existing annual+TTM panel. No 2026 interim figures were added.','Vestas FY2021 later comparatives were restated for cloud-computing accounting; this restoration uses FY2021 values as printed in the FY2021 report.','Vendor operating_income often differs materially from statutory EBIT: Orsted FY2023 vendor +12853 versus statutory -17853; Vestas FY2022 vendor -962 versus statutory -1596. Mixing them silently would change the score definition.','For Orsted FY2020, the IFRS column is used, not its alternative business-performance column.','Orsted presents held-for-sale liabilities separately from current liabilities (2020:687; 2021:492; 2025:1871 DKKm). The literal current-liabilities subtotal is used; this should be disclosed as an accounting comparability limitation.','Orsted FY2020 operating-cash-flow line refers to continuing operations while profit includes a discontinued-operation loss of 11 DKKm. No unsupported cash-flow adjustment was made.','These are issuer-hosted historical annual reports retrieved now, with dated release evidence; this is not a certified archive of every original file version.'])
(DEST/'research_wind_rows.json').write_text(json.dumps(rows,indent=2)+'\n')
(DEST/'research_wind.json').write_text(json.dumps(report,indent=2)+'\n')
print('Wrote',len(rows),'rows;',len(differences),'vendor discrepancies documented')
