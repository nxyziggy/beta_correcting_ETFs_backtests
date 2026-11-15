#!/usr/bin/env python3
"""Reproduce the US reference and extend coverage with dated annual/interim facts."""
import datetime as dt
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal

from backtest import Inputs, read_csv, run
from prepare_data import ROOT, DATA, write_csv

AREA = DATA / 'us_restoration'
OUT = ROOT / 'results_us_restored'
RESTORED = {'TSM', 'FSLR', 'PLUG', 'BE', 'ETN', 'GEV'}
FLOWS = ('operating_income', 'net_income', 'operating_cash_flow')
BALANCES = ('total_assets', 'current_liabilities')
START, END, CUTOFF = '2022-09-30', '2026-11-02', '2026-10-01'
PANELS = ('reference_expanded', 'restored_annual', 'restored_interim')
LABELS = ('Published ten-company coverage', 'Six companies restored with annual reports',
          'Six companies restored with annual and interim reports')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def identifier(prefix, value):
    return prefix + hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def expected_periods(kind):
    keys = set()
    for t in sorted(RESTORED):
        if kind == 'annual':
            keys.update((t, f'{y}-12-31') for y in range(2022 if t == 'GEV' else 2021, 2026))
        else:
            if t != 'GEV':
                keys.update((t, f'2022-{m}') for m in ('06-30', '09-30'))
            for y in range(2024 if t == 'GEV' else 2023, 2026):
                keys.update((t, f'{y}-{m}') for m in ('03-31', '06-30', '09-30'))
            keys.update((t, f'2026-{m}') for m in ('03-31', '06-30'))
    return keys


def build(annual, interims):
    registry, audit, excluded = {}, [], []
    normalized = {'annual': [], 'interim': []}
    for kind, raw_rows in [('annual', annual), ('interim', interims)]:
        seen = set()
        for raw in sorted(raw_rows, key=lambda r: (r['ticker'], r['period_end'])):
            key = raw['ticker'], raw['period_end']
            assert key not in seen, ('Duplicate source period', key)
            seen.add(key)
            assert raw['ticker'] in RESTORED and raw['unit'] == 'million'
            assert raw['currency'] in ('USD', 'TWD')
            assert raw['period_end'] < raw['publication_date'] <= raw['availability_date']
            if raw['availability_date'] >= CUTOFF or (kind == 'interim' and raw.get('ttm_compatible') is not True):
                excluded.append(dict(ticker=key[0], period_end=key[1], kind=kind,
                                     reason='After final cutoff or unresolved accounting compatibility'))
                continue
            for f in ('income_source', 'balance_source', 'cashflow_source', 'date_source'):
                assert raw[f].startswith('https://'), (key, f)
            sid = identifier('us_source_', raw)
            registry[sid] = raw
            component_ids = [sid]
            available = raw['availability_date']
            calculations = []
            if kind == 'annual':
                flows = {f: float(raw[f]) for f in FLOWS}
            else:
                prev = raw['prior_annual']
                assert prev['period_end'] == f"{int(raw['fiscal_year'])-1}-12-31", key
                assert raw['fiscal_quarter'] in (1, 2, 3)
                assert prev['period_end'] < prev['publication_date'] <= prev['availability_date']
                assert prev.get('currency', raw['currency']) == raw['currency']
                assert prev.get('unit', 'million') == 'million'
                assert prev['source'].startswith('https://')
                pid = identifier('us_annual_component_', prev)
                registry[pid] = prev
                component_ids.append(pid)
                available = max(available, prev['availability_date'])
                assert available < CUTOFF, ('Future annual component', key)
                flows = {}
                for f in FLOWS:
                    a, b, c = (float(prev[f]), float(raw['ytd'][f]), float(raw['prior_ytd'][f]))
                    flows[f] = a + b - c
                    calculations.append(dict(field=f, prior_annual=a, current_ytd=b, prior_ytd=c, value=flows[f]))
                    independently = Decimal(str(prev[f])) + Decimal(str(raw['ytd'][f])) - Decimal(str(raw['prior_ytd'][f]))
                    assert math.isclose(float(independently), flows[f], abs_tol=1e-7, rel_tol=1e-12)
            balances = {f: float(raw[f]) for f in BALANCES}
            assert all(math.isfinite(v) for v in [*flows.values(), *balances.values()])
            assert balances['total_assets'] > balances['current_liabilities'] > 0, key
            row = dict(ticker=raw['ticker'], period_end=raw['period_end'],
                       fiscal_label=('FY ' + raw['period_end'][:4] if kind == 'annual' else
                                     f"TTM through fiscal Q{raw['fiscal_quarter']} {raw['fiscal_year']}"),
                       panel='us_recovered_original_' + kind,
                       period_type='annual' if kind == 'annual' else 'trailing',
                       publication_date=raw['publication_date'], availability_date=available,
                       availability_basis='evidenced source dates; latest availability of all components',
                       currency=raw['currency'], unit='million', **flows, **balances,
                       prior_total_assets='', prior_current_liabilities='',
                       income_source=raw['income_source'], balance_source=raw['balance_source'],
                       cashflow_source=raw['cashflow_source'], source_class='recovered_primary_' + kind,
                       component_ids='|'.join(component_ids))
            row['observation_id'] = identifier('us_input_', row)
            normalized[kind].append(row)
            audit.append(dict(observation_id=row['observation_id'], ticker=key[0], period_end=key[1],
                              kind=kind, source_ids=component_ids, available=available,
                              calculations=calculations, notes=raw.get('notes', [])))
        for t, p in sorted(expected_periods(kind) - seen):
            excluded.append(dict(ticker=t, period_end=p, kind=kind, reason='Target observation not recovered'))
    return normalized, registry, audit, excluded


