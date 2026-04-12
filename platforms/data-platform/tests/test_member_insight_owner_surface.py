from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from completeness.member_insight_readiness_surface import build_member_insight_readiness_response  # noqa: E402
from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate  # noqa: E402
from workflows.postgres_temporal_nightly_sync import (  # noqa: E402
    NightlyPlannerPolicy,
    NightlySyncPlanner,
    NightlySyncRuntime,
    TemporalNightlySyncPlane,
)
from workflows.member_insight_owner_surface import (  # noqa: E402
    build_member_insight_owner_surface,
    build_member_insight_owner_surface_from_snapshot,
    query_member_insight_capability_readiness_from_snapshot,
    query_member_insight_theme_service_from_snapshot,
    query_member_insight_capability_readiness,
    query_member_insight_theme_service,
)


class MemberInsightOwnerSurfaceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _load_shared_schema(self, relative_path: str) -> dict:
        return json.loads((DATA_PLATFORM_ROOT.parents[1] / 'shared' / 'contracts' / relative_path).read_text(encoding='utf-8'))

    def _assert_matches_shared_response_schemas(self, readiness: dict, service: dict) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, service)

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

    def test_owner_surface_can_query_persisted_snapshot_without_resync(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot',
                trace_ref='navly:trace:owner-surface-snapshot',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        readiness = result['readiness_response']
        service = result['theme_service_response']
        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(readiness['extensions']['surface_source'], 'persisted_snapshot')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['extensions']['surface_source'], 'persisted_snapshot')
        self.assertEqual(service['service_object']['customer_count'], 1)
        self.assertNotIn('explanation_object', service)

    def test_owner_surface_snapshot_path_fails_closed_when_persisted_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'empty-truth-store-snapshot.json')
            PostgresTruthSubstrate().write_snapshot_file(snapshot_path)
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_missing',
                trace_ref='navly:trace:owner-surface-snapshot-missing',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        readiness = result['readiness_response']
        service = result['theme_service_response']
        self.assertEqual(readiness['readiness_status'], 'pending')
        self.assertEqual(readiness['reason_codes'], ['missing_persisted_state'])
        self.assertEqual(service['service_status'], 'not_ready')
        self.assertEqual(service['explanation_object']['reason_codes'], ['missing_persisted_state'])

    def test_owner_surface_snapshot_path_fails_closed_when_service_projection_is_missing(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_missing_service',
                trace_ref='navly:trace:owner-surface-snapshot-missing-service',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        readiness = result['readiness_response']
        service = result['theme_service_response']
        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'not_ready')
        self.assertEqual(service['explanation_object']['reason_codes'], ['missing_persisted_projection'])

    def test_snapshot_owner_surface_cli_fails_closed_when_service_projection_is_missing(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(payload['theme_service_response']['service_status'], 'not_ready')
        self.assertEqual(payload['theme_service_response']['explanation_object']['reason_codes'], ['missing_persisted_projection'])

    def test_snapshot_owner_surface_cli_missing_projection_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_projection_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-missing-projection-001',
                    '--trace-ref', 'navly:trace:owner-surface-missing-projection-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['request_id'], 'req-owner-surface-missing-projection-001')
        self.assertEqual(payload['readiness_response']['trace_ref'], 'navly:trace:owner-surface-missing-projection-001')
        self.assertEqual(payload['theme_service_response']['request_id'], 'req-owner-surface-missing-projection-001')
        self.assertEqual(payload['theme_service_response']['trace_ref'], 'navly:trace:owner-surface-missing-projection-001')

    def test_snapshot_owner_surface_cli_missing_projection_response_files_preserve_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-missing-projection-file-001',
                    '--trace-ref', 'navly:trace:owner-surface-missing-projection-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-owner-surface-missing-projection-file-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:owner-surface-missing-projection-file-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-owner-surface-missing-projection-file-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:owner-surface-missing-projection-file-001')

    def test_snapshot_owner_surface_cli_missing_projection_response_files_match_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_projection_output_file_matches_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_projection_output_file_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_projection_output_file_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-missing-projection-bundle-001',
                    '--trace-ref', 'navly:trace:owner-surface-missing-projection-bundle-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_cli_missing_projection_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_owner_surface_snapshot_path_rejects_non_member_insight_capability(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_wrong_capability',
                trace_ref='navly:trace:owner-surface-snapshot-wrong-capability',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
                requested_capability_id='navly.store.daily_overview',
            )

        self.assertEqual(result['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(result['theme_service_response']['service_status'], 'scope_mismatch')

    def test_owner_surface_snapshot_path_rejects_non_member_insight_service_object(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_wrong_service',
                trace_ref='navly:trace:owner-surface-snapshot-wrong-service',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
                requested_service_object_id='navly.service.store.daily_overview',
            )

        self.assertEqual(result['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(result['theme_service_response']['service_status'], 'scope_mismatch')

    def test_snapshot_readiness_and_theme_query_helpers_match_combined_surface(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            readiness = query_member_insight_capability_readiness_from_snapshot(
                request_id='req_owner_surface_snapshot_query_readiness',
                trace_ref='navly:trace:owner-surface-snapshot-query-readiness',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )
            service = query_member_insight_theme_service_from_snapshot(
                request_id='req_owner_surface_snapshot_query_theme',
                trace_ref='navly:trace:owner-surface-snapshot-query-theme',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        self.assertEqual(readiness['readiness_status'], 'ready')
        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['service_object']['customer_count'], 1)

    def test_snapshot_owner_surface_helpers_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_schema',
                trace_ref='navly:trace:owner-surface-snapshot-schema',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, result['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, result['theme_service_response'])

    def test_snapshot_owner_surface_helper_bundle_matches_governed_contract(self) -> None:
        contract = json.loads(
            (DATA_PLATFORM_ROOT / 'contracts' / 'member-insight-owner-surface-snapshot-bundle-entry.contract.seed.json')
            .read_text(encoding='utf-8')
        )
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_bundle_contract',
                trace_ref='navly:trace:owner-surface-snapshot-bundle-contract',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, result)
        self.assertEqual(result['state_snapshot'], str(snapshot_path))

    def test_snapshot_readiness_helper_fails_closed_when_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'empty-truth-store-snapshot.json')
            PostgresTruthSubstrate().write_snapshot_file(snapshot_path)
            readiness = query_member_insight_capability_readiness_from_snapshot(
                request_id='req_owner_surface_snapshot_readiness_missing',
                trace_ref='navly:trace:owner-surface-snapshot-readiness-missing',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        self.assertEqual(readiness['readiness_status'], 'pending')
        self.assertEqual(readiness['reason_codes'], ['missing_persisted_state'])

    def test_snapshot_theme_helper_rejects_wrong_service_object(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            service = query_member_insight_theme_service_from_snapshot(
                request_id='req_owner_surface_snapshot_theme_scope_mismatch',
                trace_ref='navly:trace:owner-surface-snapshot-theme-scope-mismatch',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
                requested_service_object_id='navly.service.store.daily_overview',
            )

        self.assertEqual(service['service_status'], 'scope_mismatch')
        self.assertEqual(service['explanation_object']['reason_codes'], ['scope_out_of_contract'])

    def test_snapshot_owner_surface_cli_matches_governed_bundle_contract(self) -> None:
        contract = json.loads(
            (DATA_PLATFORM_ROOT / 'contracts' / 'member-insight-owner-surface-snapshot-cli-bundle-entry.contract.seed.json')
            .read_text(encoding='utf-8')
        )
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(tmpdir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))
            readiness_file_payload = json.loads(Path(tmpdir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(tmpdir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)
            self.assertIn(field_name, file_payload)
        self.assertEqual(payload['theme_service_response']['service_status'], 'served')
        self.assertEqual(payload['theme_service_response']['extensions']['surface_source'], 'persisted_snapshot')
        self.assertNotIn('explanation_object', payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_matches_shared_response_contracts(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self._assert_matches_shared_response_schemas(
            payload['readiness_response'],
            payload['theme_service_response'],
        )
        self.assertNotIn('explanation_object', payload['theme_service_response'])

    def test_snapshot_owner_surface_missing_state_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'empty-truth-store-snapshot.json')
            PostgresTruthSubstrate().write_snapshot_file(snapshot_path)
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_missing_schema',
                trace_ref='navly:trace:owner-surface-snapshot-missing-schema',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, result['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, result['theme_service_response'])
        self.assertEqual(result['readiness_response']['reason_codes'], ['missing_persisted_state'])
        self.assertEqual(result['theme_service_response']['service_status'], 'not_ready')

    def test_snapshot_owner_surface_missing_projection_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )
        truth_store.service_projections.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_missing_projection_schema',
                trace_ref='navly:trace:owner-surface-snapshot-missing-projection-schema',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, result['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, result['theme_service_response'])
        self.assertEqual(result['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(result['theme_service_response']['service_status'], 'not_ready')
        self.assertEqual(result['theme_service_response']['explanation_object']['reason_codes'], ['missing_persisted_projection'])

    def test_snapshot_owner_surface_scope_mismatch_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            result = build_member_insight_owner_surface_from_snapshot(
                request_id='req_owner_surface_snapshot_scope_schema',
                trace_ref='navly:trace:owner-surface-snapshot-scope-schema',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
                requested_capability_id='navly.store.daily_overview',
                requested_service_object_id='navly.service.store.daily_overview',
            )

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, result['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, result['theme_service_response'])
        self.assertEqual(result['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(result['theme_service_response']['service_status'], 'scope_mismatch')

    def test_snapshot_owner_surface_cli_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_snapshot_owner_surface_cli_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-custom-001',
                    '--trace-ref', 'navly:trace:owner-surface-custom-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['request_id'], 'req-owner-surface-custom-001')
        self.assertEqual(payload['readiness_response']['trace_ref'], 'navly:trace:owner-surface-custom-001')
        self.assertEqual(payload['theme_service_response']['request_id'], 'req-owner-surface-custom-001')
        self.assertEqual(payload['theme_service_response']['trace_ref'], 'navly:trace:owner-surface-custom-001')

    def test_snapshot_owner_surface_cli_output_file_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-custom-file-001',
                    '--trace-ref', 'navly:trace:owner-surface-custom-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_helpers_mark_theme_service_as_persisted_snapshot(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            service = query_member_insight_theme_service_from_snapshot(
                request_id='req_owner_surface_snapshot_theme_source',
                trace_ref='navly:trace:owner-surface-snapshot-theme-source',
                target_scope_ref='navly:scope:store:demo-org-001',
                target_business_date='2026-03-23',
                org_id='demo-org-001',
                state_snapshot_path=str(snapshot_path),
            )

        self.assertEqual(service['service_status'], 'served')
        self.assertEqual(service['extensions']['surface_source'], 'persisted_snapshot')

    def test_snapshot_owner_surface_cli_file_matches_stdout_when_output_dir_is_enabled(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_bundle_preserves_state_snapshot_and_output_dir(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])

    def test_snapshot_owner_surface_cli_served_outputs_omit_explanation_object(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertNotIn('explanation_object', payload['theme_service_response'])
        self.assertNotIn('explanation_object', file_payload['theme_service_response'])
        self.assertNotIn('explanation_object', theme_service_file_payload)

    def test_snapshot_owner_surface_cli_fails_closed_when_snapshot_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'pending')
        self.assertEqual(payload['theme_service_response']['service_status'], 'not_ready')
        self.assertEqual(payload['theme_service_response']['explanation_object']['reason_codes'], ['missing_persisted_state'])

    def test_snapshot_owner_surface_cli_missing_snapshot_matches_shared_response_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self._assert_matches_shared_response_schemas(
            payload['readiness_response'],
            payload['theme_service_response'],
        )

    def test_snapshot_owner_surface_cli_missing_snapshot_still_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response']['reason_codes'], ['missing_persisted_state'])

    def test_snapshot_owner_surface_cli_missing_snapshot_output_file_matches_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_snapshot_output_file_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_snapshot_response_files_match_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_missing_snapshot_preserves_request_and_trace_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-missing-custom-001',
                    '--trace-ref', 'navly:trace:owner-surface-missing-custom-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['request_id'], 'req-owner-surface-missing-custom-001')
        self.assertEqual(payload['readiness_response']['trace_ref'], 'navly:trace:owner-surface-missing-custom-001')
        self.assertEqual(payload['theme_service_response']['request_id'], 'req-owner-surface-missing-custom-001')
        self.assertEqual(payload['theme_service_response']['trace_ref'], 'navly:trace:owner-surface-missing-custom-001')

    def test_snapshot_owner_surface_cli_missing_snapshot_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_snapshot_owner_surface_cli_missing_snapshot_output_file_preserves_request_and_trace_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-owner-surface-missing-custom-file-001',
                    '--trace-ref', 'navly:trace:owner-surface-missing-custom-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_cli_rejects_scope_mismatch_inputs(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(payload['theme_service_response']['service_status'], 'scope_mismatch')

    def test_snapshot_owner_surface_cli_scope_mismatch_matches_shared_response_contracts(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self._assert_matches_shared_response_schemas(
            payload['readiness_response'],
            payload['theme_service_response'],
        )

    def test_snapshot_owner_surface_cli_wrong_service_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_capability_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_rejects_wrong_service_object_only(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(payload['theme_service_response']['service_status'], 'scope_mismatch')
        self.assertEqual(payload['theme_service_response']['explanation_object']['reason_codes'], ['scope_out_of_contract'])

    def test_snapshot_owner_surface_cli_wrong_service_object_still_writes_output_file(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response']['readiness_status'], payload['readiness_response']['readiness_status'])
        self.assertEqual(file_payload['theme_service_response']['service_status'], 'scope_mismatch')
        self.assertEqual(
            file_payload['theme_service_response']['explanation_object']['reason_codes'],
            payload['theme_service_response']['explanation_object']['reason_codes'],
        )

    def test_snapshot_owner_surface_cli_wrong_service_output_file_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--request-id', 'req-owner-surface-wrong-service-file-001',
                    '--trace-ref', 'navly:trace:owner-surface-wrong-service-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_cli_wrong_service_output_file_matches_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_service_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_service_output_file_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_service_response_files_match_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_service_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_snapshot_owner_surface_cli_wrong_service_response_files_preserve_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--request-id', 'req-owner-surface-wrong-service-response-001',
                    '--trace-ref', 'navly:trace:owner-surface-wrong-service-response-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-owner-surface-wrong-service-response-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:owner-surface-wrong-service-response-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-owner-surface-wrong-service-response-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:owner-surface-wrong-service-response-001')

    def test_snapshot_owner_surface_cli_rejects_wrong_capability_only(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(payload['theme_service_response']['service_status'], 'scope_mismatch')

    def test_snapshot_owner_surface_cli_wrong_capability_still_writes_output_file(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(file_payload['theme_service_response']['service_status'], 'scope_mismatch')
        self.assertEqual(file_payload['readiness_response']['reason_codes'], payload['readiness_response']['reason_codes'])
        self.assertEqual(
            file_payload['theme_service_response']['explanation_object']['reason_codes'],
            payload['theme_service_response']['explanation_object']['reason_codes'],
        )

    def test_snapshot_owner_surface_cli_wrong_capability_response_files_match_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_capability_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_snapshot_owner_surface_cli_wrong_capability_response_files_preserve_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-owner-surface-wrong-capability-response-001',
                    '--trace-ref', 'navly:trace:owner-surface-wrong-capability-response-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-owner-surface-wrong-capability-response-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:owner-surface-wrong-capability-response-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-owner-surface-wrong-capability-response-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:owner-surface-wrong-capability-response-001')

    def test_snapshot_owner_surface_cli_wrong_capability_output_file_preserves_request_and_trace_ids(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-owner-surface-wrong-cap-file-001',
                    '--trace-ref', 'navly:trace:owner-surface-wrong-cap-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_bundle_preserves_request_and_trace_ids_across_negative_paths(self) -> None:
        def build_snapshot_for_case(case_name: str, tmpdir: str) -> Path:
            if case_name == 'missing_snapshot':
                return Path(tmpdir, 'missing-truth-store-snapshot.json')

            truth_store = PostgresTruthSubstrate()
            policy = NightlyPlannerPolicy.from_registry(
                backfill_start_business_date='2026-03-20',
                max_backfill_tasks_per_run=1,
            )
            planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
            runtime = NightlySyncRuntime(
                truth_store=truth_store,
                planner_policy=policy,
                app_secret='test-secret',
            )
            temporal_plane = TemporalNightlySyncPlane(
                truth_store=truth_store,
                planner=planner,
                runtime=runtime,
            )
            temporal_plane.run_nightly_scheduler(
                org_ids=['demo-org-001'],
                target_business_date='2026-03-23',
                transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
            )
            if case_name == 'missing_projection':
                truth_store.service_projections.clear()
            return truth_store.write_snapshot_file(Path(tmpdir, f'{case_name}-truth-store-snapshot.json'))

        cases = [
            {
                'name': 'missing_snapshot',
                'extra_args': [],
                'request_id': 'req-owner-surface-negative-missing-snapshot-001',
                'trace_ref': 'navly:trace:owner-surface-negative-missing-snapshot-001',
            },
            {
                'name': 'missing_projection',
                'extra_args': [],
                'request_id': 'req-owner-surface-negative-missing-projection-001',
                'trace_ref': 'navly:trace:owner-surface-negative-missing-projection-001',
            },
            {
                'name': 'wrong_service',
                'extra_args': ['--requested-service-object-id', 'navly.service.store.daily_overview'],
                'request_id': 'req-owner-surface-negative-wrong-service-001',
                'trace_ref': 'navly:trace:owner-surface-negative-wrong-service-001',
            },
            {
                'name': 'wrong_capability',
                'extra_args': ['--requested-capability-id', 'navly.store.daily_overview'],
                'request_id': 'req-owner-surface-negative-wrong-capability-001',
                'trace_ref': 'navly:trace:owner-surface-negative-wrong-capability-001',
            },
        ]

        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
        env = {
            **os.environ,
            'PYTHONPATH': str(DATA_PLATFORM_ROOT),
        }
        for case in cases:
            with self.subTest(case=case['name']):
                with tempfile.TemporaryDirectory() as tmpdir:
                    snapshot_path = build_snapshot_for_case(case['name'], tmpdir)
                    output_dir = Path(tmpdir, 'owner-surface-output')
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(script_path),
                            '--state-snapshot', str(snapshot_path),
                            '--org-id', 'demo-org-001',
                            '--target-business-date', '2026-03-23',
                            '--target-scope-ref', 'navly:scope:store:demo-org-001',
                            '--request-id', case['request_id'],
                            '--trace-ref', case['trace_ref'],
                            '--output-dir', str(output_dir),
                            *case['extra_args'],
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    payload = json.loads(completed.stdout)
                    file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

                self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
                self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
                self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
                self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_snapshot_owner_surface_helper_preserves_request_and_trace_ids_across_negative_paths(self) -> None:
        def build_snapshot_for_case(case_name: str, tmpdir: str) -> Path:
            if case_name == 'missing_snapshot':
                return Path(tmpdir, 'missing-truth-store-snapshot.json')

            truth_store = PostgresTruthSubstrate()
            policy = NightlyPlannerPolicy.from_registry(
                backfill_start_business_date='2026-03-20',
                max_backfill_tasks_per_run=1,
            )
            planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
            runtime = NightlySyncRuntime(
                truth_store=truth_store,
                planner_policy=policy,
                app_secret='test-secret',
            )
            temporal_plane = TemporalNightlySyncPlane(
                truth_store=truth_store,
                planner=planner,
                runtime=runtime,
            )
            temporal_plane.run_nightly_scheduler(
                org_ids=['demo-org-001'],
                target_business_date='2026-03-23',
                transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
            )
            if case_name == 'missing_projection':
                truth_store.service_projections.clear()
            return truth_store.write_snapshot_file(Path(tmpdir, f'{case_name}-truth-store-snapshot.json'))

        cases = [
            {
                'name': 'missing_snapshot',
                'request_id': 'req-owner-surface-helper-negative-missing-snapshot-001',
                'trace_ref': 'navly:trace:owner-surface-helper-negative-missing-snapshot-001',
                'kwargs': {},
            },
            {
                'name': 'missing_projection',
                'request_id': 'req-owner-surface-helper-negative-missing-projection-001',
                'trace_ref': 'navly:trace:owner-surface-helper-negative-missing-projection-001',
                'kwargs': {},
            },
            {
                'name': 'wrong_service',
                'request_id': 'req-owner-surface-helper-negative-wrong-service-001',
                'trace_ref': 'navly:trace:owner-surface-helper-negative-wrong-service-001',
                'kwargs': {'requested_service_object_id': 'navly.service.store.daily_overview'},
            },
            {
                'name': 'wrong_capability',
                'request_id': 'req-owner-surface-helper-negative-wrong-capability-001',
                'trace_ref': 'navly:trace:owner-surface-helper-negative-wrong-capability-001',
                'kwargs': {'requested_capability_id': 'navly.store.daily_overview'},
            },
        ]

        for case in cases:
            with self.subTest(case=case['name']):
                with tempfile.TemporaryDirectory() as tmpdir:
                    snapshot_path = build_snapshot_for_case(case['name'], tmpdir)
                    result = build_member_insight_owner_surface_from_snapshot(
                        request_id=case['request_id'],
                        trace_ref=case['trace_ref'],
                        target_scope_ref='navly:scope:store:demo-org-001',
                        target_business_date='2026-03-23',
                        org_id='demo-org-001',
                        state_snapshot_path=str(snapshot_path),
                        **case['kwargs'],
                    )

                self.assertEqual(result['readiness_response']['request_id'], case['request_id'])
                self.assertEqual(result['readiness_response']['trace_ref'], case['trace_ref'])
                self.assertEqual(result['theme_service_response']['request_id'], case['request_id'])
                self.assertEqual(result['theme_service_response']['trace_ref'], case['trace_ref'])

    def test_snapshot_owner_surface_cli_wrong_capability_output_file_matches_stdout(self) -> None:
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_capability_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = json.loads(completed.stdout)

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, payload['theme_service_response'])

    def test_snapshot_owner_surface_cli_wrong_capability_output_file_matches_shared_response_contracts(self) -> None:
        readiness_schema = self._load_shared_schema('readiness/capability_readiness_response.schema.json')
        theme_service_schema = self._load_shared_schema('service/theme_service_response.schema.json')
        truth_store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=truth_store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=truth_store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': FixtureQinqinTransport(self._fixture_bundle())},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = truth_store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            output_dir = Path(tmpdir, 'owner-surface-output')
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])


if __name__ == '__main__':
    unittest.main()
