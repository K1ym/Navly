from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from backbone_support.member_insight_canonical_backbone import build_member_insight_canonical_artifacts  # noqa: E402
from warehouse.commission_setting_canonical import build_commission_setting_canonical_artifacts  # noqa: E402
from warehouse.finance_summary_canonical import build_finance_summary_canonical_artifacts  # noqa: E402
from warehouse.staff_workforce_canonical_backbone import build_staff_workforce_canonical_artifacts  # noqa: E402


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


class StructuredTargetCanonicalLandingTest(unittest.TestCase):
    def test_all_manifest_structured_targets_have_canonical_writer_outputs(self) -> None:
        endpoint_contracts = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'endpoint-contracts.seed.json')
        manifest_targets = sorted(
            {
                target
                for entry in endpoint_contracts['entries']
                if entry['domain'] != 'shared'
                for target in entry['structured_targets']
            }
        )

        actual_targets = sorted({
            *build_member_insight_canonical_artifacts({}, org_id='demo-org-001', requested_business_date='2026-04-11').keys(),
            *build_finance_summary_canonical_artifacts(
                raw_pages_by_endpoint={},
                org_id='demo-org-001',
                requested_business_date='2026-04-11',
            ).keys(),
            *build_staff_workforce_canonical_artifacts(
                raw_pages_by_endpoint={},
                org_id='demo-org-001',
                requested_business_date='2026-04-11',
                requested_staff_code=None,
                window_start_at='2026-04-11 03:00:00',
                window_end_at='2026-04-11 04:00:00',
            ).keys(),
            *build_commission_setting_canonical_artifacts(
                [],
                org_id='demo-org-001',
                requested_business_date='2026-04-11',
            ).keys(),
        })

        self.assertEqual(actual_targets, manifest_targets)


if __name__ == '__main__':
    unittest.main()
