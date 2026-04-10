from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from completeness.readiness_surface_support import (
    endpoint_run_trace_refs,
    latest_state_trace_refs,
    latest_usable_business_date_from_states,
)
from ingestion.finance_summary_vertical_slice import FINANCE_SUMMARY_CAPABILITY_ID


def _blocking_dependencies(vertical_slice_result: dict[str, Any]) -> list[dict[str, Any]]:
    latest_states = vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']
    latest_states_by_id = {
        state['endpoint_contract_id']: state
        for state in latest_states
    }
    endpoint_runs_by_id = {
        endpoint_run['endpoint_contract_id']: endpoint_run
        for endpoint_run in vertical_slice_result['historical_run_truth']['endpoint_runs']
    }
    blocking_dependencies: list[dict[str, Any]] = []
    for dependency in vertical_slice_result['latest_state_artifacts']['finance_summary_prerequisite_state']['blocking_dependencies']:
        endpoint_contract_id = dependency['endpoint_contract_id']
        state = latest_states_by_id.get(endpoint_contract_id, {})
        endpoint_run = endpoint_runs_by_id.get(endpoint_contract_id, {})
        blocking_reason_code = (
            'upstream_error'
            if dependency.get('failure_taxonomy') or dependency.get('blocking_category')
            else 'required_dataset_missing'
        )
        blocking_dependencies.append({
            'dependency_kind': 'input_data',
            'dependency_ref': endpoint_contract_id,
            'blocking_reason_code': blocking_reason_code,
            'state_trace_refs': [state['state_trace_ref']] if state.get('state_trace_ref') else [],
            'run_trace_refs': [endpoint_run['endpoint_run_trace_ref']] if endpoint_run.get('endpoint_run_trace_ref') else [],
        })
    return blocking_dependencies


def build_finance_summary_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = FINANCE_SUMMARY_CAPABILITY_ID,
) -> dict[str, Any]:
    if requested_capability_id != FINANCE_SUMMARY_CAPABILITY_ID:
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
                'owner_surface': 'finance_summary',
            },
        }

    latest_states = vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']
    prerequisite_state = vertical_slice_result['latest_state_artifacts']['finance_summary_prerequisite_state']
    if not latest_states:
        readiness_status = 'pending'
        reason_codes = ['latest_state_not_published']
    elif prerequisite_state['prerequisite_status'] == 'ready':
        readiness_status = 'ready'
        reason_codes = []
    elif prerequisite_state['blocking_dependencies']:
        readiness_status = 'failed'
        reason_codes = ['upstream_error']
    else:
        readiness_status = 'failed'
        reason_codes = ['required_dataset_missing']

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': FINANCE_SUMMARY_CAPABILITY_ID,
        'readiness_status': readiness_status,
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date_from_states(latest_states, target_business_date),
        'reason_codes': reason_codes,
        'blocking_dependencies': _blocking_dependencies(vertical_slice_result),
        'state_trace_refs': latest_state_trace_refs(prerequisite_state, latest_states),
        'run_trace_refs': endpoint_run_trace_refs(vertical_slice_result),
        'evaluated_at': prerequisite_state.get('updated_at') or utcnow_iso(),
        'extensions': {
            'owner_surface': 'finance_summary',
            'transport_kind': vertical_slice_result.get('transport_kind'),
            'ready_endpoint_contract_ids': list(prerequisite_state.get('ready_endpoint_contract_ids', [])),
            'source_empty_endpoint_contract_ids': list(prerequisite_state.get('source_empty_endpoint_contract_ids', [])),
        },
    }
