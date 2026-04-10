from __future__ import annotations

import json
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


class ServiceSurfaceRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.capability_registry = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-registry.seed.json')
        cls.service_bindings = _load_json(DATA_PLATFORM_ROOT / 'directory' / 'capability-service-bindings.seed.json')
        cls.contract_ownership = _load_json(DATA_PLATFORM_ROOT / 'contracts' / 'contract-ownership.seed.json')

    def test_phase_one_store_capabilities_mark_owner_surfaces_as_published(self) -> None:
        self.assertEqual(self.capability_registry['status'], 'phase_1_owner_surface_published')
        statuses_by_capability = {
            entry['capability_id']: entry['status']
            for entry in self.capability_registry['entries']
        }
        self.assertEqual(statuses_by_capability['navly.store.member_insight'], 'owner_surface_published')
        self.assertEqual(statuses_by_capability['navly.store.daily_overview'], 'owner_surface_published')
        self.assertEqual(statuses_by_capability['navly.store.staff_board'], 'owner_surface_published')
        self.assertEqual(statuses_by_capability['navly.store.finance_summary'], 'owner_surface_published')

    def test_phase_one_default_service_bindings_are_published(self) -> None:
        self.assertEqual(self.service_bindings['status'], 'phase_1_owner_surface_published')
        statuses_by_service_object = {
            entry['service_object_id']: entry['status']
            for entry in self.service_bindings['entries']
        }
        self.assertEqual(statuses_by_service_object['navly.service.store.member_insight'], 'owner_surface_published')
        self.assertEqual(statuses_by_service_object['navly.service.store.daily_overview'], 'owner_surface_published')
        self.assertEqual(statuses_by_service_object['navly.service.store.staff_board'], 'owner_surface_published')
        self.assertEqual(statuses_by_service_object['navly.service.store.finance_summary'], 'owner_surface_published')
        self.assertIn('companion explanation object', self.service_bindings['notes'])

    def test_contract_ownership_tracks_shared_explanation_object_dependency(self) -> None:
        self.assertIn('capability_explanation_object', self.contract_ownership['shared_contract_dependencies'])


if __name__ == '__main__':
    unittest.main()
