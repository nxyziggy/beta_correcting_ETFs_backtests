#!/usr/bin/env python3
"""Reproducible reduced-factor research backtest; no network or mock inputs.

See HOLDINGS_RULE_CHANGE.md and the inherited METHOD_LOCK.md. Current standardized histories are NOT point-in-time archives.
Run: python backtest.py --output results
"""
import argparse, bisect, calendar, csv, datetime as dt, json, math, statistics
from functools import partial
from collections import defaultdict
from pathlib import Path
from prepare_data import DATA, ROOT, endmonth, write_csv

def read_csv(path):
    return list(csv.DictReader(path.open(encoding='utf-8'))) if path.exists() else []

def percentile(xs,p):
    xs=sorted(xs); pos=(len(xs)-1)*p; a=math.floor(pos); b=math.ceil(pos)
    return xs[a]+(xs[b]-xs[a])*(pos-a)

def ranks(values):
    xs=sorted(values.values()); n=len(xs)
    return {t:(bisect.bisect_left(xs,v)+bisect.bisect_right(xs,v))/(2*n) for t,v in values.items()}

def rebalance(values,cash,weights,cost_rate):
    """Solve post-trade NAV = pre-trade NAV minus costs on actual bought/sold dollars."""
    pre=sum(values.values())+cash
    names=sorted(set(values)|set(weights))
    def notional(nav): return sum(abs(weights.get(t,0)*nav-values.get(t,0)) for t in names)
    lo,hi=0.0,pre
    for _ in range(70):
        mid=(lo+hi)/2
        if mid+cost_rate*notional(mid)>pre: hi=mid
        else: lo=mid
    post=(lo+hi)/2; traded=notional(post); cost=cost_rate*traded
    out={t:w*post for t,w in weights.items() if w>0}
    leftover=post-sum(out.values())
    assert abs(pre-post-cost)<max(1e-9,pre*1e-10)
    assert leftover>-max(1e-9,post*1e-10)
    trades=[{'ticker':t,'old_value':values.get(t,0),'new_value':out.get(t,0),
             'trade_value':out.get(t,0)-values.get(t,0),'cost':abs(out.get(t,0)-values.get(t,0))*cost_rate}
            for t in sorted(names) if abs(out.get(t,0)-values.get(t,0))>1e-10]
    return out,max(0.0,leftover),cost,traded,trades

