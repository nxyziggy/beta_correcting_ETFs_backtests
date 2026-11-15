#!/usr/bin/env python3
"""Run the predeclared EU coverage extension; never overwrite published runs."""
import csv
import datetime as dt
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from backtest import Inputs, read_csv, run
from prepare_data import ROOT, DATA, write_csv

AREA = DATA / 'eu_restoration'
OUT = ROOT / 'results_eu_restored'
RESTORED = {'ALFEN.AS', 'NEL.OL', 'AMS.SW', 'ORSTED.CO', 'VWS.CO', 'ENR.DE', 'SAF.PA'}
FIELDS = ('operating_income', 'net_income', 'operating_cash_flow', 'total_assets', 'current_liabilities')
PANELS = ('reference_expanded', 'restored_primary', 'restored_mixed', 'reference_annual', 'restored_annual')
START = '2021-09-30'
END = '2026-11-02'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(raw, secondary=False):
    r = dict(raw)
    assert r['ticker'] in RESTORED, r
    assert r['period_type'] == 'annual', r
    assert r['unit'] == 'million', r
    assert r['currency'] in ('EUR', 'DKK', 'NOK', 'USD', 'CHF'), r
    for k in FIELDS:
        r[k] = float(r[k])
        assert math.isfinite(r[k]), (k, r)
    assert r['total_assets'] > r['current_liabilities'] > 0, r
    assert r['period_end'] < r['availability_date'] <= END, r
    for k in ('income_source', 'balance_source', 'cashflow_source'):
        assert r[k].startswith('https://'), (k, r)
    if secondary:
        r['source_class'] = 'frozen_secondary_revised_history'
        r['publication_date'] = ''
        r['availability_basis'] = 'assumed 180 days after fiscal year-end; revised vendor history, not point-in-time'
        r['availability_date'] = (dt.date.fromisoformat(r['period_end']) + dt.timedelta(days=180)).isoformat()
        r['panel'] = 'restoration_secondary_annual'
    else:
        assert r.get('publication_date'), r
        assert r['period_end'] < r['publication_date'] <= r['availability_date'], r
        r.setdefault('source_class', 'recovered_primary_annual')
        r['panel'] = 'restoration_primary_annual'
    r.setdefault('fiscal_label', 'FY ' + r['period_end'][:4])
    r.setdefault('prior_total_assets', '')
    r.setdefault('prior_current_liabilities', '')
    if r.get('observation_id'):
        r['source_observation_id'] = r['observation_id']
    key = json.dumps(r, sort_keys=True)
    r['observation_id'] = 'eu_restore_' + hashlib.sha256(key.encode()).hexdigest()[:20]
    r['component_ids'] = r['observation_id']
    return r


