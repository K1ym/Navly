from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from completeness.qinqin_endpoint_completeness import build_qinqin_endpoint_completeness_results  # noqa: E402
from quality.qinqin_endpoint_governance import (  # noqa: E402
    build_five_store_endpoint_validation_matrix,
    build_qinqin_endpoint_governance_results,
)
from tests.support.qinqin_governance_fixture_builder import (  # noqa: E402
    build_endpoint_runs,
    build_raw_pages_by_endpoint,
    endpoint_contract_ids,
    structured_target_ids,
)
from warehouse.qinqin_structured_target_landing import build_qinqin_structured_target_artifacts  # noqa: E402


class QinqinEndpointGovernanceClosureTest(unittest.TestCase):
    def _artifacts(self, org_id: str = 'store-001') -> dict[str, list[dict]]:
        raw_pages_by_endpoint = build_raw_pages_by_endpoint(org_id=org_id, value_suffix=org_id.replace('-', '_'))
        return build_qinqin_structured_target_artifacts(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            org_id=org_id,
            requested_business_date='2026-04-11',
            endpoint_contract_ids=endpoint_contract_ids(),
        )

    def test_structured_target_landing_formalizes_all_manifest_targets(self) -> None:
        artifacts = self._artifacts()
        self.assertEqual(sorted(artifacts.keys()), sorted(structured_target_ids()))
        for target_dataset in structured_target_ids():
            self.assertTrue(artifacts[target_dataset], target_dataset)
            sample_row = artifacts[target_dataset][0]
            self.assertEqual(sample_row['target_dataset'], target_dataset)
            self.assertIn('landing_row_id', sample_row)
            self.assertIn('field_values', sample_row)
            self.assertNotIn('response_envelope', sample_row)

        tech_shift_summary = artifacts['tech_shift_summary'][0]
        self.assertIn('Main__Total', tech_shift_summary['field_values'])
        self.assertIn('Extra__Total', tech_shift_summary['field_values'])
        self.assertIn('TotalClock', tech_shift_summary['field_values'])

    def test_endpoint_governance_results_cover_all_8_endpoints(self) -> None:
        raw_pages_by_endpoint = build_raw_pages_by_endpoint(org_id='store-001')
        endpoint_runs = build_endpoint_runs(org_id='store-001')
        governance_results = build_qinqin_endpoint_governance_results(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            endpoint_runs=endpoint_runs,
        )

        self.assertEqual(len(governance_results), 8)
        for result in governance_results:
            self.assertEqual(result['field_coverage_snapshot']['snapshot_status'], 'complete')
            self.assertEqual(result['field_coverage_snapshot']['missing_field_count'], 0)
            self.assertEqual(result['field_coverage_snapshot']['ungoverned_field_count'], 0)
            self.assertEqual(result['schema_alignment_snapshot']['snapshot_status'], 'aligned')
            self.assertEqual(result['schema_alignment_snapshot']['misaligned_field_count'], 0)
            self.assertEqual(result['quality_status'], 'clean')
            self.assertEqual(result['quality_issues'], [])

    def test_quality_taxonomy_maps_source_empty_auth_sign_schema_and_business(self) -> None:
        raw_pages_by_endpoint = build_raw_pages_by_endpoint(org_id='store-002')
        raw_pages_by_endpoint['qinqin.staff.get_tech_market_list.v1_7'][0]['response_envelope']['RetData']['RoomCode'] = {'unexpected': 'object'}
        endpoint_runs = build_endpoint_runs(
            org_id='store-002',
            status_overrides={
                'qinqin.member.get_customers_list.v1_1': {'endpoint_status': 'source_empty'},
                'qinqin.member.get_consume_bill_list.v1_2': {
                    'endpoint_status': 'failed',
                    'error_taxonomy': 'transport_http_error',
                    'error_code': '401',
                    'error_message': 'Authorization token expired.',
                },
                'qinqin.member.get_recharge_bill_list.v1_3': {
                    'endpoint_status': 'failed',
                    'error_taxonomy': 'source_business_error',
                    'error_code': '-500',
                    'error_message': '验签失败',
                },
                'qinqin.staff.get_person_list.v1_5': {
                    'endpoint_status': 'failed',
                    'error_taxonomy': 'source_business_error',
                    'error_code': '-300',
                    'error_message': '业务规则失败',
                },
            },
        )
        governance_results = {
            item['endpoint_contract_id']: item
            for item in build_qinqin_endpoint_governance_results(
                raw_pages_by_endpoint=raw_pages_by_endpoint,
                endpoint_runs=endpoint_runs,
            )
        }

        self.assertEqual(governance_results['qinqin.member.get_customers_list.v1_1']['quality_status'], 'source_empty')
        self.assertEqual(governance_results['qinqin.member.get_consume_bill_list.v1_2']['quality_status'], 'auth_failure')
        self.assertEqual(governance_results['qinqin.member.get_recharge_bill_list.v1_3']['quality_status'], 'sign_failure')
        self.assertEqual(governance_results['qinqin.staff.get_tech_market_list.v1_7']['quality_status'], 'schema_failure')
        self.assertEqual(governance_results['qinqin.staff.get_person_list.v1_5']['quality_status'], 'business_failure')

    def test_endpoint_completeness_results_cover_all_8_endpoints(self) -> None:
        raw_pages_by_endpoint = build_raw_pages_by_endpoint(org_id='store-003')
        endpoint_runs = build_endpoint_runs(org_id='store-003')
        structured_target_artifacts = build_qinqin_structured_target_artifacts(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            org_id='store-003',
            requested_business_date='2026-04-11',
            endpoint_contract_ids=endpoint_contract_ids(),
        )
        governance_results = build_qinqin_endpoint_governance_results(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            endpoint_runs=endpoint_runs,
        )
        completeness_results = build_qinqin_endpoint_completeness_results(
            governance_results=governance_results,
            endpoint_runs=endpoint_runs,
            structured_target_artifacts=structured_target_artifacts,
            requested_business_date='2026-04-11',
        )

        self.assertEqual(len(completeness_results), 8)
        for result in completeness_results:
            self.assertEqual(result['landing_status'], 'formalized')
            self.assertEqual(result['completeness_status'], 'ready')
            self.assertEqual(result['latest_usable_business_date'], '2026-04-11')
            self.assertEqual(len(result['formalized_target_ids']), len(result['structured_targets']))

    def test_five_store_validation_answers_did_it_run_and_did_fields_align(self) -> None:
        store_results = []
        for index in range(1, 6):
            org_id = f'store-00{index}'
            raw_pages_by_endpoint = build_raw_pages_by_endpoint(org_id=org_id)
            endpoint_runs = build_endpoint_runs(org_id=org_id)
            if org_id == 'store-005':
                raw_pages_by_endpoint['qinqin.staff.get_tech_up_clock_list.v1_6'][0]['response_envelope']['RetData']['Items'][0]['PersonCode'] = {'bad': 'shape'}
            if org_id == 'store-004':
                endpoint_runs = build_endpoint_runs(
                    org_id=org_id,
                    status_overrides={
                        'qinqin.member.get_user_trade_list.v1_4': {
                            'endpoint_status': 'failed',
                            'error_taxonomy': 'source_business_error',
                            'error_code': '-300',
                            'error_message': '业务规则失败',
                        },
                    },
                )
            structured_target_artifacts = build_qinqin_structured_target_artifacts(
                raw_pages_by_endpoint=raw_pages_by_endpoint,
                org_id=org_id,
                requested_business_date='2026-04-11',
                endpoint_contract_ids=endpoint_contract_ids(),
            )
            governance_results = build_qinqin_endpoint_governance_results(
                raw_pages_by_endpoint=raw_pages_by_endpoint,
                endpoint_runs=endpoint_runs,
            )
            completeness_results = build_qinqin_endpoint_completeness_results(
                governance_results=governance_results,
                endpoint_runs=endpoint_runs,
                structured_target_artifacts=structured_target_artifacts,
                requested_business_date='2026-04-11',
            )
            store_results.append({
                'org_id': org_id,
                'requested_business_date': '2026-04-11',
                'endpoint_runs': endpoint_runs,
                'governance_results': governance_results,
                'completeness_results': completeness_results,
            })

        validation_matrix = build_five_store_endpoint_validation_matrix(store_results)
        self.assertEqual(validation_matrix['store_count'], 5)
        self.assertEqual(len(validation_matrix['rows']), 40)

        trade_failure = next(
            row for row in validation_matrix['rows']
            if row['org_id'] == 'store-004' and row['endpoint_contract_id'] == 'qinqin.member.get_user_trade_list.v1_4'
        )
        self.assertTrue(trade_failure['did_run'])
        self.assertEqual(trade_failure['run_status'], 'failed')

        schema_failure = next(
            row for row in validation_matrix['rows']
            if row['org_id'] == 'store-005' and row['endpoint_contract_id'] == 'qinqin.staff.get_tech_up_clock_list.v1_6'
        )
        self.assertFalse(schema_failure['fields_aligned'])
        self.assertEqual(schema_failure['schema_alignment_status'], 'misaligned')


if __name__ == '__main__':
    unittest.main()
