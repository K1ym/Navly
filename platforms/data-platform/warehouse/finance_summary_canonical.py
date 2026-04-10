from __future__ import annotations

from typing import Any


RECHARGE_ENDPOINT_ID = 'qinqin.member.get_recharge_bill_list.v1_3'
ACCOUNT_TRADE_ENDPOINT_ID = 'qinqin.member.get_user_trade_list.v1_4'


def _recharge_rows(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        response_envelope = page.get('response_envelope') or {}
        ret_data = response_envelope.get('RetData') or {}
        if isinstance(ret_data, dict):
            rows.extend(ret_data.get('Data') or [])
    return rows


def _account_trade_rows(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        response_envelope = page.get('response_envelope') or {}
        ret_data = response_envelope.get('RetData') or []
        if isinstance(ret_data, list):
            rows.extend(ret_data)
    return rows


def canonicalize_recharge_bills(
    raw_page_records: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    recharge_bills: dict[str, dict[str, Any]] = {}
    recharge_bill_payments: list[dict[str, Any]] = []
    recharge_bill_sales: list[dict[str, Any]] = []
    recharge_bill_tickets: list[dict[str, Any]] = []

    for record_index, row in enumerate(_recharge_rows(raw_page_records), start=1):
        recharge_bill_id = (
            row.get('Id')
            or row.get('SnNo')
            or f'{org_id}:{requested_business_date}:recharge:{record_index}'
        )
        recharge_bills[recharge_bill_id] = {
            'recharge_bill_id': recharge_bill_id,
            'org_id': org_id,
            'bill_no': row.get('SnNo'),
            'card_id': row.get('CardId'),
            'trade_type': row.get('Type'),
            'member_name': row.get('MemberName'),
            'member_phone': row.get('MemberPhone'),
            'card_no': row.get('CardNo'),
            'card_category': row.get('Category'),
            'card_type_id': row.get('CardTypeId'),
            'card_type_name': row.get('CardTypeName'),
            'pay_amount': row.get('Pay'),
            'recharge_total_amount': row.get('Total'),
            'reality_amount': row.get('Reality'),
            'donate_amount': row.get('Donate'),
            'ticket_equity': row.get('TicketEquity'),
            'coupon_num': row.get('CouponNum'),
            'sys_id': row.get('SysId'),
            'operator_id': row.get('OptId'),
            'operator_code': row.get('OptCode'),
            'operator_name': row.get('OptName'),
            'operated_at': row.get('OptTime'),
            'source_org_name': row.get('CorsOrgName'),
            'is_anti': row.get('IsAnti'),
            'integral': row.get('Integral'),
            'chain_trade_id': row.get('ChainTradeId'),
            'chain_no_anti': row.get('ChainNoAnti'),
            'is_not_allow_anti': row.get('IsNotAllowAnti'),
            'source_endpoint_contract_id': RECHARGE_ENDPOINT_ID,
            'requested_business_date': requested_business_date,
        }

        for payment_index, payment in enumerate(row.get('Payments') or [], start=1):
            recharge_bill_payment_id = payment.get('Id') or f'{recharge_bill_id}:payment:{payment_index}'
            recharge_bill_payments.append({
                'recharge_bill_payment_id': recharge_bill_payment_id,
                'recharge_bill_id': recharge_bill_id,
                'payment_sequence': payment_index,
                'primary_trade_id': payment.get('PrimaryId'),
                'payment_name': payment.get('Name'),
                'payment_amount': payment.get('Amount'),
                'source_endpoint_contract_id': RECHARGE_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            })

        for sales_index, sales in enumerate(row.get('Sales') or [], start=1):
            recharge_bill_sales.append({
                'recharge_bill_sales_id': f'{recharge_bill_id}:sales:{sales_index}',
                'recharge_bill_id': recharge_bill_id,
                'sales_sequence': sales_index,
                'payload': sales,
                'source_endpoint_contract_id': RECHARGE_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            })

        for ticket_index, ticket in enumerate(row.get('Tickets') or [], start=1):
            recharge_bill_tickets.append({
                'recharge_bill_ticket_id': f'{recharge_bill_id}:ticket:{ticket_index}',
                'recharge_bill_id': recharge_bill_id,
                'ticket_sequence': ticket_index,
                'payload': ticket,
                'source_endpoint_contract_id': RECHARGE_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            })

    return {
        'recharge_bill': list(recharge_bills.values()),
        'recharge_bill_payment': recharge_bill_payments,
        'recharge_bill_sales': recharge_bill_sales,
        'recharge_bill_ticket': recharge_bill_tickets,
    }


def canonicalize_account_trades(
    raw_page_records: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    account_trades: dict[str, dict[str, Any]] = {}

    for record_index, row in enumerate(_account_trade_rows(raw_page_records), start=1):
        account_trade_id = (
            row.get('TradeNo')
            or f'{org_id}:{requested_business_date}:account-trade:{record_index}'
        )
        account_trades[account_trade_id] = {
            'account_trade_id': account_trade_id,
            'org_id': org_id,
            'trade_no': row.get('TradeNo'),
            'card_opt_type': row.get('CardOptType'),
            'operation_org_id': row.get('OrgId'),
            'operation_org_name': row.get('OrgName'),
            'change_balance': row.get('ChangeBalance'),
            'change_reality': row.get('ChangeReality'),
            'change_donate': row.get('ChangeDonate'),
            'end_balance': row.get('EndBalance'),
            'end_reality': row.get('EndReality'),
            'end_donate': row.get('EndDonate'),
            'change_integral': row.get('ChangeIntegral'),
            'end_integral': row.get('EndIntegral'),
            'is_anti': row.get('IsAnti'),
            'payment_type': row.get('PaymentType'),
            'operated_at': row.get('OptTime'),
            'source_endpoint_contract_id': ACCOUNT_TRADE_ENDPOINT_ID,
            'requested_business_date': requested_business_date,
        }

    return {
        'account_trade': list(account_trades.values()),
    }


def build_finance_summary_canonical_artifacts(
    *,
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    org_id: str,
    requested_business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    recharge_artifacts = canonicalize_recharge_bills(
        raw_pages_by_endpoint.get(RECHARGE_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    account_trade_artifacts = canonicalize_account_trades(
        raw_pages_by_endpoint.get(ACCOUNT_TRADE_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    return {
        **recharge_artifacts,
        **account_trade_artifacts,
    }


__all__ = [
    'ACCOUNT_TRADE_ENDPOINT_ID',
    'RECHARGE_ENDPOINT_ID',
    'build_finance_summary_canonical_artifacts',
    'canonicalize_account_trades',
    'canonicalize_recharge_bills',
]
