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
    normalize_fetch_page_result,
)
from workflows.commission_setting_governance_surface import build_commission_setting_governance_surface

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
COMMISSION_SETTING_ENDPOINT_ID = 'qinqin.staff.get_tech_commission_set_list.v1_8'
COMMISSION_SETTING_CAPABILITY_ID = 'navly.internal.data_platform.commission_setting_governance'
COMMISSION_SETTING_SERVICE_OBJECT_ID = 'navly.service.internal.commission_setting_governance'
SOURCE_EMPTY_MESSAGE_MARKERS = ('暂无数据', '无数据', '没有数据', '未查询到数据')
AUTH_MESSAGE_MARKERS = ('授权', '认证', '登录', 'token', '未授权', '无权限', '权限')
SIGN_MESSAGE_MARKERS = ('验签', '签名', 'sign')


def _new_trace_ref() -> str:
    return f'navly:trace:{uuid.uuid4().hex[:16]}'


@lru_cache(maxsize=1)
def _load_raw_store_backbone_module():
    module_path = DATA_PLATFORM_ROOT / 'raw-store' / 'raw_replay_backbone.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_raw_store_raw_replay_backbone_commission_setting',
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


def _source_empty_response(response_envelope: dict[str, Any]) -> bool:
    source_code = response_envelope.get('Code')
    message = str(response_envelope.get('Msg') or '')
    return source_code in {404, '404', '404.0'} and any(
        marker in message for marker in SOURCE_EMPTY_MESSAGE_MARKERS
    )


def _source_error(response_envelope: dict[str, Any]) -> dict[str, Any]:
    source_code = response_envelope.get('Code')
    message = str(response_envelope.get('Msg') or 'Source responded with a non-success code.')
    lowered = message.lower()
    if source_code in {401, 403} or any(marker.lower() in lowered for marker in AUTH_MESSAGE_MARKERS):
        return {
            'terminal_outcome_category': 'auth',
            'error_taxonomy': 'source_auth_error',
            'error_code': str(source_code) if source_code is not None else 'AUTH_ERROR',
            'error_message': message,
        }
    if any(marker.lower() in lowered for marker in SIGN_MESSAGE_MARKERS):
        return {
            'terminal_outcome_category': 'sign',
            'error_taxonomy': 'source_sign_error',
            'error_code': str(source_code) if source_code is not None else 'SIGN_ERROR',
            'error_message': message,
        }
    return {
        'terminal_outcome_category': 'source',
        'error_taxonomy': 'source_business_error',
        'error_code': str(source_code) if source_code is not None else 'SOURCE_NON_SUCCESS',
        'error_message': message,
    }


