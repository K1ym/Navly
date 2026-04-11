from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from ingestion.nightly_sync_planner import build_nightly_sync_plan


def _load_cursor_state_module():
    module_path = DATA_PLATFORM_ROOT / 'sync-state' / 'nightly_sync_cursor_state.py'
    spec = importlib.util.spec_from_file_location(
        'navly_data_platform_sync_state_nightly_sync_cursor_state_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load sync-state module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NightlySyncCursorStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cursor_state_module = _load_cursor_state_module()

    def test_first_launch_cursor_marks_currentness_and_backfill_pending(self) -> None:
        plan = build_nightly_sync_plan(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=['2026-04-09', '2026-04-10'],
            latest_usable_endpoint_states=[],
            endpoint_contract_ids=[
                'qinqin.member.get_recharge_bill_list.v1_3',
                'qinqin.member.get_customers_list.v1_1',
            ],
        )
        cursor_states = {
            state['endpoint_contract_id']: state
            for state in self.cursor_state_module.build_nightly_sync_cursor_states(plan)
        }

        recharge = cursor_states['qinqin.member.get_recharge_bill_list.v1_3']
        self.assertEqual(recharge['cursor_status'], 'currentness_pending')
        self.assertEqual(recharge['next_currentness_business_date'], '2026-04-11')
        self.assertEqual(recharge['next_backfill_business_date'], '2026-04-10')
        self.assertEqual(
            recharge['cursor_reason_codes'],
            ['target_business_date_not_current', 'historical_backfill_gap'],
        )

        profile_refresh = cursor_states['qinqin.member.get_customers_list.v1_1']
        self.assertEqual(profile_refresh['cursor_status'], 'currentness_pending')
        self.assertEqual(profile_refresh['next_currentness_business_date'], '2026-04-11')
        self.assertIsNone(profile_refresh['next_backfill_business_date'])
        self.assertEqual(
            profile_refresh['currentness_window_business_dates'],
            [
                '2026-04-05',
                '2026-04-06',
                '2026-04-07',
                '2026-04-08',
                '2026-04-09',
                '2026-04-10',
                '2026-04-11',
            ],
        )

    def test_followup_cursor_only_points_to_remaining_backfill_gap(self) -> None:
        latest_states = [
            {
                'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                'latest_usable_business_date': '2026-04-11',
            },
            {
                'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                'latest_usable_business_date': '2026-04-10',
            },
        ]
        plan = build_nightly_sync_plan(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=['2026-04-09', '2026-04-10'],
            latest_usable_endpoint_states=latest_states,
            endpoint_contract_ids=['qinqin.member.get_recharge_bill_list.v1_3'],
        )
        recharge = self.cursor_state_module.build_nightly_sync_cursor_states(plan)[0]

        self.assertEqual(recharge['currentness_status'], 'current')
        self.assertEqual(recharge['backfill_progress_status'], 'incomplete')
        self.assertEqual(recharge['cursor_status'], 'backfill_pending')
        self.assertIsNone(recharge['next_currentness_business_date'])
        self.assertEqual(recharge['next_backfill_business_date'], '2026-04-09')
        self.assertEqual(recharge['cursor_reason_codes'], ['historical_backfill_gap'])


if __name__ == '__main__':
    unittest.main()
