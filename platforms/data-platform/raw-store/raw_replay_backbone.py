from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def build_run_trace_ref(run_type: str, run_id: str) -> str:
    return f'navly:run-trace:{run_type}:{run_id}'


@dataclass
class IngestionRunRecord:
    ingestion_run_id: str
    run_trace_ref: str
    capability_id: str
    service_object_id: str
    source_system_id: str
    org_id: str
    requested_business_date: str
    window_start_at: str
    window_end_at: str
    transport_kind: str
    run_status: str
    started_at: str
    completed_at: str | None


@dataclass
class EndpointRunRecord:
    endpoint_run_id: str
    endpoint_run_trace_ref: str
    ingestion_run_id: str
    endpoint_contract_id: str
    org_id: str
    transport_kind: str
    endpoint_status: str
    page_count: int
    record_count: int
    terminal_outcome_category: str | None
    started_at: str
    completed_at: str | None
    error_taxonomy: str | None
    error_code: str | None
    error_message: str | None
    retryable: bool | None
    terminal_replay_artifact_id: str | None


@dataclass
class RawResponsePageRecord:
    raw_page_id: str
    run_trace_ref: str
    endpoint_run_id: str
    endpoint_contract_id: str
    page_index: int
    transport_kind: str
    replay_artifact_id: str
    request_envelope: dict[str, Any]
    response_envelope: dict[str, Any]
    response_record_count: int
    source_response_code: Any
    source_response_message: Any
    captured_at: str


@dataclass
class TransportReplayArtifactRecord:
    replay_artifact_id: str
    run_trace_ref: str
    endpoint_run_id: str
    endpoint_contract_id: str
    page_index: int
    transport_kind: str
    transport_outcome: str
    request_method: str | None
    request_url: str | None
    request_headers_redacted: dict[str, Any]
    request_payload: dict[str, Any]
    response_http_status: int | None
    response_headers: dict[str, Any]
    response_body: str | None
    source_response_code: Any
    source_response_message: Any
    error_taxonomy: str | None
    error_code: str | None
    error_message: str | None
    retryable: bool | None
    captured_at: str