def run_commission_setting_endpoint_sync(
    *,
    org_id: str,
    requested_business_date: str,
    app_secret: str,
    transport: Any,
    expected_business_dates: list[str] | None = None,
    prior_latest_usable_states: list[dict[str, Any]] | None = None,
    output_root: str | Path | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    resolved_transport_kind = _transport_kind(transport)
    artifact_store = _vertical_slice_artifact_store(output_root=output_root)
    ingestion_run = artifact_store.start_ingestion_run(
        capability_id=COMMISSION_SETTING_CAPABILITY_ID,
        service_object_id=COMMISSION_SETTING_SERVICE_OBJECT_ID,
        source_system_id='qinqin.v1_1',
        org_id=org_id,
        requested_business_date=requested_business_date,
        window_start_at=requested_business_date,
        window_end_at=requested_business_date,
        transport_kind=resolved_transport_kind,
    )
    endpoint_run = artifact_store.start_endpoint_run(
        ingestion_run_id=ingestion_run['ingestion_run_id'],
        endpoint_contract_id=COMMISSION_SETTING_ENDPOINT_ID,
        org_id=org_id,
        transport_kind=resolved_transport_kind,
    )

    request_envelope = build_signed_request(
        endpoint_contract_id=COMMISSION_SETTING_ENDPOINT_ID,
        org_id=org_id,
        start_time=None,
        end_time=None,
        app_secret=app_secret,
        data_platform_root=data_platform_root,
    )

    try:
        fetch_result = transport.fetch_page(COMMISSION_SETTING_ENDPOINT_ID, request_envelope['payload'])
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
        endpoint_contract_id=COMMISSION_SETTING_ENDPOINT_ID,
        page_index=1,
        replay_artifact=normalized_fetch_result['replay_artifact'],
    )
    response_envelope = normalized_fetch_result['response_envelope']
    transport_error = normalized_fetch_result.get('transport_error')

    response_envelopes: list[dict[str, Any]] = []
    response_record_count = 0
    endpoint_status = 'completed'
    terminal_outcome_category = 'success'
    error_taxonomy = None
    error_code = None
    error_message = None

    if transport_error:
        endpoint_status = 'failed'
        terminal_outcome_category = 'transport'
        error_taxonomy = transport_error.get('taxonomy')
        error_code = transport_error.get('code')
        error_message = transport_error.get('message')
    elif _source_empty_response(response_envelope):
        endpoint_status = 'source_empty'
        terminal_outcome_category = 'source_empty'
        response_envelopes = [response_envelope]
    elif response_envelope.get('Code') != 200:
        endpoint_status = 'failed'
        source_error = _source_error(response_envelope)
        terminal_outcome_category = source_error['terminal_outcome_category']
        error_taxonomy = source_error['error_taxonomy']
        error_code = source_error['error_code']
        error_message = source_error['error_message']
    else:
        ret_data = response_envelope.get('RetData')
        if not isinstance(ret_data, list):
            endpoint_status = 'failed'
            terminal_outcome_category = 'schema'
            error_taxonomy = 'source_schema_error'
            error_code = 'INVALID_RESPONSE_SHAPE'
            error_message = 'Commission-setting RetData must be an array.'
        else:
            response_envelopes = [response_envelope]
            response_record_count = len(ret_data)

    raw_page_record = artifact_store.append_raw_response_page(
        endpoint_run_id=endpoint_run['endpoint_run_id'],
        endpoint_contract_id=COMMISSION_SETTING_ENDPOINT_ID,
        page_index=1,
        transport_kind=transport_replay_artifact['transport_kind'],
        replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
        request_envelope=request_envelope,
        response_envelope=response_envelope,
        response_record_count=response_record_count,
        source_response_code=response_envelope.get('Code'),
        source_response_message=response_envelope.get('Msg'),
    )

    finalized_endpoint_run = artifact_store.finalize_endpoint_run(
        endpoint_run_id=endpoint_run['endpoint_run_id'],
        endpoint_status=endpoint_status,
        page_count=1,
        record_count=response_record_count,
        terminal_outcome_category=terminal_outcome_category,
        error_taxonomy=error_taxonomy,
        error_code=error_code,
        error_message=error_message,
        retryable=bool(transport_error and transport_error.get('retryable')),
        terminal_replay_artifact_id=transport_replay_artifact['replay_artifact_id'],
    )
    finalized_ingestion_run = artifact_store.finalize_ingestion_run(
        ingestion_run_id=ingestion_run['ingestion_run_id'],
        run_status='completed' if endpoint_status in {'completed', 'source_empty'} else 'failed',
    )
    governance_surface = build_commission_setting_governance_surface(
        endpoint_run=finalized_endpoint_run,
        response_envelopes=response_envelopes,
        requested_business_date=requested_business_date,
        expected_business_dates=expected_business_dates or [requested_business_date],
        prior_latest_usable_states=prior_latest_usable_states or [],
        data_platform_root=data_platform_root,
    )

    artifact_store.write_payload_map({
        'historical-run-truth/ingestion-runs.json': artifact_store.ingestion_runs,
        'historical-run-truth/endpoint-runs.json': artifact_store.endpoint_runs,
        'raw-replay/raw-response-pages.json': artifact_store.raw_response_pages,
        'raw-replay/transport-replay-artifacts.json': artifact_store.transport_replay_artifacts,
        'canonical/commission_setting.json': governance_surface['canonical_artifacts']['commission_setting'],
        'canonical/commission_setting_detail.json': governance_surface['canonical_artifacts']['commission_setting_detail'],
        'latest-state/latest-usable-endpoint-state.json': [governance_surface['latest_state_artifacts']['latest_usable_endpoint_state']],
        'latest-state/backfill-progress-state.json': governance_surface['latest_state_artifacts']['backfill_progress_state'],
        'quality/field-coverage-snapshot.json': governance_surface['quality_artifacts']['field_coverage_snapshot'],
        'quality/schema-alignment-snapshot.json': governance_surface['quality_artifacts']['schema_alignment_snapshot'],
        'quality/quality-issues.json': governance_surface['quality_artifacts']['quality_issues'],
        'completeness/commission-setting-completeness-state.json': governance_surface['completeness_artifacts']['commission_setting_completeness_state'],
    })
    return {
        'request_id': uuid.uuid4().hex,
        'trace_ref': _new_trace_ref(),
        'transport_kind': resolved_transport_kind,
        'capability_id': COMMISSION_SETTING_CAPABILITY_ID,
        'service_object_id': COMMISSION_SETTING_SERVICE_OBJECT_ID,
        'historical_run_truth': {
            'ingestion_run': finalized_ingestion_run,
            'endpoint_runs': [finalized_endpoint_run],
        },
        'raw_replay': {
            'raw_response_pages': [raw_page_record],
            'transport_replay_artifacts': [transport_replay_artifact],
        },
        **governance_surface,
    }


__all__ = ['run_commission_setting_endpoint_sync']
