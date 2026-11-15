#!/usr/bin/env python3
"""Extend complete eligible-company histories; audit the corrected timing experiment."""
import copy
import datetime as dt
import json
import math
import shutil
from collections import defaultdict

from backtest import Inputs, benchmark, read_csv, run
from prepare_data import DATA, ROOT
from run_research_corrections import (CorrectedInputs, active_stats, build_lam, common_date,
                                     digest, save, source_date, write_csv, close)

OUT = ROOT/'results_long_history'
AREA = DATA/'long_history'
COST = {'US': 10, 'EU': 15}
PRIOR_START = {'US': '2022-09-30', 'EU': '2021-09-30'}
RULES = ('q50', 'q75', 'equal')


def load(path):
    return json.loads(path.read_text())


class TimingInputs(CorrectedInputs):
    extend_freshness = False

    def freshness_days(self, record):
        base = super().freshness_days(record)
        return base + ((180 if record['period_type']=='annual' else 90) if self.extend_freshness else 0)


class HistoryInputs(TimingInputs):
    def __init__(self, region, timing, lam, registry):
        super().__init__(region, 'interim', 'lam' if region=='US' else 'evidenced', lam, registry)
        self.timing = timing
        self.extend_freshness = timing=='delay_adjusted'
        self.stage = 'common' if timing!='source' else 'evidenced'
        self.added = []
        existing = {(r['ticker'],r['period_end'],r['period_type']) for r in self.annual+self.quarterly}
        files = [(p,p.with_name('source_registry.json')) for p in sorted(AREA.glob('*/normalized_inputs.json'))]
        files.append((AREA/'prices/recovered_eu_semis_inputs.json', AREA/'prices/recovered_eu_semis_registry.json'))
        self.duplicate_rows = []
        for inputs_path, registry_path in files:
            if not inputs_path.exists():
                continue
            self.registry.update(load(registry_path))
            for r in load(inputs_path):
                key = r['ticker'],r['period_end'],r['period_type']
                if key in existing:
                    self.duplicate_rows.append(dict(ticker=key[0],period_end=key[1],source_file=str(inputs_path.relative_to(ROOT))))
                    continue
                existing.add(key)
                self.added.append(r)
                (self.annual if r['period_type']=='annual' else self.quarterly).append(copy.deepcopy(r))
        for r in self.annual+self.quarterly:
            r['evidenced_availability_date'] = r['availability_date']
            components = [self.registry[c] for c in r['component_ids'].split('|')]
            assert all(source_date(c) <= r['availability_date'] for c in components), r
            if timing!='source':
                r['availability_date'] = max(common_date(r),*(common_date(c) for c in components))
                r['availability_basis'] = 'Common 180/90 day floor on every source component'
        self.observations = {r['observation_id']:r for r in self.annual+self.quarterly}
        for r in load(AREA/'prices/listing_overrides.json'):
            self.universe[r['ticker']]['listing_start'] = r['listing_start']
        for r in read_csv(AREA/'prices/fx_additions.csv'):
            if r['date'] in self.fx[r['series']]:
                close(self.fx[r['series']][r['date']],r['rate'])
            else:
                self.fx[r['series']][r['date']] = float(r['rate'])
        self.fx_dates = {s:sorted(v) for s,v in self.fx.items()}

    def signals(self, region, date, panel, gate=False, annual_lag=0):
        # IPOs after the first-of-month information cutoff enter the next information set.
        cutoff = date[:7]+'-01'
        original = self.universe
        excluded = {t for t,u in original.items() if u['region']==region and u['listing_start'] and u['listing_start']>=cutoff}
        self.universe = {t:u for t,u in original.items() if t not in excluded}
        try:
            scores,reasons = super().signals(region,date,panel,False,0)
        finally:
            self.universe = original
        reasons.update({t:'not listed before information cutoff' for t in excluded})
        return scores,reasons