class RestoredUSInputs(Inputs):
    def __init__(self, panel, normalized):
        super().__init__()
        self.annual = read_csv(DATA / 'financials_actual_annual.csv')
        self.quarterly = read_csv(DATA / 'financials_actual_quarterly.csv')
        self.primary = []
        if panel != 'reference_expanded':
            self.annual += normalized['annual']
        if panel == 'restored_interim':
            self.quarterly += normalized['interim']
        self.observations = {r['observation_id']: r for r in self.annual + self.quarterly}

    def available(self, record, annual_lag):
        return dt.date.fromisoformat(record['availability_date'])

    def signals(self, region, date, panel, gate=False, annual_lag=0):
        return super().signals(region, date, 'hybrid', False, 0)


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8), (a, b)


def verify(result, inputs, registry):
    s = result['summary']
    assert s['start'] == START and s['latest_end'] == END and s['cost_bps'] == 10
    holdings, trades = defaultdict(list), defaultdict(list)
    for h in result['holdings']:
        holdings[h['date']].append(h)
        if h['ticker'] == 'GEV':
            assert h['date'] >= '2024-04-02'
    for t in result['trades']:
        trades[t['date']].append(t)
    previous = None
    for m in result['monthly']:
        date = dt.date.fromisoformat(m['date'])
        if previous:
            assert (date.year - previous.year) * 12 + date.month - previous.month == 1
        previous = date
        hs, ts = holdings[m['date']], trades[m['date']]
        close(sum(h['weight'] for h in hs), 1)
        close(sum(h['value'] for h in hs), m['NAV'])
        close(m['PreTradeNAV'] - m['Cost'], m['NAV'])
        close(sum(t['cost'] for t in ts), m['Cost'])
        close(sum(abs(t['trade_value']) for t in ts) * .001, m['Cost'])
        count = sum(h['ticker'] != 'CASH' and h['value'] > 0 for h in hs)
        assert count == m['Holdings']
        if s['rule'] != 'equal':
            assert 1 <= count <= 9
    for sc in result['scores']:
        r = inputs.observations[sc['observation_id']]
        assert sc['available_used'] == r['availability_date'] < sc['information_cutoff']
        age = (dt.date.fromisoformat(sc['date']) - dt.date.fromisoformat(r['period_end'])).days
        assert age <= (550 if r['period_type'] == 'annual' else 275)
        eligible = [a for a in inputs.annual + inputs.quarterly if a['ticker'] == sc['ticker']
                    and a['availability_date'] < sc['information_cutoff']
                    and (dt.date.fromisoformat(sc['date']) - dt.date.fromisoformat(a['period_end'])).days
                    <= (550 if a['period_type'] == 'annual' else 275)]
        latest = max(eligible, key=lambda a: (a['period_end'], a['period_type'] == 'trailing', a['panel'].startswith('primary')))
        assert latest['observation_id'] == r['observation_id']
        if sc['ticker'] in RESTORED:
            assert r['publication_date'] < sc['information_cutoff']
            for cid in r['component_ids'].split('|'):
                assert registry[cid]['availability_date'] < sc['information_cutoff']
        if sc['ticker'] == 'GEV':
            assert sc['date'] >= '2024-04-02'
    close(s['final_NAV'] / 100 - 1, s['total_return'])
    return dict(run=s['run'], result='PASS', months=len(result['monthly']), scores=len(result['scores']))


