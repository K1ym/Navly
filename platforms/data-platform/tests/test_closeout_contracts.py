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

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from ingestion.member_insight_vertical_slice import run_member_insight_vertical_slice  # noqa: E402
from migration.artifact_tree_bridge import (  # noqa: E402
    import_member_insight_artifact_tree_to_truth_store,
)
from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate  # noqa: E402
from workflows.postgres_temporal_operator_surface import query_operator_status_from_snapshot  # noqa: E402


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


class CloseoutContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contracts_dir = DATA_PLATFORM_ROOT / 'contracts'
        cls.ownership = _load_json(cls.contracts_dir / 'contract-ownership.seed.json')
        cls.shared_contracts_dir = DATA_PLATFORM_ROOT.parents[1] / 'shared' / 'contracts'
        cls.ddl = (
            DATA_PLATFORM_ROOT
            / 'migration'
            / 'sql'
            / '2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql'
        ).read_text(encoding='utf-8')

    def test_contract_ownership_lists_closeout_truth_objects(self) -> None:
        owned = set(self.ownership['data_platform_owned_contracts'])
        self.assertEqual(self.ownership['status'], 'phase_1_closeout_contract_frozen')
        for contract_name in {
            'nightly_sync_policy_entry',
            'scheduler_run_entry',
            'ingestion_page_run_entry',
            'raw_replay_artifact_entry',
            'latest_sync_state_entry',
            'vertical_slice_backbone_state_entry',
            'member_insight_customer_fact_entry',
            'member_insight_customer_card_fact_entry',
            'member_insight_consume_bill_fact_entry',
            'member_insight_consume_bill_payment_fact_entry',
            'member_insight_consume_bill_info_fact_entry',
            'member_insight_customer_canonical_row_entry',
            'member_insight_customer_card_canonical_row_entry',
            'member_insight_consume_bill_canonical_row_entry',
            'member_insight_consume_bill_payment_canonical_row_entry',
            'member_insight_consume_bill_info_canonical_row_entry',
            'backfill_progress_state_entry',
            'field_coverage_snapshot_entry',
            'schema_alignment_snapshot_entry',
            'quality_issue_entry',
            'capability_readiness_snapshot_entry',
            'service_projection_entry',
            'temporal_worker_bootstrap_entry',
            'nightly_run_summary_entry',
            'truth_store_snapshot_entry',
            'artifact_bridge_summary_entry',
            'member_insight_vertical_slice_summary_entry',
            'member_insight_owner_surface_snapshot_bundle_entry',
            'member_insight_owner_surface_snapshot_cli_bundle_entry',
            'operator_status_bundle_entry',
            'operator_sync_status_report_entry',
            'operator_backfill_status_report_entry',
            'operator_quality_report_entry',
        }:
            self.assertIn(contract_name, owned)

    def test_nightly_sync_policy_seed_is_formalized(self) -> None:
        policy_contract = _load_json(self.contracts_dir / 'nightly-sync-policy-entry.contract.seed.json')
        policy_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'nightly-sync-policy.seed.json')
        self.assertEqual(policy_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(policy_registry['status'], 'phase_1_closeout_frozen')
        entry = policy_registry['entries'][0]
        for field_name in policy_contract['fields']:
            self.assertIn(field_name, entry)

    def test_member_insight_capability_registry_path_is_no_longer_placeholder(self) -> None:
        dependency_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-dependency-registry.seed.json')
        capability_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-registry.seed.json')
        service_bindings = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-service-bindings.seed.json')

        self.assertFalse((DATA_PLATFORM_ROOT / 'directory' / 'capability-dependency-registry.placeholder.json').exists())
        self.assertEqual(dependency_registry['status'], 'phase_1_closeout_member_insight_authoritative')

        dependency_entry = next(
            entry for entry in dependency_registry['entries']
            if entry['capability_id'] == 'navly.store.member_insight'
        )
        capability_entry = next(
            entry for entry in capability_registry['entries']
            if entry['capability_id'] == 'navly.store.member_insight'
        )
        binding_entry = next(
            entry for entry in service_bindings['entries']
            if entry['capability_id'] == 'navly.store.member_insight'
        )

        self.assertEqual(dependency_entry['dependency_status'], 'phase_1_closeout_authoritative')
        self.assertEqual(capability_entry['status'], 'phase_1_closeout_authoritative')
        self.assertEqual(binding_entry['status'], 'phase_1_closeout_authoritative')

    def test_partial_capability_registries_only_mark_member_insight_authoritative(self) -> None:
        dependency_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-dependency-registry.seed.json')
        capability_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-registry.seed.json')
        service_bindings = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-service-bindings.seed.json')

        self.assertEqual(capability_registry['status'], 'phase_1_closeout_partial')
        self.assertEqual(service_bindings['status'], 'phase_1_closeout_partial')

        capability_statuses = {
            entry['capability_id']: entry['status']
            for entry in capability_registry['entries']
        }
        binding_statuses = {
            entry['capability_id']: entry['status']
            for entry in service_bindings['entries']
        }
        dependency_statuses = {
            entry['capability_id']: entry['dependency_status']
            for entry in dependency_registry['entries']
        }

        self.assertEqual(capability_statuses['navly.store.member_insight'], 'phase_1_closeout_authoritative')
        self.assertEqual(binding_statuses['navly.store.member_insight'], 'phase_1_closeout_authoritative')
        self.assertEqual(dependency_statuses['navly.store.member_insight'], 'phase_1_closeout_authoritative')

        for capability_id in (
            'navly.store.daily_overview',
            'navly.store.staff_board',
            'navly.store.finance_summary',
        ):
            self.assertEqual(capability_statuses[capability_id], 'seeded_not_implemented')
            self.assertEqual(binding_statuses[capability_id], 'seeded_not_implemented')
            self.assertEqual(dependency_statuses[capability_id], 'deferred_not_implemented')

    def test_operator_status_report_contracts_match_truth_store_shape(self) -> None:
        sync_report_contract = _load_json(self.contracts_dir / 'operator-sync-status-report-entry.contract.seed.json')
        backfill_report_contract = _load_json(self.contracts_dir / 'operator-backfill-status-report-entry.contract.seed.json')
        quality_report_contract = _load_json(self.contracts_dir / 'operator-quality-report-entry.contract.seed.json')
        temporal_worker_bootstrap_contract = _load_json(self.contracts_dir / 'temporal-worker-bootstrap-entry.contract.seed.json')
        nightly_run_summary_contract = _load_json(self.contracts_dir / 'nightly-run-summary-entry.contract.seed.json')
        truth_store_snapshot_contract = _load_json(self.contracts_dir / 'truth-store-snapshot-entry.contract.seed.json')
        artifact_bridge_summary_contract = _load_json(self.contracts_dir / 'artifact-bridge-summary-entry.contract.seed.json')
        vertical_slice_summary_contract = _load_json(self.contracts_dir / 'member-insight-vertical-slice-summary-entry.contract.seed.json')
        owner_surface_snapshot_bundle_contract = _load_json(self.contracts_dir / 'member-insight-owner-surface-snapshot-bundle-entry.contract.seed.json')
        owner_surface_snapshot_cli_bundle_contract = _load_json(self.contracts_dir / 'member-insight-owner-surface-snapshot-cli-bundle-entry.contract.seed.json')
        operator_status_bundle_contract = _load_json(self.contracts_dir / 'operator-status-bundle-entry.contract.seed.json')

        self.assertEqual(sync_report_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(backfill_report_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(quality_report_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(temporal_worker_bootstrap_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(nightly_run_summary_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(truth_store_snapshot_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(artifact_bridge_summary_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(vertical_slice_summary_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(owner_surface_snapshot_bundle_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(owner_surface_snapshot_cli_bundle_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(operator_status_bundle_contract['status'], 'phase_1_closeout_contract_frozen')
        self.assertEqual(
            sync_report_contract['fields'],
            ['org_id', 'scheduler_runs', 'latest_sync_states', 'service_projection_count'],
        )
        self.assertEqual(
            backfill_report_contract['fields'],
            ['org_id', 'backfill_progress_states', 'remaining_gap_count_total', 'pending_endpoint_count'],
        )
        self.assertEqual(
            quality_report_contract['fields'],
            ['org_id', 'field_coverage_snapshots', 'schema_alignment_snapshots', 'quality_issues', 'quality_issue_count'],
        )
        self.assertEqual(
            temporal_worker_bootstrap_contract['fields'],
            [
                'namespace',
                'task_queue',
                'retry_max_attempts',
                'start_to_close_timeout_seconds',
                'cron_schedule',
                'workflow_names',
                'activity_names',
            ],
        )
        self.assertEqual(
            nightly_run_summary_contract['fields'],
            [
                'request_id',
                'trace_ref',
                'scheduler_trace_ref',
                'workflow_kind',
                'effective_policy',
                'worker_bootstrap',
                'org_count',
                'org_executions',
                'scheduler_runs',
                'ingestion_runs',
                'backfill_progress_states',
                'latest_sync_states',
                'service_projections',
            ],
        )
        self.assertEqual(
            truth_store_snapshot_contract['fields'],
            [
                'scheduler_runs',
                'ingestion_runs',
                'endpoint_runs',
                'page_runs',
                'raw_replay_artifacts',
                'canonical_facts',
                'latest_sync_states',
                'backfill_progress_states',
                'field_coverage_snapshots',
                'schema_alignment_snapshots',
                'quality_issues',
                'capability_readiness_snapshots',
                'service_projections',
            ],
        )
        self.assertEqual(
            artifact_bridge_summary_contract['fields'],
            [
                'request_id',
                'trace_ref',
                'bridge_kind',
                'artifact_root',
                'ingestion_runs',
                'endpoint_runs',
                'page_runs',
                'raw_replay_artifacts',
                'latest_sync_states',
                'service_projections',
            ],
        )
        self.assertEqual(
            vertical_slice_summary_contract['fields'],
            [
                'request_id',
                'trace_ref',
                'transport_kind',
                'capability_id',
                'service_object_id',
                'ingestion_run_status',
                'endpoint_runs',
                'raw_response_pages',
                'transport_replay_artifacts',
                'customer_count',
                'consume_bill_count',
                'latest_usable_endpoint_states',
                'output_dir',
            ],
        )
        self.assertEqual(
            owner_surface_snapshot_bundle_contract['fields'],
            ['state_snapshot', 'readiness_response', 'theme_service_response'],
        )
        self.assertEqual(
            owner_surface_snapshot_cli_bundle_contract['fields'],
            ['state_snapshot', 'readiness_response', 'theme_service_response'],
        )
        self.assertEqual(
            operator_status_bundle_contract['fields'],
            ['request_id', 'trace_ref', 'state_snapshot', 'sync_status', 'backfill_status', 'quality_report'],
        )

    def test_closeout_run_and_state_contracts_freeze_authoritative_fields(self) -> None:
        ingestion_run = _load_json(self.contracts_dir / 'ingestion-run-entry.contract.seed.json')
        endpoint_run = _load_json(self.contracts_dir / 'ingestion-endpoint-run-entry.contract.seed.json')
        raw_response_page = _load_json(self.contracts_dir / 'raw-response-page-entry.contract.seed.json')
        latest_sync_state = _load_json(self.contracts_dir / 'latest-sync-state-entry.contract.seed.json')
        vertical_slice_backbone_state = _load_json(self.contracts_dir / 'vertical-slice-backbone-state-entry.contract.seed.json')
        backfill_progress_state = _load_json(self.contracts_dir / 'backfill-progress-state-entry.contract.seed.json')

        self.assertEqual(ingestion_run['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('scheduler_trace_ref', ingestion_run['fields'])
        self.assertIn('workflow_id', ingestion_run['fields'])
        self.assertIn('task_kind', ingestion_run['fields'])
        self.assertIn('transport_kind', ingestion_run['fields'])

        self.assertEqual(endpoint_run['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('requested_business_date', endpoint_run['fields'])
        self.assertIn('transport_kind', endpoint_run['fields'])
        self.assertIn('error_taxonomy', endpoint_run['fields'])
        self.assertIn('retryable', endpoint_run['fields'])

        self.assertEqual(raw_response_page['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('transport_kind', raw_response_page['fields'])
        self.assertIn('replay_artifact_id', raw_response_page['fields'])
        self.assertIn('source_response_code', raw_response_page['fields'])
        self.assertIn('source_response_message', raw_response_page['fields'])

        self.assertIn('latest_usable_business_date', latest_sync_state['fields'])
        self.assertIn('last_attempted_business_date', latest_sync_state['fields'])
        self.assertIn('last_attempted_status', latest_sync_state['fields'])

        self.assertEqual(vertical_slice_backbone_state['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('backbone_status', vertical_slice_backbone_state['fields'])
        self.assertIn('available_endpoint_contract_ids', vertical_slice_backbone_state['fields'])

        self.assertIn('cursor_business_date', backfill_progress_state['fields'])
        self.assertIn('remaining_gap_count', backfill_progress_state['fields'])
        self.assertIn('last_planned_business_dates', backfill_progress_state['fields'])

    def test_member_insight_fact_contracts_match_postgres_table_keys(self) -> None:
        customer_fact = _load_json(self.contracts_dir / 'member-insight-customer-fact-entry.contract.seed.json')
        customer_card_fact = _load_json(self.contracts_dir / 'member-insight-customer-card-fact-entry.contract.seed.json')
        consume_bill_fact = _load_json(self.contracts_dir / 'member-insight-consume-bill-fact-entry.contract.seed.json')
        consume_bill_payment_fact = _load_json(self.contracts_dir / 'member-insight-consume-bill-payment-fact-entry.contract.seed.json')
        consume_bill_info_fact = _load_json(self.contracts_dir / 'member-insight-consume-bill-info-fact-entry.contract.seed.json')

        self.assertEqual(customer_fact['fields'], ['fact_id', 'fact_trace_ref', 'org_id', 'requested_business_date', 'customer_id', 'payload_json'])
        self.assertEqual(customer_card_fact['fields'], ['fact_id', 'fact_trace_ref', 'org_id', 'requested_business_date', 'customer_card_id', 'payload_json'])
        self.assertEqual(consume_bill_fact['fields'], ['fact_id', 'fact_trace_ref', 'org_id', 'requested_business_date', 'settle_id', 'payload_json'])
        self.assertEqual(consume_bill_payment_fact['fields'], ['fact_id', 'fact_trace_ref', 'org_id', 'requested_business_date', 'settle_id', 'payment_index', 'payload_json'])
        self.assertEqual(consume_bill_info_fact['fields'], ['fact_id', 'fact_trace_ref', 'org_id', 'requested_business_date', 'settle_id', 'info_index', 'payload_json'])

    def test_member_insight_canonical_row_contracts_are_frozen(self) -> None:
        customer_row = _load_json(self.contracts_dir / 'member-insight-customer-canonical-row-entry.contract.seed.json')
        customer_card_row = _load_json(self.contracts_dir / 'member-insight-customer-card-canonical-row-entry.contract.seed.json')
        consume_bill_row = _load_json(self.contracts_dir / 'member-insight-consume-bill-canonical-row-entry.contract.seed.json')
        consume_bill_payment_row = _load_json(self.contracts_dir / 'member-insight-consume-bill-payment-canonical-row-entry.contract.seed.json')
        consume_bill_info_row = _load_json(self.contracts_dir / 'member-insight-consume-bill-info-canonical-row-entry.contract.seed.json')

        self.assertEqual(customer_row['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('customer_id', customer_row['fields'])
        self.assertEqual(customer_card_row['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('customer_card_id', customer_card_row['fields'])
        self.assertEqual(consume_bill_row['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('consume_bill_id', consume_bill_row['fields'])
        self.assertEqual(consume_bill_payment_row['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('payment_sequence', consume_bill_payment_row['fields'])
        self.assertEqual(consume_bill_info_row['status'], 'phase_1_closeout_contract_frozen')
        self.assertIn('info_sequence', consume_bill_info_row['fields'])

    def test_contracts_align_with_closeout_postgres_tables(self) -> None:
        for table_name in {
            'scheduler_run',
            'ingestion_run',
            'ingestion_endpoint_run',
            'ingestion_page_run',
            'raw_replay_artifact',
            'latest_sync_state',
            'backfill_progress_state',
            'field_coverage_snapshot',
            'schema_alignment_snapshot',
            'quality_issue',
            'capability_readiness_snapshot',
            'service_projection',
        }:
            self.assertIn(f'navly_data_platform.{table_name}', self.ddl)

    def test_transitional_artifact_bridge_imports_artifact_tree_into_truth_store(self) -> None:
        fixture_bundle = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        truth_store = PostgresTruthSubstrate()
        with tempfile.TemporaryDirectory() as tmpdir:
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            imported = import_member_insight_artifact_tree_to_truth_store(
                artifact_root=tmpdir,
                truth_store=truth_store,
                workflow_id='navly-migration-artifact-bridge',
                task_kind='artifact_bridge',
            )

        self.assertEqual(imported['bridge_kind'], 'artifact_tree_import')
        snapshot = truth_store.snapshot()
        self.assertEqual(len(snapshot['ingestion_runs']), 1)
        self.assertEqual(len(snapshot['endpoint_runs']), 2)
        self.assertEqual(len(snapshot['page_runs']), 2)
        self.assertEqual(len(snapshot['service_projections']), 1)

    def test_artifact_bridge_cli_smoke(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload['bridge_kind'], 'artifact_tree_import')
        self.assertEqual(payload['ingestion_runs'], 1)
        self.assertEqual(payload['page_runs'], 2)

    def test_artifact_bridge_cli_matches_governed_summary_contract(self) -> None:
        contract = _load_json(self.contracts_dir / 'artifact-bridge-summary-entry.contract.seed.json')
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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

    def test_artifact_bridge_summary_preserves_request_and_trace_refs(self) -> None:
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
            output_dir = Path(tmpdir, 'bridge-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--request-id', 'req-artifact-bridge-custom-001',
                    '--trace-ref', 'navly:trace:artifact-bridge-custom-001',
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(output_dir, 'artifact-bridge-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['request_id'], 'req-artifact-bridge-custom-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:artifact-bridge-custom-001')
        self.assertEqual(summary_file_payload['request_id'], payload['request_id'])
        self.assertEqual(summary_file_payload['trace_ref'], payload['trace_ref'])

    def test_artifact_bridge_cli_writes_summary_file(self) -> None:
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
            output_dir = Path(tmpdir, 'bridge-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(output_dir, 'artifact-bridge-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(summary_file_payload['output_dir'], payload['output_dir'])

    def test_artifact_bridge_summary_file_matches_stdout_when_snapshot_and_output_dir_are_enabled(self) -> None:
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
            output_dir = Path(tmpdir, 'bridge-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(output_dir, 'artifact-bridge-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(summary_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(summary_file_payload['output_dir'], payload['output_dir'])

    def test_artifact_bridge_summary_file_preserves_request_and_trace_when_snapshot_and_output_dir_are_enabled(self) -> None:
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
            output_dir = Path(tmpdir, 'bridge-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--request-id', 'req-artifact-bridge-combined-001',
                    '--trace-ref', 'navly:trace:artifact-bridge-combined-001',
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            summary_file_payload = json.loads(Path(output_dir, 'artifact-bridge-summary.json').read_text(encoding='utf-8'))

        self.assertEqual(summary_file_payload['request_id'], payload['request_id'])
        self.assertEqual(summary_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(summary_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(summary_file_payload['output_dir'], payload['output_dir'])

    def test_artifact_bridge_cli_persists_imported_state_snapshot(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            snapshot_payload = json.loads(snapshot_path.read_text(encoding='utf-8'))

        self.assertEqual(payload['state_snapshot'], str(snapshot_path))
        self.assertTrue(snapshot_payload['ingestion_runs'])

    def test_artifact_bridge_written_snapshot_matches_governed_snapshot_contract(self) -> None:
        contract = _load_json(self.contracts_dir / 'truth-store-snapshot-entry.contract.seed.json')
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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

    def test_artifact_bridge_snapshot_can_feed_status_query_cli(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['sync_status'][0]['org_id'], 'demo-org-001')
        self.assertEqual(len(payload['sync_status'][0]['latest_sync_states']), 2)
        self.assertEqual(payload['backfill_status'][0]['remaining_gap_count_total'], 0)

    def test_artifact_bridge_snapshot_can_feed_operator_status_helper(self) -> None:
        fixture_bundle = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'PYTHONPATH': str(DATA_PLATFORM_ROOT),
                },
            )
            payload = query_operator_status_from_snapshot(
                request_id='req-bridge-helper-001',
                trace_ref='navly:trace:bridge-helper-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-bridge-helper-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:bridge-helper-001')
        self.assertEqual(payload['sync_status'][0]['org_id'], 'demo-org-001')
        self.assertEqual(len(payload['sync_status'][0]['latest_sync_states']), 2)

    def test_artifact_bridge_operator_status_helper_matches_governed_contracts(self) -> None:
        bundle_contract = _load_json(self.contracts_dir / 'operator-status-bundle-entry.contract.seed.json')
        sync_contract = _load_json(self.contracts_dir / 'operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = _load_json(self.contracts_dir / 'operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = _load_json(self.contracts_dir / 'operator-quality-report-entry.contract.seed.json')
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = query_operator_status_from_snapshot(
                request_id='req-bridge-helper-contract-001',
                trace_ref='navly:trace:bridge-helper-contract-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-001'],
            )

        for field_name in bundle_contract['fields']:
            self.assertIn(field_name, payload)
        for report in payload['sync_status']:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['backfill_status']:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in payload['quality_report']:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_artifact_bridge_operator_status_helper_preserves_request_trace_and_org_order(self) -> None:
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
            payload = query_operator_status_from_snapshot(
                request_id='req-bridge-helper-order-001',
                trace_ref='navly:trace:bridge-helper-order-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-bridge-helper-order-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:bridge-helper-order-001')
        self.assertEqual([item['org_id'] for item in payload['sync_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['backfill_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in payload['quality_report']], ['demo-org-002', 'demo-org-001'])

    def test_artifact_bridge_operator_status_helper_multi_org_matches_contracts_and_trace(self) -> None:
        sync_contract = _load_json(self.contracts_dir / 'operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = _load_json(self.contracts_dir / 'operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = _load_json(self.contracts_dir / 'operator-quality-report-entry.contract.seed.json')
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
            payload = query_operator_status_from_snapshot(
                request_id='req-bridge-helper-multi-001',
                trace_ref='navly:trace:bridge-helper-multi-001',
                state_snapshot_path=snapshot_path,
                org_ids=['demo-org-002', 'demo-org-001'],
            )

        self.assertEqual(payload['request_id'], 'req-bridge-helper-multi-001')
        self.assertEqual(payload['trace_ref'], 'navly:trace:bridge-helper-multi-001')
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

    def test_artifact_bridge_can_accumulate_multiple_orgs_into_one_snapshot(self) -> None:
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            output_dir = Path(tmpdir, 'status-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
            bundle_file_payload = _load_json(Path(output_dir, 'operator-status-bundle.json'))

        self.assertEqual(
            [item['org_id'] for item in payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )
        self.assertEqual(len(payload['sync_status'][0]['latest_sync_states']), 2)
        self.assertEqual(len(payload['sync_status'][1]['latest_sync_states']), 2)

    def test_artifact_bridge_multi_org_status_query_report_files_preserve_order_and_contracts(self) -> None:
        sync_contract = _load_json(self.contracts_dir / 'operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = _load_json(self.contracts_dir / 'operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = _load_json(self.contracts_dir / 'operator-quality-report-entry.contract.seed.json')
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            output_dir = Path(tmpdir, 'status-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
            sync_reports = _load_json(Path(output_dir, 'operator-sync-status.json'))
            backfill_reports = _load_json(Path(output_dir, 'operator-backfill-status.json'))
            quality_reports = _load_json(Path(output_dir, 'operator-quality-report.json'))

        self.assertEqual([item['org_id'] for item in sync_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in backfill_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in quality_reports], ['demo-org-002', 'demo-org-001'])
        for report in sync_reports:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in backfill_reports:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in quality_reports:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_artifact_bridge_multi_org_status_query_preserves_order_and_custom_trace_together(self) -> None:
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            output_dir = Path(tmpdir, 'status-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
                    '--request-id', 'req-bridge-status-multi-order-trace-001',
                    '--trace-ref', 'navly:trace:bridge-status-multi-order-trace-001',
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
            bundle_file_payload = _load_json(Path(output_dir, 'operator-status-bundle.json'))
            sync_reports = _load_json(Path(output_dir, 'operator-sync-status.json'))
            backfill_reports = _load_json(Path(output_dir, 'operator-backfill-status.json'))
            quality_reports = _load_json(Path(output_dir, 'operator-quality-report.json'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual([item['org_id'] for item in bundle_file_payload['sync_status']], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in sync_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in backfill_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in quality_reports], ['demo-org-002', 'demo-org-001'])

    def test_artifact_bridge_multi_org_status_query_bundle_preserves_custom_request_and_trace_refs(self) -> None:
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            output_dir = Path(tmpdir, 'status-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
                    '--request-id', 'req-bridge-status-multi-001',
                    '--trace-ref', 'navly:trace:bridge-status-multi-001',
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
            bundle_file_payload = _load_json(Path(output_dir, 'operator-status-bundle.json'))

        self.assertEqual(bundle_file_payload['request_id'], payload['request_id'])
        self.assertEqual(bundle_file_payload['trace_ref'], payload['trace_ref'])
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_artifact_bridge_snapshot_can_feed_status_query_cli_output_file(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(bundle_file_payload['sync_status'][0]['org_id'], 'demo-org-001')

    def test_artifact_bridge_status_query_bundle_file_matches_stdout(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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

        self.assertEqual(bundle_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(bundle_file_payload['sync_status'], payload['sync_status'])
        self.assertEqual(bundle_file_payload['backfill_status'], payload['backfill_status'])
        self.assertEqual(bundle_file_payload['quality_report'], payload['quality_report'])

    def test_artifact_bridge_status_query_report_files_match_stdout_slices(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
            sync_reports = _load_json(Path(output_dir, 'operator-sync-status.json'))
            backfill_reports = _load_json(Path(output_dir, 'operator-backfill-status.json'))
            quality_reports = _load_json(Path(output_dir, 'operator-quality-report.json'))

        self.assertEqual(sync_reports, payload['sync_status'])
        self.assertEqual(backfill_reports, payload['backfill_status'])
        self.assertEqual(quality_reports, payload['quality_report'])

    def test_artifact_bridge_status_query_bundle_preserves_state_snapshot_output_dir_and_org_order(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
            bundle_file_payload = _load_json(Path(output_dir, 'operator-status-bundle.json'))

        self.assertEqual(bundle_file_payload['state_snapshot'], payload['state_snapshot'])
        self.assertEqual(bundle_file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(
            [item['org_id'] for item in bundle_file_payload['sync_status']],
            ['demo-org-002', 'demo-org-001'],
        )

    def test_artifact_bridge_status_query_report_files_preserve_requested_org_order(self) -> None:
        fixture_bundle_org1 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        fixture_bundle_org2 = json.loads(
            (
                DATA_PLATFORM_ROOT
                / 'tests'
                / 'fixtures'
                / 'member_insight'
                / 'qinqin_fixture_pages.bundle.json'
            ).read_text(encoding='utf-8')
        )
        for response in fixture_bundle_org2['qinqin.member.get_customers_list.v1_1']:
            for row in response.get('RetData', {}).get('Data', []) or []:
                row['OrgId'] = 'demo-org-002'
                for card in row.get('Storeds') or []:
                    card['OrgId'] = 'demo-org-002'

        env = dict(os.environ)
        env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir, 'truth-store-snapshot.json')
            artifact_root_org1 = Path(tmpdir, 'artifact-org1')
            artifact_root_org2 = Path(tmpdir, 'artifact-org2')
            output_dir = Path(tmpdir, 'status-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org1),
                output_root=artifact_root_org1,
            )
            run_member_insight_vertical_slice(
                org_id='demo-org-002',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle_org2),
                output_root=artifact_root_org2,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            for artifact_root in (artifact_root_org1, artifact_root_org2):
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
            sync_reports = _load_json(Path(output_dir, 'operator-sync-status.json'))
            backfill_reports = _load_json(Path(output_dir, 'operator-backfill-status.json'))
            quality_reports = _load_json(Path(output_dir, 'operator-quality-report.json'))

        self.assertEqual([item['org_id'] for item in sync_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in backfill_reports], ['demo-org-002', 'demo-org-001'])
        self.assertEqual([item['org_id'] for item in quality_reports], ['demo-org-002', 'demo-org-001'])

    def test_artifact_bridge_status_query_bundle_matches_governed_bundle_contract(self) -> None:
        contract = _load_json(self.contracts_dir / 'operator-status-bundle-entry.contract.seed.json')
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
            payload = _load_json(Path(output_dir, 'operator-status-bundle.json'))

        self.assertEqual(contract['status'], 'phase_1_closeout_contract_frozen')
        for field_name in contract['fields']:
            self.assertIn(field_name, payload)

    def test_artifact_bridge_status_query_reports_match_governed_entry_contracts(self) -> None:
        sync_contract = _load_json(self.contracts_dir / 'operator-sync-status-report-entry.contract.seed.json')
        backfill_contract = _load_json(self.contracts_dir / 'operator-backfill-status-report-entry.contract.seed.json')
        quality_contract = _load_json(self.contracts_dir / 'operator-quality-report-entry.contract.seed.json')
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            query_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_postgres_temporal_status.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
            sync_reports = _load_json(Path(output_dir, 'operator-sync-status.json'))
            backfill_reports = _load_json(Path(output_dir, 'operator-backfill-status.json'))
            quality_reports = _load_json(Path(output_dir, 'operator-quality-report.json'))

        for report in sync_reports:
            for field_name in sync_contract['fields']:
                self.assertIn(field_name, report)
        for report in backfill_reports:
            for field_name in backfill_contract['fields']:
                self.assertIn(field_name, report)
        for report in quality_reports:
            for field_name in quality_contract['fields']:
                self.assertIn(field_name, report)

    def test_artifact_bridge_snapshot_can_feed_owner_surface_cli(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(payload['theme_service_response']['service_status'], 'served')

    def test_artifact_bridge_snapshot_can_feed_owner_surface_cli_output_file(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['theme_service_response']['service_status'], 'served')

    def test_artifact_bridge_owner_surface_response_files_match_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_artifact_bridge_owner_surface_served_outputs_preserve_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-bridge-owner-served-001',
                    '--trace-ref', 'navly:trace:bridge-owner-served-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            bundle_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        self.assertEqual(bundle_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(bundle_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(bundle_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(bundle_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])
        self.assertEqual(readiness_file_payload['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(readiness_file_payload['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(theme_service_file_payload['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(theme_service_file_payload['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_artifact_bridge_owner_surface_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_service_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_artifact_bridge_owner_surface_scope_mismatch_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_artifact_bridge_owner_surface_file_matches_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_served_outputs_omit_explanation_object(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        self.assertNotIn('explanation_object', payload['theme_service_response'])
        self.assertNotIn('explanation_object', file_payload['theme_service_response'])
        self.assertNotIn('explanation_object', theme_service_file_payload)

    def test_artifact_bridge_snapshot_can_feed_owner_surface_cli_scope_mismatch_path(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['theme_service_response']['service_status'], 'scope_mismatch')
        self.assertEqual(file_payload['theme_service_response']['service_status'], 'scope_mismatch')

    def test_artifact_bridge_snapshot_can_feed_owner_surface_cli_missing_projection_path(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['readiness_status'], 'ready')
        self.assertEqual(payload['theme_service_response']['service_status'], 'not_ready')
        self.assertEqual(payload['theme_service_response']['explanation_object']['reason_codes'], ['missing_persisted_projection'])

    def test_artifact_bridge_missing_projection_owner_surface_file_matches_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_artifact_bridge_missing_projection_owner_surface_response_files_match_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_artifact_bridge_missing_projection_owner_surface_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_artifact_bridge_missing_projection_owner_surface_preserves_request_and_trace_ids(self) -> None:
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
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-bridge-owner-missing-projection-001',
                    '--trace-ref', 'navly:trace:bridge-owner-missing-projection-001',
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(payload['readiness_response']['request_id'], 'req-bridge-owner-missing-projection-001')
        self.assertEqual(payload['readiness_response']['trace_ref'], 'navly:trace:bridge-owner-missing-projection-001')
        self.assertEqual(payload['theme_service_response']['request_id'], 'req-bridge-owner-missing-projection-001')
        self.assertEqual(payload['theme_service_response']['trace_ref'], 'navly:trace:bridge-owner-missing-projection-001')

    def test_artifact_bridge_missing_projection_owner_surface_file_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-bridge-owner-missing-projection-bundle-001',
                    '--trace-ref', 'navly:trace:bridge-owner-missing-projection-bundle-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_artifact_bridge_missing_projection_owner_surface_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_artifact_bridge_missing_projection_owner_surface_bundle_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-bridge-owner-missing-projection-bundle-contract-001',
                    '--trace-ref', 'navly:trace:bridge-owner-missing-projection-bundle-contract-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response']['request_id'], 'req-bridge-owner-missing-projection-bundle-contract-001')
        self.assertEqual(file_payload['readiness_response']['trace_ref'], 'navly:trace:bridge-owner-missing-projection-bundle-contract-001')
        self.assertEqual(file_payload['theme_service_response']['request_id'], 'req-bridge-owner-missing-projection-bundle-contract-001')
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], 'navly:trace:bridge-owner-missing-projection-bundle-contract-001')

    def test_artifact_bridge_missing_projection_owner_surface_response_files_preserve_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
                    '--state-snapshot', str(snapshot_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            snapshot_payload = _load_json(snapshot_path)
            snapshot_payload['service_projections'] = []
            snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            subprocess.run(
                [
                    sys.executable,
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--request-id', 'req-bridge-owner-missing-projection-file-001',
                    '--trace-ref', 'navly:trace:bridge-owner-missing-projection-file-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-bridge-owner-missing-projection-file-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:bridge-owner-missing-projection-file-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-bridge-owner-missing-projection-file-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:bridge-owner-missing-projection-file-001')

    def test_artifact_bridge_snapshot_can_feed_owner_surface_cli_scope_mismatch_output_file(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(payload['output_dir'], str(output_dir))
        self.assertEqual(file_payload['output_dir'], payload['output_dir'])
        self.assertEqual(file_payload['readiness_response']['readiness_status'], 'unsupported_scope')
        self.assertEqual(file_payload['theme_service_response']['service_status'], 'scope_mismatch')

    def test_artifact_bridge_owner_surface_scope_mismatch_file_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-bridge-owner-scope-001',
                    '--trace-ref', 'navly:trace:bridge-owner-scope-001',
                    '--output-dir', str(output_dir),
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

    def test_artifact_bridge_owner_surface_scope_mismatch_response_files_preserve_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-bridge-owner-response-001',
                    '--trace-ref', 'navly:trace:bridge-owner-response-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-bridge-owner-response-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:bridge-owner-response-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-bridge-owner-response-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:bridge-owner-response-001')

    def test_artifact_bridge_owner_surface_wrong_service_response_files_preserve_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--request-id', 'req-bridge-owner-wrong-service-response-001',
                    '--trace-ref', 'navly:trace:bridge-owner-wrong-service-response-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload['request_id'], 'req-bridge-owner-wrong-service-response-001')
        self.assertEqual(readiness_file_payload['trace_ref'], 'navly:trace:bridge-owner-wrong-service-response-001')
        self.assertEqual(theme_service_file_payload['request_id'], 'req-bridge-owner-wrong-service-response-001')
        self.assertEqual(theme_service_file_payload['trace_ref'], 'navly:trace:bridge-owner-wrong-service-response-001')

    def test_artifact_bridge_owner_surface_wrong_service_response_files_match_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_service_file_matches_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_service_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_service_file_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--request-id', 'req-bridge-owner-wrong-service-001',
                    '--trace-ref', 'navly:trace:bridge-owner-wrong-service-001',
                    '--output-dir', str(output_dir),
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

    def test_artifact_bridge_owner_surface_wrong_service_bundle_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-service-object-id', 'navly.service.store.daily_overview',
                    '--request-id', 'req-bridge-owner-wrong-service-bundle-001',
                    '--trace-ref', 'navly:trace:bridge-owner-wrong-service-bundle-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_artifact_bridge_owner_surface_wrong_capability_bundle_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-bridge-owner-wrong-capability-bundle-001',
                    '--trace-ref', 'navly:trace:bridge-owner-wrong-capability-bundle-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_artifact_bridge_owner_surface_scope_mismatch_file_matches_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = json.loads(Path(output_dir, 'member-insight-owner-surface.json').read_text(encoding='utf-8'))

        self.assertEqual(file_payload['readiness_response'], payload['readiness_response'])
        self.assertEqual(file_payload['theme_service_response'], payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_scope_mismatch_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_capability_bundle_matches_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, file_payload['readiness_response'])
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, file_payload['theme_service_response'])

    def test_artifact_bridge_owner_surface_wrong_capability_bundle_preserves_request_and_trace_ids(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
                    '--state-snapshot', str(snapshot_path),
                    '--org-id', 'demo-org-001',
                    '--target-business-date', '2026-03-23',
                    '--target-scope-ref', 'navly:scope:store:demo-org-001',
                    '--requested-capability-id', 'navly.store.daily_overview',
                    '--request-id', 'req-bridge-owner-wrong-capability-bundle-001',
                    '--trace-ref', 'navly:trace:bridge-owner-wrong-capability-bundle-001',
                    '--output-dir', str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            file_payload = _load_json(Path(output_dir, 'member-insight-owner-surface.json'))

        self.assertEqual(file_payload['readiness_response']['request_id'], payload['readiness_response']['request_id'])
        self.assertEqual(file_payload['readiness_response']['trace_ref'], payload['readiness_response']['trace_ref'])
        self.assertEqual(file_payload['theme_service_response']['request_id'], payload['theme_service_response']['request_id'])
        self.assertEqual(file_payload['theme_service_response']['trace_ref'], payload['theme_service_response']['trace_ref'])

    def test_artifact_bridge_owner_surface_scope_mismatch_response_files_match_shared_response_contracts(self) -> None:
        readiness_schema = _load_json(self.shared_contracts_dir / 'readiness' / 'capability_readiness_response.schema.json')
        theme_service_schema = _load_json(self.shared_contracts_dir / 'service' / 'theme_service_response.schema.json')
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
                    '--workflow-id', 'navly-migration-artifact-bridge',
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
                    str(owner_surface_script),
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
                env=env,
            )
            readiness_file_payload = _load_json(Path(output_dir, 'member-insight-readiness-response.json'))
            theme_service_file_payload = _load_json(Path(output_dir, 'member-insight-theme-service-response.json'))

        for field_name in readiness_schema['required']:
            self.assertIn(field_name, readiness_file_payload)
        for field_name in theme_service_schema['required']:
            self.assertIn(field_name, theme_service_file_payload)

    def test_artifact_bridge_owner_surface_wrong_capability_response_files_match_stdout(self) -> None:
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
            output_dir = Path(tmpdir, 'owner-surface-output')
            run_member_insight_vertical_slice(
                org_id='demo-org-001',
                start_time='2026-03-20 00:00:00',
                end_time='2026-03-23 23:59:59',
                requested_business_date='2026-03-23',
                app_secret='test-secret',
                transport=FixtureQinqinTransport(fixture_bundle),
                output_root=tmpdir,
            )
            bridge_script = DATA_PLATFORM_ROOT / 'scripts' / 'migrate_member_insight_artifact_tree_to_postgres_truth.py'
            owner_surface_script = DATA_PLATFORM_ROOT / 'scripts' / 'query_member_insight_owner_surface_from_snapshot.py'
            subprocess.run(
                [
                    sys.executable,
                    str(bridge_script),
                    '--artifact-root', tmpdir,
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
                    str(owner_surface_script),
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
                env=env,
            )
            payload = json.loads(completed.stdout)
            readiness_file_payload = json.loads(Path(output_dir, 'member-insight-readiness-response.json').read_text(encoding='utf-8'))
            theme_service_file_payload = json.loads(Path(output_dir, 'member-insight-theme-service-response.json').read_text(encoding='utf-8'))

        self.assertEqual(readiness_file_payload, payload['readiness_response'])
        self.assertEqual(theme_service_file_payload, payload['theme_service_response'])


if __name__ == '__main__':
    unittest.main()
