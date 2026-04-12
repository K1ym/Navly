from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from tests.support.qinqin_governance_fixture_builder import build_aligned_fixture_pages_by_endpoint, build_aligned_response_bundle  # noqa: E402
from workflows.member_insight_owner_surface import build_member_insight_owner_surface  # noqa: E402
from workflows.qinqin_phase1_owner_surface import (  # noqa: E402
    build_qinqin_phase1_owner_surface,
    query_qinqin_phase1_capability_readiness,
    query_qinqin_phase1_theme_service,
)


class QinqinPhase1OwnerSurfaceTest(unittest.TestCase):
    def _base_query_kwargs(self) -> dict[str, object]:
        return {
            'request_id': 'req_phase1_owner_surface_001',
            'trace_ref': 'navly:trace:phase1-owner-surface-001',
            'target_scope_ref': 'navly:scope:store:demo-org-001',
            'target_business_date': '2026-04-12',
            'org_id': 'demo-org-001',
            'start_time': '2026-04-12 00:00:00',
            'end_time': '2026-04-12 23:59:59',
            'app_secret': 'test-secret',
        }

    def _aligned_transport(self) -> FixtureQinqinTransport:
        return FixtureQinqinTransport(build_aligned_fixture_pages_by_endpoint(value_suffix='phase1'))

    def test_member_insight_surface_remains_authoritative(self) -> None:
        expected = build_member_insight_owner_surface(
            transport=self._aligned_transport(),
            **self._base_query_kwargs(),
        )
        actual = build_qinqin_phase1_owner_surface(
            transport=self._aligned_transport(),
            requested_capability_id='navly.store.member_insight',
            requested_service_object_id='navly.service.store.member_insight',
            **self._base_query_kwargs(),
        )

        self.assertEqual(actual['readiness_response']['readiness_status'], expected['readiness_response']['readiness_status'])
        self.assertEqual(actual['theme_service_response']['service_status'], expected['theme_service_response']['service_status'])
        self.assertEqual(actual['theme_service_response']['service_object'], expected['theme_service_response']['service_object'])

    def test_finance_summary_and_staff_board_surfaces_are_served(self) -> None:
        finance_service = query_qinqin_phase1_theme_service(
            transport=self._aligned_transport(),
            requested_capability_id='navly.store.finance_summary',
            requested_service_object_id='navly.service.store.finance_summary',
            **self._base_query_kwargs(),
        )
        staff_service = query_qinqin_phase1_theme_service(
            transport=self._aligned_transport(),
            requested_capability_id='navly.store.staff_board',
            requested_service_object_id='navly.service.store.staff_board',
            **self._base_query_kwargs(),
        )

        self.assertEqual(finance_service['service_status'], 'served')
        self.assertEqual(finance_service['service_object']['recharge_bill_count'], 1)
        self.assertEqual(finance_service['service_object']['account_trade_count'], 1)
        self.assertEqual(finance_service['service_object']['recharge_total_amount'], 1)

        self.assertEqual(staff_service['service_status'], 'served')
        self.assertEqual(staff_service['service_object']['staff_count'], 1)
        self.assertEqual(staff_service['service_object']['tech_shift_item_count'], 1)
        self.assertEqual(staff_service['service_object']['sales_commission_count'], 1)

    def test_daily_overview_surface_aggregates_child_service_objects(self) -> None:
        readiness = query_qinqin_phase1_capability_readiness(
            transport=self._aligned_transport(),
            requested_capability_id='navly.store.daily_overview',
            **self._base_query_kwargs(),
        )
        service = query_qinqin_phase1_theme_service(
            transport=self._aligned_transport(),
            requested_capability_id='navly.store.daily_overview',
            requested_service_object_id='navly.service.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['service_object']['components']['member_insight']['customer_count'], 1)
        self.assertEqual(service['service_object']['components']['finance_summary']['recharge_total_amount'], 1)
        self.assertEqual(service['service_object']['components']['staff_board']['staff_count'], 1)
        self.assertEqual(service['service_object']['key_metrics']['sales_commission_amount'], 1)

    def test_capability_explanation_surface_is_formal_served_object(self) -> None:
        readiness = query_qinqin_phase1_capability_readiness(
            requested_capability_id='navly.system.capability_explanation',
            explanation_context={
                'explained_capability_id': 'navly.store.finance_summary',
                'explained_service_object_id': 'navly.service.store.finance_summary',
                'reason_codes': ['dependency_failed'],
                'summary_tokens': ['finance_summary', 'dependency_failed'],
                'state_trace_refs': ['navly:state-trace:finance-summary'],
                'run_trace_refs': ['navly:run-trace:finance-summary'],
                'suggested_next_action': 'retry_after_sync',
            },
            **self._base_query_kwargs(),
        )
        service = query_qinqin_phase1_theme_service(
            requested_capability_id='navly.system.capability_explanation',
            requested_service_object_id='navly.service.system.capability_explanation',
            explanation_context={
                'explained_capability_id': 'navly.store.finance_summary',
                'explained_service_object_id': 'navly.service.store.finance_summary',
                'reason_codes': ['dependency_failed'],
                'summary_tokens': ['finance_summary', 'dependency_failed'],
                'state_trace_refs': ['navly:state-trace:finance-summary'],
                'run_trace_refs': ['navly:run-trace:finance-summary'],
                'suggested_next_action': 'retry_after_sync',
            },
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['service_object']['explained_capability_id'], 'navly.store.finance_summary')
        self.assertEqual(service['service_object']['reason_codes'], ['dependency_failed'])
        self.assertEqual(service['service_object']['suggested_next_action'], 'retry_after_sync')

    def test_blocked_finance_dependency_propagates_to_daily_overview(self) -> None:
        bundle = build_aligned_fixture_pages_by_endpoint(value_suffix='blocked')
        bundle['qinqin.member.get_recharge_bill_list.v1_3'] = [{
            'Code': -500,
            'Msg': '验签失败',
            'RetData': {
                'Total': 0,
                'Data': [],
            },
        }]
        transport = FixtureQinqinTransport(bundle)

        finance_readiness = query_qinqin_phase1_capability_readiness(
            transport=transport,
            requested_capability_id='navly.store.finance_summary',
            **self._base_query_kwargs(),
        )
        daily_service = query_qinqin_phase1_theme_service(
            transport=FixtureQinqinTransport(bundle),
            requested_capability_id='navly.store.daily_overview',
            requested_service_object_id='navly.service.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(finance_readiness['readiness_status'], 'failed')
        self.assertEqual(finance_readiness['reason_codes'], ['dependency_failed'])
        self.assertEqual(daily_service['service_status'], 'not_ready')
        self.assertEqual(daily_service['explanation_object']['reason_codes'], ['dependency_failed'])


if __name__ == '__main__':
    unittest.main()
