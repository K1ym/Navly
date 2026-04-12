from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate


def build_operator_status_bundle(
    *,
    truth_store: PostgresTruthSubstrate,
    org_ids: Iterable[str],
) -> dict[str, Any]:
    ordered_org_ids = list(org_ids)
    return {
        'sync_status': [
            truth_store.build_sync_status_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
        'backfill_status': [
            truth_store.build_backfill_status_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
        'quality_report': [
            truth_store.build_quality_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
    }


def query_operator_status_from_snapshot(
    *,
    request_id: str,
    trace_ref: str,
    state_snapshot_path: str | Path,
    org_ids: Iterable[str],
) -> dict[str, Any]:
    truth_store = PostgresTruthSubstrate.from_snapshot_file(state_snapshot_path)
    payload = build_operator_status_bundle(
        truth_store=truth_store,
        org_ids=org_ids,
    )
    payload['request_id'] = request_id
    payload['trace_ref'] = trace_ref
    payload['state_snapshot'] = str(Path(state_snapshot_path))
    return payload
