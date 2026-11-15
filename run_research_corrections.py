#!/usr/bin/env python3
"""Reproduce coverage/timing corrections and predeclared concentration diagnostics.

Standard library only. Frozen inputs, prices and released results are never edited.
"""
import copy
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from collections import defaultdict
from decimal import Decimal

from backtest import Inputs, read_csv, run
from prepare_data import ROOT, DATA

AREA = DATA / 'research_corrections'
OUT = ROOT / 'results_research_corrected'
FIELDS = ('operating_income', 'net_income', 'operating_cash_flow',
          'total_assets', 'current_liabilities')
FLOWS = FIELDS[:3]
RULES = ('q75', 'q50', 'equal')
START = {'US': '2022-09-30', 'EU': '2021-09-30'}
COST = {'US': 10, 'EU': 15}
RESTORED = {'US': {'BE', 'ETN', 'FSLR', 'GEV', 'PLUG', 'TSM'},
            'EU': {'ALFEN.AS', 'AMS.SW', 'ENR.DE', 'NEL.OL', 'ORSTED.CO', 'SAF.PA', 'VWS.CO'}}


def load(path):
    return json.loads((ROOT / path).read_text())


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8), (a, b)


def build_lam():
    raw = load('data/research_corrections/lam_sources.json')
    assert [r['period_end'] for r in raw] == ['2024-06-30', '2024-09-29', '2024-12-29', '2025-03-30']
    registry, rows, audit = {}, [], []
    annual = raw[0]
    for r in raw:
        assert r['period_end'] < r['publication_date'] == r['availability_date']
        sid = 'lam_source_' + r['period_end']
        registry[sid] = r
        components = [sid]
        flows = {}
        for f in FLOWS:
            col = r['evidence'][f]['column_values']
            if r['period_type'] == 'annual':
                close(r[f], col[3] / 1000)
                flows[f] = r[f]
            else:
                qi = r['fiscal_quarter']
                close(r['ytd'][f], col[0 if qi == 1 else 3] / 1000)
                close(r['prior_ytd'][f], col[2 if qi == 1 else 4] / 1000)
                a, b, c = (Decimal(str(x)) for x in (annual[f], r['ytd'][f], r['prior_ytd'][f]))
                flows[f] = float(a + b - c)
                audit.append(dict(period_end=r['period_end'], field=f, prior_annual=float(a),
                                  current_ytd=float(b), prior_ytd=float(c), ttm=flows[f]))
        for f in FIELDS[3:]:
            close(r[f], r['evidence'][f]['column_values'][0] / 1000)
        if r['period_type'] != 'annual':
            components.append('lam_source_2024-06-30')
        row = dict(ticker='LRCX', period_end=r['period_end'],
                   fiscal_label='FY2024' if r is annual else f"TTM fiscal Q{r['fiscal_quarter']} FY2025",
                   period_type='annual' if r is annual else 'trailing', panel='lam_original_release',
                   publication_date=r['publication_date'], availability_date=r['availability_date'],
                   availability_basis='Original GAAP release; latest publication of all components',
                   currency='USD', unit='million', **flows,
                   total_assets=r['total_assets'], current_liabilities=r['current_liabilities'],
                   prior_total_assets='', prior_current_liabilities='', source_class='recovered_primary',
                   income_source=r['source'], balance_source=r['source'], cashflow_source=r['source'],
                   component_ids='|'.join(components), observation_id='lam_input_' + r['period_end'])
        rows.append(row)
    save(AREA / 'lam_inputs.json', rows)
    save(AREA / 'lam_arithmetic.json', audit)
    return rows, registry


def source_date(r):
    return r.get('availability_date') or r.get('published') or r['publication_date']


def common_date(r):
    annual = r.get('period_type') == 'annual' or r.get('fiscal_quarter', 4) == 4
    if r.get('period_type') == 'trailing':
        annual = False
    floor = (dt.date.fromisoformat(r['period_end']) + dt.timedelta(days=180 if annual else 90)).isoformat()
    return max(source_date(r), floor)


