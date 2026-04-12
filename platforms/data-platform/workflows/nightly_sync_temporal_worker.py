from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from workflows.nightly_sync_runtime import run_nightly_sync_runtime_cycle

TEMPORAL_WORKFLOW_NAME = 'navly.data_platform.nightly_sync.runtime_cycle'
TEMPORAL_ACTIVITY_NAME = 'navly.data_platform.nightly_sync.execute_runtime_cycle'


@dataclass(frozen=True)
class NightlySyncTemporalSpec:
    task_queue: str
    workflow_name: str
    activity_name: str


def build_nightly_sync_temporal_spec(
    *,
    task_queue: str = 'navly-data-platform-nightly-sync',
) -> NightlySyncTemporalSpec:
    return NightlySyncTemporalSpec(
        task_queue=task_queue,
        workflow_name=TEMPORAL_WORKFLOW_NAME,
        activity_name=TEMPORAL_ACTIVITY_NAME,
    )


def run_temporal_nightly_sync_activity(payload: dict[str, Any]) -> dict[str, Any]:
    return run_nightly_sync_runtime_cycle(
        db_path=payload['db_path'],
        source_system_id=payload['source_system_id'],
        org_id=payload['org_id'],
        target_business_date=payload['target_business_date'],
        expected_business_dates=payload['expected_business_dates'],
        app_secret=payload['app_secret'],
        endpoint_contract_ids=payload.get('endpoint_contract_ids'),
        max_dispatch_tasks=payload.get('max_dispatch_tasks', 8),
        max_backfill_dispatch_tasks=payload.get('max_backfill_dispatch_tasks'),
        history_start_business_date=payload.get('history_start_business_date'),
        output_root=payload.get('output_root'),
    )


def run_temporal_worker(
    *,
    temporal_server_url: str,
    namespace: str,
    task_queue: str,
    worker_identity: str,
    activity_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        from temporalio import activity, workflow
        from temporalio.client import Client
        from temporalio.worker import Worker
    except ImportError as exc:
        raise RuntimeError(
            'Temporal worker support requires temporalio. Install platforms/data-platform/requirements-runtime.txt.'
        ) from exc

    spec = build_nightly_sync_temporal_spec(task_queue=task_queue)

    @activity.defn(name=spec.activity_name)
    async def execute_runtime_cycle(payload: dict[str, Any]) -> dict[str, Any]:
        return run_temporal_nightly_sync_activity(payload)

    @workflow.defn(name=spec.workflow_name)
    class NightlySyncRuntimeWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            return await workflow.execute_activity(
                execute_runtime_cycle,
                payload,
                start_to_close_timeout=payload.get('activity_timeout_seconds', 3600),
            )

    async def _run() -> dict[str, Any]:
        client = await Client.connect(temporal_server_url, namespace=namespace)
        worker = Worker(
            client,
            task_queue=spec.task_queue,
            workflows=[NightlySyncRuntimeWorkflow],
            activities=[execute_runtime_cycle],
            identity=worker_identity,
        )
        return {
            'task_queue': spec.task_queue,
            'workflow_name': spec.workflow_name,
            'activity_name': spec.activity_name,
            'payload_preview': {
                'source_system_id': activity_payload['source_system_id'],
                'org_id': activity_payload['org_id'],
                'target_business_date': activity_payload['target_business_date'],
            },
            'worker': worker,
        }

    return {
        'temporal_server_url': temporal_server_url,
        'namespace': namespace,
        'worker_identity': worker_identity,
        'spec': asdict(spec),
        'bootstrap': _run,
    }


__all__ = [
    'NightlySyncTemporalSpec',
    'TEMPORAL_ACTIVITY_NAME',
    'TEMPORAL_WORKFLOW_NAME',
    'build_nightly_sync_temporal_spec',
    'run_temporal_nightly_sync_activity',
    'run_temporal_worker',
]
