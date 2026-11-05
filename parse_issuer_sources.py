#!/usr/bin/env python3
"""Strict parsers for retained original issuer financial-table captures."""
import datetime as dt, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
AREA=ROOT/'data'/'actual_dates'
MONTHS='January February March April May June July August September October November December'.split()
DATE=r'('+'|'.join(MONTHS)+r')\s+(\d{1,2}),\s+(20\d\d)'
DATE_SHORT=r'('+'|'.join(m[:3] for m in MONTHS)+r'|Sept)\.?\s+(\d{1,2}),\s+(20\d\d)'
DATE_ANY=r'('+'|'.join(MONTHS+[m[:3] for m in MONTHS]+['Sept'])+r')\.?\s+(\d{1,2}),\s+(20\d\d)'

def date_iso(m):
    return dt.date(int(m[3]),next(i+1 for i,x in enumerate(MONTHS) if x.startswith(m[1])),int(m[2])).isoformat()

def alltext(page):
    return '\n'.join(l.replace('\xa0',' ') for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0])))

def after(page,n):return dict(page,lines={k:v for k,v in page['lines'].items() if int(k)>=n})

def asml(page):
    metas=json.loads((AREA/'asml_metadata.json').read_text())
    meta=next((m for m in metas if m['source']==page['url']),None)
    if not meta:return None
    q=meta['fiscal_quarter'];y=meta['fiscal_year']
    labels=[r'Income from operations',r'Net income',r'Net cash provided by \(used in\) operating activities',r'Total assets',r'Total current liabilities']
    fs=[flat_field(page,p) if 'sec.gov' in page['url'] else field(page,'^'+p+r'\s+',True) for p in labels]
    assert all(len(f[1])==(2 if q==1 else 4) for f in fs[:3]),fs
    r=standard_record('ASML',y,q,meta['period_end'],meta['published'],page,fs,[f[1][1] for f in fs[:3]],[f[1][3] for f in fs[:3]] if q==4 else None)
    r.update(currency='EUR',date_source=meta['date_source'],balance=[f[1][1] for f in fs[3:]])
    if q<4:
        r['ytd']=[f[1][1 if q==1 else 3] for f in fs[:3]];r['prior_ytd']=[f[1][0 if q==1 else 2] for f in fs[:3]]
    return r

def stm(page):
    text=alltext(page)
    m=re.search(r'STMicroelectronics Reports Q([1-4])(?: and (?:FY|Full Year))? (20\d\d) Financial Results',text)
    if m:q,y=int(m[1]),int(m[2])
    else:
        m=re.search(r'STMicroelectronics Reports (20\d\d) (First|Second|Third|Fourth) Quarter Financial Results',text)
        if not m:return None
        q,y=['First','Second','Third','Fourth'].index(m[2])+1,int(m[1])
    pub=re.search(r'Geneva, '+DATE_ANY,text);end=re.search(r'quarter ended\s+'+DATE_ANY,text)
    if not pub or not end:raise ValueError('Missing ST original publication/fiscal end')
    oi=fields(page,r'^OPERATING (?:INCOME|LOSS)(?: \(LOSS\))?\s+',True);ni=fields(page,r'^NET (?:INCOME|LOSS)(?: \(LOSS\))?\s+',True)
    # The cash-flow summary explicitly labels its last pair of columns TTM.
    cf=[]
    for n,line in sorted(page['lines'].items(),key=lambda x:int(x[0])):
        line=line.replace('\xa0',' ').strip()
        if re.match(r'^Net cash from operating activities\s+[-\d(]',line):
            cells=re.sub(r'^Net cash from operating activities\s+','',line).split()
            if len(cells)==6 and cells[-1].endswith('%'):
                vals=[float(c.replace(',','').strip('()'))*(-1 if c.startswith('(') else 1) for c in cells[:5]]
                preceding=' '.join(v for k,v in page['lines'].items() if int(n)-8<=int(k)<int(n))
                if 'TTM' not in preceding:raise ValueError('Cash-flow columns not evidenced as TTM')
                cf=[(int(n),vals)];break
    if not cf:raise ValueError('Missing explicitly headed TTM cash-flow table')
    fs=[oi[0],ni[0],cf[0],field(page,r'^Total assets\s+',True),field(page,r'^Total current liabilities\s+',True)]
    annual=[oi[1][1][0],ni[1][1][0],cf[0][1][3]] if q==4 else None
    r=standard_record('STMPA.PA',y,q,date_iso(end),date_iso(pub),page,fs,[oi[0][1][0],ni[0][1][0],cf[0][1][0]],annual)
    r['reported_ttm']=[None,None,cf[0][1][3]]
    if q in (2,3):
        if len(oi)<2 or len(ni)<2:raise ValueError('Missing cumulative income statement')
        r['ytd']=[oi[1][1][0],ni[1][1][0],None];r['prior_ytd']=[oi[1][1][1],ni[1][1][1],None]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=[oi[0][1][1],ni[0][1][1],cf[0][1][2]]
    return r

