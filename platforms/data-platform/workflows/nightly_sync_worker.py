from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from workflows.nightly_sync_scheduler import build_nightly_sync_scheduler_snapshot

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_store_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'nightly_sync_cursor_ledger_store.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_nightly_sync_cursor_ledger_store',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_nightly_sync_worker(
    *,
    db_path: str | Path,
    source_system_id: str,
    org_id: str,
    target_business_date: str,
    expected_business_dates: list[str],
    latest_usable_endpoint_states: list[dict[str, Any]] | None = None,
    endpoint_contract_ids: list[str] | None = None,
    max_dispatch_tasks: int = 8,
) -> dict[str, Any]:
    store_module = _load_store_module()
    store = store_module.NightlySyncCursorLedgerStore(db_path)
    try:
        prior_ledger_entries = store.load_entries(
            source_system_id=source_system_id,
            org_id=org_id,
            target_business_date=target_business_date,
        )
        snapshot = build_nightly_sync_scheduler_snapshot(
            source_system_id=source_system_id,
            org_id=org_id,
            target_business_date=target_business_date,
            expected_business_dates=expected_business_dates,
            latest_usable_endpoint_states=latest_usable_endpoint_states,
            endpoint_contract_ids=endpoint_contract_ids,
            prior_ledger_entries=prior_ledger_entries,
            max_dispatch_tasks=max_dispatch_tasks,
        )
        store.save_ledger(snapshot['cursor_ledger'])
        return {
            'db_path': str(Path(db_path)),
            'loaded_prior_entry_count': len(prior_ledger_entries),
            'persisted_entry_count': snapshot['cursor_ledger']['entry_count'],
            'scheduler_snapshot': snapshot,
        }
    finally:
        store.close()


__all__ = ['run_nightly_sync_worker']
