from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _collect_table_rows(text: str, start_heading: str | None = None) -> list[dict[str, str]]:
    lines = text.splitlines()
    rows: list[dict[str, str]] = []
    in_section = start_heading is None
    header: list[str] | None = None

    for line in lines:
        if start_heading and line.startswith(start_heading):
            in_section = True
            header = None
            continue
        if in_section and start_heading and line.startswith('## ') and not line.startswith(start_heading):
            break
        if not in_section or not line.startswith('| '):
            continue
        cols = [col.strip() for col in line.strip().strip('|').split('|')]
        if not cols:
            continue
        if cols[0] == '参数名' or cols[0] == 'Domain':
            header = cols
            continue
        if cols[0].startswith('---') or header is None:
            continue
        rows.append(dict(zip(header, cols)))
    return rows


def _extract_backticks(value: str) -> list[str]:
    return re.findall(r'`([^`]+)`', value)


class QinqinContractGovernanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        directory = DATA_PLATFORM_ROOT / 'directory'
        cls.endpoint_contracts = _load_json(directory / 'endpoint-contracts.seed.json')
        cls.parameter_registry = _load_json(directory / 'endpoint-parameter-canonicalization.seed.json')
        cls.field_catalog = _load_json(directory / 'endpoint-field-catalog.seed.json')
        cls.field_landing = _load_json(directory / 'field-landing-policy.seed.json')
        cls.variance_registry = _load_json(directory / 'source-variance.seed.json')
        cls.source_systems = _load_json(directory / 'source-systems.seed.json')

        cls.endpoint_entries = {
            entry['endpoint_contract_id']: entry
            for entry in cls.endpoint_contracts['entries']
        }
        cls.actual_endpoint_ids = {
            entry['endpoint_contract_id']
            for entry in cls.endpoint_contracts['entries']
            if entry['domain'] != 'shared'
        }
        cls.endpoint_bindings = {
            entry['endpoint_contract_id']: entry
            for entry in cls.endpoint_contracts['endpoint_governance_bindings']
        }
        cls.parameter_entries = {
            entry['parameter_key']: entry
            for entry in cls.parameter_registry['entries']
        }
        cls.field_catalog_entries = {
            entry['endpoint_contract_id']: entry
            for entry in cls.field_catalog['entries']
        }
        cls.landing_policies = {
            entry['policy_id']: entry
            for entry in cls.field_landing['entries']
        }
        cls.variance_entries = {
            entry['variance_id']: entry
            for entry in cls.variance_registry['entries']
        }
        cls.auth_profiles = {
            entry['auth_profile_id']: entry
            for entry in cls.source_systems['auth_profiles']
        }
        cls.signature_rules = {
            entry['signature_rule_id']: entry
            for entry in cls.source_systems['signature_rules']
        }
        cls.operational_windows = {
            entry['operational_window_profile_id']: entry
            for entry in cls.source_systems['operational_window_profiles']
        }

    def _doc_text(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding='utf-8')

    def test_endpoint_registry_matches_manifest_and_bindings(self) -> None:
        self.assertEqual(self.endpoint_contracts['status'], 'phase_1_contract_frozen')
        self.assertEqual(len(self.actual_endpoint_ids), 8)
        self.assertIn('qinqin.v1_1.shared', self.endpoint_entries)

        manifest_rows = _collect_table_rows(
            self._doc_text('docs/api/qinqin/endpoint-manifest.md')
        )
        self.assertEqual(len(manifest_rows), 8)
        self.assertEqual(set(self.endpoint_bindings.keys()), self.actual_endpoint_ids)

        for row in manifest_rows:
            endpoint_contract_id = _extract_backticks(row['Endpoint Contract ID'])[0]
            entry = self.endpoint_entries[endpoint_contract_id]
            self.assertEqual(entry['domain'], row['Domain'])
            self.assertEqual(entry['version'], row['Version'])
            self.assertEqual(entry['display_name'], row['Name'])
            self.assertEqual(entry['method'], _extract_backticks(row['Method'])[0])
            self.assertEqual(entry['path'], _extract_backticks(row['Path'])[0])
            self.assertEqual(
                entry['structured_targets'],
                _extract_backticks(row['Structured Targets']),
            )

            binding = self.endpoint_bindings[endpoint_contract_id]
            self.assertEqual(binding['field_catalog_entry_id'], endpoint_contract_id)
            self.assertIn(binding['auth_profile_id'], self.auth_profiles)
            self.assertIn(binding['signature_rule_id'], self.signature_rules)
            self.assertIn(binding['operational_window_profile_id'], self.operational_windows)
            for policy_id in binding['landing_policy_ids']:
                self.assertIn(policy_id, self.landing_policies)
            for variance_id in binding['variance_ids']:
                self.assertIn(variance_id, self.variance_entries)

        self.assertEqual(
            self.source_systems['operational_window_profiles'][0]['formal_access_window'],
            '03:00-04:00',
        )
        self.assertEqual(
            self.source_systems['operational_window_profiles'][0]['timezone'],
            'Asia/Shanghai',
        )

    def test_parameter_registry_covers_request_docs(self) -> None:
        self.assertEqual(self.parameter_registry['status'], 'phase_1_contract_frozen')

        for endpoint_contract_id in self.actual_endpoint_ids:
            doc_path = self.endpoint_entries[endpoint_contract_id]['truth_source_doc']
            text = self._doc_text(doc_path)
            body_rows = _collect_table_rows(text, '## 请求 Body 参数')
            header_rows = _collect_table_rows(text, '## 请求 Header 参数')
            binding = self.endpoint_bindings[endpoint_contract_id]
            bound_keys = set(binding['required_parameter_keys']) | set(binding['optional_parameter_keys'])

            for row in body_rows:
                wire_name = row['参数名']
                required = row['是否必填'] == '是'
                matches = [
                    key for key in bound_keys
                    if self.parameter_entries[key]['request_location'] == 'body'
                    and wire_name in self.parameter_entries[key]['known_wire_variants']
                ]
                self.assertEqual(
                    len(matches), 1,
                    f'Expected exactly one body parameter match for {endpoint_contract_id} {wire_name}, got {matches}',
                )
                key = matches[0]
                if required:
                    self.assertIn(key, binding['required_parameter_keys'])
                else:
                    self.assertIn(key, binding['optional_parameter_keys'])

            modeled_header_names = {'Authorization', 'Token'}
            for row in header_rows:
                wire_name = row['参数名']
                if wire_name not in modeled_header_names:
                    continue
                matches = [
                    key for key in bound_keys
                    if self.parameter_entries[key]['request_location'] == 'header'
                    and wire_name in self.parameter_entries[key]['known_wire_variants']
                ]
                self.assertEqual(
                    len(matches), 1,
                    f'Expected exactly one header parameter match for {endpoint_contract_id} {wire_name}, got {matches}',
                )
                entry = self.parameter_entries[matches[0]]
                self.assertEqual(entry['value_source'], 'runtime_secret')
                self.assertIn('runtime_secret_ref', entry)

            if endpoint_contract_id == 'qinqin.staff.get_tech_commission_set_list.v1_8':
                auth_profile = self.auth_profiles[binding['auth_profile_id']]
                self.assertEqual(
                    auth_profile['runtime_secret_headers'],
                    ['Authorization', 'Token'],
                )
                self.assertEqual(
                    auth_profile['required_static_headers']['Content-Type'],
                    'application/json',
                )

        self.assertEqual(
            self.parameter_entries['org_id']['preferred_wire_name'],
            'OrgId',
        )
        self.assertEqual(
            self.parameter_entries['page_index']['known_wire_variants'],
            ['PageIndex', 'Page'],
        )

    def test_field_catalog_covers_response_docs_and_landing_policies(self) -> None:
        self.assertEqual(self.field_catalog['status'], 'phase_1_contract_frozen')
        self.assertTrue((DATA_PLATFORM_ROOT / 'directory' / 'endpoint-field-catalog.seed.json').exists())
        self.assertFalse((DATA_PLATFORM_ROOT / 'directory' / 'endpoint-field-catalog.placeholder.json').exists())
        self.assertEqual(set(self.field_catalog_entries.keys()), self.actual_endpoint_ids)

        allowed_path_kinds = {
            'response_status',
            'response_message',
            'payload_root',
            'page_total',
            'record_collection',
            'record_field',
            'nested_record_collection',
            'nested_record_field',
            'summary_object',
            'summary_field',
        }

        for endpoint_contract_id in self.actual_endpoint_ids:
            doc_path = self.endpoint_entries[endpoint_contract_id]['truth_source_doc']
            rows = _collect_table_rows(self._doc_text(doc_path), '## 响应示例')
            expected = {
                row['参数名']: row['参数类型']
                for row in rows
                if row['参数名'].startswith(('Code', 'Msg', 'RetData'))
            }

            entry = self.field_catalog_entries[endpoint_contract_id]
            actual_fields = entry['response_fields']
            self.assertEqual(entry['field_count'], len(actual_fields))
            self.assertEqual(len(actual_fields), len({item['field_path'] for item in actual_fields}))

            actual = {item['field_path']: item['data_type'] for item in actual_fields}
            self.assertEqual(actual, expected)

            for item in actual_fields:
                self.assertIn(item['path_kind'], allowed_path_kinds)
                policy = self.landing_policies[item['landing_policy_id']]
                self.assertEqual(policy['endpoint_contract_id'], endpoint_contract_id)

        self.assertNotIn('placeholder_only', json.dumps(self.field_catalog, ensure_ascii=False))

    def test_variance_register_covers_known_qinqin_drifts(self) -> None:
        expected_variance_ids = {
            'qinqin.param.page-name-drift',
            'qinqin.param.start-time-name-drift',
            'qinqin.param.end-time-name-drift',
            'qinqin.param.org-id-name-drift',
            'qinqin.path.consume-bill-legacy-path-required',
            'qinqin.path.recharge-bill-legacy-path-required',
            'qinqin.path.user-trade-legacy-path-required',
            'qinqin.path.person-list-legacy-path-required',
            'qinqin.path.tech-up-clock-legacy-path-required',
            'qinqin.path.tech-market-legacy-path-required',
            'qinqin.path.tech-commission-set-legacy-path-required',
            'qinqin.response.user-trade-retdata-root-shape-drift',
            'qinqin.response.person-list-retdata-root-shape-drift',
            'qinqin.response.tech-market-retdata-root-shape-drift',
            'qinqin.auth.tech-commission-set-runtime-headers-required',
            'qinqin.response.tech-commission-set-source-empty-governed',
            'qinqin.field.consume-bill-payment-source-typo',
        }
        self.assertEqual(set(self.variance_entries.keys()), expected_variance_ids)

        for binding in self.endpoint_bindings.values():
            for variance_id in binding['variance_ids']:
                self.assertIn(variance_id, self.variance_entries)

        self.assertEqual(
            self.variance_entries['qinqin.auth.tech-commission-set-runtime-headers-required']['variance_kind'],
            'auth_header_requirement',
        )
        self.assertEqual(
            self.variance_entries['qinqin.response.tech-commission-set-source-empty-governed']['variance_kind'],
            'response_empty_semantics',
        )
        self.assertIn(
            'qinqin.response.tech-commission-set-source-empty-governed',
            self.endpoint_bindings['qinqin.staff.get_tech_commission_set_list.v1_8']['variance_ids'],
        )
        self.assertEqual(
            self.variance_entries['qinqin.response.user-trade-retdata-root-shape-drift']['canonical_form'],
            'RetData=array_record_list',
        )


if __name__ == '__main__':
    unittest.main()