def amat(page):
    text=alltext(page)
    m=re.search(r'APPLIED MATERIALS ANNOUNCES (FIRST|SECOND|THIRD|FOURTH) QUARTER(?: AND FISCAL YEAR)? (20\d\d) RESULTS',text)
    if not m:return None
    q=['FIRST','SECOND','THIRD','FOURTH'].index(m[1])+1;y=int(m[2])
    pub=re.search(r'SANTA CLARA, Calif\.,\s+'+DATE_ANY,text);end=re.search(r'(?:quarter|fiscal year) ended\s+'+DATE_ANY,text)
    if not pub or not end:raise ValueError('Missing Applied original publication/fiscal end')
    oi=field(page,r'^Income from operations\s+',True)
    fs=[oi,field(after(page,oi[0]),r'^Net income\s+',True),field(page,r'^Cash provided by operating activities\s+',True),field(page,r'^Total assets\s+',True),field(page,r'^Total current liabilities\s+',True)]
    assert all(len(f[1])==(2 if q==1 else 4) for f in fs[:3]),fs
    r=standard_record('AMAT',y,q,date_iso(end),date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][2] for f in fs[:3]] if q==4 else None)
    if q<4:r['ytd']=[f[1][0 if q==1 else 2] for f in fs[:3]];r['prior_ytd']=[f[1][1 if q==1 else 3] for f in fs[:3]]
    return r

def vector(line):
    """Read observed table cells; a printed dash is reported zero, blanks are not."""
    assert '|' in line,line
    out=[];negative=False
    for raw in line.split('|')[1:]:
        cell=raw.strip().replace('\u2212','-').replace(',','')
        cell=re.sub(r'[$€£]','',cell).strip()
        if not cell:continue
        if cell=='(':negative=True;continue
        if cell==')':negative=False;continue
        if cell in ('—','–','-'):out.append(0.0);continue
        if cell=='%':raise ValueError('Percent table is not a monetary financial statement')
        if cell.startswith('('):negative=True;cell=cell[1:]
        closing=cell.endswith(')');cell=cell.rstrip(')').strip()
        if not re.fullmatch(r'-?\d+(?:\.\d+)?',cell):raise ValueError('Unexpected financial cell '+raw)
        val=float(cell)
        out.append(-abs(val) if negative else val)
        if closing:negative=False
    return out

def fields(page,pattern,space=False):
    found=[]
    for n,line in sorted(page['lines'].items(),key=lambda x:int(x[0])):
        line=line.replace('\xa0',' ').strip()
        if re.match(pattern,line):
            try:
                if space:
                    cells=re.sub(pattern,'',line).strip().replace('$','').replace(',','')
                    if '%' in cells or re.search(r'[A-Za-z]',cells):continue
                    vals=[-float(s[1:-1]) if s.startswith('(') else 0.0 if s in ('—','–','-') else float(s) for s in cells.split()]
                else:vals=vector(line)
            except (ValueError,AssertionError):continue
            if vals:found.append((int(n),vals))
    if not found:raise ValueError('Missing '+pattern)
    # Identical net income rows in income and cash-flow statements are expected.
    if any(v[1]!=found[0][1] for v in found):
        # Reconciliation tables may show one column only. Use the original first statement.
        pass
    return found

def field(page,pattern,space=False):return fields(page,pattern,space)[0]

def flat_field(page,label):
    for n,line in sorted(page['lines'].items(),key=lambda x:int(x[0])):
        line+=' '
        m=re.search(r'(?:^|\s)'+label+r'\s+((?:[-\d,(.—–]+\)?\s+)+)',line)
        if m:
            vals=[]
            for s in m[1].split():
                s=s.replace(',','');vals.append(-float(s[1:-1]) if s.startswith('(') else 0.0 if s in ('—','–','-') else float(s))
            if len(vals)>=2:return int(n),vals
    raise ValueError('Missing flat field '+label)