def collect():
    primary = []
    for path in sorted(AREA.glob('research_*_rows.json')):
        rows = json.loads(path.read_text())
        assert isinstance(rows, list), path
        for raw in rows:
            primary.append(normalize(raw))
    keys = [(r['ticker'], r['period_end']) for r in primary]
    assert len(keys) == len(set(keys)), 'Duplicate recovered fiscal period'
    assert primary, 'No recovered observations: run source recovery first'
    secondary = [normalize(r, True) for r in read_csv(DATA / 'financials_vendor.csv') if r['ticker'] in RESTORED]
    pk = set(keys)
    mixed = primary + [r for r in secondary if (r['ticker'], r['period_end']) not in pk]
    for name, rows in [('primary_inputs', primary), ('secondary_candidates', secondary), ('mixed_inputs', mixed)]:
        (AREA / (name + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    columns = ['ticker', 'period_end', 'publication_date', 'availability_date', 'source_class', 'currency', 'unit',
               *FIELDS, 'income_source', 'balance_source', 'cashflow_source', 'observation_id', 'availability_basis']
    write_csv(AREA / 'restored_financials.csv', [{k: r[k] for k in columns} for r in sorted(mixed, key=lambda x: (x['ticker'], x['period_end']))])
    return primary, mixed


class RestoredInputs(Inputs):
    def __init__(self, panel, primary, mixed):
        super().__init__()
        self.panel_name = panel
        self.annual = read_csv(DATA / 'financials_actual_annual.csv')
        self.quarterly = read_csv(DATA / 'financials_actual_quarterly.csv')
        self.primary = []
        if panel == 'restored_primary':
            self.annual += primary
        elif panel in ('restored_mixed', 'restored_annual'):
            self.annual += mixed
        if panel in ('reference_annual', 'restored_annual'):
            self.quarterly = []
        self.observations = {r['observation_id']: r for r in self.annual + self.quarterly}

    def available(self, record, annual_lag):
        return dt.date.fromisoformat(record['availability_date'])

    def signals(self, region, date, panel, gate=False, annual_lag=0):
        return super().signals(region, date, 'hybrid', False, 0)


def verify(result, inputs):
    s = result['summary']
    assert s['start'] == START and s['latest_end'] == END, s
    holdings = defaultdict(list)
    trades = defaultdict(list)
    for h in result['holdings']:
        holdings[h['date']].append(h)
    for t in result['trades']:
        trades[t['date']].append(t)
    def close(a, b):
        assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8), (a, b)
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
        close(sum(abs(t['trade_value']) for t in ts) * .0015, m['Cost'])
        count = sum(h['ticker'] != 'CASH' and h['value'] > 0 for h in hs)
        assert count == m['Holdings']
        if s['rule'] != 'equal':
            assert 1 <= count <= 9
    primary_count = secondary_count = 0
    for sc in result['scores']:
        assert sc['available_used'] < sc['information_cutoff']
        r = inputs.observations[sc['observation_id']]
        assert sc['available_used'] == r['availability_date']
        age = (dt.date.fromisoformat(sc['date']) - dt.date.fromisoformat(sc['report_period'])).days
        assert age <= (550 if sc['period_type'] == 'annual' else 275)
        if sc['ticker'] in RESTORED:
            if r['source_class'] == 'frozen_secondary_revised_history':
                secondary_count += 1
                assert not sc['original_publication']
            else:
                primary_count += 1
                assert sc['original_publication'] < sc['information_cutoff']
    close(s['final_NAV'] / 100 - 1, s['total_return'])
    return dict(run=s['run'], result='PASS', months=len(result['monthly']), scores=len(result['scores']),
                restored_primary_score_rows=primary_count, restored_secondary_score_rows=secondary_count)


def main():
    AREA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    manifests = [json.loads((ROOT / x).read_text()) for x in ('INPUT_MANIFEST.json', 'RESULT_MANIFEST.json')]
    frozen = {r['path']: r['sha256'] for rows in manifests for r in rows}
    for p, expected in frozen.items():
        assert digest(ROOT / p) == expected, ('Published file changed before run', p)
    primary, mixed = collect()
    results, checks = [], []
    for panel in PANELS:
        inputs = RestoredInputs(panel, primary, mixed)
        for rule in ('q75', 'q50', 'equal'):
            result = run(inputs, 'EU', panel, rule, 15, annual_lag=0, start=START)
            assert result
            checks.append(verify(result, inputs))
            results.append(result)
    originals = read_csv(ROOT / 'results_actual/summary.csv')
    for result in results:
        s = result['summary']
        if s['panel'].startswith('reference_'):
            panel = 'actual_expanded' if s['panel'] == 'reference_expanded' else 'actual_annual'
            expected = next(x for x in originals if x['region'] == 'EU' and x['panel'] == panel
                            and x['rule'] == s['rule'] and x['window'] == 'matched')
            for k in ('final_NAV', 'total_return', 'CAGR', 'max_drawdown_monthly', 'total_cost_NAV_units'):
                assert math.isclose(s[k], float(expected[k]), rel_tol=1e-10, abs_tol=1e-8), (s['run'], k)
        for name, rows in result.items():
            if name != 'summary':
                write_csv(OUT / s['run'] / (name + '.csv'), rows)
    summaries = [r['summary'] for r in results]
    for s in summaries:
        control = next(r for r in summaries if r['panel'] == s['panel'] and r['rule'] == 'equal')
        s['covered_universe_return'] = control['total_return']
        s['selection_return_difference_pp'] = (s['total_return'] - control['total_return']) * 100
    write_csv(OUT / 'summary.csv', summaries)
    coverage = []
    for result in results:
        s = result['summary']
        if s['rule'] != 'equal':
            continue
        for ticker in sorted(RESTORED):
            rows = [r for r in result['coverage'] if r['ticker'] == ticker]
            covered = [r['date'] for r in rows if r['covered']]
            hs = [r['date'] for r in result['holdings'] if r['ticker'] == ticker]
            coverage.append(dict(panel=s['panel'], ticker=ticker, covered_months=len(covered),
                                 modeled_months=len(rows), first_covered=min(covered, default=''),
                                 last_covered=max(covered, default=''), first_control_holding=min(hs, default=''),
                                 uncovered_months='|'.join(r['date'] for r in rows if not r['covered'])))
    write_csv(OUT / 'restored_company_coverage.csv', coverage)
    for p, expected in frozen.items():
        assert digest(ROOT / p) == expected, ('Published file modified', p)
    report = dict(checks=checks, published_reference_runs_reproduced=6, published_files_unchanged=len(frozen),
                  recovered_rows=len(primary), mixed_rows=len(mixed), restored_tickers=sorted({r['ticker'] for r in mixed}),
                  source_limit='Secondary availability is a sensitivity assumption, not verified point-in-time availability.')
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    labels = {'reference_expanded': 'Published eight-company coverage', 'restored_primary': 'Restored primary reports',
              'restored_mixed': 'Restored, secondary fallback allowed', 'reference_annual': 'Original coverage, annual only',
              'restored_annual': 'Restored coverage, annual only'}
    lines = ['# EU coverage restoration results', '',
             'Historical window: 30 September 2021–2 November 2026, EUR, after 15bp trading costs.', '',
             '| Data panel | Q75 total return | Q50 total return | Equal-weight total return |',
             '| --- | ---: | ---: | ---: |']
    for panel in PANELS:
        values = [next(s for s in summaries if s['panel'] == panel and s['rule'] == rule)['total_return'] for rule in ('q75', 'q50', 'equal')]
        lines.append('| ' + labels[panel] + ' | ' + ' | '.join(f'{v:.2%}' for v in values) + ' |')
    lines += ['', 'Restoring the seven companies reverses the ordering in this historical window: both score strategies outperform the broader equal-weight control. The annual-only restored comparison also has both strategies ahead.', '',
              'The extra candidates change relative score percentiles as well as control holdings. For example, in the restored expanded runs Infineon is retained through the endpoint, whereas the original runs sold it in December 2025. STMicroelectronics exits in March 2026 rather than September 2025. No entry or exit threshold was retuned.', '',
              '## Recovered observations', '',
              f'Recovered {len(primary)} primary annual observations. The mixed panel has {len(mixed) - len(primary)} secondary fallback observations.', '',
              '| Company ticker | Primary annual rows | First fiscal period | Last fiscal period | Restored coverage |',
              '| --- | ---: | --- | --- | --- |']
    for ticker in sorted(RESTORED):
        rows = [r for r in primary if r['ticker'] == ticker]
        cov = next(r for r in coverage if r['panel'] == 'restored_mixed' and r['ticker'] == ticker)
        lines.append(f"| {ticker} | {len(rows)} | {min((r['period_end'] for r in rows), default='')} | {max((r['period_end'] for r in rows), default='')} | {cov['covered_months']}/{cov['modeled_months']} months |")
    lines += ['', 'Each of the seven names was added to the existing candidate pool. Eligibility, score thresholds and EDF delisting still apply. Adding a company to the pool does not require Q75/Q50 to hold it.', '',
              '## What this comparison measures', '',
              'The original eight companies retain their annual and interim observations in the expanded experiments. The seven restored companies have annual observations only. The annual-only pair compares both groups at annual frequency. Changing the pool also changes score percentiles and hence entries/exits; the difference is not only the return of seven additional holdings.', '',
              'Reported consolidated operating profit is used for restored companies. Several frozen vendor observations instead match adjusted profit or later restatements. The source research files document those differences. The original eight companies were not re-audited as part of this extension.', '',
              'Some selected annual-report dates are later than preliminary earnings releases; this uses evidenced conservative availability rather than claiming the earliest possible release. Safran FY2025 uses original full-year consolidated statements released on 13 February 2026; audit procedures were complete but the formal audit report was still pending. Nel FY2024 reports continuing-operation operating profit while group net profit and operating cash flow include discontinued operations. Separately displayed held-for-sale liabilities are excluded from literal reported current-liability subtotals. These accounting comparability limits remain explicit.', '',
              'Historical prices, FX, candidate identities and all portfolio rules are inherited unchanged. This is not a new price-data or corporate-action audit. Original statement recovery does not remove retrospective candidate selection or prove future investment performance.', '',
              '## Reproduction and evidence', '',
              'Run `python3 run_eu_restoration.py` from the repository root. It is offline and uses only the Python standard library. Generated extension outputs are overwritten on rerun; published outputs remain untouched.', '',
              '- [Method specified before restored returns](../EU_RESTORATION_METHOD.md)',
              '- [Financial values and source links](../data/eu_restoration/restored_financials.csv)',
              '- [Detailed normalized primary records](../data/eu_restoration/primary_inputs.json)',
              '- [Wind-company source research](../data/eu_restoration/research_wind.json)',
              '- [Alfen/Nel source research](../data/eu_restoration/research_energy.json)',
              '- [Industrial-company source research](../data/eu_restoration/research_industry.json)',
              '- [Monthly company coverage](restored_company_coverage.csv)',
              '- [Performance summaries](summary.csv)',
              '- [Validation checks](validation.json)',
              '- [Input/source SHA-256 manifest](input_manifest.json)', '',
              f'Validation reproduced six published reference runs and confirmed that all {len(frozen)} manifested original input/result files remain unchanged. Each new run passed timing, freshness, observation-link, portfolio accounting, trading-cost and holding-bound checks.', '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))
    files = [p for p in AREA.rglob('*') if p.is_file() and '__pycache__' not in p.parts] + [ROOT / 'run_eu_restoration.py', ROOT / 'EU_RESTORATION_METHOD.md', ROOT / 'backtest.py']
    (OUT / 'input_manifest.json').write_text(json.dumps([dict(path=str(p.relative_to(ROOT)), sha256=digest(p), bytes=p.stat().st_size)
                                                        for p in sorted(files)], indent=2) + '\n')
    print(json.dumps([dict(panel=s['panel'], rule=s['rule'], return_pct=round(s['total_return'] * 100, 4),
                           coverage=s['final_covered_universe']) for s in summaries], indent=2))


if __name__ == '__main__':
    main()