class Inputs:
    def __init__(self,prefer_daily_overlap=True):
        self.price_policy='dated_daily_overlap' if prefer_daily_overlap else 'monthly_vendor_only'
        self.universe={r['ticker']:r for r in json.loads((DATA/'universe.json').read_text())}
        self.prices=defaultdict(dict);self.raw=defaultdict(dict)
        for r in read_csv(DATA/'prices_monthly.csv'):
            if r['status']=='complete':
                self.prices[r['ticker']][r['date']]=float(r['adjusted_close'])
                self.raw[r['ticker']][r['date']]=float(r['unadjusted_close'])
        # June EDF value is the documented cash consideration, not a stale exchange quote.
        if '2023-06-30' in self.prices['EDF.PA']: self.prices['EDF.PA']['2023-06-30']=12.0
        self.fx=defaultdict(dict)
        for r in read_csv(DATA/'fx_daily.csv'): self.fx[r['series']][r['date']]=float(r['rate'])
        self.fx_dates={s:sorted(ds) for s,ds in self.fx.items()}
        self.fx_log={}
        self.annual=read_csv(DATA/'financials_vendor.csv')+read_csv(DATA/'financials_supplement.csv')
        self.quarterly=read_csv(DATA/'financials_quarterly.csv')
        self.primary=read_csv(DATA/'financials_primary.csv')
        self.policy=read_csv(DATA/'policy_eligibility.csv')
        self.daily=defaultdict(dict)
        for p in sorted((DATA/'daily').glob('*.txt')):
            for line in p.read_text().splitlines():
                bits=[x.strip() for x in line.split('|')]
                if len(bits)<6: continue
                try: day=dt.datetime.strptime(bits[0],'%b %d, %Y').date().isoformat()
                except ValueError: continue
                try: adj=float(bits[5].replace(',',''))
                except ValueError: continue
                if adj>0: self.daily[p.stem][day]=adj
        # Adjusted-price levels are arbitrary across vendors. Chain observed RETURNS,
        # never splice their raw levels. Dated daily month-end ratios take priority.
        self.monthly_original={t:dict(ds) for t,ds in self.prices.items()}
        self.price_bridge=[]
        for t,ds in sorted(self.prices.items()):
            dates=sorted(ds)
            for previous,date in zip(dates,dates[1:]):
                if previous not in self.daily[t] or date not in self.daily[t]: continue
                a,b=dt.date.fromisoformat(previous),dt.date.fromisoformat(date)
                if (b.year-a.year)*12+b.month-a.month!=1:continue
                daily_gross=self.daily[t][date]/self.daily[t][previous]
                original_gross=self.monthly_original[t][date]/self.monthly_original[t][previous]
                if prefer_daily_overlap: ds[date]=ds[previous]*daily_gross
                self.price_bridge.append(dict(ticker=t,start=previous,end=date,
                    monthly_source_gross=original_gross,dated_daily_gross=daily_gross,
                    difference=daily_gross-original_gross,daily_start_adjusted=self.daily[t][previous],
                    daily_end_adjusted=self.daily[t][date],effective_return_index=ds[date],
                    chosen_source='dated daily adjusted closes' if prefer_daily_overlap else 'monthly vendor sensitivity',
                    source_file='data/daily/'+t+'.txt'))

        self.extension_config=json.loads((DATA/'extension_config.json').read_text())
        self.extension_daily=defaultdict(dict);self.extension_quotes={}
        for r in read_csv(DATA/'extension_prices_daily.csv'):
            self.extension_daily[r['ticker']][r['date']]=float(r['adjusted_close'])
        self.quote_dates={t:sorted(ds) for t,ds in self.extension_daily.items()}
        self.month_end_observations={}
        for r in read_csv(DATA/'extension_month_end_prices.csv'):
            self.month_end_observations[(r['ticker'],r['date'])]=r
        for t,ds in sorted(self.extension_daily.items()):
            previous=self.extension_config['previous_complete_month_end']
            for date in sorted(d for ticker,d in self.month_end_observations if ticker==t and d>previous):
                a=self.month_end_observations[(t,previous)];b=self.month_end_observations[(t,date)]
                gross=float(b['adjusted_close'])/float(a['adjusted_close'])
                self.prices[t][date]=self.prices[t][previous]*gross
                self.raw[t][date]=float(b['close'])
                previous=date

    def daily_price(self,t,date,required=True):
        """Latest observed close on/before a calendar label, never a synthetic quote."""
        if date>=self.extension_config['previous_complete_month_end'] and t in self.extension_daily:
            ds=self.extension_daily[t];dates=self.quote_dates[t]
        else:ds=self.daily[t];dates=sorted(ds)
        i=bisect.bisect_right(dates,date)-1
        if i<0 or (dt.date.fromisoformat(date)-dt.date.fromisoformat(dates[i])).days>4:
            if required:raise ValueError(f'Missing dated daily anchor {t} {date}')
            return None
        observed=dates[i]
        self.extension_quotes[(t,date)]={'ticker':t,'valuation_date':date,'observation_date':observed,'adjusted_close':ds[observed]}
        return ds[observed]

    def fx_value(self,s,date,monthly=False):
        ds=self.fx_dates[s];idx=bisect.bisect_right(ds,date)-1
        if idx<0: raise ValueError(f'No historical FX {s} {date}')
        used=ds[idx];age=(dt.date.fromisoformat(date)-dt.date.fromisoformat(used)).days
        if age>4: raise ValueError(f'Stale FX {s} at {date}: {used}')
        if monthly and used[:7]!=date[:7]: raise ValueError('FX crossed month boundary')
        self.fx_log[(s,date)]={'series':s,'valuation_date':date,'observation_date':used,'rate':self.fx[s][used],'age_days':age}
        return self.fx[s][used]

    def currency(self,t):
        if t in self.universe: return self.universe[t]['price_currency']
        return 'EUR' if t in ('EXV3.DE','IQQH.DE') else 'USD'

    def conversion(self,t,date,region,monthly=False):
        c=self.currency(t)
        if region=='US':
            if c!='USD': raise ValueError('Unexpected non-USD US price')
            return 1.0
        if c=='EUR': return 1.0
        usd_eur=self.fx_value('DEXUSEU',date,monthly)
        if c=='USD': return 1/usd_eur
        series={'CHF':'DEXSZUS','DKK':'DEXDNUS','NOK':'DEXNOUS'}[c]
        return 1/(usd_eur*self.fx_value(series,date,monthly))

    def price(self,t,date,region):
        p=self.prices[t].get(date)
        if p is None or p<=0: raise ValueError(f'Missing actual monthly price: {t} {date}')
        return p*self.conversion(t,date,region,True)

    def available(self,record,annual_lag):
        date=dt.date.fromisoformat(record['availability_date'])
        if record['period_type']=='annual' and record['panel'].startswith('vendor'):
            date=dt.date.fromisoformat(record['period_end'])+dt.timedelta(days=annual_lag)
        return date

    def freshness_days(self, record):
        """Maximum report age; timing experiments may offset an artificial delay."""
        return 550 if record['period_type']=='annual' else 275

    def signals(self,region,date,panel,gate=False,annual_lag=180):
        execution=dt.date.fromisoformat(date); cutoff=execution.replace(day=1)
        rows=self.annual[:]
        if panel=='hybrid': rows+=self.quarterly
        if panel=='quarterly': rows=self.quarterly
        if panel=='primary': rows=self.primary
        selected={}; reasons={}
        for t,u in self.universe.items():
            if u['region']!=region: continue
            if u['listing_start'] and date<u['listing_start']: reasons[t]='not yet regularly listed';continue
            if u['delisting_date'] and date>=u['delisting_date']: reasons[t]='delisted';continue
            if date not in self.prices[t]: reasons[t]='no observed monthly price';continue
            if gate:
                elig=[r for r in self.policy if r['ticker']==t and r['start_date']<cutoff.isoformat() and (not r.get('end_date') or cutoff.isoformat()<r['end_date'])]
                if not elig: reasons[t]='no captured dated policy participation evidence';continue
            eligible=[]
            for r in rows:
                if r['ticker']!=t or self.available(r,annual_lag)>=cutoff: continue
                age=(execution-dt.date.fromisoformat(r['period_end'])).days
                if age>self.freshness_days(r): continue
                eligible.append(r)
            if not eligible: reasons[t]='no usable dated financial observation';continue
            r=max(eligible,key=lambda a:(a['period_end'],a['period_type']=='trailing',a['panel'].startswith('primary')))
            assets=float(r['total_assets']);cl=float(r['current_liabilities'])
            if panel in ('quarterly','primary'):
                if not r['prior_total_assets'] or not r['prior_current_liabilities']:
                    reasons[t]='missing prior balance for average denominator';continue
                assets=(assets+float(r['prior_total_assets']))/2
                capital=(float(r['total_assets'])-cl+float(r['prior_total_assets'])-float(r['prior_current_liabilities']))/2
            else: capital=assets-cl
            if assets<=0 or capital<=0: reasons[t]='non-positive capital denominator';continue
            s=dict(r)
            s.update(roce=float(r['operating_income'])/capital,
                     cash_accruals=(float(r['net_income'])-float(r['operating_cash_flow']))/assets,
                     available_used=self.available(r,annual_lag).isoformat(),report_age_days=(execution-dt.date.fromisoformat(r['period_end'])).days)
            selected[t]=s
        if selected:
            rank_r=ranks({t:r['roce'] for t,r in selected.items()});rank_q=ranks({t:-r['cash_accruals'] for t,r in selected.items()})
            for t,r in selected.items():
                r.update(rank_roce=rank_r[t],rank_quality=rank_q[t],score=math.exp((.25*math.log(rank_r[t])+.12*math.log(rank_q[t]))/.37))
        return selected,reasons