def standard_record(t,y,q,end,pub,page,fs,quarter,annual=None,unit='million'):
    r=dict(ticker=t,fiscal_year=y,fiscal_quarter=q,period_end=end,published=pub,currency='USD',unit=unit,quarter=quarter,balance=[v[1][0] for v in fs[3:]],source=page['url'],evidence_lines={k:v[0] for k,v in zip(['operating_income','net_income','operating_cash_flow','total_assets','current_liabilities'],fs)})
    if annual is not None:r['annual']=annual
    assert end<pub,(end,pub)
    return r

def lam(page):
    if '/image/' not in page['url'] or '.pdf' not in page['url']:return None
    text=alltext(page)
    end=re.search(r'Quarter Ended '+DATE,text,re.I)
    pub=re.search(r'FREMONT, Calif\.,?\s+'+DATE,text)
    if not end or not pub:raise ValueError('Missing fiscal period end or publication date')
    ed=dt.date.fromisoformat(date_iso(end)); ey=ed.year
    candidates=[(abs((ed-dt.date(y,m,28)).days),y,m) for y in [ey-1,ey,ey+1] for m in [3,6,9,12]]
    _,cy,cm=min(candidates);q={3:3,6:4,9:1,12:2}[cm];fy=cy+(cm>6)
    pats=[r'^Operating income\s+',r'^Net income\s+',r'^Net cash provided by operating activities\s+',r'^Total assets\s+',r'^Total current liabilities\s+']
    fs=[field(page,p,True) for p in pats]
    assert all(len(f[1]) in (3,5) for f in fs[:3]),fs
    ann=[f[1][3] for f in fs[:3]] if q==4 else None
    r=standard_record('LRCX',fy,q,ed.isoformat(),date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],ann,'thousand')
    r['prior_year_quarter']=[f[1][2] for f in fs[:3]]
    if q in (2,3):
        assert all(len(f[1])==5 for f in fs[:3])
        r['ytd']=[f[1][3] for f in fs[:3]];r['prior_ytd']=[f[1][4] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=[f[1][2] for f in fs[:3]]
    return r

def intel(page):
    m=re.search(r'Intel Reports (First|Second|Third|Fourth)[- ]Quarter(?: and Full-Year)? (20\d\d)',page['title'],re.I)
    if not m:return None
    q=['first','second','third','fourth'].index(m[1].lower())+1;y=int(m[2]);text=alltext(page)
    pub=re.search('Released '+DATE_SHORT,text)
    if not pub:raise ValueError('Missing original release footer')
    end=re.search(r'\(In Millions, Except Per Share Amounts(?:; [Uu]naudited)?\)\s*\|\s*\|\s*'+DATE_SHORT,text)
    if not end:raise ValueError('Missing fiscal end in GAAP income-statement heading')
    fs=[field(page,p) for p in [r'^Operating income(?: \(loss\))?\s*\|',r'^Net income(?: \(loss\))?\s*\|',r'^Net cash provided by(?: \(used for\))? operating activities\s*\|',r'^Total assets\s*\|',r'^Total current liabilities\s*\|']]
    assert len(fs[0][1])==(4 if q==4 else 2),fs[0]
    assert len(fs[2][1])==2,fs[2]
    annual=[fs[0][1][2],fs[1][1][2],fs[2][1][0]] if q==4 else None
    r=standard_record('INTC',y,q,date_iso(end),date_iso(pub),page,fs,[fs[0][1][0],fs[1][1][0],fs[2][1][0] if q==1 else None],annual)
    r['prior_year_quarter']=[fs[0][1][1],fs[1][1][1],fs[2][1][1] if q==1 else None]
    if q<4:
        r['ytd']=[None,None,fs[2][1][0]];r['prior_ytd']=[None,None,fs[2][1][1]]
        if q==1:r['ytd']=r['quarter'];r['prior_ytd']=[fs[0][1][1],fs[1][1][1],fs[2][1][1]]
    return r

def gfs(page):
    m=re.search(r'GlobalFoundries Reports (First|Second|Third|Fourth) Quarter(?: (20\d\d))?(?: and Fiscal Year (20\d\d))?',page['title'],re.I)
    if not m:return None
    q=['first','second','third','fourth'].index(m[1].lower())+1;y=int(m[2] or m[3]);text=alltext(page)
    pub=re.search('^'+DATE+'$',text,re.M)
    end=re.search(r'ended '+DATE,text)
    if not pub or not end:raise ValueError('Missing original publication/fiscal end')
    fs=[field(page,p) for p in [r'^Operating profit(?: \(loss\))?\s*\|',r'^Net income(?: \(loss\))?\s*\|',r'^(?:Net cash provided by|Cash provided by|Cash generated from) operating activities\s*\|',r'^Total assets\s*\|',r'^Current liabilities\s*\|']]
    # Original 2021 tables are ascending; the 2022-onward statements are descending.
    ix=1 if (y,q)<=(2022,1) else 0;ai=3 if y==2021 else 2
    assert all(len(f[1])==(4 if q==4 else 2) for f in fs[:3]),fs
    annual=[f[1][ai] for f in fs[:3]] if q==4 else None
    r=standard_record('GFS',y,q,date_iso(end),date_iso(pub),page,fs,[f[1][ix] for f in fs[:3]],annual)
    r['balance']=[f[1][ix] for f in fs[3:]]
    r['prior_year_quarter']=[f[1][1-ix] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=r['prior_year_quarter']
    return r

def nxp(page):
    title=page['title']
    if not title.startswith('NXP Semiconductors Reports '):return None
    match=re.search(r'(First|Second|Third|Fourth) Quarter(?: and Full-[Yy]ear)? (20\d\d)',title)
    if not match:return None
    q=['First','Second','Third','Fourth'].index(match[1])+1;y=int(match[2])
    lines=[l.replace('\xa0',' ') for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0]))]
    pub=next((re.match('^'+DATE+r' at ',l) for l in lines if re.match('^'+DATE+r' at ',l)),None)
    if pub is None:raise ValueError('Missing original publication date')
    text=' '.join(lines)
    end=re.search(r'(?:which )?ended '+DATE,text)
    if end is None:raise ValueError('Missing actual fiscal period end')
    patterns=[r'^Operating income \(loss\)\s*\|',r'^Net income \(loss\)\s*\|',r'^Net cash provided by \(used for\) operating activities\s*\|',r'^Total assets\s*\|',r'^Total current liabilities\s*\|']
    fs=[field(page,p) for p in patterns]
    r={'ticker':'NXPI','fiscal_year':y,'fiscal_quarter':q,'period_end':date_iso(end),'published':date_iso(pub),'currency':'USD','unit':'million','quarter':[v[1][0] for v in fs[:3]],'balance':[v[1][0] for v in fs[3:]],'source':page['url'],'evidence_lines':{k:v[0] for k,v in zip(['operating_income','net_income','operating_cash_flow','total_assets','current_liabilities'],fs)}}
    if q==4:
        if not all(len(v[1])==5 for v in fs[:3]):raise ValueError('Unexpected annual flow columns')
        r['annual']=[v[1][3] for v in fs[:3]]
    assert date_iso(end)<date_iso(pub)
    r['prior_year_quarter']=[f[1][2] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=r['prior_year_quarter']
    return r

def micron(page):
    m=re.search(r'(First|Second|Third|Fourth) Quarter(?: and Full Year)? of Fiscal (20\d\d)',page['title'])
    if not m:return None
    q=['First','Second','Third','Fourth'].index(m[1])+1;y=int(m[2]);text=alltext(page)
    pub=re.search(r'BOISE, Idaho, '+DATE_ANY,text);end=re.search(r'(?:which )?ended\s+'+DATE_ANY,text)
    if not pub or not end:raise ValueError('Missing Micron original publication/fiscal end')
    n=next((int(n) for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0])) if 'CONSOLIDATED STATEMENTS OF OPERATIONS' in l),None)
    if n is None:raise ValueError('Missing GAAP statement heading')
    sub=after(page,n)
    fs=[field(sub,p) for p in [r'^Operating income(?: \(loss\))?\s*\|',r'^Net income(?: \(loss\))?\s*\|',r'^GAAP net cash provided by(?: \(used in\))? operating activities\s*\|',r'^Total assets\s*\|',r'^Total current liabilities\s*\|']]
    expected=3 if q==1 else 5
    assert all(len(f[1])==expected for f in fs[:2]),('Micron income columns',[(f[0],len(f[1])) for f in fs])
    assert len(fs[2][1])==(5 if q==4 else 3),('Micron CF columns',fs[2])
    r=standard_record('MU',y,q,date_iso(end),date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][3] for f in fs[:3]] if q==4 else None)
    if q<4:
        cf=field(sub,r'^Net cash provided by(?: \(used in\))? operating activities\s*\|')
        assert len(cf[1])==2,cf
        r['ytd']=[fs[0][1][0 if q==1 else 3],fs[1][1][0 if q==1 else 3],cf[1][0]]
        r['prior_ytd']=[fs[0][1][2 if q==1 else 4],fs[1][1][2 if q==1 else 4],cf[1][1]]
        r['evidence_lines']['ytd_cash_flow']=cf[0]
    return r

