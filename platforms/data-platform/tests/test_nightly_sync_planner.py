from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from ingestion.nightly_sync_planner import build_nightly_sync_plan


class NightlySyncPlannerTest(unittest.TestCase):
    def test_first_launch_prefers_latest_target_before_historical_backfill(self) -> None:
        plan = build_nightly_sync_plan(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=['2026-04-09', '2026-04-10'],
            latest_usable_endpoint_states=[],
            endpoint_contract_ids=[
                'qinqin.member.get_recharge_bill_list.v1_3',
                'qinqin.staff.get_tech_commission_set_list.v1_8',
                'qinqin.member.get_customers_list.v1_1',
            ],
        )

        currentness_by_endpoint = {
            entry['endpoint_contract_id']: entry
            for entry in plan['currentness_tasks']
        }
        backfill_by_endpoint = {
            entry['endpoint_contract_id']: entry
            for entry in plan['backfill_tasks']
        }

        self.assertEqual(
            currentness_by_endpoint['qinqin.member.get_recharge_bill_list.v1_3']['business_date'],
            '2026-04-11',
        )
        self.assertEqual(
            currentness_by_endpoint['qinqin.staff.get_tech_commission_set_list.v1_8']['business_date'],
            '2026-04-11',
        )
        self.assertEqual(
            currentness_by_endpoint['qinqin.member.get_customers_list.v1_1']['window_start_business_date'],
            '2026-04-05',
        )

        self.assertEqual(
            backfill_by_endpoint['qinqin.member.get_recharge_bill_list.v1_3']['business_date'],
            '2026-04-10',
        )
        self.assertEqual(
            backfill_by_endpoint['qinqin.member.get_recharge_bill_list.v1_3']['remaining_business_dates'],
            ['2026-04-10', '2026-04-09'],
        )
        self.assertEqual(
            backfill_by_endpoint['qinqin.staff.get_tech_commission_set_list.v1_8']['business_date'],
            '2026-04-10',
        )
        self.assertNotIn('qinqin.member.get_customers_list.v1_1', backfill_by_endpoint)

    def test_followup_run_keeps_latest_current_and_continues_older_cursor(self) -> None:
        latest_states = [
            {
                'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                'latest_usable_business_date': '2026-04-11',
            },
            {
                'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                'latest_usable_business_date': '2026-04-10',
            },
            {
                'endpoint_contract_id': 'qinqin.staff.get_tech_commission_set_list.v1_8',
                'latest_usable_business_date': '2026-04-11',
            },
        ]
        plan = build_nightly_sync_plan(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=['2026-04-09', '2026-04-10'],
            latest_usable_endpoint_states=latest_states,
            endpoint_contract_ids=[
                'qinqin.member.get_recharge_bill_list.v1_3',
                'qinqin.staff.get_tech_commission_set_list.v1_8',
            ],
        )

        endpoint_plans = {
            entry['endpoint_contract_id']: entry
            for entry in plan['endpoint_plans']
        }
        currentness_endpoints = {
            entry['endpoint_contract_id']
            for entry in plan['currentness_tasks']
        }
        backfill_by_endpoint = {
            entry['endpoint_contract_id']: entry
            for entry in plan['backfill_tasks']
        }

        self.assertNotIn('qinqin.member.get_recharge_bill_list.v1_3', currentness_endpoints)
        self.assertEqual(
            endpoint_plans['qinqin.member.get_recharge_bill_list.v1_3']['currentness_status'],
            'current',
        )
        self.assertEqual(
            endpoint_plans['qinqin.member.get_recharge_bill_list.v1_3']['recommended_next_backfill_business_date'],
            '2026-04-09',
        )
        self.assertEqual(
            backfill_by_endpoint['qinqin.member.get_recharge_bill_list.v1_3']['remaining_business_dates'],
            ['2026-04-09'],
        )

        self.assertEqual(
            endpoint_plans['qinqin.staff.get_tech_commission_set_list.v1_8']['recommended_next_backfill_business_date'],
            '2026-04-10',
        )
        self.assertEqual(
            backfill_by_endpoint['qinqin.staff.get_tech_commission_set_list.v1_8']['remaining_business_dates'],
            ['2026-04-10', '2026-04-09'],
        )


if __name__ == '__main__':
    unittest.main()
