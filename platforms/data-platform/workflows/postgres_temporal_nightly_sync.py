from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate
from ingestion.member_insight_vertical_slice import VERTICAL_SLICE_CAPABILITY_ID, run_member_insight_vertical_slice
from serving.member_insight_theme_service_surface import MEMBER_INSIGHT_SERVICE_OBJECT_ID

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _utcnow_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _new_identifier(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:12]}'


def _trace_ref(kind: str, identifier: str) -> str:
    return f'navly:{kind}:{identifier}'


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def load_nightly_sync_policy_entry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    registry = _load_json(data_platform_root / 'directory' / 'nightly-sync-policy.seed.json')
    entries = list(registry.get('entries', []))
    if not entries:
        raise KeyError(f'Missing nightly sync policy entry for {VERTICAL_SLICE_CAPABILITY_ID}')

    entry = entries[0]
    activation_local_time = str(entry.get('activation_local_time') or '03:10')
    activation_hour, activation_minute = activation_local_time.split(':', 1)
    return {
        **entry,
        'planner_mode': entry.get('planner_mode') or 'currentness_first',
        'backfill_order': entry.get('backfill_order') or entry.get('backfill_fill_direction') or 'latest_to_oldest',
        'cursor_mode': entry.get('cursor_mode') or ('carry_forward_cursor' if entry.get('carry_forward_cursor', True) else 'reset_cursor'),
        'max_backfill_tasks_per_run': entry.get('max_backfill_tasks_per_run') or 3,
        'task_queue': entry.get('task_queue') or 'navly-data-platform-nightly',
        'retry_max_attempts': entry.get('retry_max_attempts') or 3,
        'start_to_close_timeout_seconds': entry.get('start_to_close_timeout_seconds') or 300,
        'cron_schedule': entry.get('cron_schedule') or f'{activation_minute} {activation_hour} * * *',
    }


def _member_insight_endpoint_contract_ids(data_platform_root: Path = DATA_PLATFORM_ROOT) -> tuple[str, ...]:
    dependency_registry = _load_json(
        data_platform_root / 'directory' / 'capability-dependency-registry.seed.json'
    )
    for entry in dependency_registry['entries']:
        if entry['capability_id'] == VERTICAL_SLICE_CAPABILITY_ID:
            return tuple(
                entry.get('endpoint_contract_ids')
                or entry.get('required_endpoint_contract_ids')
                or []
            )
    raise KeyError(f'Missing dependency entry for {VERTICAL_SLICE_CAPABILITY_ID}')


def build_expected_business_dates(
    *,
    backfill_start_business_date: str,
    target_business_date: str,
) -> tuple[str, ...]:
    current_date = date.fromisoformat(backfill_start_business_date)
    target_date = date.fromisoformat(target_business_date)
    expected_dates: list[str] = []
    while current_date <= target_date:
        expected_dates.append(current_date.isoformat())
        current_date += timedelta(days=1)
    return tuple(expected_dates)


def business_date_window(business_date: str) -> tuple[str, str]:
    return f'{business_date} 00:00:00', f'{business_date} 23:59:59'


def _workflow_status(run_statuses: Iterable[str]) -> str:
    statuses = set(run_statuses)
    if not statuses:
        return 'failed'
    if statuses.issubset({'completed'}):
        return 'completed'
    if 'completed' in statuses:
        return 'partial_failed'
    return 'failed'


@dataclass(frozen=True)
class NightlyPlannerPolicy:
    backfill_start_business_date: str
    planner_mode: str
    backfill_order: str
    cursor_mode: str
    max_backfill_tasks_per_run: int

    @classmethod
    def from_registry(
        cls,
        *,
        backfill_start_business_date: str,
        data_platform_root: Path = DATA_PLATFORM_ROOT,
        max_backfill_tasks_per_run: int | None = None,
    ) -> 'NightlyPlannerPolicy':
        entry = load_nightly_sync_policy_entry(data_platform_root=data_platform_root)
        return cls(
            backfill_start_business_date=backfill_start_business_date,
            planner_mode=entry['planner_mode'],
            backfill_order=entry['backfill_order'],
            cursor_mode=entry['cursor_mode'],
            max_backfill_tasks_per_run=max_backfill_tasks_per_run or int(entry['max_backfill_tasks_per_run']),
        )


