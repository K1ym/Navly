from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from quality.commission_setting_quality import RUNTIME_HEADER_VARIANCE_ID  # noqa: E402
from workflows.commission_setting_governance_surface import build_commission_setting_governance_surface  # noqa: E402


def _load_sync_state_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'commission_setting_sync_state.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_commission_setting_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CommissionSettingGovernanceSurfaceTest(unittest.TestCase):
    def _success_envelope(self) -> dict:
        return {
            'Code': 200,
            'Msg': '操作成功',
            'RetData': [
                {
                    'ItemName': '至尊足道',
                    'ItemId': '425dd401-709d-456b-930d-be73bb3d55b1',
                    'PCBaseList': [
                        {
                            'Add': 125.0,
                            'AddBuy': 0.0,
                            'AddCall': 0.0,
                            'AddClock': 0.0,
                            'AddPoint': 0.0,
                            'AddWheel': 0.0,
                            'Amount': 0.0,
                            'Appoint': 125.0,
                            'Buy': 120.0,
                            'Call': 120.0,
                            'EPoint': 0.0,
                            'Id': '17d3a305-b936-4722-a2d2-b93cad4cf2af',
                            'IsOpenMultiple': False,
                            'ItemId': '425dd401-709d-456b-930d-be73bb3d55b1',
                            'ItemName': '至尊足道',
                            'Multiple': 0.0,
                            'OptTime': '2024-08-20 14:44:25',
                            'OrgId': 'demo-org-001',
                            'OverAdd': 0.0,
                            'OverBuy': 0.0,
                            'OverCall': 0.0,
                            'OverPoint': 0.0,
                            'OverWheel': 0.0,
                            'Sex': 0,
                            'SPoint': 0.0,
                            'State': 1,
                            'Wheel': 120.0,
                            'BaseCommissionChannel': 1,
                            'OverCommissionChannel': 1,
                            'AddCommissionChannel': 1,
                        }
                    ],
                }
            ],
        }

    def _endpoint_run(
        self,
        *,
        endpoint_status: str,
        terminal_outcome_category: str,
        error_taxonomy: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        endpoint_run_id: str = 'er_commission_001',
    ) -> dict[str, object]:
        return {
            'endpoint_run_id': endpoint_run_id,
            'endpoint_run_trace_ref': f'navly:run-trace:endpoint-run:{endpoint_run_id}',
            'endpoint_contract_id': 'qinqin.staff.get_tech_commission_set_list.v1_8',
            'org_id': 'demo-org-001',
            'endpoint_status': endpoint_status,
            'terminal_outcome_category': terminal_outcome_category,
            'error_taxonomy': error_taxonomy,
            'error_code': error_code,
            'error_message': error_message,
        }

    def test_successful_surface_is_current_and_complete(self) -> None:
        surface = build_commission_setting_governance_surface(
            endpoint_run=self._endpoint_run(
                endpoint_status='completed',
                terminal_outcome_category='success',
            ),
            response_envelopes=[self._success_envelope()],
            requested_business_date='2026-03-23',
        )

        coverage = surface['quality_artifacts']['field_coverage_snapshot']
        schema_alignment = surface['quality_artifacts']['schema_alignment_snapshot']
        backfill = surface['latest_state_artifacts']['backfill_progress_state']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']

        self.assertEqual(coverage['coverage_status'], 'covered')
        self.assertEqual(coverage['coverage_ratio'], 1.0)
        self.assertEqual(schema_alignment['alignment_status'], 'aligned')
        self.assertEqual(backfill['currentness_status'], 'current')
        self.assertEqual(backfill['backfill_progress_status'], 'complete')
        self.assertEqual(completeness['completeness_status'], 'complete')
        self.assertEqual(surface['quality_artifacts']['quality_issues'], [])

    def test_source_empty_is_current_zero_row_state(self) -> None:
        surface = build_commission_setting_governance_surface(
            endpoint_run=self._endpoint_run(
                endpoint_status='source_empty',
                terminal_outcome_category='source_empty',
                endpoint_run_id='er_commission_empty',
            ),
            response_envelopes=[{
                'Code': 404,
                'Msg': '暂无数据',
                'RetData': [],
            }],
            requested_business_date='2026-03-23',
        )

        coverage = surface['quality_artifacts']['field_coverage_snapshot']
        schema_alignment = surface['quality_artifacts']['schema_alignment_snapshot']
        backfill = surface['latest_state_artifacts']['backfill_progress_state']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']
        issue_codes = [issue['issue_code'] for issue in surface['quality_artifacts']['quality_issues']]

        self.assertEqual(coverage['coverage_status'], 'source_empty_governed')
        self.assertEqual(coverage['dataset_row_counts']['commission_setting'], 0)
        self.assertEqual(schema_alignment['alignment_status'], 'source_empty_governed')
        self.assertEqual(backfill['currentness_status'], 'current')
        self.assertEqual(backfill['backfill_progress_status'], 'complete')
        self.assertEqual(completeness['completeness_status'], 'complete')
        self.assertEqual(completeness['reason_codes'], ['source_empty_current'])
        self.assertIn('source_empty_current_day_full_replace', issue_codes)

    def test_auth_failure_points_to_runtime_header_variance(self) -> None:
        surface = build_commission_setting_governance_surface(
            endpoint_run=self._endpoint_run(
                endpoint_status='failed',
                terminal_outcome_category='auth',
                error_taxonomy='source_auth_error',
                error_code='-401',
                error_message='未授权访问',
                endpoint_run_id='er_commission_auth',
            ),
            response_envelopes=[{
                'Code': -401,
                'Msg': '未授权访问',
            }],
            requested_business_date='2026-03-23',
        )

        coverage = surface['quality_artifacts']['field_coverage_snapshot']
        schema_alignment = surface['quality_artifacts']['schema_alignment_snapshot']
        backfill = surface['latest_state_artifacts']['backfill_progress_state']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']
        auth_issue = next(
            issue
            for issue in surface['quality_artifacts']['quality_issues']
            if issue['issue_code'] == 'upstream_auth_headers_required'
        )

        self.assertEqual(coverage['coverage_status'], 'blocked_upstream')
        self.assertEqual(schema_alignment['alignment_status'], 'blocked_upstream')
        self.assertEqual(backfill['currentness_status'], 'blocked')
        self.assertEqual(completeness['completeness_status'], 'blocked')
        self.assertIn(RUNTIME_HEADER_VARIANCE_ID, auth_issue['related_variance_ids'])

    def test_stale_target_business_date_uses_prior_latest_usable_state(self) -> None:
        sync_state_module = _load_sync_state_module()
        prior_state = sync_state_module.build_commission_setting_latest_usable_endpoint_state(
            endpoint_run=self._endpoint_run(
                endpoint_status='completed',
                terminal_outcome_category='success',
                endpoint_run_id='er_commission_prior',
            ),
            requested_business_date='2026-03-22',
        )

        surface = build_commission_setting_governance_surface(
            endpoint_run=self._endpoint_run(
                endpoint_status='failed',
                terminal_outcome_category='transport',
                error_taxonomy='transport_timeout_error',
                error_code='TIMEOUT',
                error_message='timed out while talking to qinqin',
                endpoint_run_id='er_commission_failed',
            ),
            response_envelopes=[],
            requested_business_date='2026-03-23',
            expected_business_dates=['2026-03-22', '2026-03-23'],
            prior_latest_usable_states=[prior_state],
        )

        backfill = surface['latest_state_artifacts']['backfill_progress_state']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']

        self.assertEqual(backfill['latest_usable_business_date'], '2026-03-22')
        self.assertEqual(backfill['currentness_status'], 'stale')
        self.assertEqual(backfill['backfill_progress_status'], 'incomplete')
        self.assertEqual(backfill['missing_business_dates'], ['2026-03-23'])
        self.assertEqual(completeness['completeness_status'], 'incomplete')
        self.assertEqual(completeness['reason_codes'], ['latest_state_stale'])

    def test_schema_alignment_flags_type_and_governance_gaps(self) -> None:
        malformed_envelope = self._success_envelope()
        malformed_envelope['RetData'][0]['ItemId'] = 425
        malformed_envelope['RetData'][0]['PCBaseList'][0]['CustomBonus'] = 88.0

        surface = build_commission_setting_governance_surface(
            endpoint_run=self._endpoint_run(
                endpoint_status='completed',
                terminal_outcome_category='success',
                endpoint_run_id='er_commission_misaligned',
            ),
            response_envelopes=[malformed_envelope],
            requested_business_date='2026-03-23',
        )

        schema_alignment = surface['quality_artifacts']['schema_alignment_snapshot']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']
        issue_codes = [issue['issue_code'] for issue in surface['quality_artifacts']['quality_issues']]

        self.assertEqual(schema_alignment['alignment_status'], 'misaligned')
        self.assertIn('RetData.PCBaseList.CustomBonus', schema_alignment['ungoverned_observed_field_paths'])
        item_id_mismatch = next(
            mismatch
            for mismatch in schema_alignment['mismatches']
            if mismatch['field_path'] == 'RetData.ItemId'
        )
        self.assertEqual(item_id_mismatch['reason'], 'observed_type_mismatch')
        self.assertEqual(completeness['completeness_status'], 'blocked')
        self.assertIn('schema_alignment_gap', issue_codes)


if __name__ == '__main__':
    unittest.main()
