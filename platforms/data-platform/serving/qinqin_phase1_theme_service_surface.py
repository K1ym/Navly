from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from backbone_support.qinqin_phase1_owner_surface_registry import (
    CAPABILITY_EXPLANATION_CAPABILITY_ID,
    CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
    DAILY_OVERVIEW_CAPABILITY_ID,
    DAILY_OVERVIEW_SERVICE_OBJECT_ID,
    FINANCE_SUMMARY_CAPABILITY_ID,
    FINANCE_SUMMARY_SERVICE_OBJECT_ID,
    STAFF_BOARD_CAPABILITY_ID,
    STAFF_BOARD_SERVICE_OBJECT_ID,
    owner_surface_name,
)


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if value in {None, ''}:
        return 0.0
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _int_total(rows: list[dict[str, Any]], field_key: str) -> int:
    return int(sum(_number(row.get('field_values', {}).get(field_key)) for row in rows))


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_capability_explanation_object(
    *,
    capability_id: str,
    explanation_scope: str,
    reason_codes: list[str],
    state_trace_refs: list[str],
    run_trace_refs: list[str],
    owner_surface: str,
    latest_usable_business_date: str | None = None,
    summary_tokens: list[str] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = list(summary_tokens or [])
    if not summary and latest_usable_business_date:
        summary = [capability_id, explanation_scope, latest_usable_business_date]
    payload_extensions = dict(extensions or {})
    payload_extensions.setdefault('owner_surface', owner_surface)
    if latest_usable_business_date:
        payload_extensions.setdefault('latest_usable_business_date', latest_usable_business_date)
    return {
        'capability_id': capability_id,
        'explanation_scope': explanation_scope,
        'reason_codes': list(reason_codes),
        'summary_tokens': summary,
        'state_trace_refs': list(state_trace_refs),
        'run_trace_refs': list(run_trace_refs),
        'extensions': payload_extensions,
    }


def build_scope_mismatch_service_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    target_business_date: str,
    owner_surface: str,
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    mismatch_reason_codes = list(reason_codes or ['scope_out_of_contract'])
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'scope_mismatch',
        'service_object': {},
        'data_window': {
            'from': target_business_date,
            'to': target_business_date,
        },
        'explanation_object': build_capability_explanation_object(
            capability_id=capability_id,
            explanation_scope='service',
            reason_codes=mismatch_reason_codes,
            state_trace_refs=[],
            run_trace_refs=[],
            owner_surface=owner_surface,
            latest_usable_business_date=target_business_date,
            summary_tokens=[capability_id, 'scope_mismatch', target_business_date],
        ),
        'state_trace_refs': [],
        'run_trace_refs': [],
        'served_at': utcnow_iso(),
        'extensions': {
            'owner_surface': owner_surface,
        },
    }


def build_not_ready_service_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    owner_surface: str,
) -> dict[str, Any]:
    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'not_ready',
        'service_object': {},
        'data_window': {
            'from': latest_usable_business_date,
            'to': latest_usable_business_date,
        },
        'explanation_object': build_capability_explanation_object(
            capability_id=capability_id,
            explanation_scope='service',
            reason_codes=list(readiness_response.get('reason_codes', [])),
            state_trace_refs=state_trace_refs,
            run_trace_refs=run_trace_refs,
            owner_surface=owner_surface,
            latest_usable_business_date=latest_usable_business_date,
            summary_tokens=[capability_id, 'not_ready', latest_usable_business_date],
        ),
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'served_at': readiness_response.get('evaluated_at') or utcnow_iso(),
        'extensions': {
            'owner_surface': owner_surface,
            'readiness_status': readiness_response.get('readiness_status'),
        },
    }


def _finance_summary_service_object(
    vertical_slice_result: dict[str, Any],
    *,
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
) -> dict[str, Any]:
    artifacts = vertical_slice_result['structured_target_artifacts']
    recharge_bills = artifacts.get('recharge_bill', [])
    recharge_payments = artifacts.get('recharge_bill_payment', [])
    recharge_tickets = artifacts.get('recharge_bill_ticket', [])
    recharge_sales = artifacts.get('recharge_bill_sales', [])
    account_trades = artifacts.get('account_trade', [])
    return {
        'capability_id': FINANCE_SUMMARY_CAPABILITY_ID,
        'service_object_id': FINANCE_SUMMARY_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'recharge_bill_count': len(recharge_bills),
        'recharge_payment_count': len(recharge_payments),
        'recharge_ticket_count': len(recharge_tickets),
        'recharge_sales_count': len(recharge_sales),
        'account_trade_count': len(account_trades),
        'recharge_total_amount': _int_total(recharge_bills, 'Data__Total'),
        'recharge_paid_amount': _int_total(recharge_bills, 'Data__Pay'),
        'recharge_reality_amount': _int_total(recharge_bills, 'Data__Reality'),
        'recharge_donate_amount': _int_total(recharge_bills, 'Data__Donate'),
        'account_trade_change_balance': _int_total(account_trades, 'ChangeBalance'),
        'account_trade_change_reality': _int_total(account_trades, 'ChangeReality'),
        'account_trade_change_donate': _int_total(account_trades, 'ChangeDonate'),
        'account_trade_change_integral': _int_total(account_trades, 'ChangeIntegral'),
    }


