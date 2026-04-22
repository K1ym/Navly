from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


class BusinessDayBoundaryPolicyRegistryTest(unittest.TestCase):
    def _load_directory_registry(self) -> dict:
        path = DATA_PLATFORM_ROOT / 'directory' / 'business-day-boundary-policy.seed.json'
        return json.loads(path.read_text(encoding='utf-8'))

    def _load_contract_entry(self) -> dict:
        path = DATA_PLATFORM_ROOT / 'contracts' / 'business-day-boundary-policy-entry.contract.seed.json'
        return json.loads(path.read_text(encoding='utf-8'))

    def _load_contract_ownership(self) -> dict:
        path = DATA_PLATFORM_ROOT / 'contracts' / 'contract-ownership.seed.json'
        return json.loads(path.read_text(encoding='utf-8'))

    def test_contract_ownership_includes_business_day_boundary_policy_entry(self) -> None:
        ownership = self._load_contract_ownership()
        self.assertIn('business_day_boundary_policy_entry', ownership['data_platform_owned_contracts'])

    def test_registry_has_expected_override_order_and_metric_domains(self) -> None:
        registry = self._load_directory_registry()
        self.assertEqual(registry['registry_name'], 'business_day_boundary_policy_registry')
        self.assertEqual(registry['override_resolution_order'], ['store_ref', 'org_ref', 'global_default'])
        self.assertIn('store_operating_day', registry['supported_metric_domains'])
        self.assertIn('store_daily_overview', registry['supported_metric_domains'])

    def test_registry_entries_cover_global_org_and_store_layers(self) -> None:
        registry = self._load_directory_registry()
        scope_kinds = {entry['scope_kind'] for entry in registry['entries']}
        self.assertEqual(scope_kinds, {'global_default', 'org_ref', 'store_ref'})

    def test_contract_fields_match_registry_entries(self) -> None:
        contract = self._load_contract_entry()
        registry = self._load_directory_registry()
        required_fields = set(contract['fields'])
        for entry in registry['entries']:
            self.assertTrue(required_fields.issubset(entry.keys()))

    def test_policy_entries_have_unique_resolution_keys_and_valid_time_format(self) -> None:
        registry = self._load_directory_registry()
        seen: set[tuple[str, str, str, str]] = set()
        hhmm = re.compile(r'^\d{2}:\d{2}$')
        for entry in registry['entries']:
            key = (
                entry['metric_domain'],
                entry['scope_kind'],
                entry['scope_ref'],
                entry['effective_from'],
            )
            self.assertNotIn(key, seen)
            seen.add(key)
            self.assertRegex(entry['business_day_start_local_time'], hhmm)
            self.assertRegex(entry['business_day_end_exclusive_local_time'], hhmm)
            self.assertEqual(entry['policy_status'], 'policy_frozen')
