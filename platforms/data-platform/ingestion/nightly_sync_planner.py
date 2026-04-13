from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from directory.nightly_sync_policy_registry import load_nightly_sync_policy_entry

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _endpoint_contract_entries(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, dict[str, Any]]:
    payload = _load_json(data_platform_root / 'directory' / 'endpoint-contracts.seed.json')
    return {
        entry['endpoint_contract_id']: entry
        for entry in payload['entries']
        if entry['domain'] != 'shared'
    }


def _date_range(end_business_date: str, days: int) -> list[str]:
    end_date = date.fromisoformat(end_business_date)
    return [
        (end_date - timedelta(days=offset)).isoformat()
        for offset in reversed(range(days))
    ]


def _usable_dates_by_endpoint(
    latest_usable_endpoint_states: list[dict[str, Any]],
) -> dict[str, list[str]]:
    usable: dict[str, set[str]] = {}
    for state in latest_usable_endpoint_states:
        endpoint_contract_id = state.get('endpoint_contract_id')
        business_date = state.get('latest_usable_business_date')
        if not endpoint_contract_id or not business_date:
            continue
        usable.setdefault(str(endpoint_contract_id), set()).add(str(business_date))
    return {
        endpoint_contract_id: sorted(dates)
        for endpoint_contract_id, dates in usable.items()
    }


def build_nightly_sync_plan(
    *,
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    expected_business_dates: list[str],
    latest_usable_endpoint_states: list[dict[str, Any]] | None = None,
    endpoint_contract_ids: list[str] | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    policy_entry = load_nightly_sync_policy_entry(
        source_system_id,
        data_platform_root=data_platform_root,
    )
    endpoint_entries = _endpoint_contract_entries(data_platform_root=data_platform_root)
    selected_endpoint_ids = endpoint_contract_ids or [
        endpoint_contract_id
        for endpoint_contract_id, entry in endpoint_entries.items()
        if entry['source_system_id'] == source_system_id
    ]
    normalized_expected_dates = sorted(set([*expected_business_dates, target_business_date]))
    usable_dates_by_endpoint = _usable_dates_by_endpoint(latest_usable_endpoint_states or [])

    currentness_tasks: list[dict[str, Any]] = []
    backfill_tasks: list[dict[str, Any]] = []
    endpoint_plans: list[dict[str, Any]] = []
    backfill_dates_by_endpoint: dict[str, list[str]] = {}

    for endpoint_contract_id in selected_endpoint_ids:
        entry = endpoint_entries[endpoint_contract_id]
        increment_strategy = entry['increment_strategy']
        strategy_policy = policy_entry['increment_strategy_policies'][increment_strategy]
        covered_business_dates = usable_dates_by_endpoint.get(endpoint_contract_id, [])
        covered_business_date_set = set(covered_business_dates)
        latest_usable_business_date = max(covered_business_dates) if covered_business_dates else None
        missing_business_dates = [
            business_date
            for business_date in normalized_expected_dates
            if business_date not in covered_business_date_set
        ]
        target_is_covered = target_business_date in covered_business_date_set
        older_missing_business_dates = [
            business_date
            for business_date in missing_business_dates
            if business_date < target_business_date
        ]

        currentness_status = (
            'current'
            if target_is_covered
            else 'stale'
            if latest_usable_business_date
            else 'blocked'
        )
        currentness_window_business_days = int(strategy_policy['currentness_window_business_days'])
        currentness_window_dates = _date_range(
            target_business_date,
            currentness_window_business_days,
        )

        currentness_task: dict[str, Any] | None = None
        if not target_is_covered:
            if increment_strategy == 'profile_refresh_windowed':
                currentness_task = {
                    'task_kind': 'profile_refresh_window',
                    'endpoint_contract_id': endpoint_contract_id,
                    'display_name': entry['display_name'],
                    'window_start_business_date': currentness_window_dates[0],
                    'window_end_business_date': currentness_window_dates[-1],
                    'structured_targets': entry['structured_targets'],
                }
            else:
                currentness_task = {
                    'task_kind': 'target_business_date_sync',
                    'endpoint_contract_id': endpoint_contract_id,
                    'display_name': entry['display_name'],
                    'business_date': target_business_date,
                    'structured_targets': entry['structured_targets'],
                }
            currentness_tasks.append(currentness_task)

        recommended_next_backfill_business_date: str | None = None
        backlog_progress_status = 'not_applicable'
        if strategy_policy['allow_historical_backfill']:
            backlog_progress_status = (
                'complete' if not older_missing_business_dates else 'incomplete'
            )
            if older_missing_business_dates:
                descending_missing_business_dates = sorted(
                    older_missing_business_dates,
                    reverse=True,
                )
                recommended_next_backfill_business_date = descending_missing_business_dates[0]
                backfill_dates_by_endpoint[endpoint_contract_id] = descending_missing_business_dates

        endpoint_plans.append({
            'endpoint_contract_id': endpoint_contract_id,
            'display_name': entry['display_name'],
            'increment_strategy': increment_strategy,
            'structured_targets': entry['structured_targets'],
            'latest_usable_business_date': latest_usable_business_date,
            'covered_business_dates': covered_business_dates,
            'missing_business_dates': missing_business_dates,
            'currentness_status': currentness_status,
            'backfill_progress_status': backlog_progress_status,
            'currentness_window_business_dates': currentness_window_dates,
            'recommended_next_currentness_task': currentness_task,
            'recommended_next_backfill_business_date': recommended_next_backfill_business_date,
        })

    if backfill_dates_by_endpoint:
        max_backfill_depth = max(len(dates) for dates in backfill_dates_by_endpoint.values())
        for backfill_depth in range(max_backfill_depth):
            for endpoint_contract_id in selected_endpoint_ids:
                candidate_dates = backfill_dates_by_endpoint.get(endpoint_contract_id, [])
                if backfill_depth >= len(candidate_dates):
                    continue
                entry = endpoint_entries[endpoint_contract_id]
                backfill_tasks.append({
                    'task_kind': 'historical_backfill_sync',
                    'endpoint_contract_id': endpoint_contract_id,
                    'display_name': entry['display_name'],
                    'business_date': candidate_dates[backfill_depth],
                    'remaining_business_dates': candidate_dates[backfill_depth:],
                    'carry_forward_cursor': bool(policy_entry['carry_forward_cursor']),
                    'structured_targets': entry['structured_targets'],
                    'backfill_depth': backfill_depth + 1,
                })

    return {
        'plan_id': f'{source_system_id}::{org_id}::{target_business_date}::nightly-sync-plan',
        'generated_at': utcnow_iso(),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'target_business_date': target_business_date,
        'expected_business_dates': normalized_expected_dates,
        'sync_policy_id': policy_entry['sync_policy_id'],
        'timezone': policy_entry['timezone'],
        'activation_local_time': policy_entry['activation_local_time'],
        'formal_access_window_start_local_time': policy_entry[
            'formal_access_window_start_local_time'
        ],
        'formal_access_window_end_exclusive_local_time': policy_entry[
            'formal_access_window_end_exclusive_local_time'
        ],
        'currentness_priority': policy_entry['currentness_priority'],
        'backfill_fill_direction': policy_entry['backfill_fill_direction'],
        'carry_forward_cursor': policy_entry['carry_forward_cursor'],
        'default_page_size': policy_entry['default_page_size'],
        'currentness_tasks': currentness_tasks,
        'backfill_tasks': backfill_tasks,
        'endpoint_plans': endpoint_plans,
    }


__all__ = ['build_nightly_sync_plan']
