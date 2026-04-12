from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.postgres_temporal_operator_surface import query_operator_status_from_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Query operator sync/backfill status reports from a persisted PostgreSQL truth-substrate snapshot.'
    )
    parser.add_argument('--request-id', default='req-operator-status-snapshot-cli')
    parser.add_argument('--trace-ref', default='navly:trace:operator-status-snapshot-cli')
    parser.add_argument('--state-snapshot', required=True)
    parser.add_argument('--org-id', action='append', dest='org_ids', required=True)
    parser.add_argument('--output-dir')
    args = parser.parse_args()

    payload = query_operator_status_from_snapshot(
        request_id=args.request_id,
        trace_ref=args.trace_ref,
        state_snapshot_path=args.state_snapshot,
        org_ids=args.org_ids,
    )
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload['output_dir'] = str(output_dir)
        (output_dir / 'operator-status-bundle.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-sync-status.json').write_text(
            json.dumps(payload['sync_status'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-backfill-status.json').write_text(
            json.dumps(payload['backfill_status'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'operator-quality-report.json').write_text(
            json.dumps(payload['quality_report'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