def benchmark(region): return {'SOXX':.6,'ICLN':.4} if region=='US' else {'EXV3.DE':.5,'IQQH.DE':.5}

def constrained_selection(sc,active,rule,quarter_end,minimum,maximum):
    """Select from observed scores; a labeled floor takes priority over the entry gate."""
    if len(sc)<max(4,minimum):
        raise ValueError('Insufficient observed coverage to maintain the requested stock count')
    q25=percentile([r['score'] for r in sc.values()],.25)
    threshold=percentile([r['score'] for r in sc.values()],.75 if rule=='q75' else .5)
    rank=lambda t:(-sc[t]['score'],t)
    available_active=active&set(sc)
    survivors={t for t in available_active if not quarter_end or sc[t]['score']>q25}
    qualifiers={t for t in sc if quarter_end and sc[t]['score']>threshold}
    candidates=survivors|qualifiers
    selected=set(sorted(candidates,key=rank)[:maximum])
    cap_removed=candidates-selected
    floor=[]
    for t in sorted((t for t in sc if t not in selected and sc[t]['score']>q25),key=rank):
        if len(selected)>=minimum:break
        selected.add(t);floor.append(t)
    if not minimum<=len(selected)<=maximum:
        raise ValueError('Cannot satisfy holding bounds from observed stocks above the Q25 exit threshold')
    return selected,set(floor),cap_removed,threshold,{
        'covered':len(sc),'prior_holdings':len(active),'covered_prior_holdings':len(available_active),
        'normal_qualifiers':len(qualifiers),'retained_before_cap':len(survivors),'candidate_count':len(candidates),
        'capacity_exclusions':len(cap_removed),'floor_admissions':len(floor),'final_holdings':len(selected),
        'below_entry_gate_held':sum(sc[t]['score']<=threshold for t in selected),
        'minimum_holdings':minimum,'maximum_holdings':maximum,'quarter_end':quarter_end}