@dataclass(frozen=True)
class NightlySyncTask:
    task_id: str
    task_kind: str
    org_id: str
    business_date: str
    triggered_by_endpoint_contract_ids: tuple[str, ...]
    scheduler_trace_ref: str
    workflow_id: str
    task_queue: str
    planner_mode: str
    carry_forward_from_business_date: str | None = None


@dataclass(frozen=True)
class NightlySyncPlan:
    scheduler_trace_ref: str
    workflow_id: str
    org_id: str
    target_business_date: str
    planner_mode: str
    task_queue: str
    expected_business_dates: tuple[str, ...]
    currentness_task: NightlySyncTask
    backfill_tasks: tuple[NightlySyncTask, ...]
    endpoint_gap_map: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class TemporalWorkerBootstrap:
    namespace: str
    task_queue: str
    retry_max_attempts: int
    start_to_close_timeout_seconds: int
    cron_schedule: str

    @classmethod
    def from_registry(
        cls,
        *,
        data_platform_root: Path = DATA_PLATFORM_ROOT,
        namespace: str = 'navly-data-platform',
    ) -> 'TemporalWorkerBootstrap':
        entry = load_nightly_sync_policy_entry(data_platform_root=data_platform_root)
        return cls(
            namespace=namespace,
            task_queue=entry['task_queue'],
            retry_max_attempts=int(entry['retry_max_attempts']),
            start_to_close_timeout_seconds=int(entry['start_to_close_timeout_seconds']),
            cron_schedule=entry['cron_schedule'],
        )

    def to_record(self) -> dict[str, Any]:
        return {
            'namespace': self.namespace,
            'task_queue': self.task_queue,
            'retry_max_attempts': self.retry_max_attempts,
            'start_to_close_timeout_seconds': self.start_to_close_timeout_seconds,
            'cron_schedule': self.cron_schedule,
            'workflow_names': [
                'NightlySchedulerWorkflow',
                'NightlyExecutionWorkflow',
                'RetryWorkflow',
                'RerunWorkflow',
                'BackfillWorkflow',
            ],
            'activity_names': [
                'run_member_insight_vertical_slice',
                'persist_postgres_truth_substrate',
                'reconcile_backfill_progress',
            ],
        }


