from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from serving.persisted_owner_surface_snapshot_store import PersistedOwnerSurfaceSnapshotStore


def _snapshot(*, capability_id: str, service_object_id: str, org_id: str, business_date: str) -> dict:
    return {
        'org_id': org_id,
        'target_scope_ref': f'navly:scope:store:{org_id}',
        'snapshot_business_date': business_date,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'readiness_response': {
            'request_id': f'req::{capability_id}::{business_date}',
            'trace_ref': f'navly:trace:{capability_id}:{business_date}',
            'capability_id': capability_id,
            'readiness_status': 'ready',
            'evaluated_scope_ref': f'navly:scope:store:{org_id}',
            'requested_business_date': business_date,
            'latest_usable_business_date': business_date,
            'reason_codes': [],
            'blocking_dependencies': [],
            'state_trace_refs': [f'navly:state-trace:{capability_id}:{business_date}'],
            'run_trace_refs': [f'navly:run-trace:{capability_id}:{business_date}'],
            'evaluated_at': '2026-04-13T00:00:00Z',
        },
        'theme_service_response': {
            'request_id': f'req::{capability_id}::{business_date}',
            'trace_ref': f'navly:trace:{capability_id}:{business_date}',
            'capability_id': capability_id,
            'service_object_id': service_object_id,
            'service_status': 'served',
            'service_object': {
                'capability_id': capability_id,
                'service_object_id': service_object_id,
                'target_scope_ref': f'navly:scope:store:{org_id}',
                'target_business_date': business_date,
                'latest_usable_business_date': business_date,
            },
            'data_window': {
                'from': business_date,
                'to': business_date,
            },
            'state_trace_refs': [f'navly:state-trace:{capability_id}:{business_date}'],
            'run_trace_refs': [f'navly:run-trace:{capability_id}:{business_date}'],
            'served_at': '2026-04-13T00:00:00Z',
        },
    }


class PersistedOwnerSurfaceSnapshotStoreTest(unittest.TestCase):
    def test_store_saves_and_loads_latest_usable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PersistedOwnerSurfaceSnapshotStore(Path(tmpdir))
            store.save_snapshot(_snapshot(
                capability_id='navly.store.member_insight',
                service_object_id='navly.service.store.member_insight',
                org_id='demo-org-001',
                business_date='2026-04-11',
            ))
            store.save_snapshot(_snapshot(
                capability_id='navly.store.member_insight',
                service_object_id='navly.service.store.member_insight',
                org_id='demo-org-001',
                business_date='2026-04-12',
            ))

            latest_snapshot = store.load_snapshot(
                org_id='demo-org-001',
                capability_id='navly.store.member_insight',
                target_business_date='2026-04-13',
            )
            strict_snapshot = store.load_snapshot(
                org_id='demo-org-001',
                capability_id='navly.store.member_insight',
                target_business_date='2026-04-13',
                freshness_mode='strict_date',
            )

        self.assertIsNotNone(latest_snapshot)
        self.assertEqual(latest_snapshot['snapshot_business_date'], '2026-04-12')
        self.assertIsNone(strict_snapshot)


if __name__ == '__main__':
    unittest.main()
