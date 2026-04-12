from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.nightly_sync_temporal_worker import run_temporal_worker  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Bootstrap the Temporal nightly sync worker.'
    )
    parser.add_argument('--temporal-server-url', default=os.environ.get('TEMPORAL_SERVER_URL'))
    parser.add_argument('--namespace', default=os.environ.get('TEMPORAL_NAMESPACE', 'default'))
    parser.add_argument('--task-queue', default='navly-data-platform-nightly-sync')
    parser.add_argument('--worker-identity', default='navly-data-platform-nightly-sync-worker')
    parser.add_argument('--db-path', required=True)
    parser.add_argument('--source-system-id', default='qinqin.v1_1')
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--target-business-date', required=True)
    parser.add_argument('--expected-business-date', action='append', default=[])
    parser.add_argument('--history-start-business-date')
    parser.add_argument('--app-secret', default=os.environ.get('QINQIN_API_APP_SECRET'))
    parser.add_argument('--output-dir')
    parser.add_argument('--max-dispatch-tasks', type=int, default=8)
    parser.add_argument('--max-backfill-dispatch-tasks', type=int)
    args = parser.parse_args()

    if not args.temporal_server_url:
        parser.error('temporal-server-url or TEMPORAL_SERVER_URL is required')
    if not args.app_secret:
        parser.error('app-secret or QINQIN_API_APP_SECRET is required')

    payload = {
        'db_path': args.db_path,
        'source_system_id': args.source_system_id,
        'org_id': args.org_id,
        'target_business_date': args.target_business_date,
        'expected_business_dates': args.expected_business_date or [args.target_business_date],
        'history_start_business_date': args.history_start_business_date,
        'app_secret': args.app_secret,
        'output_root': args.output_dir,
        'max_dispatch_tasks': args.max_dispatch_tasks,
        'max_backfill_dispatch_tasks': args.max_backfill_dispatch_tasks,
    }
    runtime = run_temporal_worker(
        temporal_server_url=args.temporal_server_url,
        namespace=args.namespace,
        task_queue=args.task_queue,
        worker_identity=args.worker_identity,
        activity_payload=payload,
    )
    bootstrap = runtime.pop('bootstrap')
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    asyncio.run(bootstrap())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
