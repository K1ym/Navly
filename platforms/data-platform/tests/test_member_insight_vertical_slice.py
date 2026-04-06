from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT / 'ingestion') not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT / 'ingestion'))
if str(DATA_PLATFORM_ROOT / 'connectors' / 'qinqin') not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT / 'connectors' / 'qinqin'))

from member_insight_vertical_slice import run_member_insight_vertical_slice  # type: ignore  # noqa: E402
from qinqin_substrate import FixtureQinqinTransport, build_signed_request  # type: ignore  # noqa: E402


class MemberInsightVerticalSliceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def test_qinqin_substrate_uses_registry_preferred_wire_names(self) -> None:
        request = build_signed_request(
            endpoint_contract_id='qinqin.member.get_customers_list.v1_1',
            org_id='627149864218629',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            page_index=1,
            page_size=20,
            app_secret='test-secret',
        )
        self.assertEqual(sorted(request['payload'].keys()), sorted(['OrgId', 'Stime', 'Etime', 'PageIndex', 'PageSize', 'Sign']))
        self.assertTrue(request['payload']['Sign'])

    def test_vertical_slice_separates_historical_run_truth_and_latest_state(self) -> None:
        fixture_bundle = self._fixture_bundle()
        transport = FixtureQinqinTransport(fixture_bundle)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_member_insight_vertical_slice(
                org_id='627149864218629',
                start_time='2026-03-20 09:00:00',
                end_time='2026-03-24 09:00:00',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=transport,
                output_root=tmpdir,
            )
            self.assertEqual(result['capability_id'], 'navly.store.member_insight')
            self.assertEqual(result['service_object_id'], 'navly.service.store.member_insight')
            self.assertEqual(len(result['historical_run_truth']['endpoint_runs']), 2)
            self.assertEqual(len(result['raw_replay']['raw_response_pages']), 2)
            self.assertEqual(len(result['canonical_artifacts']['customer']), 1)
            self.assertEqual(len(result['canonical_artifacts']['consume_bill']), 1)
            self.assertEqual(len(result['canonical_artifacts']['consume_bill_payment']), 1)
            self.assertEqual(len(result['latest_state_artifacts']['latest_usable_endpoint_states']), 2)
            self.assertEqual(
                result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
                'backbone_ready',
            )
            self.assertTrue(Path(tmpdir, 'historical-run-truth', 'ingestion-runs.json').exists())
            self.assertTrue(Path(tmpdir, 'latest-state', 'latest-usable-endpoint-state.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'customer.json').exists())

    def test_cli_runner_writes_artifact_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_member_insight_vertical_slice.py'
            fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', '627149864218629',
                    '--start-time', '2026-03-20 09:00:00',
                    '--end-time', '2026-03-24 09:00:00',
                    '--requested-business-date', '2026-03-23',
                    '--app-secret', 'test-secret',
                    '--fixtures', str(fixture_path),
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload['capability_id'], 'navly.store.member_insight')
            self.assertTrue(Path(tmpdir, 'raw-replay', 'raw-response-pages.json').exists())


if __name__ == '__main__':
    unittest.main()
