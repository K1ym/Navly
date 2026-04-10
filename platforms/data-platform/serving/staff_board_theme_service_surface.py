from __future__ import annotations

from typing import Any

from ingestion.staff_board_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID
from projections.staff_board_service_projection import STAFF_BOARD_SERVICE_OBJECT_ID, build_staff_board_service_object
from serving.service_surface_support import build_explanation_object, build_scope_mismatch_response


def build_staff_board_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = STAFF_BOARD_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))
    if requested_capability_id != VERTICAL_SLICE_CAPABILITY_ID:
        return build_scope_mismatch_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=requested_capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            latest_usable_business_date=target_business_date,
            owner_surface='staff_board',
            reason_codes=['capability_scope_not_supported'],
        )
    if requested_service_object_id != STAFF_BOARD_SERVICE_OBJECT_ID:
        return build_scope_mismatch_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=VERTICAL_SLICE_CAPABILITY_ID,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
            owner_surface='staff_board',
            reason_codes=['projection_not_available'],
            state_trace_refs=state_trace_refs,
            run_trace_refs=run_trace_refs,
        )
    if readiness_response['readiness_status'] != 'ready':
        return {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': STAFF_BOARD_SERVICE_OBJECT_ID,
            'service_status': 'not_ready',
            'service_object': {},
            'data_window': {
                'from': latest_usable_business_date,
                'to': latest_usable_business_date,
            },
            'explanation_object': build_explanation_object(
                capability_id=VERTICAL_SLICE_CAPABILITY_ID,
                explanation_scope='service',
                reason_codes=list(readiness_response.get('reason_codes', [])),
                state_trace_refs=state_trace_refs,
                run_trace_refs=run_trace_refs,
                summary_tokens=[
                    VERTICAL_SLICE_CAPABILITY_ID,
                    readiness_response['readiness_status'],
                    latest_usable_business_date,
                ],
                owner_surface='staff_board',
                latest_usable_business_date=latest_usable_business_date,
                extensions={
                    'readiness_status': readiness_response['readiness_status'],
                },
            ),
            'state_trace_refs': state_trace_refs,
            'run_trace_refs': run_trace_refs,
            'served_at': readiness_response.get('evaluated_at'),
            'extensions': {
                'owner_surface': 'staff_board',
                'readiness_status': readiness_response['readiness_status'],
            },
        }
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'service_object_id': STAFF_BOARD_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': build_staff_board_service_object(
            vertical_slice_result=vertical_slice_result,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
        ),
        'data_window': {
            'from': latest_usable_business_date,
            'to': latest_usable_business_date,
        },
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'served_at': readiness_response.get('evaluated_at'),
        'extensions': {
            'owner_surface': 'staff_board',
            'transport_kind': vertical_slice_result.get('transport_kind'),
        },
    }