def is_listed(inp,t,date):
    u=inp.universe[t]
    return (not u['listing_start'] or u['listing_start']<date[:7]+'-01') and (not u['delisting_date'] or date<u['delisting_date'])


def coverage_audit(inp,region):
    dates=sorted(d for d in set.intersection(*(set(inp.prices[t]) for t in benchmark(region)))
                 if '2008-01-01'<=d<=inp.extension_config['complete_month_end'])
    for a,b in zip(dates,dates[1:]):
        assert (int(b[:4])-int(a[:4]))*12+int(b[5:7])-int(a[5:7])==1,('Benchmark calendar gap',region,a,b)
    rows=[]
    for date in dates:
        scores,reasons=inp.signals(region,date,'hybrid')
        for t,u in inp.universe.items():
            if u['region']!=region:
                continue
            listed=is_listed(inp,t,date)
            reason=reasons.get(t,'covered')
            usable=listed and t in scores
            if usable:
                try:
                    inp.price(t,date,region)
                    for b in benchmark(region):inp.price(b,date,region)
                except ValueError as exc:
                    usable=False
                    reason=str(exc)
            sc=scores.get(t,{})
            rows.append(dict(region=region,timing=inp.timing,date=date,ticker=t,listed_at_cutoff=listed,
                             complete=usable,reason=reason,period_end=sc.get('period_end',''),
                             available_used=sc.get('available_used',''),observation_id=sc.get('observation_id','')))
    return rows


def earliest_complete(rows):
    by_date=defaultdict(list)
    for r in rows:by_date[r['date']].append(r)
    suffix_good=True
    candidates=[]
    for date,rs in sorted(by_date.items(),reverse=True):
        listed=[r for r in rs if r['listed_at_cutoff']]
        suffix_good &= len(listed)>=4 and all(r['complete'] for r in listed)
        if suffix_good and int(date[5:7]) in (3,6,9,12):candidates.append(date)
    assert candidates,'No complete eligible-company window; recover the documented gaps before publishing.'
    return min(candidates)


def validate(result,inp,require_complete=False):
    s=result['summary']; hs=defaultdict(list); ts=defaultdict(list)
    assert s['start']==s['requested_start'],('Run silently advanced its start',s['run'])
    for h in result['holdings']:hs[h['date']].append(h)
    for t in result['trades']:ts[t['date']].append(t)
    for m in result['monthly']:
        close(sum(h['value'] for h in hs[m['date']]),m['NAV'])
        close(sum(h['weight'] for h in hs[m['date']]),1)
        close(sum(t['cost'] for t in ts[m['date']]),m['Cost'])
        close(m['PreTradeNAV']-m['Cost'],m['NAV'])
        if s['rule']!='equal':assert 1<=m['Holdings']<=9
        for h in hs[m['date']]:
            if h['ticker']!='CASH':assert is_listed(inp,h['ticker'],h['date'])
    for sc in result['scores']:
        r=inp.observations[sc['observation_id']]
        assert r['availability_date']==sc['available_used']<sc['information_cutoff']
        assert sc['report_age_days']<=inp.freshness_days(r)
        for cid in r['component_ids'].split('|'):
            component=inp.registry[cid]
            available=common_date(component) if inp.stage=='common' else source_date(component)
            assert available<sc['information_cutoff']
    if require_complete:
        assert all(r['covered'] for r in result['coverage'] if is_listed(inp,r['ticker'],r['date']))
    close(s['final_NAV']/100-1,s['total_return'])
    assert s['latest_end']=='2026-11-02'
    return dict(run=s['run'],status='PASS',months=len(result['monthly']),scores=len(result['scores']))


def execute(inp,region,panel,rule,start,window):
    result=run(inp,region,panel,rule,COST[region],annual_lag=0,start=start)
    result['summary'].update(window=window,timing=inp.timing,
                              annual_freshness_days=inp.freshness_days({'period_type':'annual'}),
                              interim_freshness_days=inp.freshness_days({'period_type':'trailing'}))
    result['summary']['run']+='_'+window
    return result


