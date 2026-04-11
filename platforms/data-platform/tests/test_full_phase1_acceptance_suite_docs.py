from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_full_phase1_manifest_module():
    module_path = REPO_ROOT / 'scripts' / 'full_phase1_acceptance_suite_manifest.py'
    spec = importlib.util.spec_from_file_location(
        'navly_full_phase1_acceptance_suite_manifest_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to load script module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MANIFEST_MODULE = _load_full_phase1_manifest_module()
FULL_PHASE1_ACCEPTANCE_COMMAND = _MANIFEST_MODULE.FULL_PHASE1_ACCEPTANCE_COMMAND
build_full_phase1_acceptance_suite_manifest = _MANIFEST_MODULE.build_full_phase1_acceptance_suite_manifest


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
        self.assertEqual(
            [step['command'] for step in manifest['acceptance_suite_steps']],
            [
                'bash scripts/validate-first-usable-alpha-smoke.sh',
                'bash scripts/validate-remaining-phase1-live-transport.sh',
                "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
            ],
        )
        self.assertEqual(
            [row['evidence'] for row in manifest['completion_board']],
            [
                "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
                "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
                "python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'",
                FULL_PHASE1_ACCEPTANCE_COMMAND,
                FULL_PHASE1_ACCEPTANCE_COMMAND,
                'bash scripts/validate-first-usable-alpha-smoke.sh',
                FULL_PHASE1_ACCEPTANCE_COMMAND,
                'authoritative answer: GO',
            ],
        )

    def test_docs_and_runbook_reference_the_authoritative_acceptance_suite(self) -> None:
        manifest = build_full_phase1_acceptance_suite_manifest()
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

        for step in manifest['acceptance_suite_steps']:
            self.assertIn(step['command'], spec_doc)
            self.assertIn(step['command'], runbook_doc)
            self.assertIn(step['label'], spec_doc)

        for row in manifest['completion_board']:
            self.assertIn(row['board_item'], spec_doc)
            self.assertIn(row['evidence'], spec_doc)

        self.assertIn('historical alpha gate snapshot', alpha_doc.lower())
        self.assertIn(
            '2026-04-11-navly-v1-full-phase-1-acceptance-suite-and-completion-board.md',
            alpha_doc,
        )


if __name__ == '__main__':
    unittest.main()
