from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from backbone_support.qinqin_substrate import FixtureQinqinTransport
from ingestion.member_insight_vertical_slice import DEFAULT_PAGE_SIZE, run_member_insight_vertical_slice


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the Milestone-B member insight vertical slice backbone.')
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--start-time', required=True)
    parser.add_argument('--end-time', required=True)
    parser.add_argument('--requested-business-date', required=True)
    parser.add_argument('--app-secret', required=True)
    parser.add_argument('--page-size', type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument('--fixtures', default=str(DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'))
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    fixture_bundle = json.loads(Path(args.fixtures).read_text(encoding='utf-8'))
    transport = FixtureQinqinTransport(fixture_bundle)
    result = run_member_insight_vertical_slice(
        org_id=args.org_id,
        start_time=args.start_time,
        end_time=args.end_time,
        requested_business_date=args.requested_business_date,
        app_secret=args.app_secret,
        page_size=args.page_size,
        transport=transport,
        output_root=args.output_dir,
    )
    print(json.dumps({
        'capability_id': result['capability_id'],
        'service_object_id': result['service_object_id'],
        'endpoint_runs': len(result['historical_run_truth']['endpoint_runs']),
        'customer_count': len(result['canonical_artifacts']['customer']),
        'consume_bill_count': len(result['canonical_artifacts']['consume_bill']),
        'latest_usable_endpoint_states': len(result['latest_state_artifacts']['latest_usable_endpoint_states']),
        'output_dir': args.output_dir,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
