from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def load_member_insight_artifact_tree(artifact_root: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    ingestion_runs = _load_json(root / 'historical-run-truth' / 'ingestion-runs.json')
    endpoint_runs = _load_json(root / 'historical-run-truth' / 'endpoint-runs.json')
    raw_response_pages = _load_json(root / 'raw-replay' / 'raw-response-pages.json')
    transport_replay_artifacts = _load_json(root / 'raw-replay' / 'transport-replay-artifacts.json')
    latest_usable_endpoint_states = _load_json(root / 'latest-state' / 'latest-usable-endpoint-state.json')
    vertical_slice_backbone_state = _load_json(root / 'latest-state' / 'vertical-slice-backbone-state.json')

    canonical_artifacts = {}
    for artifact_name in (
        'customer',
        'customer_card',
        'consume_bill',
        'consume_bill_payment',
        'consume_bill_info',
    ):
        canonical_artifacts[artifact_name] = _load_json(root / 'canonical' / f'{artifact_name}.json')

    ingestion_run = ingestion_runs[0]
    request_id = f"artifact-import::{ingestion_run['ingestion_run_id']}"
    trace_ref = f"navly:trace:artifact-import:{ingestion_run['ingestion_run_id']}"
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'transport_kind': ingestion_run.get('transport_kind'),
        'capability_id': ingestion_run['capability_id'],
        'service_object_id': ingestion_run['service_object_id'],
        'historical_run_truth': {
            'ingestion_run': ingestion_run,
            'endpoint_runs': endpoint_runs,
        },
        'raw_replay': {
            'raw_response_pages': raw_response_pages,
            'transport_replay_artifacts': transport_replay_artifacts,
        },
        'canonical_artifacts': canonical_artifacts,
        'latest_state_artifacts': {
            'latest_usable_endpoint_states': latest_usable_endpoint_states,
            'vertical_slice_backbone_state': vertical_slice_backbone_state,
        },
        'extensions': {
            'bridge_kind': 'artifact_tree_import',
            'artifact_root': str(root),
        },
    }


def import_member_insight_artifact_tree_to_truth_store(
    *,
    artifact_root: str | Path,
    truth_store: PostgresTruthSubstrate,
    target_scope_ref: str | None = None,
    scheduler_trace_ref: str | None = None,
    workflow_id: str | None = None,
    task_kind: str = 'artifact_bridge',
) -> dict[str, Any]:
    vertical_slice_result = load_member_insight_artifact_tree(artifact_root)
    ingestion_run = vertical_slice_result['historical_run_truth']['ingestion_run']
    org_id = ingestion_run['org_id']
    requested_business_date = ingestion_run['requested_business_date']
    return {
        'bridge_kind': 'artifact_tree_import',
        'artifact_root': str(Path(artifact_root)),
        'persistence': truth_store.persist_vertical_slice_result(
            org_id=org_id,
            target_scope_ref=target_scope_ref or f'navly:scope:store:{org_id}',
            target_business_date=requested_business_date,
            vertical_slice_result=vertical_slice_result,
            scheduler_trace_ref=scheduler_trace_ref,
            workflow_id=workflow_id,
            task_kind=task_kind,
        ),
    }
