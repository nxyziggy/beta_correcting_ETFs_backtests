#!/usr/bin/env python3
"""Build a portable archive of code, factual evidence and every computed ledger."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'outputs/actual_dates_20261104'
CORE=['README.md','ACTUAL_DATES_METHOD.md','METHOD_LOCK.md','EXTENSION_METHOD.md','HOLDINGS_RULE_CHANGE.md',
      'run_all.py','build_actual_financials.py','run_actual_dates.py','backtest.py','validate_actual.py',
      'make_actual_tables.py','prepare_data.py','prepare_extension.py','make_report.py','parse_issuer_sources.py','collect_sources.py','package_replication.py']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    files=[ROOT/n for n in CORE]
    for folder in ['data','results_actual','tables_actual','audit']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and p.name!='source_index.json' and 'actual_dates/sources/' not in str(p)]
    files += [ROOT/'baseline_1to9/INPUT_SHA256.json',ROOT/'baseline_1to9/results_final/summary.csv']
    files=sorted(set(files))
    input_files=[p for p in files if str(p.relative_to(ROOT)).startswith('data/') and p.name not in ['financials_actual_annual.csv','financials_actual_quarterly.csv','observations_normalized.json','calculation_audit.json','coverage_counts.json','ttm_exclusions.json']]
    result_files=[p for p in files if str(p.relative_to(ROOT)).startswith(('results_actual/','tables_actual/'))]
    for name,ls in [('INPUT_MANIFEST',input_files),('RESULT_MANIFEST',result_files)]:
        path=ROOT/(name+'.json');path.write_text(json.dumps([dict(path=str(p.relative_to(ROOT)),sha256=digest(p),bytes=p.stat().st_size) for p in ls],indent=2)+'\n');files.append(path)
    for name in ['REPLICATION_VERIFICATION.json']:
        if (ROOT/name).exists():files.append(ROOT/name)
    OUT.mkdir(parents=True,exist_ok=True)
    dest=OUT/'Actual_Dates_Backtest_Replication.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,'Actual_Dates_Backtest/'+str(p.relative_to(ROOT)))
    print(json.dumps(dict(file=str(dest),bytes=dest.stat().st_size,files=len(files),input_files=len(input_files),result_files=len(result_files))))
if __name__=='__main__':main()
