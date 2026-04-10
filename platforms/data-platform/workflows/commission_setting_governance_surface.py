from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from completeness.commission_setting_completeness import build_commission_setting_completeness_state
from quality.commission_setting_quality import (
    build_commission_setting_field_coverage_snapshot,
    build_commission_setting_quality_issues,
    build_commission_setting_schema_alignment_snapshot,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _load_commission_setting_sync_state_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'commission_setting_sync_state.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_commission_setting',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _dedupe_latest_states(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for state in states:
        deduped[(state['org_id'], state.get('requested_business_date') or state.get('latest_usable_business_date') or '')] = state
    return list(deduped.values())


def build_commission_setting_governance_surface(
    *,
    endpoint_run: dict[str, Any],
    response_envelopes: list[dict[str, Any]],
    requested_business_date: str,
    expected_business_dates: list[str] | None = None,
    prior_latest_usable_states: list[dict[str, Any]] | None = None,
    org_ref: str | None = None,
    store_ref: str | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    sync_state_module = _load_commission_setting_sync_state_module()
    latest_usable_endpoint_state = sync_state_module.build_commission_setting_latest_usable_endpoint_state(
        endpoint_run=endpoint_run,
        requested_business_date=requested_business_date,
    )
    historical_latest_states = _dedupe_latest_states([
        *(prior_latest_usable_states or []),
        latest_usable_endpoint_state,
    ])
    backfill_progress_state = sync_state_module.build_commission_setting_backfill_progress_state(
        org_id=endpoint_run['org_id'],
        target_business_date=requested_business_date,
        expected_business_dates=expected_business_dates or [requested_business_date],
        latest_usable_endpoint_states=historical_latest_states,
        org_ref=org_ref,
        store_ref=store_ref,
        data_platform_root=data_platform_root,
    )
    field_coverage_snapshot = build_commission_setting_field_coverage_snapshot(
        endpoint_run=endpoint_run,
        response_envelopes=response_envelopes,
        requested_business_date=requested_business_date,
        data_platform_root=data_platform_root,
    )
    schema_alignment_snapshot = build_commission_setting_schema_alignment_snapshot(
        endpoint_run=endpoint_run,
        response_envelopes=response_envelopes,
        requested_business_date=requested_business_date,
        data_platform_root=data_platform_root,
    )
    quality_issues = build_commission_setting_quality_issues(
        endpoint_run=endpoint_run,
        field_coverage_snapshot=field_coverage_snapshot,
        schema_alignment_snapshot=schema_alignment_snapshot,
        backfill_progress_state=backfill_progress_state,
    )
    completeness_state = build_commission_setting_completeness_state(
        latest_usable_endpoint_state=latest_usable_endpoint_state,
        backfill_progress_state=backfill_progress_state,
        field_coverage_snapshot=field_coverage_snapshot,
        schema_alignment_snapshot=schema_alignment_snapshot,
        quality_issues=quality_issues,
    )
    return {
        'endpoint_contract_id': latest_usable_endpoint_state['endpoint_contract_id'],
        'requested_business_date': requested_business_date,
        'latest_state_artifacts': {
            'latest_usable_endpoint_state': latest_usable_endpoint_state,
            'backfill_progress_state': backfill_progress_state,
        },
        'quality_artifacts': {
            'field_coverage_snapshot': field_coverage_snapshot,
            'schema_alignment_snapshot': schema_alignment_snapshot,
            'quality_issues': quality_issues,
        },
        'completeness_artifacts': {
            'commission_setting_completeness_state': completeness_state,
        },
    }


__all__ = ['build_commission_setting_governance_surface']
