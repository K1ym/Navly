from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
MISSING = object()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=4)
def _endpoint_contract_entries(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    return {
        entry['endpoint_contract_id']: entry
        for entry in _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')['entries']
        if entry['domain'] != 'shared'
    }


@lru_cache(maxsize=4)
def _field_catalog_entries(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    return {
        entry['endpoint_contract_id']: entry
        for entry in _load_json(data_platform_root / 'directory' / 'endpoint-field-catalog.seed.json')['entries']
    }


@lru_cache(maxsize=4)
def _landing_policies(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    return {
        entry['policy_id']: entry
        for entry in _load_json(data_platform_root / 'directory' / 'field-landing-policy.seed.json')['entries']
    }


def _iter_path_matches(node: Any, parts: list[str]) -> list[Any]:
    if not parts:
        return [node]
    if isinstance(node, list):
        matches: list[Any] = []
        for item in node:
            matches.extend(_iter_path_matches(item, parts))
        return matches
    if isinstance(node, dict):
        head = parts[0]
        if head not in node:
            return []
        return _iter_path_matches(node[head], parts[1:])
    return []


def _observed_values(page_records: list[dict[str, Any]], field_path: str) -> list[Any]:
    values: list[Any] = []
    for page_record in page_records:
        values.extend(_iter_path_matches(page_record['response_envelope'], field_path.split('.')))
    return values


def _observed_type(value: Any) -> str:
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return 'null'


def _alignment_status(expected_type: str, observed_values: list[Any]) -> tuple[str, list[str]]:
    observed_types = sorted({
        _observed_type(value)
        for value in observed_values
        if value is not None
    })
    if not observed_values:
        return 'not_observed', observed_types
    if not observed_types:
        return 'aligned', ['null']
    return ('aligned', observed_types) if observed_types == [expected_type] else ('misaligned', observed_types)


def _field_coverage_snapshot(
    *,
    endpoint_contract_id: str,
    page_records: list[dict[str, Any]],
    endpoint_run: dict[str, Any],
    data_platform_root: Path,
) -> dict[str, Any]:
    landing_policies = _landing_policies(data_platform_root=data_platform_root)
    field_results: list[dict[str, Any]] = []
    missing_field_paths: list[str] = []
    ungoverned_field_paths: list[str] = []

    for field in _field_catalog_entries(data_platform_root=data_platform_root)[endpoint_contract_id]['response_fields']:
        policy = landing_policies.get(field['landing_policy_id'])
        observed_values = _observed_values(page_records, field['field_path'])
        coverage_status = 'observed'
        if policy is None:
            coverage_status = 'ungoverned'
            ungoverned_field_paths.append(field['field_path'])
        elif not observed_values:
            coverage_status = 'missing_from_payload'
            missing_field_paths.append(field['field_path'])

        field_results.append({
            'field_path': field['field_path'],
            'path_kind': field['path_kind'],
            'expected_data_type': field['data_type'],
            'landing_policy_id': field['landing_policy_id'],
            'coverage_status': coverage_status,
            'observed_count': len(observed_values),
            'target_layer': policy['target_layer'] if policy is not None else None,
            'target_dataset': policy['target_dataset'] if policy is not None else [],
        })

    endpoint_status = endpoint_run.get('endpoint_status')
    snapshot_status = 'complete'
    if endpoint_status == 'source_empty':
        snapshot_status = 'source_empty'
    elif endpoint_status == 'failed':
        snapshot_status = 'failed'
    elif missing_field_paths or ungoverned_field_paths:
        snapshot_status = 'partial'

    return {
        'snapshot_status': snapshot_status,
        'governed_field_count': len(field_results),
        'observed_field_count': sum(1 for item in field_results if item['coverage_status'] == 'observed'),
        'missing_field_count': len(missing_field_paths),
        'ungoverned_field_count': len(ungoverned_field_paths),
        'missing_field_paths': missing_field_paths,
        'ungoverned_field_paths': ungoverned_field_paths,
        'field_results': field_results,
    }


def _schema_alignment_snapshot(
    *,
    endpoint_contract_id: str,
    page_records: list[dict[str, Any]],
    endpoint_run: dict[str, Any],
    data_platform_root: Path,
) -> dict[str, Any]:
    field_results: list[dict[str, Any]] = []
    misaligned_field_paths: list[str] = []
    not_observed_field_paths: list[str] = []

    for field in _field_catalog_entries(data_platform_root=data_platform_root)[endpoint_contract_id]['response_fields']:
        observed_values = _observed_values(page_records, field['field_path'])
        alignment_status, observed_types = _alignment_status(field['data_type'], observed_values)
        if alignment_status == 'misaligned':
            misaligned_field_paths.append(field['field_path'])
        if alignment_status == 'not_observed':
            not_observed_field_paths.append(field['field_path'])
        field_results.append({
            'field_path': field['field_path'],
            'expected_data_type': field['data_type'],
            'alignment_status': alignment_status,
            'observed_types': observed_types,
        })

    endpoint_status = endpoint_run.get('endpoint_status')
    snapshot_status = 'aligned'
    if endpoint_status == 'source_empty':
        snapshot_status = 'source_empty'
    elif endpoint_status == 'failed':
        snapshot_status = 'failed'
    elif misaligned_field_paths:
        snapshot_status = 'misaligned'

    return {
        'snapshot_status': snapshot_status,
        'aligned_field_count': sum(1 for item in field_results if item['alignment_status'] == 'aligned'),
        'misaligned_field_count': len(misaligned_field_paths),
        'not_observed_field_count': len(not_observed_field_paths),
        'misaligned_field_paths': misaligned_field_paths,
        'not_observed_field_paths': not_observed_field_paths,
        'field_results': field_results,
    }


def _classify_failed_endpoint(endpoint_run: dict[str, Any]) -> str:
    haystack = ' '.join([
        str(endpoint_run.get('error_taxonomy') or ''),
        str(endpoint_run.get('error_code') or ''),
        str(endpoint_run.get('error_message') or ''),
    ]).lower()
    if any(token in haystack for token in ['401', '403', 'auth', 'authorization', 'token', '鉴权', '未授权']):
        return 'auth_failure'
    if any(token in haystack for token in ['sign', 'signature', '验签', '签名']):
        return 'sign_failure'
    if any(token in haystack for token in ['schema', 'json', 'parse', '结构']):
        return 'schema_failure'
    return 'business_failure'


def _quality_issues(
    *,
    endpoint_contract_id: str,
    endpoint_run: dict[str, Any],
    coverage_snapshot: dict[str, Any],
    alignment_snapshot: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    endpoint_status = endpoint_run.get('endpoint_status')
    if endpoint_status == 'source_empty':
        quality_status = 'source_empty'
    elif endpoint_status == 'failed':
        quality_status = _classify_failed_endpoint(endpoint_run)
    elif alignment_snapshot['misaligned_field_count'] or coverage_snapshot['ungoverned_field_count'] or coverage_snapshot['missing_field_count']:
        quality_status = 'schema_failure'
    else:
        quality_status = 'clean'

    if quality_status == 'clean':
        return quality_status, []

    return quality_status, [{
        'issue_id': f'{endpoint_contract_id}::{quality_status}',
        'endpoint_contract_id': endpoint_contract_id,
        'issue_category': quality_status,
        'issue_status': 'open',
        'error_taxonomy': endpoint_run.get('error_taxonomy'),
        'error_code': endpoint_run.get('error_code'),
        'error_message': endpoint_run.get('error_message'),
        'missing_field_paths': coverage_snapshot['missing_field_paths'],
        'ungoverned_field_paths': coverage_snapshot['ungoverned_field_paths'],
        'misaligned_field_paths': alignment_snapshot['misaligned_field_paths'],
    }]


def build_qinqin_endpoint_governance_results(
    *,
    raw_pages_by_endpoint: dict[str, list[dict[str, Any]]],
    endpoint_runs: list[dict[str, Any]],
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> list[dict[str, Any]]:
    endpoint_runs_by_id = {
        endpoint_run['endpoint_contract_id']: endpoint_run
        for endpoint_run in endpoint_runs
    }
    results: list[dict[str, Any]] = []

    for endpoint_contract_id, contract_entry in _endpoint_contract_entries(data_platform_root=data_platform_root).items():
        endpoint_run = endpoint_runs_by_id.get(endpoint_contract_id, {
            'endpoint_contract_id': endpoint_contract_id,
            'endpoint_status': 'not_run',
            'error_taxonomy': None,
            'error_code': None,
            'error_message': None,
        })
        page_records = raw_pages_by_endpoint.get(endpoint_contract_id, [])
        coverage_snapshot = _field_coverage_snapshot(
            endpoint_contract_id=endpoint_contract_id,
            page_records=page_records,
            endpoint_run=endpoint_run,
            data_platform_root=data_platform_root,
        )
        alignment_snapshot = _schema_alignment_snapshot(
            endpoint_contract_id=endpoint_contract_id,
            page_records=page_records,
            endpoint_run=endpoint_run,
            data_platform_root=data_platform_root,
        )
        quality_status, quality_issues = _quality_issues(
            endpoint_contract_id=endpoint_contract_id,
            endpoint_run=endpoint_run,
            coverage_snapshot=coverage_snapshot,
            alignment_snapshot=alignment_snapshot,
        )
        results.append({
            'endpoint_contract_id': endpoint_contract_id,
            'structured_targets': list(contract_entry.get('structured_targets', [])),
            'endpoint_status': endpoint_run.get('endpoint_status'),
            'field_coverage_snapshot': coverage_snapshot,
            'schema_alignment_snapshot': alignment_snapshot,
            'quality_status': quality_status,
            'quality_issues': quality_issues,
        })

    return results


def build_five_store_endpoint_validation_matrix(
    store_results: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    endpoint_summary: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'store_count': 0,
        'ran_store_count': 0,
        'aligned_store_count': 0,
        'ready_store_count': 0,
    })

    for store_result in store_results:
        governance_by_endpoint = {
            item['endpoint_contract_id']: item
            for item in store_result['governance_results']
        }
        completeness_by_endpoint = {
            item['endpoint_contract_id']: item
            for item in store_result['completeness_results']
        }
        endpoint_runs_by_id = {
            item['endpoint_contract_id']: item
            for item in store_result['endpoint_runs']
        }

        for endpoint_contract_id, governance_result in governance_by_endpoint.items():
            endpoint_run = endpoint_runs_by_id.get(endpoint_contract_id, {})
            completeness_result = completeness_by_endpoint.get(endpoint_contract_id, {})
            did_run = endpoint_run.get('endpoint_status') in {'completed', 'source_empty', 'failed'}
            fields_aligned = governance_result['schema_alignment_snapshot']['snapshot_status'] == 'aligned'
            row = {
                'org_id': store_result['org_id'],
                'requested_business_date': store_result['requested_business_date'],
                'endpoint_contract_id': endpoint_contract_id,
                'did_run': did_run,
                'run_status': endpoint_run.get('endpoint_status', 'not_run'),
                'fields_aligned': fields_aligned,
                'field_coverage_status': governance_result['field_coverage_snapshot']['snapshot_status'],
                'schema_alignment_status': governance_result['schema_alignment_snapshot']['snapshot_status'],
                'quality_status': governance_result['quality_status'],
                'completeness_status': completeness_result.get('completeness_status', 'missing'),
            }
            rows.append(row)

            summary = endpoint_summary[endpoint_contract_id]
            summary['endpoint_contract_id'] = endpoint_contract_id
            summary['store_count'] += 1
            summary['ran_store_count'] += int(did_run)
            summary['aligned_store_count'] += int(fields_aligned)
            summary['ready_store_count'] += int(completeness_result.get('completeness_status') == 'ready')

    return {
        'store_count': len(store_results),
        'rows': rows,
        'endpoint_summary': sorted(endpoint_summary.values(), key=lambda item: item['endpoint_contract_id']),
    }


__all__ = [
    'build_five_store_endpoint_validation_matrix',
    'build_qinqin_endpoint_governance_results',
]
