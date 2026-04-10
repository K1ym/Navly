from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from completeness.readiness_surface_support import normalize_reason_codes, unique_strings
from projections.daily_overview_service_projection import DAILY_OVERVIEW_CAPABILITY_ID


def _component_entries(
    *,
    member_insight_owner_surface: dict[str, Any],
    staff_board_owner_surface: dict[str, Any],
    finance_summary_owner_surface: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            'capability_id': member_insight_owner_surface['readiness_response']['capability_id'],
            'service_object_id': member_insight_owner_surface['theme_service_response']['service_object_id'],
            'owner_surface': member_insight_owner_surface,
        },
        {
            'capability_id': staff_board_owner_surface['readiness_response']['capability_id'],
            'service_object_id': staff_board_owner_surface['theme_service_response']['service_object_id'],
            'owner_surface': staff_board_owner_surface,
        },
        {
            'capability_id': finance_summary_owner_surface['readiness_response']['capability_id'],
            'service_object_id': finance_summary_owner_surface['theme_service_response']['service_object_id'],
            'owner_surface': finance_summary_owner_surface,
        },
    ]


def build_daily_overview_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    member_insight_owner_surface: dict[str, Any],
    staff_board_owner_surface: dict[str, Any],
    finance_summary_owner_surface: dict[str, Any],
    requested_capability_id: str = DAILY_OVERVIEW_CAPABILITY_ID,
) -> dict[str, Any]:
    if requested_capability_id != DAILY_OVERVIEW_CAPABILITY_ID:
        return {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': requested_capability_id,
            'readiness_status': 'unsupported_scope',
            'evaluated_scope_ref': target_scope_ref,
            'requested_business_date': target_business_date,
            'latest_usable_business_date': target_business_date,
            'reason_codes': ['capability_scope_not_supported'],
            'blocking_dependencies': [],
            'state_trace_refs': [],
            'run_trace_refs': [],
            'evaluated_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'daily_overview',
            },
        }

    component_entries = _component_entries(
        member_insight_owner_surface=member_insight_owner_surface,
        staff_board_owner_surface=staff_board_owner_surface,
        finance_summary_owner_surface=finance_summary_owner_surface,
    )
    component_readiness = [
        entry['owner_surface']['readiness_response']
        for entry in component_entries
    ]
    blocking_entries = [
        entry
        for entry in component_entries
        if entry['owner_surface']['readiness_response']['readiness_status'] != 'ready'
    ]
    if not blocking_entries:
        readiness_status = 'ready'
        reason_codes: list[str] = []
    elif any(entry['owner_surface']['readiness_response']['readiness_status'] == 'failed' for entry in blocking_entries):
        readiness_status = 'failed'
        reason_codes = normalize_reason_codes(
            reason_code
            for entry in blocking_entries
            for reason_code in entry['owner_surface']['readiness_response'].get('reason_codes', [])
        )
    else:
        readiness_status = 'pending'
        reason_codes = normalize_reason_codes(
            reason_code
            for entry in blocking_entries
            for reason_code in entry['owner_surface']['readiness_response'].get('reason_codes', [])
        )
    latest_usable_business_date = min(
        readiness.get('latest_usable_business_date') or target_business_date
        for readiness in component_readiness
    )

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'readiness_status': readiness_status,
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'reason_codes': reason_codes,
        'blocking_dependencies': [
            {
                'dependency_kind': 'projection',
                'dependency_ref': entry['service_object_id'],
                'blocking_reason_code': (
                    entry['owner_surface']['readiness_response'].get('reason_codes', [])[0]
                    if entry['owner_surface']['readiness_response'].get('reason_codes')
                    else 'projection_not_available'
                ),
                'state_trace_refs': list(entry['owner_surface']['readiness_response'].get('state_trace_refs', [])),
                'run_trace_refs': list(entry['owner_surface']['readiness_response'].get('run_trace_refs', [])),
            }
            for entry in blocking_entries
        ],
        'state_trace_refs': unique_strings(
            state_trace_ref
            for readiness in component_readiness
            for state_trace_ref in readiness.get('state_trace_refs', [])
        ),
        'run_trace_refs': unique_strings(
            run_trace_ref
            for readiness in component_readiness
            for run_trace_ref in readiness.get('run_trace_refs', [])
        ),
        'evaluated_at': max(
            [readiness.get('evaluated_at') for readiness in component_readiness if readiness.get('evaluated_at')]
            or [utcnow_iso()]
        ),
        'extensions': {
            'owner_surface': 'daily_overview',
            'required_capability_ids': [entry['capability_id'] for entry in component_entries],
            'required_service_object_ids': [entry['service_object_id'] for entry in component_entries],
        },
    }
