from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import (  # noqa: E402
    DEFAULT_LIVE_TIMEOUT_MS,
    FixtureQinqinTransport,
    LiveQinqinTransport,
    TransportConfigError,
)
from ingestion.member_insight_vertical_slice import DEFAULT_PAGE_SIZE, run_member_insight_vertical_slice  # noqa: E402


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
    parser = argparse.ArgumentParser(description='Run the member insight vertical slice with fixture or live Qinqin transport.')
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--start-time', required=True)
    parser.add_argument('--end-time', required=True)
    parser.add_argument('--requested-business-date', required=True)
    parser.add_argument('--app-secret', required=True)
    parser.add_argument('--page-size', type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument('--transport', choices=('fixture', 'live'), default='fixture')
    parser.add_argument('--fixtures', default=str(DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'))
    parser.add_argument('--live-base-url')
    parser.add_argument('--live-timeout-ms', type=int)
    parser.add_argument('--live-authorization')
    parser.add_argument('--live-token')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    try:
        transport = _build_transport(args)
    except (TransportConfigError, ValueError) as exc:
        parser.error(str(exc))

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
        'transport_kind': result['transport_kind'],
        'capability_id': result['capability_id'],
        'service_object_id': result['service_object_id'],
        'ingestion_run_status': result['historical_run_truth']['ingestion_run']['run_status'],
        'endpoint_runs': len(result['historical_run_truth']['endpoint_runs']),
        'raw_response_pages': len(result['raw_replay']['raw_response_pages']),
        'transport_replay_artifacts': len(result['raw_replay']['transport_replay_artifacts']),
        'customer_count': len(result['canonical_artifacts']['customer']),
        'consume_bill_count': len(result['canonical_artifacts']['consume_bill']),
        'latest_usable_endpoint_states': len(result['latest_state_artifacts']['latest_usable_endpoint_states']),
        'output_dir': args.output_dir,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
