#!/usr/bin/env python3
"""Audit an any prior public support screen and rerun frozen accounting strategies."""
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
        assert e['award_amount_status'] and e['award_amount_note']
        for prefix in ('award', 'project_total'):
            amount, currency = e[prefix+'_amount'], e[prefix+'_currency']
            assert (amount is None) == (currency is None), e['event_id']
            if amount is not None:
                assert isinstance(amount, (int, float)) and amount > 0
                assert currency in ('USD','EUR','GBP','DKK','NOK')
        if e['award_amount_status'] == 'project_total_only':
            assert e['award_amount'] is None and e['project_total_amount'] is not None
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


def support_binding_audit(rows, summaries):
    """Monthly admission exclusions, not unselected holdings or missing financials."""
    totals, exclusions = [], []
    for mode in MODES:
        start = next(s['start'] for s in summaries if s['definition']==mode
                     and s['window']=='cross_region' and s['timing']=='source')
        listed = [r for r in rows if r['definition']==mode and r['timing']=='source'
                  and r['date']>=start and r['listed_at_cutoff'] in (True,'True')]
        excluded = [r for r in listed if r['policy_eligible'] not in (True,'True')]
        exclusions += [dict(definition=mode,region=r['region'],ticker=r['ticker'],
                            date=r['date'],information_cutoff=r['information_cutoff'],
                            reason=r['reason']) for r in excluded]
        for region in ('US','EU','US+EU'):
            rs=[r for r in listed if region=='US+EU' or r['region']==region]
            no=[r for r in excluded if region=='US+EU' or r['region']==region]
            totals.append(dict(definition=mode,region=region,start=start,
                               end=max(r['date'] for r in rs),listed_company_months=len(rs),
                               excluded_company_months=len(no),binding_rate=len(no)/len(rs)))
    return totals, exclusions


def first_admission_audit(events):
    """Classify the earliest direct event's scheme, not every later company award."""
    rows=[]
    for ticker in sorted({e['ticker'] for e in events}):
        eligible=sorted((e for e in events if e['ticker']==ticker and accepted(e,'direct')),
                        key=lambda e:(e['eligible_from'],e['event_id']))
        if not eligible:continue
        e=eligible[0]
        rows.append(dict(ticker=ticker,region=e['region'],event_id=e['event_id'],
                         eligible_from=e['eligible_from'],programme=e['programme'],
                         article_named_stream=e.get('article_named_stream') or 'earlier/other programme'))
    return rows


def award_amount_audit(events):
    fields=('event_id','ticker','region','qualifies','relationship','award_amount',
            'award_currency','award_amount_status','award_amount_note','project_total_amount',
            'project_total_currency','project_total_basis','article_named_stream')
    return [dict(**{k:e.get(k) for k in fields},
                 sources='|'.join(s['url'] for s in e['sources'])) for e in events]


