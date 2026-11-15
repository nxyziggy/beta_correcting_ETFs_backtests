#!/usr/bin/env python3
"""Reconstruct dated policy admission and rerun the frozen accounting strategies."""
import datetime as dt
import json
from collections import defaultdict

from backtest import benchmark, read_csv, run
from prepare_data import ROOT, DATA
from run_long_history import (HistoryInputs, COST, RULES, is_listed, validate,
                              year_returns, build_lam)
from run_research_corrections import active_stats, close, digest, save, write_csv

AREA = DATA/'pillar2'
OUT = ROOT/'results_pillar2'
MODES = ('direct', 'with_indirect')


def read_research():
    events, candidates = [], []
    for path in sorted(AREA.glob('research_*.json')):
        source = json.loads(path.read_text())
        events += [dict(e, research_file=str(path.relative_to(ROOT))) for e in source['events']]
        candidates += source['candidates']
    universe = {r['ticker']:r for r in json.loads((DATA/'universe.json').read_text())}
    assert {r['ticker'] for r in candidates} == set(universe), 'Every candidate needs a research audit'
    assert len(candidates) == len(universe), 'Duplicate candidate audit'
    assert len({e['event_id'] for e in events}) == len(events), 'Duplicate event identifier'
    for e in events:
        assert e['ticker'] in universe and e['region'] == universe[e['ticker']]['region']
        assert isinstance(e['qualifies'], bool)
        assert e['relationship'] in ('direct', 'subsidiary', 'indirect')
        for key in ('event_date', 'public_date', 'eligible_from'):
            if e.get(key): dt.date.fromisoformat(e[key])
        if e['qualifies']:
            assert all(e.get(k) for k in ('event_date','public_date','eligible_from','programme','sources'))
            assert e['eligible_from'] >= max(e['event_date'], e['public_date'], e.get('ownership_date') or '')
            assert e['eligible_from'] <= '2026-11-02', 'Event after market endpoint'
            assert all(s.get('url','').startswith('https://') and s.get('evidence') for s in e['sources'])
            if e.get('end_date'):
                dt.date.fromisoformat(e['end_date'])
                assert e['end_date'] > e['eligible_from']
                assert e['end_date'] >= (e.get('cancellation_public_date') or '')
        # Empty means no captured withdrawal, not a claim of perpetual funding.
        e['end_date'] = e.get('end_date') or ''
    return sorted(events,key=lambda e:(e['ticker'],e.get('eligible_from') or '9999',e['event_id'])), candidates


def accepted(event, mode):
    assert mode in MODES
    return event['qualifies'] and (mode == 'with_indirect' or event['relationship'] != 'indirect')


def end_boundary(event):
    """Exclusive engine boundary: a same-cutoff disclosure is not known yet."""
    end=event.get('end_date')
    if not end:return ''
    disclosure=(event.get('cancellation_public_date') or event.get('ownership_end_public_date')
                or event.get('end_public_date') or end)
    first_usable=(dt.date.fromisoformat(disclosure)+dt.timedelta(days=1)).isoformat()
    return max(end,first_usable)


def active_events(events, ticker, date, mode):
    cutoff = date[:7]+'-01'
    return [e for e in events if e['ticker']==ticker and accepted(e,mode)
            and e['eligible_from'] < cutoff and (not end_boundary(e) or cutoff < end_boundary(e))]


class PolicyInputs(HistoryInputs):
    def __init__(self, region, timing, mode, events, lam, registry):
        super().__init__(region,timing,lam,registry)
        self.mode, self.policy_events = mode, events
        for r in json.loads((AREA/'listing_additions.json').read_text()):
            self.universe[r['ticker']]['listing_start']=r['listing_start']
        self.policy = [dict(ticker=e['ticker'], start_date=e['eligible_from'], end_date=end_boundary(e))
                       for e in events if accepted(e,mode)]

    def signals(self, region, date, panel, gate=True, annual_lag=0):
        assert gate, 'Policy experiment must explicitly enable its gate'
        return super().signals(region,date,panel,True,0)


