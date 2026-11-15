"""Optional source retrieval. Offline backtests use the committed factual records.

SEC companyfacts/submission endpoints are mutable. The source manifest records
hashes of the exact captured versions; new downloads must be reviewed if changed.
"""
from pathlib import Path
import hashlib,json,time,urllib.request
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
DEST=ROOT.parent/'us_source_reports/tsm_gev'
HEAD={'User-Agent':'Financial research nicolas.zhang@mines-paristech.fr'}

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for row in json.loads((HERE/'source_manifest.json').read_text()):
        path=DEST/row['file']
        if not path.exists():
            req=urllib.request.Request(row['url'],headers=HEAD)
            path.write_bytes(urllib.request.urlopen(req,timeout=90).read())
            time.sleep(.3)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        print(path.name,'MATCH' if actual==row['sha256'] else 'CHANGED: review source version before extraction')

if __name__=='__main__':main()
