from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ingestion.finance_summary_vertical_slice import FINANCE_SUMMARY_CAPABILITY_ID, FINANCE_SUMMARY_SERVICE_OBJECT_ID


def _numeric_total(rows: list[dict[str, Any]], field_name: str) -> int | float:
    total = Decimal('0')
    for row in rows:
        raw_value = row.get(field_name)
        if raw_value in {None, ''}:
            continue
        try:
            total += Decimal(str(raw_value))
        except (InvalidOperation, ValueError):
            continue
    if total == total.to_integral():
        return int(total)
    return float(total)


def build_finance_summary_service_object(
    *,
    vertical_slice_result: dict[str, Any],
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
) -> dict[str, Any]:
    canonical_artifacts = vertical_slice_result['canonical_artifacts']
    prerequisite_state = vertical_slice_result['latest_state_artifacts']['finance_summary_prerequisite_state']
    return {
        'capability_id': FINANCE_SUMMARY_CAPABILITY_ID,
        'service_object_id': FINANCE_SUMMARY_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'required_endpoint_contract_ids': list(prerequisite_state.get('required_endpoint_contract_ids', [])),
        'ready_endpoint_contract_ids': list(prerequisite_state.get('ready_endpoint_contract_ids', [])),
        'source_empty_endpoint_contract_ids': list(prerequisite_state.get('source_empty_endpoint_contract_ids', [])),
        'recharge_bill_count': len(canonical_artifacts.get('recharge_bill', [])),
        'recharge_bill_payment_count': len(canonical_artifacts.get('recharge_bill_payment', [])),
        'recharge_bill_sales_count': len(canonical_artifacts.get('recharge_bill_sales', [])),
        'recharge_bill_ticket_count': len(canonical_artifacts.get('recharge_bill_ticket', [])),
        'account_trade_count': len(canonical_artifacts.get('account_trade', [])),
        'recharge_pay_amount_total': _numeric_total(canonical_artifacts.get('recharge_bill', []), 'pay_amount'),
        'recharge_reality_amount_total': _numeric_total(canonical_artifacts.get('recharge_bill', []), 'reality_amount'),
        'recharge_donate_amount_total': _numeric_total(canonical_artifacts.get('recharge_bill', []), 'donate_amount'),
        'account_trade_change_balance_total': _numeric_total(
            canonical_artifacts.get('account_trade', []),
            'change_balance',
        ),
        'account_trade_change_reality_total': _numeric_total(
            canonical_artifacts.get('account_trade', []),
            'change_reality',
        ),
        'account_trade_change_donate_total': _numeric_total(
            canonical_artifacts.get('account_trade', []),
            'change_donate',
        ),
    }
