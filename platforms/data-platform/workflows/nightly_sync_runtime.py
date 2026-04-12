from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

from connectors.qinqin.qinqin_substrate import (
    DEFAULT_LIVE_TIMEOUT_MS,
    FixtureQinqinTransport,
    LiveQinqinTransport,
)
from ingestion.finance_summary_vertical_slice import run_finance_summary_vertical_slice
from ingestion.member_insight_vertical_slice import run_member_insight_vertical_slice
from ingestion.staff_board_vertical_slice import run_staff_board_vertical_slice
from workflows.commission_setting_endpoint_sync import run_commission_setting_endpoint_sync
from workflows.nightly_sync_scheduler import build_nightly_sync_scheduler_snapshot

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = DATA_PLATFORM_ROOT / 'output' / 'nightly-sync-runtime'

MEMBER_ENDPOINTS = {
    'qinqin.member.get_customers_list.v1_1',
    'qinqin.member.get_consume_bill_list.v1_2',
}
FINANCE_ENDPOINTS = {
    'qinqin.member.get_recharge_bill_list.v1_3',
    'qinqin.member.get_user_trade_list.v1_4',
}
STAFF_ENDPOINTS = {
    'qinqin.staff.get_person_list.v1_5',
    'qinqin.staff.get_tech_up_clock_list.v1_6',
    'qinqin.staff.get_tech_market_list.v1_7',
}
COMMISSION_ENDPOINT = 'qinqin.staff.get_tech_commission_set_list.v1_8'


def _resolve_env(name: str, fallback: str | None = None) -> str | None:
    return os.environ.get(name) or (os.environ.get(fallback) if fallback else None)


def _load_cursor_ledger_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'nightly_sync_cursor_ledger.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_nightly_sync_cursor_ledger_runtime',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_live_transport_from_env() -> LiveQinqinTransport:
    timeout_raw = _resolve_env('QINQIN_API_REQUEST_TIMEOUT_MS')
    timeout_ms = int(timeout_raw) if timeout_raw else DEFAULT_LIVE_TIMEOUT_MS
    return LiveQinqinTransport(
        base_url=_resolve_env('QINQIN_API_BASE_URL', 'QINQIN_REAL_DATA_URL') or '',
        timeout_ms=timeout_ms,
        authorization=_resolve_env('QINQIN_API_AUTHORIZATION'),
        token=_resolve_env('QINQIN_API_TOKEN', 'QINQIN_REAL_DATA_TOKEN'),
    )


def _business_window(group: dict[str, Any]) -> tuple[str, str]:
    start_candidates: list[str] = []
    end_candidates: list[str] = []
    for task in group['tasks']:
        if task['task_kind'] == 'profile_refresh_window':
            start_candidates.append(task['window_start_business_date'])
            end_candidates.append(task['window_end_business_date'])
        else:
            start_candidates.append(task['business_date'])
            end_candidates.append(task['business_date'])
    start_business_date = min(start_candidates)
    end_business_date = max(end_candidates)
    start_time = f'{start_business_date} 03:00:00'
    end_time = f'{end_business_date} 23:59:59'
    return start_time, end_time


def _slice_id_for_endpoint(endpoint_contract_id: str) -> str:
    if endpoint_contract_id in MEMBER_ENDPOINTS:
        return 'member_insight'
    if endpoint_contract_id in FINANCE_ENDPOINTS:
        return 'finance_summary'
    if endpoint_contract_id in STAFF_ENDPOINTS:
        return 'staff_board'
    if endpoint_contract_id == COMMISSION_ENDPOINT:
        return 'commission_setting'
    raise KeyError(f'Unsupported endpoint_contract_id for nightly runtime: {endpoint_contract_id}')


