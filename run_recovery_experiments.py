#!/usr/bin/env python3
"""Run the fixed scoring/exit grid without changing the production defaults."""
import json
import math
import platform
from collections import defaultdict

from backtest import read_csv,run
from prepare_data import ROOT,DATA
from recovery_rules import VARIANTS,RecoveryInputs,RecoveryExitPolicy
from recovery_diagnostics import chronological_rows,first_entry_rows,recovery_exit_rows
from run_long_history import COST,year_returns,validate
from run_pillar2 import read_research,build_lam,active_events
from run_research_corrections import active_stats,close,digest,save,write_csv

OUT=ROOT/'results_recovery_experiments'
CASES={
    'direct_main':('direct','source','2019-06-30','earliest_complete'),
    'direct_timing_source':('direct','source','2019-09-30','timing_matched'),
    'direct_timing_delayed':('direct','delay_adjusted','2019-09-30','timing_matched'),
    'indirect_main':('with_indirect','source','2019-06-30','earliest_complete'),
}
FEATURE_FIELDS=('base_score','roce','cash_accruals','rank_roce','rank_quality','observation_id','available_used',
                'period_end','trend_available','prior_review','prior_information_cutoff','prior_observation_id',
                'prior_available_used','prior_report_period','same_report_period','delta_roce','delta_cash_quality',
                'trend_rank','improving_both','momentum_available','momentum_start','momentum_end',
                'momentum_start_price','momentum_end_price','momentum_return','momentum_rank','momentum_missing_reason')


def validate_features(inp,region,dates):
    rows=[]
    for date in dates:
        sc,_=inp.features(region,date)
        for ticker,r in sc.items():
            cutoff=date[:7]+'-01'
            assert active_events(inp.policy_events,ticker,date,inp.mode)
            assert r['available_used']<cutoff
            if r['trend_available']:
                assert r['prior_available_used']<r['prior_information_cutoff']<cutoff
                old=inp.observations[r['prior_observation_id']]
                assert old['availability_date']==r['prior_available_used']
            if r['momentum_available']:
                assert r['momentum_start']<r['momentum_end']<cutoff
                listing=inp.universe[ticker]['listing_start']
                assert not listing or listing<=r['momentum_start']
                close(r['momentum_return'],r['momentum_end_price']/r['momentum_start_price']-1)
            rows.append(dict(region=region,date=date,information_cutoff=cutoff,ticker=ticker,
                             **{k:r[k] for k in FEATURE_FIELDS}))
    return rows


def compare_original(result,reference):
    s=result['summary']
    for key in ('total_return','CAGR','max_drawdown_monthly','total_cost_NAV_units','total_traded_NAV_units'):
        close(s[key],reference[key])
    old=read_csv(ROOT/'results_pillar2'/reference['run']/'monthly.csv')
    assert [{k:str(v) for k,v in r.items()} for r in result['monthly']]==old,'Baseline monthly ledger changed'


