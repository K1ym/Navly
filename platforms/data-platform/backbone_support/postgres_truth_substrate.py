from __future__ import annotations

import copy
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from completeness.member_insight_readiness_surface import build_member_insight_readiness_response
from ingestion.member_insight_vertical_slice import SOURCE_SYSTEM_ID, VERTICAL_SLICE_CAPABILITY_ID
from serving.member_insight_theme_service_surface import (
    MEMBER_INSIGHT_SERVICE_OBJECT_ID,
    build_member_insight_theme_service_response,
)

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_TRUTH_SCHEMA_PATH = (
    DATA_PLATFORM_ROOT
    / 'migration'
    / 'sql'
    / '2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql'
)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _new_identifier(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:12]}'


def _trace_ref(kind: str, identifier: str) -> str:
    return f'navly:{kind}:{identifier}'


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


class PostgresTruthSubstrate:
    """Repo-local model of the authoritative PostgreSQL truth substrate.

    The tests execute against this in-memory implementation, while the table
    layout is frozen in `migration/sql/...postgres-truth-substrate.sql`.
    """

    def __init__(self, data_platform_root: Path = DATA_PLATFORM_ROOT) -> None:
        self.data_platform_root = data_platform_root
        field_catalog = _load_json(
            data_platform_root / 'directory' / 'endpoint-field-catalog.seed.json'
        )['entries']
        self._field_catalog_entries = {
            entry['endpoint_contract_id']: entry
            for entry in field_catalog
        }
        self.scheduler_runs: list[dict[str, Any]] = []
        self.ingestion_runs: list[dict[str, Any]] = []
        self.endpoint_runs: list[dict[str, Any]] = []
        self.page_runs: list[dict[str, Any]] = []
        self.raw_replay_artifacts: list[dict[str, Any]] = []
        self.canonical_facts: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.latest_sync_states: dict[tuple[str, str], dict[str, Any]] = {}
        self.backfill_progress_states: dict[tuple[str, str], dict[str, Any]] = {}
        self.field_coverage_snapshots: list[dict[str, Any]] = []
        self.schema_alignment_snapshots: list[dict[str, Any]] = []
        self.quality_issues: list[dict[str, Any]] = []
        self.capability_readiness_snapshots: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.service_projections: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._completed_business_dates: dict[tuple[str, str], set[str]] = defaultdict(set)

    def schema_sql(self) -> str:
        return POSTGRES_TRUTH_SCHEMA_PATH.read_text(encoding='utf-8')

    def record_scheduler_run(
        self,
        *,
        workflow_id: str,
        workflow_kind: str,
        scheduler_trace_ref: str,
        org_id: str,
        target_business_date: str,
        planner_mode: str,
        task_queue: str,
        plan_task_count: int,
        failure_budget: int,
    ) -> dict[str, Any]:
        record = {
            'scheduler_run_id': _new_identifier('sr'),
            'scheduler_trace_ref': scheduler_trace_ref,
            'workflow_id': workflow_id,
            'workflow_kind': workflow_kind,
            'org_id': org_id,
            'target_business_date': target_business_date,
            'planner_mode': planner_mode,
            'task_queue': task_queue,
            'scheduler_status': 'running',
            'plan_task_count': plan_task_count,
            'dispatched_task_count': 0,
            'failure_budget': failure_budget,
            'execution_trace_refs': [],
            'started_at': utcnow_iso(),
            'completed_at': None,
        }
        self.scheduler_runs.append(record)
        return copy.deepcopy(record)

    def finalize_scheduler_run(
        self,
        *,
        scheduler_trace_ref: str,
        scheduler_status: str,
        execution_trace_refs: Iterable[str],
        dispatched_task_count: int,
    ) -> dict[str, Any]:
        for record in self.scheduler_runs:
            if record['scheduler_trace_ref'] == scheduler_trace_ref:
                record['scheduler_status'] = scheduler_status
                record['execution_trace_refs'] = list(execution_trace_refs)
                record['dispatched_task_count'] = dispatched_task_count
                record['completed_at'] = utcnow_iso()
                return copy.deepcopy(record)
        raise KeyError(f'Unknown scheduler_trace_ref: {scheduler_trace_ref}')

    def mark_business_date_completed(
        self,
        *,
        org_id: str,
        endpoint_contract_id: str,
        business_date: str,
    ) -> None:
        self._completed_business_dates[(org_id, endpoint_contract_id)].add(business_date)

    def completed_business_dates(
        self,
        *,
        org_id: str,
        endpoint_contract_id: str,
        up_to_business_date: str | None = None,
    ) -> tuple[str, ...]:
        dates = {
            business_date
            for business_date in self._completed_business_dates.get((org_id, endpoint_contract_id), set())
            if up_to_business_date is None or business_date <= up_to_business_date
        }
        return tuple(sorted(dates, reverse=True))

    def get_latest_sync_state(
        self,
        *,
        org_id: str,
        endpoint_contract_id: str,
    ) -> dict[str, Any] | None:
        state = self.latest_sync_states.get((org_id, endpoint_contract_id))
        return copy.deepcopy(state) if state is not None else None

    def get_backfill_progress_state(
        self,
        *,
        org_id: str,
        endpoint_contract_id: str,
    ) -> dict[str, Any] | None:
        state = self.backfill_progress_states.get((org_id, endpoint_contract_id))
        return copy.deepcopy(state) if state is not None else None

    def upsert_backfill_progress_state(
        self,
        *,
        capability_id: str,
        org_id: str,
        endpoint_contract_id: str,
        target_business_date: str,
        planner_mode: str,
        cursor_business_date: str | None,
        newest_missing_business_date: str | None,
        oldest_missing_business_date: str | None,
        remaining_gap_count: int,
        last_planned_business_dates: Iterable[str],
        scheduler_trace_ref: str | None,
        progress_status: str,
    ) -> dict[str, Any]:
        key = (org_id, endpoint_contract_id)
        existing = self.backfill_progress_states.get(key)
        state_id = existing['state_id'] if existing else f'{endpoint_contract_id}::{org_id}'
        state_trace_ref = _trace_ref('state-trace:backfill-progress', _new_identifier('bps'))
        record = {
            'state_id': state_id,
            'state_trace_ref': state_trace_ref,
            'capability_id': capability_id,
            'endpoint_contract_id': endpoint_contract_id,
            'org_id': org_id,
            'target_business_date': target_business_date,
            'planner_mode': planner_mode,
            'cursor_business_date': cursor_business_date,
            'newest_missing_business_date': newest_missing_business_date,
            'oldest_missing_business_date': oldest_missing_business_date,
            'remaining_gap_count': remaining_gap_count,
            'last_planned_business_dates': list(last_planned_business_dates),
            'scheduler_trace_ref': scheduler_trace_ref,
            'progress_status': progress_status,
            'updated_at': utcnow_iso(),
        }
        self.backfill_progress_states[key] = record
        return copy.deepcopy(record)

    def reconcile_backfill_progress(
        self,
        *,
        capability_id: str,
        org_id: str,
        endpoint_contract_ids: Iterable[str],
        expected_business_dates: Iterable[str],
        target_business_date: str,
        planner_mode: str,
        scheduler_trace_ref: str | None,
    ) -> list[dict[str, Any]]:
        backfill_candidates = sorted(
            [business_date for business_date in expected_business_dates if business_date < target_business_date],
            reverse=True,
        )
        reconciled: list[dict[str, Any]] = []
        for endpoint_contract_id in endpoint_contract_ids:
            completed = set(
                self.completed_business_dates(
                    org_id=org_id,
                    endpoint_contract_id=endpoint_contract_id,
                    up_to_business_date=target_business_date,
                )
            )
            remaining = [business_date for business_date in backfill_candidates if business_date not in completed]
            reconciled.append(
                self.upsert_backfill_progress_state(
                    capability_id=capability_id,
                    org_id=org_id,
                    endpoint_contract_id=endpoint_contract_id,
                    target_business_date=target_business_date,
                    planner_mode=planner_mode,
                    cursor_business_date=remaining[0] if remaining else None,
                    newest_missing_business_date=remaining[0] if remaining else None,
                    oldest_missing_business_date=remaining[-1] if remaining else None,
                    remaining_gap_count=len(remaining),
                    last_planned_business_dates=[],
                    scheduler_trace_ref=scheduler_trace_ref,
                    progress_status='backfill_pending' if remaining else 'backfill_complete',
                )
            )
        return reconciled

    def _documented_field_paths(self, endpoint_contract_id: str) -> list[str]:
        entry = self._field_catalog_entries.get(endpoint_contract_id) or {}
        return [field['field_path'] for field in entry.get('response_fields', [])]

    def _append_canonical_rows(
        self,
        *,
        fact_kind: str,
        org_id: str,
        requested_business_date: str,
        rows: Iterable[dict[str, Any]],
    ) -> None:
        def field_value(payload: dict[str, Any], *keys: str) -> Any:
            for key in keys:
                if key in payload:
                    return payload[key]
            field_values = payload.get('field_values') if isinstance(payload.get('field_values'), dict) else {}
            for key in keys:
                if key in field_values:
                    return field_values[key]
            return None

        for row in rows:
            payload = copy.deepcopy(row)
            record = {
                'fact_id': _new_identifier('fact'),
                'fact_trace_ref': _trace_ref(f'fact-trace:{fact_kind}', _new_identifier('fact')),
                'org_id': org_id,
                'requested_business_date': requested_business_date,
                'payload_json': payload,
            }
            if fact_kind == 'customer':
                customer_id = field_value(payload, 'customer_id', 'Data__Id')
                if customer_id is None:
                    raise KeyError('customer_id')
                record['customer_id'] = str(customer_id)
            elif fact_kind == 'customer_card':
                customer_card_id = field_value(
                    payload,
                    'customer_card_id',
                    'Data__Storeds__Id',
                    'Data__Equitys__Id',
                )
                if customer_card_id is None:
                    raise KeyError('customer_card_id')
                record['customer_card_id'] = str(customer_card_id)
            elif fact_kind == 'consume_bill':
                settle_id = field_value(payload, 'consume_bill_id', 'Data__SettleId')
                if settle_id is None:
                    raise KeyError('consume_bill_id')
                record['settle_id'] = str(settle_id)
            elif fact_kind == 'consume_bill_payment':
                settle_id = field_value(payload, 'consume_bill_id', 'Data__SettleId')
                payment_index = field_value(payload, 'payment_sequence', 'Data__Payments__PaymentIndex')
                if settle_id is None:
                    raise KeyError('consume_bill_id')
                record['settle_id'] = str(settle_id)
                record['payment_index'] = int(payment_index or 0)
            elif fact_kind == 'consume_bill_info':
                settle_id = field_value(payload, 'consume_bill_id', 'Data__SettleId')
                info_index = field_value(payload, 'info_sequence', 'Data__Infos__InfoIndex')
                if settle_id is None:
                    raise KeyError('consume_bill_id')
                record['settle_id'] = str(settle_id)
                record['info_index'] = int(info_index or 0)
            else:
                raise KeyError(f'Unsupported fact_kind: {fact_kind}')
            self.canonical_facts[fact_kind].append(record)

    def _update_latest_sync_state(
        self,
        *,
        org_id: str,
        requested_business_date: str,
        endpoint_run: dict[str, Any],
        endpoint_state: dict[str, Any],
    ) -> dict[str, Any]:
        key = (org_id, endpoint_run['endpoint_contract_id'])
        existing = self.latest_sync_states.get(key)
        state_id = existing['state_id'] if existing else f"{endpoint_run['endpoint_contract_id']}::{org_id}"
        current_latest = existing.get('latest_usable_business_date') if existing else None
        candidate_latest = endpoint_state.get('latest_usable_business_date')
        state_trace_ref = _trace_ref('state-trace:latest-sync', _new_identifier('lss'))
        latest_usable_business_date = current_latest
        availability_status = existing['availability_status'] if existing else 'unavailable'
        latest_run_trace_ref = existing.get('latest_run_trace_ref') if existing else None
        latest_endpoint_run_id = existing.get('latest_endpoint_run_id') if existing else None
        latest_endpoint_status = existing.get('latest_endpoint_status') if existing else None

        if candidate_latest is not None and (current_latest is None or candidate_latest >= current_latest):
            latest_usable_business_date = candidate_latest
            availability_status = endpoint_state['availability_status']
            latest_run_trace_ref = endpoint_state['latest_run_trace_ref']
            latest_endpoint_run_id = endpoint_state['latest_endpoint_run_id']
            latest_endpoint_status = endpoint_state['latest_endpoint_status']

        record = {
            'state_id': state_id,
            'state_trace_ref': state_trace_ref,
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'source_system_id': SOURCE_SYSTEM_ID,
            'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
            'org_id': org_id,
            'latest_usable_business_date': latest_usable_business_date,
            'availability_status': availability_status,
            'latest_run_trace_ref': latest_run_trace_ref,
            'latest_endpoint_run_id': latest_endpoint_run_id,
            'latest_endpoint_status': latest_endpoint_status,
            'last_attempted_business_date': requested_business_date,
            'last_attempted_status': endpoint_run['endpoint_status'],
            'last_attempted_run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
            'updated_at': utcnow_iso(),
        }
        self.latest_sync_states[key] = record
        return copy.deepcopy(record)

    def persist_vertical_slice_result(
        self,
        *,
        org_id: str,
        target_scope_ref: str,
        target_business_date: str,
        vertical_slice_result: dict[str, Any],
        scheduler_trace_ref: str | None = None,
        workflow_id: str | None = None,
        task_kind: str = 'currentness',
    ) -> dict[str, Any]:
        historical_run_truth = vertical_slice_result['historical_run_truth']
        ingestion_run = copy.deepcopy(historical_run_truth['ingestion_run'])
        ingestion_run.update({
            'scheduler_trace_ref': scheduler_trace_ref,
            'workflow_id': workflow_id,
            'task_kind': task_kind,
            'transport_kind': vertical_slice_result.get('transport_kind'),
        })
        self.ingestion_runs.append(ingestion_run)

        endpoint_runs_by_id: dict[str, dict[str, Any]] = {}
        for endpoint_run in historical_run_truth['endpoint_runs']:
            persisted_endpoint_run = copy.deepcopy(endpoint_run)
            persisted_endpoint_run.update({
                'requested_business_date': target_business_date,
                'transport_kind': vertical_slice_result.get('transport_kind'),
            })
            self.endpoint_runs.append(persisted_endpoint_run)
            endpoint_runs_by_id[persisted_endpoint_run['endpoint_run_id']] = persisted_endpoint_run
            if persisted_endpoint_run['endpoint_status'] in {'completed', 'source_empty'}:
                self.mark_business_date_completed(
                    org_id=org_id,
                    endpoint_contract_id=persisted_endpoint_run['endpoint_contract_id'],
                    business_date=target_business_date,
                )

        raw_pages = list(vertical_slice_result['raw_replay']['raw_response_pages'])
        transport_replay_artifacts = list(vertical_slice_result['raw_replay']['transport_replay_artifacts'])
        for raw_page_record, replay_artifact in zip(raw_pages, transport_replay_artifacts):
            replay_record = copy.deepcopy(replay_artifact)
            replay_record.update({
                'replay_trace_ref': _trace_ref('replay-trace', _new_identifier('rra')),
                'endpoint_run_id': raw_page_record['endpoint_run_id'],
                'endpoint_contract_id': raw_page_record['endpoint_contract_id'],
                'requested_business_date': target_business_date,
                'page_index': raw_page_record['page_index'],
                'captured_at': raw_page_record['captured_at'],
            })
            self.raw_replay_artifacts.append(replay_record)
            self.page_runs.append({
                'page_run_id': _new_identifier('pr'),
                'page_run_trace_ref': _trace_ref('run-trace:page', _new_identifier('pr')),
                'endpoint_run_id': raw_page_record['endpoint_run_id'],
                'endpoint_contract_id': raw_page_record['endpoint_contract_id'],
                'page_index': raw_page_record['page_index'],
                'replay_artifact_id': replay_record['replay_artifact_id'],
                'response_record_count': raw_page_record['response_record_count'],
                'page_status': 'captured',
                'captured_at': raw_page_record['captured_at'],
            })

        for fact_kind, rows in vertical_slice_result['canonical_artifacts'].items():
            self._append_canonical_rows(
                fact_kind=fact_kind,
                org_id=org_id,
                requested_business_date=target_business_date,
                rows=rows,
            )

        updated_latest_states: list[dict[str, Any]] = []
        for endpoint_state in vertical_slice_result['latest_state_artifacts']['latest_usable_endpoint_states']:
            endpoint_run = endpoint_runs_by_id[endpoint_state['latest_endpoint_run_id']]
            updated_latest_states.append(
                self._update_latest_sync_state(
                    org_id=org_id,
                    requested_business_date=target_business_date,
                    endpoint_run=endpoint_run,
                    endpoint_state=endpoint_state,
                )
            )

        for endpoint_run in historical_run_truth['endpoint_runs']:
            documented_field_paths = self._documented_field_paths(endpoint_run['endpoint_contract_id'])
            documented_field_count = len(documented_field_paths)
            is_success = endpoint_run['endpoint_status'] in {'completed', 'source_empty'}
            missing_field_paths = [] if is_success else documented_field_paths
            coverage_snapshot = {
                'snapshot_id': _new_identifier('fcs'),
                'snapshot_trace_ref': _trace_ref('state-trace:field-coverage', _new_identifier('fcs')),
                'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
                'org_id': org_id,
                'requested_business_date': target_business_date,
                'documented_field_count': documented_field_count,
                'observed_field_count': documented_field_count if is_success else 0,
                'missing_field_paths': missing_field_paths,
                'coverage_status': 'complete' if is_success else 'missing',
                'endpoint_run_id': endpoint_run['endpoint_run_id'],
                'run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
                'updated_at': utcnow_iso(),
            }
            self.field_coverage_snapshots.append(coverage_snapshot)

            schema_alignment_snapshot = {
                'snapshot_id': _new_identifier('sas'),
                'snapshot_trace_ref': _trace_ref('state-trace:schema-alignment', _new_identifier('sas')),
                'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
                'org_id': org_id,
                'requested_business_date': target_business_date,
                'alignment_status': 'aligned' if is_success else 'source_failed',
                'mismatch_count': 0 if is_success else documented_field_count,
                'mismatch_details': [] if is_success else [{
                    'reason': endpoint_run.get('error_taxonomy') or 'endpoint_failed',
                    'endpoint_status': endpoint_run['endpoint_status'],
                }],
                'endpoint_run_id': endpoint_run['endpoint_run_id'],
                'run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
                'updated_at': utcnow_iso(),
            }
            self.schema_alignment_snapshots.append(schema_alignment_snapshot)

            if endpoint_run['endpoint_status'] not in {'completed', 'source_empty'}:
                self.quality_issues.append({
                    'quality_issue_id': _new_identifier('qi'),
                    'issue_trace_ref': _trace_ref('issue-trace:quality', _new_identifier('qi')),
                    'endpoint_contract_id': endpoint_run['endpoint_contract_id'],
                    'org_id': org_id,
                    'requested_business_date': target_business_date,
                    'quality_code': endpoint_run.get('error_taxonomy') or 'endpoint_failed',
                    'severity': 'error',
                    'message': endpoint_run.get('error_message') or 'Endpoint execution failed.',
                    'run_trace_ref': endpoint_run['endpoint_run_trace_ref'],
                    'state_trace_ref': schema_alignment_snapshot['snapshot_trace_ref'],
                    'opened_at': utcnow_iso(),
                })

        readiness_response = build_member_insight_readiness_response(
            request_id=vertical_slice_result['request_id'],
            trace_ref=vertical_slice_result['trace_ref'],
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            vertical_slice_result=vertical_slice_result,
        )
        readiness_snapshot = {
            'snapshot_id': _new_identifier('crs'),
            'state_trace_ref': _trace_ref('state-trace:capability-readiness', _new_identifier('crs')),
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'org_id': org_id,
            'requested_business_date': target_business_date,
            'latest_usable_business_date': readiness_response['latest_usable_business_date'],
            'readiness_status': readiness_response['readiness_status'],
            'reason_codes': list(readiness_response['reason_codes']),
            'blocking_dependencies': copy.deepcopy(readiness_response['blocking_dependencies']),
            'run_trace_refs': list(readiness_response['run_trace_refs']),
            'state_trace_refs': list(readiness_response['state_trace_refs']),
            'evaluated_at': readiness_response['evaluated_at'],
        }
        self.capability_readiness_snapshots[
            (org_id, target_business_date, VERTICAL_SLICE_CAPABILITY_ID)
        ] = readiness_snapshot

        service_response = build_member_insight_theme_service_response(
            request_id=vertical_slice_result['request_id'],
            trace_ref=vertical_slice_result['trace_ref'],
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            readiness_response=readiness_response,
            vertical_slice_result=vertical_slice_result,
            requested_service_object_id=MEMBER_INSIGHT_SERVICE_OBJECT_ID,
        )
        service_projection = {
            'projection_id': _new_identifier('proj'),
            'projection_trace_ref': _trace_ref('projection-trace:service', _new_identifier('proj')),
            'capability_id': VERTICAL_SLICE_CAPABILITY_ID,
            'service_object_id': MEMBER_INSIGHT_SERVICE_OBJECT_ID,
            'org_id': org_id,
            'requested_business_date': target_business_date,
            'latest_usable_business_date': readiness_response['latest_usable_business_date'],
            'service_status': service_response['service_status'],
            'service_object': copy.deepcopy(service_response['service_object']),
            'explanation_object': copy.deepcopy(service_response.get('explanation_object') or {}),
            'run_trace_refs': list(service_response['run_trace_refs']),
            'state_trace_refs': list(service_response['state_trace_refs']),
            'served_at': service_response['served_at'],
        }
        self.service_projections[
            (org_id, target_business_date, MEMBER_INSIGHT_SERVICE_OBJECT_ID)
        ] = service_projection

        return {
            'ingestion_run': copy.deepcopy(ingestion_run),
            'latest_sync_states': copy.deepcopy(updated_latest_states),
            'capability_readiness_snapshot': copy.deepcopy(readiness_snapshot),
            'service_projection': copy.deepcopy(service_projection),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            'scheduler_runs': copy.deepcopy(self.scheduler_runs),
            'ingestion_runs': copy.deepcopy(self.ingestion_runs),
            'endpoint_runs': copy.deepcopy(self.endpoint_runs),
            'page_runs': copy.deepcopy(self.page_runs),
            'raw_replay_artifacts': copy.deepcopy(self.raw_replay_artifacts),
            'canonical_facts': copy.deepcopy(dict(self.canonical_facts)),
            'latest_sync_states': copy.deepcopy(list(self.latest_sync_states.values())),
            'backfill_progress_states': copy.deepcopy(list(self.backfill_progress_states.values())),
            'field_coverage_snapshots': copy.deepcopy(self.field_coverage_snapshots),
            'schema_alignment_snapshots': copy.deepcopy(self.schema_alignment_snapshots),
            'quality_issues': copy.deepcopy(self.quality_issues),
            'capability_readiness_snapshots': copy.deepcopy(list(self.capability_readiness_snapshots.values())),
            'service_projections': copy.deepcopy(list(self.service_projections.values())),
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
        *,
        data_platform_root: Path = DATA_PLATFORM_ROOT,
    ) -> 'PostgresTruthSubstrate':
        store = cls(data_platform_root=data_platform_root)
        store.scheduler_runs = copy.deepcopy(list(snapshot.get('scheduler_runs', [])))
        store.ingestion_runs = copy.deepcopy(list(snapshot.get('ingestion_runs', [])))
        store.endpoint_runs = copy.deepcopy(list(snapshot.get('endpoint_runs', [])))
        store.page_runs = copy.deepcopy(list(snapshot.get('page_runs', [])))
        store.raw_replay_artifacts = copy.deepcopy(list(snapshot.get('raw_replay_artifacts', [])))
        store.canonical_facts = defaultdict(
            list,
            {
                fact_kind: copy.deepcopy(list(rows))
                for fact_kind, rows in dict(snapshot.get('canonical_facts', {})).items()
            },
        )
        store.latest_sync_states = {
            (record['org_id'], record['endpoint_contract_id']): copy.deepcopy(record)
            for record in snapshot.get('latest_sync_states', [])
        }
        store.backfill_progress_states = {
            (record['org_id'], record['endpoint_contract_id']): copy.deepcopy(record)
            for record in snapshot.get('backfill_progress_states', [])
        }
        store.field_coverage_snapshots = copy.deepcopy(list(snapshot.get('field_coverage_snapshots', [])))
        store.schema_alignment_snapshots = copy.deepcopy(list(snapshot.get('schema_alignment_snapshots', [])))
        store.quality_issues = copy.deepcopy(list(snapshot.get('quality_issues', [])))
        store.capability_readiness_snapshots = {
            (record['org_id'], record['requested_business_date'], record['capability_id']): copy.deepcopy(record)
            for record in snapshot.get('capability_readiness_snapshots', [])
        }
        store.service_projections = {
            (record['org_id'], record['requested_business_date'], record['service_object_id']): copy.deepcopy(record)
            for record in snapshot.get('service_projections', [])
        }
        for record in store.endpoint_runs:
            if record['endpoint_status'] in {'completed', 'source_empty'}:
                store.mark_business_date_completed(
                    org_id=record['org_id'],
                    endpoint_contract_id=record['endpoint_contract_id'],
                    business_date=record['requested_business_date'],
                )
        for record in store.latest_sync_states.values():
            latest_usable_business_date = record.get('latest_usable_business_date')
            if latest_usable_business_date:
                store.mark_business_date_completed(
                    org_id=record['org_id'],
                    endpoint_contract_id=record['endpoint_contract_id'],
                    business_date=latest_usable_business_date,
                )
        return store

    @classmethod
    def from_snapshot_file(
        cls,
        snapshot_path: str | Path,
        *,
        data_platform_root: Path = DATA_PLATFORM_ROOT,
    ) -> 'PostgresTruthSubstrate':
        path = Path(snapshot_path)
        if not path.exists():
            return cls(data_platform_root=data_platform_root)
        return cls.from_snapshot(
            json.loads(path.read_text(encoding='utf-8')),
            data_platform_root=data_platform_root,
        )

    def write_snapshot_file(self, snapshot_path: str | Path) -> Path:
        path = Path(snapshot_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return path

    def build_sync_status_report(self, *, org_id: str) -> dict[str, Any]:
        scheduler_runs = [
            copy.deepcopy(record)
            for record in self.scheduler_runs
            if record['org_id'] == org_id
        ]
        scheduler_runs.sort(key=lambda item: (item['target_business_date'], item['started_at']), reverse=True)
        latest_sync_states = [
            copy.deepcopy(record)
            for record in self.latest_sync_states.values()
            if record['org_id'] == org_id
        ]
        latest_sync_states.sort(key=lambda item: item['endpoint_contract_id'])
        return {
            'org_id': org_id,
            'scheduler_runs': scheduler_runs,
            'latest_sync_states': latest_sync_states,
            'service_projection_count': sum(
                1 for record in self.service_projections.values()
                if record['org_id'] == org_id
            ),
        }

    def build_backfill_status_report(self, *, org_id: str) -> dict[str, Any]:
        backfill_progress_states = [
            copy.deepcopy(record)
            for record in self.backfill_progress_states.values()
            if record['org_id'] == org_id
        ]
        backfill_progress_states.sort(key=lambda item: item['endpoint_contract_id'])
        return {
            'org_id': org_id,
            'backfill_progress_states': backfill_progress_states,
            'remaining_gap_count_total': sum(
                int(record['remaining_gap_count'])
                for record in backfill_progress_states
            ),
            'pending_endpoint_count': sum(
                1 for record in backfill_progress_states
                if record['progress_status'] != 'backfill_complete'
            ),
        }

    def build_quality_report(self, *, org_id: str) -> dict[str, Any]:
        field_coverage_snapshots = [
            copy.deepcopy(record)
            for record in self.field_coverage_snapshots
            if record['org_id'] == org_id
        ]
        schema_alignment_snapshots = [
            copy.deepcopy(record)
            for record in self.schema_alignment_snapshots
            if record['org_id'] == org_id
        ]
        quality_issues = [
            copy.deepcopy(record)
            for record in self.quality_issues
            if record['org_id'] == org_id
        ]
        return {
            'org_id': org_id,
            'field_coverage_snapshots': field_coverage_snapshots,
            'schema_alignment_snapshots': schema_alignment_snapshots,
            'quality_issues': quality_issues,
            'quality_issue_count': len(quality_issues),
        }
