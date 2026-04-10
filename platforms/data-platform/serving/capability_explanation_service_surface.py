from __future__ import annotations

from typing import Any

from projections.capability_explanation_service_projection import (
    CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
    build_capability_explanation_service_object,
)
from serving.service_surface_support import build_explanation_object, build_scope_mismatch_response


def build_capability_explanation_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    theme_service_response: dict[str, Any] | None,
    requested_service_object_id: str = CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))
    capability_id = readiness_response['capability_id']
    if requested_service_object_id != CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID:
        return build_scope_mismatch_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
            owner_surface='capability_explanation',
            reason_codes=['projection_not_available'],
            state_trace_refs=state_trace_refs,
            run_trace_refs=run_trace_refs,
        )
    explanation_scope = 'readiness' if readiness_response['readiness_status'] != 'ready' else 'service'
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': build_capability_explanation_service_object(
            readiness_response=readiness_response,
            theme_service_response=theme_service_response,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
        ),
        'data_window': {
            'from': latest_usable_business_date,
            'to': latest_usable_business_date,
        },
        'explanation_object': build_explanation_object(
            capability_id=capability_id,
            explanation_scope=explanation_scope,
            reason_codes=list(readiness_response.get('reason_codes', [])),
            state_trace_refs=state_trace_refs,
            run_trace_refs=run_trace_refs,
            summary_tokens=[
                capability_id,
                readiness_response['readiness_status'],
                latest_usable_business_date,
            ],
            owner_surface='capability_explanation',
            latest_usable_business_date=latest_usable_business_date,
            extensions={
                'theme_service_status': theme_service_response.get('service_status') if theme_service_response else None,
            },
        ),
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'served_at': readiness_response.get('evaluated_at'),
        'extensions': {
            'owner_surface': 'capability_explanation',
            'target_service_object_id': theme_service_response.get('service_object_id') if theme_service_response else None,
        },
    }
