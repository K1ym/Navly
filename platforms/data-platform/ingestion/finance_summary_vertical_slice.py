from __future__ import annotations

import importlib.util
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from connectors.qinqin.qinqin_substrate import (
    build_exception_fetch_result,
    build_signed_request,
    load_seed_backed_qinqin_registry,
    normalize_fetch_page_result,
)
from warehouse.finance_summary_canonical import (
    ACCOUNT_TRADE_ENDPOINT_ID,
    RECHARGE_ENDPOINT_ID,
    build_finance_summary_canonical_artifacts,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
FINANCE_SUMMARY_CAPABILITY_ID = 'navly.store.finance_summary'
FINANCE_SUMMARY_SERVICE_OBJECT_ID = 'navly.service.store.finance_summary'
SOURCE_SYSTEM_ID = 'qinqin.v1_1'
DEFAULT_PAGE_SIZE = 200
FINANCE_SUMMARY_DEPENDENCY_BOUNDARY = {
    'capability_id': FINANCE_SUMMARY_CAPABILITY_ID,
    'default_service_object_id': FINANCE_SUMMARY_SERVICE_OBJECT_ID,
    'dependency_status': 'local_slice_governed',
    'notes': 'ASP-32 keeps the finance_summary dependency boundary local to the finance slice until the global registry is promoted beyond placeholder status.',
    'endpoint_contract_ids': [
        RECHARGE_ENDPOINT_ID,
        ACCOUNT_TRADE_ENDPOINT_ID,
    ],
    'required_canonical_datasets': [
        'recharge_bill',
        'recharge_bill_payment',
        'recharge_bill_sales',
        'recharge_bill_ticket',
        'account_trade',
    ],
}
SOURCE_EMPTY_MESSAGE_MARKERS = ('暂无数据', '无数据', '没有数据', '未查询到数据')
AUTH_MESSAGE_MARKERS = ('授权', '认证', '登录', 'token', '未授权', '无权限', '权限')
SIGN_MESSAGE_MARKERS = ('验签', '签名', 'sign')


class SourceSchemaError(ValueError):
    pass


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
        'navly_data_platform_raw_store_raw_replay_backbone_finance_summary',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load raw-store module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _load_finance_summary_latest_state_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'finance_summary_latest_state.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_finance_summary_latest_state',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _vertical_slice_artifact_store(output_root: str | Path | None):
    return _load_raw_store_backbone_module().VerticalSliceArtifactStore(output_root=output_root)


def _transport_kind(transport: Any) -> str:
    return str(getattr(transport, 'transport_kind', None) or 'legacy')


def _source_empty_response(response_envelope: dict[str, Any]) -> bool:
    source_code = response_envelope.get('Code')
    message = str(response_envelope.get('Msg') or '')
    if source_code in {204, 404} and any(marker in message for marker in SOURCE_EMPTY_MESSAGE_MARKERS):
        return True
    return False


def _source_error(response_envelope: dict[str, Any]) -> dict[str, Any]:
    source_code = response_envelope.get('Code')
    message = str(response_envelope.get('Msg') or 'Source responded with a non-success code.')
    lowered_message = message.lower()
    if source_code in {401, 403} or any(marker.lower() in lowered_message for marker in AUTH_MESSAGE_MARKERS):
        return {
            'taxonomy': 'source_auth_error',
            'code': str(source_code) if source_code is not None else 'AUTH_ERROR',
            'message': message,
            'retryable': False,
            'terminal_outcome_category': 'auth',
        }
    if any(marker.lower() in lowered_message for marker in SIGN_MESSAGE_MARKERS):
        return {
            'taxonomy': 'source_sign_error',
            'code': str(source_code) if source_code is not None else 'SIGN_ERROR',
            'message': message,
            'retryable': False,
            'terminal_outcome_category': 'sign',
        }
    return {
        'taxonomy': 'source_business_error',
        'code': str(source_code) if source_code is not None else 'SOURCE_NON_SUCCESS',
        'message': message,
        'retryable': False,
        'terminal_outcome_category': 'source',
    }


def _schema_error(endpoint_contract_id: str, exc: SourceSchemaError) -> dict[str, Any]:
    return {
        'taxonomy': 'source_schema_error',
        'code': 'INVALID_RESPONSE_SHAPE',
        'message': f'{endpoint_contract_id}: {exc}',
        'retryable': False,
        'terminal_outcome_category': 'schema',
    }


def _normalize_total_and_data_payload(response_envelope: dict[str, Any]) -> dict[str, Any]:
    ret_data = response_envelope.get('RetData')
    if not isinstance(ret_data, dict):
        raise SourceSchemaError('RetData must be an object with Total and Data.')
    rows = ret_data.get('Data')
    if not isinstance(rows, list):
        raise SourceSchemaError('RetData.Data must be an array.')
    total_raw = ret_data.get('Total', len(rows))
    try:
        total = int(total_raw or 0)
    except (TypeError, ValueError) as exc:
        raise SourceSchemaError('RetData.Total must be numeric.') from exc
    return {
        'rows': rows,
        'total': total,
    }


def _normalize_array_record_list_payload(response_envelope: dict[str, Any]) -> dict[str, Any]:
    ret_data = response_envelope.get('RetData')
    if not isinstance(ret_data, list):
        raise SourceSchemaError('RetData must be an array record list.')
    return {
        'rows': ret_data,
        'total': len(ret_data),
    }


FINANCE_PAGE_PAYLOAD_NORMALIZERS = {
    RECHARGE_ENDPOINT_ID: _normalize_total_and_data_payload,
    ACCOUNT_TRADE_ENDPOINT_ID: _normalize_array_record_list_payload,
}


def _normalized_page_payload(
    *,
    endpoint_contract_id: str,
    response_envelope: dict[str, Any],
) -> dict[str, Any]:
    normalizer = FINANCE_PAGE_PAYLOAD_NORMALIZERS.get(endpoint_contract_id)
    if normalizer is None:
        raise KeyError(f'Unsupported finance endpoint_contract_id: {endpoint_contract_id}')
    return normalizer(response_envelope)


def _empty_terminal_result(accumulated_records: int) -> dict[str, Any]:
    if accumulated_records == 0:
        return {
            'endpoint_status': 'source_empty',
            'record_count': 0,
            'terminal_outcome_category': 'source_empty',
        }
    return {
        'endpoint_status': 'completed',
        'record_count': accumulated_records,
        'terminal_outcome_category': 'success',
    }


def _endpoint_uses_pagination(endpoint_contract_id: str, registry: Any) -> bool:
    binding = registry.endpoint_governance_binding(endpoint_contract_id)
    return 'page_index' in binding.required_parameter_keys or 'page_index' in binding.optional_parameter_keys


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


def run_finance_summary_vertical_slice(
    *,
    org_id: str,
    start_time: str,
    end_time: str,
    requested_business_date: str,
    app_secret: str,
    transport: Any,
    page_size: int = DEFAULT_PAGE_SIZE,
    member_card_id: str | None = None,
    trade_type: int | None = None,
    output_root: str | Path | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)
    resolved_transport_kind = _transport_kind(transport)
    artifact_store = _vertical_slice_artifact_store(output_root=output_root)
    ingestion_run = artifact_store.start_ingestion_run(
        capability_id=FINANCE_SUMMARY_CAPABILITY_ID,
        service_object_id=FINANCE_SUMMARY_SERVICE_OBJECT_ID,
        source_system_id=SOURCE_SYSTEM_ID,
        org_id=org_id,
        requested_business_date=requested_business_date,
        window_start_at=start_time,
        window_end_at=end_time,
        transport_kind=resolved_transport_kind,
    )
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    completed_endpoint_runs: list[dict[str, Any]] = []

    for endpoint_contract_id in FINANCE_SUMMARY_DEPENDENCY_BOUNDARY['endpoint_contract_ids']:
        endpoint_run = artifact_store.start_endpoint_run(
            ingestion_run_id=ingestion_run['ingestion_run_id'],
            endpoint_contract_id=endpoint_contract_id,
            org_id=org_id,
            transport_kind=resolved_transport_kind,
        )
        raw_pages_by_endpoint[endpoint_contract_id] = []
        page_index = 1
        accumulated_records = 0
        uses_pagination = _endpoint_uses_pagination(endpoint_contract_id, registry)
        page_size_wire = registry.preferred_wire_name('page_size') if uses_pagination else None
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
                member_card_id=member_card_id if endpoint_contract_id == ACCOUNT_TRADE_ENDPOINT_ID else None,
                trade_type=trade_type if endpoint_contract_id == ACCOUNT_TRADE_ENDPOINT_ID else None,
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

            page_rows: list[dict[str, Any]] = []
            response_total = 0
            schema_error: dict[str, Any] | None = None
            if transport_error is None and response_envelope.get('Code') == 200:
                try:
                    normalized_page_payload = _normalized_page_payload(
                        endpoint_contract_id=endpoint_contract_id,
                        response_envelope=response_envelope,
                    )
                    page_rows = normalized_page_payload['rows']
                    response_total = normalized_page_payload['total']
                except SourceSchemaError as exc:
                    schema_error = _schema_error(endpoint_contract_id, exc)
            response_record_count = len(page_rows)
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

            if _source_empty_response(response_envelope):
                terminal_result = _empty_terminal_result(accumulated_records)
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status=terminal_result['endpoint_status'],
                        page_count=page_index,
                        record_count=terminal_result['record_count'],
                        terminal_outcome_category=terminal_result['terminal_outcome_category'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if transport_error:
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        terminal_outcome_category='transport',
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
                source_error = _source_error(response_envelope)
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        terminal_outcome_category=source_error['terminal_outcome_category'],
                        error_taxonomy=source_error['taxonomy'],
                        error_code=source_error['code'],
                        error_message=source_error['message'],
                        retryable=source_error['retryable'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if schema_error is not None:
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        terminal_outcome_category=schema_error['terminal_outcome_category'],
                        error_taxonomy=schema_error['taxonomy'],
                        error_code=schema_error['code'],
                        error_message=schema_error['message'],
                        retryable=schema_error['retryable'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if response_record_count == 0:
                terminal_result = _empty_terminal_result(accumulated_records)
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status=terminal_result['endpoint_status'],
                        page_count=page_index,
                        record_count=terminal_result['record_count'],
                        terminal_outcome_category=terminal_result['terminal_outcome_category'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            if uses_pagination:
                current_page_size = int(request_envelope['payload'][page_size_wire])
                has_more_pages = response_total > (page_index * current_page_size)
                if has_more_pages:
                    page_index += 1
                    continue

            completed_endpoint_runs.append(
                artifact_store.finalize_endpoint_run(
                    endpoint_run_id=endpoint_run['endpoint_run_id'],
                    endpoint_status='completed',
                    page_count=page_index,
                    record_count=accumulated_records,
                    terminal_outcome_category='success',
                    terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                )
            )
            finalized = True

    finalized_ingestion_run = artifact_store.finalize_ingestion_run(
        ingestion_run_id=ingestion_run['ingestion_run_id'],
        run_status=_run_status(completed_endpoint_runs),
    )
    canonical_artifacts = build_finance_summary_canonical_artifacts(
        raw_pages_by_endpoint=_canonical_input_by_endpoint(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            endpoint_runs=completed_endpoint_runs,
        ),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    latest_state_module = _load_finance_summary_latest_state_module()
    latest_usable_endpoint_states = latest_state_module.build_finance_summary_latest_usable_endpoint_states(
        endpoint_runs=completed_endpoint_runs,
        source_system_id=SOURCE_SYSTEM_ID,
        requested_business_date=requested_business_date,
    )
    finance_summary_prerequisite_state = latest_state_module.build_finance_summary_prerequisite_state(
        capability_id=FINANCE_SUMMARY_CAPABILITY_ID,
        service_object_id=FINANCE_SUMMARY_SERVICE_OBJECT_ID,
        requested_business_date=requested_business_date,
        latest_usable_endpoint_states=latest_usable_endpoint_states,
    )
    artifact_store.write_payload_map({
        'historical-run-truth/ingestion-runs.json': artifact_store.ingestion_runs,
        'historical-run-truth/endpoint-runs.json': artifact_store.endpoint_runs,
        'raw-replay/raw-response-pages.json': artifact_store.raw_response_pages,
        'raw-replay/transport-replay-artifacts.json': artifact_store.transport_replay_artifacts,
        'canonical/recharge_bill.json': canonical_artifacts.get('recharge_bill', []),
        'canonical/recharge_bill_payment.json': canonical_artifacts.get('recharge_bill_payment', []),
        'canonical/recharge_bill_sales.json': canonical_artifacts.get('recharge_bill_sales', []),
        'canonical/recharge_bill_ticket.json': canonical_artifacts.get('recharge_bill_ticket', []),
        'canonical/account_trade.json': canonical_artifacts.get('account_trade', []),
        'latest-state/latest-usable-endpoint-state.json': latest_usable_endpoint_states,
        'latest-state/finance-summary-prerequisite-state.json': finance_summary_prerequisite_state,
    })
    return {
        'request_id': uuid.uuid4().hex,
        'trace_ref': _new_trace_ref(),
        'transport_kind': resolved_transport_kind,
        'capability_id': FINANCE_SUMMARY_CAPABILITY_ID,
        'service_object_id': FINANCE_SUMMARY_SERVICE_OBJECT_ID,
        'dependency_boundary': FINANCE_SUMMARY_DEPENDENCY_BOUNDARY,
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
            'finance_summary_prerequisite_state': finance_summary_prerequisite_state,
        },
    }


__all__ = [
    'DEFAULT_PAGE_SIZE',
    'FINANCE_SUMMARY_CAPABILITY_ID',
    'FINANCE_SUMMARY_DEPENDENCY_BOUNDARY',
    'FINANCE_SUMMARY_SERVICE_OBJECT_ID',
    'run_finance_summary_vertical_slice',
]
