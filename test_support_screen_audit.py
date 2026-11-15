"""Check published support-screen coverage and non-company amount distinctions."""
import copy
import csv
import json
import unittest

from prepare_data import ROOT
from run_pillar2 import (first_admission_audit, original_ledger_start_audit,
                        read_research, support_binding_audit)


def rows(path):
    with (ROOT/path).open() as stream:
        return list(csv.DictReader(stream))


class SupportScreenAuditTests(unittest.TestCase):
    def test_binding_counts_exclude_only_unadmitted_listed_months(self):
        eligibility=rows('results_pillar2/monthly_eligibility.csv')
        summary=rows('results_pillar2/summary.csv')
        totals,excluded=support_binding_audit(eligibility,summary)
        actual={(r['definition'],r['region']):(r['listed_company_months'],r['excluded_company_months'])
                for r in totals}
        self.assertEqual(actual,{('direct','US'):(1336,68),('direct','EU'):(1278,11),
                                 ('direct','US+EU'):(2614,79),('with_indirect','US'):(1336,2),
                                 ('with_indirect','EU'):(1278,0),('with_indirect','US+EU'):(2614,2)})
        counts={}
        for r in excluded:
            key=(r['definition'],r['ticker']);counts[key]=counts.get(key,0)+1
        self.assertEqual(counts,{('direct','TSM'):66,('direct','MU'):2,
                                 ('direct','ALFEN.AS'):11,('with_indirect','MU'):2})
        self.assertEqual(max(r['end'] for r in totals),'2026-10-31')
        boolean_rows=copy.deepcopy(eligibility)
        for r in boolean_rows:
            for key in ('listed_at_cutoff','policy_eligible'):r[key]=r[key]=='True'
        self.assertEqual(support_binding_audit(boolean_rows,summary),(totals,excluded))

    def test_company_amounts_are_not_consortium_costs(self):
        events={e['event_id']:e for e in read_research()[0]}
        self.assertEqual(events['LRCX_CA_ETP_2016']['award_amount'],48816)
        ti=events['TXN_TEF_2019']
        self.assertEqual((ti['award_amount'],ti['award_currency'],ti['award_amount_status']),
                         (5124000,'USD','conditional_commitment'))
        for key in ('IFX_DE_ENIAC_ENLIGHT_2014','NXPI_ENIAC_ENLIGHT_2014'):
            e=events[key]
            self.assertIsNone(e['award_amount'])
            self.assertEqual((e['project_total_amount'],e['project_total_currency'],e['project_total_basis']),
                             (41300000,'EUR','total_project_cost'))
        self.assertEqual(len(events),54)

    def test_first_admission_classification_is_not_later_award_count(self):
        first=first_admission_audit(read_research()[0])
        modern={r['ticker'] for r in first if r['article_named_stream']!='earlier/other programme'}
        self.assertEqual(len(first),31)
        self.assertEqual(modern,{'GEV','TSM'})
        self.assertEqual(next(r for r in first if r['ticker']=='MU')['event_id'],'MU_VA_SMG_2019')

    def test_original_sparse_ledger_starts_with_four_eu_names(self):
        path=ROOT/'data/research_corrections'
        lam=json.loads((path/'lam_inputs.json').read_text())
        registry={'lam_source_'+r['period_end']:r for r in json.loads((path/'lam_sources.json').read_text())}
        audit=original_ledger_start_audit(lam,registry)
        results={r['region']:r for r in audit['results']}
        for region,date,count in (('US','2025-03-31',5),('EU','2023-12-31',4)):
            first=results[region]['first_investable_quarter']
            self.assertEqual((first['date'],first['covered']),(date,count))
            self.assertEqual(first,results[region]['first_complete_remaining_window'])
        self.assertEqual(results['EU']['first_five_name_quarter']['date'],'2024-12-31')


if __name__=='__main__':
    unittest.main()
