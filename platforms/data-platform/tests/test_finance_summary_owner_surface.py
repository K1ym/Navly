from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.finance_summary_owner_surface import (  # noqa: E402
    build_finance_summary_owner_surface,
    query_finance_summary_capability_readiness,
    query_finance_summary_theme_service,
)


class FinanceSummaryOwnerSurfaceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'finance_summary' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_query_kwargs(self) -> dict[str, object]:
        return {
            'request_id': 'req_finance_surface_001',
            'trace_ref': 'navly:trace:finance-surface-001',
            'target_scope_ref': 'navly:scope:store:demo-org-001',
            'target_business_date': '2026-03-23',
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'app_secret': 'test-secret',
        }

    def test_owner_surface_returns_ready_and_served_for_finance_summary(self) -> None:
        result = build_finance_summary_owner_surface(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            **self._base_query_kwargs(),
        )

        readiness = result['readiness_response']
        service = result['theme_service_response']

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['service_object']['recharge_bill_count'], 1)
        self.assertEqual(service['service_object']['account_trade_count'], 1)
        self.assertEqual(service['service_object']['recharge_pay_amount_total'], 2000)
        self.assertEqual(service['service_object']['recharge_donate_amount_total'], 200)
        self.assertEqual(service['service_object']['account_trade_change_balance_total'], 2000)
        self.assertTrue(readiness['state_trace_refs'])
        self.assertTrue(readiness['run_trace_refs'])

    def test_owner_surface_reports_failed_readiness_and_not_ready_service(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_user_trade_list.v1_4'] = [
            {
                'Code': -500,
                'Msg': '验签失败',
            }
        ]
        transport = FixtureQinqinTransport(fixture_bundle)

        readiness = query_finance_summary_capability_readiness(
            transport=transport,
            **self._base_query_kwargs(),
        )
        service = query_finance_summary_theme_service(
            transport=transport,
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'failed')
        self.assertEqual(readiness['reason_codes'], ['upstream_error'])
        self.assertEqual(len(readiness['blocking_dependencies']), 1)
        self.assertEqual(
            readiness['blocking_dependencies'][0]['dependency_ref'],
            'qinqin.member.get_user_trade_list.v1_4',
        )
        self.assertEqual(service['service_status'], 'not_ready')
        self.assertEqual(service['service_object'], {})
        self.assertEqual(service['explanation_object']['reason_codes'], ['upstream_error'])

    def test_owner_surface_rejects_non_finance_summary_capability(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        readiness = query_finance_summary_capability_readiness(
            transport=transport,
            requested_capability_id='navly.store.daily_overview',
            **self._base_query_kwargs(),
        )
        service = query_finance_summary_theme_service(
            transport=transport,
            requested_capability_id='navly.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'unsupported_scope')
        self.assertEqual(readiness['reason_codes'], ['capability_scope_not_supported'])
        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['capability_scope_not_supported'])

    def test_owner_surface_rejects_non_finance_summary_service_object(self) -> None:
        service = query_finance_summary_theme_service(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            requested_service_object_id='navly.service.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['projection_not_available'])


if __name__ == '__main__':
    unittest.main()