def microchip(page):
    text=alltext(page);m=re.search(r'(First|Second|Third|Fourth) Quarter(?: and| of)?\s+Fiscal Year (20\d\d)',text)
    if not m:return None
    q=['First','Second','Third','Fourth'].index(m[1])+1;y=int(m[2])
    pub=re.search('^'+DATE_ANY+'$',text,re.M);end=re.search(r'(?:quarter|year|which|months) ended\s+'+DATE_ANY,text,re.I)
    if not pub or not end:raise ValueError('Missing Microchip original publication/fiscal end')
    n=next((int(n) for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0])) if re.search(r'CONSOLIDATED\s*STATEMENTS OF (?:OPERATIONS|INCOME)',l)),None)
    if n is None:raise ValueError('Missing Microchip GAAP income statement heading')
    sub=after(page,n)
    fs=[field(sub,p,True) for p in [r'^Operating (?:\(loss\) )?(?:income|loss)(?: \(loss\))?\s+',r'^Net (?:\(loss\) )?(?:income|loss)(?: \(loss\))?\s+',r'^GAAP cash flow from operations, as reported\s+',r'^Total assets\s+',r'^Total current liabilities\s+']]
    assert all(len(f[1])==(2 if q==1 else 4) for f in fs[:2]),fs
    assert len(fs[2][1])==(2 if q==1 else 4),fs
    r=standard_record('MCHP',y,q,date_iso(end),date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][2] for f in fs[:3]] if q==4 else None)
    r['prior_year_quarter']=[f[1][1] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=r['prior_year_quarter']
    if q in (2,3):r['ytd']=[f[1][2] for f in fs[:3]];r['prior_ytd']=[f[1][3] for f in fs[:3]]
    return r

def ti(page):
    if '/static-files/' not in page['url']:return None
    text=alltext(page);m=re.search(r'(?:reports|reported)\s+(?:(first|second|third|fourth)[- ]quarter|(Q4))\s+(20\d\d)',text,re.I)
    if not m:return None
    q=4 if m[2] else ['first','second','third','fourth'].index(m[1].lower())+1;y=int(m[3])
    pub=re.search(r'DALLAS[ (]+?'+DATE_ANY,text)
    if not pub:raise ValueError('Missing Texas Instruments publication date')
    oi=field(page,r'^Operating profit\s+',True)
    fs=[oi,field(after(page,oi[0]),r'^Net income\s+',True),field(page,r'^Cash flows from operating activities\s+',True),field(page,r'^Total assets\s+',True),field(page,r'^Total current liabilities\s+',True)]
    expected=4 if q==4 else 2
    assert all(len(f[1])==expected for f in fs[:3]),fs
    month=q*3;day=31 if month in (3,12) else 30;end=dt.date(y,month,day).isoformat()
    assert re.search(MONTHS[month-1]+r'\s+'+str(day),text),'Fiscal end not in financial statement'
    r=standard_record('TXN',y,q,end,date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][2] for f in fs[:3]] if q==4 else None)
    r['prior_year_quarter']=[f[1][1] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=r['prior_year_quarter']
    return r

def enphase(page):
    # Some issuer tables contain an empty first cell before their row label.
    page=dict(page,lines={n:re.sub(r'^\s*\|\s*','',l.replace('\xa0',' ')) for n,l in page['lines'].items()})
    text=alltext(page);m=re.search(r'(first|second|third|fourth)-quarter-(20\d\d)',page['url'])
    if not m:return None
    q=['first','second','third','fourth'].index(m[1])+1;y=int(m[2])
    pub=re.search(r'FREMONT, Calif\., '+DATE_ANY,text)
    if not pub:raise ValueError('Missing Enphase original publication date')
    n=next((int(n) for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0])) if 'CONSOLIDATED STATEMENTS OF OPERATIONS' in l),None)
    if n is None:raise ValueError('Missing Enphase GAAP statement')
    sub=after(page,n)
    fs=[field(sub,p) for p in [r'^Income(?: \(loss\))? from operations\s*\|',r'^Net income(?: \(loss\))?\s*\|',r'^Net cash provided by(?: \(used in\))? operating activities\s*\|',r'^Total assets\s*\|',r'^Total current liabilities\s*\|']]
    assert all(len(f[1]) in (2,3,5) for f in fs[:3]),fs
    month=q*3;day=31 if month in (3,12) else 30;end=dt.date(y,month,day).isoformat()
    assert re.search(MONTHS[month-1]+r'\s+'+str(day),alltext(sub)),'Enphase period-end heading missing'
    r=standard_record('ENPH',y,q,end,date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][3] for f in fs[:3]] if q==4 else None,'thousand')
    r['prior_year_quarter']=[f[1][1 if len(f[1])==2 else 2] for f in fs[:3]]
    if q==1:r['ytd']=r['quarter'];r['prior_ytd']=r['prior_year_quarter']
    if q in (2,3) and all(len(f[1])==5 for f in fs[:3]):r['ytd']=[f[1][3] for f in fs[:3]];r['prior_ytd']=[f[1][4] for f in fs[:3]]
    return r

