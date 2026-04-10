from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
PERSON_ENDPOINT_ID = 'qinqin.staff.get_person_list.v1_5'
TECH_UP_CLOCK_ENDPOINT_ID = 'qinqin.staff.get_tech_up_clock_list.v1_6'
TECH_MARKET_ENDPOINT_ID = 'qinqin.staff.get_tech_market_list.v1_7'

_LEAF_PATH_KINDS = {
    'record_field',
    'nested_record_field',
    'summary_field',
}
_POLICY_PREFIXES = {
    f'{PERSON_ENDPOINT_ID}.staff': 'RetData.',
    f'{PERSON_ENDPOINT_ID}.staff-item': 'RetData.ItemList.',
    f'{TECH_UP_CLOCK_ENDPOINT_ID}.tech-shift-item': 'RetData.Items.',
    f'{TECH_UP_CLOCK_ENDPOINT_ID}.tech-shift-summary': 'RetData.',
    f'{TECH_MARKET_ENDPOINT_ID}.sales-commission': 'RetData.',
}
_FIRST_CAP_RE = re.compile(r'(.)([A-Z][a-z]+)')
_ALL_CAP_RE = re.compile(r'([a-z0-9])([A-Z])')


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _field_catalog_entries(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    payload = _load_json(data_platform_root / 'directory' / 'endpoint-field-catalog.seed.json')
    return {
        entry['endpoint_contract_id']: entry
        for entry in payload['entries']
    }


def _snake_case(value: str) -> str:
    normalized = _FIRST_CAP_RE.sub(r'\1_\2', value.replace('-', '_'))
    normalized = _ALL_CAP_RE.sub(r'\1_\2', normalized)
    return normalized.replace('__', '_').lower()


def _dataset_leaf_paths(
    endpoint_contract_id: str,
    policy_id: str,
    *,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> list[str]:
    entry = _field_catalog_entries(data_platform_root)[endpoint_contract_id]
    prefix = _POLICY_PREFIXES[policy_id]
    leaf_paths: list[str] = []
    for field in entry['response_fields']:
        if field['landing_policy_id'] != policy_id or field['path_kind'] not in _LEAF_PATH_KINDS:
            continue
        suffix = field['field_path']
        if suffix.startswith(prefix):
            suffix = suffix[len(prefix):]
        if suffix and suffix not in leaf_paths:
            leaf_paths.append(suffix)
    return leaf_paths


def _lookup(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _flatten_fields(
    payload: dict[str, Any],
    field_paths: list[str],
) -> dict[str, Any]:
    return {
        '_'.join(_snake_case(part) for part in path.split('.')): _lookup(payload, path)
        for path in field_paths
    }


def _person_rows(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        ret_data = page.get('response_envelope', {}).get('RetData')
        if isinstance(ret_data, list):
            rows.extend(ret_data)
    return rows


def _tech_shift_items(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        ret_data = page.get('response_envelope', {}).get('RetData')
        if isinstance(ret_data, dict):
            items = ret_data.get('Items')
            if isinstance(items, list):
                rows.extend(items)
    return rows


def _tech_shift_summaries(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        ret_data = page.get('response_envelope', {}).get('RetData')
        if isinstance(ret_data, dict) and isinstance(ret_data.get('Items'), list) and ret_data.get('Items'):
            rows.append(ret_data)
    return rows


def _sales_commission_rows(raw_page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in raw_page_records:
        ret_data = page.get('response_envelope', {}).get('RetData')
        if isinstance(ret_data, list):
            rows.extend(ret_data)
    return rows


def _fallback_id(parts: list[Any]) -> str:
    normalized = [str(part).strip() for part in parts if part not in {None, ''}]
    return ':'.join(normalized)


def canonicalize_staff(
    raw_page_records: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    staff_field_paths = _dataset_leaf_paths(
        PERSON_ENDPOINT_ID,
        f'{PERSON_ENDPOINT_ID}.staff',
        data_platform_root=data_platform_root,
    )
    item_field_paths = _dataset_leaf_paths(
        PERSON_ENDPOINT_ID,
        f'{PERSON_ENDPOINT_ID}.staff-item',
        data_platform_root=data_platform_root,
    )
    staff_rows: dict[str, dict[str, Any]] = {}
    staff_item_rows: dict[str, dict[str, Any]] = {}

    for staff_row in _person_rows(raw_page_records):
        staff_id = str(staff_row.get('Id') or _fallback_id([org_id, staff_row.get('Code'), staff_row.get('Name')]))
        canonical_staff = {
            'staff_id': staff_id,
            'org_id': staff_row.get('OrgId') or org_id,
            'requested_business_date': requested_business_date,
            'source_endpoint_contract_id': PERSON_ENDPOINT_ID,
        }
        canonical_staff.update(_flatten_fields(staff_row, staff_field_paths))
        canonical_staff['org_id'] = canonical_staff.get('org_id') or org_id
        staff_rows[staff_id] = canonical_staff

        for item_index, item_row in enumerate(staff_row.get('ItemList') or [], start=1):
            staff_item_id = str(
                item_row.get('ItemId')
                or _fallback_id([staff_id, item_row.get('ItemCode'), item_index])
            )
            canonical_item = {
                'staff_item_id': staff_item_id,
                'staff_id': staff_id,
                'staff_code': staff_row.get('Code'),
                'org_id': staff_row.get('OrgId') or org_id,
                'item_sequence': item_index,
                'requested_business_date': requested_business_date,
                'source_endpoint_contract_id': PERSON_ENDPOINT_ID,
            }
            canonical_item.update(_flatten_fields(item_row, item_field_paths))
            staff_item_rows[staff_item_id] = canonical_item

    return {
        'staff': list(staff_rows.values()),
        'staff_item': list(staff_item_rows.values()),
    }


def canonicalize_tech_shift(
    raw_page_records: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
    requested_staff_code: str | None,
    window_start_at: str,
    window_end_at: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    item_field_paths = _dataset_leaf_paths(
        TECH_UP_CLOCK_ENDPOINT_ID,
        f'{TECH_UP_CLOCK_ENDPOINT_ID}.tech-shift-item',
        data_platform_root=data_platform_root,
    )
    summary_field_paths = _dataset_leaf_paths(
        TECH_UP_CLOCK_ENDPOINT_ID,
        f'{TECH_UP_CLOCK_ENDPOINT_ID}.tech-shift-summary',
        data_platform_root=data_platform_root,
    )
    tech_shift_items: dict[str, dict[str, Any]] = {}
    tech_shift_summaries: dict[str, dict[str, Any]] = {}

    for item_index, item_row in enumerate(_tech_shift_items(raw_page_records), start=1):
        tech_shift_item_id = _fallback_id([
            item_row.get('SettleNo'),
            item_row.get('PersonCode'),
            item_row.get('HandCardCode'),
            item_row.get('STime'),
            item_row.get('ItemName'),
            item_index,
        ])
        canonical_item = {
            'tech_shift_item_id': tech_shift_item_id,
            'org_id': org_id,
            'requested_business_date': requested_business_date,
            'requested_staff_code': requested_staff_code,
            'window_start_at': window_start_at,
            'window_end_at': window_end_at,
            'source_endpoint_contract_id': TECH_UP_CLOCK_ENDPOINT_ID,
        }
        canonical_item.update(_flatten_fields(item_row, item_field_paths))
        tech_shift_items[tech_shift_item_id] = canonical_item

    for ret_data in _tech_shift_summaries(raw_page_records):
        summary_id = _fallback_id([
            org_id,
            requested_business_date,
            requested_staff_code or 'ALL',
            window_start_at,
            window_end_at,
        ])
        canonical_summary = {
            'tech_shift_summary_id': summary_id,
            'org_id': org_id,
            'requested_business_date': requested_business_date,
            'requested_staff_code': requested_staff_code,
            'window_start_at': window_start_at,
            'window_end_at': window_end_at,
            'source_endpoint_contract_id': TECH_UP_CLOCK_ENDPOINT_ID,
        }
        canonical_summary.update(_flatten_fields(ret_data, summary_field_paths))
        tech_shift_summaries[summary_id] = canonical_summary

    return {
        'tech_shift_item': list(tech_shift_items.values()),
        'tech_shift_summary': list(tech_shift_summaries.values()),
    }


def canonicalize_sales_commission(
    raw_page_records: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
    requested_staff_code: str | None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    field_paths = _dataset_leaf_paths(
        TECH_MARKET_ENDPOINT_ID,
        f'{TECH_MARKET_ENDPOINT_ID}.sales-commission',
        data_platform_root=data_platform_root,
    )
    sales_commissions: dict[str, dict[str, Any]] = {}

    for row_index, row in enumerate(_sales_commission_rows(raw_page_records), start=1):
        sales_commission_id = str(
            row.get('Id')
            or _fallback_id([row.get('SettleNo'), row.get('PersonCode'), row.get('ItemCode'), row_index])
        )
        canonical_row = {
            'sales_commission_id': sales_commission_id,
            'org_id': org_id,
            'requested_business_date': requested_business_date,
            'requested_staff_code': requested_staff_code,
            'source_endpoint_contract_id': TECH_MARKET_ENDPOINT_ID,
        }
        canonical_row.update(_flatten_fields(row, field_paths))
        sales_commissions[sales_commission_id] = canonical_row

    return {
        'sales_commission': list(sales_commissions.values()),
    }


def build_staff_workforce_canonical_artifacts(
    *,
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    org_id: str,
    requested_business_date: str,
    requested_staff_code: str | None,
    window_start_at: str,
    window_end_at: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    staff_artifacts = canonicalize_staff(
        raw_pages_by_endpoint.get(PERSON_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
        data_platform_root=data_platform_root,
    )
    tech_shift_artifacts = canonicalize_tech_shift(
        raw_pages_by_endpoint.get(TECH_UP_CLOCK_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
        requested_staff_code=requested_staff_code,
        window_start_at=window_start_at,
        window_end_at=window_end_at,
        data_platform_root=data_platform_root,
    )
    sales_commission_artifacts = canonicalize_sales_commission(
        raw_pages_by_endpoint.get(TECH_MARKET_ENDPOINT_ID, []),
        org_id=org_id,
        requested_business_date=requested_business_date,
        requested_staff_code=requested_staff_code,
        data_platform_root=data_platform_root,
    )
    return {
        **staff_artifacts,
        **tech_shift_artifacts,
        **sales_commission_artifacts,
    }


__all__ = [
    'PERSON_ENDPOINT_ID',
    'TECH_MARKET_ENDPOINT_ID',
    'TECH_UP_CLOCK_ENDPOINT_ID',
    'build_staff_workforce_canonical_artifacts',
    'canonicalize_sales_commission',
    'canonicalize_staff',
    'canonicalize_tech_shift',
]
