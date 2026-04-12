from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SYSTEM_ID = 'qinqin.v1_1'

ROOT_PATH_KINDS = {
    'record_collection',
    'nested_record_collection',
    'summary_object',
}
COLLECTION_ROOT_PATH_KINDS = {
    'record_collection',
    'nested_record_collection',
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=4)
def _target_datasets(data_platform_root: Path = DATA_PLATFORM_ROOT) -> tuple[str, ...]:
    endpoint_contracts = _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')
    ordered: list[str] = []
    seen: set[str] = set()
    for entry in endpoint_contracts['entries']:
        for target_dataset in entry.get('structured_targets', []):
            if target_dataset in seen:
                continue
            seen.add(target_dataset)
            ordered.append(target_dataset)
    return tuple(ordered)


@lru_cache(maxsize=4)
def _structured_policy_descriptors(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, list[dict[str, Any]]]:
    landing_policies = {
        entry['policy_id']: entry
        for entry in _load_json(data_platform_root / 'directory' / 'field-landing-policy.seed.json')['entries']
        if entry['target_layer'] == 'L1'
    }
    descriptors: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in _load_json(data_platform_root / 'directory' / 'endpoint-field-catalog.seed.json')['entries']:
        fields_by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for field in entry['response_fields']:
            policy_id = field['landing_policy_id']
            if policy_id not in landing_policies:
                continue
            fields_by_policy[policy_id].append(field)
        for policy_id, fields in fields_by_policy.items():
            descriptors[entry['endpoint_contract_id']].append({
                'policy_id': policy_id,
                'endpoint_contract_id': entry['endpoint_contract_id'],
                'target_dataset': landing_policies[policy_id]['target_dataset'][0],
                'field_selector': landing_policies[policy_id]['field_selector'],
                'fields': fields,
                'root_paths': [
                    field['field_path']
                    for field in fields
                    if field['path_kind'] in ROOT_PATH_KINDS
                ],
                'collection_root_paths': [
                    field['field_path']
                    for field in fields
                    if field['path_kind'] in COLLECTION_ROOT_PATH_KINDS
                ],
            })
    return dict(descriptors)


def _normalize_field_key(field_path: str) -> str:
    parts = field_path.split('.')
    if parts and parts[0] == 'RetData':
        parts = parts[1:]
    return '__'.join(parts) if parts else field_path.replace('.', '__')


def _iter_path_matches(
    node: Any,
    parts: list[str],
    *,
    source_path: str = '',
    parent_path: str | None = None,
    parent_value: Any = None,
) -> list[dict[str, Any]]:
    if not parts:
        return [{
            'value': node,
            'source_path': source_path,
            'parent_path': parent_path,
            'parent_value': parent_value,
        }]
    if isinstance(node, list):
        matches: list[dict[str, Any]] = []
        for index, item in enumerate(node):
            item_path = f'{source_path}[{index}]' if source_path else f'[{index}]'
            matches.extend(
                _iter_path_matches(
                    item,
                    parts,
                    source_path=item_path,
                    parent_path=source_path or None,
                    parent_value=node,
                )
            )
        return matches
    if isinstance(node, dict):
        head = parts[0]
        if head not in node:
            return []
        child_path = f'{source_path}.{head}' if source_path else head
        return _iter_path_matches(
            node[head],
            parts[1:],
            source_path=child_path,
            parent_path=source_path or None,
            parent_value=node,
        )
    return []


def _expand_row_roots(response_envelope: dict[str, Any], root_path: str) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    for match in _iter_path_matches(response_envelope, root_path.split('.')):
        value = match['value']
        if isinstance(value, list):
            for index, item in enumerate(value):
                roots.append({
                    'value': item,
                    'policy_root_path': root_path,
                    'source_path': f"{match['source_path']}[{index}]",
                    'parent_path': match['parent_path'],
                    'parent_value': match['parent_value'],
                })
        else:
            roots.append({
                **match,
                'policy_root_path': root_path,
            })
    return roots


def _extract_relative_value(node: Any, relative_path: str) -> Any:
    matches = _iter_path_matches(node, relative_path.split('.')) if relative_path else [{'value': node}]
    if not matches:
        return None
    return matches[0]['value']


def _scalar_parent_context(parent_value: Any) -> dict[str, Any]:
    if not isinstance(parent_value, dict):
        return {}
    return {
        key: value
        for key, value in parent_value.items()
        if not isinstance(value, (dict, list))
    }


