from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.nightly_sync_runtime import run_nightly_sync_runtime_cycle  # noqa: E402


class NightlySyncRuntimeTest(unittest.TestCase):
    @staticmethod
    def _fixture_transport() -> FixtureQinqinTransport:
        fixture_bundle = {}
        fixture_bundle_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        fixture_bundle.update(json.loads(fixture_bundle_path.read_text(encoding='utf-8')))
        finance_fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'finance_summary' / 'qinqin_fixture_pages.bundle.json'
        fixture_bundle.update(json.loads(finance_fixture_path.read_text(encoding='utf-8')))
        staff_fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'staff_board' / 'qinqin_staff_fixture_pages.bundle.json'
        fixture_bundle.update(json.loads(staff_fixture_path.read_text(encoding='utf-8')))
        fixture_bundle['qinqin.staff.get_tech_commission_set_list.v1_8'] = [
            {
                'Code': 404,
                'Msg': '暂无数据',
                'RetData': [],
            }
        ]
        return FixtureQinqinTransport(fixture_bundle)

    def test_runtime_cycle_executes_dispatches_and_persists_final_ledger(self) -> None:
        transport = self._fixture_transport()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_nightly_sync_runtime_cycle(
                db_path=Path(tmpdir) / 'nightly-runtime.sqlite3',
                source_system_id='qinqin.v1_1',
                org_id='demo-org-001',
                target_business_date='2026-04-11',
                expected_business_dates=['2026-04-11'],
                app_secret='test-secret',
                transport=transport,
                endpoint_contract_ids=[
                    'qinqin.member.get_customers_list.v1_1',
                    'qinqin.member.get_consume_bill_list.v1_2',
                    'qinqin.member.get_recharge_bill_list.v1_3',
                    'qinqin.member.get_user_trade_list.v1_4',
                    'qinqin.staff.get_person_list.v1_5',
                    'qinqin.staff.get_tech_up_clock_list.v1_6',
                    'qinqin.staff.get_tech_market_list.v1_7',
                    'qinqin.staff.get_tech_commission_set_list.v1_8',
                ],
                max_dispatch_tasks=8,
                output_root=Path(tmpdir) / 'artifacts',
            )

            self.assertEqual(len(result['initial_snapshot']['dispatch_plan']), 8)
            self.assertEqual(len(result['execution']['execution_results']), 4)
            self.assertEqual(result['final_snapshot']['cursor_ledger']['entry_count'], 8)
            member = next(
                entry
                for entry in result['final_snapshot']['cursor_ledger']['entries']
                if entry['endpoint_contract_id'] == 'qinqin.member.get_consume_bill_list.v1_2'
            )
            self.assertEqual(member['cursor_status'], 'current_and_complete')
            commission = next(
                entry
                for entry in result['final_snapshot']['cursor_ledger']['entries']
                if entry['endpoint_contract_id'] == 'qinqin.staff.get_tech_commission_set_list.v1_8'
            )
            self.assertEqual(commission['cursor_status'], 'current_and_complete')

    def test_runtime_cycle_carries_history_forward_across_target_dates(self) -> None:
        transport = self._fixture_transport()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'nightly-runtime.sqlite3'
            common_kwargs = {
                'db_path': db_path,
                'source_system_id': 'qinqin.v1_1',
                'org_id': 'demo-org-001',
                'app_secret': 'test-secret',
                'transport': transport,
                'endpoint_contract_ids': ['qinqin.staff.get_tech_commission_set_list.v1_8'],
                'max_dispatch_tasks': 1,
                'max_backfill_dispatch_tasks': 1,
                'history_start_business_date': '2026-04-09',
                'output_root': Path(tmpdir) / 'artifacts',
            }

            first_day = run_nightly_sync_runtime_cycle(
                target_business_date='2026-04-11',
                expected_business_dates=[],
                **common_kwargs,
            )
            first_day_entry = first_day['final_snapshot']['cursor_ledger']['entries'][0]
            self.assertEqual(first_day_entry['next_backfill_business_date'], '2026-04-09')

            second_day = run_nightly_sync_runtime_cycle(
                target_business_date='2026-04-12',
                expected_business_dates=[],
                **common_kwargs,
            )
            second_day_entry = second_day['initial_snapshot']['cursor_ledger']['entries'][0]
            self.assertEqual(second_day_entry['next_currentness_business_date'], '2026-04-12')
            self.assertEqual(second_day_entry['next_backfill_business_date'], '2026-04-09')
            self.assertEqual(
                second_day['initial_snapshot']['planner_output']['expected_business_dates'],
                ['2026-04-09', '2026-04-10', '2026-04-11', '2026-04-12'],
            )


if __name__ == '__main__':
    unittest.main()
