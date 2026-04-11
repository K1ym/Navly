from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso


def _ledger_entry_id(
    *,
    source_system_id: str,
    org_id: str,
    endpoint_contract_id: str,
    target_business_date: str,
) -> str:
    return f'{source_system_id}::{org_id}::{endpoint_contract_id}::{target_business_date}::nightly-sync-ledger'


def build_nightly_sync_cursor_ledger_entry(
    cursor_state: dict[str, Any],
    *,
    prior_ledger_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_system_id = cursor_state['source_system_id']
    org_id = cursor_state['org_id']
    endpoint_contract_id = cursor_state['endpoint_contract_id']
    target_business_date = cursor_state['target_business_date']
    ledger_entry_id = _ledger_entry_id(
        source_system_id=source_system_id,
        org_id=org_id,
        endpoint_contract_id=endpoint_contract_id,
        target_business_date=target_business_date,
    )

    prior_completed_business_date = (
        prior_ledger_entry.get('last_completed_business_date')
        if prior_ledger_entry
        else None
    )
    last_completed_business_date = (
        cursor_state.get('latest_usable_business_date') or prior_completed_business_date
    )
    pending_business_dates: list[str] = []
    if cursor_state.get('next_currentness_business_date'):
        pending_business_dates.append(cursor_state['next_currentness_business_date'])
    next_backfill_business_date = cursor_state.get('next_backfill_business_date')
    if next_backfill_business_date and next_backfill_business_date not in pending_business_dates:
        pending_business_dates.append(next_backfill_business_date)

    return {
        'ledger_entry_id': ledger_entry_id,
        'ledger_trace_ref': build_state_trace_ref('nightly-sync-cursor-ledger', ledger_entry_id),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'endpoint_contract_id': endpoint_contract_id,
        'target_business_date': target_business_date,
        'cursor_status': cursor_state['cursor_status'],
        'last_completed_business_date': last_completed_business_date,
        'last_attempted_business_date': (
            cursor_state.get('next_currentness_business_date')
            or next_backfill_business_date
            or last_completed_business_date
        ),
        'next_currentness_business_date': cursor_state.get('next_currentness_business_date'),
        'next_backfill_business_date': next_backfill_business_date,
        'covered_business_dates': list(cursor_state.get('covered_business_dates', [])),
        'pending_business_dates': pending_business_dates,
        'carry_forward_cursor': bool(cursor_state['carry_forward_cursor']),
        'backfill_fill_direction': cursor_state['backfill_fill_direction'],
        'updated_at': utcnow_iso(),
    }


def build_nightly_sync_cursor_ledger(
    cursor_states: list[dict[str, Any]],
    *,
    prior_ledger_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prior_by_endpoint = {
        (
            entry['source_system_id'],
            entry['org_id'],
            entry['endpoint_contract_id'],
            entry['target_business_date'],
        ): entry
        for entry in (prior_ledger_entries or [])
    }
    entries = []
    for cursor_state in cursor_states:
        key = (
            cursor_state['source_system_id'],
            cursor_state['org_id'],
            cursor_state['endpoint_contract_id'],
            cursor_state['target_business_date'],
        )
        entries.append(
            build_nightly_sync_cursor_ledger_entry(
                cursor_state,
                prior_ledger_entry=prior_by_endpoint.get(key),
            )
        )

    source_system_id = cursor_states[0]['source_system_id'] if cursor_states else ''
    org_id = cursor_states[0]['org_id'] if cursor_states else ''
    target_business_date = cursor_states[0]['target_business_date'] if cursor_states else ''
    ledger_id = f'{source_system_id}::{org_id}::{target_business_date}::nightly-sync-ledger'
    return {
        'ledger_id': ledger_id,
        'ledger_trace_ref': build_state_trace_ref('nightly-sync-ledger', ledger_id),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'target_business_date': target_business_date,
        'entry_count': len(entries),
        'entries': entries,
        'updated_at': utcnow_iso(),
    }


def build_latest_usable_states_from_cursor_ledger_entries(
    ledger_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for entry in ledger_entries:
        latest_usable_business_date = entry.get('last_completed_business_date')
        if not latest_usable_business_date:
            continue
        state_id = (
            f"{entry['endpoint_contract_id']}::{entry['org_id']}::{entry['target_business_date']}"
        )
        states.append({
            'state_id': state_id,
            'state_trace_ref': build_state_trace_ref('latest-usable-endpoint-state', state_id),
            'source_system_id': entry['source_system_id'],
            'endpoint_contract_id': entry['endpoint_contract_id'],
            'org_id': entry['org_id'],
            'latest_usable_business_date': latest_usable_business_date,
            'availability_status': 'available',
            'latest_run_trace_ref': entry['ledger_trace_ref'],
            'latest_endpoint_run_id': entry['ledger_entry_id'],
            'latest_endpoint_status': 'completed',
            'updated_at': entry['updated_at'],
        })
    return states


__all__ = [
    'build_nightly_sync_cursor_ledger',
    'build_nightly_sync_cursor_ledger_entry',
    'build_latest_usable_states_from_cursor_ledger_entries',
]
