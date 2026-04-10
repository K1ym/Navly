from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def build_state_trace_ref(state_type: str, state_id: str) -> str:
    return f'navly:state-trace:{state_type}:{state_id}'


def _observed_outcome_category(endpoint_run: dict[str, Any]) -> str:
    terminal_outcome_category = endpoint_run.get('terminal_outcome_category')
    if terminal_outcome_category:
        return str(terminal_outcome_category)
    endpoint_status = endpoint_run['endpoint_status']
    if endpoint_status == 'completed':
        return 'success'
    if endpoint_status == 'source_empty':
        return 'source_empty'
    return 'unknown'


def build_finance_summary_latest_usable_endpoint_states(
    *,
    endpoint_runs: list[dict[str, Any]],
    source_system_id: str,
    requested_business_date: str,
) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for endpoint_run in endpoint_runs:
        endpoint_status = endpoint_run['endpoint_status']
        availability_status = (
            'available'
            if endpoint_status == 'completed'
            else 'source_empty'
            if endpoint_status == 'source_empty'
            else 'unavailable'
        )
        observed_outcome_category = _observed_outcome_category(endpoint_run)
        is_usable = availability_status in {'available', 'source_empty'}
        state_id = f"{endpoint_run['endpoint_contract_id']}::{endpoint_run['org_id']}::{requested_business_date}"
        states.append({
            'state_id': state_id,
            'state_trace_ref': build_state_trace_ref('latest-usable-endpoint-state', state_id),
            'source_system_id': source_system_id,
            'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
            'org_id': endpoint_run['org_id'],
            'requested_business_date': requested_business_date,
            'availability_status': availability_status,
            'latest_observed_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
            'latest_observed_endpoint_run_id': endpoint_run['endpoint_run_id'],
            'latest_observed_endpoint_status': endpoint_status,
            'latest_observed_outcome_category': observed_outcome_category,
            'latest_usable_business_date': requested_business_date if is_usable else None,
            'latest_usable_run_trace_ref': endpoint_run['endpoint_run_trace_ref'] if is_usable else None,
            'latest_usable_endpoint_run_id': endpoint_run['endpoint_run_id'] if is_usable else None,
            'latest_usable_outcome_category': observed_outcome_category if is_usable else None,
            'blocking_category': None if is_usable else observed_outcome_category,
            'failure_taxonomy': endpoint_run.get('error_taxonomy'),
            'failure_code': endpoint_run.get('error_code'),
            'failure_message': endpoint_run.get('error_message'),
            'updated_at': utcnow_iso(),
        })
    return states


def build_finance_summary_prerequisite_state(
    *,
    capability_id: str,
    service_object_id: str,
    requested_business_date: str,
    latest_usable_endpoint_states: list[dict[str, Any]],
) -> dict[str, Any]:
    ready_endpoint_contract_ids = [
        state['endpoint_contract_id']
        for state in latest_usable_endpoint_states
        if state['availability_status'] in {'available', 'source_empty'}
    ]
    source_empty_endpoint_contract_ids = [
        state['endpoint_contract_id']
        for state in latest_usable_endpoint_states
        if state['availability_status'] == 'source_empty'
    ]
    blocking_dependencies = [
        {
            'endpoint_contract_id': state['endpoint_contract_id'],
            'availability_status': state['availability_status'],
            'blocking_category': state['blocking_category'],
            'failure_taxonomy': state['failure_taxonomy'],
            'failure_code': state['failure_code'],
            'failure_message': state['failure_message'],
            'latest_observed_run_trace_ref': state['latest_observed_run_trace_ref'],
            'latest_observed_endpoint_run_id': state['latest_observed_endpoint_run_id'],
        }
        for state in latest_usable_endpoint_states
        if state['availability_status'] == 'unavailable'
    ]
    all_ready = len(ready_endpoint_contract_ids) == len(latest_usable_endpoint_states) and bool(latest_usable_endpoint_states)
    state_id = f'{capability_id}::{requested_business_date}'
    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('finance-summary-prerequisite-state', state_id),
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'requested_business_date': requested_business_date,
        'backbone_status': 'backbone_ready' if all_ready else 'backbone_incomplete',
        'prerequisite_status': 'ready' if all_ready else 'blocked',
        'required_endpoint_contract_ids': [
            state['endpoint_contract_id']
            for state in latest_usable_endpoint_states
        ],
        'ready_endpoint_contract_ids': ready_endpoint_contract_ids,
        'source_empty_endpoint_contract_ids': source_empty_endpoint_contract_ids,
        'blocking_endpoint_contract_ids': [
            dependency['endpoint_contract_id']
            for dependency in blocking_dependencies
        ],
        'blocking_dependencies': blocking_dependencies,
        'updated_at': utcnow_iso(),
    }


__all__ = [
    'build_finance_summary_latest_usable_endpoint_states',
    'build_finance_summary_prerequisite_state',
    'build_state_trace_ref',
    'utcnow_iso',
]
