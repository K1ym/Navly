from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso
from directory.nightly_sync_policy_registry import resolve_nightly_sync_history_start_business_date
from ingestion.nightly_sync_planner import build_nightly_sync_plan

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_filename: str, module_name: str):
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / module_filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _dispatch_entry(
    *,
    dispatch_sequence: int,
    task: dict[str, Any],
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    dispatch_priority: str,
) -> dict[str, Any]:
    dispatch_id = (
        f'{source_system_id}::{org_id}::{target_business_date}'
        f'::dispatch::{dispatch_priority}::{dispatch_sequence}'
    )
    return {
        'dispatch_id': dispatch_id,
        'dispatch_trace_ref': build_state_trace_ref('nightly-sync-dispatch', dispatch_id),
        'dispatch_sequence': dispatch_sequence,
        'dispatch_priority': dispatch_priority,
        **task,
    }


def resolve_expected_business_dates(
    *,
    target_business_date: str,
    expected_business_dates: list[str],
    history_start_business_date: str | None = None,
) -> list[str]:
    resolved_dates = set([*expected_business_dates, target_business_date])
    if history_start_business_date:
        start_date = date.fromisoformat(history_start_business_date)
        end_date = date.fromisoformat(target_business_date)
        if start_date <= end_date:
            current_date = start_date
            while current_date <= end_date:
                resolved_dates.add(current_date.isoformat())
                current_date += timedelta(days=1)
    return sorted(resolved_dates)


def build_nightly_sync_scheduler_snapshot(
    *,
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    expected_business_dates: list[str],
    latest_usable_endpoint_states: list[dict[str, Any]] | None = None,
    endpoint_contract_ids: list[str] | None = None,
    prior_ledger_entries: list[dict[str, Any]] | None = None,
    max_dispatch_tasks: int = 8,
    max_backfill_dispatch_tasks: int | None = None,
    history_start_business_date: str | None = None,
) -> dict[str, Any]:
    resolved_history_start_business_date = resolve_nightly_sync_history_start_business_date(
        source_system_id,
        explicit_history_start_business_date=history_start_business_date,
        data_platform_root=DATA_PLATFORM_ROOT,
    )
    resolved_expected_business_dates = resolve_expected_business_dates(
        target_business_date=target_business_date,
        expected_business_dates=expected_business_dates,
        history_start_business_date=resolved_history_start_business_date,
    )
    plan = build_nightly_sync_plan(
        source_system_id=source_system_id,
        org_id=org_id,
        target_business_date=target_business_date,
        expected_business_dates=resolved_expected_business_dates,
        latest_usable_endpoint_states=latest_usable_endpoint_states,
        endpoint_contract_ids=endpoint_contract_ids,
        data_platform_root=DATA_PLATFORM_ROOT,
    )
    cursor_state_module = _load_module(
        'nightly_sync_cursor_state.py',
        'navly_data_platform_sync_state_nightly_sync_cursor_state',
    )
    cursor_ledger_module = _load_module(
        'nightly_sync_cursor_ledger.py',
        'navly_data_platform_sync_state_nightly_sync_cursor_ledger',
    )
    cursor_states = cursor_state_module.build_nightly_sync_cursor_states(plan)
    cursor_ledger = cursor_ledger_module.build_nightly_sync_cursor_ledger(
        cursor_states,
        prior_ledger_entries=prior_ledger_entries,
    )

    dispatch_plan: list[dict[str, Any]] = []
    dispatch_sequence = 1
    dispatched_currentness_count = 0
    for task in plan['currentness_tasks']:
        if len(dispatch_plan) >= max_dispatch_tasks:
            break
        dispatch_plan.append(
            _dispatch_entry(
                dispatch_sequence=dispatch_sequence,
                task=task,
                source_system_id=source_system_id,
                org_id=org_id,
                target_business_date=target_business_date,
                dispatch_priority='currentness',
            )
        )
        dispatch_sequence += 1
        dispatched_currentness_count += 1
    deferred_currentness_tasks = max(
        0,
        len(plan['currentness_tasks']) - dispatched_currentness_count,
    )
    resolved_backfill_dispatch_budget = (
        0
        if deferred_currentness_tasks > 0
        else (
            max_backfill_dispatch_tasks
            if max_backfill_dispatch_tasks is not None
            else max(0, max_dispatch_tasks - dispatched_currentness_count)
        )
    )
    dispatched_backfill_count = 0
    for task in plan['backfill_tasks']:
        if dispatched_backfill_count >= resolved_backfill_dispatch_budget:
            break
        dispatch_plan.append(
            _dispatch_entry(
                dispatch_sequence=dispatch_sequence,
                task=task,
                source_system_id=source_system_id,
                org_id=org_id,
                target_business_date=target_business_date,
                dispatch_priority='backfill',
            )
        )
        dispatch_sequence += 1
        dispatched_backfill_count += 1

    cycle_id = f'{source_system_id}::{org_id}::{target_business_date}::nightly-sync-cycle'
    return {
        'cycle_id': cycle_id,
        'cycle_trace_ref': build_state_trace_ref('nightly-sync-cycle', cycle_id),
        'generated_at': utcnow_iso(),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'target_business_date': target_business_date,
        'max_dispatch_tasks': max_dispatch_tasks,
        'max_backfill_dispatch_tasks': max_backfill_dispatch_tasks,
        'history_start_business_date': resolved_history_start_business_date,
        'planner_output': plan,
        'cursor_states': cursor_states,
        'cursor_ledger': cursor_ledger,
        'dispatch_plan': dispatch_plan,
        'deferred_currentness_tasks': deferred_currentness_tasks,
        'deferred_backfill_tasks': max(
            0,
            len(plan['backfill_tasks']) - dispatched_backfill_count,
        ),
    }


__all__ = ['build_nightly_sync_scheduler_snapshot']
