"""Predefined, point-in-time score and exit alternatives; no fitted parameters."""
import calendar
import copy
import math

from backtest import percentile, ranks
from run_long_history import HistoryInputs
from run_pillar2 import PolicyInputs

VARIANTS={
    'baseline': ('base','single'),
    'balanced': ('balanced','single'),
    'trend': ('trend','single'),
    'momentum': ('momentum','single'),
    'confirm_exit': ('base','confirm'),
    'recovery_grace': ('base','grace'),
    'no_score_exit': ('base','none'),
    'trend_confirm': ('trend','confirm'),
    'momentum_confirm': ('momentum','confirm'),
}


def shifted_month_end(date, months):
    index=int(date[:4])*12+int(date[5:7])-1+months
    year,month=divmod(index,12);month+=1
    return f'{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}'


class RecoveryInputs(PolicyInputs):
    def __init__(self,region,timing,mode,events,lam,registry,score_mode='base'):
        super().__init__(region,timing,mode,events,lam,registry)
        self.score_mode=score_mode
        self.feature_cache={}

    def features(self, region, date):
        key=region,date
        if key in self.feature_cache:return self.feature_cache[key]
        current,reasons=super().signals(region,date,'hybrid',True,0)
        previous_date=shifted_month_end(date,-12)
        prior,_=HistoryInputs.signals(self,region,previous_date,'hybrid',False,0)
        momentum_start,momentum_end=shifted_month_end(date,-13),shifted_month_end(date,-2)
        for ticker,r in current.items():
            r['base_score']=r['score']
            old=prior.get(ticker)
            r.update(trend_available=old is not None,prior_review=previous_date,
                     prior_information_cutoff=previous_date[:7]+'-01',
                     prior_observation_id=old.get('observation_id','') if old else '',
                     prior_available_used=old.get('available_used','') if old else '',
                     prior_report_period=old.get('period_end','') if old else '',
                     same_report_period=bool(old and old['period_end']==r['period_end']),
                     delta_roce=r['roce']-old['roce'] if old else '',
                     delta_cash_quality=-r['cash_accruals']+old['cash_accruals'] if old else '',
                     momentum_start=momentum_start,momentum_end=momentum_end,
                     momentum_available=False,momentum_return='',momentum_missing_reason='',
                     momentum_start_price='',momentum_end_price='')
            listing=self.universe[ticker]['listing_start']
            if listing and listing>momentum_start:
                r['momentum_missing_reason']='lookback precedes actual listing'
            elif momentum_start not in self.prices[ticker] or momentum_end not in self.prices[ticker]:
                r['momentum_missing_reason']='missing exact month-end price'
            else:
                try:
                    r['momentum_start_price']=self.price(ticker,momentum_start,region)
                    r['momentum_end_price']=self.price(ticker,momentum_end,region)
                    r['momentum_return']=r['momentum_end_price']/r['momentum_start_price']-1
                    r['momentum_available']=True
                except ValueError as exc:r['momentum_missing_reason']=str(exc)
        trend_r=ranks({t:r['delta_roce'] for t,r in current.items() if r['trend_available']})
        trend_q=ranks({t:r['delta_cash_quality'] for t,r in current.items() if r['trend_available']})
        momentum=ranks({t:r['momentum_return'] for t,r in current.items() if r['momentum_available']})
        for ticker,r in current.items():
            r['trend_rank']=(trend_r[ticker]+trend_q[ticker])/2 if r['trend_available'] else ''
            r['momentum_rank']=momentum.get(ticker,'')
            r['improving_both']=bool(r['trend_available'] and r['delta_roce']>0 and r['delta_cash_quality']>0)
        self.feature_cache[key]=(current,reasons)
        return current,reasons

    def signals(self,region,date,panel,gate=True,annual_lag=0):
        assert gate
        source,reasons=self.features(region,date)
        selected=copy.deepcopy(source)
        for r in selected.values():
            r['feature_fallback']=False
            if self.score_mode=='balanced':r['score']=math.sqrt(r['rank_roce']*r['rank_quality'])
            elif self.score_mode in ('trend','momentum'):
                if r[self.score_mode+'_available']:r['score']=(r['base_score']+r[self.score_mode+'_rank'])/2
                else:r['feature_fallback']=True
            else:assert self.score_mode=='base'
        return selected,dict(reasons)