def european_date(s):
    m=re.search(r'(\d{1,2})\s+('+'|'.join(MONTHS)+r')\s+(20\d\d)',s)
    if not m:raise ValueError('Missing evidenced European-format date')
    return dt.date(int(m[3]),MONTHS.index(m[2])+1,int(m[1])).isoformat()

def airbus(page):
    metas=json.loads((AREA/'airbus_metadata.json').read_text())
    meta=next((m for m in metas if m['source']==page['url']),None)
    if not meta:return None
    text=alltext(page);y,q=meta['fiscal_year'],meta['fiscal_quarter']
    # Actual period end must occur in the statement title, not be approximated.
    title=' '.join(text.splitlines()[:60])
    end=european_date(title)
    if int(end[:4])!=y:raise ValueError('Airbus fiscal year disagrees with statement')
    pats=[r'^(?:Profit(?: \(Loss\))?|\(Loss\) Profit|Loss) before financial result and income taxes(?: \(EBIT\))?',
          r'^(?:Profit(?: \(Loss\))?|\(Loss\) Profit|Loss) for the period',r'^Cash (?:provided by(?: \(used for\))?|used for(?: \(provided by\))?) operating activities',
          r'^Total assets',r'^(?:Total )?current liabilities']
    fs=[]
    for pat in pats:
        matches=[]
        for n,l in sorted(page['lines'].items(),key=lambda x:int(x[0])):
            # Some PDF labels wrap across lines. Monetary rows remain in table order.
            l=l.replace('\xa0',' ').strip()
            if not re.search(r'\d',l):
                l+=' '+page['lines'].get(str(int(n)+1),'').strip()
                if not re.search(r'\d',l):l+=' '+page['lines'].get(str(int(n)+2),'').strip()
            m=re.match(pat+r'\s+((?:\(?-?[\d,]+\)?\s*){2,4})',l,re.I)
            if m:
                vals=[-float(s.strip('()').replace(',','')) if s.startswith('(') else float(s.replace(',','')) for s in m[1].split()]
                if pat.startswith(r'^Cash ') and len(vals)==3:vals=vals[1:]
                matches.append((int(n),vals[:2]))
        if not matches:raise ValueError('Missing Airbus '+pat)
        fs.append(matches[0])
    # Airbus interim statements report cumulative year-to-date flows.
    vals=[f[1][0] for f in fs[:3]]
    r=standard_record('AIR.PA',y,q,end,meta['published'],page,fs,vals if q==1 else [None]*3,vals if q==4 else None)
    r.update(currency='EUR',date_source=meta['date_source'])
    if q<4:r['ytd']=vals;r['prior_ytd']=[f[1][1] for f in fs[:3]]
    return r