class NightlySyncPlanner:
    def __init__(
        self,
        *,
        truth_store: PostgresTruthSubstrate,
        policy: NightlyPlannerPolicy,
        endpoint_contract_ids: Sequence[str] | None = None,
    ) -> None:
        self.truth_store = truth_store
        self.policy = policy
        self.endpoint_contract_ids = tuple(endpoint_contract_ids or _member_insight_endpoint_contract_ids())

    def build_plan(
        self,
        *,
        org_id: str,
        target_business_date: str,
        scheduler_trace_ref: str,
        workflow_id: str,
        task_queue: str,
    ) -> NightlySyncPlan:
        expected_business_dates = build_expected_business_dates(
            backfill_start_business_date=self.policy.backfill_start_business_date,
            target_business_date=target_business_date,
        )
        self.truth_store.reconcile_backfill_progress(
            capability_id=VERTICAL_SLICE_CAPABILITY_ID,
            org_id=org_id,
            endpoint_contract_ids=self.endpoint_contract_ids,
            expected_business_dates=expected_business_dates,
            target_business_date=target_business_date,
            planner_mode=self.policy.planner_mode,
            scheduler_trace_ref=scheduler_trace_ref,
        )

        endpoint_gap_map: dict[str, tuple[str, ...]] = {}
        gap_union: set[str] = set()
        descending_dates = tuple(
            sorted(
                [business_date for business_date in expected_business_dates if business_date < target_business_date],
                reverse=True,
            )
        )

        for endpoint_contract_id in self.endpoint_contract_ids:
            completed_dates = set(
                self.truth_store.completed_business_dates(
                    org_id=org_id,
                    endpoint_contract_id=endpoint_contract_id,
                    up_to_business_date=target_business_date,
                )
            )
            candidate_gaps = [business_date for business_date in descending_dates if business_date not in completed_dates]
            progress_state = self.truth_store.get_backfill_progress_state(
                org_id=org_id,
                endpoint_contract_id=endpoint_contract_id,
            )
            cursor_business_date = progress_state['cursor_business_date'] if progress_state else None
            if cursor_business_date:
                candidate_gaps = [
                    business_date for business_date in candidate_gaps
                    if business_date <= cursor_business_date
                ]
            endpoint_gap_map[endpoint_contract_id] = tuple(candidate_gaps)
            gap_union.update(candidate_gaps)

        selected_backfill_dates = tuple(
            sorted(gap_union, reverse=True)[: self.policy.max_backfill_tasks_per_run]
        )

        currentness_task = NightlySyncTask(
            task_id=_new_identifier('task'),
            task_kind='currentness',
            org_id=org_id,
            business_date=target_business_date,
            triggered_by_endpoint_contract_ids=self.endpoint_contract_ids,
            scheduler_trace_ref=scheduler_trace_ref,
            workflow_id=workflow_id,
            task_queue=task_queue,
            planner_mode=self.policy.planner_mode,
        )
        backfill_tasks: list[NightlySyncTask] = []
        selected_date_set = set(selected_backfill_dates)
        for business_date in selected_backfill_dates:
            triggering_endpoints = tuple(
                endpoint_contract_id
                for endpoint_contract_id, gaps in endpoint_gap_map.items()
                if business_date in gaps
            )
            backfill_tasks.append(
                NightlySyncTask(
                    task_id=_new_identifier('task'),
                    task_kind='backfill',
                    org_id=org_id,
                    business_date=business_date,
                    triggered_by_endpoint_contract_ids=triggering_endpoints,
                    scheduler_trace_ref=scheduler_trace_ref,
                    workflow_id=workflow_id,
                    task_queue=task_queue,
                    planner_mode=self.policy.planner_mode,
                    carry_forward_from_business_date=business_date,
                )
            )

        for endpoint_contract_id, gaps in endpoint_gap_map.items():
            planned_dates = [business_date for business_date in gaps if business_date in selected_date_set]
            remaining_dates = [business_date for business_date in gaps if business_date not in selected_date_set]
            self.truth_store.upsert_backfill_progress_state(
                capability_id=VERTICAL_SLICE_CAPABILITY_ID,
                org_id=org_id,
                endpoint_contract_id=endpoint_contract_id,
                target_business_date=target_business_date,
                planner_mode=self.policy.planner_mode,
                cursor_business_date=remaining_dates[0] if remaining_dates else None,
                newest_missing_business_date=remaining_dates[0] if remaining_dates else None,
                oldest_missing_business_date=remaining_dates[-1] if remaining_dates else None,
                remaining_gap_count=len(remaining_dates),
                last_planned_business_dates=planned_dates,
                scheduler_trace_ref=scheduler_trace_ref,
                progress_status='backfill_dispatched' if planned_dates else 'backfill_complete',
            )

        return NightlySyncPlan(
            scheduler_trace_ref=scheduler_trace_ref,
            workflow_id=workflow_id,
            org_id=org_id,
            target_business_date=target_business_date,
            planner_mode=self.policy.planner_mode,
            task_queue=task_queue,
            expected_business_dates=expected_business_dates,
            currentness_task=currentness_task,
            backfill_tasks=tuple(backfill_tasks),
            endpoint_gap_map=endpoint_gap_map,
        )