def _staff_board_service_object(
    vertical_slice_result: dict[str, Any],
    *,
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
) -> dict[str, Any]:
    artifacts = vertical_slice_result['structured_target_artifacts']
    staff_rows = artifacts.get('staff', [])
    staff_items = artifacts.get('staff_item', [])
    shift_items = artifacts.get('tech_shift_item', [])
    shift_summaries = artifacts.get('tech_shift_summary', [])
    sales_commissions = artifacts.get('sales_commission', [])
    return {
        'capability_id': STAFF_BOARD_CAPABILITY_ID,
        'service_object_id': STAFF_BOARD_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'staff_count': len(staff_rows),
        'staff_item_count': len(staff_items),
        'tech_shift_item_count': len(shift_items),
        'tech_shift_summary_count': len(shift_summaries),
        'sales_commission_count': len(sales_commissions),
        'tech_shift_total_clock': _int_total(shift_summaries, 'TotalClock'),
        'tech_shift_turnover_amount': _int_total(shift_items, 'Items__Turnover'),
        'tech_shift_income_amount': _int_total(shift_items, 'Items__Income'),
        'sales_commission_amount': _int_total(sales_commissions, 'Commission'),
    }


def _daily_overview_service_object(
    *,
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
    component_surfaces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    member_service = component_surfaces['member_insight']['theme_service_response']
    finance_service = component_surfaces['finance_summary']['theme_service_response']
    staff_service = component_surfaces['staff_board']['theme_service_response']
    member_object = member_service.get('service_object', {})
    finance_object = finance_service.get('service_object', {})
    staff_object = staff_service.get('service_object', {})
    return {
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'service_object_id': DAILY_OVERVIEW_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'components': {
            'member_insight': {
                'service_status': member_service.get('service_status'),
                'customer_count': member_object.get('customer_count', 0),
                'consume_bill_count': member_object.get('consume_bill_count', 0),
            },
            'finance_summary': {
                'service_status': finance_service.get('service_status'),
                'recharge_total_amount': finance_object.get('recharge_total_amount', 0),
                'account_trade_count': finance_object.get('account_trade_count', 0),
            },
            'staff_board': {
                'service_status': staff_service.get('service_status'),
                'staff_count': staff_object.get('staff_count', 0),
                'tech_shift_total_clock': staff_object.get('tech_shift_total_clock', 0),
            },
        },
        'key_metrics': {
            'customer_count': member_object.get('customer_count', 0),
            'consume_bill_count': member_object.get('consume_bill_count', 0),
            'recharge_total_amount': finance_object.get('recharge_total_amount', 0),
            'account_trade_count': finance_object.get('account_trade_count', 0),
            'staff_count': staff_object.get('staff_count', 0),
            'tech_shift_total_clock': staff_object.get('tech_shift_total_clock', 0),
            'sales_commission_amount': staff_object.get('sales_commission_amount', 0),
        },
    }


def _explanation_service_object(
    *,
    target_scope_ref: str,
    target_business_date: str,
    explanation_context: dict[str, Any],
) -> dict[str, Any]:
    reason_codes = list(explanation_context.get('reason_codes', []))
    return {
        'capability_id': CAPABILITY_EXPLANATION_CAPABILITY_ID,
        'service_object_id': CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'explained_capability_id': explanation_context.get('explained_capability_id'),
        'explained_service_object_id': explanation_context.get('explained_service_object_id'),
        'reason_codes': reason_codes,
        'summary_tokens': list(explanation_context.get('summary_tokens', [])) or ['capability_explanation', target_business_date],
        'suggested_next_action': explanation_context.get('suggested_next_action'),
        'state_trace_refs': list(explanation_context.get('state_trace_refs', [])),
        'run_trace_refs': list(explanation_context.get('run_trace_refs', [])),
    }


def build_qinqin_phase1_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    vertical_slice_result: dict[str, Any],
    requested_capability_id: str,
    requested_service_object_id: str,
) -> dict[str, Any]:
    capability_id = vertical_slice_result['capability_id']
    service_object_id = vertical_slice_result['service_object_id']
    owner_surface = owner_surface_name(capability_id)
    if requested_capability_id != capability_id or requested_service_object_id != service_object_id:
        return build_scope_mismatch_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=requested_capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            owner_surface=owner_surface,
        )

    if readiness_response['readiness_status'] != 'ready':
        return build_not_ready_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=capability_id,
            service_object_id=service_object_id,
            target_business_date=target_business_date,
            readiness_response=readiness_response,
            owner_surface=owner_surface,
        )

    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    state_trace_refs = list(readiness_response.get('state_trace_refs', []))
    run_trace_refs = list(readiness_response.get('run_trace_refs', []))
    service_builder = {
        FINANCE_SUMMARY_CAPABILITY_ID: _finance_summary_service_object,
        STAFF_BOARD_CAPABILITY_ID: _staff_board_service_object,
    }.get(capability_id)
    if service_builder is None:
        raise KeyError(f'No phase-1 theme service builder registered for capability_id: {capability_id}')

    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'served',
        'service_object': service_builder(
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
            'owner_surface': owner_surface,
            'transport_kind': vertical_slice_result.get('transport_kind'),
        },
    }


