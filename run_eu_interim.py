#!/usr/bin/env python3
"""Build auditable interim TTM inputs and compare against the annual restoration."""
import datetime as dt
import hashlib
import json
import math
from collections import defaultdict

from backtest import read_csv, run
from prepare_data import ROOT, DATA, write_csv
from run_eu_restoration import RestoredInputs, RESTORED, START, END, digest, verify
from snapshot_integrity import verify_frozen_entries

AREA = DATA / 'eu_interim'
OUT = ROOT / 'results_eu_interim'
FLOWS = ('operating_income', 'net_income', 'operating_cash_flow')
PANELS = ('annual_restoration_reference', 'restored_interim')


def identifier(prefix, obj):
    return prefix + hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:20]


def expected_periods():
    result = set()
    for t in RESTORED:
        if t in ('ALFEN.AS', 'SAF.PA'):
            result.update((t, f'{y}-06-30') for y in range(2021, 2027))
        elif t == 'ENR.DE':
            result.add((t, '2021-06-30'))
            for y in range(2022, 2027):
                result.update([(t, f'{y-1}-12-31'), (t, f'{y}-03-31'), (t, f'{y}-06-30')])
        else:
            result.update([(t, '2021-06-30'), (t, '2021-09-30')])
            for y in range(2022, 2026):
                result.update((t, f'{y}-{m}') for m in ('03-31', '06-30', '09-30'))
            result.update([(t, '2026-03-31'), (t, '2026-06-30')])
    return result


def build(annual, observations):
    by_year = {(r['ticker'], int(r['period_end'][:4])): r for r in annual}
    registry = {r['observation_id']: r for r in annual}
    rows, audit, exclusions = [], [], []
    seen = set()
    for raw in sorted(observations, key=lambda r: (r['ticker'], r['period_end'])):
        t, period = raw['ticker'], raw['period_end']
        assert t in RESTORED and raw['unit'] == 'million', raw
        assert raw['fiscal_quarter'] in (1, 2, 3), raw
        key = (t, period)
        assert key not in seen, ('Duplicate interim', key)
        seen.add(key)
        assert period < raw['publication_date'] <= raw['availability_date'], raw
        if raw['availability_date'] >= '2026-10-01':
            exclusions.append(dict(ticker=t, period_end=period, reason='Published after final information cutoff'))
            continue
        if raw.get('ttm_compatible') is not True:
            exclusions.append(dict(ticker=t, period_end=period, reason='Unresolved reporting-basis compatibility', notes=raw.get('notes', [])))
            continue
        prev = by_year.get((t, int(raw['fiscal_year']) - 1))
        if prev is None:
            exclusions.append(dict(ticker=t, period_end=period, reason='Prior annual not available'))
            continue
        assert prev['currency'] == raw['currency'], ('Currency mismatch', key)
        current_id = identifier('interim_source_', raw)
        registry[current_id] = dict(raw, observation_id=current_id)
        prior_id = prev['observation_id']
        prior = prev
        if raw.get('prior_annual'):
            override = dict(raw['prior_annual'])
            assert override['period_end'] == prev['period_end'], ('Wrong prior fiscal year', key)
            assert override.get('source', '').startswith('https://'), override
            assert override['period_end'] < override['publication_date'], override
            override.setdefault('availability_date', override['publication_date'])
            assert override['publication_date'] <= override['availability_date']
            override.update(ticker=t, currency=raw['currency'], unit='million')
            prior_id = identifier('interim_comparable_annual_', override)
            registry[prior_id] = dict(override, observation_id=prior_id)
            prior = override
        values, calculations = {}, []
        incomplete = False
        for f in FLOWS:
            if raw.get('reported_ttm', {}).get(f) is not None:
                value = float(raw['reported_ttm'][f])
                calculation = dict(field=f, method='issuer-reported TTM', value=value)
            else:
                a, b, c = prior.get(f), raw.get('ytd', {}).get(f), raw.get('prior_ytd', {}).get(f)
                if any(x is None for x in (a, b, c)):
                    incomplete = True
                    break
                a, b, c = float(a), float(b), float(c)
                value = a + b - c
                calculation = dict(field=f, method='prior annual + current YTD - comparative prior YTD',
                                   prior_annual=a, current_ytd=b, prior_ytd=c, value=value)
            assert math.isfinite(value), (key, f)
            values[f] = value
            calculations.append(calculation)
        if incomplete:
            exclusions.append(dict(ticker=t, period_end=period, reason='Missing complete comparable flows'))
            continue
        available = max(raw['availability_date'], prior['availability_date'])
        assert available < '2026-10-01', ('Later source component cannot enter frozen window', key)
        assets, liabilities = float(raw['total_assets']), float(raw['current_liabilities'])
        assert assets > liabilities > 0, (key, assets, liabilities)
        for field in ('income_source', 'balance_source', 'cashflow_source', 'date_source'):
            assert raw[field].startswith('https://'), (key, field)
        row = dict(ticker=t, period_end=period, fiscal_label=f"TTM through fiscal Q{raw['fiscal_quarter']} {raw['fiscal_year']}",
                   period_type='trailing', panel='eu_recovered_original_ttm', publication_date=raw['publication_date'],
                   availability_date=available, availability_basis='latest dated source component, observed comparable annual + YTD - prior YTD',
                   currency=raw['currency'], unit='million', **values, total_assets=assets, current_liabilities=liabilities,
                   prior_total_assets='', prior_current_liabilities='', income_source=raw['income_source'],
                   balance_source=raw['balance_source'], cashflow_source=raw['cashflow_source'],
                   source_class='recovered_primary_interim_ttm', component_ids='|'.join([current_id, prior_id]))
        row['observation_id'] = identifier('eu_ttm_', row)
        rows.append(row)
        audit.append(dict(observation_id=row['observation_id'], ticker=t, period_end=period, available=available,
                          current_source_id=current_id, prior_annual_source_id=prior_id, calculations=calculations,
                          comparable_annual_override=bool(raw.get('prior_annual')), notes=raw.get('notes', [])))
    for t, period in sorted(expected_periods() - seen):
        exclusions.append(dict(ticker=t, period_end=period, reason='Expected interim observation not recovered'))
    return rows, audit, exclusions, registry


