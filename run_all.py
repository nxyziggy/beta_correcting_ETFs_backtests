#!/usr/bin/env python3
"""One-command, network-free reproduction using the frozen factual inputs."""
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for script in ('build_actual_financials.py','run_actual_dates.py','validate_actual.py','make_actual_tables.py'):
    print('\nRunning '+script,flush=True)
    subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=True)
print('\nFinished. See results_actual/ and tables_actual/. No network or API key was used.')
