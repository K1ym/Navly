from __future__ import annotations

import argparse
import json
from copy import deepcopy
from typing import Any

VALIDATION_STATUS_FIXTURE_ONLY = 'fixture-only'
VALIDATION_STATUS_LIVE_VALIDATED = 'live-validated'
EXPECTED_CLASSIFICATION_PATHS = (
    'source_empty',
    'auth',
    'sign',
    'schema',
    'transport',
)
SAFE_ENTRYPOINT = 'bash scripts/validate-remaining-phase1-live-transport.sh'

REMAINING_ENDPOINT_ROWS: list[dict[str, Any]] = [
    {
        'slice_id': 'finance_summary',
        'capability_id': 'navly.store.finance_summary',
        'service_object_id': 'navly.service.store.finance_summary',
        'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
        'dataset_short_name': 'recharge',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'response_received',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': (
            'Recharge shares the finance_summary live loopback harness with account_trade. '
            'The row is live-validated because LiveQinqinTransport exercises the real HTTP path.'
        ),
    },
    {
        'slice_id': 'finance_summary',
        'capability_id': 'navly.store.finance_summary',
        'service_object_id': 'navly.service.store.finance_summary',
        'endpoint_contract_id': 'qinqin.member.get_user_trade_list.v1_4',
        'dataset_short_name': 'account_trade',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'source_empty',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': 'account_trade keeps the explicit source_empty live path and the full classification matrix.',
    },
    {
        'slice_id': 'staff_board',
        'capability_id': 'navly.store.staff_board',
        'service_object_id': 'navly.service.store.staff_board',
        'endpoint_contract_id': 'qinqin.staff.get_person_list.v1_5',
        'dataset_short_name': 'person',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'response_received',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_staff_board_loopback_live_transport_paths'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_schema_error_is_classified'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': 'person uses the staff_board vertical slice and now exercises LiveQinqinTransport through the loopback harness.',
    },
    {
        'slice_id': 'staff_board',
        'capability_id': 'navly.store.staff_board',
        'service_object_id': 'navly.service.store.staff_board',
        'endpoint_contract_id': 'qinqin.staff.get_tech_up_clock_list.v1_6',
        'dataset_short_name': 'clock',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'response_received',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_staff_board_loopback_live_transport_paths'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_auth_error_is_classified'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': 'clock keeps endpoint-specific body-parameter coverage while validating the live HTTP path.',
    },
    {
        'slice_id': 'staff_board',
        'capability_id': 'navly.store.staff_board',
        'service_object_id': 'navly.service.store.staff_board',
        'endpoint_contract_id': 'qinqin.staff.get_tech_market_list.v1_7',
        'dataset_short_name': 'market',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'response_received',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_staff_board_loopback_live_transport_paths'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_sign_error_is_classified'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': (
            'market is live-validated on the successful LiveQinqinTransport path. '
            'Its source_empty classification stays explicit, but today that classification is still frozen by fixture regression.'
        ),
    },
    {
        'slice_id': 'commission_setting',
        'capability_id': None,
        'service_object_id': None,
        'endpoint_contract_id': 'qinqin.staff.get_tech_commission_set_list.v1_8',
        'dataset_short_name': 'commission',
        'validation_status': VALIDATION_STATUS_LIVE_VALIDATED,
        'live_transport_harness': 'loopback_live_transport',
        'current_live_exercised_path': 'source_empty',
        'loopback_live_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_commission_setting_loopback_live_transport_source_empty_path'
        ),
        'classification_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_commission_setting_sign_classification_stays_distinct_from_auth'
        ),
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'notes': (
            'commission is an endpoint-scoped governance surface, not a published capability/service binding. '
            'The live-validated row only claims loopback LiveQinqinTransport execution, not upstream credential proof.'
        ),
    },
]

ADJACENT_FIXTURE_ONLY_SURFACES: list[dict[str, Any]] = [
    {
        'surface_id': 'navly.store.daily_overview',
        'validation_status': VALIDATION_STATUS_FIXTURE_ONLY,
        'evidence': 'platforms/data-platform/tests/test_daily_overview_owner_surface.py',
        'notes': 'daily_overview is an aggregate projection surface and does not own direct Qinqin transport.',
    },
    {
        'surface_id': 'navly.system.capability_explanation',
        'validation_status': VALIDATION_STATUS_FIXTURE_ONLY,
        'evidence': 'platforms/data-platform/tests/test_capability_explanation_owner_surface.py',
        'notes': 'capability_explanation consumes owner surfaces and remains fixture-only for this ASP.',
    },
]