class CorrectedInputs(Inputs):
    def __init__(self, region, frequency, stage, lam, lam_registry):
        super().__init__()
        self.stage, self.frequency, self.region = stage, frequency, region
        self.annual = read_csv(DATA / 'financials_actual_annual.csv')
        self.quarterly = read_csv(DATA / 'financials_actual_quarterly.csv')
        self.primary = []
        self.registry = {r['observation_id']: r for r in load('data/actual_dates/observations_normalized.json')}
        if frequency != 'reference':
            if region == 'US':
                restored = load('data/us_restoration/normalized_inputs.json')
                self.annual += restored['annual']
                if frequency == 'interim':
                    self.quarterly += restored['interim']
                self.registry.update(load('data/us_restoration/source_registry.json'))
            else:
                self.annual += load('data/eu_restoration/primary_inputs.json')
                if frequency == 'interim':
                    self.quarterly += load('data/eu_interim/trailing_inputs.json')
                self.registry.update(load('data/eu_interim/source_registry.json'))
        if stage != 'released' and region == 'US':
            old_keys = {(r['ticker'], r['period_end']) for r in self.annual + self.quarterly}
            assert all((r['ticker'], r['period_end']) not in old_keys for r in lam)
            self.annual += copy.deepcopy(lam[:1])
            self.quarterly += copy.deepcopy(lam[1:])
            self.registry.update(lam_registry)
        if stage in ('evidenced', 'common') and region == 'EU':
            fixes = {r['observation_id']: r for r in load('data/research_corrections/safran_date_corrections.json')}
            for r in self.annual:
                if r['observation_id'] not in fixes:
                    continue
                f = fixes[r['observation_id']]
                for name in FIELDS:
                    close(r[name], f['verified_values'][name])
                assert r['availability_date'] == f['old_availability_date']
                r['publication_date'] = r['availability_date'] = f['availability_date']
                r['availability_basis'] = 'Verified earlier original consolidated results attachment'
                for name in ('income_source', 'balance_source', 'cashflow_source'):
                    r[name] = f['source']
                # Registry keys identify released facts; this dated overlay is saved separately.
                self.registry[r['observation_id']] = copy.deepcopy(r)
        for r in self.annual + self.quarterly:
            r['evidenced_availability_date'] = r['availability_date']
            components = [self.registry[c] for c in r['component_ids'].split('|')]
            assert all(source_date(c) <= r['availability_date'] for c in components), r
            if stage == 'common':
                r['availability_date'] = max(common_date(r), *(common_date(c) for c in components))
                r['availability_basis'] = 'max(evidenced date, annual +180d / interim +90d) for input and every component'
        self.observations = {r['observation_id']: r for r in self.annual + self.quarterly}

    def available(self, record, annual_lag):
        return dt.date.fromisoformat(record['availability_date'])

    def signals(self, region, date, panel, gate=False, annual_lag=0):
        return super().signals(region, date, 'hybrid', False, 0)


def active_stats(strategy, control):
    a, b = strategy['monthly'][1:], control['monthly'][1:]
    assert [r['date'] for r in a] == [r['date'] for r in b]
    x = [r['PeriodReturn'] - c['PeriodReturn'] for r, c in zip(a, b)]
    n, mean, sd = len(x), statistics.mean(x), statistics.stdev(x)
    centered = [v - mean for v in x]
    # Bartlett kernel, fixed 3 monthly lags; covariance divisor n; finite-sample n/(n-1).
    lrv = sum(v*v for v in centered) / n
    for lag in range(1, 4):
        gamma = sum(centered[i]*centered[i-lag] for i in range(lag, n)) / n
        lrv += 2 * (1 - lag/4) * gamma
    hac_se = math.sqrt(max(0, lrv) / (n-1))
    return dict(months=n, mean_monthly_active_pp=100*mean, tracking_error_pct=100*sd*math.sqrt(12),
                t_iid=mean/(sd/math.sqrt(n)) if sd else None,
                t_newey_west_3=mean/hac_se if hac_se else None,
                hac_95_low_monthly_pp=100*(mean-1.96*hac_se),
                hac_95_high_monthly_pp=100*(mean+1.96*hac_se))


