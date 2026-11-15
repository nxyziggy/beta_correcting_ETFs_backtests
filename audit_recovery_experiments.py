#!/usr/bin/env python3
"""Ledger replay and cutoff checks, reusing the production input classes."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from backtest import ranks
from recovery_rules import RecoveryInputs
from run_long_history import HistoryInputs
from run_pillar2 import read_research
from run_research_corrections import source_date, common_date

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results_recovery_experiments'
EXPECTED_VARIANTS={'baseline','balanced','trend','momentum','confirm_exit',
                   'recovery_grace','no_score_exit','trend_confirm','momentum_confirm'}
CASES={'direct_main':('direct','source'),
       'direct_timing_source':('direct','source'),
       'direct_timing_delayed':('direct','delay_adjusted'),
       'indirect_main':('with_indirect','source')}


def read(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def close(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8),(a,b)


def quantile(values,p):
    x=sorted(values);position=(len(x)-1)*p
    i,j=math.floor(position),math.ceil(position)
    return x[i]+(x[j]-x[i])*(position-i)


def raw_metrics(observation):
    assets=float(observation['total_assets'])
    capital=assets-float(observation['current_liabilities'])
    return (float(observation['operating_income'])/capital,
            (float(observation['net_income'])-float(observation['operating_cash_flow']))/assets)


def main():
    summary=read(OUT/'summary.csv')
    assert len(summary)==152
    groups=Counter((s['case'],s['region']) for s in summary)
    assert len(groups)==8 and set(groups.values())=={19}
    assert {s['variant'] for s in summary if s['rule']!='equal'}==EXPECTED_VARIANTS
    assert sum(s['rule']=='equal' for s in summary)==8
    refs=read(ROOT/'results_pillar2/summary.csv');reproductions=0
    for s in summary:
        if s['variant'] not in ('baseline','equal'):continue
        window='timing_matched' if s['case'].startswith('direct_timing') else 'earliest_complete'
        reference=next(r for r in refs if r['region']==s['region'] and r['definition']==s['definition']
                       and r['timing']==s['timing'] and r['window']==window and r['rule']==s['rule'])
        assert read(OUT/s['run']/'monthly.csv')==read(ROOT/'results_pillar2'/reference['run']/'monthly.csv')
        reproductions+=1
    features=read(OUT/'signal_features.csv');fmap=defaultdict(dict)
    for f in features:
        key=f['case'],f['region'],f['date']
        assert f['ticker'] not in fmap[key]
        fmap[key][f['ticker']]=f
        cutoff=f['information_cutoff'];assert f['available_used']<cutoff
        if f['trend_available']=='True':assert f['prior_available_used']<f['prior_information_cutoff']<cutoff
        if f['momentum_available']=='True':
            assert f['momentum_start']<f['momentum_end']<cutoff
            close(f['momentum_return'],float(f['momentum_end_price'])/float(f['momentum_start_price'])-1)
    covered=defaultdict(set)
    for c in read(OUT/'eligibility.csv'):
        if c['covered']=='True':covered[c['case'],c['region'],c['date']].add(c['ticker'])
    assert set(covered)==set(fmap)
    assert all(covered[k]==set(v) for k,v in fmap.items())
    threshold_checks=event_checks=holding_checks=0
    for s in summary:
        def scores(date):
            computed={}
            for ticker,r in fmap[s['case'],s['region'],date].items():
                base=float(r['base_score']);mode=s['score_mode']
                if mode=='balanced':value=math.sqrt(float(r['rank_roce'])*float(r['rank_quality']))
                elif mode in ('trend','momentum') and r[mode+'_available']=='True':
                    value=(base+float(r[mode+'_rank']))/2
                else:value=base
                computed[ticker]=value
            return computed
        for h in read(OUT/s['run']/'holdings.csv'):
            if h['ticker']!='CASH':
                assert h['ticker'] in fmap[s['case'],s['region'],h['date']]
                holding_checks+=1
        path=OUT/s['run']/'selection_audit.csv'
        if path.exists():
            for a in read(path):
                sc=scores(a['date'])
                close(a['entry_threshold'],quantile(list(sc.values()),.75 if s['rule']=='q75' else .5))
                close(a['exit_threshold'],quantile(list(sc.values()),.25))
                assert int(a['covered'])==len(sc)
                threshold_checks+=1
        path=OUT/s['run']/'events.csv'
        if path.exists():
            for e in read(path):
                if e['score']!='':
                    close(e['score'],scores(e['date'])[e['ticker']]);event_checks+=1
    for region in ('US','EU'):
        a=next(s for s in summary if s['region']==region and s['case']=='direct_timing_source' and s['rule']=='equal')
        b=next(s for s in summary if s['region']==region and s['case']=='direct_timing_delayed' and s['rule']=='equal')
        assert read(OUT/a['run']/'monthly.csv')==read(OUT/b['run']/'monthly.csv')

    # Load already-published Lam inputs without build_lam(), which rewrites files.
    lam=json.loads((ROOT/'data/research_corrections/lam_inputs.json').read_text())
    raw=json.loads((ROOT/'data/research_corrections/lam_sources.json').read_text())
    registry={'lam_source_'+r['period_end']:r for r in raw}
    events,_=read_research()
    inputs={(case,region):RecoveryInputs(region,timing,mode,events,lam,registry)
            for case,(mode,timing) in CASES.items() for region in ('US','EU')}
    component_checks=trend_checks=price_checks=0
    for f in features:
        inp=inputs[f['case'],f['region']]
        current=inp.observations[f['observation_id']]
        roce,accruals=raw_metrics(current)
        close(roce,f['roce']);close(accruals,f['cash_accruals'])
        observations=[(f['observation_id'],f['information_cutoff'])]
        if f['trend_available']=='True':observations.append((f['prior_observation_id'],f['prior_information_cutoff']))
        for oid,cutoff in observations:
            observation=inp.observations[oid]
            assert observation['availability_date']<cutoff
            for cid in observation['component_ids'].split('|'):
                component=inp.registry[cid]
                available=common_date(component) if inp.stage=='common' else source_date(component)
                assert available<cutoff;component_checks+=1
        if f['trend_available']=='True':
            old_roce,old_accruals=raw_metrics(inp.observations[f['prior_observation_id']])
            close(roce-old_roce,f['delta_roce'])
            close(-accruals+old_accruals,f['delta_cash_quality']);trend_checks+=1
        if f['momentum_available']=='True':
            listing=inp.universe[f['ticker']]['listing_start']
            assert not listing or listing<=f['momentum_start']
            close(f['momentum_start_price'],inp.price(f['ticker'],f['momentum_start'],f['region']))
            close(f['momentum_end_price'],inp.price(f['ticker'],f['momentum_end'],f['region']))
            price_checks+=1
    for group in fmap.values():
        tr=ranks({t:float(f['delta_roce']) for t,f in group.items() if f['trend_available']=='True'})
        tq=ranks({t:float(f['delta_cash_quality']) for t,f in group.items() if f['trend_available']=='True'})
        momentum=ranks({t:float(f['momentum_return']) for t,f in group.items() if f['momentum_available']=='True'})
        for ticker,f in group.items():
            if f['trend_available']=='True':close(f['trend_rank'],(tr[ticker]+tq[ticker])/2)
            if f['momentum_available']=='True':close(f['momentum_rank'],momentum[ticker])
    isolation_checks=0
    for region in ('US','EU'):
        for timing in ('source','delay_adjusted'):
            inp=RecoveryInputs(region,timing,'direct',events,lam,registry,'trend')
            before,_=inp.signals(region,'2022-06-30','hybrid')
            for observation in inp.annual+inp.quarterly:
                if observation['availability_date']>='2022-06-01':
                    observation['operating_income']=float(observation['operating_income'])*1000
            ticker=next(iter(before))
            inp.prices[ticker]['2022-05-31']*=100
            inp.prices[ticker]['2022-06-30']*=100
            inp.feature_cache.clear()
            after,_=inp.signals(region,'2022-06-30','hybrid')
            assert before==after
            previous,_=HistoryInputs.signals(inp,region,'2021-06-30','hybrid',False)
            for observation in inp.annual+inp.quarterly:
                if observation['availability_date']>='2021-06-01':
                    observation['operating_income']=float(observation['operating_income'])*1000
            unchanged,_=HistoryInputs.signals(inp,region,'2021-06-30','hybrid',False)
            assert previous==unchanged;isolation_checks+=1
    paths=['audit_recovery_experiments.py','recovery_rules.py','backtest.py',
           'results_recovery_experiments/summary.csv','results_recovery_experiments/signal_features.csv',
           'results_recovery_experiments/eligibility.csv']
    result=dict(audit_date='2026-11-15',status='PASS',
                procedure='Ledger replay, source arithmetic and in-memory information-isolation checks; no portfolio variants rerun.',
                variants=9,runs=len(summary),controls=8,exact_baseline_control_monthly_reproductions=reproductions,
                feature_rows=len(features),feature_and_eligibility_sets_identical=True,
                timing_control_pairs_identical=2,selection_threshold_recalculations=threshold_checks,
                event_score_recalculations=event_checks,covered_holdings_checked=holding_checks,
                source_component_cutoff_checks=component_checks,raw_fundamental_change_recalculations=trend_checks,
                investor_currency_endpoint_pair_checks=price_checks,feature_rank_groups=len(fmap),
                region_timing_future_isolation_cases=isolation_checks,
                implementation_findings='No blocking leakage or implementation defect found in the tested scoring, coverage and information-cutoff paths.',
                limitations=['The replay imports the production input classes and is not an independent implementation.',
                             'The replay validates computations against frozen inputs; it does not independently certify vendor-adjusted price vintages.',
                             'The candidate pool and already-observed evaluation periods remain retrospective.',
                             'Fundamental trend has greater initial missing coverage in Europe; baseline fallback keeps coverage fixed but changes feature activation.',
                             'Large historical gains from informed alternatives do not establish an untouched out-of-sample advantage.'],
                hashes=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in paths])
    (OUT/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('hashes','limitations')},indent=2))


if __name__=='__main__':main()