def _source_index(source_record_path: str) -> int:
    if '[' not in source_record_path or ']' not in source_record_path:
        return 0
    tail = source_record_path.rsplit('[', 1)[-1].split(']', 1)[0]
    try:
        return int(tail)
    except ValueError:
        return 0


def _enrich_member_insight_canonical_fields(
    *,
    target_dataset: str,
    field_values: dict[str, Any],
    parent_context: dict[str, Any],
    source_record_path: str,
    row_value: Any,
    endpoint_contract_id: str,
    requested_business_date: str,
) -> dict[str, Any]:
    if target_dataset == 'customer':
        return {
            'customer_id': field_values.get('Data__Id'),
            'org_id': field_values.get('Data__OrgId'),
            'phone': field_values.get('Data__Phone'),
            'name': field_values.get('Data__Name'),
            'stored_amount': field_values.get('Data__StoredAmount'),
            'consume_amount': field_values.get('Data__ConsumeAmount'),
            'last_consume_time': field_values.get('Data__LastConsumeTime'),
            'registered_at': field_values.get('Data__CTime'),
            'marketer_id': field_values.get('Data__MarketerId'),
            'marketer_name': field_values.get('Data__MarketerName'),
            'source_endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
        }
    if target_dataset == 'customer_card':
        return {
            'customer_card_id': field_values.get('Data__Storeds__Id') or field_values.get('Data__Equitys__Id'),
            'customer_id': parent_context.get('Id'),
            'card_group': 'stored_card' if 'Data__Storeds__Id' in field_values else 'equity_card',
            'org_id': field_values.get('Data__Storeds__OrgId') or field_values.get('Data__Equitys__OrgId'),
            'card_type_id': field_values.get('Data__Storeds__CardTypeId') or field_values.get('Data__Equitys__CardTypeId'),
            'card_type_name': field_values.get('Data__Storeds__CardTypeName') or field_values.get('Data__Equitys__CardTypeName'),
            'card_no': field_values.get('Data__Storeds__CardNo') or field_values.get('Data__Equitys__CardNo'),
            'balance': field_values.get('Data__Storeds__Balance') or field_values.get('Data__Equitys__Balance'),
            'total_amount': field_values.get('Data__Storeds__Total') or field_values.get('Data__Equitys__Total'),
            'consume_amount': field_values.get('Data__Storeds__Consume') or field_values.get('Data__Equitys__Consume'),
            'opened_at': field_values.get('Data__Storeds__OpenTime') or field_values.get('Data__Equitys__OpenTime'),
            'expires_at': field_values.get('Data__Storeds__ExpireTime') or field_values.get('Data__Equitys__ExpireTime'),
            'state': field_values.get('Data__Storeds__State') or field_values.get('Data__Equitys__State'),
            'source_endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
        }
    if target_dataset == 'consume_bill':
        return {
            'consume_bill_id': field_values.get('Data__SettleId'),
            'settle_no': field_values.get('Data__SettleNo'),
            'org_id': parent_context.get('OrgId') or field_values.get('Data__OrgId'),
            'consume_amount': field_values.get('Data__Consume'),
            'pay_amount': field_values.get('Data__Pay'),
            'discount_amount': field_values.get('Data__DiscountAmount'),
            'deduction_amount': field_values.get('Data__DeductionAmount'),
            'ticket_amount': field_values.get('Data__TicketAmount'),
            'created_at': field_values.get('Data__CTime'),
            'settled_at': field_values.get('Data__OptTime'),
            'room_code': field_values.get('Data__RoomCode'),
            'hand_card_code': field_values.get('Data__HandCardCode'),
            'operator_code': field_values.get('Data__OptCode'),
            'operator_name': field_values.get('Data__OptName'),
            'source_endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
        }
    if target_dataset == 'consume_bill_payment':
        return {
            'consume_bill_id': parent_context.get('SettleId'),
            'payment_sequence': _source_index(source_record_path),
            'payment_name': field_values.get('Data__Payments__Name'),
            'payment_amount': field_values.get('Data__Payments__Amount'),
            'payment_type': field_values.get('Data__Payments__PaymentType'),
            'payment_source': field_values.get('Data__Payments__PyamentSource'),
            'source_endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
        }
    if target_dataset == 'consume_bill_info':
        return {
            'consume_bill_id': parent_context.get('SettleId'),
            'info_sequence': _source_index(source_record_path),
            'payload': row_value if isinstance(row_value, dict) else {},
            'source_endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
        }
    return {}