class RecoveryExitPolicy:
    def __init__(self,mode):
        assert mode in ('single','confirm','grace','none')
        self.mode=mode
        self.score_exit_qualifying_quarters={'single':1,'confirm':2,'grace':'1_or_2','none':0}[mode]
        self.streaks={};self.last_exits={};self.last_date=None;self.review_log=[]

    def select(self,sc,active,rule,quarter_end,minimum,maximum,date):
        assert self.last_date is None or date>self.last_date,'Selection called more than once or out of order'
        self.last_date=date;self.last_exits={}
        assert len(sc)>=max(4,minimum)
        q25=percentile([r['score'] for r in sc.values()],.25)
        threshold=percentile([r['score'] for r in sc.values()],.75 if rule=='q75' else .5)
        rank=lambda t:(-sc[t]['score'],t)
        available=active&set(sc)
        self.streaks={t:n for t,n in self.streaks.items() if t in available}
        survivors=set();pending=[];deferred=0
        for ticker in sorted(available):
            breach=sc[ticker]['score']<=q25
            exit_now=False;grace=False
            if quarter_end:
                self.streaks[ticker]=self.streaks.get(ticker,0)+1 if breach else 0
                count=self.streaks[ticker]
                if breach:
                    if self.mode=='single':exit_now=True
                    elif self.mode=='confirm':exit_now=count>=2
                    elif self.mode=='grace':
                        grace=count==1 and sc[ticker].get('improving_both',False)
                        exit_now=not grace
                    if not exit_now:deferred+=1
                pending.append(dict(date=date,ticker=ticker,breach=breach,streak=count,
                                    improving_both=sc[ticker].get('improving_both',False),
                                    grace=grace,score_exit=exit_now,score=sc[ticker]['score'],q25=q25))
                if exit_now:
                    reason={'single':'EXIT_BOTTOM_QUARTILE','confirm':'EXIT_BOTTOM_QUARTILE_CONFIRMED',
                            'grace':'EXIT_BOTTOM_QUARTILE_AFTER_GRACE' if count>=2 else 'EXIT_BOTTOM_QUARTILE_NO_RECOVERY'}[self.mode]
                    self.last_exits[ticker]=(reason,count)
            if not exit_now:survivors.add(ticker)
        qualifiers={t for t in sc if quarter_end and sc[t]['score']>threshold}
        candidates=survivors|qualifiers
        selected=set(sorted(candidates,key=rank)[:maximum]);cap_removed=candidates-selected;floor=[]
        for ticker in sorted((t for t in sc if t not in selected and sc[t]['score']>q25),key=rank):
            if len(selected)>=minimum:break
            selected.add(ticker);floor.append(ticker)
        assert minimum<=len(selected)<=maximum
        for r in pending:
            r.update(held_after=r['ticker'] in selected,capacity_removed=r['ticker'] in cap_removed)
            self.review_log.append(r)
        self.streaks={t:n for t,n in self.streaks.items() if t in selected}
        return selected,set(floor),cap_removed,threshold,dict(
            covered=len(sc),prior_holdings=len(active),covered_prior_holdings=len(available),
            normal_qualifiers=len(qualifiers),retained_before_cap=len(survivors),candidate_count=len(candidates),
            capacity_exclusions=len(cap_removed),floor_admissions=len(floor),final_holdings=len(selected),
            below_entry_gate_held=sum(sc[t]['score']<=threshold for t in selected),
            minimum_holdings=minimum,maximum_holdings=maximum,quarter_end=quarter_end,
            deferred_score_exits=sum(r['breach'] and not r['score_exit'] and r['held_after'] for r in pending),
            attempted_score_deferrals=deferred,score_exit_rule=self.mode)

    def exit_reason(self,ticker):return self.last_exits.get(ticker,('EXIT_SCORE_RULE',0))[0]
    def exit_streak(self,ticker):return self.last_exits.get(ticker,('',0))[1]
