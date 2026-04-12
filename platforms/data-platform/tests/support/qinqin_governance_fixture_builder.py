from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[2]

ROOT_CONTAINER_PATH_KINDS = {
    'payload_root',
    'record_collection',
    'nested_record_collection',
    'summary_object',
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def endpoint_contract_ids() -> list[str]:
    return [
        entry['endpoint_contract_id']
        for entry in _load_json(DATA_PLATFORM_ROOT / 'directory' / 'endpoint-contracts.seed.json')['entries']
        if entry['domain'] != 'shared'
    ]


@lru_cache(maxsize=1)
def structured_target_ids() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for entry in _load_json(DATA_PLATFORM_ROOT / 'directory' / 'endpoint-contracts.seed.json')['entries']:
        for structured_target in entry.get('structured_targets', []):
            if structured_target in seen:
                continue
            seen.add(structured_target)
            ordered.append(structured_target)
    return ordered


def _sample_value(data_type: str, field_path: str, value_suffix: str) -> Any:
    leaf = field_path.split('.')[-1].replace('-', '_')
    if data_type == 'string':
        return f'{leaf.lower()}_{value_suffix}'
    if data_type == 'number':
        return 1
    if data_type == 'boolean':
        return True
    if data_type == 'array':
        return []
    return {}


def _set_path_value(root: dict[str, Any], field_path: str, value: Any, *, replace: bool = False) -> None:
    parts = field_path.split('.')
    current: Any = root
    for index, part in enumerate(parts):
        if isinstance(current, list):
            if not current or not isinstance(current[0], (dict, list)):
                current.append({})
            current = current[0]

        is_last = index == len(parts) - 1
        if is_last:
            if replace or part not in current:
                current[part] = value
            return

        if part not in current or not isinstance(current[part], (dict, list)):
            current[part] = {}
        current = current[part]


def build_aligned_response_bundle(*, value_suffix: str = 'sample') -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    field_catalog = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'endpoint-field-catalog.seed.json')

    for entry in field_catalog['entries']:
        response_envelope: dict[str, Any] = {}
        for field in entry['response_fields']:
            if field['path_kind'] not in ROOT_CONTAINER_PATH_KINDS:
                continue
            container: Any = [] if field['data_type'] == 'array' else {}
            _set_path_value(response_envelope, field['field_path'], container, replace=True)
        for field in entry['response_fields']:
            if field['path_kind'] in ROOT_CONTAINER_PATH_KINDS:
                continue
            value = 1 if field['path_kind'] == 'page_total' else _sample_value(field['data_type'], field['field_path'], value_suffix)
            _set_path_value(response_envelope, field['field_path'], value, replace=True)
        response_envelope.setdefault('Code', 200)
        response_envelope.setdefault('Msg', '操作成功')
        bundle[entry['endpoint_contract_id']] = response_envelope

    return bundle


def build_raw_pages_by_endpoint(
    *,
    org_id: str,
    value_suffix: str = 'sample',
) -> dict[str, list[dict[str, Any]]]:
    bundle = build_aligned_response_bundle(value_suffix=value_suffix)
    raw_pages: dict[str, list[dict[str, Any]]] = {}

    for endpoint_contract_id, response_envelope in bundle.items():
        ret_data = response_envelope.get('RetData')
        if isinstance(ret_data, dict) and isinstance(ret_data.get('Data'), list):
            record_count = len(ret_data['Data'])
        elif isinstance(ret_data, list):
            record_count = len(ret_data)
        elif isinstance(ret_data, dict) and ret_data:
            record_count = 1
        else:
            record_count = 0

        suffix = endpoint_contract_id.split('.')[-1]
        raw_pages[endpoint_contract_id] = [{
            'raw_page_id': f'raw_{org_id}_{suffix}',
            'endpoint_contract_id': endpoint_contract_id,
            'page_index': 1,
            'replay_artifact_id': f'replay_{org_id}_{suffix}',
            'request_envelope': {
                'payload': {
                    'OrgId': org_id,
                },
            },
            'response_envelope': response_envelope,
            'response_record_count': record_count,
        }]

    return raw_pages


def build_endpoint_runs(
    *,
    org_id: str,
    status_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    overrides = status_overrides or {}
    endpoint_runs: list[dict[str, Any]] = []
    for endpoint_contract_id in endpoint_contract_ids():
        override = overrides.get(endpoint_contract_id, {})
        suffix = endpoint_contract_id.split('.')[-1]
        endpoint_runs.append({
            'endpoint_run_id': f'er_{org_id}_{suffix}',
            'endpoint_run_trace_ref': f'navly:run-trace:endpoint-run:{org_id}:{endpoint_contract_id}',
            'endpoint_contract_id': endpoint_contract_id,
            'org_id': org_id,
            'endpoint_status': 'completed',
            'error_taxonomy': None,
            'error_code': None,
            'error_message': None,
            **override,
        })
    return endpoint_runs

