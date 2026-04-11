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

from workflows.nightly_sync_worker import run_nightly_sync_worker  # noqa: E402


class NightlySyncWorkerTest(unittest.TestCase):
    def test_worker_persists_ledger_and_returns_dispatch_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'nightly-ledger.sqlite3'
            result = run_nightly_sync_worker(
                db_path=db_path,
                source_system_id='qinqin.v1_1',
                org_id='demo-org-001',
                target_business_date='2026-04-11',
                expected_business_dates=['2026-04-09', '2026-04-10'],
                latest_usable_endpoint_states=[],
                endpoint_contract_ids=['qinqin.member.get_recharge_bill_list.v1_3'],
                max_dispatch_tasks=2,
            )

            self.assertEqual(result['loaded_prior_entry_count'], 0)
            self.assertEqual(result['persisted_entry_count'], 1)
            self.assertEqual(
                result['scheduler_snapshot']['dispatch_plan'][0]['dispatch_priority'],
                'currentness',
            )
            self.assertTrue(db_path.exists())

    def test_worker_script_writes_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'worker-output'
            db_path = Path(tmpdir) / 'nightly-ledger.sqlite3'
            subprocess.run(
                [
                    sys.executable,
                    'platforms/data-platform/scripts/run_nightly_sync_worker.py',
                    '--db-path',
                    str(db_path),
                    '--org-id',
                    'demo-org-001',
                    '--target-business-date',
                    '2026-04-11',
                    '--expected-business-date',
                    '2026-04-09',
                    '--expected-business-date',
                    '2026-04-10',
                    '--endpoint-contract-id',
                    'qinqin.member.get_recharge_bill_list.v1_3',
                    '--output-dir',
                    str(output_dir),
                ],
                cwd=DATA_PLATFORM_ROOT.parents[1],
                check=True,
            )

            worker_result = json.loads((output_dir / 'worker-result.json').read_text(encoding='utf-8'))
            dispatch_plan = json.loads((output_dir / 'dispatch-plan.json').read_text(encoding='utf-8'))
            cursor_ledger = json.loads((output_dir / 'cursor-ledger.json').read_text(encoding='utf-8'))

            self.assertEqual(worker_result['persisted_entry_count'], 1)
            self.assertEqual(dispatch_plan[0]['dispatch_priority'], 'currentness')
            self.assertEqual(cursor_ledger['entry_count'], 1)


if __name__ == '__main__':
    unittest.main()