def verify(result, inputs):
    s = result['summary']
    assert s['start'] == START[s['region']] and s['latest_end'] == '2026-11-02'
    assert s['cost_bps'] == COST[s['region']]
    holdings, trades = defaultdict(list), defaultdict(list)
    for h in result['holdings']:
        holdings[h['date']].append(h)
    for t in result['trades']:
        trades[t['date']].append(t)
    for m in result['monthly']:
        hs, ts = holdings[m['date']], trades[m['date']]
        close(sum(h['weight'] for h in hs), 1)
        close(sum(h['value'] for h in hs), m['NAV'])
        close(m['PreTradeNAV']-m['Cost'], m['NAV'])
        close(sum(t['cost'] for t in ts), m['Cost'])
        close(sum(abs(t['trade_value']) for t in ts)*s['cost_bps']/10000, m['Cost'])
    for sc in result['scores']:
        r = inputs.observations[sc['observation_id']]
        assert r['availability_date'] == sc['available_used'] < sc['information_cutoff']
        age = (dt.date.fromisoformat(sc['date'])-dt.date.fromisoformat(r['period_end'])).days
        assert age <= (550 if r['period_type'] == 'annual' else 275)
        for cid in r['component_ids'].split('|'):
            c = inputs.registry[cid]
            date = common_date(c) if inputs.stage == 'common' else source_date(c)
            assert date < sc['information_cutoff']
        if sc['ticker'] == 'GEV':
            assert sc['date'] >= '2024-04-02'
    close(s['final_NAV']/100-1, s['total_return'])
    return dict(run=s['run'], result='PASS', months=len(result['monthly']), scores=len(result['scores']))


def execute(inputs, panel, rule):
    result = run(inputs, inputs.region, panel, rule, COST[inputs.region], annual_lag=0, start=START[inputs.region])
    result['summary'].update(information_timing_policy='common_180_90_components' if inputs.stage=='common' else 'evidenced_source_dates',
                             annual_minimum_delay_days=180 if inputs.stage=='common' else 0,
                             interim_minimum_delay_days=90 if inputs.stage=='common' else 0)
    return result


def attribution(result, inputs):
    """Additive NAV-unit P&L; initial NAV=100 makes one unit one return percentage point."""
    s = result['summary']
    end, anchor = s['latest_end'], s['monthly_end']
    terminal = {}
    for h in result['holdings']:
        if h['date'] == anchor and h['ticker'] != 'CASH':
            t = h['ticker']
            terminal[t] = h['value'] * inputs.daily_price(t, end)/inputs.daily_price(t, anchor)
    trade_values, costs = defaultdict(float), defaultdict(float)
    for t in result['trades']:
        trade_values[t['ticker']] += t['trade_value']
        costs[t['ticker']] += t['cost']
    rows = []
    for t in sorted(t for t,u in inputs.universe.items() if u['region']=='US'):
        hs = [h for h in result['holdings'] if h['ticker'] == t]
        pnl = terminal.get(t, 0)-trade_values[t]
        rows.append(dict(panel=s['panel'], rule=s['rule'], ticker=t, gross_pnl_pp=pnl,
                         costs_pp=costs[t], net_pnl_pp=pnl-costs[t],
                         first_held=min((h['date'] for h in hs), default=''),
                         months_held=len(hs), average_weight=sum(h['weight'] for h in hs)/len(result['monthly'])))
    close(sum(r['net_pnl_pp'] for r in rows), 100*s['total_return'])
    return rows


