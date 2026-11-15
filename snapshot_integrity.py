"""Separate frozen research artifacts from versioned implementation provenance.

Historical input manifests also identify the code used at publication. Those
code hashes are provenance, not an assertion that compatible extensions are
forbidden. Each legacy runner separately reproduces its published reference
returns; financial inputs, market data, results and method files still require
their exact recorded hashes. Only the explicit root implementation list below
is exempt from the historical hash-equality check.
"""
import hashlib


VERSIONED_IMPLEMENTATION = frozenset({
    'backtest.py', 'prepare_data.py', 'run_eu_restoration.py', 'run_eu_interim.py',
    'run_us_restoration.py', 'run_research_corrections.py',
    'test_research_corrections.py', 'snapshot_integrity.py',
})


def verify_frozen_entries(root, entries):
    """Verify immutable entries and return only that frozen artifact mapping."""
    frozen = {}
    for row in entries:
        relative = row['path']
        if relative in VERSIONED_IMPLEMENTATION:
            continue
        path = root / relative
        assert path.is_file(), ('Frozen artifact missing', relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == row['sha256'], ('Frozen artifact changed', relative)
        frozen[relative] = actual
    return frozen
