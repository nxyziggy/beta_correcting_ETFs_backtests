from html.parser import HTMLParser
from pathlib import Path
from decimal import Decimal
import json,re
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT.parent/'us_source_reports/power'
class IX(HTMLParser):
 def __init__(self):super().__init__();self.cs={};self.context=None;self.datepart=None;self.num=None;self.nums=[]
 def handle_starttag(self,t,aa):
  a=dict(aa)
  if t=='xbrli:context':self.context={'id':a['id'],'dimension':False}
  if self.context is not None:
   if t in ('xbrldi:explicitmember','xbrldi:typedmember'):self.context['dimension']=True
   if t in ('xbrli:startdate','xbrli:enddate','xbrli:instant'):self.datepart=t
  if t=='ix:nonfraction':self.num=dict(a,text='')
 def handle_endtag(self,t):
  if t=='xbrli:context':self.cs[self.context['id']]=self.context;self.context=None
  if t in ('xbrli:startdate','xbrli:enddate','xbrli:instant'):self.datepart=None
  if t=='ix:nonfraction' and self.num is not None:self.nums.append(self.num);self.num=None
 def handle_data(self,s):
  if self.datepart and self.context is not None:self.context[self.datepart]=s
  if self.num is not None:self.num['text']+=s
 def values(self):
  out={}
  for n in self.nums:
   c=self.cs.get(n['contextref'],{})
   if c.get('dimension'):continue
   st=c.get('xbrli:startdate');en=c.get('xbrli:enddate',c.get('xbrli:instant'))
   tx=n['text'].replace(',','').replace('\xa0','').strip()
   if tx in ('—','–','-'):v=Decimal(0)
   else:
    try:v=Decimal(tx)
    except:continue
   v*=Decimal(10)**int(n.get('scale','0'))
   if n.get('sign')=='-':v=-v
   out.setdefault((n['name'],st,en),set()).add(v)
  return out
facts=json.loads((ROOT/'data/us_restoration/sources/power/facts.json').read_text())
cache={};checked=0;errors=[]
for r in facts:
 if 'concept' not in r:continue
 name=r['source'].split('/')[-1]
 if name not in cache:
  p=IX();p.feed((BASE/name).read_text());cache[name]=p.values()
 key=(r['concept'],r.get('start'),r['end']);vs=cache[name].get(key,set())
 if Decimal(r['val']) not in vs:errors.append(dict(file=name,key=key,expected=r['val'],values=[str(x) for x in vs]))
 checked+=1
print(json.dumps(dict(checked=checked,filings=len(cache),errors=errors),indent=2))
