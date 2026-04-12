from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso
from backbone_support.qinqin_phase1_owner_surface_registry import (
    DAILY_OVERVIEW_CAPABILITY_ID,
    FINANCE_SUMMARY_CAPABILITY_ID,
    MEMBER_INSIGHT_CAPABILITY_ID,
    STAFF_BOARD_CAPABILITY_ID,
)
from directory.business_day_boundary_policy_registry import resolve_business_day_boundary_policy
from serving.persisted_owner_surface_snapshot_store import PersistedOwnerSurfaceSnapshotStore
from workflows.daily_overview_owner_surface import _build_daily_overview_owner_surface
from workflows.finance_summary_owner_surface import _build_finance_summary_owner_surface
from workflows.member_insight_owner_surface import _build_member_insight_owner_surface
from workflows.staff_board_owner_surface import _build_staff_board_owner_surface


COMPONENT_CAPABILITY_IDS = (
    MEMBER_INSIGHT_CAPABILITY_ID,
    FINANCE_SUMMARY_CAPABILITY_ID,
    STAFF_BOARD_CAPABILITY_ID,
)


def _request_id(capability_id: str, org_id: str, business_date: str) -> str:
    return f'persisted-owner-surface::{capability_id}::{org_id}::{business_date}'


def _trace_ref(capability_id: str, org_id: str, business_date: str) -> str:
    request_id = _request_id(capability_id, org_id, business_date)
    return build_state_trace_ref('persisted-owner-surface', request_id)


def _scope_ref(org_id: str) -> str:
    return f'navly:scope:store:{org_id}'


def _snapshot_bundle(
    *,
    org_id: str,
    business_date: str,
    capability_id: str,
    owner_surface_result: dict[str, Any],
) -> dict[str, Any]:
    theme_service_response = owner_surface_result['theme_service_response']
    return {
        'org_id': org_id,
        'target_scope_ref': _scope_ref(org_id),
        'snapshot_business_date': business_date,
        'capability_id': capability_id,
        'service_object_id': theme_service_response['service_object_id'],
        'readiness_response': owner_surface_result['readiness_response'],
        'theme_service_response': theme_service_response,
        'persisted_at': utcnow_iso(),
    }


def build_component_owner_surface_snapshot(
    *,
    vertical_slice_result: dict[str, Any],
    org_id: str,
) -> dict[str, Any]:
    capability_id = str(vertical_slice_result['capability_id'])
    business_date = str(
        vertical_slice_result['historical_run_truth']['ingestion_run']['requested_business_date']
    )
    common_kwargs = {
        'request_id': _request_id(capability_id, org_id, business_date),
        'trace_ref': _trace_ref(capability_id, org_id, business_date),
        'target_scope_ref': _scope_ref(org_id),
        'target_business_date': business_date,
        'vertical_slice_result': vertical_slice_result,
    }

    if capability_id == MEMBER_INSIGHT_CAPABILITY_ID:
        owner_surface_result = _build_member_insight_owner_surface(**common_kwargs)
    elif capability_id == FINANCE_SUMMARY_CAPABILITY_ID:
        owner_surface_result = _build_finance_summary_owner_surface(**common_kwargs)
    elif capability_id == STAFF_BOARD_CAPABILITY_ID:
        owner_surface_result = _build_staff_board_owner_surface(**common_kwargs)
    else:
        raise KeyError(f'Unsupported component capability_id: {capability_id}')

    return _snapshot_bundle(
        org_id=org_id,
        business_date=business_date,
        capability_id=capability_id,
        owner_surface_result=owner_surface_result,
    )


def build_daily_overview_snapshot_from_component_snapshots(
    *,
    org_id: str,
    business_date: str,
    member_snapshot: dict[str, Any],
    finance_snapshot: dict[str, Any],
    staff_snapshot: dict[str, Any],
) -> dict[str, Any]:
    owner_surface_result = _build_daily_overview_owner_surface(
        request_id=_request_id(DAILY_OVERVIEW_CAPABILITY_ID, org_id, business_date),
        trace_ref=_trace_ref(DAILY_OVERVIEW_CAPABILITY_ID, org_id, business_date),
        target_scope_ref=_scope_ref(org_id),
        target_business_date=business_date,
        org_id=org_id,
        member_insight_owner_surface={
            'readiness_response': member_snapshot['readiness_response'],
            'theme_service_response': member_snapshot['theme_service_response'],
        },
        staff_board_owner_surface={
            'readiness_response': staff_snapshot['readiness_response'],
            'theme_service_response': staff_snapshot['theme_service_response'],
        },
        finance_summary_owner_surface={
            'readiness_response': finance_snapshot['readiness_response'],
            'theme_service_response': finance_snapshot['theme_service_response'],
        },
    )
    return _snapshot_bundle(
        org_id=org_id,
        business_date=business_date,
        capability_id=DAILY_OVERVIEW_CAPABILITY_ID,
        owner_surface_result=owner_surface_result,
    )


def materialize_phase1_owner_surface_snapshots(
    *,
    execution_results: list[dict[str, Any]],
    org_id: str,
    persisted_serving_root: str,
) -> dict[str, Any]:
    store = PersistedOwnerSurfaceSnapshotStore(persisted_serving_root)
    affected_business_dates: set[str] = set()
    saved_capability_ids: list[str] = []

    for execution in execution_results:
        vertical_slice_result = execution.get('result')
        if not isinstance(vertical_slice_result, dict):
            continue
        capability_id = vertical_slice_result.get('capability_id')
        if capability_id not in COMPONENT_CAPABILITY_IDS:
            continue
        snapshot = build_component_owner_surface_snapshot(
            vertical_slice_result=vertical_slice_result,
            org_id=org_id,
        )
        store.save_snapshot(snapshot)
        affected_business_dates.add(snapshot['snapshot_business_date'])
        saved_capability_ids.append(snapshot['capability_id'])

    for business_date in sorted(affected_business_dates):
        member_snapshot = store.load_snapshot(
            org_id=org_id,
            capability_id=MEMBER_INSIGHT_CAPABILITY_ID,
            target_business_date=business_date,
            freshness_mode='strict_date',
        )
        finance_snapshot = store.load_snapshot(
            org_id=org_id,
            capability_id=FINANCE_SUMMARY_CAPABILITY_ID,
            target_business_date=business_date,
            freshness_mode='strict_date',
        )
        staff_snapshot = store.load_snapshot(
            org_id=org_id,
            capability_id=STAFF_BOARD_CAPABILITY_ID,
            target_business_date=business_date,
            freshness_mode='strict_date',
        )
        if not member_snapshot or not finance_snapshot or not staff_snapshot:
            continue
        daily_overview_snapshot = build_daily_overview_snapshot_from_component_snapshots(
            org_id=org_id,
            business_date=business_date,
            member_snapshot=member_snapshot,
            finance_snapshot=finance_snapshot,
            staff_snapshot=staff_snapshot,
        )
        store.save_snapshot(daily_overview_snapshot)
        saved_capability_ids.append(daily_overview_snapshot['capability_id'])

    return {
        'persisted_serving_root': str(store.root),
        'saved_snapshot_count': len(saved_capability_ids),
        'saved_capability_ids': saved_capability_ids,
        'affected_business_dates': sorted(affected_business_dates),
        'business_day_boundary_policy': resolve_business_day_boundary_policy(
            store_ref=_scope_ref(org_id),
            org_ref=f'navly:scope:org:{org_id}',
        ),
    }


__all__ = [
    'build_component_owner_surface_snapshot',
    'build_daily_overview_snapshot_from_component_snapshots',
    'materialize_phase1_owner_surface_snapshots',
]
