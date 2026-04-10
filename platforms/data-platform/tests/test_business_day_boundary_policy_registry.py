from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _resolve_policy(
    entries: list[dict],
    resolution_hierarchy: list[str],
    *,
    org_ref: str | None,
    store_ref: str | None,
) -> dict:
    matches_by_selector: dict[str, list[dict]] = {selector: [] for selector in resolution_hierarchy}

    for entry in entries:
        selector_kind = entry['selector_kind']
        if selector_kind == 'store_ref' and store_ref and entry['store_ref'] == store_ref:
            matches_by_selector['store_ref'].append(entry)
        elif selector_kind == 'org_ref' and org_ref and entry['org_ref'] == org_ref:
            matches_by_selector['org_ref'].append(entry)
        elif selector_kind == 'global_default':
            matches_by_selector['global_default'].append(entry)

    for selector_kind in resolution_hierarchy:
        matches = matches_by_selector[selector_kind]
        if not matches:
            continue
        if len(matches) != 1:
            raise AssertionError(f'Expected exactly one {selector_kind} match, got {matches}')
        return matches[0]

    raise AssertionError('Expected at least one matching business-day boundary policy')


class BusinessDayBoundaryPolicyRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = _load_json(
            DATA_PLATFORM_ROOT / 'directory' / 'business-day-boundary-policy.seed.json'
        )
        cls.contract = _load_json(
            DATA_PLATFORM_ROOT / 'contracts' / 'business-day-boundary-policy-entry.contract.seed.json'
        )
        cls.contract_ownership = _load_json(
            DATA_PLATFORM_ROOT / 'contracts' / 'contract-ownership.seed.json'
        )
        cls.reference_text = (
            REPO_ROOT / 'docs' / 'reference' / 'data-platform' / 'business-day-boundary-policy-registry.md'
        ).read_text(encoding='utf-8')
        cls.spec_text = (
            REPO_ROOT / 'docs' / 'specs' / 'data-platform' / '2026-04-10-business-day-boundary-policy-registry.md'
        ).read_text(encoding='utf-8')

    def test_registry_contract_and_ownership_are_wired(self) -> None:
        self.assertEqual(self.registry['registry_name'], 'business_day_boundary_policy_registry')
        self.assertEqual(self.registry['status'], 'phase_1_contract_frozen')
        self.assertEqual(
            self.registry['resolution_hierarchy'],
            ['store_ref', 'org_ref', 'global_default'],
        )
        self.assertIn(
            'business_day_boundary_policy_entry',
            self.contract_ownership['data_platform_owned_contracts'],
        )
        self.assertEqual(self.contract['contract_name'], 'business_day_boundary_policy_entry')
        self.assertEqual(self.contract['owner'], 'data-platform')
        self.assertEqual(self.contract['status'], 'phase_1_contract_frozen')

    def test_seed_entries_follow_contract_shape(self) -> None:
        expected_fields = set(self.contract['fields'])
        allowed_selector_kinds = set(self.contract['allowed_values']['selector_kind'])
        allowed_policy_status = set(self.contract['allowed_values']['policy_status'])

        self.assertEqual(len(self.registry['entries']), 1)

        for entry in self.registry['entries']:
            self.assertEqual(set(entry.keys()), expected_fields)
            self.assertIn(entry['selector_kind'], allowed_selector_kinds)
            self.assertIn(entry['policy_status'], allowed_policy_status)
            self.assertRegex(entry['business_day_boundary_local_time'], r'^\d{2}:\d{2}:\d{2}$')
            self.assertTrue(entry['truth_source_docs'])
            for relative_path in entry['truth_source_docs']:
                self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path)

            if entry['selector_kind'] == 'global_default':
                self.assertIsNone(entry['org_ref'])
                self.assertIsNone(entry['store_ref'])
            elif entry['selector_kind'] == 'org_ref':
                self.assertTrue(entry['org_ref'])
                self.assertIsNone(entry['store_ref'])
            elif entry['selector_kind'] == 'store_ref':
                self.assertTrue(entry['store_ref'])

        self.assertEqual(
            self.registry['entries'][0]['business_day_boundary_local_time'],
            '03:00:00',
        )
        self.assertEqual(
            self.registry['entries'][0]['timezone'],
            'Asia/Shanghai',
        )

    def test_docs_mark_registry_as_governed_object_not_runtime_config(self) -> None:
        for text in (self.reference_text, self.spec_text):
            self.assertIn('governed object', text)
            self.assertIn('不是 runtime config', text)
            self.assertIn('global_default', text)
            self.assertIn('org_ref', text)
            self.assertIn('store_ref', text)

        self.assertIn('03:00:00', self.reference_text)
        self.assertIn('03:00:00', self.spec_text)
        self.assertIn('Asia/Shanghai', self.reference_text)
        self.assertIn('Asia/Shanghai', self.spec_text)

    def test_resolution_hierarchy_prefers_store_then_org_then_global_default(self) -> None:
        global_default = self.registry['entries'][0]
        synthetic_org_override = {
            **global_default,
            'policy_id': 'synthetic.org.override',
            'selector_kind': 'org_ref',
            'org_ref': 'navly:scope:org:demo-org-001',
            'business_day_boundary_local_time': '04:00:00',
            'notes': 'Synthetic org override used to freeze resolution semantics in tests.',
        }
        synthetic_store_override = {
            **global_default,
            'policy_id': 'synthetic.store.override',
            'selector_kind': 'store_ref',
            'org_ref': 'navly:scope:org:demo-org-001',
            'store_ref': 'navly:scope:store:demo-store-001',
            'business_day_boundary_local_time': '05:00:00',
            'notes': 'Synthetic store override used to freeze resolution semantics in tests.',
        }
        resolution_entries = [
            global_default,
            synthetic_org_override,
            synthetic_store_override,
        ]

        matched_store = _resolve_policy(
            resolution_entries,
            self.registry['resolution_hierarchy'],
            org_ref='navly:scope:org:demo-org-001',
            store_ref='navly:scope:store:demo-store-001',
        )
        self.assertEqual(matched_store['policy_id'], 'synthetic.store.override')

        matched_org = _resolve_policy(
            resolution_entries,
            self.registry['resolution_hierarchy'],
            org_ref='navly:scope:org:demo-org-001',
            store_ref='navly:scope:store:other-store',
        )
        self.assertEqual(matched_org['policy_id'], 'synthetic.org.override')

        matched_global = _resolve_policy(
            resolution_entries,
            self.registry['resolution_hierarchy'],
            org_ref='navly:scope:org:other-org',
            store_ref='navly:scope:store:other-store',
        )
        self.assertEqual(matched_global['policy_id'], 'navly.business_day_boundary.global_default')


if __name__ == '__main__':
    unittest.main()
