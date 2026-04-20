from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from directory.nightly_sync_policy_registry import (  # noqa: E402
    resolve_nightly_sync_endpoint_fetch_concurrency,
    resolve_nightly_sync_history_start_business_date,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


class NightlySyncPolicyRegistryTest(unittest.TestCase):
    def test_contract_ownership_includes_nightly_sync_policy_entry(self) -> None:
        ownership = _load_json(DATA_PLATFORM_ROOT / 'contracts' / 'contract-ownership.seed.json')
        self.assertIn(
            'nightly_sync_policy_entry',
            ownership['data_platform_owned_contracts'],
        )

    def test_registry_freezes_qinqin_nightly_currentness_and_backfill_policy(self) -> None:
        registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'nightly-sync-policy.seed.json')
        self.assertEqual(registry['registry_name'], 'nightly_sync_policy_registry')
        self.assertEqual(registry['status'], 'phase_1_policy_frozen')
        self.assertEqual(len(registry['entries']), 1)

        entry = registry['entries'][0]
        self.assertEqual(entry['source_system_id'], 'qinqin.v1_1')
        self.assertEqual(entry['timezone'], 'Asia/Shanghai')
        self.assertEqual(entry['activation_local_time'], '03:10')
        self.assertEqual(entry['formal_access_window_start_local_time'], '03:00')
        self.assertEqual(entry['formal_access_window_end_exclusive_local_time'], '04:00')
        self.assertEqual(entry['currentness_priority'], 'target_business_date_first')
        self.assertEqual(entry['backfill_fill_direction'], 'latest_to_oldest')
        self.assertTrue(entry['carry_forward_cursor'])
        self.assertEqual(entry['default_page_size'], 200)
        self.assertIsNone(entry['default_history_start_business_date'])
        self.assertEqual(
            entry['runtime_history_start_business_date_env_var'],
            'QINQIN_HISTORY_START_BUSINESS_DATE',
        )
        self.assertTrue(entry['operator_backfill_defaults_to_full_history'])
        self.assertEqual(entry['max_concurrent_endpoint_fetches'], 3)
        self.assertEqual(
            entry['runtime_max_concurrent_endpoint_fetches_env_var'],
            'NAVLY_QINQIN_MAX_CONCURRENT_ENDPOINT_FETCHES',
        )

        strategy_policies = entry['increment_strategy_policies']
        self.assertEqual(
            set(strategy_policies),
            {
                'business_window_incremental',
                'daily_full_replace',
                'profile_refresh_windowed',
            },
        )
        self.assertTrue(strategy_policies['business_window_incremental']['allow_historical_backfill'])
        self.assertTrue(strategy_policies['daily_full_replace']['allow_historical_backfill'])
        self.assertFalse(strategy_policies['profile_refresh_windowed']['allow_historical_backfill'])
        self.assertEqual(
            strategy_policies['profile_refresh_windowed']['currentness_window_business_days'],
            7,
        )

    def test_history_start_resolution_prefers_explicit_then_env(self) -> None:
        self.assertEqual(
            resolve_nightly_sync_history_start_business_date(
                'qinqin.v1_1',
                explicit_history_start_business_date='2026-03-01',
                environ={'QINQIN_HISTORY_START_BUSINESS_DATE': '2026-02-01'},
            ),
            '2026-03-01',
        )
        self.assertEqual(
            resolve_nightly_sync_history_start_business_date(
                'qinqin.v1_1',
                environ={'QINQIN_HISTORY_START_BUSINESS_DATE': '2026-02-01'},
            ),
            '2026-02-01',
        )

    def test_endpoint_fetch_concurrency_prefers_request_then_env_then_policy(self) -> None:
        self.assertEqual(
            resolve_nightly_sync_endpoint_fetch_concurrency(
                'qinqin.v1_1',
                requested_max_concurrent_endpoint_fetches=6,
                environ={'NAVLY_QINQIN_MAX_CONCURRENT_ENDPOINT_FETCHES': '5'},
            ),
            6,
        )
        self.assertEqual(
            resolve_nightly_sync_endpoint_fetch_concurrency(
                'qinqin.v1_1',
                environ={'NAVLY_QINQIN_MAX_CONCURRENT_ENDPOINT_FETCHES': '5'},
            ),
            5,
        )
        self.assertEqual(
            resolve_nightly_sync_endpoint_fetch_concurrency('qinqin.v1_1', environ={}),
            3,
        )


if __name__ == '__main__':
    unittest.main()
