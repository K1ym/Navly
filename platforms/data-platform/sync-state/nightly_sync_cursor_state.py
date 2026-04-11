from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso


def _cursor_reason_codes(
    *,
    currentness_status: str,
    backfill_progress_status: str,
) -> list[str]:
    reason_codes: list[str] = []
    if currentness_status != 'current':
        reason_codes.append('target_business_date_not_current')
    if backfill_progress_status == 'incomplete':
        reason_codes.append('historical_backfill_gap')
    elif backfill_progress_status == 'blocked':
        reason_codes.append('backfill_blocked')
    return reason_codes


def _cursor_status(
    *,
    next_currentness_business_date: str | None,
    next_backfill_business_date: str | None,
    currentness_status: str,
    backfill_progress_status: str,
) -> str:
    if next_currentness_business_date:
        return 'currentness_pending'
    if next_backfill_business_date:
        return 'backfill_pending'
    if currentness_status == 'current' and backfill_progress_status in {'complete', 'not_applicable'}:
        return 'current_and_complete'
    if backfill_progress_status == 'blocked':
        return 'blocked'
    return 'waiting_for_next_cycle'


def build_nightly_sync_cursor_state(
    *,
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    endpoint_plan: dict[str, Any],
    carry_forward_cursor: bool,
    backfill_fill_direction: str,
) -> dict[str, Any]:
    endpoint_contract_id = endpoint_plan['endpoint_contract_id']
    currentness_status = endpoint_plan['currentness_status']
    backfill_progress_status = endpoint_plan['backfill_progress_status']
    next_currentness_business_date = (
        target_business_date if currentness_status != 'current' else None
    )
    next_backfill_business_date = endpoint_plan.get('recommended_next_backfill_business_date')
    state_id = (
        f'{source_system_id}::{org_id}::{endpoint_contract_id}::{target_business_date}'
        '::nightly-sync-cursor'
    )

    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('nightly-sync-cursor-state', state_id),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'endpoint_contract_id': endpoint_contract_id,
        'target_business_date': target_business_date,
        'currentness_status': currentness_status,
        'backfill_progress_status': backfill_progress_status,
        'cursor_status': _cursor_status(
            next_currentness_business_date=next_currentness_business_date,
            next_backfill_business_date=next_backfill_business_date,
            currentness_status=currentness_status,
            backfill_progress_status=backfill_progress_status,
        ),
        'cursor_reason_codes': _cursor_reason_codes(
            currentness_status=currentness_status,
            backfill_progress_status=backfill_progress_status,
        ),
        'latest_usable_business_date': endpoint_plan.get('latest_usable_business_date'),
        'covered_business_dates': list(endpoint_plan.get('covered_business_dates', [])),
        'missing_business_dates': list(endpoint_plan.get('missing_business_dates', [])),
        'currentness_window_business_dates': list(
            endpoint_plan.get('currentness_window_business_dates', [])
        ),
        'next_currentness_business_date': next_currentness_business_date,
        'next_backfill_business_date': next_backfill_business_date,
        'carry_forward_cursor': carry_forward_cursor,
        'backfill_fill_direction': backfill_fill_direction,
        'updated_at': utcnow_iso(),
    }


def build_nightly_sync_cursor_states(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        build_nightly_sync_cursor_state(
            source_system_id=plan['source_system_id'],
            org_id=plan['org_id'],
            target_business_date=plan['target_business_date'],
            endpoint_plan=endpoint_plan,
            carry_forward_cursor=bool(plan['carry_forward_cursor']),
            backfill_fill_direction=plan['backfill_fill_direction'],
        )
        for endpoint_plan in plan['endpoint_plans']
    ]


__all__ = [
    'build_nightly_sync_cursor_state',
    'build_nightly_sync_cursor_states',
]
