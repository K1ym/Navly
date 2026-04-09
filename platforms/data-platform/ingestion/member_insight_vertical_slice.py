from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_latest_usable_endpoint_states, build_vertical_slice_backbone_state
from backbone_support.member_insight_canonical_backbone import build_member_insight_canonical_artifacts
from connectors.qinqin.qinqin_substrate import (
    build_exception_fetch_result,
    build_signed_request,
    load_seed_backed_qinqin_registry,
    normalize_fetch_page_result,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
VERTICAL_SLICE_CAPABILITY_ID = 'navly.store.member_insight'
SOURCE_SYSTEM_ID = 'qinqin.v1_1'
DEFAULT_PAGE_SIZE = 200


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_member_insight_dependency_entry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    registry = _load_json(data_platform_root / 'directory' / 'capability-dependency-registry.placeholder.json')
    for entry in registry['entries']:
        if entry['capability_id'] == VERTICAL_SLICE_CAPABILITY_ID:
            return entry
    raise KeyError(f'Missing dependency entry for {VERTICAL_SLICE_CAPABILITY_ID}')


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
        'navly_data_platform_raw_store_raw_replay_backbone',
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


def _source_business_error(response_envelope: dict[str, Any]) -> dict[str, Any]:
    source_code = response_envelope.get('Code')
    return {
        'taxonomy': 'source_business_error',
        'code': str(source_code) if source_code is not None else 'SOURCE_NON_SUCCESS',
        'message': str(response_envelope.get('Msg') or 'Source responded with a non-success code.'),
        'retryable': False,
    }


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


def run_member_insight_vertical_slice(
    *,
    org_id: str,
    start_time: str,
    end_time: str,
    requested_business_date: str,
    app_secret: str,
    transport: Any,
    page_size: int = DEFAULT_PAGE_SIZE,
    output_root: str | Path | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    dependency_entry = _load_member_insight_dependency_entry(data_platform_root=data_platform_root)
    service_object_id = dependency_entry['default_service_object_id']
    registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)
    resolved_transport_kind = _transport_kind(transport)
    artifact_store = _vertical_slice_artifact_store(output_root=output_root)
    ingestion_run = artifact_store.start_ingestion_run(
        capability_id=VERTICAL_SLICE_CAPABILITY_ID,
        service_object_id=service_object_id,
        source_system_id=SOURCE_SYSTEM_ID,
        org_id=org_id,
        requested_business_date=requested_business_date,
        window_start_at=start_time,
        window_end_at=end_time,
        transport_kind=resolved_transport_kind,
    )
    page_size_wire = registry.preferred_wire_name('page_size')
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    completed_endpoint_runs: list[dict[str, Any]] = []

    for endpoint_contract_id in dependency_entry.get('endpoint_contract_ids', []):
        endpoint_run = artifact_store.start_endpoint_run(
            ingestion_run_id=ingestion_run['ingestion_run_id'],
            endpoint_contract_id=endpoint_contract_id,
            org_id=org_id,
            transport_kind=resolved_transport_kind,
        )
        raw_pages_by_endpoint[endpoint_contract_id] = []
        page_index = 1
        accumulated_records = 0
        finalized = False

        while not finalized:
            request_envelope = build_signed_request(
                endpoint_contract_id=endpoint_contract_id,
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                page_index=page_index,
                page_size=page_size,
                app_secret=app_secret,
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
            page_rows = response_envelope.get('RetData', {}).get('Data', []) or []
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

            transport_error = normalized_fetch_result.get('transport_error')
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
                source_error = _source_business_error(response_envelope)
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status='failed',
                        page_count=page_index,
                        record_count=accumulated_records,
                        error_taxonomy=source_error['taxonomy'],
                        error_code=source_error['code'],
                        error_message=source_error['message'],
                        retryable=source_error['retryable'],
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            total = int(response_envelope.get('RetData', {}).get('Total', response_record_count) or 0)
            if response_record_count == 0:
                endpoint_status = 'source_empty' if accumulated_records == 0 else 'completed'
                completed_endpoint_runs.append(
                    artifact_store.finalize_endpoint_run(
                        endpoint_run_id=endpoint_run['endpoint_run_id'],
                        endpoint_status=endpoint_status,
                        page_count=page_index,
                        record_count=accumulated_records,
                        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
                    )
                )
                finalized = True
                continue

            current_page_size = int(request_envelope['payload'][page_size_wire])
            has_more_pages = total > (page_index * current_page_size)
            if has_more_pages:
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
    canonical_artifacts = build_member_insight_canonical_artifacts(
        raw_pages_by_endpoint=_canonical_input_by_endpoint(
            raw_pages_by_endpoint=raw_pages_by_endpoint,
            endpoint_runs=completed_endpoint_runs,
        ),
        org_id=org_id,
        requested_business_date=requested_business_date,
    )
    latest_usable_endpoint_states = build_latest_usable_endpoint_states(
        endpoint_runs=completed_endpoint_runs,
        source_system_id=SOURCE_SYSTEM_ID,
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
        'canonical/customer.json': canonical_artifacts.get('customer', []),
        'canonical/customer_card.json': canonical_artifacts.get('customer_card', []),
        'canonical/consume_bill.json': canonical_artifacts.get('consume_bill', []),
        'canonical/consume_bill_payment.json': canonical_artifacts.get('consume_bill_payment', []),
        'canonical/consume_bill_info.json': canonical_artifacts.get('consume_bill_info', []),
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
