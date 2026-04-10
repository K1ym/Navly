from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
COMMISSION_SETTING_ENDPOINT_ID = 'qinqin.staff.get_tech_commission_set_list.v1_8'
SOURCE_EMPTY_VARIANCE_ID = 'qinqin.response.tech-commission-set-source-empty-governed'
RUNTIME_HEADER_VARIANCE_ID = 'qinqin.auth.tech-commission-set-runtime-headers-required'
SOURCE_EMPTY_ALLOWED_FIELD_PATHS = {'Code', 'Msg', 'RetData'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def _load_commission_setting_governance(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    endpoint_contracts = _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')
    field_catalog = _load_json(data_platform_root / 'directory' / 'endpoint-field-catalog.seed.json')
    variance_registry = _load_json(data_platform_root / 'directory' / 'source-variance.seed.json')

    binding = next(
        (
            entry
            for entry in endpoint_contracts['endpoint_governance_bindings']
            if entry['endpoint_contract_id'] == COMMISSION_SETTING_ENDPOINT_ID
        ),
        None,
    )
    if binding is None:
        raise ValueError(f'Missing governance binding for {COMMISSION_SETTING_ENDPOINT_ID}.')

    field_catalog_entry = next(
        (
            entry
            for entry in field_catalog['entries']
            if entry['endpoint_contract_id'] == COMMISSION_SETTING_ENDPOINT_ID
        ),
        None,
    )
    if field_catalog_entry is None:
        raise ValueError(f'Missing field catalog entry for {COMMISSION_SETTING_ENDPOINT_ID}.')

    variances_by_id = {
        entry['variance_id']: entry
        for entry in variance_registry['entries']
        if entry['endpoint_contract_id'] == COMMISSION_SETTING_ENDPOINT_ID
    }
    return field_catalog_entry, binding, variances_by_id


def _value_type(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return type(value).__name__


def _walk_observed_fields(value: Any, *, prefix: str, observed: dict[str, set[str]]) -> None:
    if prefix:
        observed.setdefault(prefix, set()).add(_value_type(value))

    if isinstance(value, dict):
        for key, child_value in value.items():
            child_prefix = key if not prefix else f'{prefix}.{key}'
            _walk_observed_fields(child_value, prefix=child_prefix, observed=observed)
        return

    if not isinstance(value, list):
        return

    for item in value:
        if isinstance(item, dict):
            for key, child_value in item.items():
                child_prefix = f'{prefix}.{key}' if prefix else key
                _walk_observed_fields(child_value, prefix=child_prefix, observed=observed)
        elif isinstance(item, list):
            _walk_observed_fields(item, prefix=prefix, observed=observed)


def _observed_field_types(response_envelopes: list[dict[str, Any]]) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = {}
    for envelope in response_envelopes:
        _walk_observed_fields(envelope, prefix='', observed=observed)
    return {
        field_path: sorted(value_types)
        for field_path, value_types in observed.items()
    }


def _dataset_row_counts(response_envelopes: list[dict[str, Any]]) -> dict[str, int]:
    commission_setting_rows = 0
    commission_setting_detail_rows = 0

    for envelope in response_envelopes:
        ret_data = envelope.get('RetData')
        if not isinstance(ret_data, list):
            continue
        commission_setting_rows += len(ret_data)
        for row in ret_data:
            if not isinstance(row, dict):
                continue
            detail_rows = row.get('PCBaseList') or []
            if isinstance(detail_rows, list):
                commission_setting_detail_rows += len(detail_rows)

    return {
        'commission_setting': commission_setting_rows,
        'commission_setting_detail': commission_setting_detail_rows,
    }


def _snapshot_id(org_id: str, requested_business_date: str, suffix: str) -> str:
    return f'{COMMISSION_SETTING_ENDPOINT_ID}::{org_id}::{requested_business_date}::{suffix}'


def _applied_variance_ids(endpoint_run: dict[str, Any]) -> list[str]:
    applied: list[str] = []
    if endpoint_run['endpoint_status'] == 'source_empty':
        applied.append(SOURCE_EMPTY_VARIANCE_ID)
    if endpoint_run.get('error_taxonomy') == 'source_auth_error':
        applied.append(RUNTIME_HEADER_VARIANCE_ID)
    return applied


def build_commission_setting_field_coverage_snapshot(
    *,
    endpoint_run: dict[str, Any],
    response_envelopes: list[dict[str, Any]],
    requested_business_date: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    field_catalog_entry, _, _ = _load_commission_setting_governance(data_platform_root=data_platform_root)
    expected_fields = {
        item['field_path']
        for item in field_catalog_entry['response_fields']
    }
    observed_field_types = _observed_field_types(response_envelopes)
    observed_governed_field_paths = set(observed_field_types).intersection(expected_fields)
    endpoint_status = endpoint_run['endpoint_status']

    if endpoint_status == 'source_empty':
        applicable_field_paths = sorted(
            field_path
            for field_path in observed_governed_field_paths
            if field_path in SOURCE_EMPTY_ALLOWED_FIELD_PATHS
        )
        covered_field_paths = applicable_field_paths
        missing_field_paths: list[str] = []
        inapplicable_field_paths = sorted(expected_fields.difference(applicable_field_paths))
        coverage_status = 'source_empty_governed'
    elif endpoint_status == 'failed':
        applicable_field_paths = []
        covered_field_paths = []
        missing_field_paths = []
        inapplicable_field_paths = sorted(expected_fields)
        coverage_status = 'blocked_upstream'
    else:
        applicable_field_paths = sorted(expected_fields)
        covered_field_paths = sorted(observed_governed_field_paths)
        missing_field_paths = sorted(expected_fields.difference(observed_governed_field_paths))
        inapplicable_field_paths = []
        coverage_status = 'covered' if not missing_field_paths else 'partial_observation'

    applicable_field_count = len(applicable_field_paths)
    covered_field_count = len(covered_field_paths)
    coverage_ratio = (
        covered_field_count / applicable_field_count
        if applicable_field_count
        else None
    )
    org_id = endpoint_run['org_id']
    snapshot_id = _snapshot_id(org_id, requested_business_date, 'field-coverage')

    return {
        'snapshot_id': snapshot_id,
        'snapshot_trace_ref': build_state_trace_ref('field-coverage-snapshot', snapshot_id),
        'endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
        'org_id': org_id,
        'requested_business_date': requested_business_date,
        'endpoint_run_id': endpoint_run['endpoint_run_id'],
        'endpoint_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
        'coverage_status': coverage_status,
        'governed_field_count': len(expected_fields),
        'applicable_field_count': applicable_field_count,
        'covered_field_count': covered_field_count,
        'coverage_ratio': coverage_ratio,
        'covered_field_paths': covered_field_paths,
        'missing_field_paths': missing_field_paths,
        'inapplicable_field_paths': inapplicable_field_paths,
        'observed_ungoverned_field_paths': sorted(set(observed_field_types).difference(expected_fields)),
        'dataset_row_counts': _dataset_row_counts(response_envelopes),
        'applied_variance_ids': _applied_variance_ids(endpoint_run),
        'updated_at': utcnow_iso(),
    }


def build_commission_setting_schema_alignment_snapshot(
    *,
    endpoint_run: dict[str, Any],
    response_envelopes: list[dict[str, Any]],
    requested_business_date: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    field_catalog_entry, binding, _ = _load_commission_setting_governance(data_platform_root=data_platform_root)
    field_meta = {
        item['field_path']: item
        for item in field_catalog_entry['response_fields']
    }
    observed_field_types = _observed_field_types(response_envelopes)
    ungoverned_observed_field_paths = sorted(set(observed_field_types).difference(field_meta))
    endpoint_status = endpoint_run['endpoint_status']
    mismatches: list[dict[str, Any]] = []
    structural_missing_field_paths: list[str] = []

    if endpoint_status == 'source_empty':
        alignment_status = 'source_empty_governed'
    elif endpoint_status == 'failed':
        alignment_status = 'blocked_upstream'
    else:
        required_structural_paths = [
            field_path
            for field_path, item in field_meta.items()
            if item['path_kind'] in {
                'response_status',
                'response_message',
                'record_collection',
                'nested_record_collection',
            }
        ]
        for field_path in required_structural_paths:
            if field_path not in observed_field_types:
                structural_missing_field_paths.append(field_path)
                mismatches.append({
                    'field_path': field_path,
                    'expected_data_type': field_meta[field_path]['data_type'],
                    'observed_data_types': [],
                    'reason': 'expected_path_missing',
                })

        for field_path, value_types in observed_field_types.items():
            if field_path not in field_meta:
                continue
            expected_data_type = field_meta[field_path]['data_type']
            if expected_data_type not in value_types:
                mismatches.append({
                    'field_path': field_path,
                    'expected_data_type': expected_data_type,
                    'observed_data_types': value_types,
                    'reason': 'observed_type_mismatch',
                })

        alignment_status = 'aligned'
        if mismatches or ungoverned_observed_field_paths:
            alignment_status = 'misaligned'

    org_id = endpoint_run['org_id']
    snapshot_id = _snapshot_id(org_id, requested_business_date, 'schema-alignment')

    return {
        'snapshot_id': snapshot_id,
        'snapshot_trace_ref': build_state_trace_ref('schema-alignment-snapshot', snapshot_id),
        'endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
        'org_id': org_id,
        'requested_business_date': requested_business_date,
        'endpoint_run_id': endpoint_run['endpoint_run_id'],
        'endpoint_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
        'alignment_status': alignment_status,
        'response_payload_shape': binding['response_payload_shape'],
        'mismatch_count': len(mismatches),
        'mismatches': mismatches,
        'structural_missing_field_paths': structural_missing_field_paths,
        'ungoverned_observed_field_paths': ungoverned_observed_field_paths,
        'applied_variance_ids': _applied_variance_ids(endpoint_run),
        'updated_at': utcnow_iso(),
    }


def _quality_issue(
    *,
    org_id: str,
    requested_business_date: str,
    issue_code: str,
    severity: str,
    summary: str,
    state_trace_refs: list[str],
    run_trace_refs: list[str],
    related_variance_ids: list[str] | None = None,
) -> dict[str, Any]:
    issue_id = f'{COMMISSION_SETTING_ENDPOINT_ID}::{org_id}::{requested_business_date}::{issue_code}'
    return {
        'issue_id': issue_id,
        'issue_trace_ref': build_state_trace_ref('quality-issue', issue_id),
        'endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
        'org_id': org_id,
        'requested_business_date': requested_business_date,
        'issue_code': issue_code,
        'severity': severity,
        'issue_status': 'open',
        'summary': summary,
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'related_variance_ids': related_variance_ids or [],
        'updated_at': utcnow_iso(),
    }


def build_commission_setting_quality_issues(
    *,
    endpoint_run: dict[str, Any],
    field_coverage_snapshot: dict[str, Any],
    schema_alignment_snapshot: dict[str, Any],
    backfill_progress_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    org_id = endpoint_run['org_id']
    requested_business_date = field_coverage_snapshot['requested_business_date']
    run_trace_refs = [endpoint_run['endpoint_run_trace_ref']]
    issues: list[dict[str, Any]] = []

    if endpoint_run['endpoint_status'] == 'source_empty':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='source_empty_current_day_full_replace',
            severity='info',
            summary='Commission setting returned no rows and is governed as a current zero-row full-replace snapshot.',
            state_trace_refs=[
                field_coverage_snapshot['snapshot_trace_ref'],
                schema_alignment_snapshot['snapshot_trace_ref'],
            ],
            run_trace_refs=run_trace_refs,
            related_variance_ids=[SOURCE_EMPTY_VARIANCE_ID],
        ))

    if endpoint_run.get('error_taxonomy') == 'source_auth_error':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='upstream_auth_headers_required',
            severity='error',
            summary='Commission setting is blocked by upstream auth failure; the governed runtime header variance must be satisfied.',
            state_trace_refs=[
                field_coverage_snapshot['snapshot_trace_ref'],
                schema_alignment_snapshot['snapshot_trace_ref'],
            ],
            run_trace_refs=run_trace_refs,
            related_variance_ids=[RUNTIME_HEADER_VARIANCE_ID],
        ))
    elif endpoint_run['endpoint_status'] == 'failed':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='upstream_endpoint_error',
            severity='error',
            summary='Commission setting latest state is blocked by an upstream endpoint failure.',
            state_trace_refs=[
                field_coverage_snapshot['snapshot_trace_ref'],
                schema_alignment_snapshot['snapshot_trace_ref'],
            ],
            run_trace_refs=run_trace_refs,
        ))

    if field_coverage_snapshot['coverage_status'] == 'partial_observation':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='field_coverage_partial',
            severity='warning',
            summary='Observed commission-setting payload covered only part of the governed field catalog for this snapshot.',
            state_trace_refs=[field_coverage_snapshot['snapshot_trace_ref']],
            run_trace_refs=run_trace_refs,
        ))

    if schema_alignment_snapshot['alignment_status'] == 'misaligned':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='schema_alignment_gap',
            severity='error',
            summary='Observed commission-setting payload no longer aligns with the governed field catalog and response shape.',
            state_trace_refs=[schema_alignment_snapshot['snapshot_trace_ref']],
            run_trace_refs=run_trace_refs,
        ))

    if backfill_progress_state and backfill_progress_state['backfill_progress_status'] != 'complete':
        issues.append(_quality_issue(
            org_id=org_id,
            requested_business_date=requested_business_date,
            issue_code='backfill_gap',
            severity='warning',
            summary='Commission-setting backfill coverage is incomplete for the governed business-date window.',
            state_trace_refs=[backfill_progress_state['state_trace_ref']],
            run_trace_refs=run_trace_refs,
        ))

    return issues


__all__ = [
    'COMMISSION_SETTING_ENDPOINT_ID',
    'RUNTIME_HEADER_VARIANCE_ID',
    'SOURCE_EMPTY_VARIANCE_ID',
    'build_commission_setting_field_coverage_snapshot',
    'build_commission_setting_quality_issues',
    'build_commission_setting_schema_alignment_snapshot',
]