def frozen_files():
    result = {}
    for directory in ('data', 'results_actual', 'results_eu_restored', 'results_eu_interim', 'results_us_restored'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and 'research_corrections' not in p.parts and '__pycache__' not in p.parts:
                result[str(p.relative_to(ROOT))] = digest(p)
    for name in ('INPUT_MANIFEST.json', 'RESULT_MANIFEST.json'):
        for r in load(name):
            assert digest(ROOT/r['path']) == r['sha256'], r['path']
    return result


def timing_audit(inputs, panel):
    rows = []
    for r in inputs.annual + inputs.quarterly:
        if inputs.universe[r['ticker']]['region'] != inputs.region:
            continue
        period = dt.date.fromisoformat(r['period_end'])
        effective = r['availability_date']
        rows.append(dict(panel=panel, region=inputs.region, ticker=r['ticker'], observation_id=r['observation_id'],
                         group='restored' if r['ticker'] in RESTORED[inputs.region] else 'original',
                         period_type=r['period_type'], period_end=r['period_end'],
                         evidenced_availability=r['evidenced_availability_date'], effective_availability=effective,
                         source_lag_days=(dt.date.fromisoformat(r['evidenced_availability_date'])-period).days,
                         effective_lag_days=(dt.date.fromisoformat(effective)-period).days,
                         later_than_input_floor=effective > (period+dt.timedelta(days=180 if r['period_type']=='annual' else 90)).isoformat(),
                         source=r['income_source'], component_ids=r['component_ids']))
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    frozen = frozen_files()
    lam, lam_registry = build_lam()
    results, inputs_map, checks, timing = {}, {}, [], []
    baselines = {'US': read_csv(ROOT/'results_us_restored/summary.csv'),
                 'EU': read_csv(ROOT/'results_eu_interim/summary.csv')}
    baseline_count = 0
    for region in ('US', 'EU'):
        for frequency in (('reference', 'annual', 'interim') if region == 'US' else ('annual', 'interim')):
            stages = ('released', 'lam', 'common') if region == 'US' else ('released', 'evidenced', 'common')
            for stage in stages:
                panel = f'{frequency}_{stage}'
                inp = CorrectedInputs(region, frequency, stage, lam, lam_registry)
                inputs_map[region, panel] = inp
                timing.extend(timing_audit(inp, panel))
                for rule in RULES:
                    result = execute(inp, panel, rule)
                    checks.append(verify(result, inp))
                    if stage == 'released':
                        old_panel = ({'reference': 'reference_expanded', 'annual': 'restored_annual',
                                      'interim': 'restored_interim'} if region == 'US' else
                                     {'annual': 'annual_restoration_reference', 'interim': 'restored_interim'})[frequency]
                        old = next(r for r in baselines[region] if r['panel'] == old_panel and r['rule'] == rule)
                        for field in ('total_return', 'final_NAV', 'total_cost_NAV_units', 'max_drawdown_monthly'):
                            close(result['summary'][field], old[field])
                        baseline_count += 1
                    results[region, panel, rule] = result
                    if stage != 'released':
                        for kind, rows in result.items():
                            if kind != 'summary':
                                write_csv(OUT/result['summary']['run']/(kind+'.csv'), rows)
                if stage != 'released':
                    save(AREA/f'{region}_{panel}_inputs.json', [r for r in inp.annual+inp.quarterly
                                                              if inp.universe[r['ticker']]['region']==region])
                print('Validated', region, panel, flush=True)
    summary, stats, pnl = [], [], []
    for (region, panel, rule), result in results.items():
        s = dict(result['summary'])
        control = results[region, panel, 'equal']
        s['matched_control_return'] = control['summary']['total_return']
        s['selection_difference_pp'] = 100*(s['total_return']-s['matched_control_return'])
        summary.append(s)
        if rule != 'equal':
            stats.append(dict(region=region, panel=panel, rule=rule, **active_stats(result, control)))
        if region == 'US':
            pnl.extend(attribution(result, inputs_map[region, panel]))
    write_csv(OUT/'summary.csv', summary)
    write_csv(OUT/'active_statistics.csv', stats)
    write_csv(OUT/'us_attribution.csv', pnl)
    write_csv(OUT/'timing_audit.csv', timing)
    lag_summary = []
    for key in sorted({(r['region'], r['panel'], r['group']) for r in timing}):
        rs = [r for r in timing if (r['region'],r['panel'],r['group']) == key and r['period_type']=='annual']
        if rs:
            lag_summary.append(dict(region=key[0], panel=key[1], group=key[2], annual_rows=len(rs),
                                    median_source_lag=statistics.median(r['source_lag_days'] for r in rs),
                                    median_effective_lag=statistics.median(r['effective_lag_days'] for r in rs),
                                    rows_later_than_180=sum(r['later_than_input_floor'] for r in rs)))
    write_csv(OUT/'annual_lag_summary.csv', lag_summary)
    lam_months = []
    for (region, panel, rule), result in results.items():
        if region != 'US':
            continue
        scores = {r['date']: r for r in result['scores'] if r['ticker']=='LRCX'}
        hs = {r['date']: r for r in result['holdings'] if r['ticker']=='LRCX'}
        for r in result['coverage']:
            if r['ticker']=='LRCX':
                lam_months.append(dict(panel=panel, rule=rule, date=r['date'], covered=r['covered'],
                                       held=r['date'] in hs, reason=r['reason'],
                                       period=scores.get(r['date'],{}).get('report_period','')))
                if inputs_map[region,panel].stage == 'lam' or (inputs_map[region,panel].stage == 'common' and '2025-01-31' <= r['date'] <= '2025-09-30'):
                    assert r['covered'], ('Lam gap remains', panel, r)
        if inputs_map[region,panel].stage == 'lam':
            assert not any(r['ticker']=='LRCX' and r['event']=='EXIT_COVERAGE_OR_ELIGIBILITY' for r in result['events'])
    write_csv(OUT/'lam_monthly_coverage_and_holdings.csv', lam_months)
    loo, loo_monthly = [], []
    for panel in ('annual_released','interim_released','annual_lam','interim_lam','annual_common','interim_common'):
        inp = inputs_map['US',panel]
        candidates = sorted(t for t,u in inp.universe.items() if u['region']=='US')
        assert len(candidates)==16
        for ticker in candidates:
            reduced = copy.copy(inp)
            reduced.universe = {t:u for t,u in inp.universe.items() if t != ticker}
            reruns = {rule: execute(reduced, panel+'_without_'+ticker, rule) for rule in RULES}
            for rule, result in reruns.items():
                assert not any(r['ticker']==ticker for r in result['scores']+result['holdings'])
                checks.append(verify(result, reduced))
                for m in result['monthly']:
                    loo_monthly.append(dict(panel=panel, omitted=ticker, rule=rule, date=m['date'],
                                            NAV=m['NAV'], PeriodReturn=m['PeriodReturn'], InitialDeployment=m['InitialDeployment']))
            for scope in ('control_only','whole_universe'):
                for rule in RULES[:2]:
                    strategy = results['US',panel,rule] if scope=='control_only' else reruns[rule]
                    control = reruns['equal']
                    loo.append(dict(panel=panel, omitted=ticker, scope=scope, rule=rule,
                                    strategy_return_pct=100*strategy['summary']['total_return'],
                                    control_return_pct=100*control['summary']['total_return'],
                                    difference_pp=100*(strategy['summary']['total_return']-control['summary']['total_return']),
                                    **active_stats(strategy,control)))
        print('Validated all 16 leave-one-out cases:', panel, flush=True)
    write_csv(OUT/'us_leave_one_out.csv', loo)
    write_csv(OUT/'us_leave_one_out_monthly.csv', loo_monthly)
    for path, sha in frozen.items():
        assert digest(ROOT/path)==sha, ('Released file modified',path)
    save(OUT/'preserved_file_manifest.json', [dict(path=p,sha256=h) for p,h in sorted(frozen.items())])
    validation = dict(released_runs_reproduced=baseline_count, corrected_lam_sources=4,
                      lam_ttm_arithmetic_fields=9, safran_annual_dates_corrected=5,
                      safran_financial_values_matched=25, lam_covered_all_source_date_months=True,
                      lam_2025_gap_closed_including_common_timing=True,
                      preserved_files=len(frozen), leave_one_out_runs=6*16*3,
                      leave_one_out_comparisons=len(loo), checks=checks)
    save(OUT/'validation.json', validation)
    report(summary,stats,pnl,loo,lag_summary,lam_months,validation,inputs_map)
    reproducibility = [ROOT/'backtest.py', ROOT/'prepare_data.py', ROOT/'run_research_corrections.py', ROOT/'test_research_corrections.py',
                       ROOT/'RESEARCH_CORRECTIONS_METHOD.md', *sorted(AREA.glob('*.json'))]
    save(OUT/'input_manifest.json', [dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in reproducibility])
    print('PASS: corrected runs, source timing, coverage, accounting and all sensitivities',flush=True)


def report(summary,stats,pnl,loo,lags,lam_months,validation,inputs_map):
    lines = ['# Coverage, timing and concentration corrections', '',
             'Run `python3 run_research_corrections.py`. Method: [predeclared corrections](../RESEARCH_CORRECTIONS_METHOD.md).', '',
             'The main candidate universe retains Bloom Energy. Corrected source-date runs and a common timing policy are both shown; neither is selected for its performance. These are historical simulations through 2 November 2026, not evidence of a persistent selection advantage.', '',
             '## Results bridge', '',
             'Annual/interim labels describe the restored names. The original names retain their original annual and interim inputs in every row. Returns include US 10bp / EU 15bp trading costs. US starts 30 September 2022; EU starts 30 September 2021. Prices, FX, scoring, quarterly entry/exit reviews and monthly reweighting are unchanged.', '',
             '| Region | Restored data / correction | Q75 | Q50 | Equal weight |',
             '|---|---|---:|---:|---:|']
    for region,panel in dict.fromkeys((s['region'],s['panel']) for s in summary):
        ss={s['rule']:s for s in summary if s['region']==region and s['panel']==panel}
        lines.append(f"| {region} | {panel} | " + ' | '.join(f"{100*ss[r]['total_return']:.2f}%" for r in RULES) + ' |')
    lines += ['', '`released` exactly reproduces the old snapshot; `lam` adds the four real Lam observations; `evidenced` corrects Safran annual dates; `common` includes these repairs and applies the same timing floor to every company and every source component.', '',
              '## Lam Research: repair the missing facts', '',
              'Added the original GAAP FY2024 release and FY2025 Q1–Q3 releases. TTM flows use FY2024 + current fiscal YTD − prior fiscal YTD; quarter-end balance sheets supply capital denominators. No expired filing is carried forward and no freshness threshold is relaxed.', '',
              '[Source facts and original release URLs](../data/research_corrections/lam_sources.json) · [TTM arithmetic](../data/research_corrections/lam_arithmetic.json) · [monthly coverage and holdings](lam_monthly_coverage_and_holdings.csv).', '']
    for rule in RULES:
        rs=[r for r in lam_months if r['panel']=='reference_released' and r['rule']==rule]
        gap=[r['date'] for r in rs if not r['covered']]
        absent=[r['date'] for r in rs if '2025-01-31'<=r['date']<'2025-09-30' and not r['held']]
        lines.append(f"- Released {rule}: {len(gap)} uncovered month-end observations ({', '.join(gap)}); {len(absent)} month-end holdings without Lam from January through August 2025. September 30 is the re-entry date, not a ninth absent month.")
    lines += ['', 'Lam has usable inputs at every monthly observation in the repaired source-date runs, with zero coverage exits. Score-based exits remain possible. The common-delay scenario closes the 2025 gap too, but has two older coverage gaps (December 2022 and December 2023): its artificial delay plus the unchanged first-of-month cutoff/freshness limit makes older reports expire before replacements become usable. These are separate timing-sensitivity effects, not missing FY2024/25 observations. The user-provided carry-forward figures are a different counterfactual; the corrected runs use newly recovered financial facts.', '',
              '## Publication timing', '',
              'Safran FY2020–24 now uses the original consolidated results attachments on 25 February 2021, 24 February 2022, 17 February 2023, 15 February 2024 and 14 February 2025. All 25 financial values match the original-year annual-report values already modeled; FY2025 already used results day. [Date/source evidence](../data/research_corrections/safran_date_corrections.json).', '',
              'For broader comparability, `common` uses max(evidenced availability, period end +180 days for annual / +90 days for interim), including every component of a TTM input. Both original and restored names follow this rule. A genuinely later source remains later. This conservative scenario is not an estimate of the true earliest information date.', '',
              'Other SEC/annual-report dates remain conservative evidence dates where earlier complete statements have not been verified. Safran interim dates also remain at their captured report dates. The source-date runs therefore still contain residual differences in source timing; use the common-policy rows to assess that sensitivity. This change does not certify an exhaustive earliest-release archive.', '',
              '| Region / panel | Group | Annual observations | Median source lag | Median effective lag | Later than 180d |',
              '|---|---|---:|---:|---:|---:|']
    for r in lags:
        if r['panel'] in ('interim_released','interim_common'):
            lines.append(f"| {r['region']} / {r['panel']} | {r['group']} | {r['annual_rows']} | {r['median_source_lag']:g}d | {r['median_effective_lag']:g}d | {r['rows_later_than_180']} |")
    lines += ['', 'Lag summaries include all annual input rows supplied to each panel, including pre-start history; they are not restricted to filings ultimately selected. The one annual exception beyond 180 days is GE Vernova FY2022, first captured in its March 2024 pre-listing registration statement. Its real filing date and April 2024 listing restriction are retained. [Every input and component ID](timing_audit.csv) and [annual lag summary](annual_lag_summary.csv) expose the sample and exceptions.', '',
              '## Bloom and concentration', '',
              'Removing the realized winner is an ex-post diagnostic, not a repaired investable strategy. Two tests are kept separate: remove a company from the control only (the strategies stay fixed), or remove it from the full scoring universe and rerun every rule. Every one of the 16 US candidates is omitted in turn, including companies that were not the winner.', '',
              '| Panel | Omit Bloom from | Rule | Strategy | Control | Difference |',
              '|---|---|---|---:|---:|---:|']
    for r in loo:
        if r['omitted']=='BE':
            lines.append(f"| {r['panel']} | {r['scope']} | {r['rule']} | {r['strategy_return_pct']:.2f}% | {r['control_return_pct']:.2f}% | {r['difference_pp']:+.2f}pp |")
    inp=inputs_map['US','interim_lam']; anchor='2026-10-31'; end='2026-11-02'
    bloom_return=inp.price('BE',anchor,'US')/inp.price('BE',START['US'],'US')*inp.daily_price('BE',end)/inp.daily_price('BE',anchor)-1
    lines += ['', f"Bloom's frozen adjusted-price return across the US window is {100*bloom_return:.2f}%. Its contribution depends on when and how much each portfolio held, so it is not its stock return multiplied by a single initial weight.", '',
              '| Panel | Rule | First held | Months held | Mean weight | Bloom net contribution |',
              '|---|---|---|---:|---:|---:|']
    for r in pnl:
        if r['ticker']=='BE' and not r['panel'].startswith('reference'):
            lines.append(f"| {r['panel']} | {r['rule']} | {r['first_held'] or 'Never'} | {r['months_held']} | {100*r['average_weight']:.2f}% | {r['net_pnl_pp']:.2f}pp |")
    lines += ['', 'In the released interim panel, omitting Bloom from the full universe reproduces the reported +29.40pp / +48.00pp Q75/Q50 leads. With the strategies held fixed instead, omitting Bloom from the control gives +15.12pp / +7.49pp. The difference is caused by reranking and the ensuing changes to holdings. The diagnostic supports concentration sensitivity; it does not justify deleting Bloom from the main universe.', '',
              'Across the 16 control-only omissions, Bloom has the largest effect on the control in the released and repaired interim panels. Removing Micron also reverses Q75’s gap; only removing Bloom reverses Q50’s gap under these source-date panels. Thus “one stock” is a useful explanation of much of the US result, not a literal claim that no other constituent matters.', '',
              '[All leave-one-out results](us_leave_one_out.csv) · [monthly sensitivity NAVs](us_leave_one_out_monthly.csv) · [all-stock contribution accounting](us_attribution.csv). Contributions are final holding value minus net purchases minus that stock’s trading costs; they sum to the portfolio return on starting NAV 100. Mean weights are equally weighted month-end snapshots, including the initial deployment.', '',
              '## Uncertainty', '',
              'These statistics compare Q75/Q50 with their matched equal-weight control, not the ETF benchmark. They use complete monthly simple-return differences, exclude initial deployment and the partial final mark, and report both IID and Newey–West t-statistics (fixed three monthly lags, Bartlett weights, n/(n−1) finite-sample adjustment). Tracking error is annualized. Confidence intervals in the CSV use the large-sample 1.96 multiplier and are descriptive, not a multiple-testing correction.', '',
              '| Region / panel | Rule | Months | Mean active / month | Tracking error | IID t | NW(3) t |',
              '|---|---|---:|---:|---:|---:|---:|']
    for r in stats:
        if not r['panel'].startswith('reference'):
            lines.append(f"| {r['region']} / {r['panel']} | {r['rule']} | {r['months']} | {r['mean_monthly_active_pp']:+.3f}pp | {r['tracking_error_pct']:.2f}% | {r['t_iid']:+.2f} | {r['t_newey_west_3']:+.2f} |")
    lines += ['', 'A large cumulative return gap can coexist with a small monthly t-statistic. The short, concentrated, retrospectively examined sample cannot establish a stable stock-selection edge or infer that one scoring rule is generally inferior. Timing and constituent sensitivity are part of the result.', '',
              '## Validation and preservation', '',
              f"Reproduced {validation['released_runs_reproduced']} released runs; checked 4 Lam sources, 9 TTM flow calculations, 25 Safran value matches, every selected source cutoff, freshness, holdings/NAV/cost reconciliation, zero Lam coverage gaps under evidenced dates and closure of the 2025 gap under common timing, and {validation['leave_one_out_runs']} leave-one-out reruns. All {validation['preserved_files']} captured prior data/result files remained byte-for-byte unchanged.", '',
              'Run `python3 -m unittest test_research_corrections.py` for six regression tests covering the missing months, January release cutoff, independently calculated Lam TTM values, Safran March availability, component delays and the statistical formulas.', '',
              '[Validation](validation.json) · [input hashes](input_manifest.json) · [preserved snapshot hashes](preserved_file_manifest.json) · [full summary](summary.csv) · [active-return statistics](active_statistics.csv). The legacy engine argument `annual_lag_days=0` is retained in run names; the added `information_timing_policy` and annual/interim minimum-delay columns explicitly identify the common scenario’s effective delays.', '',
              'Direct retrieval of Safran PDFs returned HTTP403; issuer PDF text and dated archive links were verified through web retrieval. The evidence JSON records that limitation, rather than inventing a downloaded-PDF hash. Lam release downloads have SHA-256 hashes and compact table evidence.', '']
    (OUT/'REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
