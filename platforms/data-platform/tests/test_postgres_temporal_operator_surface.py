from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.postgres_temporal_operator_surface import (  # noqa: E402
    SYNC_BACKFILL_CAPABILITY_ID,
    SYNC_BACKFILL_SERVICE_OBJECT_ID,
    run_operator_surface,
)


class PostgresTemporalOperatorSurfaceTest(unittest.TestCase):
    def test_sync_backfill_defaults_to_governed_full_history_window(self) -> None:
        fixture_bundle_path = (
            DATA_PLATFORM_ROOT
            / 'tests'
            / 'fixtures'
            / 'member_insight'
            / 'qinqin_fixture_pages.bundle.json'
        )
        transport = FixtureQinqinTransport(
            json.loads(fixture_bundle_path.read_text(encoding='utf-8')),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir) / 'state-snapshot.json'
            with patch.dict('os.environ', {'QINQIN_HISTORY_START_BUSINESS_DATE': '2026-04-09'}, clear=False):
                result = run_operator_surface(
                    request_id='req-ops-backfill-auto-001',
                    trace_ref='navly:trace:req-ops-backfill-auto-001',
                    target_scope_ref='navly:scope:store:demo-org-001',
                    target_business_date='2026-04-11',
                    capability_id=SYNC_BACKFILL_CAPABILITY_ID,
                    service_object_id=SYNC_BACKFILL_SERVICE_OBJECT_ID,
                    org_id='demo-org-001',
                    state_snapshot_path=str(snapshot_path),
                    transport=transport,
                    app_secret='test-secret',
                )

        service_object = result['theme_service_response']['service_object']
        self.assertEqual(service_object['requested_window']['from'], '2026-04-09')
        self.assertEqual(service_object['requested_window']['to'], '2026-04-11')
        self.assertEqual(
            service_object['action_parameters'],
            {
                'backfill_from': '2026-04-09',
                'backfill_to': '2026-04-11',
            },
        )
        self.assertEqual(
            service_object['action_result']['requested_business_dates'],
            ['2026-04-11', '2026-04-10', '2026-04-09'],
        )


if __name__ == '__main__':
    unittest.main()