def coverage_audit(inp, region):
    dates = sorted(d for d in set.intersection(*(set(inp.prices[t]) for t in benchmark(region)))
                   if '2008-01-01' <= d <= inp.extension_config['complete_month_end'])
    for a,b in zip(dates,dates[1:]):
        assert (int(b[:4])-int(a[:4]))*12+int(b[5:7])-int(a[5:7]) == 1
    rows = []
    for date in dates:
        scores, reasons = inp.signals(region,date,'hybrid',True)
        for ticker,u in inp.universe.items():
            if u['region'] != region: continue
            listing = is_listed(inp,ticker,date)
            es = active_events(inp.policy_events,ticker,date,inp.mode)
            required = listing and bool(es)
            complete = required and ticker in scores
            reason = reasons.get(ticker,'covered')
            if not listing: reason = 'not listed at information cutoff or already delisted'
            elif not es: reason = 'no captured qualifying policy event at cutoff'
            if complete:
                try:
                    inp.price(ticker,date,region)
                    for b in benchmark(region): inp.price(b,date,region)
                except ValueError as exc:
                    complete, reason = False, str(exc)
            r=scores.get(ticker,{})
            rows.append(dict(region=region,definition=inp.mode,timing=inp.timing,date=date,
                             information_cutoff=date[:7]+'-01',ticker=ticker,listed_at_cutoff=listing,
                             policy_eligible=bool(es),required=required,complete=complete,reason=reason,
                             event_ids='|'.join(e['event_id'] for e in es),
                             observation_id=r.get('observation_id',''),available_used=r.get('available_used','')))
    return rows


def start_audit(rows):
    by_date=defaultdict(list)
    for r in rows: by_date[r['date']].append(r)
    suffix=True; complete_starts=[]; audit=[]
    for date,rs in sorted(by_date.items(),reverse=True):
        required=[r for r in rs if r['required']]
        missing=[r for r in required if not r['complete']]
        good=len(required)>=4 and not missing
        suffix &= good
        if int(date[5:7]) in (3,6,9,12):
            audit.append(dict(region=rs[0]['region'],definition=rs[0]['definition'],timing=rs[0]['timing'],
                              date=date,policy_eligible_listed=len(required),covered=len(required)-len(missing),
                              missing_tickers='|'.join(r['ticker'] for r in missing),
                              complete_this_month=good,complete_remaining_window=suffix))
            if suffix: complete_starts.append(date)
    assert complete_starts, ('No complete policy-gated window',rows[0]['region'],rows[0]['definition'])
    return min(complete_starts),list(reversed(audit))


def validate_policy(result, inp):
    check=validate(result,inp)
    assert result['summary']['documented_policy_gate']
    monthly_dates={r['date'] for r in result['monthly']}
    source_audit=coverage_audit(inp,result['summary']['region'])
    assert all(r['complete'] for r in source_audit if r['date'] in monthly_dates and r['required'])
    links=[]
    for h in result['holdings']:
        if h['ticker']=='CASH':continue
        es=active_events(inp.policy_events,h['ticker'],h['date'],inp.mode)
        assert es,('Holding without public policy evidence',h)
        links.append(dict(run=result['summary']['run'],date=h['date'],ticker=h['ticker'],weight=h['weight'],
                          information_cutoff=h['date'][:7]+'-01',event_ids='|'.join(e['event_id'] for e in es)))
    for s in result['scores']:
        assert active_events(inp.policy_events,s['ticker'],s['date'],inp.mode)
        assert s['P2']=='documented policy participation gate'
    check['holdings_with_policy_links']=len(links)
    return check, links


