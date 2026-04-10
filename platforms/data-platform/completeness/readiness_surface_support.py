from __future__ import annotations

from typing import Any, Iterable


LEGACY_REASON_CODE_MAP = {
    'capability_not_registered': 'capability_scope_not_supported',
    'dependency_failed': 'upstream_error',
    'missing_dependency': 'required_dataset_missing',
    'scope_out_of_contract': 'projection_not_available',
}


def unique_strings(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def normalize_reason_codes(values: Iterable[str | None]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not value:
            continue
        normalized.append(LEGACY_REASON_CODE_MAP.get(value, value))
    return unique_strings(normalized)


def latest_usable_business_date_from_states(
    latest_states: list[dict[str, Any]],
    fallback_business_date: str,
) -> str:
    usable_dates = [
        state.get('latest_usable_business_date')
        for state in latest_states
        if state.get('latest_usable_business_date')
    ]
    return min(usable_dates) if usable_dates else fallback_business_date


def endpoint_run_trace_refs(vertical_slice_result: dict[str, Any]) -> list[str]:
    historical_run_truth = vertical_slice_result.get('historical_run_truth', {})
    ingestion_run = historical_run_truth.get('ingestion_run', {})
    endpoint_runs = historical_run_truth.get('endpoint_runs', [])
    return unique_strings([
        ingestion_run.get('run_trace_ref'),
        *[endpoint_run.get('endpoint_run_trace_ref') for endpoint_run in endpoint_runs],
    ])


def latest_state_trace_refs(
    backbone_state: dict[str, Any],
    latest_states: list[dict[str, Any]],
) -> list[str]:
    return unique_strings([
        backbone_state.get('state_trace_ref'),
        *[state.get('state_trace_ref') for state in latest_states],
    ])
