from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso


def build_explanation_object(
    *,
    capability_id: str,
    explanation_scope: str,
    reason_codes: list[str],
    state_trace_refs: list[str],
    run_trace_refs: list[str],
    summary_tokens: list[str],
    owner_surface: str,
    latest_usable_business_date: str,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'capability_id': capability_id,
        'explanation_scope': explanation_scope,
        'reason_codes': reason_codes,
        'summary_tokens': summary_tokens,
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'extensions': {
            'owner_surface': owner_surface,
            'latest_usable_business_date': latest_usable_business_date,
            **(extensions or {}),
        },
    }


def build_scope_mismatch_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    target_business_date: str,
    latest_usable_business_date: str,
    owner_surface: str,
    reason_codes: list[str],
    state_trace_refs: list[str] | None = None,
    run_trace_refs: list[str] | None = None,
    summary_tokens: list[str] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_state_trace_refs = list(state_trace_refs or [])
    resolved_run_trace_refs = list(run_trace_refs or [])
    resolved_latest_usable_business_date = latest_usable_business_date or target_business_date
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'scope_mismatch',
        'service_object': {},
        'data_window': {
            'from': resolved_latest_usable_business_date,
            'to': resolved_latest_usable_business_date,
        },
        'explanation_object': build_explanation_object(
            capability_id=capability_id,
            explanation_scope='service',
            reason_codes=reason_codes,
            state_trace_refs=resolved_state_trace_refs,
            run_trace_refs=resolved_run_trace_refs,
            summary_tokens=summary_tokens or [capability_id, 'scope_mismatch', resolved_latest_usable_business_date],
            owner_surface=owner_surface,
            latest_usable_business_date=resolved_latest_usable_business_date,
            extensions=extensions,
        ),
        'state_trace_refs': resolved_state_trace_refs,
        'run_trace_refs': resolved_run_trace_refs,
        'served_at': utcnow_iso(),
        'extensions': {
            'owner_surface': owner_surface,
            **(extensions or {}),
        },
    }
