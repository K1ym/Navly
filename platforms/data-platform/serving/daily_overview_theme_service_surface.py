from __future__ import annotations

from typing import Any

from projections.daily_overview_service_projection import (
    DAILY_OVERVIEW_CAPABILITY_ID,
    DAILY_OVERVIEW_SERVICE_OBJECT_ID,
    build_daily_overview_service_object,
)
from serving.service_surface_support import build_explanation_object, build_scope_mismatch_response


def build_daily_overview_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    business_day_policy: dict[str, Any],
    member_insight_service_response: dict[str, Any],
    staff_board_service_response: dict[str, Any],
    finance_summary_service_response: dict[str, Any],
    requested_capability_id: str = DAILY_OVERVIEW_CAPABILITY_ID,
    requested_service_object_id: str = DAILY_OVERVIEW_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))
    if requested_capability_id != DAILY_OVERVIEW_CAPABILITY_ID:
        return build_scope_mismatch_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=requested_capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            latest_usable_business_date=target_business_date,
            owner_surface='daily_overview',
            reason_codes=['capability_scope_not_supported'],
        )
    if requested_service_object_id != DAILY_OVERVIEW_SERVICE_OBJECT_ID:
        return build_scope_mismatch_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=DAILY_OVERVIEW_CAPABILITY_ID,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
            owner_surface='daily_overview',
            reason_codes=['projection_not_available'],
            state_trace_refs=state_trace_refs,
            run_trace_refs=run_trace_refs,
        )
    if readiness_response['readiness_status'] != 'ready':
        return {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
            'service_object_id': DAILY_OVERVIEW_SERVICE_OBJECT_ID,
            'service_status': 'not_ready',
            'service_object': {},
            'data_window': {
                'from': latest_usable_business_date,
                'to': latest_usable_business_date,
            },
            'explanation_object': build_explanation_object(
                capability_id=DAILY_OVERVIEW_CAPABILITY_ID,
                explanation_scope='service',
                reason_codes=list(readiness_response.get('reason_codes', [])),
                state_trace_refs=state_trace_refs,
                run_trace_refs=run_trace_refs,
                summary_tokens=[
                    DAILY_OVERVIEW_CAPABILITY_ID,
                    readiness_response['readiness_status'],
                    latest_usable_business_date,
                ],
                owner_surface='daily_overview',
                latest_usable_business_date=latest_usable_business_date,
                extensions={
                    'readiness_status': readiness_response['readiness_status'],
                },
            ),
            'state_trace_refs': state_trace_refs,
            'run_trace_refs': run_trace_refs,
            'served_at': readiness_response.get('evaluated_at'),
            'extensions': {
                'owner_surface': 'daily_overview',
                'readiness_status': readiness_response['readiness_status'],
            },
        }
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'service_object_id': DAILY_OVERVIEW_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': build_daily_overview_service_object(
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
            business_day_policy=business_day_policy,
            member_insight_service_response=member_insight_service_response,
            staff_board_service_response=staff_board_service_response,
            finance_summary_service_response=finance_summary_service_response,
        ),
        'data_window': {
            'from': latest_usable_business_date,
            'to': latest_usable_business_date,
        },
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'served_at': readiness_response.get('evaluated_at'),
        'extensions': {
            'owner_surface': 'daily_overview',
            'business_day_policy_id': business_day_policy['policy_id'],
        },
    }
