#!/usr/bin/env python3
"""Merge captured source lines for audit and reviewed numerical transcription."""
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def texts(p):
    raw=p.read_text()
    if p.suffix=='.json':
        obj=json.loads(raw)
        return '\n'.join(x['text'] for x in obj.get('content',[]) if x.get('type')=='text')
    return raw

def main():
    pages={}
    for p in sorted((ROOT.parent/'tmp').glob('actual_dates_*')):
        if p.suffix not in ('.txt','.json'):continue
        try: raw=texts(p)
        except (ValueError,TypeError):continue
        for block in re.split(r'\n-{20,}\n',raw):
            m=re.search(r'^([^\n]*) \((https?://[^\n]+)\)\s*$',block,re.M)
            if not m:continue
            url=m[2];page=pages.setdefault(url,{'url':url,'title':m[1],'lines':{},'refs':[],'captures':[]})
            ref=re.search(r'【(turn\d+\w+)】',block)
            if ref and ref[1] not in page['refs']:page['refs'].append(ref[1])
            page['captures'].append(p.name)
            total=re.search(r'Total lines: (\d+)',block)
            if total:page['total_lines']=int(total[1])
            for line in block.splitlines():
                match=re.match(r'L(\d+)(?:@P[\d-]+)?:\s?(.*)',line)
                if match:page['lines'][match[1]]=match[2]
    out=ROOT/'data'/'actual_dates'/'source_index.json'
    out.write_text(json.dumps(pages,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'pages':len(pages),'captured_lines':sum(len(p['lines']) for p in pages.values())}))

if __name__=='__main__':main()
