from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_store_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'nightly_sync_cursor_ledger_store.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_nightly_sync_cursor_ledger_store_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NightlySyncCursorLedgerStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store_module = _load_store_module()

    def test_store_round_trips_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'nightly-ledger.sqlite3'
            store = self.store_module.NightlySyncCursorLedgerStore(db_path)
            try:
                ledger = {
                    'source_system_id': 'qinqin.v1_1',
                    'org_id': 'demo-org-001',
                    'target_business_date': '2026-04-11',
                    'entry_count': 1,
                    'entries': [
                        {
                            'ledger_entry_id': 'ledger_001',
                            'ledger_trace_ref': 'navly:state-trace:ledger:001',
                            'source_system_id': 'qinqin.v1_1',
                            'org_id': 'demo-org-001',
                            'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                            'target_business_date': '2026-04-11',
                            'cursor_status': 'backfill_pending',
                            'last_completed_business_date': '2026-04-11',
                            'last_attempted_business_date': '2026-04-10',
                            'next_currentness_business_date': None,
                            'next_backfill_business_date': '2026-04-10',
                            'covered_business_dates': ['2026-04-11'],
                            'pending_business_dates': ['2026-04-10'],
                            'carry_forward_cursor': True,
                            'backfill_fill_direction': 'latest_to_oldest',
                            'updated_at': '2026-04-11T14:00:00Z',
                        }
                    ],
                }
                store.save_ledger(ledger)
                loaded = store.load_entries(
                    source_system_id='qinqin.v1_1',
                    org_id='demo-org-001',
                    target_business_date='2026-04-11',
                )
            finally:
                store.close()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]['endpoint_contract_id'], 'qinqin.member.get_recharge_bill_list.v1_3')
            self.assertEqual(loaded[0]['pending_business_dates'], ['2026-04-10'])
            self.assertTrue(db_path.exists())


if __name__ == '__main__':
    unittest.main()
