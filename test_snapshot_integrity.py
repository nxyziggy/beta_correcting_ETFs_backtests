"""Historical data stay immutable while compatible implementation code evolves."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from prepare_data import ROOT
from run_research_corrections import frozen_files
from snapshot_integrity import verify_frozen_entries


class SnapshotIntegrityTests(unittest.TestCase):
    def record(self,root,path,text):
        p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        return dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

    def test_known_root_code_is_provenance_not_a_frozen_data_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            code=self.record(root,'backtest.py','old implementation')
            data=self.record(root,'data/observations.csv','fixed observations')
            (root/'backtest.py').write_text('compatible implementation extension')
            self.assertEqual(verify_frozen_entries(root,[code,data]),
                             {'data/observations.csv':data['sha256']})

    def test_code_named_file_under_data_is_still_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            row=self.record(root,'data/backtest.py','captured source')
            (root/row['path']).write_text('modified captured source')
            with self.assertRaisesRegex(AssertionError,'Frozen artifact changed'):
                verify_frozen_entries(root,[row])

    def test_results_and_method_documents_remain_strict(self):
        for path in ('results_old/input_manifest.json','METHOD.md','unrecognized_script.py'):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);row=self.record(root,path,'original')
                (root/path).write_text('changed')
                with self.assertRaisesRegex(AssertionError,'Frozen artifact changed'):
                    verify_frozen_entries(root,[row])

    def test_corrections_keep_the_original_upstream_scope(self):
        expected={r['path'] for r in json.loads((ROOT/'results_research_corrected/preserved_file_manifest.json').read_text())}
        actual=set(frozen_files())
        self.assertEqual(actual,expected)
        self.assertFalse(any(p.startswith(('data/long_history/','data/pillar2/','data/recovery_experiments/')) for p in actual))


if __name__=='__main__':unittest.main()