def _group_dispatch_plan(dispatch_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in dispatch_plan:
        slice_id = _slice_id_for_endpoint(entry['endpoint_contract_id'])
        key = (entry['dispatch_priority'], slice_id)
        grouped.setdefault(key, {
            'slice_id': slice_id,
            'dispatch_priority': entry['dispatch_priority'],
            'tasks': [],
        })
        grouped[key]['tasks'].append(entry)
    for group in grouped.values():
        business_dates = [
            entry.get('business_date') or entry.get('window_end_business_date')
            for entry in group['tasks']
            if entry.get('business_date') or entry.get('window_end_business_date')
        ]
        group['target_business_date'] = max(business_dates) if business_dates else ''
        task_kinds = sorted({entry['task_kind'] for entry in group['tasks']})
        group['task_kind'] = '+'.join(task_kinds)
    return list(grouped.values())


def execute_dispatch_plan(
    *,
    dispatch_plan: list[dict[str, Any]],
    org_id: str,
    app_secret: str,
    transport: Any,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    grouped_dispatches = _group_dispatch_plan(dispatch_plan)
    output_root_path = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    output_root_path.mkdir(parents=True, exist_ok=True)
    execution_results: list[dict[str, Any]] = []
    new_latest_states: list[dict[str, Any]] = []

    for group_index, group in enumerate(grouped_dispatches, start=1):
        slice_id = group['slice_id']
        artifact_root = output_root_path / f'{group_index:02d}-{slice_id}-{group["dispatch_priority"]}'
        if slice_id == 'member_insight':
            start_time, end_time = _business_window(group)
            result = run_member_insight_vertical_slice(
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                requested_business_date=group['target_business_date'],
                app_secret=app_secret,
                transport=transport,
                output_root=artifact_root,
            )
            new_latest_states.extend(result['latest_state_artifacts']['latest_usable_endpoint_states'])
        elif slice_id == 'finance_summary':
            start_time, end_time = _business_window(group)
            result = run_finance_summary_vertical_slice(
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                requested_business_date=group['target_business_date'],
                app_secret=app_secret,
                transport=transport,
                output_root=artifact_root,
            )
            new_latest_states.extend(result['latest_state_artifacts']['latest_usable_endpoint_states'])
        elif slice_id == 'staff_board':
            start_time, end_time = _business_window(group)
            result = run_staff_board_vertical_slice(
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                requested_business_date=group['target_business_date'],
                app_secret=app_secret,
                transport=transport,
                output_root=artifact_root,
            )
            new_latest_states.extend(result['latest_state_artifacts']['latest_usable_endpoint_states'])
        elif slice_id == 'commission_setting':
            result = run_commission_setting_endpoint_sync(
                org_id=org_id,
                requested_business_date=group['target_business_date'],
                app_secret=app_secret,
                transport=transport,
                output_root=artifact_root,
            )
            new_latest_states.append(result['latest_state_artifacts']['latest_usable_endpoint_state'])
        else:
            raise KeyError(f'Unsupported slice_id: {slice_id}')

        execution_results.append({
            'slice_id': slice_id,
            'dispatch_priority': group['dispatch_priority'],
            'task_kind': group['task_kind'],
            'artifact_root': str(artifact_root),
            'result': result,
        })

    return {
        'execution_results': execution_results,
        'new_latest_usable_endpoint_states': new_latest_states,
    }


def run_nightly_sync_runtime_cycle(
    *,
    db_path: str | Path,
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    expected_business_dates: list[str],
    app_secret: str,
    transport: Any | None = None,
    endpoint_contract_ids: list[str] | None = None,
    max_dispatch_tasks: int = 8,
    max_backfill_dispatch_tasks: int | None = None,
    history_start_business_date: str | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    from workflows.nightly_sync_worker import _load_store_module  # local import to keep scripts lean

    resolved_transport = transport or build_live_transport_from_env()
    store_module = _load_store_module()
    store = store_module.NightlySyncCursorLedgerStore(db_path)
    try:
        prior_ledger_entries = store.load_effective_entries(
            source_system_id=source_system_id,
            org_id=org_id,
            as_of_target_business_date=target_business_date,
        )
        cursor_ledger_module = _load_cursor_ledger_module()
        prior_latest_states = cursor_ledger_module.build_latest_usable_states_from_cursor_ledger_entries(
            prior_ledger_entries
        )
        initial_snapshot = build_nightly_sync_scheduler_snapshot(
            source_system_id=source_system_id,
            org_id=org_id,
            target_business_date=target_business_date,
            expected_business_dates=expected_business_dates,
            latest_usable_endpoint_states=prior_latest_states,
            endpoint_contract_ids=endpoint_contract_ids,
            prior_ledger_entries=prior_ledger_entries,
            max_dispatch_tasks=max_dispatch_tasks,
            max_backfill_dispatch_tasks=max_backfill_dispatch_tasks,
            history_start_business_date=history_start_business_date,
        )
        execution = execute_dispatch_plan(
            dispatch_plan=initial_snapshot['dispatch_plan'],
            org_id=org_id,
            app_secret=app_secret,
            transport=resolved_transport,
            output_root=output_root,
        )
        merged_latest_states = [
            *prior_latest_states,
            *execution['new_latest_usable_endpoint_states'],
        ]
        final_snapshot = build_nightly_sync_scheduler_snapshot(
            source_system_id=source_system_id,
            org_id=org_id,
            target_business_date=target_business_date,
            expected_business_dates=expected_business_dates,
            latest_usable_endpoint_states=merged_latest_states,
            endpoint_contract_ids=endpoint_contract_ids,
            prior_ledger_entries=prior_ledger_entries,
            max_dispatch_tasks=max_dispatch_tasks,
            max_backfill_dispatch_tasks=max_backfill_dispatch_tasks,
            history_start_business_date=history_start_business_date,
        )
        store.save_ledger(final_snapshot['cursor_ledger'])
        return {
            'db_path': str(Path(db_path)),
            'initial_snapshot': initial_snapshot,
            'execution': execution,
            'final_snapshot': final_snapshot,
        }
    finally:
        store.close()


__all__ = [
    'build_live_transport_from_env',
    'execute_dispatch_plan',
    'run_nightly_sync_runtime_cycle',
]
