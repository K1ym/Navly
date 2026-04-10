from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ingestion.staff_board_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID


STAFF_BOARD_SERVICE_OBJECT_ID = 'navly.service.store.staff_board'


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


def build_staff_board_service_object(
    *,
    vertical_slice_result: dict[str, Any],
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
) -> dict[str, Any]:
    canonical_artifacts = vertical_slice_result['canonical_artifacts']
    backbone_state = vertical_slice_result['latest_state_artifacts']['vertical_slice_backbone_state']
    return {
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'service_object_id': STAFF_BOARD_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'requested_staff_code': vertical_slice_result.get('staff_code'),
        'available_endpoint_contract_ids': list(backbone_state.get('available_endpoint_contract_ids', [])),
        'staff_count': len(canonical_artifacts.get('staff', [])),
        'staff_item_count': len(canonical_artifacts.get('staff_item', [])),
        'staff_on_clock_count': len(
            [
                row
                for row in canonical_artifacts.get('staff', [])
                if row.get('person_state_name') == '上钟' or row.get('person_state') == 2
            ]
        ),
        'tech_shift_item_count': len(canonical_artifacts.get('tech_shift_item', [])),
        'tech_shift_summary_count': len(canonical_artifacts.get('tech_shift_summary', [])),
        'sales_commission_count': len(canonical_artifacts.get('sales_commission', [])),
        'tech_shift_turnover_total': _numeric_total(canonical_artifacts.get('tech_shift_item', []), 'turnover'),
        'tech_shift_income_total': _numeric_total(canonical_artifacts.get('tech_shift_item', []), 'income'),
        'tech_shift_main_total': _numeric_total(canonical_artifacts.get('tech_shift_summary', []), 'main_total'),
        'tech_shift_extra_total': _numeric_total(canonical_artifacts.get('tech_shift_summary', []), 'extra_total'),
        'sales_commission_total': _numeric_total(canonical_artifacts.get('sales_commission', []), 'commission'),
    }