def main():
    OUT.mkdir(exist_ok=True)
    folders=('data','results_actual','results_us_restored','results_eu_restored','results_eu_interim',
             'results_research_corrected','results_long_history','results_pillar2')
    frozen={str(p.relative_to(ROOT)):digest(p) for folder in folders for p in (ROOT/folder).rglob('*')
            if p.is_file() and 'recovery_experiments' not in p.parts and '__pycache__' not in p.parts}
    prior_runs={r['run'] for r in read_csv(OUT/'summary.csv')}
    events,_=read_research();lam,registry=build_lam()
    reference=read_csv(ROOT/'results_pillar2/summary.csv')
    results=[];lookup={};datasets={};checks=[];reproductions=[];feature_rows=[];exit_reviews=[]
    feature_coverage=[];coverage_rows=[]
    for case,(mode,timing,start,old_window) in CASES.items():
        for region in ('US','EU'):
            inp=RecoveryInputs(region,timing,mode,events,lam,registry)
            datasets[case,region]=inp
            control=None
            configurations=[('equal','base','single','equal')]
            configurations += [(variant,score,exit_mode,rule) for variant,(score,exit_mode) in VARIANTS.items()
                               for rule in ('q50','q75')]
            for variant,score,exit_mode,rule in configurations:
                inp.score_mode=score
                policy=None if rule=='equal' else RecoveryExitPolicy(exit_mode)
                result=run(inp,region,'recovery_'+case+'_'+variant,rule,COST[region],gate=True,
                           annual_lag=0,start=start,selection_policy=policy)
                assert result is not None
                s=result['summary'];s.update(case=case,variant=variant,definition=mode,timing=timing,
                                            score_mode=score,exit_mode=exit_mode)
                check=validate(result,inp)
                for h in result['holdings']:
                    if h['ticker']!='CASH':assert active_events(events,h['ticker'],h['date'],mode)
                dates=[m['date'] for m in result['monthly']]
                if rule=='equal':
                    control=result
                    for c in result['coverage']:
                        if active_events(events,c['ticker'],c['date'],mode):
                            from run_long_history import is_listed
                            if is_listed(inp,c['ticker'],c['date']):assert c['covered'],c
                    coverage_rows += [dict(case=case,region=region,**c) for c in result['coverage']]
                else:assert result['coverage']==control['coverage'],'Feature changed eligibility/control coverage'
                if variant in ('baseline','equal'):
                    old=next(r for r in reference if r['definition']==mode and r['region']==region
                             and r['timing']==timing and r['window']==old_window and r['rule']==rule)
                    compare_original(result,old)
                    reproductions.append(dict(case=case,region=region,rule=rule,status='PASS'))
                if policy:
                    exit_reviews += [dict(run=s['run'],case=case,region=region,variant=variant,rule=rule,**r)
                                     for r in policy.review_log]
                checks.append(check);results.append(result);lookup[case,region,variant,rule]=result
                # Scores/features and eligibility are stored once per case/region, not once per rule.
                for key in ('monthly','holdings','trades','events','selection_audit','recent_daily'):
                    path=OUT/s['run']/(key+'.csv')
                    if result[key]:write_csv(path,result[key])
                    elif path.exists():path.unlink()
            fr=validate_features(inp,region,dates)
            feature_rows += [dict(case=case,**r) for r in fr]
            feature_coverage.append(dict(case=case,region=region,company_months=len(fr),
                                         trend_missing=sum(not r['trend_available'] for r in fr),
                                         momentum_missing=sum(not r['momentum_available'] for r in fr)))
            print('Completed',case,region,flush=True)
    for region in ('US','EU'):
        a=lookup['direct_timing_source',region,'equal','equal']
        b=lookup['direct_timing_delayed',region,'equal','equal']
        assert a['monthly']==b['monthly'],'Financial timing moved equal-weight control'
    summary=[];comparison=[];years=[];stats=[];chronology=[]
    for result in results:
        s=result['summary'];case,region,variant,rule=(s[k] for k in ('case','region','variant','rule'))
        control=lookup[case,region,'equal','equal']
        baseline=control if rule=='equal' else lookup[case,region,'baseline',rule]
        bs=baseline['summary'];cs=control['summary']
        s.update(control_return=cs['total_return'],baseline_return=bs['total_return'],
                 delta_baseline_pp=100*(s['total_return']-bs['total_return']),
                 delta_control_pp=100*(s['total_return']-cs['total_return']),
                 delta_baseline_cagr_pp=100*(s['CAGR']-bs['CAGR']),
                 delta_baseline_drawdown_pp=100*(s['max_drawdown_monthly']-bs['max_drawdown_monthly']),
                 annualized_two_way_turnover=12*sum(m['Turnover'] for m in result['monthly'][1:])/len(result['monthly'][1:]),
                 score_exits=sum(e['event'].startswith('EXIT_BOTTOM_QUARTILE') for e in result['events']),
                 deferred_score_exits=sum(r.get('deferred_score_exits',0) for r in result['selection_audit']))
        summary.append(s);years+=year_returns(result)
        if rule!='equal':
            comparison.append({k:s[k] for k in ('run','case','region','variant','rule','start','total_return',
                              'CAGR','delta_baseline_pp','delta_control_pp','max_drawdown_monthly',
                              'delta_baseline_drawdown_pp','annualized_two_way_turnover','total_cost_NAV_units',
                              'score_exits','deferred_score_exits','max_monthly_stock_weight')})
            stats.append(dict(run=s['run'],case=case,region=region,variant=variant,rule=rule,
                              comparison='equal',**active_stats(result,control)))
            if variant!='baseline':stats.append(dict(run=s['run'],case=case,region=region,variant=variant,rule=rule,
                                                     comparison='baseline',**active_stats(result,baseline)))
        if case=='direct_main' and rule!='equal':chronology+=chronological_rows(result,baseline,control)
    main_results=[r for r in results if r['summary']['case']=='direct_main' and r['summary']['rule']!='equal']
    entries=first_entry_rows(main_results);recoveries=[]
    for result in main_results:
        s=result['summary']
        if s['variant']=='baseline':continue
        baseline=lookup['direct_main',s['region'],'baseline',s['rule']]
        recoveries+=recovery_exit_rows(baseline,result,datasets['direct_main',s['region']])
    recovery_summary=[]
    for region in ('US','EU'):
        for rule in ('q50','q75'):
            for variant in VARIANTS:
                if variant=='baseline':continue
                rows=[r for r in recoveries if r['region']==region and r['rule']==rule and r['variant']==variant]
                complete=[r for r in rows if r['status']=='complete']
                positive=[r for r in complete if r['six_month_stock_return']>0]
                nonpositive=[r for r in complete if r['six_month_stock_return']<=0]
                recovery_summary.append(dict(region=region,rule=rule,variant=variant,
                    baseline_score_exits=len(rows),complete_horizons=len(complete),
                    censored_horizons=sum(r['right_censored'] for r in rows),positive_recoveries=len(positive),
                    positive_with_more_exposure=sum(r['variant_months_exposed']>r['baseline_months_exposed'] for r in positive),
                    positive_with_less_exposure=sum(r['variant_months_exposed']<r['baseline_months_exposed'] for r in positive),
                    nonpositive_horizons=len(nonpositive),
                    nonpositive_with_more_exposure=sum(r['variant_months_exposed']>r['baseline_months_exposed'] for r in nonpositive)))
    decision=[]
    for variant in VARIANTS:
        if variant=='baseline':continue
        values={(r['region'],r['rule']):r for r in comparison if r['case']=='direct_main' and r['variant']==variant}
        screen=(all(values['US',rule]['delta_baseline_pp']>0 for rule in ('q50','q75'))
                and all(values['EU',rule]['delta_baseline_pp']>=0 for rule in ('q50','q75')))
        decision.append(dict(variant=variant,both_us_improve_no_eu_return_loss=screen,
                             worst_drawdown_change_pp=min(r['delta_baseline_drawdown_pp'] for r in values.values()),
                             **{region+'_'+rule+'_delta_pp':values[region,rule]['delta_baseline_pp']
                                for region in ('US','EU') for rule in ('q50','q75')}))
    for name,rows in dict(summary=summary,comparisons=comparison,year_returns=years,active_statistics=stats,
                          chronological_results=chronology,first_entries=entries,recovery_exit_diagnostics=recoveries,
                          signal_features=feature_rows,feature_coverage=feature_coverage,exit_reviews=exit_reviews,
                          eligibility=coverage_rows,decision_screen=decision,recovery_summary=recovery_summary).items():
        write_csv(OUT/(name+'.csv'),rows)
    import shutil
    for name in prior_runs-{s['run'] for s in summary}:
        p=OUT/name
        assert p.parent==OUT and name.startswith(('US_','EU_'))
        if p.is_dir():shutil.rmtree(p)
    for p,h in frozen.items():assert digest(ROOT/p)==h,('Prior snapshot changed',p)
    validation=dict(status='PASS',python_version=platform.python_version(),runs=len(results),variants=list(VARIANTS),checks=checks,
                    baseline_reproductions=reproductions,controls_identical_across_variants=True,
                    timing_controls_identical=True,preserved_files=len(frozen))
    save(OUT/'validation.json',validation)
    save(OUT/'preserved_manifest.json',[dict(path=p,sha256=h) for p,h in sorted(frozen.items())])
    inputs=[ROOT/p for p in ('backtest.py','recovery_rules.py','recovery_diagnostics.py','run_recovery_experiments.py',
             'run_pillar2.py','run_long_history.py','run_research_corrections.py','RECOVERY_EXPERIMENT_METHOD.md',
             'test_selection_hook.py','test_recovery_rules.py','test_recovery_exit_policy.py','test_recovery_diagnostics.py',
             'audit_recovery_experiments.py')]
    inputs += [p for p in (DATA/'recovery_experiments').rglob('*') if p.is_file()]
    save(OUT/'input_manifest.json',[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in sorted(inputs)])
    make_report(summary,decision,feature_coverage,validation,entries,chronology,exit_reviews,recovery_summary)
    print('PASS: fixed-grid scoring and exit experiments, controls, cutoffs and preserved histories',flush=True)