def original_ledger_start_audit(lam, registry):
    """Coverage diagnostic only; the sparse original ledger is not reclassified."""
    result=[]
    for region in ('US','EU'):
        inp=HistoryInputs(region,'source',lam,registry)
        dates=sorted(d for d in set.intersection(*(set(inp.prices[t]) for t in benchmark(region)))
                     if '2019-01-01'<=d<=inp.extension_config['complete_month_end'])
        rows=[]
        for date in dates:
            cutoff=date[:7]+'-01'
            eligible={e['ticker'] for e in inp.policy if e['region']==region
                      and e['start_date']<cutoff and (not e.get('end_date') or cutoff<e['end_date'])
                      and is_listed(inp,e['ticker'],date)}
            scores,_=inp.signals(region,date,'hybrid',gate=True)
            missing=eligible-set(scores)
            for ticker in eligible:
                try:
                    inp.price(ticker,date,region)
                    for b in benchmark(region):inp.price(b,date,region)
                except ValueError:missing.add(ticker)
            rows.append(dict(date=date,eligible=sorted(eligible),covered=len(eligible)-len(missing),
                             missing=sorted(missing)))
        quarters=[r for r in rows if r['date'][5:7] in ('03','06','09','12')]
        first=next(r for r in quarters if r['covered']>=4 and not r['missing'])
        complete=next(r for r in quarters if all(s['covered']>=4 and not s['missing']
                                               for s in rows if s['date']>=r['date']))
        five=next((r for r in quarters if r['covered']>=5 and not r['missing']),None)
        result.append(dict(region=region,first_investable_quarter=first,
                           first_complete_remaining_window=complete,first_five_name_quarter=five))
    return dict(source='data/policy_eligibility.csv',financial_inputs='HistoryInputs(source), hybrid',
                engine_start_requirement='At least four scored names at a quarter-end; default minimum_holdings=1 does not lower that startup threshold.',
                coverage_requirement='Every then-listed eligible company has usable financial and investor-currency price data; complete suffix checked through the last full month.',
                limitation='The original sparse ledger is not exhaustive and includes EU programme approvals/participation with national grants pending. This diagnostic does not certify a confirmed-article-stream reconstruction.',
                results=result)


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
            if p.is_file() and 'pillar2' not in p.parts and 'recovery_experiments' not in p.parts
            and '__pycache__' not in p.parts}
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
    binding,exclusions=support_binding_audit(audit,summaries)
    admissions=first_admission_audit(events)
    write_csv(OUT/'binding_rates.csv',binding)
    write_csv(OUT/'binding_exclusions.csv',exclusions)
    write_csv(OUT/'first_admission_audit.csv',admissions)
    write_csv(OUT/'award_amounts.csv',award_amount_audit(events))
    original_ledger=original_ledger_start_audit(lam,registry)
    save(OUT/'original_ledger_start_audit.json',original_ledger)
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
                            'run_pillar2.py','test_pillar2.py','test_support_screen_audit.py','PILLAR2_METHOD.md')]
    inputs += [p for p in AREA.rglob('*') if p.is_file()]
    save(OUT/'input_manifest.json',[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in sorted(inputs)])
    make_report(summaries,candidate_rows,events,validation,start_rows,binding,exclusions,admissions,original_ledger)
    print(json.dumps(validation['starts'],indent=2))
    print('PASS: policy gates, every candidate, complete coverage, unchanged timing controls and ungated returns')