def run(inputs,region,panel,rule,cost_bps,gate=False,annual_lag=180,start=None,minimum_holdings=1,maximum_holdings=9,selection_policy=None):
    """Run the fixed accounting engine, optionally delegating stock selection.

    A custom policy's select(sc, active, rule, quarter_end, minimum, maximum,
    date) returns the constrained_selection tuple. Give each run a fresh policy
    instance when it tracks history. Coverage and capacity exit labels remain
    engine-owned; other exits may use exit_reason(ticker) and exit_streak(ticker).
    With no policy the historical selection, event schema and results are unchanged.
    """
    assert rule in ('q75','q50','equal')
    assert 1<=minimum_holdings<=maximum_holdings
    key=f'{region}_{panel}_{"policy_" if gate else ""}{rule}_{cost_bps:g}bp_lag{annual_lag}'+(f'_from{start}' if start else '')+('_digrin_only' if inputs.price_policy=='monthly_vendor_only' else '')
    dates=sorted(set.intersection(*(set(inputs.prices[t]) for t in benchmark(region))))
    history_floor=min('2020-01-01',start) if start else '2020-01-01'
    dates=[d for d in dates if history_floor<=d<=inputs.extension_config['complete_month_end'] and (start is None or d>=start)]
    values={};cash=100.;bvalues={};bcash=100.;ever_held=set()
    monthly=[];scores=[];trades=[];events=[];holdings=[];coverage=[];selection_audit=[];previous=None;started=False
    for date in dates:
        sc,reasons=inputs.signals(region,date,panel,gate,annual_lag)
        quarter_end=int(date[5:7]) in (3,6,9,12)
        decision=quarter_end
        if not started and len(sc)<max(4,minimum_holdings): continue
        if not started and not decision: continue
        if not started: started=True
        initial=previous is None
        old_nav=sum(values.values())+cash
        if previous:
            for t in list(values):
                values[t]*=inputs.price(t,date,region)/inputs.price(t,previous,region)
                if t=='EDF.PA' and date=='2023-06-30':
                    cash+=values.pop(t)
                    events.append({'date':date,'ticker':t,'event':'CASH_DELIST','score':'','threshold':'','recovery_streak':0})
            for t in bvalues: bvalues[t]*=inputs.price(t,date,region)/inputs.price(t,previous,region)
        pre=sum(values.values())+cash
        q25=q50=q75=None
        target={};retained=set()
        if len(sc)>=max(4,minimum_holdings):
            q25,q50,q75=(percentile([r['score'] for r in sc.values()],p) for p in (.25,.5,.75))
            if rule=='equal': retained=set(sc) if decision else set(values)&set(sc)
            else:
                active=set(values)
                if selection_policy is None:
                    retained,floor,cap_removed,threshold,audit=constrained_selection(sc,active,rule,quarter_end,minimum_holdings,maximum_holdings)
                else:
                    retained,floor,cap_removed,threshold,audit=selection_policy.select(
                        sc=sc,active=set(active),rule=rule,quarter_end=quarter_end,
                        minimum=minimum_holdings,maximum=maximum_holdings,date=date)
                    retained,floor,cap_removed=set(retained),set(floor),set(cap_removed)
                    assert retained<=set(sc),'Selection policy retained an uncovered/ineligible stock'
                    assert floor<=retained and cap_removed<=set(sc) and not retained&cap_removed
                    assert minimum_holdings<=len(retained)<=maximum_holdings
                selection_audit.append({'date':date,**audit,'entry_threshold':threshold,'exit_threshold':q25})
                for t in sorted(active-retained):
                    if t not in sc:event='EXIT_COVERAGE_OR_ELIGIBILITY'
                    elif t in cap_removed:event='EXIT_CAPACITY'
                    elif selection_policy is None:event='EXIT_BOTTOM_QUARTILE'
                    else:
                        reason=getattr(selection_policy,'exit_reason',None)
                        event=reason(t) if callable(reason) else 'EXIT_SCORE_RULE'
                        assert isinstance(event,str) and event.startswith('EXIT_')
                        assert event not in ('EXIT_COVERAGE_OR_ELIGIBILITY','EXIT_CAPACITY'), 'Reserved engine exit label'
                    record={'date':date,'ticker':t,'event':event,'score':sc[t]['score'] if t in sc else '',
                        'threshold':q25 if 'BOTTOM_QUARTILE' in event else '', 'recovery_streak':0}
                    streak=getattr(selection_policy,'exit_streak',None)
                    if callable(streak):
                        record['score_exit_streak']=0 if event in ('EXIT_COVERAGE_OR_ELIGIBILITY','EXIT_CAPACITY') else streak(t)
                    events.append(record)
                for t in sorted(retained-active):
                    event='ENTER_FLOOR' if t in floor else 'REENTER' if t in ever_held else 'ENTER_INITIAL' if initial else 'ENTER_THRESHOLD'
                    events.append({'date':date,'ticker':t,'event':event,'score':sc[t]['score'],'threshold':threshold,
                        'recovery_streak':0 if t in floor else 1})
                for t in sorted(cap_removed-active):
                    events.append({'date':date,'ticker':t,'event':'EXCLUDE_CAPACITY','score':sc[t]['score'],'threshold':'','recovery_streak':0})
            if retained:
                target={t:1/len(retained)+(0.015 if rule!='equal' and sc[t]['score']>=q75 else 0) for t in sorted(retained)}
                total=sum(target.values());target={t:w/total for t,w in target.items()}
        else:
            raise ValueError(f'Insufficient coverage for {key} on {date}; cannot claim the requested holding bounds')
        values,cash,cost,notional,ts=rebalance(values,cash,target,cost_bps/10000)
        if rule!='equal':assert minimum_holdings<=len(values)<=maximum_holdings
        ever_held.update(values)
        bvalues,bcash,_,_,_=rebalance(bvalues,bcash,benchmark(region),0)
        nav=sum(values.values())+cash;bnav=sum(bvalues.values())+bcash
        for t in ts: trades.append({'date':date,**t})
        for t,v in sorted(values.items()): holdings.append({'date':date,'ticker':t,'value':v,'weight':v/nav})
        holdings.append({'date':date,'ticker':'CASH','value':cash,'weight':cash/nav})
        for t,u in inputs.universe.items():
            if u['region']!=region: continue
            coverage.append({'date':date,'ticker':t,'covered':t in sc,'reason':reasons.get(t,'covered')})
        for t,r in sorted(sc.items()):
            scores.append({'date':date,'information_cutoff':date[:7]+'-01','ticker':t,
                'P1_ROCE':r['roce'],'P1_cash_accruals':r['cash_accruals'],'rank_ROCE':r['rank_roce'],'rank_quality':r['rank_quality'],
                'P1_reduced':r['score'],'P2':'documented policy participation gate' if gate else 'not scored','P3':'not observed',
                'composite_reduced':r['score'],'q25':q25,'q50':q50,'q75':q75,'held_after_trade':t in values,
                'report_period':r['period_end'],'period_type':r['period_type'],'available_used':r['available_used'],
                'report_age_days':r['report_age_days'],'source_panel':r['panel'],
                'observation_id':r.get('observation_id',''),'component_ids':r.get('component_ids',''),
                'original_publication':r.get('publication_date',''),
                'income_source':r['income_source'],'balance_source':r['balance_source'],'cashflow_source':r['cashflow_source']})
        monthly.append({'date':date,'NAV':nav,'BenchmarkNAV':bnav,'ETFReturn':nav/100-1,'BenchReturn':bnav/100-1,
            'AlphaRatio':nav/bnav-1,'ActiveReturnPP':(nav-bnav)/100,'PeriodReturn':nav/old_nav-1,
            'InitialDeployment':initial,'PreTradeNAV':pre,'Cost':cost,'TradedNotional':notional,'Turnover':notional/pre,
            'Holdings':len(values),'CoveredUniverse':len(sc),'CashWeight':cash/nav})
        previous=date
    if not monthly: return None
    daily=[]
    anchor=monthly[-1]['date'];needed=set(values)|set(bvalues)
    all_daily=set.intersection(*(set(inputs.extension_daily[t]) for t in needed)) if needed else set()
    if all(inputs.daily_price(t,anchor,False) is not None for t in needed):
        for date in sorted(d for d in all_daily if anchor<d<=inputs.extension_config['as_of']):
            if region=='EU' and any(date not in inputs.fx[s] for s in inputs.fx): continue
            nav=cash+sum(v*inputs.daily_price(t,date)/inputs.daily_price(t,anchor)*inputs.conversion(t,date,region)/inputs.conversion(t,anchor,region) for t,v in values.items())
            bn=bcash+sum(v*inputs.daily_price(t,date)/inputs.daily_price(t,anchor)*inputs.conversion(t,date,region)/inputs.conversion(t,anchor,region) for t,v in bvalues.items())
            daily.append({'date':date,'NAV':nav,'BenchmarkNAV':bn,'ETFReturn':nav/100-1,'BenchReturn':bn/100-1,
                          'AlphaRatio':nav/bn-1,'SinceMonthEndReturn':nav/monthly[-1]['NAV']-1,'Holdings':len(values)})
    end=daily[-1] if daily else monthly[-1]
    years=(dt.date.fromisoformat(end['date'])-dt.date.fromisoformat(monthly[0]['date'])).days/365.2425
    returns=[r['PeriodReturn'] for r in monthly[1:]]
    vol=statistics.stdev(returns)*math.sqrt(12) if len(returns)>1 else 0
    peak=100.;dd=0
    for r in monthly: peak=max(peak,r['NAV']);dd=min(dd,r['NAV']/peak-1)
    summary={'run':key,'region':region,'panel':panel,'rule':rule,'price_policy':inputs.price_policy,'documented_policy_gate':gate,'cost_bps':cost_bps,
        'annual_lag_days':annual_lag,'reentry_qualifying_quarters':1,'membership_schedule':'quarterly',
        'score_exit_qualifying_quarters':1,'normal_entry_quantile':.75 if rule=='q75' else .5 if rule=='q50' else '',
        'constraint_applied':rule!='equal','minimum_holdings':minimum_holdings if rule!='equal' else '',
        'maximum_holdings':maximum_holdings if rule!='equal' else '',
        'requested_start':start or '', 'start':monthly[0]['date'],'monthly_end':monthly[-1]['date'],'latest_end':end['date'],
        'complete_monthly_returns':len(returns),'total_return':end['NAV']/100-1,'benchmark_return':end['BenchmarkNAV']/100-1,
        'relative_alpha':end['NAV']/end['BenchmarkNAV']-1,'active_return_pp':(end['NAV']-end['BenchmarkNAV'])/100,
        'CAGR':(end['NAV']/100)**(1/years)-1 if years>0 else 0,
        'benchmark_CAGR':(end['BenchmarkNAV']/100)**(1/years)-1 if years>0 else 0,
        'monthly_vol_annualized':vol,'Sharpe_rf0_monthly':statistics.mean(returns)*12/vol if vol else '',
        'max_drawdown_monthly':dd,'final_NAV':end['NAV'],'final_benchmark_NAV':end['BenchmarkNAV'],
        'final_holdings':len(values),'final_covered_universe':monthly[-1]['CoveredUniverse'],
        'total_cost_NAV_units':sum(r['Cost'] for r in monthly),'total_traded_NAV_units':sum(r['TradedNotional'] for r in monthly),
        'exits':sum(r['event'].startswith('EXIT_') for r in events),'reentries':sum(r['event']=='REENTER' for r in events),
        'recovery_watches':sum(r['event']=='RECOVERY_WATCH' for r in events)}
    summary.update(min_observed_holdings=min(r['Holdings'] for r in monthly),max_observed_holdings=max(r['Holdings'] for r in monthly),
        floor_admissions=sum(r['event']=='ENTER_FLOOR' for r in events),
        floor_months=sum(r['floor_admissions']>0 for r in selection_audit),
        off_quarter_floor_admissions=sum(r['event']=='ENTER_FLOOR' and int(r['date'][5:7]) not in (3,6,9,12) for r in events),
        capacity_exits=sum(r['event']=='EXIT_CAPACITY' for r in events),
        max_monthly_stock_weight=max((r['weight'] for r in holdings if r['ticker']!='CASH'),default=0))
    if selection_policy is not None and rule!='equal':
        if hasattr(selection_policy,'score_exit_qualifying_quarters'):
            summary['score_exit_qualifying_quarters']=selection_policy.score_exit_qualifying_quarters
        if callable(getattr(selection_policy,'exit_streak',None)):
            for event in events:event.setdefault('score_exit_streak',0)
    summary['Paper_CAGR_div_vol']=summary['CAGR']/vol if vol else ''
    quarterly=[]
    ends={}
    for r in monthly: ends[r['date'][:4]+'-Q'+str((int(r['date'][5:7])-1)//3+1)]=r
    prevn=100.;prevb=100.
    if daily: ends[daily[-1]['date'][:4]+'-Q'+str((int(daily[-1]['date'][5:7])-1)//3+1)]=daily[-1]
    for q,r in sorted(ends.items()):
        quarterly.append({'quarter':q,'date':r['date'],'NAV':r['NAV'],'BenchmarkNAV':r['BenchmarkNAV'],
            'ETFQuarterReturn':r['NAV']/prevn-1,'BenchQuarterReturn':r['BenchmarkNAV']/prevb-1,
            'ETFCumulativeReturn':r['ETFReturn'],'BenchCumulativeReturn':r['BenchReturn'],'AlphaRatio':r['AlphaRatio'],
            'Holdings':r['Holdings'],'partial_quarter':not quarterly or r['date']!=endmonth(int(r['date'][:4]),int(r['date'][5:7])).isoformat() or int(r['date'][5:7]) not in (3,6,9,12)})
        prevn=r['NAV'];prevb=r['BenchmarkNAV']
    extension_daily=[]
    h={}
    for r in holdings:h.setdefault(r['date'],{})[r['ticker']]=r['value']
    m={r['date']:r for r in monthly}
    # This extension uses actual closes. Month-end executions map to their last
    # observed common trading session, retaining the calendar label separately.
    possible=sorted(set.intersection(*(set(inputs.extension_daily[t]) for t in benchmark(region)))) if monthly[-1]['date']>='2026-08-31' else []
    actual_ends={max(d for d in possible if d<=label):label for label in m if label>='2026-08-31'}
    for date in possible:
        if not '2026-09-01'<=date<=inputs.extension_config['as_of']:continue
        if date in actual_ends:
            label=actual_ends[date];r=m[label]
            extension_daily.append(dict(date=date,NAV=r['NAV'],BenchmarkNAV=r['BenchmarkNAV'],ETFReturn=r['ETFReturn'],BenchReturn=r['BenchReturn'],AlphaRatio=r['AlphaRatio'],Holdings=r['Holdings'],last_rebalance=label,rebalance_close=True))
            continue
        anchors=[label for label in m if label<date]
        if not anchors:continue
        a=max(anchors);v=h[a];names=[t for t in v if t!='CASH']
        if any(date not in inputs.extension_daily[t] for t in names):continue
        nav=v.get('CASH',0)+sum(value*inputs.daily_price(t,date)/inputs.daily_price(t,a)*inputs.conversion(t,date,region)/inputs.conversion(t,a,region) for t,value in v.items() if t!='CASH')
        bn=m[a]['BenchmarkNAV']*sum(w*inputs.daily_price(t,date)/inputs.daily_price(t,a) for t,w in benchmark(region).items())
        extension_daily.append(dict(date=date,NAV=nav,BenchmarkNAV=bn,ETFReturn=nav/100-1,BenchReturn=bn/100-1,AlphaRatio=nav/bn-1,Holdings=len(names),last_rebalance=a,rebalance_close=False))
    return {'summary':summary,'monthly':monthly,'quarterly':quarterly,'recent_daily':daily,'extension_daily':extension_daily,'scores':scores,'holdings':holdings,'trades':trades,'events':events,'coverage':coverage,'selection_audit':selection_audit}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='results_final')
    ap.add_argument('--min-holdings',type=int,default=1)
    ap.add_argument('--max-holdings',type=int,default=9)
    args=ap.parse_args()
    execute=partial(run,minimum_holdings=args.min_holdings,maximum_holdings=args.max_holdings)
    out=Path(args.output);out=out if out.is_absolute() else ROOT/out;out.mkdir(parents=True,exist_ok=True)
    inputs=Inputs();runs=[]
    for region,basecost in [('US',10),('EU',15)]:
        for panel in ('annual','hybrid','quarterly','primary'):
            for rule in ('q75','q50','equal'):
                for cost in (0,basecost,2*basecost):
                    result=execute(inputs,region,panel,rule,cost)
                    if result: runs.append(result)
        for rule in ('q75','q50','equal'):
            for lag,gate in ((240,False),(180,True)):
                result=execute(inputs,region,'annual',rule,basecost,gate,lag)
                if result:runs.append(result)
        # Identical start dates separate selection effects from differing market windows.
        for panel in ('annual','hybrid'):
            for rule in ('q75','q50','equal'):
                for start in ('2022-07-31', '2022-08-31' if region=='US' else '2021-10-31'):
                    result=execute(inputs,region,panel,rule,basecost,start=start)
                    if result:runs.append(result)
    monthly_only=Inputs(prefer_daily_overlap=False)
    for region,cost in [('US',10),('EU',15)]:
        for panel in ('annual','hybrid'):
            for rule in ('q75','q50','equal'):
                result=execute(monthly_only,region,panel,rule,cost)
                if result:runs.append(result)
    for r in runs:
        for kind,rows in r.items():
            if kind!='summary':write_csv(out/r['summary']['run']/(kind+'.csv'),rows)
    summaries=[r['summary'] for r in runs]
    lookup={s['run']:s for s in summaries}
    for s in summaries:
        control=s['run'].replace('_'+s['rule']+'_','_equal_')
        c=lookup[control]
        s['covered_universe_return']=c['total_return']
        s['selection_return_ratio']=(1+s['total_return'])/(1+c['total_return'])-1
    write_csv(out/'summary.csv',summaries)
    write_csv(out/'fx_valuation_audit.csv',list(inputs.fx_log.values()))
    write_csv(out/'price_source_bridge.csv',inputs.price_bridge)
    write_csv(out/'daily_observation_audit.csv',[inputs.extension_quotes[k] for k in sorted(inputs.extension_quotes)])
    (out/'run_metadata.json').write_text(json.dumps({'description':'Real-data reduced-factor reconstruction; not an exact replication or certified point-in-time backtest',
        'as_of':inputs.extension_config['as_of'],'runs':len(runs),'complete_price_month_end':inputs.extension_config['complete_month_end'],'parameters':'HOLDINGS_RULE_CHANGE.md; inherited METHOD_LOCK.md and EXTENSION_METHOD.md',
        'reentry_qualifying_quarters':1,'membership_schedule':'quarterly','score_exit_qualifying_quarters':1,
        'minimum_holdings':args.min_holdings,'maximum_holdings':args.max_holdings,'primary_entry_rule':'q75',
        'minimum_rule':'Highest-scoring eligible stocks above Q25; every admission below the normal entry gate is flagged',
        'missing_factors':['subsidy utilization','WACC','planned vs actual project capex','historical analyst targets','governance','lobbying','network centrality','IP centrality']},indent=2)+'\n')
    print(json.dumps([s for s in summaries if s['panel'] in ('annual','hybrid') and s['rule']!='equal' and s['cost_bps'] in (10,15) and not s['documented_policy_gate'] and s['annual_lag_days']==180 and '_from' not in s['run']],indent=2))

if __name__=='__main__':main()
