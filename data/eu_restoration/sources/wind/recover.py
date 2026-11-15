from pathlib import Path
import concurrent.futures,urllib.request,json,logging
from pypdf import PdfReader
ROOT=Path(__file__).parent
ARCHIVE=ROOT.parents[4]/'eu_source_reports'/'wind'
URLS={
'ORSTED_2020':'https://cdn.orsted.com/-/media/annual2020/annual-report-2020.pdf',
'ORSTED_2021':'https://cdn.orsted.com/-/media/annual2021/annual-report-2021.pdf',
'ORSTED_2022':'https://cdn.orsted.com/-/media/2022-annual-report/orsted-annual-report-2022.pdf',
'ORSTED_2023':'https://cdn.orsted.com/-/media/annual-report-2023/orsted-ar-2023.pdf',
'ORSTED_2024':'https://cdn.orsted.com/-/media/annual2024/orsted-annual-report-2024.pdf',
'ORSTED_2025':'https://cdn.orsted.com/-/media/annual-2025/annual-report-2025.pdf',
'VWS_2020':'https://www.vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2020/210210_01_Annual_Report_2020.pdf.coredownload.inline.pdf',
'VWS_2021':'https://vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2021/Vestas_Annual_Report_2021.pdf.coredownload.pdf',
'VWS_2022':'https://www.vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2022/Vestas%20Annual%20Report%202022.pdf',
'VWS_2023':'https://www.vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2023/2023-annual-report/Annual%20Report%202023.pdf.coredownload.inline.pdf',
'VWS_2024':'https://www.vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2024/fy-2024/Vestas%20Annual%20Report%202024.pdf',
'VWS_2025':'https://www.vestas.com/content/dam/vestas-com/global/en/investor/reports-and-presentations/financial/2025/fy-2025/Vestas%20Annual%20Report%202025.pdf'}
def get(item):
 k,u=item;p=ARCHIVE/(k+'.pdf')
 try:
  ARCHIVE.mkdir(parents=True,exist_ok=True)
  if (ARCHIVE/(k+'.json')).exists():return
  if not p.exists():p.write_bytes(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read())
  pages=[]
  for page in PdfReader(p).pages:
   try:pages.append(page.extract_text(extraction_mode='layout'))
   except Exception as exc:pages.append('[EXTRACTION ERROR] '+str(exc))
  (ARCHIVE/(k+'.json')).write_text(json.dumps(pages))
  print(k,len(pages),flush=True)
 except Exception as e:print(k,repr(e),flush=True)
if __name__=='__main__':
 logging.getLogger('pypdf').setLevel(logging.ERROR)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:list(ex.map(get,URLS.items()))
