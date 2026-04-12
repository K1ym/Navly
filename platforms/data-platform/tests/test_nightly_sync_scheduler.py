from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.nightly_sync_scheduler import build_nightly_sync_scheduler_snapshot  # noqa: E402


class NightlySyncSchedulerTest(unittest.TestCase):
    def test_scheduler_dispatch_prioritizes_currentness_before_backfill_under_budget(self) -> None:
        snapshot = build_nightly_sync_scheduler_snapshot(
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
            max_dispatch_tasks=2,
        )

        dispatch_plan = snapshot['dispatch_plan']
        self.assertEqual(len(dispatch_plan), 2)
        self.assertEqual(
            [entry['dispatch_priority'] for entry in dispatch_plan],
            ['currentness', 'currentness'],
        )
        self.assertEqual(snapshot['deferred_currentness_tasks'], 1)
        self.assertGreaterEqual(snapshot['deferred_backfill_tasks'], 1)

    def test_scheduler_dispatches_backfill_when_extra_backfill_budget_is_provided(self) -> None:
        snapshot = build_nightly_sync_scheduler_snapshot(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=['2026-04-09', '2026-04-10'],
            latest_usable_endpoint_states=[],
            endpoint_contract_ids=[
                'qinqin.member.get_recharge_bill_list.v1_3',
                'qinqin.staff.get_tech_commission_set_list.v1_8',
            ],
            max_dispatch_tasks=2,
            max_backfill_dispatch_tasks=2,
        )

        self.assertEqual(
            [entry['dispatch_priority'] for entry in snapshot['dispatch_plan']],
            ['currentness', 'currentness', 'backfill', 'backfill'],
        )
        self.assertEqual(snapshot['deferred_currentness_tasks'], 0)
        self.assertEqual(snapshot['deferred_backfill_tasks'], 0)

    def test_scheduler_history_start_business_date_expands_expected_window(self) -> None:
        snapshot = build_nightly_sync_scheduler_snapshot(
            source_system_id='qinqin.v1_1',
            org_id='demo-org-001',
            target_business_date='2026-04-11',
            expected_business_dates=[],
            history_start_business_date='2026-04-09',
            latest_usable_endpoint_states=[],
            endpoint_contract_ids=['qinqin.member.get_recharge_bill_list.v1_3'],
            max_dispatch_tasks=1,
        )

        self.assertEqual(
            snapshot['planner_output']['expected_business_dates'],
            ['2026-04-09', '2026-04-10', '2026-04-11'],
        )

    def test_scheduler_script_writes_snapshot_dispatch_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            latest_states_path = Path(tmpdir) / 'latest-states.json'
            latest_states_path.write_text(
                json.dumps(
                    [
                        {
                            'endpoint_contract_id': 'qinqin.member.get_recharge_bill_list.v1_3',
                            'latest_usable_business_date': '2026-04-11',
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding='utf-8',
            )
            output_dir = Path(tmpdir) / 'scheduler-output'
            subprocess.run(
                [
                    sys.executable,
                    'platforms/data-platform/scripts/run_nightly_sync_scheduler.py',
                    '--org-id',
                    'demo-org-001',
                    '--target-business-date',
                    '2026-04-11',
                    '--expected-business-date',
                    '2026-04-09',
                    '--expected-business-date',
                    '2026-04-10',
                    '--latest-usable-states-json',
                    str(latest_states_path),
                    '--endpoint-contract-id',
                    'qinqin.member.get_recharge_bill_list.v1_3',
                    '--output-dir',
                    str(output_dir),
                ],
                cwd=DATA_PLATFORM_ROOT.parents[1],
                check=True,
            )

            snapshot = json.loads((output_dir / 'scheduler-snapshot.json').read_text(encoding='utf-8'))
            ledger = json.loads((output_dir / 'cursor-ledger.json').read_text(encoding='utf-8'))
            dispatch_plan = json.loads((output_dir / 'dispatch-plan.json').read_text(encoding='utf-8'))

            self.assertEqual(snapshot['source_system_id'], 'qinqin.v1_1')
            self.assertEqual(ledger['entry_count'], 1)
            self.assertEqual(ledger['entries'][0]['next_backfill_business_date'], '2026-04-10')
            self.assertEqual(dispatch_plan[0]['dispatch_priority'], 'backfill')


if __name__ == '__main__':
    unittest.main()
