from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso
from directory.business_day_boundary_policy_registry import (
    resolve_business_day_boundary_policy as resolve_directory_business_day_boundary_policy,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
COMMISSION_SETTING_ENDPOINT_ID = 'qinqin.staff.get_tech_commission_set_list.v1_8'
USABLE_AVAILABILITY_STATUSES = {'available', 'source_empty'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def _load_business_day_policy_registry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    return _load_json(data_platform_root / 'directory' / 'business-day-boundary-policy.seed.json')


def resolve_business_day_boundary_policy(
    *,
    org_ref: str | None = None,
    store_ref: str | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    return resolve_directory_business_day_boundary_policy(
        org_ref=org_ref,
        store_ref=store_ref,
        data_platform_root=data_platform_root,
    )


def _availability_status(endpoint_run: dict[str, Any]) -> str:
    endpoint_status = endpoint_run['endpoint_status']
    if endpoint_status == 'completed':
        return 'available'
    if endpoint_status == 'source_empty':
        return 'source_empty'
    return 'unavailable'


def build_commission_setting_latest_usable_endpoint_state(
    *,
    endpoint_run: dict[str, Any],
    requested_business_date: str,
    source_system_id: str = 'qinqin.v1_1',
) -> dict[str, Any]:
    availability_status = _availability_status(endpoint_run)
    is_usable = availability_status in USABLE_AVAILABILITY_STATUSES
    state_id = f"{COMMISSION_SETTING_ENDPOINT_ID}::{endpoint_run['org_id']}::{requested_business_date}"
    observed_outcome_category = (
        endpoint_run.get('terminal_outcome_category')
        or 'success' if endpoint_run['endpoint_status'] == 'completed'
        else endpoint_run['endpoint_status']
    )

    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('latest-usable-endpoint-state', state_id),
        'source_system_id': source_system_id,
        'endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
        'org_id': endpoint_run['org_id'],
        'requested_business_date': requested_business_date,
        'availability_status': availability_status,
        'latest_observed_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
        'latest_observed_endpoint_run_id': endpoint_run['endpoint_run_id'],
        'latest_observed_endpoint_status': endpoint_run['endpoint_status'],
        'latest_observed_outcome_category': observed_outcome_category,
        'latest_usable_business_date': requested_business_date if is_usable else None,
        'latest_usable_run_trace_ref': endpoint_run['endpoint_run_trace_ref'] if is_usable else None,
        'latest_usable_endpoint_run_id': endpoint_run['endpoint_run_id'] if is_usable else None,
        'latest_usable_outcome_category': observed_outcome_category if is_usable else None,
        'blocking_category': None if is_usable else observed_outcome_category,
        'failure_taxonomy': endpoint_run.get('error_taxonomy'),
        'failure_code': endpoint_run.get('error_code'),
        'failure_message': endpoint_run.get('error_message'),
        'updated_at': utcnow_iso(),
    }


def build_commission_setting_backfill_progress_state(
    *,
    org_id: str,
    target_business_date: str,
    expected_business_dates: list[str],
    latest_usable_endpoint_states: list[dict[str, Any]],
    org_ref: str | None = None,
    store_ref: str | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    policy_entry = resolve_business_day_boundary_policy(
        org_ref=org_ref,
        store_ref=store_ref,
        data_platform_root=data_platform_root,
    )
    normalized_expected_dates = sorted(set([*expected_business_dates, target_business_date]))
    covered_states_by_business_date: dict[str, dict[str, Any]] = {}
    for state in latest_usable_endpoint_states:
        business_date = state.get('latest_usable_business_date')
        if not business_date:
            continue
        covered_states_by_business_date[str(business_date)] = state

    covered_business_dates = sorted(covered_states_by_business_date)
    missing_business_dates = [
        business_date
        for business_date in normalized_expected_dates
        if business_date not in covered_states_by_business_date
    ]
    latest_usable_business_date = max(covered_business_dates) if covered_business_dates else None
    latest_usable_state = (
        covered_states_by_business_date[latest_usable_business_date]
        if latest_usable_business_date
        else None
    )

    if target_business_date in covered_states_by_business_date:
        currentness_status = 'current'
        if missing_business_dates:
            backfill_progress_status = 'incomplete'
            progress_reason_codes = ['historical_backfill_gap']
        else:
            backfill_progress_status = 'complete'
            progress_reason_codes = []
    elif latest_usable_business_date:
        currentness_status = 'stale'
        backfill_progress_status = 'incomplete'
        progress_reason_codes = ['latest_usable_business_date_behind_target']
    else:
        currentness_status = 'blocked'
        backfill_progress_status = 'blocked'
        progress_reason_codes = ['target_business_date_unusable']

    state_id = f'{COMMISSION_SETTING_ENDPOINT_ID}::{org_id}::{target_business_date}::backfill'
    return {
        'state_id': state_id,
        'state_trace_ref': build_state_trace_ref('backfill-progress-state', state_id),
        'endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
        'org_id': org_id,
        'target_business_date': target_business_date,
        'expected_business_dates': normalized_expected_dates,
        'covered_business_dates': covered_business_dates,
        'missing_business_dates': missing_business_dates,
        'latest_usable_business_date': latest_usable_business_date,
        'latest_usable_state_trace_ref': latest_usable_state['state_trace_ref'] if latest_usable_state else None,
        'backfill_progress_status': backfill_progress_status,
        'currentness_status': currentness_status,
        'progress_reason_codes': progress_reason_codes,
        'business_day_boundary_policy_id': policy_entry['policy_id'],
        'business_day_boundary_local_time': policy_entry['business_day_boundary_local_time'],
        'timezone': policy_entry['timezone'],
        'updated_at': utcnow_iso(),
    }


__all__ = [
    'build_commission_setting_backfill_progress_state',
    'build_commission_setting_latest_usable_endpoint_state',
    'resolve_business_day_boundary_policy',
]