def _landing_row(
    *,
    page_record: dict[str, Any],
    descriptor: dict[str, Any],
    row_root: dict[str, Any] | None,
    org_id: str,
    requested_business_date: str,
) -> dict[str, Any]:
    field_values: dict[str, Any] = {}
    if row_root is None:
        response_envelope = page_record['response_envelope']
        for field in descriptor['fields']:
            if field['path_kind'] in ROOT_PATH_KINDS:
                continue
            matches = _iter_path_matches(response_envelope, field['field_path'].split('.'))
            if matches:
                field_values[_normalize_field_key(field['field_path'])] = matches[0]['value']
    else:
        root_path = row_root['policy_root_path']
        for field in descriptor['fields']:
            if field['path_kind'] in ROOT_PATH_KINDS:
                continue
            field_path = field['field_path']
            relative_path = field_path[len(root_path) + 1:] if field_path.startswith(f'{root_path}.') else ''
            value = _extract_relative_value(row_root['value'], relative_path)
            if value is not None:
                field_values[_normalize_field_key(field['field_path'])] = value

    source_record_path = row_root['source_path'] if row_root is not None else f"page:{page_record['page_index']}"
    parent_context = _scalar_parent_context(row_root.get('parent_value') if row_root else None)
    record = {
        'landing_row_id': f"{descriptor['policy_id']}::{page_record['raw_page_id']}::{source_record_path}",
        'source_system_id': SOURCE_SYSTEM_ID,
        'endpoint_contract_id': descriptor['endpoint_contract_id'],
        'target_dataset': descriptor['target_dataset'],
        'landing_policy_id': descriptor['policy_id'],
        'org_id': org_id,
        'requested_business_date': requested_business_date,
        'page_index': page_record['page_index'],
        'raw_page_id': page_record['raw_page_id'],
        'replay_artifact_id': page_record.get('replay_artifact_id'),
        'source_record_path': source_record_path,
        'parent_source_path': row_root.get('parent_path') if row_root else None,
        'field_values': field_values,
        'parent_context': parent_context,
        **_enrich_member_insight_canonical_fields(
            target_dataset=descriptor['target_dataset'],
            field_values=field_values,
            parent_context=parent_context,
            source_record_path=source_record_path,
            row_value=row_root.get('value') if row_root else None,
            endpoint_contract_id=descriptor['endpoint_contract_id'],
            requested_business_date=requested_business_date,
        ),
    }
    if descriptor['target_dataset'] == 'customer_card' and row_root is None and not field_values:
        return {}
    return record


def build_qinqin_structured_target_artifacts(
    *,
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    org_id: str,
    requested_business_date: str,
    endpoint_contract_ids: list[str] | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    included_endpoint_ids = set(endpoint_contract_ids or raw_pages_by_endpoint.keys())
    artifacts = {
        target_dataset: []
        for target_dataset in _target_datasets(data_platform_root=data_platform_root)
    }

    for endpoint_contract_id in included_endpoint_ids:
        for descriptor in _structured_policy_descriptors(data_platform_root=data_platform_root).get(endpoint_contract_id, []):
            target_rows = artifacts[descriptor['target_dataset']]
            for page_record in raw_pages_by_endpoint.get(endpoint_contract_id, []):
                row_roots: list[dict[str, Any]] = []
                for root_path in descriptor['collection_root_paths']:
                    row_roots.extend(_expand_row_roots(page_record['response_envelope'], root_path))
                if row_roots:
                    for row_root in row_roots:
                        target_rows.append(
                            _landing_row(
                                page_record=page_record,
                                descriptor=descriptor,
                                row_root=row_root,
                                org_id=org_id,
                                requested_business_date=requested_business_date,
                            )
                        )
                    continue
                row = _landing_row(
                    page_record=page_record,
                    descriptor=descriptor,
                    row_root=None,
                    org_id=org_id,
                    requested_business_date=requested_business_date,
                )
                if row:
                    target_rows.append(row)

    return artifacts


__all__ = [
    'build_qinqin_structured_target_artifacts',
]