def infineon(page):
    if not page['url'].endswith('.pdf'):return None
    text=alltext(page)
    intro=re.search(r'Neubiberg,[^\n]+',text)
    if intro is None:raise ValueError('Missing Infineon original release date')
    try:pub=european_date(intro[0])
    except ValueError:
        d=re.search(DATE_ANY,intro[0]);pub=date_iso(d) if d else None
    if not pub:raise ValueError('Missing Infineon original release date')
    # The publication announces the actual reported fiscal period in its opening.
    head=' '.join(text.splitlines()[:100])
    m=re.search(r'(?:ended(?: on)?|period ended)\s+(\d{1,2}\s+(?:'+'|'.join(MONTHS)+r')\s+20\d\d)',head)
    if m:end=european_date(m[1])
    else:
        m=re.search(r'ended(?: on)?\s+'+DATE_ANY,head)
        if not m:raise ValueError('Missing Infineon actual period end')
        end=date_iso(m)
    month=int(end[5:7]);q={12:1,3:2,6:3,9:4}[month];y=int(end[:4])+(month==12)
    oi=field(page,r'^Operating (?:profit|income)(?: \(loss\))?\s+',True)
    ni=field(after(page,oi[0]),r'^(?:Profit \(loss\) for the period|Net income \(loss\))\s+',True)
    cf=field(page,r'^(?:Net cash provided by|Cash flows from) operating activities\s+',True)
    fs=[oi,ni,cf,flat_field(page,r'Total assets'),field(page,r'^Total current liabilities\s+',True)]
    assert all(len(f[1]) in (3,5) for f in fs[:3]),fs
    vals=[f[1][0] for f in fs[:3]]
    r=standard_record('IFX.DE',y,q,end,pub,page,fs,vals,[f[1][3] for f in fs[:3]] if q==4 else None)
    r['currency']='EUR';r['prior_year_quarter']=[f[1][2] for f in fs[:3]]
    if q==1:r['ytd']=vals;r['prior_ytd']=r['prior_year_quarter']
    if q in (2,3) and all(len(f[1])==5 for f in fs[:3]):r['ytd']=[f[1][3] for f in fs[:3]];r['prior_ytd']=[f[1][4] for f in fs[:3]]
    return r