def main():
    OUT.mkdir(exist_ok=True)
    previous={r['run'] for r in read_csv(OUT/'summary.csv')}
    # Older experiments remain byte-identical; policy research and outputs are additive.
    folders=('data','results_actual','results_us_restored','results_eu_restored','results_eu_interim',
             'results_research_corrected','results_long_history')
    frozen={str(p.relative_to(ROOT)):digest(p) for folder in folders for p in (ROOT/folder).rglob('*')
            if p.is_file() and 'pillar2' not in p.parts and '__pycache__' not in p.parts}
    research_hashes={p:digest(p) for p in AREA.rglob('*') if p.is_file()}
    events,candidates=read_research()
    save(OUT/'events_normalized.json',events)
    lam,registry=build_lam()
    datasets={};audit=[];start_rows=[];starts={}
    for mode in MODES:
        for region in ('US','EU'):
            for timing in ('source','delay_adjusted'):
                inp=PolicyInputs(region,timing,mode,events,lam,registry)
                key=(mode,region,timing);datasets[key]=inp
                rows=coverage_audit(inp,region);audit+=rows
                starts[key],rs=start_audit(rows);start_rows+=rs
    write_csv(OUT/'monthly_eligibility.csv',audit)
    write_csv(OUT/'start_audit.csv',start_rows)
    financial_gaps=[r for r in audit if r['required'] and not r['complete']]
    write_csv(OUT/'all_financial_gaps.csv',financial_gaps)
    results=[];checks=[];links=[];run_inputs={}
    for mode in MODES:
        cross=max(starts[mode,r,'source'] for r in ('US','EU'))
        matched=max(starts[mode,r,t] for r in ('US','EU') for t in ('source','delay_adjusted'))
        for region in ('US','EU'):
            for window,start,timings in (
                ('earliest_complete',starts[mode,region,'source'],('source',)),
                ('cross_region',cross,('source',)),
                ('timing_matched',matched,('source','delay_adjusted'))):
                for timing in timings:
                    inp=datasets[mode,region,timing]
                    for rule in RULES:
                        result=run(inp,region,'pillar2_'+mode+'_'+timing,rule,COST[region],
                                   gate=True,annual_lag=0,start=start)
                        assert result is not None
                        s=result['summary'];s['run']+='_'+window
                        s.update(definition=mode,timing=timing,window=window,
                                 policy_membership='historical_confirmed_recipient',
                                 annual_freshness_days=inp.freshness_days({'period_type':'annual'}),
                                 interim_freshness_days=inp.freshness_days({'period_type':'trailing'}))
                        check,ls=validate_policy(result,inp);checks.append(check);links+=ls
                        results.append(result);run_inputs[s['run']]=inp
    summaries=[];years=[];statistics=[]
    for result in results:
        s=result['summary']
        own=next(r for r in results if all(r['summary'][k]==s[k] for k in ('definition','region','window','timing'))
                 and r['summary']['rule']=='equal')
        fixed=next(r for r in results if all(r['summary'][k]==s[k] for k in ('definition','region','window'))
                   and r['summary']['timing']=='source' and r['summary']['rule']=='equal')
        if s['window']=='timing_matched':assert own['monthly']==fixed['monthly'],'Timing changed control'
        s['fixed_policy_control_return']=fixed['summary']['total_return']
        s['vs_fixed_policy_control_pp']=100*(s['total_return']-s['fixed_policy_control_return'])
        summaries.append(s);years+=year_returns(result)
        if s['rule']!='equal':statistics.append(dict(run=s['run'],**active_stats(result,fixed)))
        for name,rows in result.items():
            if name=='summary':continue
            path=OUT/s['run']/(name+'.csv')
            if rows:write_csv(path,rows)
            elif path.exists():path.unlink()
    # Verify numerical preservation independently of file hashes.
    baseline=[]
    old=read_csv(ROOT/'results_long_history/summary.csv')
    for region in ('US','EU'):
        inp=HistoryInputs(region,'source',lam,registry)
        for rule in RULES:
            reference=next(r for r in old if r['region']==region and r['window']=='earliest_complete'
                           and r['timing']=='source' and r['rule']==rule)
            result=run(inp,region,'ungated_check',rule,COST[region],annual_lag=0,start=reference['start'])
            close(result['summary']['total_return'],reference['total_return'])
            baseline.append(dict(region=region,rule=rule,status='PASS'))
    universe=datasets['direct','US','source'].universe
    candidate_rows=[]
    for c in sorted(candidates,key=lambda r:(universe[r['ticker']]['region'],r['ticker'])):
        t=c['ticker'];es=[e for e in events if e['ticker']==t]
        direct=[e for e in es if accepted(e,'direct')]
        broad=[e for e in es if accepted(e,'with_indirect')]
        candidate_rows.append(dict(ticker=t,name=universe[t]['name'],region=universe[t]['region'],
                                   first_direct_evidence=min((e['eligible_from'] for e in direct),default=''),
                                   first_including_indirect=min((e['eligible_from'] for e in broad),default=''),
                                   direct_event_ids='|'.join(e['event_id'] for e in direct),
                                   indirect_event_ids='|'.join(e['event_id'] for e in broad if e['relationship']=='indirect'),
                                   coverage_status=c['coverage_status'],unresolved=json.dumps(c.get('unresolved',[]))))
    write_csv(OUT/'candidate_audit.csv',candidate_rows)
    write_csv(OUT/'summary.csv',summaries);write_csv(OUT/'year_returns.csv',years)
    write_csv(OUT/'active_statistics.csv',statistics);write_csv(OUT/'holdings_policy_links.csv',links)
    # Only remove outputs of previously generated runs no longer in this specification.
    import shutil
    for name in previous-{s['run'] for s in summaries}:
        p=OUT/name
        assert p.parent==OUT and name.startswith(('US_','EU_'))
        if p.is_dir():shutil.rmtree(p)
    for p,h in frozen.items():assert digest(ROOT/p)==h,('Prior snapshot changed',p)
    for p,h in research_hashes.items():assert digest(p)==h,('Research changed during run',str(p.relative_to(ROOT)))
    assert read_research()[0]==events,'Normalized event ledger is not an exact copy of the source research'
    validation=dict(status='PASS',runs=len(results),candidates=len(candidates),events=len(events),
                    starts=[dict(definition=k[0],region=k[1],timing=k[2],start=v) for k,v in starts.items()],
                    timing_controls_identical=True,checks=checks,ungated_reproductions=baseline,
                    preserved_files=len(frozen))
    save(OUT/'validation.json',validation)
    save(OUT/'preserved_manifest.json',[dict(path=p,sha256=h) for p,h in sorted(frozen.items())])
    inputs=[ROOT/p for p in ('backtest.py','run_research_corrections.py','run_long_history.py',
                            'run_pillar2.py','test_pillar2.py','PILLAR2_METHOD.md')]
    inputs += [p for p in AREA.rglob('*') if p.is_file()]
    save(OUT/'input_manifest.json',[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in sorted(inputs)])
    make_report(summaries,candidate_rows,events,validation,start_rows)
    print(json.dumps(validation['starts'],indent=2))
    print('PASS: policy gates, every candidate, complete coverage, unchanged timing controls and ungated returns')


