from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from projections.capability_explanation_service_projection import CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID
from serving.capability_explanation_service_surface import build_capability_explanation_service_response
from workflows.daily_overview_owner_surface import build_daily_overview_owner_surface
from workflows.finance_summary_owner_surface import build_finance_summary_owner_surface
from workflows.member_insight_owner_surface import build_member_insight_owner_surface
from workflows.staff_board_owner_surface import build_staff_board_owner_surface


def _unsupported_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
) -> dict[str, Any]:
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
            'owner_surface': 'capability_explanation',
        },
    }


def _supported_owner_surface(
    *,
    requested_capability_id: str,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
) -> dict[str, Any] | None:
    if requested_capability_id == 'navly.store.member_insight':
        return build_member_insight_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        )
    if requested_capability_id == 'navly.store.staff_board':
        return build_staff_board_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        )
    if requested_capability_id == 'navly.store.finance_summary':
        return build_finance_summary_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        )
    if requested_capability_id == 'navly.store.daily_overview':
        return build_daily_overview_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        )
    return None


def build_capability_explanation_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_service_object_id: str = CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    owner_surface = _supported_owner_surface(
        requested_capability_id=requested_capability_id,
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
    )
    if owner_surface is None:
        readiness_response = _unsupported_readiness_response(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            requested_capability_id=requested_capability_id,
        )
        theme_service_response = None
    else:
        readiness_response = owner_surface['readiness_response']
        theme_service_response = owner_surface['theme_service_response']
    explanation_service_response = build_capability_explanation_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        readiness_response=readiness_response,
        theme_service_response=theme_service_response,
        requested_service_object_id=requested_service_object_id,
    )
    return {
        'owner_surface': owner_surface,
        'readiness_response': readiness_response,
        'theme_service_response': theme_service_response,
        'explanation_service_response': explanation_service_response,
    }


def query_capability_explanation_service(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    requested_service_object_id: str = CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    return build_capability_explanation_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        requested_capability_id=requested_capability_id,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        requested_service_object_id=requested_service_object_id,
    )['explanation_service_response']
