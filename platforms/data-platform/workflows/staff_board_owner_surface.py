from __future__ import annotations

from typing import Any

from completeness.staff_board_readiness_surface import build_staff_board_readiness_response
from ingestion.staff_board_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID, run_staff_board_vertical_slice
from projections.staff_board_service_projection import STAFF_BOARD_SERVICE_OBJECT_ID
from serving.staff_board_theme_service_surface import build_staff_board_theme_service_response


def _run_staff_board_vertical_slice(
    *,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    staff_code: str | None = None,
) -> dict[str, Any]:
    return run_staff_board_vertical_slice(
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        requested_business_date=target_business_date,
        app_secret=app_secret,
        transport=transport,
        staff_code=staff_code,
    )


def _build_staff_board_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = STAFF_BOARD_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    readiness_response = build_staff_board_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )
    theme_service_response = build_staff_board_theme_service_response(
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


def build_staff_board_owner_surface(
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
    staff_code: str | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_staff_board_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        staff_code=staff_code,
    )
    return _build_staff_board_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
    )


def sync_and_query_staff_board_capability_readiness(
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
    staff_code: str | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_staff_board_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        staff_code=staff_code,
    )
    return _build_staff_board_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )['readiness_response']


def query_staff_board_capability_readiness(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_staff_board_capability_readiness(**kwargs)


def sync_and_query_staff_board_theme_service(
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
    requested_service_object_id: str = STAFF_BOARD_SERVICE_OBJECT_ID,
    staff_code: str | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_staff_board_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        staff_code=staff_code,
    )
    return _build_staff_board_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )['theme_service_response']


def query_staff_board_theme_service(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_staff_board_theme_service(**kwargs)