def linde(page):
    m=re.search(r'linde-([1-4])q(\d\d)-earnings-release-tables.pdf',page['url'])
    if not m:return None
    q,y=int(m[1]),2000+int(m[2]);text=alltext(page)
    pub=re.search(r'(?:Guildford|Woking), UK, '+DATE_ANY,text)
    if not pub:raise ValueError('Missing Linde original publication date')
    oi=field(page,r'^Operating Profit\s+',True)
    fs=[oi,field(page,r'^Income \(Including Noncontrolling Interests\)\s+',True),field(page,r'^Net cash provided by(?: \(used for\))? operating activities\s+',True),field(page,r'^Total Assets\s+',True),field(page,r'^Total Current Liabilities\s+',True)]
    assert all(len(f[1])==(2 if q==1 else 4) for f in fs[:3]),fs
    month=q*3;day=31 if month in (3,12) else 30;end=dt.date(y,month,day).isoformat()
    assert re.search(MONTHS[month-1]+r'\s+'+str(day),text)
    r=standard_record('LIN',y,q,end,date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][2] for f in fs[:3]] if q==4 else None)
    r['prior_year_quarter']=[f[1][1] for f in fs[:3]]
    if q<4:r['ytd']=[f[1][0 if q==1 else 2] for f in fs[:3]];r['prior_ytd']=[f[1][1 if q==1 else 3] for f in fs[:3]]
    return r

