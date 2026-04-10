from __future__ import annotations

import json
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


class CapabilityDependencyRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-dependency-registry.seed.json')
        cls.contract = _load_json(DATA_PLATFORM_ROOT / 'contracts' / 'capability-dependency-entry.contract.seed.json')
        cls.contract_ownership = _load_json(DATA_PLATFORM_ROOT / 'contracts' / 'contract-ownership.seed.json')
        cls.reference_text = (
            REPO_ROOT / 'docs' / 'reference' / 'data-platform' / 'capability-dependency-registry.md'
        ).read_text(encoding='utf-8')
        cls.spec_text = (
            REPO_ROOT / 'docs' / 'specs' / 'data-platform' / '2026-04-10-phase-1-capability-dependency-registry.md'
        ).read_text(encoding='utf-8')

    def test_registry_contract_and_ownership_are_wired(self) -> None:
        self.assertEqual(self.registry['registry_name'], 'capability_dependency_registry')
        self.assertEqual(self.registry['status'], 'phase_1_contract_frozen')
        self.assertFalse(
            (DATA_PLATFORM_ROOT / 'directory' / 'capability-dependency-registry.placeholder.json').exists()
        )
        self.assertIn(
            'capability_dependency_entry',
            self.contract_ownership['data_platform_owned_contracts'],
        )
        self.assertEqual(self.contract['contract_name'], 'capability_dependency_entry')
        self.assertEqual(self.contract['owner'], 'data-platform')
        self.assertEqual(self.contract['status'], 'phase_1_contract_frozen')

    def test_seed_entries_follow_contract_shape(self) -> None:
        expected_fields = set(self.contract['fields'])
        allowed_dependency_kind = set(self.contract['allowed_values']['dependency_kind'])
        allowed_dependency_status = set(self.contract['allowed_values']['dependency_status'])

        self.assertEqual(len(self.registry['entries']), 4)
        seen_capability_ids: set[str] = set()

        for entry in self.registry['entries']:
            self.assertEqual(set(entry.keys()), expected_fields)
            self.assertIn(entry['dependency_kind'], allowed_dependency_kind)
            self.assertIn(entry['dependency_status'], allowed_dependency_status)
            self.assertTrue(entry['truth_source_docs'])
            for relative_path in entry['truth_source_docs']:
                self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path)
            seen_capability_ids.add(entry['capability_id'])

            if entry['dependency_kind'] == 'input_data':
                self.assertTrue(entry['required_endpoint_contract_ids'])
                self.assertTrue(entry['required_canonical_datasets'])
                self.assertEqual(entry['required_service_object_ids'], [])
            if entry['dependency_kind'] == 'projection':
                self.assertEqual(entry['required_endpoint_contract_ids'], [])
                self.assertEqual(entry['required_canonical_datasets'], [])
                self.assertTrue(entry['required_service_object_ids'])

        self.assertEqual(
            seen_capability_ids,
            {
                'navly.store.member_insight',
                'navly.store.daily_overview',
                'navly.store.staff_board',
                'navly.store.finance_summary',
            },
        )

    def test_docs_mark_registry_as_governed_matrix_not_placeholder(self) -> None:
        for text in (self.reference_text, self.spec_text):
            self.assertIn('governed object', text)
            self.assertIn('dependency matrix', text)
            self.assertIn('daily_overview', text)
            self.assertIn('staff_board', text)
            self.assertIn('finance_summary', text)
            self.assertIn('member_insight', text)
            self.assertIn('placeholder', text)


if __name__ == '__main__':
    unittest.main()
