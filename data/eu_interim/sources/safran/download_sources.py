import concurrent.futures,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[5]/'eu_source_reports'/'interim_safran'
root.mkdir(parents=True,exist_ok=True)
sources={2021:404856,2022:419356,2023:432771,2024:441806,2025:448922,2026:451695}
def fetch(item):
 y,i=item;p=root/f'SAF_H1_{y}.pdf';u=f'https://www.safran-group.com/download/media/{i}'
 r=subprocess.run(['curl','-L','--fail','--retry','1','--max-time','45','-A','Mozilla/5.0','-o',str(p),u],capture_output=True)
 return {'year':y,'url':u,'ok':r.returncode==0,'path':str(p),'error':r.stderr.decode()[-200:] if r.returncode else ''}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for r in pool.map(fetch,sources.items()): print(r)
