from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from backbone_support.qinqin_phase1_owner_surface_registry import owner_surface_name


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
        blocking_reason_code = (
            'dependency_failed'
            if endpoint_run.get('endpoint_status') == 'failed'
            else 'missing_dependency'
        )
        blocking.append({
            'dependency_kind': 'input_data',
            'dependency_ref': state['endpoint_contract_id'],
            'blocking_reason_code': blocking_reason_code,
            'state_trace_refs': [state['state_trace_ref']],
            'run_trace_refs': [endpoint_run['endpoint_run_trace_ref']] if endpoint_run.get('endpoint_run_trace_ref') else [],
        })
    return blocking


def build_qinqin_phase1_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str,
) -> dict[str, Any]:
    capability_id = vertical_slice_result['capability_id']
    owner_surface = owner_surface_name(capability_id)
    if requested_capability_id != capability_id:
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
                'owner_surface': owner_surface,
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
    latest_usable_business_date = min(latest_usable_dates) if latest_usable_dates else target_business_date
    has_failed_dependency = any(
        endpoint_run.get('endpoint_status') == 'failed'
        for endpoint_run in vertical_slice_result['historical_run_truth']['endpoint_runs']
    )

    if backbone_state['backbone_status'] == 'backbone_ready':
        readiness_status = 'ready'
        reason_codes: list[str] = []
    elif has_failed_dependency:
        readiness_status = 'failed'
        reason_codes = ['dependency_failed']
    else:
        readiness_status = 'pending'
        reason_codes = ['missing_dependency']

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
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
            'owner_surface': owner_surface,
            'transport_kind': vertical_slice_result.get('transport_kind'),
            'available_endpoint_contract_ids': backbone_state.get('available_endpoint_contract_ids', []),
        },
    }

