from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.daily_overview_owner_surface import (  # noqa: E402
    build_daily_overview_owner_surface,
    query_daily_overview_capability_readiness,
    query_daily_overview_theme_service,
)


class DailyOverviewOwnerSurfaceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        bundle: dict = {}
        for relative_path in (
            'tests/fixtures/member_insight/qinqin_fixture_pages.bundle.json',
            'tests/fixtures/staff_board/qinqin_staff_fixture_pages.bundle.json',
            'tests/fixtures/finance_summary/qinqin_fixture_pages.bundle.json',
        ):
            bundle.update(
                json.loads((DATA_PLATFORM_ROOT / relative_path).read_text(encoding='utf-8'))
            )
        return bundle

    def _base_query_kwargs(self) -> dict[str, object]:
        return {
            'request_id': 'req_daily_overview_surface_001',
            'trace_ref': 'navly:trace:daily-overview-surface-001',
            'target_scope_ref': 'navly:scope:store:demo-org-001',
            'target_business_date': '2026-03-23',
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'app_secret': 'test-secret',
        }

    def test_owner_surface_returns_ready_and_served_for_daily_overview(self) -> None:
        result = build_daily_overview_owner_surface(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            **self._base_query_kwargs(),
        )

        readiness = result['readiness_response']
        service = result['theme_service_response']

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(
            service['service_object']['business_day_boundary_policy']['business_day_boundary_local_time'],
            '03:00:00',
        )
        self.assertEqual(
            service['service_object']['business_day_boundary_policy']['timezone'],
            'Asia/Shanghai',
        )
        self.assertEqual(
            service['service_object']['published_service_object_ids'],
            [
                'navly.service.store.member_insight',
                'navly.service.store.staff_board',
                'navly.service.store.finance_summary',
            ],
        )
        self.assertEqual(service['service_object']['member_insight']['customer_count'], 1)
        self.assertEqual(service['service_object']['staff_board']['staff_count'], 2)
        self.assertEqual(service['service_object']['finance_summary']['account_trade_count'], 1)

    def test_owner_surface_reports_child_failure_for_daily_overview(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_user_trade_list.v1_4'] = [
            {
                'Code': -401,
                'Msg': '未授权访问',
            }
        ]
        transport = FixtureQinqinTransport(fixture_bundle)

        readiness = query_daily_overview_capability_readiness(
            transport=transport,
            **self._base_query_kwargs(),
        )
        service = query_daily_overview_theme_service(
            transport=transport,
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'failed')
        self.assertEqual(readiness['reason_codes'], ['upstream_error'])
        self.assertEqual(len(readiness['blocking_dependencies']), 1)
        self.assertEqual(
            readiness['blocking_dependencies'][0]['dependency_ref'],
            'navly.service.store.finance_summary',
        )
        self.assertEqual(service['service_status'], 'not_ready')
        self.assertEqual(service['explanation_object']['reason_codes'], ['upstream_error'])

    def test_owner_surface_rejects_non_daily_overview_capability(self) -> None:
        readiness = query_daily_overview_capability_readiness(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            requested_capability_id='navly.store.finance_summary',
            **self._base_query_kwargs(),
        )
        service = query_daily_overview_theme_service(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            requested_capability_id='navly.store.finance_summary',
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'unsupported_scope')
        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['capability_scope_not_supported'])

    def test_owner_surface_rejects_non_daily_overview_service_object(self) -> None:
        service = query_daily_overview_theme_service(
            transport=FixtureQinqinTransport(self._fixture_bundle()),
            requested_service_object_id='navly.service.store.member_insight',
            **self._base_query_kwargs(),
        )

        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['projection_not_available'])


if __name__ == '__main__':
    unittest.main()
