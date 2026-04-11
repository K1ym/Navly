from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.nightly_sync_worker import run_nightly_sync_worker  # noqa: E402


def _load_json_list(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'entries' in payload:
        return list(payload['entries'])
    if isinstance(payload, list):
        return payload
    raise ValueError(f'Unsupported JSON payload in {path}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run the local nightly sync worker with persisted cursor ledger storage.'
    )
    parser.add_argument('--db-path', required=True)
    parser.add_argument('--source-system-id', default='qinqin.v1_1')
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--target-business-date', required=True)
    parser.add_argument('--expected-business-date', action='append', default=[])
    parser.add_argument('--latest-usable-states-json')
    parser.add_argument('--endpoint-contract-id', action='append', default=[])
    parser.add_argument('--max-dispatch-tasks', type=int, default=8)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    result = run_nightly_sync_worker(
        db_path=args.db_path,
        source_system_id=args.source_system_id,
        org_id=args.org_id,
        target_business_date=args.target_business_date,
        expected_business_dates=args.expected_business_date or [args.target_business_date],
        latest_usable_endpoint_states=_load_json_list(args.latest_usable_states_json),
        endpoint_contract_ids=args.endpoint_contract_id or None,
        max_dispatch_tasks=args.max_dispatch_tasks,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'worker-result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    (output_dir / 'dispatch-plan.json').write_text(
        json.dumps(result['scheduler_snapshot']['dispatch_plan'], ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    (output_dir / 'cursor-ledger.json').write_text(
        json.dumps(result['scheduler_snapshot']['cursor_ledger'], ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