class VerticalSliceArtifactStore:
    def __init__(self, output_root: str | Path | None = None) -> None:
        self.output_root = Path(output_root) if output_root else None
        self.ingestion_runs: list[dict[str, Any]] = []
        self.endpoint_runs: list[dict[str, Any]] = []
        self.raw_response_pages: list[dict[str, Any]] = []
        self.transport_replay_artifacts: list[dict[str, Any]] = []

    def start_ingestion_run(
        self,
        capability_id: str,
        service_object_id: str,
        source_system_id: str,
        org_id: str,
        requested_business_date: str,
        window_start_at: str,
        window_end_at: str,
        transport_kind: str,
    ) -> dict[str, Any]:
        ingestion_run_id = f'ir_{uuid.uuid4().hex[:12]}'
        record = IngestionRunRecord(
            ingestion_run_id=ingestion_run_id,
            run_trace_ref=build_run_trace_ref('ingestion-run', ingestion_run_id),
            capability_id=capability_id,
            service_object_id=service_object_id,
            source_system_id=source_system_id,
            org_id=org_id,
            requested_business_date=requested_business_date,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            transport_kind=transport_kind,
            run_status='running',
            started_at=utcnow_iso(),
            completed_at=None,
        )
        stored = asdict(record)
        self.ingestion_runs.append(stored)
        return stored

    def finalize_ingestion_run(self, ingestion_run_id: str, run_status: str) -> dict[str, Any]:
        for record in self.ingestion_runs:
            if record['ingestion_run_id'] == ingestion_run_id:
                record['run_status'] = run_status
                record['completed_at'] = utcnow_iso()
                return record
        raise KeyError(f'Unknown ingestion_run_id: {ingestion_run_id}')

    def start_endpoint_run(
        self,
        ingestion_run_id: str,
        endpoint_contract_id: str,
        org_id: str,
        transport_kind: str,
    ) -> dict[str, Any]:
        endpoint_run_id = f'er_{uuid.uuid4().hex[:12]}'
        record = EndpointRunRecord(
            endpoint_run_id=endpoint_run_id,
            endpoint_run_trace_ref=build_run_trace_ref('endpoint-run', endpoint_run_id),
            ingestion_run_id=ingestion_run_id,
            endpoint_contract_id=endpoint_contract_id,
            org_id=org_id,
            transport_kind=transport_kind,
            endpoint_status='running',
            page_count=0,
            record_count=0,
            terminal_outcome_category=None,
            started_at=utcnow_iso(),
            completed_at=None,
            error_taxonomy=None,
            error_code=None,
            error_message=None,
            retryable=None,
            terminal_replay_artifact_id=None,
        )
        stored = asdict(record)
        self.endpoint_runs.append(stored)
        return stored

    def finalize_endpoint_run(
        self,
        endpoint_run_id: str,
        endpoint_status: str,
        page_count: int,
        record_count: int,
        terminal_outcome_category: str | None = None,
        error_taxonomy: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retryable: bool | None = None,
        terminal_replay_artifact_id: str | None = None,
    ) -> dict[str, Any]:
        for record in self.endpoint_runs:
            if record['endpoint_run_id'] == endpoint_run_id:
                record['endpoint_status'] = endpoint_status
                record['page_count'] = page_count
                record['record_count'] = record_count
                record['terminal_outcome_category'] = terminal_outcome_category
                record['completed_at'] = utcnow_iso()
                record['error_taxonomy'] = error_taxonomy
                record['error_code'] = error_code
                record['error_message'] = error_message
                record['retryable'] = retryable
                record['terminal_replay_artifact_id'] = terminal_replay_artifact_id
                return record
        raise KeyError(f'Unknown endpoint_run_id: {endpoint_run_id}')

    def append_transport_replay_artifact(
        self,
        *,
        endpoint_run_id: str,
        endpoint_contract_id: str,
        page_index: int,
        replay_artifact: Mapping[str, Any],
    ) -> dict[str, Any]:
        replay_artifact_id = f'ra_{uuid.uuid4().hex[:12]}'
        record = TransportReplayArtifactRecord(
            replay_artifact_id=replay_artifact_id,
            run_trace_ref=build_run_trace_ref('replay-artifact', replay_artifact_id),
            endpoint_run_id=endpoint_run_id,
            endpoint_contract_id=endpoint_contract_id,
            page_index=page_index,
            transport_kind=str(replay_artifact.get('transport_kind') or 'unknown'),
            transport_outcome=str(replay_artifact.get('transport_outcome') or 'unknown'),
            request_method=replay_artifact.get('request_method'),
            request_url=replay_artifact.get('request_url'),
            request_headers_redacted=dict(replay_artifact.get('request_headers_redacted') or {}),
            request_payload=dict(replay_artifact.get('request_payload') or {}),
            response_http_status=replay_artifact.get('response_http_status'),
            response_headers=dict(replay_artifact.get('response_headers') or {}),
            response_body=replay_artifact.get('response_body'),
            source_response_code=replay_artifact.get('source_response_code'),
            source_response_message=replay_artifact.get('source_response_message'),
            error_taxonomy=replay_artifact.get('error_taxonomy'),
            error_code=replay_artifact.get('error_code'),
            error_message=replay_artifact.get('error_message'),
            retryable=replay_artifact.get('retryable'),
            captured_at=utcnow_iso(),
        )
        stored = asdict(record)
        self.transport_replay_artifacts.append(stored)
        return stored

    def append_raw_response_page(
        self,
        endpoint_run_id: str,
        endpoint_contract_id: str,
        page_index: int,
        transport_kind: str,
        replay_artifact_id: str,
        request_envelope: dict[str, Any],
        response_envelope: dict[str, Any],
        response_record_count: int,
        source_response_code: Any,
        source_response_message: Any,
    ) -> dict[str, Any]:
        raw_page_id = f'rp_{uuid.uuid4().hex[:12]}'
        record = RawResponsePageRecord(
            raw_page_id=raw_page_id,
            run_trace_ref=build_run_trace_ref('raw-page', raw_page_id),
            endpoint_run_id=endpoint_run_id,
            endpoint_contract_id=endpoint_contract_id,
            page_index=page_index,
            transport_kind=transport_kind,
            replay_artifact_id=replay_artifact_id,
            request_envelope=request_envelope,
            response_envelope=response_envelope,
            response_record_count=response_record_count,
            source_response_code=source_response_code,
            source_response_message=source_response_message,
            captured_at=utcnow_iso(),
        )
        stored = asdict(record)
        self.raw_response_pages.append(stored)
        return stored

    def snapshot(self) -> dict[str, Any]:
        return {
            'historical_run_truth': {
                'ingestion_runs': self.ingestion_runs,
                'endpoint_runs': self.endpoint_runs,
            },
            'raw_replay': {
                'raw_response_pages': self.raw_response_pages,
                'transport_replay_artifacts': self.transport_replay_artifacts,
            },
        }

    def write_payload_map(self, relative_payload_map: Mapping[str, Any]) -> None:
        if self.output_root is None:
            return
        for relative_path, payload in relative_payload_map.items():
            path = self.output_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


__all__ = [
    'EndpointRunRecord',
    'IngestionRunRecord',
    'RawResponsePageRecord',
    'TransportReplayArtifactRecord',
    'VerticalSliceArtifactStore',
    'build_run_trace_ref',
    'utcnow_iso',
]
