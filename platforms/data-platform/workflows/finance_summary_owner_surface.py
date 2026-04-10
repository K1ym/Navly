from __future__ import annotations

from typing import Any

from completeness.finance_summary_readiness_surface import build_finance_summary_readiness_response
from ingestion.finance_summary_vertical_slice import FINANCE_SUMMARY_CAPABILITY_ID, FINANCE_SUMMARY_SERVICE_OBJECT_ID, run_finance_summary_vertical_slice
from serving.finance_summary_theme_service_surface import build_finance_summary_theme_service_response


def _run_finance_summary_vertical_slice(
    *,
    target_business_date: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
    member_card_id: str | None = None,
    trade_type: int | None = None,
) -> dict[str, Any]:
    return run_finance_summary_vertical_slice(
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        requested_business_date=target_business_date,
        app_secret=app_secret,
        transport=transport,
        member_card_id=member_card_id,
        trade_type=trade_type,
    )


def _build_finance_summary_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = FINANCE_SUMMARY_CAPABILITY_ID,
    requested_service_object_id: str = FINANCE_SUMMARY_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    readiness_response = build_finance_summary_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )
    theme_service_response = build_finance_summary_theme_service_response(
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


def build_finance_summary_owner_surface(
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
    member_card_id: str | None = None,
    trade_type: int | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_finance_summary_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        member_card_id=member_card_id,
        trade_type=trade_type,
    )
    return _build_finance_summary_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
    )


def sync_and_query_finance_summary_capability_readiness(
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
    requested_capability_id: str = FINANCE_SUMMARY_CAPABILITY_ID,
    member_card_id: str | None = None,
    trade_type: int | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_finance_summary_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        member_card_id=member_card_id,
        trade_type=trade_type,
    )
    return _build_finance_summary_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )['readiness_response']


def query_finance_summary_capability_readiness(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_finance_summary_capability_readiness(**kwargs)


def sync_and_query_finance_summary_theme_service(
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
    requested_capability_id: str = FINANCE_SUMMARY_CAPABILITY_ID,
    requested_service_object_id: str = FINANCE_SUMMARY_SERVICE_OBJECT_ID,
    member_card_id: str | None = None,
    trade_type: int | None = None,
) -> dict[str, Any]:
    vertical_slice_result = _run_finance_summary_vertical_slice(
        target_business_date=target_business_date,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        member_card_id=member_card_id,
        trade_type=trade_type,
    )
    return _build_finance_summary_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )['theme_service_response']


def query_finance_summary_theme_service(**kwargs: Any) -> dict[str, Any]:
    return sync_and_query_finance_summary_theme_service(**kwargs)
