from __future__ import annotations

import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.full_phase1_acceptance_suite_manifest import (  # noqa: E402
    FULL_PHASE1_ACCEPTANCE_COMMAND,
    build_full_phase1_acceptance_suite_manifest,
)


class FullPhase1AcceptanceSuiteDocsTest(unittest.TestCase):
    def test_manifest_freezes_authoritative_command_and_completion_board(self) -> None:
        manifest = build_full_phase1_acceptance_suite_manifest()

        self.assertEqual(manifest['suite_name'], 'navly_v1_full_phase_1_acceptance_suite')
        self.assertEqual(manifest['status'], 'verification_governed')
        self.assertEqual(manifest['authoritative_command'], FULL_PHASE1_ACCEPTANCE_COMMAND)

        step_ids = {step['step_id'] for step in manifest['acceptance_suite_steps']}
        self.assertEqual(
            step_ids,
            {
                'alpha_smoke',
                'remaining_live_transport',
                'full_data_platform_regression',
            },
        )
        board_items = {row['board_item']: row for row in manifest['completion_board']}
        self.assertEqual(board_items['alpha']['status'], 'reached')
        self.assertEqual(board_items['full phase-1']['status'], 'reached')
        self.assertEqual(board_items['go/no-go']['status'], 'go')
        self.assertIn('authoritative', manifest['authoritative_go_no_go_answer'])

    def test_docs_and_runbook_reference_the_authoritative_acceptance_suite(self) -> None:
        spec_doc = (
            REPO_ROOT
            / 'docs/specs/navly-v1/verification/2026-04-11-navly-v1-full-phase-1-acceptance-suite-and-completion-board.md'
        ).read_text(encoding='utf-8')
        runbook_doc = (
            REPO_ROOT / 'docs/runbooks/full-phase-1-acceptance-suite.md'
        ).read_text(encoding='utf-8')
        alpha_doc = (
            REPO_ROOT
            / 'docs/specs/navly-v1/verification/2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md'
        ).read_text(encoding='utf-8')

        for text in (spec_doc, runbook_doc):
            self.assertIn('completion board', text.lower())
            self.assertIn('full phase-1', text.lower())
            self.assertIn('alpha', text.lower())
            self.assertIn('go/no-go', text.lower())
            self.assertIn('acceptance suite', text.lower())
            self.assertIn('authoritative', text.lower())
            self.assertIn(FULL_PHASE1_ACCEPTANCE_COMMAND, text)

        self.assertIn('historical alpha gate snapshot', alpha_doc.lower())
        self.assertIn(
            '2026-04-11-navly-v1-full-phase-1-acceptance-suite-and-completion-board.md',
            alpha_doc,
        )


if __name__ == '__main__':
    unittest.main()
