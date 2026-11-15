"""Verify the portable replay and its protections against mismatched evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from collect_long_history_us import OUT, evidence_value, rebuild_frozen, sec_snapshot_path


class FrozenUSCollectorTests(unittest.TestCase):
    def setUp(self):
        self.raw = dict(ticker='TEST', period_start='2018-01-01', period_end='2018-12-31',
                        publication_date='2019-02-10', currency='USD', accession='original')

    def fact(self, value, instant=False):
        value = dict(val=value, accn='original', end='2018-12-31',
                     filed='2019-02-10', unit='USD')
        if not instant:
            value['start'] = '2018-01-01'
        return value

    def test_captured_records_reproduce_every_released_observation(self):
        self.assertEqual(rebuild_frozen(), json.loads((OUT/'normalized_inputs.json').read_text()))

    def test_derived_income_and_cashflow_use_raw_components(self):
        self.raw['evidence'] = {key:self.fact(value*1e6) for key,value in
                               dict(revenue=100, cost=60, sga=15, rd=5).items()}
        self.assertEqual(evidence_value({'components':{'revenue':999}}, self.raw, True), 20)
        cfo = dict(continuing_operations=self.fact(4e6), discontinued_operations=self.fact(-1e6),
                   statement_qa={'normalized_group_cfo':3})
        self.assertEqual(evidence_value(cfo, self.raw, True), 3)
        gross = dict(gross_profit=self.fact(20e6), operating_expenses=self.fact(7e6))
        self.assertEqual(evidence_value(gross, self.raw, True), 13)

    def test_wrong_accession_date_currency_or_duration_fails(self):
        for field,wrong in [('accn','restated'), ('end','2019-12-31'), ('filed','2020-01-01'),
                            ('unit','EUR'), ('start','2018-04-01')]:
            fact=self.fact(1e6);fact[field]=wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                evidence_value(fact,self.raw,True)
        with self.assertRaises(ValueError):
            evidence_value(self.fact(1e6),self.raw,False)
        self.assertEqual(evidence_value(self.fact(1e6,instant=True),self.raw,False),1)

    def test_explicit_cache_rejects_missing_or_ambiguous_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            with self.assertRaises(ValueError):
                sec_snapshot_path(directory,'TEST')
            path=directory/'TEST_facts.json';path.write_text('{}')
            self.assertEqual(sec_snapshot_path(directory,'TEST'),path)
            (directory/'TEST_companyfacts.json').write_text('{}')
            with self.assertRaises(ValueError):
                sec_snapshot_path(directory,'TEST')


if __name__ == '__main__':
    unittest.main()
