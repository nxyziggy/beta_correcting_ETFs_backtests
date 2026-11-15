#!/usr/bin/env python3
"""Audit frozen price depth and build an append-only FRED FX supplement offline."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from backtest import Inputs
from prepare_data import ROOT, endmonth

AREA = ROOT / 'data/long_history/prices'


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    inputs = Inputs()
    added = []
    seen = set()
    overlap = 0
    for row in json.loads((AREA/'fx_web_capture.json').read_text()):
        key = row['series'], row['date']
        assert key not in seen, key
        seen.add(key)
        assert row['rate'] > 0 and row['source'] == 'https://fred.stlouisfed.org/data/' + row['series']
        old = inputs.fx[row['series']].get(row['date'])
        if old is not None:
            assert old == row['rate'], ('Existing FX differs', key)
            overlap += 1
        else:
            added.append(row)
            inputs.fx[row['series']][row['date']] = row['rate']
    inputs.fx_dates = {s: sorted(rows) for s, rows in inputs.fx.items()}
    write_csv(AREA/'fx_additions.csv', sorted(added, key=lambda r: (r['series'], r['date'])))
    fx_audit = []
    for year in range(2018, 2021):
        for month in range(1, 13):
            date = endmonth(year, month).isoformat()
            for series in sorted(inputs.fx):
                try:
                    rate = inputs.fx_value(series, date, True)
                    covered = True
                    observed = inputs.fx_log[series, date]['observation_date']
                except ValueError:
                    rate, covered, observed = '', False, ''
                fx_audit.append(dict(date=date, series=series, covered=covered,
                                     observation_date=observed, rate=rate))
    write_csv(AREA/'fx_month_end_audit.csv', fx_audit)
    listings = {r['ticker']: r for r in json.loads((AREA/'listing_overrides.json').read_text())}
    price_audit = []
    for ticker in sorted(inputs.prices):
        dates = sorted(inputs.prices[ticker])
        daily = sorted(inputs.daily[ticker])
        source = ROOT / 'data/prices' / (ticker+'.txt')
        price_audit.append(dict(ticker=ticker, first_frozen_month_end=dates[0],
                                last_effective_month_end=dates[-1], monthly_observations=len(dates),
                                first_independent_dated_daily=daily[0] if daily else '',
                                listing_override=listings.get(ticker,{}).get('listing_start',''),
                                capture_path=str(source.relative_to(ROOT)),
                                capture_sha256=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else ''))
    write_csv(AREA/'price_depth_audit.csv', price_audit)
    validation = dict(fx_rows_added=len(added), equal_overlap_observations=overlap,
                      month_end_failures=[r for r in fx_audit if not r['covered']],
                      no_original_market_files_modified=True,
                      limitation='Older monthly prices retain the released Digrin adjusted-price source; independent dated daily validation starts July2026. No new claim of exchange-grade total-return validation is made.')
    (AREA/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k!='month_end_failures'}))


if __name__ == '__main__':
    main()
