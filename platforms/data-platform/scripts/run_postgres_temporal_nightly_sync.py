from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate  # noqa: E402
from connectors.qinqin.qinqin_substrate import (  # noqa: E402
    DEFAULT_LIVE_TIMEOUT_MS,
    FixtureQinqinTransport,
    LiveQinqinTransport,
    TransportConfigError,
)
from workflows.postgres_temporal_nightly_sync import (  # noqa: E402
    NightlyPlannerPolicy,
    NightlySyncPlanner,
    NightlySyncRuntime,
    TemporalNightlySyncPlane,
    TemporalWorkerBootstrap,
    load_nightly_sync_policy_entry,
)


def _resolve_cli_or_env(cli_value: str | None, *env_names: str) -> str | None:
    if cli_value:
        return cli_value
    for env_name in env_names:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    return None


def _build_transport(args: argparse.Namespace):
    if args.transport == 'fixture':
        fixture_bundle = json.loads(Path(args.fixtures).read_text(encoding='utf-8'))
        return FixtureQinqinTransport(fixture_bundle)

    live_base_url = _resolve_cli_or_env(args.live_base_url, 'QINQIN_API_BASE_URL', 'QINQIN_REAL_DATA_URL')
    live_authorization = _resolve_cli_or_env(args.live_authorization, 'QINQIN_API_AUTHORIZATION')
    live_token = _resolve_cli_or_env(args.live_token, 'QINQIN_API_TOKEN', 'QINQIN_REAL_DATA_TOKEN')
    live_timeout_ms = args.live_timeout_ms
    if live_timeout_ms is None:
        live_timeout_raw = _resolve_cli_or_env(None, 'QINQIN_API_REQUEST_TIMEOUT_MS')
        live_timeout_ms = int(live_timeout_raw) if live_timeout_raw else DEFAULT_LIVE_TIMEOUT_MS

    return LiveQinqinTransport(
        base_url=live_base_url or '',
        timeout_ms=live_timeout_ms,
        authorization=live_authorization,
        token=live_token,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run the repo-authoritative PostgreSQL/Temporal nightly sync plane with fixture or live transport.'
    )
    parser.add_argument('--request-id', default='req-navly-nightly-run-001')
    parser.add_argument('--trace-ref', default='navly:trace:req-navly-nightly-run-001')
    parser.add_argument('--org-id', action='append', dest='org_ids', required=True)
    parser.add_argument('--target-business-date', required=True)
    parser.add_argument('--backfill-start-business-date', required=True)
    parser.add_argument('--app-secret', required=True)
    parser.add_argument('--max-backfill-tasks-per-run', type=int)
    parser.add_argument('--transport', choices=('fixture', 'live'), default='fixture')
    parser.add_argument(
        '--fixtures',
        default=str(DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'),
    )
    parser.add_argument('--live-base-url')
    parser.add_argument('--live-timeout-ms', type=int)
    parser.add_argument('--live-authorization')
    parser.add_argument('--live-token')
    parser.add_argument('--output-dir')
    parser.add_argument('--state-snapshot')
    args = parser.parse_args()

    try:
        transport = _build_transport(args)
    except (TransportConfigError, ValueError) as exc:
        parser.error(str(exc))

    truth_store = (
        PostgresTruthSubstrate.from_snapshot_file(args.state_snapshot)
        if args.state_snapshot
        else PostgresTruthSubstrate()
    )
    policy = NightlyPlannerPolicy.from_registry(
        backfill_start_business_date=args.backfill_start_business_date,
        max_backfill_tasks_per_run=args.max_backfill_tasks_per_run,
    )
    planner = NightlySyncPlanner(truth_store=truth_store, policy=policy)
    runtime = NightlySyncRuntime(
        truth_store=truth_store,
        planner_policy=policy,
        app_secret=args.app_secret,
    )
    temporal_plane = TemporalNightlySyncPlane(
        truth_store=truth_store,
        planner=planner,
        runtime=runtime,
        worker_bootstrap=TemporalWorkerBootstrap.from_registry(),
    )
    result = temporal_plane.run_nightly_scheduler(
        org_ids=args.org_ids,
        target_business_date=args.target_business_date,
        transport_by_org={org_id: transport for org_id in args.org_ids},
    )
    snapshot = truth_store.snapshot()
    policy_entry = load_nightly_sync_policy_entry()
    payload = {
        'request_id': args.request_id,
        'trace_ref': args.trace_ref,
        'scheduler_trace_ref': result['scheduler_trace_ref'],
        'workflow_kind': result['workflow_kind'],
        'effective_policy': {
            'policy_id': policy_entry['policy_id'],
            'planner_mode': policy.planner_mode,
            'backfill_order': policy.backfill_order,
            'cursor_mode': policy.cursor_mode,
            'backfill_start_business_date': policy.backfill_start_business_date,
            'max_backfill_tasks_per_run': policy.max_backfill_tasks_per_run,
        },
        'worker_bootstrap': result['worker_bootstrap'],
        'org_count': len(result['org_executions']),
        'org_executions': [
            {
                'org_id': execution['org_id'],
                'currentness_business_date': execution['plan']['currentness_task']['business_date'],
                'backfill_business_dates': [
                    task['business_date'] for task in execution['plan']['backfill_tasks']
                ],
                'outcome_run_statuses': [
                    outcome['run_status'] for outcome in execution['execution']['outcomes']
                ],
            }
            for execution in result['org_executions']
        ],
        'scheduler_runs': len(snapshot['scheduler_runs']),
        'ingestion_runs': len(snapshot['ingestion_runs']),
        'backfill_progress_states': len(snapshot['backfill_progress_states']),
        'latest_sync_states': len(snapshot['latest_sync_states']),
        'service_projections': len(snapshot['service_projections']),
    }
    if args.state_snapshot:
        snapshot_path = truth_store.write_snapshot_file(args.state_snapshot)
        payload['state_snapshot'] = str(snapshot_path)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / 'nightly-run-summary.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'scheduler-runs.json').write_text(
            json.dumps(snapshot['scheduler_runs'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'latest-sync-states.json').write_text(
            json.dumps(snapshot['latest_sync_states'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'backfill-progress-states.json').write_text(
            json.dumps(snapshot['backfill_progress_states'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'service-projections.json').write_text(
            json.dumps(snapshot['service_projections'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-sync-status.json').write_text(
            json.dumps(
                [truth_store.build_sync_status_report(org_id=org_id) for org_id in args.org_ids],
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-backfill-status.json').write_text(
            json.dumps(
                [truth_store.build_backfill_status_report(org_id=org_id) for org_id in args.org_ids],
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-quality-report.json').write_text(
            json.dumps(
                [truth_store.build_quality_report(org_id=org_id) for org_id in args.org_ids],
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        payload['output_dir'] = str(output_dir)
        (output_dir / 'nightly-run-summary.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
