from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport  # noqa: E402
from workflows.nightly_sync_runtime import run_nightly_sync_runtime_cycle  # noqa: E402


def _load_json_list(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'entries' in payload:
        return list(payload['entries'])
    if isinstance(payload, list):
        return payload
    raise ValueError(f'Unsupported JSON payload in {path}')


def _build_transport(args: argparse.Namespace):
    if args.transport == 'fixture':
        return FixtureQinqinTransport(
            _load_json_list(args.fixture_bundle_json) if args.fixture_bundle_json else {}
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run the nightly sync runtime cycle and persist cursor ledger state.'
    )
    parser.add_argument('--db-path', required=True)
    parser.add_argument('--source-system-id', default='qinqin.v1_1')
    parser.add_argument('--org-id', default=os.environ.get('QINQIN_API_ORG_ID'), required=False)
    parser.add_argument('--target-business-date', required=True)
    parser.add_argument('--expected-business-date', action='append', default=[])
    parser.add_argument('--history-start-business-date')
    parser.add_argument('--endpoint-contract-id', action='append', default=[])
    parser.add_argument('--max-dispatch-tasks', type=int, default=8)
    parser.add_argument('--max-backfill-dispatch-tasks', type=int)
    parser.add_argument('--persisted-serving-root')
    parser.add_argument('--app-secret', default=os.environ.get('QINQIN_API_APP_SECRET'), required=False)
    parser.add_argument('--transport', choices=('live', 'fixture'), default='live')
    parser.add_argument('--fixture-bundle-json')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    if not args.org_id:
        parser.error('org-id or QINQIN_API_ORG_ID is required')
    if not args.app_secret:
        parser.error('app-secret or QINQIN_API_APP_SECRET is required')

    transport = _build_transport(args)
    result = run_nightly_sync_runtime_cycle(
        db_path=args.db_path,
        source_system_id=args.source_system_id,
        org_id=args.org_id,
        target_business_date=args.target_business_date,
        expected_business_dates=args.expected_business_date or [args.target_business_date],
        app_secret=args.app_secret,
        transport=transport,
        endpoint_contract_ids=args.endpoint_contract_id or None,
        max_dispatch_tasks=args.max_dispatch_tasks,
        max_backfill_dispatch_tasks=args.max_backfill_dispatch_tasks,
        history_start_business_date=args.history_start_business_date,
        persisted_serving_root=args.persisted_serving_root,
        output_root=args.output_dir,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'runtime-result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
