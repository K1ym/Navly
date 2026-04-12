from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate  # noqa: E402
from migration.artifact_tree_bridge import import_member_insight_artifact_tree_to_truth_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Import a member-insight artifact tree into the repo-local PostgreSQL truth substrate model.'
    )
    parser.add_argument('--artifact-root', required=True)
    parser.add_argument('--request-id', default='req-member-insight-artifact-bridge-cli')
    parser.add_argument('--trace-ref', default='navly:trace:req-member-insight-artifact-bridge-cli')
    parser.add_argument('--scheduler-trace-ref')
    parser.add_argument('--workflow-id')
    parser.add_argument('--task-kind', default='artifact_bridge')
    parser.add_argument('--state-snapshot')
    parser.add_argument('--output-dir')
    args = parser.parse_args()

    truth_store = (
        PostgresTruthSubstrate.from_snapshot_file(args.state_snapshot)
        if args.state_snapshot
        else PostgresTruthSubstrate()
    )
    result = import_member_insight_artifact_tree_to_truth_store(
        artifact_root=args.artifact_root,
        truth_store=truth_store,
        scheduler_trace_ref=args.scheduler_trace_ref,
        workflow_id=args.workflow_id,
        task_kind=args.task_kind,
    )
    snapshot = truth_store.snapshot()
    payload = {
        'request_id': args.request_id,
        'trace_ref': args.trace_ref,
        'bridge_kind': result['bridge_kind'],
        'artifact_root': result['artifact_root'],
        'ingestion_runs': len(snapshot['ingestion_runs']),
        'endpoint_runs': len(snapshot['endpoint_runs']),
        'page_runs': len(snapshot['page_runs']),
        'raw_replay_artifacts': len(snapshot['raw_replay_artifacts']),
        'latest_sync_states': len(snapshot['latest_sync_states']),
        'service_projections': len(snapshot['service_projections']),
    }
    if args.state_snapshot:
        snapshot_path = truth_store.write_snapshot_file(args.state_snapshot)
        payload['state_snapshot'] = str(snapshot_path)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload['output_dir'] = str(output_dir)
        (output_dir / 'artifact-bridge-summary.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
