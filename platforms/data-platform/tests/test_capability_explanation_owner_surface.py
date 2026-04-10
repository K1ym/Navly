from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.capability_explanation_owner_surface import query_capability_explanation_service  # noqa: E402


class CapabilityExplanationOwnerSurfaceTest(unittest.TestCase):
    def _finance_fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'finance_summary' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_query_kwargs(self) -> dict[str, object]:
        return {
            'request_id': 'req_explanation_surface_001',
            'trace_ref': 'navly:trace:explanation-surface-001',
            'target_scope_ref': 'navly:scope:store:demo-org-001',
            'target_business_date': '2026-03-23',
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'app_secret': 'test-secret',
        }

    def test_explanation_service_serves_ready_capability_summary(self) -> None:
        result = query_capability_explanation_service(
            transport=FixtureQinqinTransport(self._finance_fixture_bundle()),
            requested_capability_id='navly.store.finance_summary',
            **self._base_query_kwargs(),
        )

        self.assertEqual(result['service_status'], 'served')
        self.assertEqual(result['service_object']['readiness_status'], 'ready')
        self.assertEqual(result['service_object']['theme_service_status'], 'served')
        self.assertEqual(result['service_object']['recommended_fallback_action'], 'consume_theme_service')
        self.assertEqual(result['service_object']['next_recheck_hint'], 'recheck_not_required')

    def test_explanation_service_reports_failed_capability_summary(self) -> None:
        fixture_bundle = self._finance_fixture_bundle()
        fixture_bundle['qinqin.member.get_user_trade_list.v1_4'] = [
            {
                'Code': -500,
                'Msg': '验签失败',
            }
        ]
        result = query_capability_explanation_service(
            transport=FixtureQinqinTransport(fixture_bundle),
            requested_capability_id='navly.store.finance_summary',
            **self._base_query_kwargs(),
        )

        self.assertEqual(result['service_status'], 'served')
        self.assertEqual(result['service_object']['readiness_status'], 'failed')
        self.assertEqual(result['service_object']['reason_codes'], ['upstream_error'])
        self.assertEqual(
            result['service_object']['recommended_fallback_action'],
            'retry_after_upstream_recovery',
        )
        self.assertEqual(result['explanation_object']['reason_codes'], ['upstream_error'])

    def test_explanation_service_handles_unsupported_capability(self) -> None:
        result = query_capability_explanation_service(
            transport=FixtureQinqinTransport(self._finance_fixture_bundle()),
            requested_capability_id='navly.store.unknown_capability',
            **self._base_query_kwargs(),
        )

        self.assertEqual(result['service_status'], 'served')
        self.assertEqual(result['service_object']['readiness_status'], 'unsupported_scope')
        self.assertEqual(result['service_object']['reason_codes'], ['capability_scope_not_supported'])
        self.assertEqual(
            result['service_object']['recommended_fallback_action'],
            'adjust_requested_capability_or_scope',
        )


if __name__ == '__main__':
    unittest.main()
