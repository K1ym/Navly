from __future__ import annotations

from typing import Any

from warehouse.qinqin_structured_target_landing import build_qinqin_structured_target_artifacts


CUSTOMER_ENDPOINT_ID = 'qinqin.member.get_customers_list.v1_1'
CONSUME_ENDPOINT_ID = 'qinqin.member.get_consume_bill_list.v1_2'


def canonicalize_customers(raw_page_records: list[dict[str, Any]], org_id: str, requested_business_date: str) -> dict[str, list[dict[str, Any]]]:
    artifacts = build_qinqin_structured_target_artifacts(
        raw_pages_by_endpoint={
            CUSTOMER_ENDPOINT_ID: raw_page_records,
        },
        org_id=org_id,
        requested_business_date=requested_business_date,
        endpoint_contract_ids=[CUSTOMER_ENDPOINT_ID],
    )
    return {
        'customer': artifacts['customer'],
        'customer_card': artifacts['customer_card'],
    }


def canonicalize_consume_bills(raw_page_records: list[dict[str, Any]], org_id: str, requested_business_date: str) -> dict[str, list[dict[str, Any]]]:
    artifacts = build_qinqin_structured_target_artifacts(
        raw_pages_by_endpoint={
            CONSUME_ENDPOINT_ID: raw_page_records,
        },
        org_id=org_id,
        requested_business_date=requested_business_date,
        endpoint_contract_ids=[CONSUME_ENDPOINT_ID],
    )
    return {
        'consume_bill': artifacts['consume_bill'],
        'consume_bill_payment': artifacts['consume_bill_payment'],
        'consume_bill_info': artifacts['consume_bill_info'],
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