def frozen_files():
    frozen = {}
    for name in ('INPUT_MANIFEST.json', 'RESULT_MANIFEST.json', 'results_eu_restored/input_manifest.json',
                 'results_eu_interim/input_manifest.json', 'results_eu_interim/preserved_file_manifest.json'):
        for r in json.loads((ROOT / name).read_text()):
            assert digest(ROOT / r['path']) == r['sha256'], ('Existing file changed', r['path'])
            frozen[r['path']] = r['sha256']
    for directory in ('data/eu_restoration', 'data/eu_interim', 'results_eu_restored', 'results_eu_interim'):
        for p in (ROOT / directory).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                frozen[str(p.relative_to(ROOT))] = digest(p)
    return frozen


def main():
    AREA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    frozen = frozen_files()
    raw = {}
    for kind in ('annual', 'interim'):
        raw[kind] = [r for p in sorted(AREA.glob(f'research_*_{kind}.json')) for r in json.loads(p.read_text())]
        assert {r['ticker'] for r in raw[kind]} == RESTORED, ('Finish source recovery before running', kind)
    normalized, registry, audit, excluded = build(raw['annual'], raw['interim'])
    for name, value in [('normalized_inputs', normalized), ('source_registry', registry),
                        ('arithmetic_audit', audit), ('exclusions', excluded)]:
        (AREA / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    write_csv(AREA / 'financials_annual.csv', normalized['annual'])
    write_csv(AREA / 'financials_interim.csv', normalized['interim'])
    original = read_csv(ROOT / 'results_actual/summary.csv')
    results, checks = [], []
    for panel in PANELS:
        inputs = RestoredUSInputs(panel, normalized)
        for rule in ('q75', 'q50', 'equal'):
            result = run(inputs, 'US', panel, rule, 10, annual_lag=0, start=START)
            checks.append(verify(result, inputs, registry))
            s = result['summary']
            if panel == 'reference_expanded':
                old = next(r for r in original if r['region'] == 'US' and r['panel'] == 'actual_expanded'
                           and r['rule'] == rule and r['window'] == 'matched')
                for f in ('total_return', 'final_NAV', 'CAGR', 'max_drawdown_monthly', 'total_cost_NAV_units'):
                    close(s[f], old[f])
            for kind, rows in result.items():
                if kind != 'summary':
                    write_csv(OUT / s['run'] / (kind + '.csv'), rows)
            results.append(result)
    summaries = [r['summary'] for r in results]
    for s in summaries:
        control = next(x for x in summaries if x['panel'] == s['panel'] and x['rule'] == 'equal')
        s['covered_universe_return'] = control['total_return']
        s['selection_return_difference_pp'] = 100 * (s['total_return'] - control['total_return'])
    write_csv(OUT / 'summary.csv', summaries)
    controls = [r for r in results if r['summary']['rule'] == 'equal']
    unchanged = controls[1]['coverage'] == controls[2]['coverage'] and controls[1]['monthly'] == controls[2]['monthly']
    coverage = []
    for result in controls:
        for ticker in sorted(RESTORED):
            cs = [r for r in result['coverage'] if r['ticker'] == ticker]
            ss = [r for r in result['scores'] if r['ticker'] == ticker]
            hs = [r['date'] for r in result['holdings'] if r['ticker'] == ticker]
            coverage.append(dict(panel=result['summary']['panel'], ticker=ticker,
                                 covered_months=sum(r['covered'] for r in cs), modeled_months=len(cs),
                                 first_covered=min((r['date'] for r in ss), default=''),
                                 first_control_holding=min(hs, default=''),
                                 annual_score_months=sum(r['period_type'] == 'annual' for r in ss),
                                 ttm_score_months=sum(r['period_type'] == 'trailing' for r in ss),
                                 uncovered_reasons=' | '.join(sorted({r['reason'] for r in cs if not r['covered']}))))
    write_csv(OUT / 'restored_company_coverage.csv', coverage)
    for p, sha in frozen.items():
        assert digest(ROOT / p) == sha, ('Previous file modified', p)
    validation = dict(runs=checks, published_reference_runs_reproduced=3, preserved_files=len(frozen),
                      expected_annual=len(expected_periods('annual')), recovered_annual=len(normalized['annual']),
                      expected_interims=len(expected_periods('interim')), usable_ttm=len(normalized['interim']),
                      arithmetic_fields_checked=3 * len(normalized['interim']), excluded=len(excluded),
                      annual_interim_equal_control_unchanged=unchanged)
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    (OUT / 'preserved_file_manifest.json').write_text(json.dumps([dict(path=p, sha256=h) for p,h in sorted(frozen.items())], indent=2) + '\n')
    make_report(summaries, coverage, validation)
    files = [p for p in AREA.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT / 'run_us_restoration.py', ROOT / 'US_RESTORATION_METHOD.md', ROOT / 'backtest.py']
    (OUT / 'input_manifest.json').write_text(json.dumps([dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in sorted(files)], indent=2) + '\n')
    print(json.dumps(dict(validation={k:v for k,v in validation.items() if k != 'runs'},
                         returns=[{k:s[k] for k in ('panel', 'rule', 'total_return')} for s in summaries]), indent=2))


def make_report(summaries, coverage, v):
    lines = ['# US coverage restoration results', '',
             'USD total returns, 30 September 2022 through 2 November 2026, after modeled 10bp trading costs.', '',
             '| Financial coverage | Q75 | Q50 | Equal weight |', '| --- | ---: | ---: | ---: |']
    for panel, label in zip(PANELS, LABELS):
        vals = [next(s['total_return'] for s in summaries if s['panel'] == panel and s['rule'] == r) for r in ('q75', 'q50', 'equal')]
        lines.append('| ' + label + ' | ' + ' | '.join(f'{x:.2%}' for x in vals) + ' |')
    lines += ['', 'The original ten companies retain their existing histories. Candidate identities, prices, FX, costs, score rules and dates are fixed. Restoring financial coverage changes the stock pool and ranks. Quarterly updates can then change scores and trades within that restored pool.', '',
              '## Restored company coverage', '',
              '| Company | Months covered | First covered | First equal-weight holding | Annual score months | TTM score months |',
              '| --- | ---: | --- | --- | ---: | ---: |']
    for r in coverage:
        if r['panel'] == 'restored_interim':
            lines.append(f"| {r['ticker']} | {r['covered_months']}/{r['modeled_months']} | {r['first_covered']} | {r['first_control_holding']} | {r['annual_score_months']} | {r['ttm_score_months']} |")
    lines += ['', f"Recovered {v['recovered_annual']}/{v['expected_annual']} targeted annual observations and {v['usable_ttm']}/{v['expected_interims']} usable interim observations. Exclusions or gaps: {v['excluded']}; see the [exclusion ledger](../data/us_restoration/exclusions.json).", '',
              'GE Vernova remains ineligible before its 2 April 2024 listing. The control admits eligible new names at quarter-ends. Sixteen covered companies therefore does not mean sixteen holdings throughout the historical window.', '',
              f"The annual-restored and interim-restored equal-weight coverage and monthly ledgers are {'identical' if v['annual_interim_equal_control_unchanged'] else 'different; inspect the coverage ledger for timing differences'}.", '',
              '## Sources, timing and limits', '',
              'New flows use original annual figures or comparable prior annual + current YTD − prior YTD; balance sheets are current. Every calculation records the source components. SEC facts retain accession and filing dates, and issuer reports supply missing disclosures. Full filing dates can be later than earnings announcements. A later published restatement is not available retroactively.', '',
              'Eaton operating profit is a derived subtotal: sales less cost of products sold, selling/administrative expenses and research/development. It excludes separately reported financing, disposal and other income/expense lines. The component facts are documented; this is not an issuer-reported operating-income line, and the mixed other-income/expense line limits comparability.', '',
              'TSMC annual and interim inputs consistently use Taiwan-endorsed IFRS consolidated statements filed on Form 6-K. They are not mixed with the IASB-IFRS 20-F annual series, whose tax-recognition timing can change net income and liabilities. Accounting-basis evidence and an example reconciliation are retained in the source records.', '',
              'The last rebalance uses information published strictly before 1 October 2026. Later Q3 results cannot affect this fixed window. The inherited market data, retrospective universe, accounting comparability across companies and future performance are not independently established by this extension.', '',
              '## Reproduce and audit', '', 'Run `python3 run_us_restoration.py` from the repository root; the calculation is offline and uses the Python standard library.', '',
              '- [Method specified before returns](../US_RESTORATION_METHOD.md)',
              '- [Annual inputs](../data/us_restoration/financials_annual.csv) and [interim inputs](../data/us_restoration/financials_interim.csv)',
              '- [Source registry](../data/us_restoration/source_registry.json) and [arithmetic audit](../data/us_restoration/arithmetic_audit.json)',
              '- [Summary](summary.csv) and [coverage](restored_company_coverage.csv)',
              '- [Validation](validation.json), [input hashes](input_manifest.json) and [preserved-file hashes](preserved_file_manifest.json)', '',
              f"Validated {v['arithmetic_fields_checked']} TTM flow calculations and all nine runs, including reproduction of all three published US reference runs. Source timing, latest-period selection, freshness, listing eligibility, holdings, NAV and costs passed. {v['preserved_files']} prior files remain unchanged.", '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