class NightlySyncRuntime:
    def __init__(
        self,
        *,
        truth_store: PostgresTruthSubstrate,
        planner_policy: NightlyPlannerPolicy,
        app_secret: str,
        endpoint_contract_ids: Sequence[str] | None = None,
    ) -> None:
        self.truth_store = truth_store
        self.planner_policy = planner_policy
        self.app_secret = app_secret
        self.endpoint_contract_ids = tuple(endpoint_contract_ids or _member_insight_endpoint_contract_ids())

    def execute_task(
        self,
        *,
        task: NightlySyncTask,
        transport: Any,
    ) -> dict[str, Any]:
        start_time, end_time = business_date_window(task.business_date)
        vertical_slice_result = run_member_insight_vertical_slice(
            org_id=task.org_id,
            start_time=start_time,
            end_time=end_time,
            requested_business_date=task.business_date,
            app_secret=self.app_secret,
            transport=transport,
        )
        persistence = self.truth_store.persist_vertical_slice_result(
            org_id=task.org_id,
            target_scope_ref=f'navly:scope:store:{task.org_id}',
            target_business_date=task.business_date,
            vertical_slice_result=vertical_slice_result,
            scheduler_trace_ref=task.scheduler_trace_ref,
            workflow_id=task.workflow_id,
            task_kind=task.task_kind,
        )
        return {
            'task': asdict(task),
            'requested_business_date': task.business_date,
            'run_status': persistence['ingestion_run']['run_status'],
            'run_trace_ref': persistence['ingestion_run']['run_trace_ref'],
            'readiness_status': persistence['capability_readiness_snapshot']['readiness_status'],
            'service_status': persistence['service_projection']['service_status'],
            'evaluated_at': _utcnow_iso(),
        }

    def execute_plan(
        self,
        *,
        plan: NightlySyncPlan,
        transport: Any,
    ) -> dict[str, Any]:
        outcomes = [self.execute_task(task=plan.currentness_task, transport=transport)]
        for task in plan.backfill_tasks:
            outcomes.append(self.execute_task(task=task, transport=transport))

        self.truth_store.reconcile_backfill_progress(
            capability_id=VERTICAL_SLICE_CAPABILITY_ID,
            org_id=plan.org_id,
            endpoint_contract_ids=self.endpoint_contract_ids,
            expected_business_dates=plan.expected_business_dates,
            target_business_date=plan.target_business_date,
            planner_mode=plan.planner_mode,
            scheduler_trace_ref=plan.scheduler_trace_ref,
        )
        return {
            'scheduler_trace_ref': plan.scheduler_trace_ref,
            'workflow_id': plan.workflow_id,
            'org_id': plan.org_id,
            'target_business_date': plan.target_business_date,
            'expected_business_dates': list(plan.expected_business_dates),
            'currentness_task': asdict(plan.currentness_task),
            'backfill_tasks': [asdict(task) for task in plan.backfill_tasks],
            'outcomes': outcomes,
        }


