from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport, build_signed_request  # noqa: E402
from ingestion.staff_board_vertical_slice import _load_staff_board_dependency_entry, _pagination_total, run_staff_board_vertical_slice  # noqa: E402


class RecordingFixtureTransport:
    transport_kind = 'fixture'

    def __init__(self, fixture_pages_by_endpoint: dict[str, list[dict]]) -> None:
        self._transport = FixtureQinqinTransport(fixture_pages_by_endpoint)
        self.requests: list[dict[str, object]] = []

    def fetch_page(self, endpoint_contract_id: str, request_payload: dict[str, object]) -> dict[str, object]:
        self.requests.append({
            'endpoint_contract_id': endpoint_contract_id,
            'request_payload': dict(request_payload),
        })
        return self._transport.fetch_page(endpoint_contract_id, request_payload)


class FailingEndpointTransport:
    transport_kind = 'fixture'

    def __init__(
        self,
        fixture_pages_by_endpoint: dict[str, list[dict]],
        *,
        failing_endpoint_id: str,
        exception: Exception,
    ) -> None:
        self._transport = FixtureQinqinTransport(fixture_pages_by_endpoint)
        self._failing_endpoint_id = failing_endpoint_id
        self._exception = exception

    def fetch_page(self, endpoint_contract_id: str, request_payload: dict[str, object]) -> dict[str, object]:
        if endpoint_contract_id == self._failing_endpoint_id:
            raise self._exception
        return self._transport.fetch_page(endpoint_contract_id, request_payload)


class StaffBoardVerticalSliceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'staff_board' / 'qinqin_staff_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_run_kwargs(self) -> dict[str, object]:
        return {
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'requested_business_date': '2026-03-23',
            'app_secret': 'test-secret',
        }

    def test_build_signed_request_uses_endpoint_specific_body_params(self) -> None:
        person_request = build_signed_request(
            endpoint_contract_id='qinqin.staff.get_person_list.v1_5',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            page_index=1,
            page_size=20,
            app_secret='test-secret',
            staff_code='018',
        )
        self.assertEqual(sorted(person_request['payload'].keys()), ['OrgId', 'Sign'])

        clock_request = build_signed_request(
            endpoint_contract_id='qinqin.staff.get_tech_up_clock_list.v1_6',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            page_index=1,
            page_size=20,
            app_secret='test-secret',
            staff_code='018',
        )
        self.assertEqual(sorted(clock_request['payload'].keys()), ['Code', 'Etime', 'OrgId', 'Sign', 'Stime'])
        self.assertEqual(clock_request['payload']['Code'], '018')

    def test_build_signed_request_accepts_registry_defined_extra_body_params(self) -> None:
        request = build_signed_request(
            endpoint_contract_id='qinqin.member.get_user_trade_list.v1_4',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            app_secret='test-secret',
            extra_params={
                'member_card_id': 'card_001',
                'trade_type': 2,
            },
        )
        self.assertEqual(request['payload']['Id'], 'card_001')
        self.assertEqual(request['payload']['Type'], 2)
        self.assertIn('Sign', request['payload'])

    def test_vertical_slice_lands_staff_workforce_canonical_and_latest_state(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_staff_board_vertical_slice(
                transport=transport,
                output_root=tmpdir,
                **self._base_run_kwargs(),
            )

            self.assertEqual(result['capability_id'], 'navly.store.staff_board')
            self.assertEqual(result['service_object_id'], 'navly.service.store.staff_board')
            self.assertEqual(result['dependency_entry']['dependency_status'], 'phase_1_contract_frozen')
            self.assertEqual(
                result['dependency_entry']['required_endpoint_contract_ids'],
                [
                    'qinqin.staff.get_person_list.v1_5',
                    'qinqin.staff.get_tech_up_clock_list.v1_6',
                    'qinqin.staff.get_tech_market_list.v1_7',
                ],
            )
            self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'completed')
            self.assertEqual(len(result['historical_run_truth']['endpoint_runs']), 3)
            self.assertEqual(len(result['raw_replay']['raw_response_pages']), 3)
            self.assertEqual(len(result['raw_replay']['transport_replay_artifacts']), 3)
            self.assertEqual(len(result['canonical_artifacts']['staff']), 2)
            self.assertEqual(len(result['canonical_artifacts']['staff_item']), 3)
            self.assertEqual(len(result['canonical_artifacts']['tech_shift_item']), 2)
            self.assertEqual(len(result['canonical_artifacts']['tech_shift_summary']), 1)
            self.assertEqual(len(result['canonical_artifacts']['sales_commission']), 2)
            self.assertEqual(result['canonical_artifacts']['staff'][0]['source_endpoint_contract_id'], 'qinqin.staff.get_person_list.v1_5')
            self.assertEqual(result['canonical_artifacts']['staff_item'][0]['staff_id'], 'staff_001')
            self.assertEqual(result['canonical_artifacts']['tech_shift_summary'][0]['main_total'], 2)
            self.assertEqual(result['canonical_artifacts']['sales_commission'][0]['sales_commission_id'], 'sales_001')
            self.assertEqual(len(result['latest_state_artifacts']['latest_usable_endpoint_states']), 3)
            self.assertEqual(
                result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
                'backbone_ready',
            )
            self.assertTrue(Path(tmpdir, 'canonical', 'staff.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'staff_item.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'tech_shift_item.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'tech_shift_summary.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'sales_commission.json').exists())
            self.assertTrue(Path(tmpdir, 'latest-state', 'latest-usable-endpoint-state.json').exists())

    def test_source_empty_is_latest_usable_and_keeps_backbone_ready(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.staff.get_tech_market_list.v1_7'] = [
            {
                'Code': 404,
                'Msg': '暂无数据',
                'RetData': [],
            }
        ]
        result = run_staff_board_vertical_slice(
            transport=FixtureQinqinTransport(fixture_bundle),
            **self._base_run_kwargs(),
        )
        market_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_tech_market_list.v1_7'
        ][0]
        market_state = [
            item for item in result['latest_state_artifacts']['latest_usable_endpoint_states']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_tech_market_list.v1_7'
        ][0]
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'completed')
        self.assertEqual(market_endpoint['endpoint_status'], 'source_empty')
        self.assertEqual(market_state['availability_status'], 'source_empty')
        self.assertEqual(len(result['canonical_artifacts']['sales_commission']), 0)
        self.assertEqual(
            result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
            'backbone_ready',
        )

    def test_missing_capability_dependency_entry_raises_descriptive_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            directory = root / 'directory'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'capability-dependency-registry.seed.json').write_text(json.dumps({
                'entries': [],
            }), encoding='utf-8')
            with self.assertRaisesRegex(KeyError, 'Missing capability dependency entry'):
                _load_staff_board_dependency_entry(data_platform_root=root)

    def test_pagination_total_ignores_non_object_retdata(self) -> None:
        self.assertEqual(
            _pagination_total({'RetData': []}, 7),
            7,
        )

    def test_clock_source_empty_does_not_land_summary_rows(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.staff.get_tech_up_clock_list.v1_6'] = [
            {
                'Code': 404,
                'Msg': '暂无数据',
                'RetData': {
                    'Items': [],
                    'Main': {
                        'Total': 0,
                    },
                    'Extra': {
                        'Total': 0,
                    },
                    'TotalClock': 0,
                },
            }
        ]
        result = run_staff_board_vertical_slice(
            transport=FixtureQinqinTransport(fixture_bundle),
            **self._base_run_kwargs(),
        )
        shift_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_tech_up_clock_list.v1_6'
        ][0]
        self.assertEqual(shift_endpoint['endpoint_status'], 'source_empty')
        self.assertEqual(len(result['canonical_artifacts']['tech_shift_item']), 0)
        self.assertEqual(len(result['canonical_artifacts']['tech_shift_summary']), 0)

    def test_source_sign_error_is_classified(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.staff.get_tech_market_list.v1_7'] = [
            {
                'Code': -500,
                'Msg': '验签失败',
                'RetData': [],
            }
        ]
        result = run_staff_board_vertical_slice(
            transport=FixtureQinqinTransport(fixture_bundle),
            **self._base_run_kwargs(),
        )
        market_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_tech_market_list.v1_7'
        ][0]
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'partial_failed')
        self.assertEqual(market_endpoint['error_taxonomy'], 'source_sign_error')
        self.assertEqual(market_endpoint['error_code'], '-500')

    def test_source_auth_error_is_classified(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.staff.get_tech_up_clock_list.v1_6'] = [
            {
                'Code': -401,
                'Msg': '未授权访问',
                'RetData': {},
            }
        ]
        result = run_staff_board_vertical_slice(
            transport=FixtureQinqinTransport(fixture_bundle),
            **self._base_run_kwargs(),
        )
        shift_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_tech_up_clock_list.v1_6'
        ][0]
        self.assertEqual(shift_endpoint['error_taxonomy'], 'source_auth_error')
        self.assertEqual(shift_endpoint['endpoint_status'], 'failed')

    def test_source_schema_error_is_classified(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.staff.get_person_list.v1_5'] = [
            {
                'Code': 200,
                'Msg': '操作成功',
                'RetData': {},
            }
        ]
        result = run_staff_board_vertical_slice(
            transport=FixtureQinqinTransport(fixture_bundle),
            **self._base_run_kwargs(),
        )
        person_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_person_list.v1_5'
        ][0]
        self.assertEqual(person_endpoint['error_taxonomy'], 'source_schema_error')
        self.assertEqual(person_endpoint['error_code'], 'INVALID_RESPONSE_SHAPE')

    def test_transport_error_is_classified(self) -> None:
        transport = FailingEndpointTransport(
            self._fixture_bundle(),
            failing_endpoint_id='qinqin.staff.get_person_list.v1_5',
            exception=TimeoutError('timed out'),
        )
        result = run_staff_board_vertical_slice(
            transport=transport,
            **self._base_run_kwargs(),
        )
        person_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.staff.get_person_list.v1_5'
        ][0]
        self.assertEqual(person_endpoint['error_taxonomy'], 'transport_timeout_error')
        self.assertTrue(person_endpoint['retryable'])

    def test_staff_code_filter_only_hits_filterable_endpoints(self) -> None:
        transport = RecordingFixtureTransport(self._fixture_bundle())
        result = run_staff_board_vertical_slice(
            transport=transport,
            staff_code='018',
            **self._base_run_kwargs(),
        )
        requests_by_endpoint = {
            item['endpoint_contract_id']: item['request_payload']
            for item in transport.requests
        }
        self.assertNotIn('Code', requests_by_endpoint['qinqin.staff.get_person_list.v1_5'])
        self.assertEqual(requests_by_endpoint['qinqin.staff.get_tech_up_clock_list.v1_6']['Code'], '018')
        self.assertEqual(requests_by_endpoint['qinqin.staff.get_tech_market_list.v1_7']['Code'], '018')
        self.assertEqual(result['canonical_artifacts']['tech_shift_item'][0]['requested_staff_code'], '018')
        self.assertEqual(result['canonical_artifacts']['sales_commission'][0]['requested_staff_code'], '018')


if __name__ == '__main__':
    unittest.main()
