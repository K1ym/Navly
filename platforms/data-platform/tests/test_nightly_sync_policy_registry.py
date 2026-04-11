from __future__ import annotations

import json
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == '__main__':
    unittest.main()