def build_daily_overview_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    requested_capability_id: str,
    requested_service_object_id: str,
    component_surfaces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    owner_surface = owner_surface_name(DAILY_OVERVIEW_CAPABILITY_ID)
    if (
        requested_capability_id != DAILY_OVERVIEW_CAPABILITY_ID
        or requested_service_object_id != DAILY_OVERVIEW_SERVICE_OBJECT_ID
    ):
        return build_scope_mismatch_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=requested_capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            owner_surface=owner_surface,
        )

    if readiness_response['readiness_status'] != 'ready':
        return build_not_ready_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=DAILY_OVERVIEW_CAPABILITY_ID,
            service_object_id=DAILY_OVERVIEW_SERVICE_OBJECT_ID,
            target_business_date=target_business_date,
            readiness_response=readiness_response,
            owner_surface=owner_surface,
        )

    latest_usable_business_date = readiness_response.get('latest_usable_business_date') or target_business_date
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'service_object_id': DAILY_OVERVIEW_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': _daily_overview_service_object(
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            latest_usable_business_date=latest_usable_business_date,
            component_surfaces=component_surfaces,
        ),
        'data_window': {
            'from': latest_usable_business_date,
            'to': latest_usable_business_date,
        },
        'state_trace_refs': list(readiness_response.get('state_trace_refs', [])),
        'run_trace_refs': list(readiness_response.get('run_trace_refs', [])),
        'served_at': readiness_response.get('evaluated_at') or utcnow_iso(),
        'extensions': {
            'owner_surface': owner_surface,
            'component_capability_ids': [
                component_surfaces['member_insight']['readiness_response']['capability_id'],
                component_surfaces['finance_summary']['readiness_response']['capability_id'],
                component_surfaces['staff_board']['readiness_response']['capability_id'],
            ],
        },
    }


def build_capability_explanation_theme_service_response(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    readiness_response: dict[str, Any],
    requested_capability_id: str,
    requested_service_object_id: str,
    explanation_context: dict[str, Any],
) -> dict[str, Any]:
    owner_surface = owner_surface_name(CAPABILITY_EXPLANATION_CAPABILITY_ID)
    if (
        requested_capability_id != CAPABILITY_EXPLANATION_CAPABILITY_ID
        or requested_service_object_id != CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID
    ):
        return build_scope_mismatch_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            capability_id=requested_capability_id,
            service_object_id=requested_service_object_id,
            target_business_date=target_business_date,
            owner_surface=owner_surface,
        )

    state_trace_refs = _unique_strings([
        *list(readiness_response.get('state_trace_refs', [])),
        *list(explanation_context.get('state_trace_refs', [])),
    ])
    run_trace_refs = _unique_strings([
        *list(readiness_response.get('run_trace_refs', [])),
        *list(explanation_context.get('run_trace_refs', [])),
    ])
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': CAPABILITY_EXPLANATION_CAPABILITY_ID,
        'service_object_id': CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
        'service_status': 'served',
        'service_object': _explanation_service_object(
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            explanation_context=explanation_context,
        ),
        'data_window': {
            'from': target_business_date,
            'to': target_business_date,
        },
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'served_at': readiness_response.get('evaluated_at') or utcnow_iso(),
        'extensions': {
            'owner_surface': owner_surface,
        },
    }

