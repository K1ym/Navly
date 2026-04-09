from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from ingestion.member_insight_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _run_trace_refs(vertical_slice_result: dict[str, Any]) -> list[str]:
    ingestion_run = vertical_slice_result['historical_run_truth']['ingestion_run']
    endpoint_runs = vertical_slice_result['historical_run_truth']['endpoint_runs']
    return _unique_strings([
        ingestion_run.get('run_trace_ref'),
        *[endpoint_run.get('endpoint_run_trace_ref') for endpoint_run in endpoint_runs],
    ])


def _state_trace_refs(vertical_slice_result: dict[str, Any]) -> list[str]:
    latest_states = vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']
    backbone_state = vertical_slice_result['latest_state_artifacts']['vertical_slice_backbone_state']
    return _unique_strings([
        backbone_state.get('state_trace_ref'),
        *[state.get('state_trace_ref') for state in latest_states],
    ])


def _blocking_dependencies(vertical_slice_result: dict[str, Any]) -> list[dict[str, Any]]:
    latest_states = vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']
    endpoint_runs_by_id = {
        endpoint_run['endpoint_contract_id']: endpoint_run
        for endpoint_run in vertical_slice_result['historical_run_truth']['endpoint_runs']
    }
    blocking: list[dict[str, Any]] = []
    for state in latest_states:
        if state['availability_status'] in {'available', 'source_empty'}:
            continue
        endpoint_run = endpoint_runs_by_id.get(state['endpoint_contract_id'], {})
        blocking.append({
            'dependency_kind': 'input_data',
            'dependency_ref': state['endpoint_contract_id'],
            'blocking_reason_code': 'missing_dependency',
            'state_trace_refs': [state['state_trace_ref']],
            'run_trace_refs': [endpoint_run['endpoint_run_trace_ref']] if endpoint_run.get('endpoint_run_trace_ref') else [],
        })
    return blocking


def build_member_insight_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
) -> dict[str, Any]:
    if requested_capability_id != VERTICAL_SLICE_CAPABILITY_ID:
        return {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': requested_capability_id,
            'readiness_status': 'unsupported_scope',
            'evaluated_scope_ref': target_scope_ref,
            'requested_business_date': target_business_date,
            'latest_usable_business_date': target_business_date,
            'reason_codes': ['capability_not_registered'],
            'blocking_dependencies': [],
            'state_trace_refs': [],
            'run_trace_refs': [],
            'evaluated_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
            },
        }

    latest_states = vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']
    backbone_state = vertical_slice_result['latest_state_artifacts']['vertical_slice_backbone_state']
    blocking_dependencies = _blocking_dependencies(vertical_slice_result)
    latest_usable_dates = _unique_strings([
        state.get('latest_usable_business_date')
        for state in latest_states
        if state.get('latest_usable_business_date')
    ])
    latest_usable_business_date = latest_usable_dates[0] if latest_usable_dates else target_business_date

    if backbone_state['backbone_status'] == 'backbone_ready':
        readiness_status = 'ready'
        reason_codes: list[str] = []
    else:
        readiness_status = 'pending'
        reason_codes = ['missing_dependency']

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'readiness_status': readiness_status,
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'reason_codes': reason_codes,
        'blocking_dependencies': blocking_dependencies,
        'state_trace_refs': _state_trace_refs(vertical_slice_result),
        'run_trace_refs': _run_trace_refs(vertical_slice_result),
        'evaluated_at': backbone_state['updated_at'],
        'extensions': {
            'owner_surface': 'member_insight',
            'transport_kind': vertical_slice_result.get('transport_kind'),
            'available_endpoint_contract_ids': backbone_state.get('available_endpoint_contract_ids', []),
        },
    }
