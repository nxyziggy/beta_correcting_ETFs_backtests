"""Optional source retrieval. Offline backtests use the committed factual records.

SEC companyfacts/submission endpoints are mutable. The source manifest records
hashes of the exact captured versions; new downloads must be reviewed if changed.
Set SEC_USER_AGENT to your own descriptive user-agent and contact address before
downloading. Credentials or personal contact details must not be hard-coded here.
"""
from pathlib import Path
import hashlib,json,os,time,urllib.request
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
DEST=ROOT.parent/'us_source_reports/tsm_gev'

def sec_request_headers():
    user_agent=os.environ.get('SEC_USER_AGENT','').strip()
    if not user_agent:
        raise SystemExit('Set SEC_USER_AGENT to a descriptive user-agent with your contact address before downloading SEC sources.')
    return {'User-Agent':user_agent}

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for row in json.loads((HERE/'source_manifest.json').read_text()):
        path=DEST/row['file']
        if not path.exists():
            req=urllib.request.Request(row['url'],headers=sec_request_headers())
            path.write_bytes(urllib.request.urlopen(req,timeout=90).read())
            time.sleep(.3)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        print(path.name,'MATCH' if actual==row['sha256'] else 'CHANGED: review source version before extraction')

if __name__=='__main__':main()
