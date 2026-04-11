from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import build_state_trace_ref, utcnow_iso
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
) -> dict[str, Any]:
    plan = build_nightly_sync_plan(
        source_system_id=source_system_id,
        org_id=org_id,
        target_business_date=target_business_date,
        expected_business_dates=expected_business_dates,
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
    for task in plan['backfill_tasks']:
        if len(dispatch_plan) >= max_dispatch_tasks:
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

    cycle_id = f'{source_system_id}::{org_id}::{target_business_date}::nightly-sync-cycle'
    return {
        'cycle_id': cycle_id,
        'cycle_trace_ref': build_state_trace_ref('nightly-sync-cycle', cycle_id),
        'generated_at': utcnow_iso(),
        'source_system_id': source_system_id,
        'org_id': org_id,
        'target_business_date': target_business_date,
        'max_dispatch_tasks': max_dispatch_tasks,
        'planner_output': plan,
        'cursor_states': cursor_states,
        'cursor_ledger': cursor_ledger,
        'dispatch_plan': dispatch_plan,
        'deferred_currentness_tasks': max(
            0,
            len(plan['currentness_tasks'])
            - len([entry for entry in dispatch_plan if entry['dispatch_priority'] == 'currentness']),
        ),
        'deferred_backfill_tasks': max(
            0,
            len(plan['backfill_tasks'])
            - len([entry for entry in dispatch_plan if entry['dispatch_priority'] == 'backfill']),
        ),
    }


__all__ = ['build_nightly_sync_scheduler_snapshot']
