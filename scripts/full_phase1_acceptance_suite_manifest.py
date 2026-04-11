from __future__ import annotations

import argparse
import json
from copy import deepcopy
from typing import Any

FULL_PHASE1_ACCEPTANCE_COMMAND = 'bash scripts/validate-full-phase1-acceptance-suite.sh'

ACCEPTANCE_SUITE_STEPS: list[dict[str, str]] = [
    {
        'step_id': 'alpha_smoke',
        'label': 'First usable alpha smoke baseline',
        'command': 'bash scripts/validate-first-usable-alpha-smoke.sh',
        'covers': 'D e2e acceptance',
        'status': 'green',
    },
    {
        'step_id': 'remaining_live_transport',
        'label': 'Remaining Qinqin live transport validation matrix',
        'command': 'bash scripts/validate-remaining-phase1-live-transport.sh',
        'covers': 'D e2e acceptance + E regression baseline',
        'status': 'green',
    },
    {
        'step_id': 'full_data_platform_regression',
        'label': 'Full data-platform contract and owner-surface regression',
        'command': "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
        'covers': 'A boundary verification + B contract consistency + C docs consistency + E regression baseline',
        'status': 'green',
    },
]

COMPLETION_BOARD_ROWS: list[dict[str, str]] = [
    {
        'board_group': 'verification',
        'board_item': 'A boundary verification',
        'status': 'green',
        'evidence': "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
    },
    {
        'board_group': 'verification',
        'board_item': 'B contract consistency',
        'status': 'green',
        'evidence': "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
    },
    {
        'board_group': 'verification',
        'board_item': 'C docs consistency',
        'status': 'green',
        'evidence': "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
    },
    {
        'board_group': 'verification',
        'board_item': 'D e2e acceptance',
        'status': 'green',
        'evidence': FULL_PHASE1_ACCEPTANCE_COMMAND,
    },
    {
        'board_group': 'verification',
        'board_item': 'E regression baseline',
        'status': 'green',
        'evidence': FULL_PHASE1_ACCEPTANCE_COMMAND,
    },
    {
        'board_group': 'milestone',
        'board_item': 'alpha',
        'status': 'reached',
        'evidence': 'bash scripts/validate-first-usable-alpha-smoke.sh',
    },
    {
        'board_group': 'milestone',
        'board_item': 'full phase-1',
        'status': 'reached',
        'evidence': FULL_PHASE1_ACCEPTANCE_COMMAND,
    },
    {
        'board_group': 'decision',
        'board_item': 'go/no-go',
        'status': 'go',
        'evidence': 'authoritative answer: GO',
    },
]

POST_PHASE1_OUT_OF_SCOPE: list[str] = [
    'real upstream credential replays and tenant-specific secrets handling',
    'new channels outside WeCom + OpenClaw',
    'post-phase-1 orchestration and richer UI surfaces',
]


def build_full_phase1_acceptance_suite_manifest() -> dict[str, Any]:
    return {
        'suite_name': 'navly_v1_full_phase_1_acceptance_suite',
        'status': 'verification_governed',
        'authoritative_command': FULL_PHASE1_ACCEPTANCE_COMMAND,
        'acceptance_suite_steps': deepcopy(ACCEPTANCE_SUITE_STEPS),
        'completion_board': deepcopy(COMPLETION_BOARD_ROWS),
        'authoritative_go_no_go_answer': (
            'authoritative GO: full phase-1 acceptance suite is green; '
            'post-phase-1 items stay out of the gate.'
        ),
        'post_phase1_out_of_scope': deepcopy(POST_PHASE1_OUT_OF_SCOPE),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Print the governed Navly full Phase-1 acceptance suite manifest.'
    )
    parser.add_argument('--format', choices=('json',), default='json')
    args = parser.parse_args()
    if args.format != 'json':
        raise ValueError(f'Unsupported format: {args.format}')
    print(json.dumps(build_full_phase1_acceptance_suite_manifest(), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
