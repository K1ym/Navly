from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_latest_usable_endpoint_states, build_vertical_slice_backbone_state
from connectors.qinqin.qinqin_substrate import (
    build_exception_fetch_result,
    build_signed_request,
    load_seed_backed_qinqin_registry,
    normalize_fetch_page_result,
)
from warehouse.staff_workforce_canonical_backbone import (
    PERSON_ENDPOINT_ID,
    TECH_MARKET_ENDPOINT_ID,
    TECH_UP_CLOCK_ENDPOINT_ID,
    build_staff_workforce_canonical_artifacts,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
VERTICAL_SLICE_CAPABILITY_ID = 'navly.store.staff_board'
DEFAULT_REQUIRED_CANONICAL_DATASETS = (
    'staff',
    'staff_item',
    'tech_shift_item',
    'tech_shift_summary',
    'sales_commission',
)
DEFAULT_PAGE_SIZE = 200
SOURCE_EMPTY_CODES = {'404', '404.0'}
SOURCE_EMPTY_KEYWORDS = ('暂无数据', '无数据', '没有数据', '未查询到数据')
SOURCE_SIGN_KEYWORDS = ('验签', '签名', 'sign')
SOURCE_AUTH_KEYWORDS = ('未授权', '无权限', '鉴权', '认证', 'token', 'authorization', 'auth')


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_staff_board_dependency_entry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    capability_registry = _load_json(data_platform_root / 'directory' / 'capability-registry.seed.json')
    capability_entry = next(
        (
            entry
            for entry in capability_registry['entries']
            if entry['capability_id'] == VERTICAL_SLICE_CAPABILITY_ID
        ),
        None,
    )
    if capability_entry is None:
        raise ValueError(
            f'Missing capability registry entry for {VERTICAL_SLICE_CAPABILITY_ID} in {data_platform_root / "directory" / "capability-registry.seed.json"}.'
        )
    field_landing = _load_json(data_platform_root / 'directory' / 'field-landing-policy.seed.json')
    endpoint_order = [
        entry['endpoint_contract_id']
        for entry in _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')['entries']
    ]
    required_dataset_set = set(DEFAULT_REQUIRED_CANONICAL_DATASETS)
    endpoint_ids = {
        entry['endpoint_contract_id']
        for entry in field_landing['entries']
        if set(entry.get('target_dataset') or []).intersection(required_dataset_set)
    }
    ordered_endpoint_ids = [
        endpoint_contract_id
        for endpoint_contract_id in endpoint_order
        if endpoint_contract_id in endpoint_ids
    ]
    return {
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'dependency_status': 'derived_from_field_landing_policy',
        'default_service_object_id': capability_entry['default_service_object_id'],
        'endpoint_contract_ids': ordered_endpoint_ids,
        'required_canonical_datasets': list(DEFAULT_REQUIRED_CANONICAL_DATASETS),
    }


def _new_trace_ref() -> str:
    return f'navly:trace:{uuid.uuid4().hex[:16]}'


def _run_status(endpoint_runs: list[dict[str, Any]]) -> str:
    if not endpoint_runs:
        return 'failed'
    statuses = {entry['endpoint_status'] for entry in endpoint_runs}
    if statuses.issubset({'completed', 'source_empty'}):
        return 'completed'
    if 'completed' in statuses or 'source_empty' in statuses:
        return 'partial_failed'
    return 'failed'


@lru_cache(maxsize=1)
def _load_raw_store_backbone_module():
    module_path = DATA_PLATFORM_ROOT / 'raw-store' / 'raw_replay_backbone.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_raw_store_raw_replay_backbone_staff_board',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load raw-store module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _vertical_slice_artifact_store(output_root: str | Path | None):
    return _load_raw_store_backbone_module().VerticalSliceArtifactStore(output_root=output_root)


def _transport_kind(transport: Any) -> str:
    return str(getattr(transport, 'transport_kind', None) or 'legacy')


def _source_code_string(response_envelope: dict[str, Any]) -> str:
    code = response_envelope.get('Code')
    if code is None:
        return ''
    return str(code).strip()


def _source_message(response_envelope: dict[str, Any]) -> str:
    return str(response_envelope.get('Msg') or '').strip()


def _source_empty_response(response_envelope: dict[str, Any]) -> bool:
    source_code = _source_code_string(response_envelope)
    if source_code in SOURCE_EMPTY_CODES:
        return True
    message = _source_message(response_envelope)
    return any(keyword in message for keyword in SOURCE_EMPTY_KEYWORDS)


def _source_failure(response_envelope: dict[str, Any]) -> dict[str, Any]:
    source_code = _source_code_string(response_envelope) or 'SOURCE_NON_SUCCESS'
    source_message = _source_message(response_envelope) or 'Source responded with a non-success code.'
    if _source_empty_response(response_envelope):
        return {
            'endpoint_status': 'source_empty',
            'error_taxonomy': None,
            'error_code': None,
            'error_message': None,
            'retryable': False,
        }

    message_lower = source_message.lower()
    if any(keyword in source_message for keyword in SOURCE_SIGN_KEYWORDS) or any(
        keyword in message_lower for keyword in SOURCE_SIGN_KEYWORDS
    ):
        taxonomy = 'source_sign_error'
    elif any(keyword in source_message for keyword in SOURCE_AUTH_KEYWORDS) or any(
        keyword in message_lower for keyword in SOURCE_AUTH_KEYWORDS
    ):
        taxonomy = 'source_auth_error'
    else:
        taxonomy = 'source_business_error'
    return {
        'endpoint_status': 'failed',
        'error_taxonomy': taxonomy,
        'error_code': source_code,
        'error_message': source_message,
        'retryable': False,
    }


def _schema_error(endpoint_contract_id: str, detail: str) -> dict[str, Any]:
    return {
        'endpoint_status': 'failed',
        'error_taxonomy': 'source_schema_error',
        'error_code': 'INVALID_RESPONSE_SHAPE',
        'error_message': f'{endpoint_contract_id} returned an unexpected response shape: {detail}.',
        'retryable': False,
    }


def _extract_page_rows(endpoint_contract_id: str, response_envelope: dict[str, Any]) -> dict[str, Any]:
    ret_data = response_envelope.get('RetData')
    if endpoint_contract_id == PERSON_ENDPOINT_ID:
        if not isinstance(ret_data, list):
            return _schema_error(endpoint_contract_id, 'RetData must be an array')
        if any(not isinstance(row, dict) for row in ret_data):
            return _schema_error(endpoint_contract_id, 'RetData rows must be objects')
        return {
            'endpoint_status': 'completed',
            'record_count': len(ret_data),
            'page_rows': ret_data,
        }

    if endpoint_contract_id == TECH_UP_CLOCK_ENDPOINT_ID:
        if not isinstance(ret_data, dict):
            return _schema_error(endpoint_contract_id, 'RetData must be an object')
        items = ret_data.get('Items', [])
        if items is None:
            items = []
        if not isinstance(items, list):
            return _schema_error(endpoint_contract_id, 'RetData.Items must be an array')
        if any(not isinstance(row, dict) for row in items):
            return _schema_error(endpoint_contract_id, 'RetData.Items rows must be objects')
        for summary_key in ('Main', 'Extra'):
            summary_block = ret_data.get(summary_key)
            if summary_block is not None and not isinstance(summary_block, dict):
                return _schema_error(endpoint_contract_id, f'RetData.{summary_key} must be an object')
        return {
            'endpoint_status': 'completed',
            'record_count': len(items),
            'page_rows': items,
        }

    if endpoint_contract_id == TECH_MARKET_ENDPOINT_ID:
        if not isinstance(ret_data, list):
            return _schema_error(endpoint_contract_id, 'RetData must be an array')
        if any(not isinstance(row, dict) for row in ret_data):
            return _schema_error(endpoint_contract_id, 'RetData rows must be objects')
        return {
            'endpoint_status': 'completed',
            'record_count': len(ret_data),
            'page_rows': ret_data,
        }

    return _schema_error(endpoint_contract_id, 'endpoint shape handler is not implemented')


def _canonical_input_by_endpoint(
    *,
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    endpoint_runs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    usable_endpoint_ids = {
        endpoint_run['endpoint_contract_id']
        for endpoint_run in endpoint_runs
        if endpoint_run['endpoint_status'] in {'completed', 'source_empty'}
    }
    return {
        endpoint_contract_id: pages if endpoint_contract_id in usable_endpoint_ids else []
        for endpoint_contract_id, pages in raw_pages_by_endpoint.items()
    }


def _pagination_total(response_envelope: dict[str, Any], default_total: int) -> int:
    ret_data = response_envelope.get('RetData')
    if isinstance(ret_data, dict):
        return int(ret_data.get('Total', default_total) or 0)
    return default_total


def run_staff_board_vertical_slice(
    *,
    org_id: str,
    start_time: str,
    end_time: str,
    requested_business_date: str,
    app_secret: str,
    transport: Any,
    staff_code: str | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    output_root: str | Path | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    dependency_entry = _load_staff_board_dependency_entry(data_platform_root=data_platform_root)
    service_object_id = dependency_entry['default_service_object_id']
    registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)
    resolved_transport_kind = _transport_kind(transport)
    artifact_store = _vertical_slice_artifact_store(output_root=output_root)
    source_system_id = registry.endpoint_contract(dependency_entry['endpoint_contract_ids'][0]).source_system_id
    ingestion_run = artifact_store.start_ingestion_run(
        capability_id=VERTICAL_SLICE_CAPABILITY_ID,
        service_object_id=service_object_id,
        source_system_id=source_system_id,
        org_id=org_id,
        requested_business_date=requested_business_date,
        window_start_at=start_time,
        window_end_at=end_time,
        transport_kind=resolved_transport_kind,
    )

    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    completed_endpoint_runs: list[dict[str, Any]] = []

    for endpoint_contract_id in dependency_entry['endpoint_contract_ids']:
        endpoint_run = artifact_store.start_endpoint_run(
            ingestion_run_id=ingestion_run['ingestion_run_id'],
            endpoint_contract_id=endpoint_contract_id,
            org_id=org_id,
            transport_kind=resolved_transport_kind,
        )
        raw_pages_by_endpoint[endpoint_contract_id] = []
        uses_pagination = registry.uses_pagination(endpoint_contract_id)
        page_index = 1
        accumulated_records = 0
        finalized = False

        while not finalized:
            request_envelope = build_signed_request(
                endpoint_contract_id=endpoint_contract_id,
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                page_index=page_index if uses_pagination else None,
                page_size=page_size if uses_pagination else None,
                app_secret=app_secret,
                staff_code=staff_code,
                data_platform_root=data_platform_root,
            )

            try:
                fetch_result = transport.fetch_page(endpoint_contract_id, request_envelope['payload'])
            except Exception as exc:
                fetch_result = build_exception_fetch_result(
                    exception=exc,
                    request_envelope=request_envelope,
                    default_transport_kind=resolved_transport_kind,
                )

            normalized_fetch_result = normalize_fetch_page_result(
                fetch_result=fetch_result,
                request_envelope=request_envelope,
                default_transport_kind=resolved_transport_kind,
            )
            transport_replay_artifact = artifact_store.append_transport_replay_artifact(
                endpoint_run_id=endpoint_run['endpoint_run_id'],
                endpoint_contract_id=endpoint_contract_id,
                page_index=page_index,
                replay_artifact=normalized_fetch_result['replay_artifact'],
            )
            response_envelope = normalized_fetch_result['response_envelope']
            transport_error = normalized_fetch_result.get('transport_error')
            extracted_page = None
            response_record_count = 0
            if not transport_error and response_envelope.get('Code') == 200:
                extracted_page = _extract_page_rows(endpoint_contract_id, response_envelope)
                response_record_count = extracted_page.get('record_count', 0)
            accumulated_records += response_record_count

            raw_page_record = artifact_store.append_raw_response_page(
                endpoint_run_id=endpoint_run['endpoint_run_id'],
                endpoint_contract_id=endpoint_contract_id,
                page_index=page_index,
                transport_kind=transport_replay_artifact['transport_kind'],
                replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                request_envelope=request_envelope,
                response_envelope=response_envelope,
                response_record_count=response_record_count,
                source_response_code=response_envelope.get('Code'),
                source_response_message=response_envelope.get('Msg'),
            )
            raw_pages_by_endpoint[endpoint_contract_id].append(raw_page_record)

            if transport_error:
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        error_taxonomy=transport_error.get('taxonomy'),
                        error_code=transport_error.get('code'),
                        error_message=transport_error.get('message'),
                        retryable=transport_error.get('retryable'),
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if response_envelope.get('Code') != 200:
                source_failure = _source_failure(response_envelope)
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status=source_failure['endpoint_status'],
                        page_count=page_index,
                        record_count=accumulated_records,
                        error_taxonomy=source_failure['error_taxonomy'],
                        error_code=source_failure['error_code'],
                        error_message=source_failure['error_message'],
                        retryable=source_failure['retryable'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if extracted_page is None or extracted_page['endpoint_status'] == 'failed':
                schema_failure = extracted_page or _schema_error(endpoint_contract_id, 'missing extracted page result')
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        error_taxonomy=schema_failure['error_taxonomy'],
                        error_code=schema_failure['error_code'],
                        error_message=schema_failure['error_message'],
                        retryable=schema_failure['retryable'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if response_record_count == 0:
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='source_empty' if accumulated_records == 0 else 'completed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if uses_pagination:
                total = _pagination_total(response_envelope, response_record_count)
                current_page_size = int(request_envelope['payload'][registry.preferred_wire_name('page_size')])
                if total > page_index * current_page_size:
                    page_index += 1
                    continue

            completed_endpoint_runs.append(
                artifact_store.finalize_endpoint_run(
                    endpoint_run_id=endpoint_run['endpoint_run_id'],
                    endpoint_status='completed',
                    page_count=page_index,
                    record_count=accumulated_records,
                    terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                )
            )
            finalized = True

    finalized_ingestion_run = artifact_store.finalize_ingestion_run(
        ingestion_run_id=ingestion_run['ingestion_run_id'],
        run_status=_run_status(completed_endpoint_runs),
    )
    canonical_artifacts = build_staff_workforce_canonical_artifacts(
        raw_pages_by_endpoint=_canonical_input_by_endpoint(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            endpoint_runs=completed_endpoint_runs,
        ),
        org_id=org_id,
        requested_business_date=requested_business_date,
        requested_staff_code=staff_code,
        window_start_at=start_time,
        window_end_at=end_time,
        data_platform_root=data_platform_root,
    )
    latest_usable_endpoint_states = build_latest_usable_endpoint_states(
        endpoint_runs=completed_endpoint_runs,
        source_system_id=source_system_id,
        requested_business_date=requested_business_date,
    )
    vertical_slice_backbone_state = build_vertical_slice_backbone_state(
        capability_id=VERTICAL_SLICE_CAPABILITY_ID,
        service_object_id=service_object_id,
        requested_business_date=requested_business_date,
        latest_usable_endpoint_states=latest_usable_endpoint_states,
    )
    artifact_store.write_payload_map({
        'historical-run-truth/ingestion-runs.json': artifact_store.ingestion_runs,
        'historical-run-truth/endpoint-runs.json': artifact_store.endpoint_runs,
        'raw-replay/raw-response-pages.json': artifact_store.raw_response_pages,
        'raw-replay/transport-replay-artifacts.json': artifact_store.transport_replay_artifacts,
        'canonical/staff.json': canonical_artifacts.get('staff', []),
        'canonical/staff_item.json': canonical_artifacts.get('staff_item', []),
        'canonical/tech_shift_item.json': canonical_artifacts.get('tech_shift_item', []),
        'canonical/tech_shift_summary.json': canonical_artifacts.get('tech_shift_summary', []),
        'canonical/sales_commission.json': canonical_artifacts.get('sales_commission', []),
        'latest-state/latest-usable-endpoint-state.json': latest_usable_endpoint_states,
        'latest-state/vertical-slice-backbone-state.json': vertical_slice_backbone_state,
    })
    return {
        'request_id': uuid.uuid4().hex,
        'trace_ref': _new_trace_ref(),
        'transport_kind': resolved_transport_kind,
        'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
        'service_object_id': service_object_id,
        'dependency_entry': dependency_entry,
        'staff_code': staff_code,
        'historical_run_truth': {
            'ingestion_run': finalized_ingestion_run,
            'endpoint_runs': completed_endpoint_runs,
        },
        'raw_replay': {
            'raw_response_pages': artifact_store.raw_response_pages,
            'transport_replay_artifacts': artifact_store.transport_replay_artifacts,
        },
        'canonical_artifacts': canonical_artifacts,
        'latest_state_artifacts': {
            'latest_usable_endpoint_states': latest_usable_endpoint_states,
            'vertical_slice_backbone_state': vertical_slice_backbone_state,
        },
    }


__all__ = [
    'DEFAULT_PAGE_SIZE',
    'VERTICAL_SLICE_CAPABILITY_ID',
    'run_staff_board_vertical_slice',
]
