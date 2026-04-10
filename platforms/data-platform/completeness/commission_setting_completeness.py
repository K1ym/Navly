from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_commission_setting_completeness_state(
    *,
    latest_usable_endpoint_state: dict[str, Any],
    backfill_progress_state: dict[str, Any],
    field_coverage_snapshot: dict[str, Any],
    schema_alignment_snapshot: dict[str, Any],
    quality_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    endpoint_contract_id = latest_usable_endpoint_state['endpoint_contract_id']
    org_id = latest_usable_endpoint_state['org_id']
    requested_business_date = latest_usable_endpoint_state['requested_business_date']
    availability_status = latest_usable_endpoint_state['availability_status']
    currentness_status = backfill_progress_state['currentness_status']
    schema_alignment_status = schema_alignment_snapshot['alignment_status']

    if schema_alignment_status == 'misaligned':
        completeness_status = 'blocked'
        reason_codes = ['schema_alignment_gap']
    elif currentness_status == 'blocked':
        completeness_status = 'blocked'
        reason_codes = ['upstream_unavailable']
    elif currentness_status != 'current':
        completeness_status = 'incomplete'
        reason_codes = ['latest_state_stale']
    elif availability_status == 'source_empty':
        completeness_status = 'complete'
        reason_codes = ['source_empty_current']
    else:
        completeness_status = 'complete'
        reason_codes = []

    state_id = f'{endpoint_contract_id}::{org_id}::{requested_business_date}::completeness'
    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('commission-setting-completeness-state', state_id),
        'endpoint_contract_id': endpoint_contract_id,
        'org_id': org_id,
        'requested_business_date': requested_business_date,
        'latest_usable_business_date': latest_usable_endpoint_state.get('latest_usable_business_date'),
        'completeness_status': completeness_status,
        'reason_codes': reason_codes,
        'coverage_status': field_coverage_snapshot['coverage_status'],
        'schema_alignment_status': schema_alignment_status,
        'backfill_progress_status': backfill_progress_state['backfill_progress_status'],
        'currentness_status': currentness_status,
        'quality_issue_codes': [issue['issue_code'] for issue in quality_issues],
        'quality_issue_refs': [issue['issue_trace_ref'] for issue in quality_issues],
        'state_trace_refs': _unique_strings([
            latest_usable_endpoint_state.get('state_trace_ref'),
            backfill_progress_state.get('state_trace_ref'),
            field_coverage_snapshot.get('snapshot_trace_ref'),
            schema_alignment_snapshot.get('snapshot_trace_ref'),
        ]),
        'run_trace_refs': _unique_strings([
            latest_usable_endpoint_state.get('latest_observed_run_trace_ref'),
        ]),
        'updated_at': utcnow_iso(),
    }


__all__ = ['build_commission_setting_completeness_state']