def make_report(summary,candidates,events,validation,start_rows,binding,exclusions,admissions,original_ledger):
    lines=['# Any prior public support screen and portfolio results','',
           'Run `python3 run_pillar2.py`. [Admission rule and limitations](../PILLAR2_METHOD.md).',
           'This broad historical extension admits a listed candidate after captured public evidence of any qualifying named direct/subsidiary public support, however small, under an earlier industrial, technology or energy programme. No minimum size or recency is required. Completed projects remain evidence of past support; a recorded withdrawal or ownership boundary can end an event. Missing evidence is not an assumed award.','',
           'It is **not a replication of the article\'s specified policy streams, baskets or event dates**. The article discusses confirmed subsidies broadly, but operationally names CHIPS/IRA and EU Chips/IPCEI/France 2030/Green Deal support and illustrates June 2023 admission for Infineon and NXP. This screen instead admits both from a 2014 EnLight research project. The 31-company candidate list is retrospective and is not an exhaustive historical recipient universe. [Article](https://mitleadtrades.substack.com/p/performative-beta-trap-correcting).','',
           '## How often the screen excludes a listed company','',
           'The denominator is one observation per listed candidate per complete month from each definition\'s common cross-region start. An exclusion means no usable qualifying support event before the first day of that month. It does not mean that the score rejected the company or that its financial data were missing. The terminal 2 November 2026 partial return is not another company-month.','',
           '| Definition | Region | First month | Last month | Listed company-months | Excluded | Binding rate |',
           '|---|---|---|---|---:|---:|---:|']
    for r in binding:
        lines.append(f"| {r['definition']} | {r['region']} | {r['start']} | {r['end']} | "
                     f"{r['listed_company_months']:,} | {r['excluded_company_months']} | {100*r['binding_rate']:.2f}% |")
    lines+=['','| Definition | Excluded company | Months | First excluded month | Last excluded month |',
            '|---|---|---:|---|---|']
    for mode in MODES:
        for ticker in sorted({r['ticker'] for r in exclusions if r['definition']==mode}):
            dates=sorted(r['date'] for r in exclusions if r['definition']==mode and r['ticker']==ticker)
            lines.append(f"| {mode} | {ticker} | {len(dates)} | {dates[0]} | {dates[-1]} |")
    article_first=[r for r in admissions if r['article_named_stream']!='earlier/other programme']
    tsm_months=sum(r['definition']=='direct' and r['ticker']=='TSM' for r in exclusions)
    alfen_months=sum(r['definition']=='direct' and r['ticker']=='ALFEN.AS' for r in exclusions)
    lines+=['',f"Only {len(article_first)} of {len(admissions)} earliest direct admissions in this ledger use the article's named modern streams: "+
            '; '.join(f"{r['ticker']} ({r['article_named_stream']})" for r in article_first)+'. '+
            'This counts first admissions only; a company can receive another programme later. '
            'Micron is excluded in June and July 2019; its July 1 event becomes usable in August, while new purchases wait for a quarterly review.','',
            '[Binding counts](binding_rates.csv) · [Every excluded company-month](binding_exclusions.csv) · '
            '[First-admission classification](first_admission_audit.csv).','',
            f'The screen excludes very few observations. The TSMC direct-versus-indirect classification accounts for {tsm_months} US company-months; '
            f'Alfen accounts for all {alfen_months} direct EU exclusions. The indirect EU coverage matches the ungated pool. '
            'The result measures accounting selection within this candidate list, not broad discrimination between firms with and without meaningful public support.','',
            'The sparse original policy ledger produces the following coverage-only start diagnostic under the engine\'s minimum of four scored names at a quarter-end:','',
            '| Region | First investable quarter | Covered eligible companies | First five-name quarter |',
            '|---|---|---:|---|']
    for r in original_ledger['results']:
        first=r['first_investable_quarter'];five=r['first_five_name_quarter']
        lines.append(f"| {r['region']} | {first['date']} | {first['covered']} | {five['date'] if five else 'None'} |")
    lines+=['','All then-eligible companies are covered at those starts and throughout the remaining monthly window. '
            'This is a diagnostic of the existing sparse ledger, whose EU records include programme participation with national funding pending; '
            'it is not a new confirmed-award reconstruction or a return backtest of the article\'s streams. '
            '[Diagnostic and exact eligible sets](original_ledger_start_audit.json).','',
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
    lines+=['','## Award amounts and the Alfen boundary','',
            'Amounts do not affect admission, ranks or weights. Each event records a company amount and currency when established, or an explicit unknown/project-total-only status. '
            'Ceilings, conditional commitments, recognized credits and lower bounds retain separate labels. Consortium costs, public contributions and third-party awards are not assigned to each company. '
            'Missing amounts are null, never zero. [All event amounts and evidence](award_amounts.csv).','',
            '- Lam Research: USD48,816 approved California training contract. '
            '[State release](https://www.labor.ca.gov/wp-content/uploads/sites/338/2019/07/ETPPressRelease-January2016.pdf).',
            '- Texas Instruments: USD5,124,000 TEF commitment conditional on investment and staffing; no payment is inferred. '
            '[Governor release](https://gov.texas.gov/news/post/governor-abbott-announces-texas-instruments-new-300mm-facility-in-richardson).',
            '- Infineon and NXP: EUR41.3m is the total EnLight cost across 27 partners, only partly publicly funded. Individual company awards and the total public contribution are unknown. '
            '[ECSEL release](https://via.ritzau.dk/pressemeddelelse/3293310/ecsel?publisherId=90456).','',
            'Alfen\'s March 2018 prospectus reports EUR968,000 of 2017 government-grant income for an African solar/storage system, but the captured passage does not identify the grantor or programme. '
            'The later DEI ISES record names Alfen and a EUR2,776,119 project grant; its final-report publication is dated 13 April 2020. '
            'The descriptions plausibly concern the same project, but that does not establish that the Dutch grantor/programme was publicly identifiable in March 2018. '
            'The existing 2020 direct-admission boundary is retained as an unresolved evidence/classification choice, not a claim that Alfen received no earlier public support. '
            'Separately evidenced SDE+ customer exposure admits it in the indirect panel. '
            '[2018 prospectus, note 9](https://live.euronext.com/sites/default/files/amco-9819704-v1-prospectus_alfen_n_v__dated_12_march_2018_including_e-disclaimer.pdf) · '
            '[DEI registry](https://projecten.topsectorenergie.nl/projecten/integrated-sustainable-energy-station-19011).','',
            '[All-candidate audit and unresolved questions](candidate_audit.csv) · '
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
