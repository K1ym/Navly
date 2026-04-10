from __future__ import annotations

from typing import Any

from completeness.daily_overview_readiness_surface import build_daily_overview_readiness_response
from directory.business_day_boundary_policy_registry import resolve_business_day_boundary_policy
from projections.daily_overview_service_projection import DAILY_OVERVIEW_CAPABILITY_ID, DAILY_OVERVIEW_SERVICE_OBJECT_ID
from serving.daily_overview_theme_service_surface import build_daily_overview_theme_service_response
from workflows.finance_summary_owner_surface import build_finance_summary_owner_surface
from workflows.member_insight_owner_surface import build_member_insight_owner_surface
from workflows.staff_board_owner_surface import build_staff_board_owner_surface


def _org_scope_ref(org_id: str) -> str:
    return f'navly:scope:org:{org_id}'


def _component_owner_surfaces(
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
) -> dict[str, dict[str, Any]]:
    return {
        'member_insight_owner_surface': build_member_insight_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        ),
        'staff_board_owner_surface': build_staff_board_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        ),
        'finance_summary_owner_surface': build_finance_summary_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=org_id,
            start_time=start_time,
            end_time=end_time,
            app_secret=app_secret,
            transport=transport,
        ),
    }


def _build_daily_overview_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    org_id: str,
    member_insight_owner_surface: dict[str, Any],
    staff_board_owner_surface: dict[str, Any],
    finance_summary_owner_surface: dict[str, Any],
    requested_capability_id: str = DAILY_OVERVIEW_CAPABILITY_ID,
    requested_service_object_id: str = DAILY_OVERVIEW_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    readiness_response = build_daily_overview_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        member_insight_owner_surface=member_insight_owner_surface,
        staff_board_owner_surface=staff_board_owner_surface,
        finance_summary_owner_surface=finance_summary_owner_surface,
        requested_capability_id=requested_capability_id,
    )
    business_day_policy = resolve_business_day_boundary_policy(
        store_ref=target_scope_ref,
        org_ref=_org_scope_ref(org_id),
    )
    theme_service_response = build_daily_overview_theme_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        readiness_response=readiness_response,
        business_day_policy=business_day_policy,
        member_insight_service_response=member_insight_owner_surface['theme_service_response'],
        staff_board_service_response=staff_board_owner_surface['theme_service_response'],
        finance_summary_service_response=finance_summary_owner_surface['theme_service_response'],
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )
    return {
        'member_insight_owner_surface': member_insight_owner_surface,
        'staff_board_owner_surface': staff_board_owner_surface,
        'finance_summary_owner_surface': finance_summary_owner_surface,
        'readiness_response': readiness_response,
        'theme_service_response': theme_service_response,
    }


def build_daily_overview_owner_surface(
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
    component_surfaces = _component_owner_surfaces(
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
    return _build_daily_overview_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        member_insight_owner_surface=component_surfaces['member_insight_owner_surface'],
        staff_board_owner_surface=component_surfaces['staff_board_owner_surface'],
        finance_summary_owner_surface=component_surfaces['finance_summary_owner_surface'],
    )


def sync_and_query_daily_overview_capability_readiness(
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
    requested_capability_id: str = DAILY_OVERVIEW_CAPABILITY_ID,
) -> dict[str, Any]:
    component_surfaces = _component_owner_surfaces(
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
    return _build_daily_overview_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        member_insight_owner_surface=component_surfaces['member_insight_owner_surface'],
        staff_board_owner_surface=component_surfaces['staff_board_owner_surface'],
        finance_summary_owner_surface=component_surfaces['finance_summary_owner_surface'],
        requested_capability_id=requested_capability_id,
    )['readiness_response']


def query_daily_overview_capability_readiness(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_daily_overview_capability_readiness(**kwargs)


def sync_and_query_daily_overview_theme_service(
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
    requested_capability_id: str = DAILY_OVERVIEW_CAPABILITY_ID,
    requested_service_object_id: str = DAILY_OVERVIEW_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    component_surfaces = _component_owner_surfaces(
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
    return _build_daily_overview_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        org_id=org_id,
        member_insight_owner_surface=component_surfaces['member_insight_owner_surface'],
        staff_board_owner_surface=component_surfaces['staff_board_owner_surface'],
        finance_summary_owner_surface=component_surfaces['finance_summary_owner_surface'],
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )['theme_service_response']


def query_daily_overview_theme_service(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_daily_overview_theme_service(**kwargs)
