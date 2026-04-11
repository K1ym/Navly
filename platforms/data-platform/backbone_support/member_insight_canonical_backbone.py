from __future__ import annotations

from typing import Any


CUSTOMER_ENDPOINT_ID = 'qinqin.member.get_customers_list.v1_1'
CONSUME_ENDPOINT_ID = 'qinqin.member.get_consume_bill_list.v1_2'


def _rows(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        rows.extend(page.get('response_envelope', {}).get('RetData', {}).get('Data', []) or [])
    return rows


def _card_groups(customer_row: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    cards = customer_row.get('Cards') or {}
    return [
        ('stored', customer_row.get('Storeds') or cards.get('Storeds') or []),
        ('equity', customer_row.get('Equitys') or cards.get('Equitys') or []),
    ]


def _ticket_groups(customer_row: dict[str, Any]) -> list[dict[str, Any]]:
    return customer_row.get('Tickets') or []


def _coupon_groups(customer_row: dict[str, Any]) -> list[dict[str, Any]]:
    return customer_row.get('Coupons') or []


def canonicalize_customers(raw_page_records: list[dict[str, Any]], org_id: str, requested_business_date: str) -> dict[str, list[dict[str, Any]]]:
    customers: dict[str, dict[str, Any]] = {}
    customer_cards: dict[str, dict[str, Any]] = {}
    customer_tickets: dict[str, dict[str, Any]] = {}
    customer_coupons: dict[str, dict[str, Any]] = {}
    for row in _rows(raw_page_records):
        customer_id = row.get('Id')
        if not customer_id:
            continue
        customers[customer_id] = {
            'customer_id': customer_id,
            'org_id': row.get('OrgId') or org_id,
            'phone': row.get('Phone'),
            'name': row.get('Name'),
            'stored_amount': row.get('StoredAmount'),
            'consume_amount': row.get('ConsumeAmount'),
            'last_consume_time': row.get('LastConsumeTime'),
            'registered_at': row.get('CTime'),
            'marketer_id': row.get('MarketerId'),
            'marketer_name': row.get('MarketerName'),
            'source_endpoint_contract_id': CUSTOMER_ENDPOINT_ID,
            'requested_business_date': requested_business_date,
        }
        for card_group, entries in _card_groups(row):
            for index, card in enumerate(entries, start=1):
                card_id = card.get('Id') or f'{customer_id}:{card_group}:{index}'
                customer_cards[card_id] = {
                    'customer_card_id': card_id,
                    'customer_id': customer_id,
                    'card_group': card_group,
                    'org_id': card.get('OrgId') or row.get('OrgId') or org_id,
                    'card_type_id': card.get('CardTypeId'),
                    'card_type_name': card.get('CardTypeName'),
                    'card_no': card.get('CardNo'),
                    'balance': card.get('Balance'),
                    'total_amount': card.get('Total'),
                    'consume_amount': card.get('Consume'),
                    'opened_at': card.get('OpenTime'),
                    'expires_at': card.get('ExpireTime'),
                    'state': card.get('State') or card.get('CardState'),
                    'source_endpoint_contract_id': CUSTOMER_ENDPOINT_ID,
                    'requested_business_date': requested_business_date,
                }
        for index, ticket in enumerate(_ticket_groups(row), start=1):
            ticket_id = ticket.get('Id') or f'{customer_id}:ticket:{index}'
            customer_tickets[ticket_id] = {
                'customer_ticket_id': ticket_id,
                'customer_id': customer_id,
                'org_id': ticket.get('OrgId') or row.get('OrgId') or org_id,
                'user_name': ticket.get('UserName') or row.get('Name'),
                'user_phone': ticket.get('UserPhone') or row.get('Phone'),
                'card_trade_id': ticket.get('CardTradeId'),
                'settle_id': ticket.get('SettleId'),
                'consume_id': ticket.get('ConsumeId'),
                'item_id': ticket.get('ItemId'),
                'expires_at': ticket.get('ExpireTime'),
                'is_used': ticket.get('IsUsed'),
                'state': ticket.get('State'),
                'card_trade_ticket_id': ticket.get('CardTradeTicketId'),
                'operator_id': ticket.get('OptId'),
                'operator_code': ticket.get('OptCode'),
                'operator_name': ticket.get('OptName'),
                'operated_at': ticket.get('OptTime'),
                'ticket_id': ticket.get('TicketId'),
                'ticket_name': ticket.get('TicketName'),
                'ticket_price': ticket.get('TicketPrice'),
                'ticket_num_index': ticket.get('TicketNumIndex'),
                'ticket_type': ticket.get('TicketType'),
                'remark': ticket.get('Remark'),
                'card_no': ticket.get('CardNo'),
                'card_ping': ticket.get('CardPing'),
                'source_endpoint_contract_id': CUSTOMER_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            }
        for index, coupon in enumerate(_coupon_groups(row), start=1):
            coupon_id = coupon.get('Id') or f'{customer_id}:coupon:{index}'
            customer_coupons[coupon_id] = {
                'customer_coupon_id': coupon_id,
                'customer_id': customer_id,
                'org_id': coupon.get('OrgId') or row.get('OrgId') or org_id,
                'user_name': coupon.get('UserName') or row.get('Name'),
                'user_phone': coupon.get('UserPhone') or row.get('Phone'),
                'card_trade_id': coupon.get('CardTradeId'),
                'coupon_type_id': coupon.get('CouponTypeId'),
                'coupon_type_name': coupon.get('CouponTypeName'),
                'coupon_type': coupon.get('Type'),
                'deduction_amount': coupon.get('DeductionAmount'),
                'amount_limit': coupon.get('AmountLimit'),
                'settle_id': coupon.get('SettleId'),
                'consume_id': coupon.get('ConsumeId'),
                'expires_at': coupon.get('ExpireTime'),
                'is_used': coupon.get('IsUsed'),
                'state': coupon.get('State'),
                'operated_at': coupon.get('OptTime'),
                'operator_id': coupon.get('OptId'),
                'operator_code': coupon.get('OptCode'),
                'operator_name': coupon.get('OptName'),
                'remark': coupon.get('Remark'),
                'used_at': coupon.get('UsedTime'),
                'created_at': coupon.get('CTime'),
                'source': coupon.get('Source'),
                'source_endpoint_contract_id': CUSTOMER_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            }
    return {
        'customer': list(customers.values()),
        'customer_card': list(customer_cards.values()),
        'customer_ticket': list(customer_tickets.values()),
        'customer_coupon': list(customer_coupons.values()),
    }


def canonicalize_consume_bills(raw_page_records: list[dict[str, Any]], org_id: str, requested_business_date: str) -> dict[str, list[dict[str, Any]]]:
    consume_bills: dict[str, dict[str, Any]] = {}
    consume_bill_payments: list[dict[str, Any]] = []
    consume_bill_infos: list[dict[str, Any]] = []
    for row in _rows(raw_page_records):
        settle_id = row.get('SettleId')
        if not settle_id:
            continue
        consume_bills[settle_id] = {
            'consume_bill_id': settle_id,
            'settle_no': row.get('SettleNo'),
            'org_id': org_id,
            'consume_amount': row.get('Consume'),
            'pay_amount': row.get('Pay'),
            'discount_amount': row.get('DiscountAmount'),
            'deduction_amount': row.get('DeductionAmount'),
            'ticket_amount': row.get('TicketAmount'),
            'created_at': row.get('CTime'),
            'settled_at': row.get('OptTime'),
            'room_code': row.get('RoomCode'),
            'hand_card_code': row.get('HandCardCode'),
            'operator_code': row.get('OptCode'),
            'operator_name': row.get('OptName'),
            'source_endpoint_contract_id': CONSUME_ENDPOINT_ID,
            'requested_business_date': requested_business_date,
        }
        for index, payment in enumerate(row.get('Payments') or [], start=1):
            consume_bill_payments.append({
                'consume_bill_id': settle_id,
                'payment_sequence': index,
                'payment_name': payment.get('Name'),
                'payment_amount': payment.get('Amount'),
                'payment_type': payment.get('PaymentType'),
                'payment_source': payment.get('PyamentSource'),
                'source_endpoint_contract_id': CONSUME_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            })
        for index, info in enumerate(row.get('Infos') or [], start=1):
            consume_bill_infos.append({
                'consume_bill_id': settle_id,
                'info_sequence': index,
                'payload': info,
                'source_endpoint_contract_id': CONSUME_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            })
    return {
        'consume_bill': list(consume_bills.values()),
        'consume_bill_payment': consume_bill_payments,
        'consume_bill_info': consume_bill_infos,
    }


def build_member_insight_canonical_artifacts(
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    org_id: str,
    requested_business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    customer_artifacts = canonicalize_customers(
        raw_pages_by_endpoint.get(CUSTOMER_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    consume_artifacts = canonicalize_consume_bills(
        raw_pages_by_endpoint.get(CONSUME_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    return {
        **customer_artifacts,
        **consume_artifacts,
    }
