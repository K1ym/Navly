from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    endpoint_status: str
    page_count: int
    record_count: int
    started_at: str
    completed_at: str | None
    error_code: str | None
    error_message: str | None


@dataclass
class RawResponsePageRecord:
    raw_page_id: str
    run_trace_ref: str
    endpoint_run_id: str
    endpoint_contract_id: str
    page_index: int
    request_envelope: dict[str, Any]
    response_envelope: dict[str, Any]
    response_record_count: int
    captured_at: str


class VerticalSliceArtifactStore:
    def __init__(self, output_root: str | Path | None = None) -> None:
        self.output_root = Path(output_root) if output_root else None
        self.ingestion_runs: list[dict[str, Any]] = []
        self.endpoint_runs: list[dict[str, Any]] = []
        self.raw_response_pages: list[dict[str, Any]] = []

    def start_ingestion_run(
        self,
        capability_id: str,
        service_object_id: str,
        source_system_id: str,
        org_id: str,
        requested_business_date: str,
        window_start_at: str,
        window_end_at: str,
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

    def start_endpoint_run(self, ingestion_run_id: str, endpoint_contract_id: str, org_id: str) -> dict[str, Any]:
        endpoint_run_id = f'er_{uuid.uuid4().hex[:12]}'
        record = EndpointRunRecord(
            endpoint_run_id=endpoint_run_id,
            endpoint_run_trace_ref=build_run_trace_ref('endpoint-run', endpoint_run_id),
            ingestion_run_id=ingestion_run_id,
            endpoint_contract_id=endpoint_contract_id,
            org_id=org_id,
            endpoint_status='running',
            page_count=0,
            record_count=0,
            started_at=utcnow_iso(),
            completed_at=None,
            error_code=None,
            error_message=None,
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
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        for record in self.endpoint_runs:
            if record['endpoint_run_id'] == endpoint_run_id:
                record['endpoint_status'] = endpoint_status
                record['page_count'] = page_count
                record['record_count'] = record_count
                record['completed_at'] = utcnow_iso()
                record['error_code'] = error_code
                record['error_message'] = error_message
                return record
        raise KeyError(f'Unknown endpoint_run_id: {endpoint_run_id}')

    def append_raw_response_page(
        self,
        endpoint_run_id: str,
        endpoint_contract_id: str,
        page_index: int,
        request_envelope: dict[str, Any],
        response_envelope: dict[str, Any],
        response_record_count: int,
    ) -> dict[str, Any]:
        raw_page_id = f'rp_{uuid.uuid4().hex[:12]}'
        record = RawResponsePageRecord(
            raw_page_id=raw_page_id,
            run_trace_ref=build_run_trace_ref('raw-page', raw_page_id),
            endpoint_run_id=endpoint_run_id,
            endpoint_contract_id=endpoint_contract_id,
            page_index=page_index,
            request_envelope=request_envelope,
            response_envelope=response_envelope,
            response_record_count=response_record_count,
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
            },
        }

    def write_json_artifacts(
        self,
        canonical_artifacts: dict[str, Any],
        latest_state_artifacts: dict[str, Any],
    ) -> None:
        if self.output_root is None:
            return
        artifact_groups = {
            self.output_root / 'historical-run-truth' / 'ingestion-runs.json': self.ingestion_runs,
            self.output_root / 'historical-run-truth' / 'endpoint-runs.json': self.endpoint_runs,
            self.output_root / 'raw-replay' / 'raw-response-pages.json': self.raw_response_pages,
            self.output_root / 'canonical' / 'customer.json': canonical_artifacts.get('customer', []),
            self.output_root / 'canonical' / 'customer_card.json': canonical_artifacts.get('customer_card', []),
            self.output_root / 'canonical' / 'consume_bill.json': canonical_artifacts.get('consume_bill', []),
            self.output_root / 'canonical' / 'consume_bill_payment.json': canonical_artifacts.get('consume_bill_payment', []),
            self.output_root / 'canonical' / 'consume_bill_info.json': canonical_artifacts.get('consume_bill_info', []),
            self.output_root / 'latest-state' / 'latest-usable-endpoint-state.json': latest_state_artifacts.get('latest_usable_endpoint_states', []),
            self.output_root / 'latest-state' / 'vertical-slice-backbone-state.json': latest_state_artifacts.get('vertical_slice_backbone_state', {}),
        }
        for path, payload in artifact_groups.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