def year_returns(result):
    values=defaultdict(lambda:1.0)
    for r in result['monthly']:values[r['date'][:4]]*=1+r['PeriodReturn']
    if result['recent_daily']:
        last=result['recent_daily'][-1]
        values[last['date'][:4]]*=last['NAV']/result['monthly'][-1]['NAV']
    return [dict(run=result['summary']['run'],year=y,return_pct=100*(v-1),
                 partial_year=y in (result['summary']['start'][:4],result['summary']['latest_end'][:4]))
            for y,v in sorted(values.items())]


def main():
    OUT.mkdir(exist_ok=True)
    previous_run_names={r['run'] for r in read_csv(OUT/'summary.csv')}
    frozen={str(p.relative_to(ROOT)):digest(p) for folder in ('data','results_actual','results_us_restored',
             'results_eu_restored','results_eu_interim','results_research_corrected')
            for p in (ROOT/folder).rglob('*') if p.is_file() and 'long_history' not in p.parts and '__pycache__' not in p.parts}
    lam,registry=build_lam()
    datasets={}; audit=[]; starts={}; timing_starts={}; checks=[]; results=[]; baseline_checks=[]
    previous=read_csv(ROOT/'results_research_corrected/summary.csv')
    # Reproduce the unextended snapshots before adding historical facts.
    # Then isolate the user's freshness correction with exactly those same financial inputs.
    for region in ('US','EU'):
        for case in ('source','delay_legacy','delay_adjusted'):
            stage=('lam' if region=='US' else 'evidenced') if case=='source' else 'common'
            inp=TimingInputs(region,'interim',stage,lam,registry)
            inp.extend_freshness=case=='delay_adjusted'; inp.timing=case
            for rule in RULES:
                r=execute(inp,region,'prior_'+case,rule,PRIOR_START[region],'timing_repair')
                if case!='delay_adjusted':
                    old=next(s for s in previous if s['region']==region and s['panel']=='interim_'+stage and s['rule']==rule)
                    close(r['summary']['total_return'],old['total_return'])
                    baseline_checks.append(dict(region=region,case=case,rule=rule,result='PASS'))
                checks.append(validate(r,inp));results.append(r)
        for timing in ('source','delay_legacy','delay_adjusted'):
            inp=HistoryInputs(region,timing,lam,registry)
            datasets[region,timing]=inp
            records=coverage_audit(inp,region);audit+=records
            if timing=='source':starts[region]=earliest_complete(records)
            if timing=='delay_adjusted':timing_starts[region]=earliest_complete(records)
            save(OUT/f'{region}_{timing}_inputs.json',[r for r in inp.annual+inp.quarterly if inp.universe[r['ticker']]['region']==region])
    write_csv(OUT/'coverage_audit.csv',audit)
    added=[]
    for region in ('US','EU'):
        for r in datasets[region,'source'].added:
            if datasets[region,'source'].universe[r['ticker']]['region']==region:
                added.append(dict(region=region,ticker=r['ticker'],period_end=r['period_end'],
                                  period_type=r['period_type'],availability=r['availability_date'],
                                  observation_id=r['observation_id'],component_ids=r['component_ids']))
    write_csv(OUT/'added_observations.csv',added)
    print('Earliest complete starts:',starts,flush=True)
    common_start=max(starts.values())
    timing_start=max(common_start,*timing_starts.values())
    for region in ('US','EU'):
        for window,start in [('earliest_complete',starts[region]),('cross_region',common_start),
                             ('prior_start',PRIOR_START[region]),('timing_matched',timing_start)]:
            for timing in (('source',) if window in ('earliest_complete','cross_region') else ('source','delay_adjusted')):
                inp=datasets[region,timing]
                for rule in RULES:
                    r=execute(inp,region,'long_'+timing,rule,start,window)
                    checks.append(validate(r,inp,require_complete=timing=='source' or window=='timing_matched'))
                    results.append(r)
    summaries=[];statistics_rows=[];years=[];gaps=[]
    for r in results:
        s=r['summary'];region=s['region'];window=s['window'];case=s['timing']
        own=next(x for x in results if x['summary']['region']==region and x['summary']['window']==window
                 and x['summary']['timing']==case and x['summary']['rule']=='equal')
        fixed=next(x for x in results if x['summary']['region']==region and x['summary']['window']==window
                   and x['summary']['timing']=='source' and x['summary']['rule']=='equal')
        if window=='timing_matched':
            assert own['monthly']==fixed['monthly'],'Timing experiment changed the equal-weight control'
        s['own_coverage_control_return']=own['summary']['total_return']
        s['fixed_source_control_return']=fixed['summary']['total_return']
        s['vs_own_control_pp']=100*(s['total_return']-s['own_coverage_control_return'])
        s['vs_fixed_control_pp']=100*(s['total_return']-s['fixed_source_control_return'])
        summaries.append(s);years+=year_returns(r)
        for k,rows in r.items():
            if k!='summary':
                path=OUT/s['run']/(k+'.csv')
                if rows:write_csv(path,rows)
                elif path.exists():path.unlink()
        if s['rule']!='equal':
            for control_name,control in [('own_coverage',own),('fixed_source',fixed)]:
                statistics_rows.append(dict(run=s['run'],control=control_name,**active_stats(r,control)))
        else:
            for c in r['coverage']:
                if not c['covered']:
                    # Full ledger includes prelisting/delisted observations, classified separately.
                    inp=datasets[region,'source'] if window!='timing_repair' else TimingInputs(region,'interim','common',lam,registry)
                    gaps.append(dict(region=region,window=window,timing=case,date=c['date'],ticker=c['ticker'],
                                     listed_at_cutoff=is_listed(inp,c['ticker'],c['date']),reason=c['reason']))
    write_csv(OUT/'summary.csv',summaries);write_csv(OUT/'year_returns.csv',years)
    write_csv(OUT/'active_statistics.csv',statistics_rows);write_csv(OUT/'all_gaps.csv',gaps)
    gap_summary=[]
    for key in sorted({(r['region'],r['window'],r['timing'],r['ticker']) for r in gaps if r['listed_at_cutoff']}):
        rs=[r for r in gaps if (r['region'],r['window'],r['timing'],r['ticker'])==key and r['listed_at_cutoff']]
        gap_summary.append(dict(region=key[0],window=key[1],timing=key[2],ticker=key[3],
                                missing_months=len(rs),dates='|'.join(r['date'] for r in rs)))
    write_csv(OUT/'gap_summary.csv',gap_summary)
    current_run_names={s['run'] for s in summaries}
    for name in previous_run_names-current_run_names:
        path=OUT/name
        assert path.parent==OUT and name.startswith(('US_','EU_'))
        if path.is_dir():shutil.rmtree(path)
    for p,h in frozen.items():assert digest(ROOT/p)==h,('Frozen snapshot changed',p)
    validation=dict(starts=starts,cross_region_start=common_start,timing_matched_start=timing_start,
                    timing_matched_control_NAV_identical=True,runs=len(results),
                    added_observations=len(added),
                    baseline_reproductions=baseline_checks,checks=checks,preserved_files=len(frozen))
    save(OUT/'validation.json',validation)
    save(OUT/'preserved_manifest.json',[dict(path=p,sha256=h) for p,h in sorted(frozen.items())])
    inputs=[ROOT/'backtest.py',ROOT/'run_long_history.py',ROOT/'test_long_history.py',ROOT/'LONG_HISTORY_METHOD.md',
            ROOT/'collect_long_history_us.py',ROOT/'collect_long_history_prices.py',
            *[p for p in AREA.rglob('*') if p.is_file()]]
    save(OUT/'input_manifest.json',[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in sorted(inputs)])
    make_report(summaries,gap_summary,starts,common_start,validation,audit)
    print('PASS: histories, fixed controls, every coverage gap and preserved snapshots',flush=True)


