#!/usr/bin/env python3
"""Post-result concentration diagnostics; never supply inputs to selection.

Remove each company before all ranks are calculated and rerun the baseline and
four existing score variants. These are sensitivity tests on already-seen data,
not new strategies, additive stock attribution, or independent observations.
"""
import copy

from backtest import read_csv, run
from prepare_data import ROOT
from recovery_rules import RecoveryInputs, RecoveryExitPolicy, VARIANTS
from run_long_history import COST, validate
from run_pillar2 import read_research, build_lam
from run_research_corrections import close, digest, save, write_csv

OUT = ROOT / 'results_recovery_experiments'
SCORE_VARIANTS = ('trend', 'momentum', 'trend_confirm', 'momentum_confirm')


def without_company(inputs, ticker):
    """Clear precomputed ranks as well as removing the universe member."""
    if ticker not in inputs.universe:
        raise ValueError('Unknown omitted company: ' + ticker)
    reduced = copy.copy(inputs)
    reduced.universe = {t: u for t, u in inputs.universe.items() if t != ticker}
    reduced.feature_cache = {}
    return reduced


def wealth_comparison(variant_nav, baseline_nav):
    """Percent relative wealth and percentage-point return gaps are different."""
    return dict(relative_wealth_pct=100 * (variant_nav / baseline_nav - 1),
                cumulative_return_gap_pp=variant_nav - baseline_nav)


def milestone_rows(result, baseline):
    s = result['summary']
    own = {m['date']: m['NAV'] for m in result['monthly']}
    base = {m['date']: m['NAV'] for m in baseline['monthly']}
    own[s['latest_end']] = s['final_NAV']
    base[s['latest_end']] = baseline['summary']['final_NAV']
    dates = [('year_end_2020', '2020-12-31'), ('may_2024', '2024-05-31'),
             ('june_2026', '2026-06-30'), ('full_endpoint', s['latest_end'])]
    if s['region'] == 'US':
        first = min((h['date'] for h in result['holdings'] if h['ticker'] == 'BE'), default='')
        if first:
            dates.append(('first_Bloom_entry', first))
    return [dict(region=s['region'], variant=s['variant'], rule=s['rule'], milestone=label,
                 date=date, variant_NAV=own[date], baseline_NAV=base[date],
                 **wealth_comparison(own[date], base[date])) for label, date in dates]


def realized_variants(summaries):
    """Compare actual monthly paths, holdings and trades across every case."""
    signatures = {}
    groups = sorted({(s['case'], s['region'], s['rule']) for s in summaries if s['rule'] != 'equal'})
    for variant in VARIANTS:
        signature = []
        for case, region, rule in groups:
            s = next(s for s in summaries if (s['case'], s['region'], s['rule'], s['variant'])
                     == (case, region, rule, variant))
            for name in ('monthly', 'holdings', 'trades'):
                signature.append(digest(OUT / s['run'] / (name + '.csv')))
        signatures[variant] = tuple(signature)
    duplicates = {}
    first = {}
    for variant, signature in signatures.items():
        if signature in first:
            duplicates[variant] = first[signature]
        else:
            first[signature] = variant
    return dict(specified_alternatives=len(VARIANTS)-1, distinct_portfolio_alternatives=len(first)-1,
                duplicate_of=duplicates, comparison_groups=len(groups))


def omission_summaries(rows):
    summaries = []
    for region in ('US', 'EU'):
        for variant in SCORE_VARIANTS:
            for rule in ('q50', 'q75'):
                group = [r for r in rows if (r['region'], r['variant'], r['rule']) == (region, variant, rule)]
                full = next(r for r in group if not r['omitted'])
                omitted = [r for r in group if r['omitted']]
                bloom = next((r for r in omitted if r['omitted'] == 'BE'), None)
                other = [r['delta_baseline_pp'] for r in omitted if r['omitted'] != 'BE']
                summaries.append(dict(region=region, variant=variant, rule=rule,
                    full_delta_pp=full['delta_baseline_pp'], omissions=len(omitted),
                    positive_omissions=sum(r['delta_baseline_pp'] > 0 for r in omitted),
                    minimum_delta_pp=min(r['delta_baseline_pp'] for r in omitted),
                    maximum_delta_pp=max(r['delta_baseline_pp'] for r in omitted),
                    without_Bloom_delta_pp=bloom['delta_baseline_pp'] if bloom else None,
                    other_omissions_minimum_pp=min(other), other_omissions_maximum_pp=max(other)))
    return summaries


