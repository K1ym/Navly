from __future__ import annotations

from typing import Any

from completeness.readiness_surface_support import normalize_reason_codes


CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation'

_FALLBACK_ACTIONS = {
    'capability_scope_not_supported': 'adjust_requested_capability_or_scope',
    'latest_state_not_published': 'retry_after_latest_state_publish',
    'projection_not_available': 'wait_for_projection_publication',
    'required_dataset_missing': 'investigate_required_dataset_backfill',
    'upstream_error': 'retry_after_upstream_recovery',
}
_RECHECK_HINTS = {
    'capability_scope_not_supported': 'recheck_not_required_until_request_changes',
    'latest_state_not_published': 'recheck_after_latest_state_publish',
    'projection_not_available': 'recheck_after_projection_publish',
    'required_dataset_missing': 'recheck_after_backfill_completion',
    'upstream_error': 'recheck_after_next_successful_sync',
}


def _recommended_fallback_action(readiness_status: str, reason_codes: list[str]) -> str:
    if readiness_status == 'ready':
        return 'consume_theme_service'
    for reason_code in reason_codes:
        action = _FALLBACK_ACTIONS.get(reason_code)
        if action:
            return action
    return 'inspect_trace_refs'


def _next_recheck_hint(readiness_status: str, reason_codes: list[str]) -> str:
    if readiness_status == 'ready':
        return 'recheck_not_required'
    for reason_code in reason_codes:
        hint = _RECHECK_HINTS.get(reason_code)
        if hint:
            return hint
    return 'recheck_after_manual_investigation'


def build_capability_explanation_service_object(
    *,
    readiness_response: dict[str, Any],
    theme_service_response: dict[str, Any] | None,
    target_scope_ref: str,
    target_business_date: str,
) -> dict[str, Any]:
    reason_codes = normalize_reason_codes(readiness_response.get('reason_codes', []))
    service_status = theme_service_response.get('service_status') if theme_service_response else None
    return {
        'capability_id': readiness_response['capability_id'],
        'service_object_id': CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': readiness_response.get('latest_usable_business_date') or target_business_date,
        'readiness_status': readiness_response['readiness_status'],
        'theme_service_status': service_status,
        'reason_codes': reason_codes,
        'blocking_dependencies': list(readiness_response.get('blocking_dependencies', [])),
        'explanation_fragments': [
            {
                'fragment_kind': 'readiness_status',
                'value': readiness_response['readiness_status'],
            },
            *[
                {
                    'fragment_kind': 'reason_code',
                    'value': reason_code,
                }
                for reason_code in reason_codes
            ],
        ],
        'recommended_fallback_action': _recommended_fallback_action(
            readiness_response['readiness_status'],
            reason_codes,
        ),
        'next_recheck_hint': _next_recheck_hint(
            readiness_response['readiness_status'],
            reason_codes,
        ),
    }