def make_report(summary,gaps,starts,common_start,validation,audit):
    lines=['# Longer histories and repaired timing comparison','',
           'Run `python3 run_long_history.py`. [Method](../LONG_HISTORY_METHOD.md). Builds on the unmerged PR #3 correction inputs; source-date rules and costs remain unchanged.','',
           '**Scope: retrospective accounting-score tests, not a historical Pillar 2 backtest.** No government programme determines the June 2019 main start or September 2019 matched timing start. The dated industrial-policy participation gate is not applied. The captured [policy ledger](../data/policy_eligibility.csv) contains no event before 2022 and is not an exhaustive historical inventory. A valid Pillar 2 extension requires dated company eligibility under the relevant programmes; accounting-data coverage alone does not establish it.','',
           'All 16 US and 15 EU candidates remain in the retrospective pool. Companies enter the information set only after listing; no predecessor price proxy is used. Every listed/eligible company has prices, FX and a usable original financial observation throughout each main source-date window. These are the earliest complete windows supported by the original reports recovered in this release, not a claim that earlier research is impossible.','',
           f"Earliest complete starts: US **{starts['US']}**, EU **{starts['EU']}**. Common cross-region start: **{common_start}**. Endpoint: **2026-11-02**. US returns in USD; EU in EUR; costs 10bp/15bp per traded notional.",'',
           '| Region | Window | Start | Q50 | Q75 | Equal weight |','|---|---|---|---:|---:|---:|']
    for region in ('US','EU'):
        for window in ('earliest_complete','cross_region','prior_start','timing_matched'):
            ss={r['rule']:r for r in summary if r['region']==region and r['window']==window and r['timing']=='source'}
            lines.append(f"| {region} | {window} | {ss['equal']['start']} | "+' | '.join(f"{100*ss[k]['total_return']:.2f}%" for k in RULES)+' |')
    lines+=['','Earlier periods use annual reports where complete interim statements were not recovered. Subsequent original interim observations remain available; no annualization of invented quarters is used. Adding previously missing annual facts can also change results at the old start dates; the prior-start rows isolate this data effect from extending the holding period.','',
            'The preceding March 2019 review is incomplete: US Bloom/Linde original annual filings miss its March 1 information cutoff; EU ams, Safran, Enel and Nel also lack usable recovered figures at that cutoff. June is the next scheduled review after these original reports become available. Additional older original/pre-IPO archives could extend the boundary further; the audit does not declare such archives nonexistent.','',
            '## Timing correction','',
            'The earlier common-delay experiment also changed coverage: its unchanged freshness limits could expire a report before the delayed replacement became usable. The new `delay_adjusted` panel keeps the 180/90-day component availability floors but extends annual freshness from 550 to 730 days and interim freshness from 275 to 365 days. Source-date freshness stays 550/275 days. This offset is restricted to the artificial timing experiment.','',
            'Every delayed strategy is compared with the **fixed source-date equal-weight control**. Its own delayed-coverage control is reported separately so remaining initial-availability/membership changes stay visible. Extending freshness alone does not guarantee identical coverage, especially at the start or near a listing; only the fixed-control comparison keeps the hurdle unchanged.','',
            'First isolate the correction on the same inputs and starts as PR #3 (no newly recovered history):','',
            '| Region | Timing | Q50 | Q75 | Own control | Fixed source control | Q50 vs fixed |','|---|---|---:|---:|---:|---:|---:|']
    for region in ('US','EU'):
        for timing in ('source','delay_legacy','delay_adjusted'):
            ss={r['rule']:r for r in summary if r['region']==region and r['window']=='timing_repair' and r['timing']==timing}
            lines.append(f"| {region} | {timing} | "+' | '.join(f"{100*ss[k]['total_return']:.2f}%" for k in RULES)+f" | {100*ss['q50']['fixed_source_control_return']:.2f}% | {ss['q50']['vs_fixed_control_pp']:+.2f}pp |")
    lines+=['',f"The complete timing comparison starts **{validation['timing_matched_start']}**, the earliest common quarter-end with full coverage under both timing policies. The June 2019 EU delayed panel has too few usable reports to run; it is not silently advanced or compared with a different source-date start. Both equal-weight controls have identical monthly NAVs throughout this matched window:",'',
            '| Region | Timing | Q50 | Q75 | Own control | Fixed source control |','|---|---|---:|---:|---:|---:|']
    for region in ('US','EU'):
        for timing in ('source','delay_adjusted'):
            ss={r['rule']:r for r in summary if r['region']==region and r['window']=='timing_matched' and r['timing']==timing}
            lines.append(f"| {region} | {timing} | "+' | '.join(f"{100*ss[k]['total_return']:.2f}%" for k in RULES)+f" | {100*ss['q50']['fixed_source_control_return']:.2f}% |")
    lines+=['','## Every coverage gap','',
            '[All gaps](all_gaps.csv) lists each company/month, including a flag that separates listed candidates from prelisting/delisted cases. [Gap summary](gap_summary.csv) gives counts and exact dates. [Full pre-start coverage audit](coverage_audit.csv) includes every candidate each month and explains why earlier dates fail. None is silently removed to obtain an earlier main start.','',
            '| Region | Window | Timing | Company | Missing months | Dates |','|---|---|---|---|---:|---|']
    for r in gaps:
        if r['window'] in ('timing_repair','earliest_complete','timing_matched'):
            lines.append(f"| {r['region']} | {r['window']} | {r['timing']} | {r['ticker']} | {r['missing_months']} | {r['dates'].replace('|',', ')} |")
    lines+=['','## Data limits and checks','',
            'The universe was selected retrospectively. Longer histories do not remove survivor/selection bias or include companies absent from the research candidate list. Monthly dividend/split-adjusted prices are the same frozen vendor series used in the earlier study; independent dated daily overlap is limited to the recent window. They are not a certified historical investable index. Listing overrides exclude pre-merger Linde/Praxair and pre-spin-off GE Vernova proxies.','',
            f"Added {validation['added_observations']} financial observations (100 annual and one GFS trailing observation): [observation inventory](added_observations.csv). Older original source facts, publication dates, component IDs, accession evidence and downloaded-source hashes are under [data/long_history](../data/long_history). Additional FX observations come from official FRED tables and preserve every existing rate. Later comparative facts are not backdated to earlier reports.",'',
            'Older TSM observations are standalone IASB-IFRS annual 20-Fs in TWD at their actual filing dates; later restored observations use the already documented Taiwan-IFRS series. No TTM calculation combines these bases. Linde 2018/2019 group operating cashflow explicitly includes the separately reported discontinued-operation cashflows; the source audit retains both rows and the arithmetic.','',
            'The engine now honors explicitly requested starts before 2020 and exposes a freshness policy hook. Its original defaults remain unchanged. Historical snapshot code manifests refer to the earlier commit; data/result bytes and the reproduced numerical outputs are preserved.','',
            f"Validation: {validation['runs']} runs, {len(validation['baseline_reproductions'])} PR #3 reproductions, all selected source/component cutoffs, policy-specific freshness, full source-date coverage, listing restrictions, cost/holdings/NAV reconciliation, and {validation['preserved_files']} prior data/result files preserved byte-for-byte.",'',
            'Tests: `python3 -m unittest test_long_history.py test_research_corrections.py` (12 regression tests).','',
            '[Summary including CAGR, volatility and drawdown](summary.csv) · [Calendar-year returns](year_returns.csv) · [Monthly active statistics](active_statistics.csv) · [Validation](validation.json) · [Input manifest](input_manifest.json).','']
    (OUT/'REPORT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