def build_diagnostics():
    references = read_csv(OUT / 'summary.csv')
    events, _ = read_research()
    lam, registry = build_lam()
    rows, milestones = [], []
    runs = reproductions = 0
    for region in ('US', 'EU'):
        original = RecoveryInputs(region, 'source', 'direct', events, lam, registry)
        names = sorted(t for t, u in original.universe.items() if u['region'] == region)
        full_coverage = None
        for omitted in [''] + names:
            inputs = without_company(original, omitted) if omitted else original
            results = {}
            for variant in ('baseline',) + SCORE_VARIANTS:
                score, exit_mode = VARIANTS[variant]
                inputs.score_mode = score
                for rule in ('q50', 'q75'):
                    result = run(inputs, region, 'recovery_concentration', rule, COST[region],
                                 gate=True, annual_lag=0, start='2019-06-30',
                                 selection_policy=RecoveryExitPolicy(exit_mode))
                    assert result is not None
                    s = result['summary']; s['variant'] = variant
                    assert s['start'] == '2019-06-30'
                    validate(result, inputs)
                    assert not any(h['ticker'] == omitted for h in result['holdings'])
                    covered = {(c['date'], c['ticker']) for c in result['coverage'] if c['covered']}
                    if full_coverage is None:
                        full_coverage = covered
                    assert covered == {(d, t) for d, t in full_coverage if t != omitted}
                    results[variant, rule] = result
                    runs += 1
                    if not omitted:
                        reference = next(r for r in references if r['case'] == 'direct_main'
                                         and (r['region'], r['variant'], r['rule']) == (region, variant, rule))
                        close(s['total_return'], reference['total_return'])
                        old = read_csv(OUT / reference['run'] / 'monthly.csv')
                        assert [r['date'] for r in old] == [m['date'] for m in result['monthly']]
                        for a, b in zip(old, result['monthly']):
                            close(a['NAV'], b['NAV'])
                        reproductions += 1
            for variant in SCORE_VARIANTS:
                for rule in ('q50', 'q75'):
                    result, baseline = results[variant, rule], results['baseline', rule]
                    s, b = result['summary'], baseline['summary']
                    rows.append(dict(region=region, variant=variant, rule=rule, omitted=omitted,
                        total_return=s['total_return'], baseline_return=b['total_return'],
                        delta_baseline_pp=100 * (s['total_return'] - b['total_return']),
                        start=s['start'], end=s['latest_end']))
                    if not omitted:
                        milestones += milestone_rows(result, baseline)
            if omitted:
                print('Concentration diagnostic:', region, 'without', omitted, flush=True)
    summary = omission_summaries(rows)
    for name, values in (('score_omissions', rows), ('score_omission_summary', summary),
                         ('relative_wealth_milestones', milestones)):
        write_csv(OUT / (name + '.csv'), values)
    us = RecoveryInputs('US', 'source', 'direct', events, lam, registry)
    stock = dict(ticker='BE', start='2024-06-30', end='2026-06-30',
                 price_multiple=us.price('BE', '2026-06-30', 'US') / us.price('BE', '2024-06-30', 'US'))
    stats = read_csv(OUT / 'active_statistics.csv')
    statistical_family = [r for r in stats if r['case'] == 'direct_main' and r['comparison'] == 'baseline']
    validation = dict(status='PASS', sensitivity_runs=runs, main_monthly_reproductions=reproductions,
        main_case='direct_main', existing_variants=list(SCORE_VARIANTS),
        omitted_candidates=31, ranks_recomputed_after_omission=True, other_coverage_unchanged=True,
        baseline_comparisons_in_main_family=len(statistical_family), realized=realized_variants(references),
        Bloom_price_interval=stock,
        limitations=['Omission changes relative ranks, selections and weights; it is not additive attribution.',
                     'Omitted companies remain in the main portfolios and controls.',
                     'Dates and omissions were inspected after returns were observed; no holdout or parameter fitting.',
                     'We reuse the portfolio engine and input classes; these diagnostics are not an independent implementation.'],
        hashes=[dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in
                (ROOT/'analyze_recovery_robustness.py', ROOT/'recovery_rules.py', OUT/'summary.csv',
                 OUT/'active_statistics.csv', OUT/'input_manifest.json')])
    save(OUT / 'concentration_validation.json', validation)
    return summary, milestones, stats, validation