def make_report(summary,candidates,events,validation,start_rows):
    lines=['# Historical Pillar 2 eligibility and portfolio results','',
           'Run `python3 run_pillar2.py`. [Admission rule and limitations](../PILLAR2_METHOD.md).',
           'The main panel requires published, named direct/subsidiary support under an industrial, technology or energy programme. Earlier programmes qualify; broad sector exposure alone does not. Every US/EU research candidate is audited. Missing evidence remains an exclusion rather than an assumed award.','',
           'Membership means **historical confirmed-recipient admission**, not a claim that an old grant remains active or unspent. Completed projects do not erase past receipt. Recorded withdrawals can end an event; other valid events can still qualify the company. The candidate list is still retrospective, and this is not a reconstruction of every listed subsidy recipient outside the 31 candidates.','',
           '## Main results: direct and subsidiary recipients','',
           'Cumulative returns include 10bp US / 15bp EU trading costs through **2 November 2026**. US returns are in USD and EU returns in EUR. Different earliest starts are not a common-period regional comparison.','',
           '| Region | Window | Start | Q50 | Q75 | Equal weight |',
           '|---|---|---|---:|---:|---:|']
    for mode in MODES:
        if mode!='direct':lines+=['','## Sensitivity including evidenced indirect beneficiaries','',
                                  'Only dated company-specific supplier/customer links qualify here. These are not labeled direct awards.','',
                                  '| Region | Window | Start | Q50 | Q75 | Equal weight |',
                                  '|---|---|---|---:|---:|---:|']
        for region in ('US','EU'):
            for window in ('earliest_complete','cross_region'):
                ss={s['rule']:s for s in summary if s['definition']==mode and s['region']==region
                    and s['window']==window and s['timing']=='source'}
                lines.append(f"| {region} | {window} | {ss['equal']['start']} | "+
                             ' | '.join(f"{100*ss[k]['total_return']:.2f}%" for k in RULES)+' |')
    lines+=['','## Why these starts','',
            'Policy evidence and data availability jointly determine the start. The engine requires at least four scored eligible companies and complete coverage of every listed policy-eligible candidate throughout the remaining window. A company is not removed merely to obtain an earlier start. No return was used to select these dates.','',
            '[Quarterly start audit](start_audit.csv) lists policy counts and every blocking company. '
            '[Monthly eligibility](monthly_eligibility.csv) distinguishes policy exclusion, listing status and missing financial/market inputs. '
            '[Every financial gap](all_financial_gaps.csv) includes pre-start periods.','']
    for region in ('US','EU'):
        start=next(s['start'] for s in summary if s['definition']=='direct' and s['region']==region
                   and s['window']=='earliest_complete')
        prior=[r for r in start_rows if r['definition']=='direct' and r['region']==region
               and r['timing']=='source' and r['date']<start]
        if prior:
            p=prior[-1]
            lines.append(f"- {region}: preceding review {p['date']} has {p['policy_eligible_listed']} listed policy-eligible companies, "
                         f"{p['covered']} covered; missing inputs: {p['missing_tickers'] or 'none in that month (see subsequent gaps)'}. "
                         f"The first complete remaining window starts {start}.")
    lines+=['','## Every candidate and its earliest captured admission evidence','',
            'Dates below are evidence/ownership dates, not automatic purchase dates. The first-of-month cutoff, listing restrictions, quarterly admission and financial coverage also apply. Blank means no qualifying source captured under that definition; it is not proof that a company never received support.','',
            '| Region | Company | First direct/subsidiary | Including indirect | Direct programme(s) |',
            '|---|---|---|---|---|']
    for c in candidates:
        programs=[]
        for e in events:
            if e['ticker']==c['ticker'] and accepted(e,'direct') and e['programme'] not in programs:
                url=e['sources'][0]['url']
                programs.append(f"[{e['programme']}]({url})")
        lines.append(f"| {c['region']} | {c['ticker']} | {c['first_direct_evidence'] or 'Not evidenced'} | "
                     f"{c['first_including_indirect'] or 'Not evidenced'} | {'; '.join(programs).replace('|','/')} |")
    lines+=['','[All-candidate audit and unresolved questions](candidate_audit.csv) · '
            '[Source-linked event ledger](events_normalized.json) · '
            '[Policy events supporting every holding](holdings_policy_links.csv).','',
            '## Matched financial-timing comparison','',
            'The financial delay uses 180/90-day availability floors and 730/365-day freshness; policy dates stay unchanged. '
            'Each definition starts both financial treatments together when coverage is complete. Equal-weight monthly NAVs are asserted identical within each region/definition.','',
            '| Definition | Region | Start | Timing | Q50 | Q75 | Equal weight |',
            '|---|---|---|---|---:|---:|---:|']
    for mode in MODES:
        for region in ('US','EU'):
            for timing in ('source','delay_adjusted'):
                ss={s['rule']:s for s in summary if s['definition']==mode and s['region']==region
                    and s['window']=='timing_matched' and s['timing']==timing}
                lines.append(f"| {mode} | {region} | {ss['equal']['start']} | {timing} | "+
                             ' | '.join(f"{100*ss[k]['total_return']:.2f}%" for k in RULES)+' |')
    lines+=['','## Validation and remaining limits','',
            f"{validation['runs']} runs pass policy/source cutoffs, complete eligible coverage, listing and cost/holdings/NAV checks. "
            f"All {validation['candidates']} candidates have a research record. Six ungated headline results reproduce; "
            f"{validation['preserved_files']} earlier input/result files remain byte-identical.",'',
            'This adds the dated admission gate to the existing two accounting signals. It does not add subsidy utilization, '
            'full six-factor scoring, fixed sector baskets or Pillar 3 network scores. Earlier adjusted prices and the retrospective '
            'candidate list retain the limitations documented in the longer-history report. The earliest captured evidence is '
            'a conservative research boundary, not a claim that every earlier archive has been exhausted.','',
            'There is no minimum award-size threshold. Small targeted research/training awards can establish eligibility; '
            'that does not establish material or continuing earnings support. Public infrastructure and university benefits '
            'are classified as indirect unless company receipt or ownership is documented.','',
            '[Why US/EU results differ](ATTRIBUTION.md) · '
            '[Summary with CAGR/volatility/drawdown](summary.csv) · [Active-return statistics](active_statistics.csv) · '
            '[Year returns](year_returns.csv) · [Validation](validation.json) · [Input hashes](input_manifest.json).','']
    (OUT/'REPORT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
