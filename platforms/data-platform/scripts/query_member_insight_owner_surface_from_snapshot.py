from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from workflows.member_insight_owner_surface import build_member_insight_owner_surface_from_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Query the member_insight owner surface from a persisted PostgreSQL truth-substrate snapshot.'
    )
    parser.add_argument('--state-snapshot', required=True)
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--target-business-date', required=True)
    parser.add_argument('--target-scope-ref', required=True)
    parser.add_argument('--request-id', default='req-owner-surface-snapshot-cli')
    parser.add_argument('--trace-ref', default='navly:trace:owner-surface-snapshot-cli')
    parser.add_argument('--requested-capability-id')
    parser.add_argument('--requested-service-object-id')
    parser.add_argument('--output-dir')
    args = parser.parse_args()

    payload = build_member_insight_owner_surface_from_snapshot(
        request_id=args.request_id,
        trace_ref=args.trace_ref,
        target_scope_ref=args.target_scope_ref,
        target_business_date=args.target_business_date,
        org_id=args.org_id,
        state_snapshot_path=args.state_snapshot,
        requested_capability_id=args.requested_capability_id or 'navly.store.member_insight',
        requested_service_object_id=args.requested_service_object_id or 'navly.service.store.member_insight',
    )
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload['output_dir'] = str(output_dir)
        (output_dir / 'member-insight-owner-surface.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'member-insight-readiness-response.json').write_text(
            json.dumps(payload['readiness_response'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        (output_dir / 'member-insight-theme-service-response.json').write_text(
            json.dumps(payload['theme_service_response'], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
