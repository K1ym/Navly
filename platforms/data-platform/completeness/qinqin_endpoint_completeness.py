from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=4)
def _endpoint_contract_entries(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    return {
        entry['endpoint_contract_id']: entry
        for entry in _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')['entries']
        if entry['domain'] != 'shared'
    }


def _completeness_status(governance_result: dict[str, Any], landing_status: str) -> str:
    quality_status = governance_result['quality_status']
    if landing_status != 'formalized':
        return 'incomplete'
    if quality_status == 'clean':
        if governance_result['field_coverage_snapshot']['snapshot_status'] == 'complete' and governance_result['schema_alignment_snapshot']['snapshot_status'] == 'aligned':
            return 'ready'
        return 'incomplete'
    if quality_status == 'source_empty':
        return 'source_empty'
    if quality_status == 'auth_failure':
        return 'failed_auth'
    if quality_status == 'sign_failure':
        return 'failed_sign'
    if quality_status == 'schema_failure':
        return 'failed_schema'
    return 'failed_business'


def build_qinqin_endpoint_completeness_results(
    *,
    governance_results: list[dict[str, Any]],
    endpoint_runs: list[dict[str, Any]],
    structured_target_artifacts: dict[str, list[dict[str, Any]]],
    requested_business_date: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> list[dict[str, Any]]:
    governance_by_endpoint = {
        item['endpoint_contract_id']: item
        for item in governance_results
    }
    endpoint_runs_by_id = {
        item['endpoint_contract_id']: item
        for item in endpoint_runs
    }
    results: list[dict[str, Any]] = []

    for endpoint_contract_id, contract_entry in _endpoint_contract_entries(data_platform_root=data_platform_root).items():
        governance_result = governance_by_endpoint[endpoint_contract_id]
        endpoint_run = endpoint_runs_by_id.get(endpoint_contract_id, {})
        structured_targets = list(contract_entry.get('structured_targets', []))
        formalized_target_ids = [
            target_dataset
            for target_dataset in structured_targets
            if target_dataset in structured_target_artifacts
        ]
        landing_status = 'formalized' if len(formalized_target_ids) == len(structured_targets) else 'missing_target'
        completeness_status = _completeness_status(governance_result, landing_status)
        results.append({
            'endpoint_contract_id': endpoint_contract_id,
            'requested_business_date': requested_business_date,
            'latest_usable_business_date': requested_business_date if completeness_status in {'ready', 'source_empty'} else None,
            'structured_targets': structured_targets,
            'formalized_target_ids': formalized_target_ids,
            'landing_status': landing_status,
            'field_coverage_status': governance_result['field_coverage_snapshot']['snapshot_status'],
            'schema_alignment_status': governance_result['schema_alignment_snapshot']['snapshot_status'],
            'quality_status': governance_result['quality_status'],
            'completeness_status': completeness_status,
            'latest_endpoint_status': endpoint_run.get('endpoint_status'),
            'backfill_progress_state': {
                'status': 'governed_fixture_window',
                'expected_business_date_count': 1,
                'completed_business_date_count': 1 if completeness_status in {'ready', 'source_empty'} else 0,
            },
        })

    return results


__all__ = [
    'build_qinqin_endpoint_completeness_results',
]