EXPECTED_CLASSIFICATION_ROWS: list[dict[str, str]] = [
    {
        'surface_id': 'finance_summary',
        'classification_path': 'source_empty',
        'authoritative_signal': (
            'endpoint_status=source_empty; terminal_outcome_category=source_empty; '
            'latest_usable_endpoint_state.availability_status=source_empty'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure'
        ),
    },
    {
        'surface_id': 'finance_summary',
        'classification_path': 'auth',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=auth; '
            'error_taxonomy=source_auth_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
    },
    {
        'surface_id': 'finance_summary',
        'classification_path': 'sign',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=sign; '
            'error_taxonomy=source_sign_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
    },
    {
        'surface_id': 'finance_summary',
        'classification_path': 'schema',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=schema; '
            'error_taxonomy=source_schema_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
    },
    {
        'surface_id': 'finance_summary',
        'classification_path': 'transport',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=transport; '
            'error_taxonomy=transport_timeout_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_finance_summary_vertical_slice.py::'
            'test_finance_summary_classifies_sign_auth_schema_and_transport'
        ),
    },
    {
        'surface_id': 'staff_board',
        'classification_path': 'source_empty',
        'authoritative_signal': (
            'endpoint_status=source_empty; latest_usable_endpoint_state.availability_status=source_empty; '
            'vertical_slice_backbone_state.backbone_status=backbone_ready'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_empty_is_latest_usable_and_keeps_backbone_ready'
        ),
    },
    {
        'surface_id': 'staff_board',
        'classification_path': 'auth',
        'authoritative_signal': (
            'endpoint_status=failed; error_taxonomy=source_auth_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_auth_error_is_classified'
        ),
    },
    {
        'surface_id': 'staff_board',
        'classification_path': 'sign',
        'authoritative_signal': (
            'endpoint_status=failed; error_taxonomy=source_sign_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_sign_error_is_classified'
        ),
    },
    {
        'surface_id': 'staff_board',
        'classification_path': 'schema',
        'authoritative_signal': (
            'endpoint_status=failed; error_taxonomy=source_schema_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_source_schema_error_is_classified'
        ),
    },
    {
        'surface_id': 'staff_board',
        'classification_path': 'transport',
        'authoritative_signal': (
            'endpoint_status=failed; error_taxonomy=transport_timeout_error'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_staff_board_vertical_slice.py::'
            'test_transport_error_is_classified'
        ),
    },
    {
        'surface_id': 'commission_setting',
        'classification_path': 'source_empty',
        'authoritative_signal': (
            'endpoint_status=source_empty; terminal_outcome_category=source_empty; '
            'field_coverage_snapshot.coverage_status=source_empty_governed; '
            'commission_setting_completeness_state.reason_codes=source_empty_current'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_commission_setting_governance_surface.py::'
            'test_source_empty_is_current_zero_row_state'
        ),
    },
    {
        'surface_id': 'commission_setting',
        'classification_path': 'auth',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=auth; '
            'error_taxonomy=source_auth_error; schema_alignment_snapshot.alignment_status=blocked_upstream'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_commission_setting_governance_surface.py::'
            'test_auth_failure_points_to_runtime_header_variance'
        ),
    },
    {
        'surface_id': 'commission_setting',
        'classification_path': 'sign',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=sign; '
            'error_taxonomy=source_sign_error; schema_alignment_snapshot.alignment_status=blocked_upstream'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::'
            'test_commission_setting_sign_classification_stays_distinct_from_auth'
        ),
    },
    {
        'surface_id': 'commission_setting',
        'classification_path': 'schema',
        'authoritative_signal': (
            'endpoint_status=completed; terminal_outcome_category=success; '
            'schema_alignment_snapshot.alignment_status=misaligned; '
            'commission_setting_completeness_state.completeness_status=blocked'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_commission_setting_governance_surface.py::'
            'test_schema_alignment_flags_type_and_governance_gaps'
        ),
    },
    {
        'surface_id': 'commission_setting',
        'classification_path': 'transport',
        'authoritative_signal': (
            'endpoint_status=failed; terminal_outcome_category=transport; '
            'error_taxonomy=transport_timeout_error; '
            'commission_setting_completeness_state.reason_codes=latest_state_stale'
        ),
        'mechanical_evidence': (
            'platforms/data-platform/tests/test_commission_setting_governance_surface.py::'
            'test_stale_target_business_date_uses_prior_latest_usable_state'
        ),
    },
]


def build_phase1_remaining_live_transport_validation_matrix() -> dict[str, Any]:
    return {
        'matrix_name': 'phase_1_remaining_qinqin_live_transport_validation_matrix',
        'status': 'phase_1_verification_governed',
        'safe_entrypoint': SAFE_ENTRYPOINT,
        'status_vocabulary': {
            VALIDATION_STATUS_FIXTURE_ONLY: (
                'Only FixtureQinqinTransport or aggregate fixture surfaces are covered. '
                'No LiveQinqinTransport loopback evidence exists yet.'
            ),
            VALIDATION_STATUS_LIVE_VALIDATED: (
                'The real LiveQinqinTransport HTTP code path is exercised through a loopback harness. '
                'This is bounded live transport validation, not a claim about upstream credential success.'
            ),
        },
        'expected_classification_paths': list(EXPECTED_CLASSIFICATION_PATHS),
        'remaining_endpoint_rows': deepcopy(REMAINING_ENDPOINT_ROWS),
        'adjacent_fixture_only_surfaces': deepcopy(ADJACENT_FIXTURE_ONLY_SURFACES),
        'classification_matrix': deepcopy(EXPECTED_CLASSIFICATION_ROWS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Print the governed remaining Phase-1 Qinqin live transport validation matrix.'
    )
    parser.add_argument(
        '--format',
        choices=('json',),
        default='json',
        help='Output format. Only json is currently supported.',
    )
    args = parser.parse_args()
    if args.format != 'json':
        raise ValueError(f'Unsupported format: {args.format}')
    print(json.dumps(build_phase1_remaining_live_transport_validation_matrix(), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
