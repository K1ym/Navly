from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from ingestion.member_insight_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID

MEMBER_INSIGHT_SERVICE_OBJECT_ID = 'navly.service.store.member_insight'


def _explanation_object(
    *,
    capability_id: str,
    reason_codes: list[str],
    state_trace_refs: list[str],
    run_trace_refs: list[str],
    latest_usable_business_date: str,
) -> dict[str, Any]:
    return {
        'capability_id': capability_id,
        'explanation_scope': 'service',
        'reason_codes': reason_codes,
        'summary_tokens': [
            capability_id,
            'not_ready',
            latest_usable_business_date,
        ],
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'extensions': {
            'owner_surface': 'member_insight',
            'latest_usable_business_date': latest_usable_business_date,
        },
    }


def _service_object(
    vertical_slice_result: dict[str, Any],
    *,
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
) -> dict[str, Any]:
    canonical_artifacts = vertical_slice_result['canonical_artifacts']
    backbone_state = vertical_slice_result['latest_state_artifacts']['vertical_slice_backbone_state']
    return {
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'available_endpoint_contract_ids': list(backbone_state.get('available_endpoint_contract_ids', [])),
        'customer_count': len(canonical_artifacts.get('customer', [])),
        'customer_card_count': len(canonical_artifacts.get('customer_card', [])),
        'consume_bill_count': len(canonical_artifacts.get('consume_bill', [])),
        'consume_bill_payment_count': len(canonical_artifacts.get('consume_bill_payment', [])),
        'consume_bill_info_count': len(canonical_artifacts.get('consume_bill_info', [])),
    }


def build_member_insight_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str = VERTICAL_SLICE_CAPABILITY_ID,
    requested_service_object_id: str = MEMBER_INSIGHT_SERVICE_OBJECT_ID,
) -> dict[str, Any]:
    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))

    if requested_capability_id != VERTICAL_SLICE_CAPABILITY_ID or requested_service_object_id != MEMBER_INSIGHT_SERVICE_OBJECT_ID:
        return {
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
            'explanation_object': _explanation_object(
                capability_id=requested_capability_id,
                reason_codes=['scope_out_of_contract'],
                state_trace_refs=[],
                run_trace_refs=[],
                latest_usable_business_date=target_business_date,
            ),
            'state_trace_refs': [],
            'run_trace_refs': [],
            'served_at': utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
            },
        }

    if readiness_response['readiness_status'] != 'ready':
        return {
            'request_id': request_id,
            'trace_ref': trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
            'service_status': 'not_ready',
            'service_object': {},
            'data_window': {
                'from': latest_usable_business_date,
                'to': latest_usable_business_date,
            },
            'explanation_object': _explanation_object(
                capability_id=VERTICAL_SLICE_CAPABILITY_ID,
                reason_codes=list(readiness_response.get('reason_codes', [])),
                state_trace_refs=state_trace_refs,
                run_trace_refs=run_trace_refs,
                latest_usable_business_date=latest_usable_business_date,
            ),
            'state_trace_refs': state_trace_refs,
            'run_trace_refs': run_trace_refs,
            'served_at': readiness_response.get('evaluated_at') or utcnow_iso(),
            'extensions': {
                'owner_surface': 'member_insight',
                'readiness_status': readiness_response['readiness_status'],
            },
        }

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': _service_object(
            vertical_slice_result,
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
        'served_at': readiness_response.get('evaluated_at') or utcnow_iso(),
        'extensions': {
            'owner_surface': 'member_insight',
            'transport_kind': vertical_slice_result.get('transport_kind'),
        },
    }
