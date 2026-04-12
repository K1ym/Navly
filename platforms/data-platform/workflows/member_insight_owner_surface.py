from __future__ import annotations

from pathlib import Path
from typing import Any

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate, utcnow_iso
from completeness.member_insight_readiness_surface import build_member_insight_readiness_response
from ingestion.member_insight_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID, run_member_insight_vertical_slice
from serving.member_insight_theme_service_surface import (
    MEMBER_INSIGHT_SERVICE_OBJECT_ID,
    build_member_insight_theme_service_response,
)


def _run_member_insight_vertical_slice(
    *,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
) -> dict[str, Any]:
    return run_member_insight_vertical_slice(
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        requested_business_date=target_business_date,
        app_secret=app_secret,
        transport=transport,
    )


def _build_member_insight_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    readiness_response = build_member_insight_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )
    theme_service_response = build_member_insight_theme_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        readiness_response=readiness_response,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )
    return {
        'vertical_slice_result': vertical_slice_result,
        'readiness_response': readiness_response,
        'theme_service_response': theme_service_response,
    }


def _build_snapshot_backed_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    truth_store: PostgresTruthSubstrate,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    if requested_capability_id != VERTICAL_SLICE_CAPABILITY_ID:
        readiness_response = {
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
                'surface_source': 'persisted_snapshot',
            },
        }
        service_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': requested_capability_id,
            'service_object_id': requested_service_object_id,
            'service_status': 'scope_mismatch',
            'service_object': {},
            'data_window': {
                'from': target_business_date,
                'to': target_business_date,
            },
            'explanation_object': {
                'capability_id': requested_capability_id,
                'explanation_scope': 'service',
                'reason_codes': ['scope_out_of_contract'],
                'state_trace_refs': [],
                'run_trace_refs': [],
            },
            'state_trace_refs': [],
            'run_trace_refs': [],
            'served_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
        return {
            'readiness_response': readiness_response,
            'theme_service_response': service_response,
        }

    readiness_snapshot = truth_store.capability_readiness_snapshots.get(
        (org_id, target_business_date, VERTICAL_SLICE_CAPABILITY_ID)
    )
    if readiness_snapshot is None:
        readiness_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'readiness_status': 'pending',
            'evaluated_scope_ref': target_scope_ref,
            'requested_business_date': target_business_date,
            'latest_usable_business_date': target_business_date,
            'reason_codes': ['missing_persisted_state'],
            'blocking_dependencies': [],
            'state_trace_refs': [],
            'run_trace_refs': [],
            'evaluated_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
        service_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': requested_service_object_id,
            'service_status': 'not_ready',
            'service_object': {},
            'data_window': {
                'from': target_business_date,
                'to': target_business_date,
            },
            'explanation_object': {
                'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
                'explanation_scope': 'service',
                'reason_codes': ['missing_persisted_state'],
                'state_trace_refs': [],
                'run_trace_refs': [],
            },
            'state_trace_refs': [],
            'run_trace_refs': [],
            'served_at': readiness_response['evaluated_at'],
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
        return {
            'readiness_response': readiness_response,
            'theme_service_response': service_response,
        }

    readiness_response = {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'readiness_status': readiness_snapshot['readiness_status'],
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': readiness_snapshot['latest_usable_business_date'],
        'reason_codes': list(readiness_snapshot['reason_codes']),
        'blocking_dependencies': list(readiness_snapshot['blocking_dependencies']),
        'state_trace_refs': list(readiness_snapshot['state_trace_refs']),
        'run_trace_refs': list(readiness_snapshot['run_trace_refs']),
        'evaluated_at': readiness_snapshot['evaluated_at'],
        'extensions': {
            'owner_surface': 'member_insight',
            'surface_source': 'persisted_snapshot',
        },
    }

    if requested_service_object_id != MEMBER_INSIGHT_SERVICE_OBJECT_ID:
        service_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': requested_service_object_id,
            'service_status': 'scope_mismatch',
            'service_object': {},
            'data_window': {
                'from': target_business_date,
                'to': target_business_date,
            },
            'explanation_object': {
                'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
                'explanation_scope': 'service',
                'reason_codes': ['scope_out_of_contract'],
                'state_trace_refs': [],
                'run_trace_refs': [],
            },
            'state_trace_refs': [],
            'run_trace_refs': [],
            'served_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
        return {
            'readiness_response': readiness_response,
            'theme_service_response': service_response,
        }

    service_projection = truth_store.service_projections.get(
        (org_id, target_business_date, MEMBER_INSIGHT_SERVICE_OBJECT_ID)
    )
    if service_projection is None:
        service_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
            'service_status': 'not_ready',
            'service_object': {},
            'data_window': {
                'from': readiness_response['latest_usable_business_date'],
                'to': readiness_response['latest_usable_business_date'],
            },
            'explanation_object': {
                'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
                'explanation_scope': 'service',
                'reason_codes': ['missing_persisted_projection'],
                'state_trace_refs': list(readiness_response['state_trace_refs']),
                'run_trace_refs': list(readiness_response['run_trace_refs']),
            },
            'state_trace_refs': list(readiness_response['state_trace_refs']),
            'run_trace_refs': list(readiness_response['run_trace_refs']),
            'served_at': readiness_response['evaluated_at'],
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
    else:
        service_response = {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
            'service_status': service_projection['service_status'],
            'service_object': dict(service_projection['service_object']),
            'data_window': {
                'from': service_projection['latest_usable_business_date'],
                'to': service_projection['latest_usable_business_date'],
            },
            'state_trace_refs': list(service_projection['state_trace_refs']),
            'run_trace_refs': list(service_projection['run_trace_refs']),
            'served_at': service_projection['served_at'],
            'extensions': {
                'owner_surface': 'member_insight',
                'surface_source': 'persisted_snapshot',
            },
        }
        explanation_object = dict(service_projection['explanation_object'])
        if explanation_object:
            service_response['explanation_object'] = explanation_object
    return {
        'readiness_response': readiness_response,
        'theme_service_response': service_response,
    }


def build_member_insight_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
) -> dict[str, Any]:
    vertical_slice_result = _run_member_insight_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
    )
    return _build_member_insight_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
    )


def sync_and_query_member_insight_capability_readiness(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
) -> dict[str, Any]:
    vertical_slice_result = _run_member_insight_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
    )
    return _build_member_insight_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )['readiness_response']


def query_member_insight_capability_readiness(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
) -> dict[str, Any]:
    return sync_and_query_member_insight_capability_readiness(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        requested_capability_id=requested_capability_id,
    )


def sync_and_query_member_insight_theme_service(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    vertical_slice_result = _run_member_insight_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
    )
    return _build_member_insight_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )['theme_service_response']


def query_member_insight_theme_service(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    return sync_and_query_member_insight_theme_service(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )


def build_member_insight_owner_surface_from_snapshot(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    state_snapshot_path: str,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    truth_store = PostgresTruthSubstrate.from_snapshot_file(state_snapshot_path)
    payload = _build_snapshot_backed_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        truth_store=truth_store,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )
    payload['state_snapshot'] = str(Path(state_snapshot_path))
    return payload


def query_member_insight_capability_readiness_from_snapshot(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    state_snapshot_path: str,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
) -> dict[str, Any]:
    return build_member_insight_owner_surface_from_snapshot(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        state_snapshot_path=state_snapshot_path,
        requested_capability_id=requested_capability_id,
    )['readiness_response']


def query_member_insight_theme_service_from_snapshot(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    state_snapshot_path: str,
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    return build_member_insight_owner_surface_from_snapshot(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        state_snapshot_path=state_snapshot_path,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )['theme_service_response']