def report_lines(summary, milestones, stats, validation):
    lines = ['## Dependence on individual stocks', '',
        'These post-result checks remove one company from the entire candidate pool before reranking '
        'both the alternative and its baseline. The main portfolios keep every eligible company. '
        'Omission effects include changed ranks, selections and weights; they are not additive stock contributions.', '',
        '| Region | Existing variant | Rule | Full-pool gain over baseline | Without Bloom | Omission gains > 0 | Range across omissions |',
        '|---|---|---|---:|---:|---:|---:|']
    for r in summary:
        bloom = 'n/a' if r['without_Bloom_delta_pp'] is None else f"{r['without_Bloom_delta_pp']:+.2f}pp"
        lines.append(f"| {r['region']} | {r['variant']} | {r['rule'].upper()} | {r['full_delta_pp']:+.2f}pp | {bloom} | "
                     f"{r['positive_omissions']}/{r['omissions']} | {r['minimum_delta_pp']:+.2f} to {r['maximum_delta_pp']:+.2f}pp |")
    trends = [r for r in summary if r['region'] == 'US' and r['variant'] == 'trend']
    lines += ['', 'For the fundamental-improvement score, the US gain changes from '+
        ' / '.join(f"{r['full_delta_pp']:+.2f}pp" for r in trends)+' (Q50/Q75) to '+
        ' / '.join(f"{r['without_Bloom_delta_pp']:+.2f}pp" for r in trends)+
        ' without Bloom. Compare full-pool and omission results before interpreting a gain as broadly distributed. '
        'The gain ranges after every other US omission are '+
        ' / '.join(f"{r['other_omissions_minimum_pp']:+.2f} to {r['other_omissions_maximum_pp']:+.2f}pp" for r in trends)+'.', '',
        '[Every omission](score_omissions.csv) and [summary](score_omission_summary.csv) include both score variants '
        'and their existing two-review exit combinations. No stock is removed from the headline results.', '',
        '## When the relative gains appeared', '',
        '**Relative wealth** means variant NAV / baseline NAV − 1. It is a percentage, not the difference '
        'between cumulative returns in percentage points. These are continuous portfolio paths, not fresh restarts.', '',
        '| US variant | Rule | At December 2020 | At May 2024 | At the full endpoint |',
        '|---|---|---:|---:|---:|']
    for variant in SCORE_VARIANTS:
        for rule in ('q50', 'q75'):
            values = [next(r['relative_wealth_pct'] for r in milestones if
                (r['region'], r['variant'], r['rule'], r['milestone']) == ('US', variant, rule, name))
                for name in ('year_end_2020', 'may_2024', 'full_endpoint')]
            lines.append(f"| {variant} | {rule.upper()} | "+' | '.join(f'{v:+.2f}%' for v in values)+' |')
    entries = [r for r in milestones if r['region'] == 'US' and r['variant'] == 'trend'
               and r['milestone'] == 'first_Bloom_entry']
    lines += ['', 'At its first Bloom entry the trend portfolio was '+
        '; '.join(f"{r['relative_wealth_pct']:+.2f}% relative to baseline for {r['rule'].upper()} ({r['date']})" for r in entries)+
        f". Bloom’s adjusted USD price then rose {validation['Bloom_price_interval']['price_multiple']:.2f}x "
        'over June 2024–June 2026. This stock-price interval starts at Q50’s entry, not Q75’s later entry; '
        'it is not the portfolio’s realized return. The milestones distinguish early and later performance; '
        'none is a new validation period.', '',
        '[All milestone NAVs and both return measures](relative_wealth_milestones.csv).', '',
        '## Statistical uncertainty', '',
        'Each cell is the monthly active-return **IID t / Newey–West t** (three lags). '
        'Deployment costs and the terminal partial month are excluded from these monthly statistics. '
        'The baseline is the existing strategy using the same Q50/Q75 rule; equal weight is the unchanged control.', '',
        '| Region | Alternative | Q50 vs baseline | Q75 vs baseline | Q50 vs equal weight | Q75 vs equal weight |',
        '|---|---|---:|---:|---:|---:|']
    main = [r for r in stats if r['case'] == 'direct_main']
    for region in ('US', 'EU'):
        for variant in VARIANTS:
            if variant == 'baseline':
                continue
            cells = []
            for comparison in ('baseline', 'equal'):
                for rule in ('q50', 'q75'):
                    r = next(r for r in main if (r['region'], r['variant'], r['rule'], r['comparison'])
                             == (region, variant, rule, comparison))
                    cells.append(' / '.join(f'{float(r[k]):+.2f}' if r[k] not in ('', None) else 'n/a'
                                            for k in ('t_iid', 't_newey_west_3')))
            lines.append(f'| {region} | {variant} | '+' | '.join(cells)+' |')
    highest = max(float(r[k]) for r in main if r['region'] == 'US' and r['comparison'] == 'equal'
                  for k in ('t_iid', 't_newey_west_3') if r[k] not in ('', None))
    lines += ['', f"The largest US t-statistic against equal weight is {highest:.2f}. "
        f"The main case alone contains {validation['baseline_comparisons_in_main_family']} specified alternative-versus-baseline "
        'comparisons, before the additional timing, eligibility and omission analyses. These are unadjusted '
        'statistics on already-seen data. Some baseline comparisons exceed two; that does not establish '
        'a reliable advantage after selection or against equal weight. Duplicate portfolio paths '
        'supply no distinct performance evidence.', '',
        '[All statistics](active_statistics.csv) · [Diagnostic validation](concentration_validation.json).', '']
    return lines


def main():
    outputs = build_diagnostics()
    write_report(outputs)
    print('PASS: scoring omissions, relative-wealth milestones and uncertainty disclosures')


def write_report(outputs):
    (OUT/'CONCENTRATION.md').write_text('# Scoring concentration, timing and uncertainty\n\n'+'\n'.join(report_lines(*outputs)))


if __name__ == '__main__':
    main()