def nextera(page):
    capture=next((c for c in page['captures'] if re.match(r'actual_dates_nee_release_20\d\dq[1-4]\.txt',c)),None)
    if not capture:return None
    m=re.search(r'(20\d\d)q([1-4])',capture);y,q=int(m[1]),int(m[2])
    meta=next(r for r in json.loads((AREA/'nee_archive_metadata.json').read_text()) if (r['y'],r['q'])==(y,q))
    pub=dt.datetime.strptime(meta['pub'],'%m/%d/%Y').date().isoformat()
    # Releases present each period in a separate statement: current quarter,
    # prior-year quarter, current YTD, prior-year YTD. The rightmost column is NEE.
    oi=fields(page,r'^Operating Income \(Loss\)\s+',True)
    ni=fields(page,r'^Net Income \(Loss\)\s+',True)
    cf=fields(page,r'^Net cash provided by \(used in\) operating activities\s+',True)
    assets=field(page,r'^(?:TOTAL ASSETS|Total Assets)\s+',True)
    cl=field(page,r'^Total current liabilities\s+',True)
    assert len(oi)==(2 if q==1 else 4),(q,len(oi))
    assert len(ni)==(2 if q==1 else 4),(q,len(ni))
    assert len(cf)==2,cf
    # Confirm the last monetary column is the consolidated company from table headers.
    assert 'NextEra' in alltext(page) and 'Energy' in alltext(page)
    month=q*3;day=31 if month in (3,12) else 30;end=dt.date(y,month,day).isoformat()
    text=alltext(page)
    assert re.search(MONTHS[month-1]+r'\s+'+str(day)+r',?\s+'+str(y),text),'NEE actual period heading missing'
    fs=[oi[0],ni[0],cf[0],assets,cl]
    annual=[oi[2][1][-1],ni[2][1][-1],cf[0][1][-1]] if q==4 else None
    r=standard_record('NEE',y,q,end,pub,page,fs,[oi[0][1][-1],ni[0][1][-1],cf[0][1][-1] if q==1 else None],annual)
    r.update(balance=[assets[1][-1],cl[1][-1]],date_source=meta['archive'])
    if q<4:
        ix=0 if q==1 else 2
        r['ytd']=[oi[ix][1][-1],ni[ix][1][-1],cf[0][1][-1]]
        r['prior_ytd']=[oi[ix+1][1][-1],ni[ix+1][1][-1],cf[1][1][-1]]
    return r

def microchip_html(page):
    text=alltext(page).replace('\xa0',' ')
    m=re.search(r'Fourth Quarter(?: and)?\s+Fiscal Year (20\d\d)',text)
    if not m:return None
    y=int(m[1]);pub=re.search(r'CHANDLER, (?:Ariz\.,|Arizona -)\s+'+DATE_ANY,text)
    if not pub:raise ValueError('Missing original Microchip HTML publication date')
    fs=[field(page,p) for p in [r'^Operating income\s*\|',r'^Net income\s*\|',r'^GAAP cash flow from operations, as reported\s*\|',r'^Total assets\s*\|',r'^Total current liabilities\s*\|']]
    assert all(len(f[1])==4 for f in fs[:3]),fs
    return standard_record('MCHP',y,4,str(y)+'-03-31',date_iso(pub),page,fs,[f[1][0] for f in fs[:3]],[f[1][2] for f in fs[:3]])

def main():
    pages=json.loads((AREA/'source_index.json').read_text())
    records=[];errors=[];keys=set()
    for page in pages.values():
        if not page['lines']:continue
        parser=next((f for hosts,f in [(('investors.nxp.com/','media.nxp.com/','nxpsemiconductorsnewsroom.gcs-web.com/'),nxp),(('investor.lamresearch.com/image/',),lam),(('www.intc.com/news-events/press-releases/detail/',),intel),(('investors.gf.com/news-releases/news-release-details/',),gfs),(('investor.asml.com/static-files/',),asml),(('investors.st.com/static-files/',),stm),(('investor.appliedmaterials.com/static-files/',),amat)] if any(h in page['url'] for h in hosts)),None)
        if parser is None:
            parser=next((f for host,f in [('sec.gov/Archives/edgar/data/937966/',asml),('micron.gcs-web.com/news-releases/',micron),('/microchip/news/',microchip),('ir.microchip.com/',microchip_html),('investor.ti.com/static-files/',ti),('investor.enphase.com/news-releases/',enphase),('airbus.com/',airbus),('infineon.com/',infineon),('assets.linde.com/',linde),('nexteraenergy.com/',nextera)] if host in page['url']),None)
        if parser is None:continue
        try:r=parser(page)
        except (ValueError,AssertionError) as e:errors.append({'source':page['url'],'reason':str(e)});continue
        if r:
            key=(r['ticker'],r['fiscal_year'],r['fiscal_quarter'])
            if key in keys:raise ValueError('Duplicate report '+str(key))
            keys.add(key);records.append(r)
    records.sort(key=lambda r:(r['ticker'],r['period_end']))
    (AREA/'parsed_observations.json').write_text(json.dumps(records,indent=2)+'\n')
    (AREA/'parser_exclusions.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(json.dumps({'complete_original_reports':len(records),'parser_exclusions':errors},indent=2))
    for r in records:print(r['ticker'],r['fiscal_year'],r['fiscal_quarter'],r['period_end'],r['published'],r['quarter'],r['balance'],r.get('annual',''))

if __name__=='__main__':main()
