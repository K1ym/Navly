from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from completeness.member_insight_readiness_surface import build_member_insight_readiness_response  # noqa: E402
from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.member_insight_owner_surface import (  # noqa: E402
    build_member_insight_owner_surface,
    query_member_insight_capability_readiness,
    query_member_insight_theme_service,
)


class MemberInsightOwnerSurfaceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_query_kwargs(self) -> dict[str, object]:
        return {
            'request_id': 'req_owner_surface_001',
            'trace_ref': 'navly:trace:owner-surface-001',
            'target_scope_ref': 'navly:scope:store:demo-org-001',
            'target_business_date': '2026-03-23',
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'app_secret': 'test-secret',
        }

    def test_owner_surface_returns_ready_and_served_for_member_insight(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        result = build_member_insight_owner_surface(
            transport=transport,
            **self._base_query_kwargs(),
        )

        readiness = result['readiness_response']
        service = result['theme_service_response']

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['service_object']['customer_count'], 1)
        self.assertEqual(service['service_object']['customer_ticket_count'], 0)
        self.assertEqual(service['service_object']['customer_coupon_count'], 0)
        self.assertEqual(service['service_object']['consume_bill_count'], 1)
        self.assertTrue(readiness['state_trace_refs'])
        self.assertTrue(readiness['run_trace_refs'])
        self.assertEqual(service['state_trace_refs'], readiness['state_trace_refs'])
        self.assertEqual(service['run_trace_refs'], readiness['run_trace_refs'])

    def test_owner_surface_reports_failed_readiness_and_not_ready_service(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_consume_bill_list.v1_2'] = [
            {
                'Code': -500,
                'Msg': '验签失败',
                'RetData': {
                    'Total': 0,
                    'Data': [],
                },
            }
        ]
        transport = FixtureQinqinTransport(fixture_bundle)

        readiness = query_member_insight_capability_readiness(
            transport=transport,
            **self._base_query_kwargs(),
        )
        service = query_member_insight_theme_service(
            transport=transport,
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'failed')
        self.assertEqual(readiness['reason_codes'], ['dependency_failed'])
        self.assertEqual(len(readiness['blocking_dependencies']), 1)
        self.assertEqual(
            readiness['blocking_dependencies'][0]['dependency_ref'],
            'qinqin.member.get_consume_bill_list.v1_2',
        )
        self.assertEqual(
            readiness['blocking_dependencies'][0]['blocking_reason_code'],
            'dependency_failed',
        )
        self.assertEqual(service['service_status'], 'not_ready')
        self.assertEqual(service['service_object'], {})
        self.assertEqual(service['explanation_object']['reason_codes'], ['dependency_failed'])

    def test_owner_surface_rejects_non_member_insight_capability(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        readiness = query_member_insight_capability_readiness(
            transport=transport,
            requested_capability_id='navly.store.daily_overview',
            **self._base_query_kwargs(),
        )
        service = query_member_insight_theme_service(
            transport=transport,
            requested_capability_id='navly.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(readiness['readiness_status'], 'unsupported_scope')
        self.assertEqual(readiness['reason_codes'], ['capability_not_registered'])
        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['service_object'], {})
        self.assertEqual(
            service['explanation_object']['capability_id'],
            'navly.store.daily_overview',
        )

    def test_owner_surface_rejects_non_member_insight_service_object(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        service = query_member_insight_theme_service(
            transport=transport,
            requested_service_object_id='navly.service.store.daily_overview',
            **self._base_query_kwargs(),
        )

        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['scope_out_of_contract'])

    def test_readiness_surface_uses_min_latest_usable_business_date(self) -> None:
        readiness = build_member_insight_readiness_response(
            request_id='req_owner_surface_min_date',
            trace_ref='navly:trace:owner-surface-min-date',
            target_scope_ref='navly:scope:store:demo-org-001',
            target_business_date='2026-03-23',
            vertical_slice_result={
                'historical_run_truth': {
                    'ingestion_run': {
                        'run_trace_ref': 'navly:run-trace:ingestion:min-date',
                    },
                    'endpoint_runs': [
                        {
                            'endpoint_contract_id': 'qinqin.member.get_customers_list.v1_1',
                            'endpoint_run_trace_ref': 'navly:run-trace:endpoint:customers',
                            'endpoint_status': 'completed',
                        },
                        {
                            'endpoint_contract_id': 'qinqin.member.get_consume_bill_list.v1_2',
                            'endpoint_run_trace_ref': 'navly:run-trace:endpoint:consume',
                            'endpoint_status': 'completed',
                        },
                    ],
                },
                'latest_state_artifacts': {
                    'latest_usable_endpoint_states': [
                        {
                            'endpoint_contract_id': 'qinqin.member.get_customers_list.v1_1',
                            'state_trace_ref': 'navly:state-trace:customers',
                            'latest_usable_business_date': '2026-03-23',
                            'availability_status': 'available',
                        },
                        {
                            'endpoint_contract_id': 'qinqin.member.get_consume_bill_list.v1_2',
                            'state_trace_ref': 'navly:state-trace:consume',
                            'latest_usable_business_date': '2026-03-21',
                            'availability_status': 'available',
                        },
                    ],
                    'vertical_slice_backbone_state': {
                        'state_trace_ref': 'navly:state-trace:vertical-slice',
                        'backbone_status': 'backbone_ready',
                        'updated_at': '2026-04-09T00:00:00Z',
                        'available_endpoint_contract_ids': [
                            'qinqin.member.get_customers_list.v1_1',
                            'qinqin.member.get_consume_bill_list.v1_2',
                        ],
                    },
                },
                'transport_kind': 'fixture',
            },
        )

        self.assertEqual(readiness['latest_usable_business_date'], '2026-03-21')


if __name__ == '__main__':
    unittest.main()
