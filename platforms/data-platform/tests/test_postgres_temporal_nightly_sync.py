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
CONTRACTS_ROOT = DATA_PLATFORM_ROOT / 'contracts'

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate  # noqa: E402
from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from ingestion.member_insight_vertical_slice import run_member_insight_vertical_slice  # noqa: E402
from workflows.postgres_temporal_nightly_sync import (  # noqa: E402
    NightlyPlannerPolicy,
    NightlySyncPlanner,
    NightlySyncRuntime,
    TemporalNightlySyncPlane,
    TemporalWorkerBootstrap,
    load_nightly_sync_policy_entry,
)
from workflows.postgres_temporal_operator_surface import (  # noqa: E402
    build_operator_status_bundle,
    query_operator_status_from_snapshot,
)


class PostgresTemporalNightlySyncTest(unittest.TestCase):
    def _load_contract(self, filename: str) -> dict:
        return json.loads((CONTRACTS_ROOT / filename).read_text(encoding='utf-8'))

    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _healthy_transport(self) -> FixtureQinqinTransport:
        return FixtureQinqinTransport(self._fixture_bundle())

    def _failing_transport(self) -> FixtureQinqinTransport:
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
        return FixtureQinqinTransport(fixture_bundle)

    def _vertical_slice_result(self, *, requested_business_date: str) -> dict:
        return run_member_insight_vertical_slice(
            org_id='demo-org-001',
            start_time=f'{requested_business_date} 00:00:00',
            end_time=f'{requested_business_date} 23:59:59',
            requested_business_date=requested_business_date,
            app_secret='test-secret',
            transport=self._healthy_transport(),
        )

    def test_postgres_truth_substrate_persists_authoritative_objects(self) -> None:
        store = PostgresTruthSubstrate()
        result = self._vertical_slice_result(requested_business_date='2026-03-23')
        persisted = store.persist_vertical_slice_result(
            org_id='demo-org-001',
            target_scope_ref='navly:scope:store:demo-org-001',
            target_business_date='2026-03-23',
            vertical_slice_result=result,
            scheduler_trace_ref='navly:workflow-trace:test:scheduler',
            workflow_id='navly-nightly-demo-org-001-2026-03-23',
        )

        self.assertEqual(len(store.ingestion_runs), 1)
        self.assertEqual(len(store.endpoint_runs), 2)
        self.assertEqual(len(store.page_runs), 2)
        self.assertEqual(len(store.raw_replay_artifacts), 2)
        self.assertEqual(len(store.canonical_facts['customer']), 1)
        self.assertEqual(len(store.canonical_facts['consume_bill']), 1)
        self.assertIn('customer_id', store.canonical_facts['customer'][0])
        self.assertIn('settle_id', store.canonical_facts['consume_bill'][0])
        self.assertEqual(len(store.field_coverage_snapshots), 2)
        self.assertEqual(len(store.schema_alignment_snapshots), 2)
        self.assertEqual(persisted['capability_readiness_snapshot']['readiness_status'], 'ready')
        self.assertEqual(persisted['service_projection']['service_status'], 'served')

        latest_state = store.get_latest_sync_state(
            org_id='demo-org-001',
            endpoint_contract_id='qinqin.member.get_customers_list.v1_1',
        )
        self.assertEqual(latest_state['latest_usable_business_date'], '2026-03-23')
        schema_sql = store.schema_sql()
        self.assertIn('navly_data_platform.ingestion_run', schema_sql)
        self.assertIn('navly_data_platform.backfill_progress_state', schema_sql)
        self.assertIn('navly_data_platform.service_projection', schema_sql)

    def test_policy_and_worker_bootstrap_load_from_repo_seed(self) -> None:
        policy_entry = load_nightly_sync_policy_entry()
        planner_policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
        )
        worker_bootstrap = TemporalWorkerBootstrap.from_registry()

        self.assertEqual(policy_entry['planner_mode'], 'currentness_first')
        self.assertEqual(planner_policy.backfill_order, 'latest_to_oldest')
        self.assertEqual(planner_policy.cursor_mode, 'carry_forward_cursor')
        self.assertEqual(planner_policy.max_backfill_tasks_per_run, 3)
        self.assertEqual(worker_bootstrap.task_queue, 'navly-data-platform-nightly')
        self.assertEqual(worker_bootstrap.retry_max_attempts, 3)

    def test_worker_bootstrap_loads_timeout_and_cron_from_repo_seed(self) -> None:
        worker_bootstrap = TemporalWorkerBootstrap.from_registry()
        self.assertEqual(worker_bootstrap.start_to_close_timeout_seconds, 900)
        self.assertEqual(worker_bootstrap.cron_schedule, '0 0 19 * * *')

    def test_worker_bootstrap_matches_governed_contract(self) -> None:
        contract = self._load_contract('temporal-worker-bootstrap-entry.contract.seed.json')
        worker_bootstrap = TemporalWorkerBootstrap.from_registry().to_record()
        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, worker_bootstrap)

    def test_latest_sync_state_does_not_regress_when_backfill_writes_older_date(self) -> None:
        store = PostgresTruthSubstrate()
        store.persist_vertical_slice_result(
            org_id='demo-org-001',
            target_scope_ref='navly:scope:store:demo-org-001',
            target_business_date='2026-03-23',
            vertical_slice_result=self._vertical_slice_result(requested_business_date='2026-03-23'),
        )
        store.persist_vertical_slice_result(
            org_id='demo-org-001',
            target_scope_ref='navly:scope:store:demo-org-001',
            target_business_date='2026-03-21',
            vertical_slice_result=self._vertical_slice_result(requested_business_date='2026-03-21'),
            task_kind='backfill',
        )

        latest_state = store.get_latest_sync_state(
            org_id='demo-org-001',
            endpoint_contract_id='qinqin.member.get_customers_list.v1_1',
        )
        self.assertEqual(latest_state['latest_usable_business_date'], '2026-03-23')
        self.assertEqual(latest_state['last_attempted_business_date'], '2026-03-21')

    def test_planner_generates_non_empty_backfill_tasks_for_older_gaps(self) -> None:
        store = PostgresTruthSubstrate()
        endpoint_ids = (
            'qinqin.member.get_customers_list.v1_1',
            'qinqin.member.get_consume_bill_list.v1_2',
        )
        for endpoint_contract_id in endpoint_ids:
            store.mark_business_date_completed(
                org_id='demo-org-001',
                endpoint_contract_id=endpoint_contract_id,
                business_date='2026-03-23',
            )
            store.mark_business_date_completed(
                org_id='demo-org-001',
                endpoint_contract_id=endpoint_contract_id,
                business_date='2026-03-20',
            )

        planner = NightlySyncPlanner(
            truth_store=store,
            policy=NightlyPlannerPolicy.from_registry(
                backfill_start_business_date='2026-03-20',
                max_backfill_tasks_per_run=3,
            ),
            endpoint_contract_ids=endpoint_ids,
        )
        plan = planner.build_plan(
            org_id='demo-org-001',
            target_business_date='2026-03-23',
            scheduler_trace_ref='navly:workflow-trace:test:planner',
            workflow_id='navly-nightly-demo-org-001-2026-03-23',
            task_queue='navly-data-platform-nightly',
        )

        self.assertEqual(
            plan.expected_business_dates,
            ('2026-03-20', '2026-03-21', '2026-03-22', '2026-03-23'),
        )
        self.assertEqual(
            [task.business_date for task in plan.backfill_tasks],
            ['2026-03-22', '2026-03-21'],
        )

    def test_carry_forward_cursor_resumes_from_previous_breakpoint(self) -> None:
        store = PostgresTruthSubstrate()
        endpoint_ids = (
            'qinqin.member.get_customers_list.v1_1',
            'qinqin.member.get_consume_bill_list.v1_2',
        )
        for endpoint_contract_id in endpoint_ids:
            store.mark_business_date_completed(
                org_id='demo-org-001',
                endpoint_contract_id=endpoint_contract_id,
                business_date='2026-03-23',
            )

        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(
            truth_store=store,
            policy=policy,
            endpoint_contract_ids=endpoint_ids,
        )
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
            endpoint_contract_ids=endpoint_ids,
        )

        first_plan = planner.build_plan(
            org_id='demo-org-001',
            target_business_date='2026-03-23',
            scheduler_trace_ref='navly:workflow-trace:test:carry-forward-1',
            workflow_id='navly-nightly-demo-org-001-2026-03-23',
            task_queue='navly-data-platform-nightly',
        )
        self.assertEqual(first_plan.backfill_tasks[0].business_date, '2026-03-22')
        runtime.execute_plan(plan=first_plan, transport=self._healthy_transport())

        second_plan = planner.build_plan(
            org_id='demo-org-001',
            target_business_date='2026-03-24',
            scheduler_trace_ref='navly:workflow-trace:test:carry-forward-2',
            workflow_id='navly-nightly-demo-org-001-2026-03-24',
            task_queue='navly-data-platform-nightly',
        )
        self.assertEqual(second_plan.backfill_tasks[0].business_date, '2026-03-21')
        progress_state = store.get_backfill_progress_state(
            org_id='demo-org-001',
            endpoint_contract_id='qinqin.member.get_customers_list.v1_1',
        )
        self.assertEqual(progress_state['cursor_business_date'], '2026-03-20')

    def test_temporal_plane_exposes_nightly_retry_and_rerun_paths_with_trace_linkage(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-22',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )

        nightly = temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._failing_transport()},
        )
        nightly_execution = nightly['org_executions'][0]['execution']
        self.assertEqual(nightly['worker_bootstrap']['task_queue'], 'navly-data-platform-nightly')
        self.assertTrue(nightly_execution['backfill_tasks'])
        self.assertEqual(nightly['org_executions'][0]['scheduler_run']['workflow_kind'], 'nightly_scheduler')
        self.assertTrue(nightly['org_executions'][0]['scheduler_run']['execution_trace_refs'])
        self.assertEqual(store.ingestion_runs[0]['scheduler_trace_ref'], nightly['scheduler_trace_ref'])

        retry = temporal_plane.run_retry_workflow(
            org_id='demo-org-001',
            business_date='2026-03-23',
            transport=self._healthy_transport(),
        )
        rerun = temporal_plane.run_rerun_workflow(
            org_id='demo-org-001',
            business_date='2026-03-22',
            transport=self._healthy_transport(),
        )

        self.assertEqual(retry['outcome']['task']['task_kind'], 'retry')
        self.assertEqual(retry['outcome']['run_status'], 'completed')
        self.assertEqual(rerun['outcome']['task']['task_kind'], 'rerun')
        self.assertEqual(rerun['outcome']['run_status'], 'completed')
        self.assertEqual(len(store.scheduler_runs), 3)

    def test_scheduler_run_persists_failure_budget_and_task_queue_from_worker_policy(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-22',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        worker_bootstrap = TemporalWorkerBootstrap.from_registry()
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
            worker_bootstrap=worker_bootstrap,
        )

        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        scheduler_run = store.scheduler_runs[0]
        self.assertEqual(scheduler_run['task_queue'], worker_bootstrap.task_queue)
        self.assertEqual(scheduler_run['failure_budget'], worker_bootstrap.retry_max_attempts)

    def test_cli_runner_exposes_repo_controlled_nightly_execution_path(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--max-backfill-tasks-per-run', '3',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload['output_dir'], tmpdir)
            self.assertTrue(Path(tmpdir, 'nightly-run-summary.json').exists())
            self.assertTrue(Path(tmpdir, 'scheduler-runs.json').exists())
            self.assertTrue(Path(tmpdir, 'latest-sync-states.json').exists())
            self.assertTrue(Path(tmpdir, 'backfill-progress-states.json').exists())
            self.assertTrue(Path(tmpdir, 'service-projections.json').exists())
            self.assertTrue(Path(tmpdir, 'operator-sync-status.json').exists())
            self.assertTrue(Path(tmpdir, 'operator-backfill-status.json').exists())
            self.assertTrue(Path(tmpdir, 'operator-quality-report.json').exists())
        self.assertEqual(payload['workflow_kind'], 'nightly_scheduler')
        self.assertEqual(payload['effective_policy']['policy_id'], 'navly.phase1.member_insight.nightly_sync')
        self.assertEqual(payload['effective_policy']['planner_mode'], 'currentness_first')
        self.assertEqual(payload['effective_policy']['backfill_order'], 'latest_to_oldest')
        self.assertEqual(payload['effective_policy']['cursor_mode'], 'carry_forward_cursor')
        self.assertEqual(payload['worker_bootstrap']['task_queue'], 'navly-data-platform-nightly')
        self.assertEqual(payload['org_count'], 1)
        self.assertEqual(payload['scheduler_runs'], 1)
        self.assertEqual(payload['ingestion_runs'], 4)
        self.assertEqual(
            payload['org_executions'][0]['backfill_business_dates'],
            ['2026-03-22', '2026-03-21', '2026-03-20'],
        )

    def test_cli_runner_worker_bootstrap_matches_governed_contract(self) -> None:
        contract = self._load_contract('temporal-worker-bootstrap-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        completed = subprocess.run(
            [
                sys.executable,
                str(script_path),
                '--org-id', 'demo-org-001',
                '--target-business-date', '2026-03-23',
                '--backfill-start-business-date', '2026-03-20',
                '--app-secret', 'test-secret',
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload['worker_bootstrap'])

    def test_cli_runner_worker_bootstrap_lists_expected_workflows_and_activities(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        completed = subprocess.run(
            [
                sys.executable,
                str(script_path),
                '--org-id', 'demo-org-001',
                '--target-business-date', '2026-03-23',
                '--backfill-start-business-date', '2026-03-20',
                '--app-secret', 'test-secret',
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(completed.stdout)
        worker_bootstrap = payload['worker_bootstrap']

        self.assertEqual(
            worker_bootstrap['workflow_names'],
            ['NightlySchedulerWorkflow', 'NightlyExecutionWorkflow', 'RetryWorkflow', 'RerunWorkflow'],
        )
        self.assertEqual(
            worker_bootstrap['activity_names'],
            ['run_member_insight_vertical_slice', 'persist_postgres_truth_substrate', 'reconcile_backfill_progress'],
        )

    def test_cli_runner_summary_matches_governed_summary_contract(self) -> None:
        contract = self._load_contract('nightly-run-summary-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(tmpdir, 'nightly-run-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)
            self.assertIn(field_name, summary_file_payload)

    def test_cli_runner_summary_preserves_custom_request_and_trace_refs(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--request-id', 'req-nightly-summary-custom-001',
                    '--trace-ref', 'navly:trace:req-nightly-summary-custom-001',
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(tmpdir, 'nightly-run-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['request_id'], 'req-nightly-summary-custom-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:req-nightly-summary-custom-001')
        self.assertEqual(summary_file_payload['request_id'], payload['request_id'])
        self.assertEqual(summary_file_payload['trace_ref'], payload['trace_ref'])

    def test_cli_runner_summary_file_matches_stdout_when_state_snapshot_is_enabled(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(tmpdir, 'nightly-run-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(summary_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(summary_file_payload['output_dir'], payload['output_dir'])

    def test_cli_runner_summary_preserves_request_trace_and_snapshot_metadata_together(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--request-id', 'req-nightly-summary-combined-001',
                    '--trace-ref', 'navly:trace:req-nightly-summary-combined-001',
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(tmpdir, 'nightly-run-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['request_id'], 'req-nightly-summary-combined-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:req-nightly-summary-combined-001')
        self.assertEqual(summary_file_payload['request_id'], payload['request_id'])
        self.assertEqual(summary_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(summary_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(summary_file_payload['output_dir'], payload['output_dir'])

    def test_cli_runner_writes_operator_facing_status_payloads(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            latest_sync_states = json.loads(Path(tmpdir, 'latest-sync-states.json').read_text(encoding='utf-8'))
            backfill_progress_states = json.loads(Path(tmpdir, 'backfill-progress-states.json').read_text(encoding='utf-8'))
            service_projections = json.loads(Path(tmpdir, 'service-projections.json').read_text(encoding='utf-8'))
            operator_quality_report = json.loads(Path(tmpdir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(len(latest_sync_states), 2)
        self.assertTrue(all(item['latest_usable_business_date'] == '2026-03-23' for item in latest_sync_states))
        self.assertEqual(len(backfill_progress_states), 2)
        self.assertTrue(all(item['progress_status'] == 'backfill_complete' for item in backfill_progress_states))
        self.assertEqual(len(service_projections), 4)
        self.assertEqual(len(operator_quality_report), 1)

    def test_runner_exported_operator_report_files_match_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            sync_reports = json.loads(Path(tmpdir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(tmpdir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(tmpdir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        for report in sync_reports:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in backfill_reports:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in quality_reports:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_runner_exported_state_files_match_governed_contracts(self) -> None:
        scheduler_contract = self._load_contract('scheduler-run-entry.contract.seed.json')
        latest_sync_contract = self._load_contract('latest-sync-state-entry.contract.seed.json')
        backfill_progress_contract = self._load_contract('backfill-progress-state-entry.contract.seed.json')
        service_projection_contract = self._load_contract('service-projection-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            scheduler_runs = json.loads(Path(tmpdir, 'scheduler-runs.json').read_text(encoding='utf-8'))
            latest_sync_states = json.loads(Path(tmpdir, 'latest-sync-states.json').read_text(encoding='utf-8'))
            backfill_progress_states = json.loads(Path(tmpdir, 'backfill-progress-states.json').read_text(encoding='utf-8'))
            service_projections = json.loads(Path(tmpdir, 'service-projections.json').read_text(encoding='utf-8'))

        for record in scheduler_runs:
            for field_name in scheduler_contract['fields']:
                self.assertIn(field_name, record)
        for record in latest_sync_states:
            for field_name in latest_sync_contract['fields']:
                self.assertIn(field_name, record)
        for record in backfill_progress_states:
            for field_name in backfill_progress_contract['fields']:
                self.assertIn(field_name, record)
        for record in service_projections:
            for field_name in service_projection_contract['fields']:
                self.assertIn(field_name, record)

    def test_truth_store_builds_operator_sync_and_backfill_reports(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=3,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        sync_report = store.build_sync_status_report(org_id='demo-org-001')
        backfill_report = store.build_backfill_status_report(org_id='demo-org-001')
        self.assertEqual(sync_report['org_id'], 'demo-org-001')
        self.assertEqual(len(sync_report['latest_sync_states']), 2)
        self.assertEqual(len(sync_report['scheduler_runs']), 1)
        self.assertEqual(backfill_report['org_id'], 'demo-org-001')
        self.assertEqual(len(backfill_report['backfill_progress_states']), 2)
        self.assertEqual(backfill_report['remaining_gap_count_total'], 0)

    def test_truth_store_builds_quality_report(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._failing_transport()},
        )

        quality_report = store.build_quality_report(org_id='demo-org-001')
        self.assertEqual(quality_report['org_id'], 'demo-org-001')
        self.assertGreaterEqual(len(quality_report['field_coverage_snapshots']), 2)
        self.assertGreaterEqual(len(quality_report['schema_alignment_snapshots']), 2)
        self.assertEqual(
            {
                item['endpoint_contract_id']
                for item in quality_report['field_coverage_snapshots']
            },
            {
                'qinqin.member.get_customers_list.v1_1',
                'qinqin.member.get_consume_bill_list.v1_2',
            },
        )
        self.assertGreaterEqual(quality_report['quality_issue_count'], 1)

    def test_operator_surface_builds_status_bundle_from_truth_store(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        bundle = build_operator_status_bundle(
            truth_store=store,
            org_ids=['demo-org-001'],
        )
        self.assertEqual(len(bundle['sync_status']), 1)
        self.assertEqual(len(bundle['backfill_status']), 1)
        self.assertEqual(len(bundle['quality_report']), 1)
        self.assertEqual(bundle['sync_status'][0]['org_id'], 'demo-org-001')
        self.assertEqual(bundle['backfill_status'][0]['org_id'], 'demo-org-001')
        self.assertEqual(bundle['quality_report'][0]['org_id'], 'demo-org-001')

    def test_temporal_plane_preserves_multi_org_fanout(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )

        result = temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001', 'demo-org-002'],
            target_business_date='2026-03-23',
            transport_by_org={
                'demo-org-001': self._healthy_transport(),
                'demo-org-002': self._healthy_transport(),
            },
        )

        self.assertEqual(len(result['org_executions']), 2)
        self.assertEqual({item['org_id'] for item in result['org_executions']}, {'demo-org-001', 'demo-org-002'})
        self.assertEqual(len(store.scheduler_runs), 2)
        self.assertEqual(
            len(store.build_sync_status_report(org_id='demo-org-001')['latest_sync_states']),
            2,
        )
        self.assertEqual(
            len(store.build_sync_status_report(org_id='demo-org-002')['latest_sync_states']),
            2,
        )

    def test_temporal_plane_preserves_requested_org_order(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )

        result = temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-002', 'demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={
                'demo-org-001': self._healthy_transport(),
                'demo-org-002': self._healthy_transport(),
            },
        )

        self.assertEqual(
            [item['org_id'] for item in result['org_executions']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_cli_runner_exports_multi_org_status_artifacts(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--max-backfill-tasks-per-run', '1',
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            operator_sync_status = json.loads(Path(tmpdir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            operator_backfill_status = json.loads(Path(tmpdir, 'operator-backfill-status.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['org_count'], 2)
        self.assertEqual({item['org_id'] for item in payload['org_executions']}, {'demo-org-001', 'demo-org-002'})
        self.assertEqual(len(operator_sync_status), 2)
        self.assertEqual(len(operator_backfill_status), 2)
        self.assertEqual({item['org_id'] for item in operator_sync_status}, {'demo-org-001', 'demo-org-002'})
        self.assertEqual({item['org_id'] for item in operator_backfill_status}, {'demo-org-001', 'demo-org-002'})

    def test_cli_runner_resumes_carry_forward_cursor_from_state_snapshot(self) -> None:
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            first = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--max-backfill-tasks-per-run', '1',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            first_payload = json.loads(first.stdout)
            second = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-24',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--max-backfill-tasks-per-run', '1',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            second_payload = json.loads(second.stdout)
            restored_snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))

        self.assertEqual(first_payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(
            first_payload['org_executions'][0]['backfill_business_dates'],
            ['2026-03-22'],
        )
        self.assertEqual(second_payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(
            second_payload['org_executions'][0]['backfill_business_dates'],
            ['2026-03-21'],
        )
        self.assertTrue(restored_snapshot['backfill_progress_states'])

    def test_state_snapshot_matches_governed_snapshot_contract(self) -> None:
        contract = self._load_contract('truth-store-snapshot-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = json.loads(snapshot_path.read_text(encoding='utf-8'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, snapshot_payload)

    def test_state_snapshot_canonical_fact_rows_match_governed_fact_contracts(self) -> None:
        customer_fact_contract = self._load_contract('member-insight-customer-fact-entry.contract.seed.json')
        customer_card_fact_contract = self._load_contract('member-insight-customer-card-fact-entry.contract.seed.json')
        consume_bill_fact_contract = self._load_contract('member-insight-consume-bill-fact-entry.contract.seed.json')
        consume_bill_payment_fact_contract = self._load_contract('member-insight-consume-bill-payment-fact-entry.contract.seed.json')
        consume_bill_info_fact_contract = self._load_contract('member-insight-consume-bill-info-fact-entry.contract.seed.json')
        script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = json.loads(snapshot_path.read_text(encoding='utf-8'))

        canonical_facts = snapshot_payload['canonical_facts']
        contract_pairs = [
            ('customer', customer_fact_contract),
            ('customer_card', customer_card_fact_contract),
            ('consume_bill', consume_bill_fact_contract),
            ('consume_bill_payment', consume_bill_payment_fact_contract),
            ('consume_bill_info', consume_bill_info_fact_contract),
        ]
        for fact_kind, contract in contract_pairs:
            self.assertTrue(canonical_facts[fact_kind])
            for field_name in contract['fields']:
                self.assertIn(field_name, canonical_facts[fact_kind][0])

    def test_status_query_cli_reads_operator_reports_from_saved_snapshot(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--max-backfill-tasks-per-run', '1',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(len(payload['sync_status']), 2)
        self.assertEqual(len(payload['backfill_status']), 2)
        self.assertEqual(len(payload['quality_report']), 2)
        self.assertEqual({item['org_id'] for item in payload['sync_status']}, {'demo-org-001', 'demo-org-002'})
        self.assertEqual({item['org_id'] for item in payload['backfill_status']}, {'demo-org-001', 'demo-org-002'})
        self.assertEqual({item['org_id'] for item in payload['quality_report']}, {'demo-org-001', 'demo-org-002'})

    def test_status_query_cli_preserves_request_and_trace_refs(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-custom-001',
                    '--trace-ref', 'navly:trace:operator-status-custom-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['request_id'], 'req-operator-status-custom-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-status-custom-001')

    def test_status_query_bundle_file_preserves_custom_request_and_trace_refs(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-custom-file-001',
                    '--trace-ref', 'navly:trace:operator-status-custom-file-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])

    def test_status_query_cli_fails_closed_when_snapshot_is_missing(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(payload['sync_status'][0]['scheduler_runs'], [])
        self.assertEqual(payload['backfill_status'][0]['backfill_progress_states'], [])
        self.assertEqual(payload['quality_report'][0]['quality_issues'], [])

    def test_status_query_cli_missing_snapshot_preserves_custom_request_and_trace_refs(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-missing-custom-001',
                    '--trace-ref', 'navly:trace:operator-status-missing-custom-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['request_id'], 'req-operator-status-missing-custom-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-status-missing-custom-001')

    def test_status_query_missing_snapshot_bundle_file_preserves_custom_request_and_trace_refs(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-missing-file-001',
                    '--trace-ref', 'navly:trace:operator-status-missing-file-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])

    def test_status_query_cli_writes_operator_status_artifacts(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload['output_dir'], str(output_dir))
            self.assertTrue(Path(output_dir, 'operator-status-bundle.json').exists())
            self.assertTrue(Path(output_dir, 'operator-sync-status.json').exists())
            self.assertTrue(Path(output_dir, 'operator-backfill-status.json').exists())
            self.assertTrue(Path(output_dir, 'operator-quality-report.json').exists())

    def test_status_query_bundle_file_matches_governed_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_status_query_missing_snapshot_bundle_matches_governed_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_status_query_bundle_file_matches_stdout_when_output_dir_is_enabled(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(bundle_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])

    def test_status_query_bundle_file_preserves_state_snapshot_and_output_dir_for_multi_org_queries(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_status_query_multi_org_bundle_preserves_custom_request_and_trace_refs(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-multi-001',
                    '--trace-ref', 'navly:trace:operator-status-multi-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_status_query_report_files_match_stdout_slices(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])

    def test_status_query_report_files_stay_aligned_with_bundle_under_custom_trace(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-operator-status-reports-001',
                    '--trace-ref', 'navly:trace:operator-status-reports-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])
        self.assertEqual(payload['request_id'], 'req-operator-status-reports-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-status-reports-001')

    def test_status_query_cli_missing_snapshot_still_writes_output_bundle(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(bundle_file_payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])

    def test_status_query_missing_snapshot_bundle_file_matches_governed_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, bundle_file_payload)

    def test_status_query_cli_missing_snapshot_report_files_match_stdout_slices(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])

    def test_status_query_missing_snapshot_bundle_file_preserves_state_snapshot_and_output_dir(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(bundle_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])

    def test_status_query_missing_snapshot_report_files_match_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        for report in sync_reports:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in backfill_reports:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in quality_reports:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_status_query_cli_matches_governed_status_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_status_query_reports_match_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_status_query_missing_snapshot_reports_match_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_status_query_preserves_requested_org_order(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--org-id', 'demo-org-002',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(
            [item['org_id'] for item in payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_status_query_missing_snapshot_preserves_requested_org_order(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(
            [item['org_id'] for item in payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_bridge_fed_status_query_bundle_preserves_custom_request_and_trace_refs(self) -> None:
        fixture_bundle = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            artifact_root = Path(tmpdir, 'artifact')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=artifact_root,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', str(artifact_root),
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-bridge-status-custom-001',
                    '--trace-ref', 'navly:trace:bridge-status-custom-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])

    def test_bridge_fed_status_query_report_files_stay_aligned_with_bundle_under_custom_trace(self) -> None:
        fixture_bundle = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            artifact_root = Path(tmpdir, 'artifact')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=artifact_root,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', str(artifact_root),
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-bridge-status-aligned-001',
                    '--trace-ref', 'navly:trace:bridge-status-aligned-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])
        self.assertEqual(payload['request_id'], 'req-bridge-status-aligned-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:bridge-status-aligned-001')

    def test_bridge_fed_status_query_report_files_preserve_custom_request_and_trace_refs(self) -> None:
        fixture_bundle = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            artifact_root = Path(tmpdir, 'artifact')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=artifact_root,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', str(artifact_root),
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--request-id', 'req-bridge-status-reports-001',
                    '--trace-ref', 'navly:trace:bridge-status-reports-001',
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])

    def test_status_query_missing_snapshot_bundle_file_preserves_requested_org_order(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            bundle_file_payload = json.loads(Path(output_dir, 'operator-status-bundle.json').read_text(encoding='utf-8'))

        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_status_query_missing_snapshot_report_files_preserve_requested_org_order(self) -> None:
        query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            output_dir = Path(tmpdir, 'status-output')
            subprocess.run(
                [
                    sys.executable,
                    str(query_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-002',
                    '--org-id', 'demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            sync_reports = json.loads(Path(output_dir, 'operator-sync-status.json').read_text(encoding='utf-8'))
            backfill_reports = json.loads(Path(output_dir, 'operator-backfill-status.json').read_text(encoding='utf-8'))
            quality_reports = json.loads(Path(output_dir, 'operator-quality-report.json').read_text(encoding='utf-8'))

        self.assertEqual([item['org_id'] for item in sync_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in backfill_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in quality_reports], ['demo-org-002', 'demo-org-001'])

    def test_operator_surface_reads_status_bundle_from_saved_snapshot(self) -> None:
        runner_script = DATA_PLATFORM_ROOT / 'scripts' / 'run_postgres_temporal_nightly_sync.py'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--backfill-start-business-date', '2026-03-20',
                    '--app-secret', 'test-secret',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-surface-snapshot-001',
                trace_ref='navly:trace:operator-surface-snapshot-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(len(payload['sync_status']), 1)
        self.assertEqual(len(payload['backfill_status']), 1)
        self.assertEqual(len(payload['quality_report']), 1)

    def test_operator_surface_helper_matches_governed_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-contract-001',
                trace_ref='navly:trace:operator-helper-contract-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_operator_surface_helper_preserves_request_and_trace_refs(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-001',
                trace_ref='navly:trace:operator-helper-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-operator-helper-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-helper-001')

    def test_operator_surface_helper_preserves_requested_org_order(self) -> None:
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001', 'demo-org-002'],
            target_business_date='2026-03-23',
            transport_by_org={
                'demo-org-001': self._healthy_transport(),
                'demo-org-002': self._healthy_transport(),
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-order-001',
                trace_ref='navly:trace:operator-helper-order-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(
            [item['org_id'] for item in payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_operator_surface_helper_multi_org_request_trace_and_contracts_align(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001', 'demo-org-002'],
            target_business_date='2026-03-23',
            transport_by_org={
                'demo-org-001': self._healthy_transport(),
                'demo-org-002': self._healthy_transport(),
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-multi-001',
                trace_ref='navly:trace:operator-helper-multi-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-operator-helper-multi-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-helper-multi-001')
        self.assertEqual([item['org_id'] for item in payload['sync_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['backfill_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['quality_report']], ['demo-org-002', 'demo-org-001'])
        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_operator_surface_helper_missing_snapshot_preserves_request_and_trace_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-missing-001',
                trace_ref='navly:trace:operator-helper-missing-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-operator-helper-missing-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-helper-missing-001')

    def test_operator_surface_helper_missing_snapshot_matches_governed_bundle_contract(self) -> None:
        contract = self._load_contract('operator-status-bundle-entry.contract.seed.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-missing-contract-001',
                trace_ref='navly:trace:operator-helper-missing-contract-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_operator_surface_helper_matches_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        store = PostgresTruthSubstrate()
        policy = NightlyPlannerPolicy.from_registry(
            backfill_start_business_date='2026-03-20',
            max_backfill_tasks_per_run=1,
        )
        planner = NightlySyncPlanner(truth_store=store, policy=policy)
        runtime = NightlySyncRuntime(
            truth_store=store,
            planner_policy=policy,
            app_secret='test-secret',
        )
        temporal_plane = TemporalNightlySyncPlane(
            truth_store=store,
            planner=planner,
            runtime=runtime,
        )
        temporal_plane.run_nightly_scheduler(
            org_ids=['demo-org-001'],
            target_business_date='2026-03-23',
            transport_by_org={'demo-org-001': self._healthy_transport()},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = store.write_snapshot_file(Path(tmpdir, 'truth-store-snapshot.json'))
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-entry-contracts-001',
                trace_ref='navly:trace:operator-helper-entry-contracts-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_operator_surface_helper_missing_snapshot_matches_governed_entry_contracts(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-missing-entry-contracts-001',
                trace_ref='navly:trace:operator-helper-missing-entry-contracts-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_operator_surface_helper_missing_snapshot_preserves_requested_org_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-missing-order-001',
                trace_ref='navly:trace:operator-helper-missing-order-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(
            [item['org_id'] for item in payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['backfill_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in payload['quality_report']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_operator_surface_helper_missing_snapshot_multi_org_request_trace_and_contracts_align(self) -> None:
        sync_contract = self._load_contract('operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = self._load_contract('operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = self._load_contract('operator-quality-report-entry.contract.seed.json')
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-helper-missing-multi-001',
                trace_ref='navly:trace:operator-helper-missing-multi-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-operator-helper-missing-multi-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:operator-helper-missing-multi-001')
        self.assertEqual([item['org_id'] for item in payload['sync_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['backfill_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['quality_report']], ['demo-org-002', 'demo-org-001'])
        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_operator_surface_returns_empty_reports_for_missing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'missing-truth-store-snapshot.json')
            payload = query_operator_status_from_snapshot(
                request_id='req-operator-surface-missing-001',
                trace_ref='navly:trace:operator-surface-missing-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertEqual(payload['sync_status'][0]['org_id'], 'demo-org-001')
        self.assertEqual(payload['sync_status'][0]['scheduler_runs'], [])
        self.assertEqual(payload['backfill_status'][0]['backfill_progress_states'], [])
        self.assertEqual(payload['quality_report'][0]['quality_issues'], [])


if __name__ == '__main__':
    unittest.main()