def make_report(summary,decision,features,validation,entries,chronology,exit_reviews,recovery_summary):
    bykey={(s['case'],s['region'],s['variant'],s['rule']):s for s in summary}
    lines=['# Scoring and exit-rule experiments','',
           '[Fixed experiment definitions](../RECOVERY_EXPERIMENT_METHOD.md). Run `python3 run_recovery_experiments.py`. '
           'The existing strategy remains the default. All eight alternatives and the baseline are disclosed; no parameters were optimized after seeing these runs.','',
           f"**{sum(r['both_us_improve_no_eu_return_loss'] for r in decision)} of the eight alternatives passes the full-window four-return screen.** "
           'Changing the score has substantially larger effects than slowing exits alone. Fundamental improvement and price momentum '
           'bring several US entries forward, but their effects on European returns differ. These are findings on already-seen history, not a validated replacement strategy.','',
           'The universe uses the broad [any prior public support screen](../results_pillar2/REPORT.md), '
           'with named direct/subsidiary support for the main case. It does not replicate the article’s narrower '
           'Pillar 2 programme streams or basket weights. The candidate list remains retrospective.','',
           'The trend score combines the existing score with a rank of improvement in operating return and cash quality, '
           '50/50. The momentum score combines the existing score with trailing price momentum, also 50/50. '
           'Confirmation waits for two consecutive bad quarterly reviews before a score exit. '
           'All variants retain mandatory eligibility and capacity exits.','',
           '## Full direct-support history: 30 June 2019–2 November 2026','',
           'Returns include modeled costs. US in USD; EU in EUR. Equal-weight membership and NAV are unchanged by scoring/exit variants.','',
           '| Variant | US Q50 | US Q75 | EU Q50 | EU Q75 |','|---|---:|---:|---:|---:|']
    for variant in VARIANTS:
        values=[bykey['direct_main',region,variant,rule]['total_return'] for region in ('US','EU') for rule in ('q50','q75')]
        lines.append(f"| {variant} | "+' | '.join(f'{x:.2%}' for x in values)+' |')
    lines+=['| Equal weight | '+' | '.join(f"{bykey['direct_main',region,'equal','equal']['total_return']:.2%}"
                                          for region in ('US','EU') for _ in range(2))+' |','',
            '## Changes versus the existing strategy','',
            '| Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ | Four-return screen | Worst drawdown change |',
            '|---|---:|---:|---:|---:|---|---:|']
    for r in decision:
        values=[r[region+'_'+rule+'_delta_pp'] for region in ('US','EU') for rule in ('q50','q75')]
        lines.append(f"| {r['variant']} | "+' | '.join(f'{x:+.2f}pp' for x in values)+
                     f" | {'Pass' if r['both_us_improve_no_eu_return_loss'] else 'Fail'} | {r['worst_drawdown_change_pp']:+.2f}pp |")
    lines+=['','The screen requires both US returns to improve and neither EU return to decline. '
            'It does not establish a robust improvement or eliminate risk/cost tradeoffs. A negative drawdown change means a worse maximum monthly drawdown. '
            '`no_score_exit` remains a diagnostic, with capacity and eligibility exits still enforced.','',
            'The fundamental-trend score is the clearest compromise in these runs: both US returns improve substantially, '
            'EU Q50 improves slightly, and EU Q75 declines. Price momentum raises both US returns above their equal-weight control, '
            'but lowers both EU returns relative to their existing strategies. The two-quarter exit by itself has small, mixed '
            'full-window effects; removing score exits hurts EU Q75 materially. '
            f"The recovery-grace condition triggers {sum(r['grace'] for r in exit_reviews if r['variant']=='recovery_grace')} times "
            'across the tested cases and therefore does not change these portfolios. Its effectiveness is untested by these outcomes.','',
            '## Risk and trading tradeoffs','',
            'Each cell is annualized return / maximum monthly drawdown / annualized two-way turnover. '
            'Turnover counts purchases plus sales; costs remain 10bp per traded dollar in the US and 15bp in Europe.','',
            '| Variant | US Q50 | US Q75 | EU Q50 | EU Q75 |','|---|---:|---:|---:|---:|']
    for variant in ('baseline','trend','momentum','confirm_exit','trend_confirm'):
        rows=[bykey['direct_main',region,variant,rule] for region in ('US','EU') for rule in ('q50','q75')]
        lines.append(f'| {variant} | '+' | '.join(
            f"{r['CAGR']:.2%} / {r['max_drawdown_monthly']:.2%} / {r['annualized_two_way_turnover']:.2f}x" for r in rows)+' |')
    lines+=['','Momentum reduces both European full-window returns but also reduces both European maximum monthly drawdowns. '
            'Trend increases trading in both regions. The four-return screen therefore is not a complete risk-adjusted ranking.','',
            '## Timing and eligibility robustness','',
            'The [complete comparison](comparisons.csv) includes direct/source and delayed financial timing from September 2019, '
            'plus indirect-inclusive eligibility from June 2019. Source and delayed controls have identical monthly NAVs. '
            'The [chronological readout](chronological_results.csv) splits continuous portfolio paths into 2019–2022, '
            '2023–end and July 2020–end. These periods have already been observed and are not untouched holdouts.','',
            '| Case | Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ |',
            '|---|---|---:|---:|---:|---:|']
    for case in CASES:
        if case=='direct_main':continue
        for variant in VARIANTS:
            if variant=='baseline':continue
            values=[bykey[case,region,variant,rule]['delta_baseline_pp'] for region in ('US','EU') for rule in ('q50','q75')]
            lines.append(f'| {case} | {variant} | '+' | '.join(f'{v:+.2f}pp' for v in values)+' |')
    eu_source=bykey['direct_timing_source','EU','momentum','q75']
    eu_delay=bykey['direct_timing_delayed','EU','momentum','q75']
    lines+=['','Timing can change a relative verdict through the baseline as well as the alternative. '
            f"For EU Q75, momentum returns {eu_source['total_return']:.2%} under source timing and {eu_delay['total_return']:.2%} under delayed timing, "
            f"while their baselines return {eu_source['baseline_return']:.2%} and {eu_delay['baseline_return']:.2%}. "
            'A positive delayed comparison does not erase the loss relative to the main source-date baseline.','',
            '## Entries and missed recoveries','',
            'Examples of first US admissions (all candidates are retained in the linked audit):','',
            '| Score/exit variant | Rule | Bloom | First Solar | GE Vernova |',
            '|---|---|---|---|---|']
    for variant in ('baseline','trend','momentum','confirm_exit','trend_confirm'):
        for rule in ('q50','q75'):
            dates=[next(r['variant_first_entry'] for r in entries if r['region']=='US' and r['rule']==rule
                        and r['variant']==variant and r['ticker']==ticker) for ticker in ('BE','FSLR','GEV')]
            lines.append(f"| {variant} | {rule} | "+' | '.join(d or 'Never held' for d in dates)+' |')
    lines+=['','Earlier first admission does not imply uninterrupted exposure to every later rally. '
            'For example, two-quarter confirmation delays Intel’s March 2023 exit to June 2023, '
            'but does not solve every missed recovery. Capacity removals can still occur under every exit variant.','',
            '[Every stock’s first-entry changes](first_entries.csv) includes earlier, later, new and missed entries. '
            '[Six-month outcomes after every baseline score exit](recovery_exit_diagnostics.csv) show subsequent baseline/variant exposure, '
            'with incomplete horizons right-censored. [Recovery counts](recovery_summary.csv) report both positive and nonpositive outcomes, '
            'including extra exposure to subsequent losses. These forward returns are hindsight diagnostics only; they do not enter any signal. '
            '[Exit review ledger](exit_reviews.csv) distinguishes attempted deferrals, actual retained positions, score exits and capacity removal.','',
            '| US rule | Variant | Positive six-month outcomes with more exposure | Nonpositive outcomes with more exposure |',
            '|---|---|---:|---:|']
    for rule in ('q50','q75'):
        for variant in ('trend','confirm_exit'):
            r=next(r for r in recovery_summary if r['region']=='US' and r['rule']==rule and r['variant']==variant)
            lines.append(f"| {rule} | {variant} | {r['positive_with_more_exposure']} / {r['positive_recoveries']} | "
                         f"{r['nonpositive_with_more_exposure']} / {r['nonpositive_horizons']} |")
    lines+=['','These are outcomes after baseline score exits, with extra exposure measured by the number of subsequent monthly intervals held. '
            'Q50 and Q75 events can overlap and are not independent observations. Trend’s large US gains do not demonstrate '
            'better retention through the previously missed recoveries: it adds exposure to none of the positive outcomes above. '
            'Confirmation retains some recoveries, but also some subsequent losses.','',
            '## Chronological sensitivity for the main scoring alternatives','',
            'Changes versus the matching baseline over each continuous-position subperiod. These windows were fixed in advance of the variant runs; '
            'the July 2020 boundary follows the independently audited fundamental-feature coverage. Positions are not restarted at a boundary.','',
            '| Period | Variant | US Q50 Δ | US Q75 Δ | EU Q50 Δ | EU Q75 Δ |','|---|---|---:|---:|---:|---:|']
    for period in ('early','late','common_trend_coverage'):
        for variant in ('trend','momentum','trend_confirm'):
            values=[next(r['delta_vs_baseline_pp'] for r in chronology if r['period']==period and r['variant']==variant
                         and r['region']==region and r['rule']==rule) for region in ('US','EU') for rule in ('q50','q75')]
            lines.append(f'| {period} | {variant} | '+' | '.join(f'{v:+.2f}pp' for v in values)+' |')
    lines+=['','Fundamental trend improves all four returns after July 2020 and in the later 2023–2026 slice, '
            'while its EU Q75 full-history return is lower. This identifies sensitivity to the early period and feature activation; '
            'it does not establish that missing early inputs are the sole cause. Under delayed financial availability, '
            'the direct EU Q50 trend result is slightly below its delayed baseline.','',
            '## Feature coverage','',
            'Missing features retain the baseline score and never remove a stock. Early European fundamental-trend coverage is weaker than US coverage. '
            'The July 2020 boundary marks improved coverage for established names; IPO-related missingness remains, '
            'and continuous portfolio paths retain earlier position effects. This is not identical feature coverage or a fresh-start experiment. '
            'The raw [signal ledger](signal_features.csv) '
            'contains each current/prior observation, cutoff, price endpoint, factor and missing-feature reason.','',
            '| Case | Region | Company-months | Missing fundamental trend | Missing momentum |',
            '|---|---|---:|---:|---:|']
    for r in features:lines.append(f"| {r['case']} | {r['region']} | {r['company_months']} | {r['trend_missing']} | {r['momentum_missing']} |")
    lines+=['','## Validation and limits','',
            f"{validation['runs']} runs, {len(validation['baseline_reproductions'])} exact monthly baseline/control reproductions, "
            f"and {validation['preserved_files']} prior input/result files preserved byte-for-byte. "
            'Coverage, source dates, price endpoints, IPO history, costs, holdings and NAVs are checked. '
            'Selection state advances only on scheduled reviews; policy/data/delisting restrictions remain mandatory.','',
            'The candidate universe and adjusted-price histories retain their earlier retrospective-data limitations. '
            'Testing several informed alternatives on already-seen history creates selection risk even without a parameter sweep. '
            'The fixed method is committed alongside its outputs, not independently preregistered. '
            'Monthly drawdown omits intramonth losses; the historical timing tests are sensitivities, not proof of future performance.','',
            f"Generated with Python {validation['python_version']}. Hashes identify the committed snapshot; "
            'other Python/platform combinations may change the last floating-point digits of ledger text without a meaningful return change.','',
            '[Full summary and risk/cost metrics](summary.csv) · [Monthly active-return uncertainty](active_statistics.csv) · '
            '[Year returns](year_returns.csv) · [Validation](validation.json) · [Input hashes](input_manifest.json) · '
            '[Independent computation audit](independent_audit.json). Reproduce the latter with '
            '`python3 audit_recovery_experiments.py`.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
