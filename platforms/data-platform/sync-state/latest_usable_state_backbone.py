from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def build_state_trace_ref(state_type: str, state_id: str) -> str:
    return f'navly:state-trace:{state_type}:{state_id}'


def build_latest_usable_endpoint_states(
    endpoint_runs: list[dict[str, Any]],
    source_system_id: str,
    requested_business_date: str,
) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for endpoint_run in endpoint_runs:
        endpoint_status = endpoint_run['endpoint_status']
        availability_status = (
            'available' if endpoint_status == 'completed'
            else 'source_empty' if endpoint_status == 'source_empty'
            else 'unavailable'
        )
        state_id = f"{endpoint_run['endpoint_contract_id']}::{endpoint_run['org_id']}::{requested_business_date}"
        states.append({
            'state_id': state_id,
            'state_trace_ref': build_state_trace_ref('latest-usable-endpoint-state', state_id),
            'source_system_id': source_system_id,
            'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
            'org_id': endpoint_run['org_id'],
            'latest_usable_business_date': requested_business_date if availability_status in {'available', 'source_empty'} else None,
            'availability_status': availability_status,
            'latest_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
            'latest_endpoint_run_id': endpoint_run['endpoint_run_id'],
            'latest_endpoint_status': endpoint_status,
            'updated_at': utcnow_iso(),
        })
    return states


def build_vertical_slice_backbone_state(
    capability_id: str,
    service_object_id: str,
    requested_business_date: str,
    latest_usable_endpoint_states: list[dict[str, Any]],
) -> dict[str, Any]:
    available_endpoint_ids = [
        state['endpoint_contract_id']
        for state in latest_usable_endpoint_states
        if state['availability_status'] in {'available', 'source_empty'}
    ]
    backbone_ready = len(available_endpoint_ids) == len(latest_usable_endpoint_states) and bool(latest_usable_endpoint_states)
    state_id = f'{capability_id}::{requested_business_date}'
    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('vertical-slice-backbone-state', state_id),
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'requested_business_date': requested_business_date,
        'backbone_status': 'backbone_ready' if backbone_ready else 'backbone_incomplete',
        'available_endpoint_contract_ids': available_endpoint_ids,
        'updated_at': utcnow_iso(),
    }