class InterimInputs(RestoredInputs):
    def __init__(self, panel, annual, trailing):
        super().__init__('restored_primary', annual, annual)
        self.panel_name = panel
        if panel == 'restored_interim':
            self.quarterly += trailing
        self.observations = {r['observation_id']: r for r in self.annual + self.quarterly}


def validate_arithmetic(rows, audit, registry):
    by_id = {r['observation_id']: r for r in rows}
    for a in audit:
        r = by_id[a['observation_id']]
        current = registry[a['current_source_id']]
        previous = registry[a['prior_annual_source_id']]
        assert r['availability_date'] == max(current['availability_date'], previous['availability_date'])
        assert float(r['total_assets']) == float(current['total_assets'])
        assert float(r['current_liabilities']) == float(current['current_liabilities'])
        for f in FLOWS:
            value = (float(current['reported_ttm'][f]) if current.get('reported_ttm', {}).get(f) is not None
                     else float(previous[f]) + float(current['ytd'][f]) - float(current['prior_ytd'][f]))
            assert math.isclose(value, r[f], abs_tol=1e-9), (a, f)


def main():
    AREA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    frozen = {}
    for name in ('INPUT_MANIFEST.json', 'RESULT_MANIFEST.json', 'results_eu_restored/input_manifest.json'):
        frozen.update(verify_frozen_entries(ROOT, json.loads((ROOT / name).read_text())))
    for base in ('results_eu_restored', 'data/eu_restoration'):
        for p in (ROOT / base).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                frozen[str(p.relative_to(ROOT))] = digest(p)
    annual = json.loads((DATA / 'eu_restoration/primary_inputs.json').read_text())
    observations = []
    for path in sorted(AREA.glob('research_*_observations.json')):
        observations.extend(json.loads(path.read_text()))
    assert {r['ticker'] for r in observations} == RESTORED, 'Finish source recovery for all seven companies before running'
    trailing, audit, exclusions, registry = build(annual, observations)
    validate_arithmetic(trailing, audit, registry)
    for name, value in [('trailing_inputs', trailing), ('arithmetic_audit', audit), ('exclusions', exclusions), ('source_registry', registry)]:
        (AREA / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    write_csv(AREA / 'financials_interim.csv', trailing)
    results, checks = [], []
    for panel in PANELS:
        inputs = InterimInputs(panel, annual, trailing)
        for rule in ('q75', 'q50', 'equal'):
            result = run(inputs, 'EU', panel, rule, 15, annual_lag=0, start=START)
            checks.append(verify(result, inputs))
            for sc in result['scores']:
                if sc['source_panel'] == 'eu_recovered_original_ttm':
                    for component in sc['component_ids'].split('|'):
                        assert registry[component]['availability_date'] < sc['information_cutoff'], ('Future component', sc)
            results.append(result)
    previous = read_csv(ROOT / 'results_eu_restored/summary.csv')
    for result in results:
        s = result['summary']
        if s['panel'] == 'annual_restoration_reference':
            original = next(x for x in previous if x['panel'] == 'restored_primary' and x['rule'] == s['rule'])
            for k in ('total_return', 'final_NAV', 'CAGR', 'max_drawdown_monthly', 'total_cost_NAV_units'):
                assert math.isclose(s[k], float(original[k]), abs_tol=1e-8), ('Reference changed', k, s)
        for kind, rows in result.items():
            if kind != 'summary':
                write_csv(OUT / s['run'] / (kind + '.csv'), rows)
    controls = [r for r in results if r['summary']['rule'] == 'equal']
    assert controls[0]['coverage'] == controls[1]['coverage'], 'Unexpected eligibility change; investigate before interpretation'
    for a, b in zip(controls[0]['monthly'], controls[1]['monthly']):
        assert math.isclose(a['NAV'], b['NAV'], abs_tol=1e-8), 'Equal-weight control changed'
    summaries = [r['summary'] for r in results]
    for s in summaries:
        c = next(x for x in summaries if x['panel'] == s['panel'] and x['rule'] == 'equal')
        s['covered_universe_return'] = c['total_return']
        s['selection_return_difference_pp'] = 100 * (s['total_return'] - c['total_return'])
    write_csv(OUT / 'summary.csv', summaries)
    usage = []
    scores = controls[1]['scores']
    for t in sorted(RESTORED):
        rs = [r for r in trailing if r['ticker'] == t]
        ss = [r for r in scores if r['ticker'] == t]
        usage.append(dict(ticker=t, expected_interims=sum(x[0] == t for x in expected_periods()),
                          recovered_interims=sum(x['ticker'] == t for x in observations), usable_ttm=len(rs),
                          covered_months=len(ss), ttm_score_months=sum(r['period_type'] == 'trailing' for r in ss),
                          annual_score_months=sum(r['period_type'] == 'annual' for r in ss),
                          latest_interim=max((r['period_end'] for r in rs), default=''),
                          earliest_available=min((r['availability_date'] for r in rs), default='')))
    write_csv(OUT / 'interim_coverage.csv', usage)
    for path, sha in frozen.items():
        assert digest(ROOT / path) == sha, ('Prior file modified', path)
    validation = dict(runs=checks, original_files_preserved=len(frozen), annual_reference_runs_reproduced=3,
                      expected_interims=len(expected_periods()), recovered_interims=len(observations),
                      usable_ttm=len(trailing), excluded=len(exclusions),
                      arithmetic_fields_checked=len(audit)*3, equal_weight_coverage_and_NAV_unchanged=True)
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    (OUT / 'preserved_file_manifest.json').write_text(json.dumps([dict(path=p, sha256=h) for p, h in sorted(frozen.items())], indent=2) + '\n')
    make_report(summaries, usage, exclusions, validation)
    files = [p for p in AREA.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT / 'run_eu_interim.py', ROOT / 'EU_INTERIM_METHOD.md', ROOT / 'backtest.py',
              ROOT / 'run_eu_restoration.py', ROOT / 'snapshot_integrity.py']
    (OUT / 'input_manifest.json').write_text(json.dumps([dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in sorted(files)], indent=2) + '\n')
    print(json.dumps(dict(validation={k:v for k,v in validation.items() if k != 'runs'},
                         returns=[dict(panel=s['panel'], rule=s['rule'], total_return=s['total_return']) for s in summaries]), indent=2))


def make_report(summaries, usage, exclusions, validation):
    lines = ['# EU interim-data results', '', 'EUR total returns, 30 September 2021 through 2 November 2026, after modeled 15bp trading costs.', '',
             '| Financial inputs for the seven restored companies | Q75 | Q50 | Equal weight |', '| --- | ---: | ---: | ---: |']
    for panel, label in zip(PANELS, ('Annual restoration reference', 'Annual plus recovered interim reports')):
        vs = [next(s for s in summaries if s['panel'] == panel and s['rule'] == rule)['total_return'] for rule in ('q75', 'q50', 'equal')]
        lines.append('| ' + label + ' | ' + ' | '.join(f'{v:.2%}' for v in vs) + ' |')
    lines += ['', 'The original eight companies retain their existing financial histories. The pool, prices, FX, costs and trading rules are fixed. The equal-weight control has identical eligibility and monthly NAV in both experiments; only the score portfolios respond to the newly available financial information.', '',
              '## Coverage', '', '| Ticker | Expected interims | Recovered | Valid TTM | Months scored using TTM | Months scored using annual |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for u in usage:
        lines.append(f"| {u['ticker']} | {u['expected_interims']} | {u['recovered_interims']} | {u['usable_ttm']} | {u['ttm_score_months']} | {u['annual_score_months']} |")
    lines += ['', 'Quarterly financial statements are used for Nel, Vestas, Orsted, ams OSRAM and Siemens Energy. Alfen and Safran supply half-year statements. Annual-score months are normal when a year-end report is the latest eligible fiscal period; they are not necessarily collection gaps.', '',
              f"There are {len(exclusions)} excluded or unrecovered observations; see [exclusion details](../data/eu_interim/exclusions.json).", '',
              '## Construction and limits', '',
              'Flow measures use observed prior annual + current YTD - comparative prior YTD; current balance-sheet figures are used directly. The arithmetic audit records every component. Contemporary restated annual comparatives or evidenced reclassifications are used where needed, with their actual availability dates. Original annual-score observations remain unchanged.', '',
              'Some continuing/discontinued-operation and interest-classification conventions differ across issuers. These are documented in the company research files. Historical annual publication choices remain as in the earlier restoration; Q4 preliminary announcements have not been used to bring those annual observations forward. Some Safran availability dates conservatively use the full interim-report publication rather than the earliest preliminary release.', '',
              'The October 31, 2026 rebalance uses information published strictly before October 1. The November 2 endpoint is a price mark without another rebalance. Later Q3 reports cannot affect this test. Future returns, a complete historical investable universe and original price/corporate-action accuracy are not established by this extension.', '',
              '## Reproduce and inspect', '', 'Run `python3 run_eu_interim.py` from the repository root. The run is offline and uses the Python standard library.', '',
              '- [Method fixed before results](../EU_INTERIM_METHOD.md)', '- [Recovered TTM financial inputs and source links](../data/eu_interim/financials_interim.csv)',
              '- [Source registry](../data/eu_interim/source_registry.json)', '- [Component arithmetic](../data/eu_interim/arithmetic_audit.json)',
              '- [Performance summary](summary.csv)', '- [Coverage and source usage](interim_coverage.csv)', '- [Validation](validation.json)',
              '- [Input hashes](input_manifest.json)', '',
              f"Verified {validation['arithmetic_fields_checked']} TTM flow calculations and reproduced all three annual-restoration reference runs. Source timing, freshness, holdings, NAV and trading costs passed; {validation['original_files_preserved']} prior files are unchanged.", '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
