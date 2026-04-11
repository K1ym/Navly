from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.nightly_sync_temporal_worker import (  # noqa: E402
    TEMPORAL_ACTIVITY_NAME,
    TEMPORAL_WORKFLOW_NAME,
    build_nightly_sync_temporal_spec,
)


class NightlySyncTemporalWorkerTest(unittest.TestCase):
    def test_temporal_spec_freezes_task_queue_and_names(self) -> None:
        spec = build_nightly_sync_temporal_spec(task_queue='navly-nightly-sync')
        self.assertEqual(spec.task_queue, 'navly-nightly-sync')
        self.assertEqual(spec.workflow_name, TEMPORAL_WORKFLOW_NAME)
        self.assertEqual(spec.activity_name, TEMPORAL_ACTIVITY_NAME)


if __name__ == '__main__':
    unittest.main()