class TemporalNightlySyncPlane:
    def __init__(
        self,
        *,
        truth_store: PostgresTruthSubstrate,
        planner: NightlySyncPlanner,
        runtime: NightlySyncRuntime,
        worker_bootstrap: TemporalWorkerBootstrap | None = None,
    ) -> None:
        self.truth_store = truth_store
        self.planner = planner
        self.runtime = runtime
        self.worker_bootstrap = worker_bootstrap or TemporalWorkerBootstrap.from_registry()

    def run_nightly_scheduler(
        self,
        *,
        org_ids: Sequence[str],
        target_business_date: str,
        transport_by_org: dict[str, Any],
    ) -> dict[str, Any]:
        scheduler_trace_ref = _trace_ref('workflow-trace:nightly-scheduler', _new_identifier('wf'))
        org_executions: list[dict[str, Any]] = []
        for org_id in org_ids:
            workflow_id = f'navly-nightly-{org_id}-{target_business_date}'
            plan = self.planner.build_plan(
                org_id=org_id,
                target_business_date=target_business_date,
                scheduler_trace_ref=scheduler_trace_ref,
                workflow_id=workflow_id,
                task_queue=self.worker_bootstrap.task_queue,
            )
            self.truth_store.record_scheduler_run(
                workflow_id=workflow_id,
                workflow_kind='nightly_scheduler',
                scheduler_trace_ref=scheduler_trace_ref,
                org_id=org_id,
                target_business_date=target_business_date,
                planner_mode=plan.planner_mode,
                task_queue=self.worker_bootstrap.task_queue,
                plan_task_count=1 + len(plan.backfill_tasks),
                failure_budget=self.worker_bootstrap.retry_max_attempts,
            )
            execution = self.runtime.execute_plan(
                plan=plan,
                transport=transport_by_org[org_id],
            )
            finalized_scheduler_run = self.truth_store.finalize_scheduler_run(
                scheduler_trace_ref=scheduler_trace_ref,
                scheduler_status=_workflow_status(
                    outcome['run_status'] for outcome in execution['outcomes']
                ),
                execution_trace_refs=[
                    outcome['run_trace_ref']
                    for outcome in execution['outcomes']
                ],
                dispatched_task_count=len(execution['outcomes']),
            )
            org_executions.append({
                'org_id': org_id,
                'plan': {
                    'expected_business_dates': list(plan.expected_business_dates),
                    'currentness_task': asdict(plan.currentness_task),
                    'backfill_tasks': [asdict(task) for task in plan.backfill_tasks],
                },
                'execution': execution,
                'scheduler_run': finalized_scheduler_run,
            })
        return {
            'scheduler_trace_ref': scheduler_trace_ref,
            'workflow_kind': 'nightly_scheduler',
            'worker_bootstrap': self.worker_bootstrap.to_record(),
            'org_executions': org_executions,
        }

    def _run_single_task_workflow(
        self,
        *,
        workflow_kind: str,
        task_kind: str,
        org_id: str,
        business_date: str,
        transport: Any,
    ) -> dict[str, Any]:
        scheduler_trace_ref = _trace_ref(f'workflow-trace:{workflow_kind}', _new_identifier('wf'))
        workflow_id = f'navly-{task_kind}-{org_id}-{business_date}'
        task = NightlySyncTask(
            task_id=_new_identifier('task'),
            task_kind=task_kind,
            org_id=org_id,
            business_date=business_date,
            triggered_by_endpoint_contract_ids=self.planner.endpoint_contract_ids,
            scheduler_trace_ref=scheduler_trace_ref,
            workflow_id=workflow_id,
            task_queue=self.worker_bootstrap.task_queue,
            planner_mode=self.planner.policy.planner_mode,
            carry_forward_from_business_date=business_date if task_kind in {'retry', 'rerun'} else None,
        )
        self.truth_store.record_scheduler_run(
            workflow_id=workflow_id,
            workflow_kind=workflow_kind,
            scheduler_trace_ref=scheduler_trace_ref,
            org_id=org_id,
            target_business_date=business_date,
            planner_mode=self.planner.policy.planner_mode,
            task_queue=self.worker_bootstrap.task_queue,
            plan_task_count=1,
            failure_budget=self.worker_bootstrap.retry_max_attempts,
        )
        outcome = self.runtime.execute_task(task=task, transport=transport)
        finalized_scheduler_run = self.truth_store.finalize_scheduler_run(
            scheduler_trace_ref=scheduler_trace_ref,
            scheduler_status=_workflow_status([outcome['run_status']]),
            execution_trace_refs=[outcome['run_trace_ref']],
            dispatched_task_count=1,
        )
        return {
            'scheduler_trace_ref': scheduler_trace_ref,
            'workflow_kind': workflow_kind,
            'scheduler_run': finalized_scheduler_run,
            'outcome': outcome,
        }

    def run_retry_workflow(
        self,
        *,
        org_id: str,
        business_date: str,
        transport: Any,
    ) -> dict[str, Any]:
        return self._run_single_task_workflow(
            workflow_kind='retry_workflow',
            task_kind='retry',
            org_id=org_id,
            business_date=business_date,
            transport=transport,
        )

    def run_rerun_workflow(
        self,
        *,
        org_id: str,
        business_date: str,
        transport: Any,
    ) -> dict[str, Any]:
        return self._run_single_task_workflow(
            workflow_kind='rerun_workflow',
            task_kind='rerun',
            org_id=org_id,
            business_date=business_date,
            transport=transport,
        )

    def run_backfill_workflow(
        self,
        *,
        org_id: str,
        backfill_from_business_date: str,
        backfill_to_business_date: str,
        transport: Any,
    ) -> dict[str, Any]:
        if backfill_from_business_date > backfill_to_business_date:
            raise ValueError(
                'backfill_from_business_date must be less than or equal to backfill_to_business_date'
            )

        scheduler_trace_ref = _trace_ref('workflow-trace:backfill-workflow', _new_identifier('wf'))
        workflow_id = (
            f'navly-backfill-{org_id}-{backfill_from_business_date}-{backfill_to_business_date}'
        )
        requested_business_dates = tuple(
            sorted(
                build_expected_business_dates(
                    backfill_start_business_date=backfill_from_business_date,
                    target_business_date=backfill_to_business_date,
                ),
                reverse=True,
            )
        )
        tasks = tuple(
            NightlySyncTask(
                task_id=_new_identifier('task'),
                task_kind='backfill',
                org_id=org_id,
                business_date=business_date,
                triggered_by_endpoint_contract_ids=self.planner.endpoint_contract_ids,
                scheduler_trace_ref=scheduler_trace_ref,
                workflow_id=workflow_id,
                task_queue=self.worker_bootstrap.task_queue,
                planner_mode=self.planner.policy.planner_mode,
                carry_forward_from_business_date=business_date,
            )
            for business_date in requested_business_dates
        )
        self.truth_store.record_scheduler_run(
            workflow_id=workflow_id,
            workflow_kind='backfill_workflow',
            scheduler_trace_ref=scheduler_trace_ref,
            org_id=org_id,
            target_business_date=backfill_to_business_date,
            planner_mode=self.planner.policy.planner_mode,
            task_queue=self.worker_bootstrap.task_queue,
            plan_task_count=len(tasks),
            failure_budget=self.worker_bootstrap.retry_max_attempts,
        )

        outcomes = [
            self.runtime.execute_task(task=task, transport=transport)
            for task in tasks
        ]
        expected_business_dates = build_expected_business_dates(
            backfill_start_business_date=self.planner.policy.backfill_start_business_date,
            target_business_date=backfill_to_business_date,
        )
        self.truth_store.reconcile_backfill_progress(
            capability_id=VERTICAL_SLICE_CAPABILITY_ID,
            org_id=org_id,
            endpoint_contract_ids=self.planner.endpoint_contract_ids,
            expected_business_dates=expected_business_dates,
            target_business_date=backfill_to_business_date,
            planner_mode=self.planner.policy.planner_mode,
            scheduler_trace_ref=scheduler_trace_ref,
        )
        finalized_scheduler_run = self.truth_store.finalize_scheduler_run(
            scheduler_trace_ref=scheduler_trace_ref,
            scheduler_status=_workflow_status([outcome['run_status'] for outcome in outcomes]),
            execution_trace_refs=[outcome['run_trace_ref'] for outcome in outcomes],
            dispatched_task_count=len(outcomes),
        )
        return {
            'scheduler_trace_ref': scheduler_trace_ref,
            'workflow_kind': 'backfill_workflow',
            'requested_backfill_from_business_date': backfill_from_business_date,
            'requested_backfill_to_business_date': backfill_to_business_date,
            'requested_business_dates': list(requested_business_dates),
            'scheduler_run': finalized_scheduler_run,
            'outcomes': outcomes,
        }
