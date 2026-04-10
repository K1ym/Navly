from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import FixtureQinqinTransport, LiveQinqinTransport, build_signed_request  # noqa: E402
from ingestion.finance_summary_vertical_slice import _normalized_page_payload, run_finance_summary_vertical_slice  # noqa: E402


class _TimeoutOnEndpointTransport:
    transport_kind = 'fixture'

    def __init__(self, delegate: FixtureQinqinTransport, endpoint_contract_id: str) -> None:
        self._delegate = delegate
        self._endpoint_contract_id = endpoint_contract_id

    def fetch_page(self, endpoint_contract_id: str, request_payload: dict[str, object]) -> dict[str, object]:
        if endpoint_contract_id == self._endpoint_contract_id:
            raise TimeoutError('timed out while talking to qinqin')
        return self._delegate.fetch_page(endpoint_contract_id, request_payload)


class _QinqinTestServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], responses_by_path: dict[str, object]) -> None:
        super().__init__(server_address, _QinqinTestRequestHandler)
        self.responses_by_path = responses_by_path


class _QinqinTestRequestHandler(BaseHTTPRequestHandler):
    server: _QinqinTestServer

    def do_POST(self) -> None:  # noqa: N802
        response_entry = self.server.responses_by_path.get(self.path)
        if response_entry is None:
            status_code = 404
            response_payload: object = {'error': 'not found'}
        elif isinstance(response_entry, tuple):
            status_code, response_payload = response_entry
        else:
            status_code = 200
            response_payload = response_entry

        response_body = json.dumps(response_payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _serve_qinqin_responses(responses_by_path: dict[str, object]):
    server = _QinqinTestServer(('127.0.0.1', 0), responses_by_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f'http://{host}:{port}'
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class FinanceSummaryVerticalSliceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'finance_summary' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_run_kwargs(self) -> dict[str, object]:
        return {
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'requested_business_date': '2026-03-23',
            'app_secret': 'test-secret',
        }

    def test_build_signed_request_supports_finance_endpoints(self) -> None:
        recharge_request = build_signed_request(
            endpoint_contract_id='qinqin.member.get_recharge_bill_list.v1_3',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            app_secret='test-secret',
            page_index=1,
            page_size=50,
        )
        self.assertEqual(
            sorted(recharge_request['payload'].keys()),
            sorted(['OrgId', 'Stime', 'Etime', 'PageIndex', 'PageSize', 'Sign']),
        )

        trade_request = build_signed_request(
            endpoint_contract_id='qinqin.member.get_user_trade_list.v1_4',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            app_secret='test-secret',
            member_card_id='card_001',
            trade_type=2,
        )
        self.assertEqual(
            sorted(trade_request['payload'].keys()),
            sorted(['OrgId', 'Stime', 'Etime', 'Id', 'Type', 'Sign']),
        )

    def test_build_signed_request_ignores_required_runtime_header_parameters(self) -> None:
        request = build_signed_request(
            endpoint_contract_id='qinqin.staff.get_tech_commission_set_list.v1_8',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            app_secret='test-secret',
        )
        self.assertEqual(
            sorted(request['payload'].keys()),
            sorted(['OrgId', 'Sign']),
        )
        self.assertTrue(request['payload']['Sign'])

    def test_normalized_page_payload_dispatches_by_finance_endpoint(self) -> None:
        fixture_bundle = self._fixture_bundle()
        recharge_payload = _normalized_page_payload(
            endpoint_contract_id='qinqin.member.get_recharge_bill_list.v1_3',
            response_envelope=fixture_bundle['qinqin.member.get_recharge_bill_list.v1_3'][0],
        )
        trade_payload = _normalized_page_payload(
            endpoint_contract_id='qinqin.member.get_user_trade_list.v1_4',
            response_envelope=fixture_bundle['qinqin.member.get_user_trade_list.v1_4'][0],
        )

        self.assertEqual(recharge_payload['total'], 1)
        self.assertEqual(len(recharge_payload['rows']), 1)
        self.assertEqual(trade_payload['total'], 1)
        self.assertEqual(len(trade_payload['rows']), 1)

        with self.assertRaises(KeyError):
            _normalized_page_payload(
                endpoint_contract_id='qinqin.staff.get_person_list.v1_5',
                response_envelope={'Code': 200, 'Msg': '操作成功', 'RetData': []},
            )

    def test_finance_summary_vertical_slice_success_path(self) -> None:
        transport = FixtureQinqinTransport(self._fixture_bundle())
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_finance_summary_vertical_slice(
                transport=transport,
                output_root=tmpdir,
                **self._base_run_kwargs(),
            )

            self.assertTrue(Path(tmpdir, 'canonical', 'recharge_bill.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'account_trade.json').exists())
            self.assertTrue(Path(tmpdir, 'latest-state', 'finance-summary-prerequisite-state.json').exists())

        self.assertEqual(result['capability_id'], 'navly.store.finance_summary')
        self.assertEqual(result['service_object_id'], 'navly.service.store.finance_summary')
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'completed')
        self.assertEqual(len(result['historical_run_truth']['endpoint_runs']), 2)
        self.assertTrue(all(run['terminal_outcome_category'] == 'success' for run in result['historical_run_truth']['endpoint_runs']))
        self.assertEqual(len(result['raw_replay']['raw_response_pages']), 2)
        self.assertEqual(len(result['canonical_artifacts']['recharge_bill']), 1)
        self.assertEqual(len(result['canonical_artifacts']['recharge_bill_payment']), 1)
        self.assertEqual(len(result['canonical_artifacts']['recharge_bill_sales']), 1)
        self.assertEqual(len(result['canonical_artifacts']['recharge_bill_ticket']), 1)
        self.assertEqual(len(result['canonical_artifacts']['account_trade']), 1)
        self.assertEqual(len(result['latest_state_artifacts']['latest_usable_endpoint_states']), 2)
        self.assertEqual(
            result['latest_state_artifacts']['finance_summary_prerequisite_state']['prerequisite_status'],
            'ready',
        )

    def test_finance_summary_marks_404_no_data_as_source_empty(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_user_trade_list.v1_4'] = [
            {
                'Code': 404,
                'Msg': '暂无数据',
            }
        ]
        transport = FixtureQinqinTransport(fixture_bundle)
        result = run_finance_summary_vertical_slice(
            transport=transport,
            **self._base_run_kwargs(),
        )

        account_trade_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_user_trade_list.v1_4'
        ][0]
        account_trade_state = [
            item for item in result['latest_state_artifacts']['latest_usable_endpoint_states']
            if item['endpoint_contract_id'] == 'qinqin.member.get_user_trade_list.v1_4'
        ][0]

        self.assertEqual(account_trade_endpoint['endpoint_status'], 'source_empty')
        self.assertEqual(account_trade_endpoint['terminal_outcome_category'], 'source_empty')
        self.assertEqual(account_trade_state['availability_status'], 'source_empty')
        self.assertEqual(
            result['latest_state_artifacts']['finance_summary_prerequisite_state']['prerequisite_status'],
            'ready',
        )
        self.assertEqual(len(result['canonical_artifacts']['account_trade']), 0)

    def test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure(self) -> None:
        fixture_bundle = self._fixture_bundle()
        responses_by_path = {
            '/api/thirdparty/GetRechargeBillList': fixture_bundle['qinqin.member.get_recharge_bill_list.v1_3'][0],
            '/api/thirdparty/GetUserTradeList': (
                404,
                {
                    'Code': 404,
                    'Msg': '暂无数据',
                    'RetData': [],
                },
            ),
        }
        with _serve_qinqin_responses(responses_by_path) as base_url:
            transport = LiveQinqinTransport(base_url=base_url, timeout_ms=3000)
            result = run_finance_summary_vertical_slice(
                transport=transport,
                **self._base_run_kwargs(),
            )

        account_trade_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_user_trade_list.v1_4'
        ][0]

        self.assertEqual(account_trade_endpoint['endpoint_status'], 'source_empty')
        self.assertEqual(account_trade_endpoint['terminal_outcome_category'], 'source_empty')
        self.assertIsNone(account_trade_endpoint['error_taxonomy'])
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'completed')

    def test_finance_summary_source_empty_after_prior_pages_finishes_completed(self) -> None:
        fixture_bundle = self._fixture_bundle()
        recharge_row = fixture_bundle['qinqin.member.get_recharge_bill_list.v1_3'][0]['RetData']['Data'][0]
        fixture_bundle['qinqin.member.get_recharge_bill_list.v1_3'] = [
            {
                'Code': 200,
                'Msg': '操作成功',
                'RetData': {
                    'Total': 2,
                    'Data': [recharge_row],
                },
            },
            {
                'Code': 404,
                'Msg': '暂无数据',
            },
        ]
        transport = FixtureQinqinTransport(fixture_bundle)
        result = run_finance_summary_vertical_slice(
            transport=transport,
            page_size=1,
            **self._base_run_kwargs(),
        )

        recharge_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_recharge_bill_list.v1_3'
        ][0]

        self.assertEqual(recharge_endpoint['endpoint_status'], 'completed')
        self.assertEqual(recharge_endpoint['record_count'], 1)
        self.assertEqual(recharge_endpoint['terminal_outcome_category'], 'success')
        self.assertEqual(len(result['canonical_artifacts']['recharge_bill']), 1)

    def test_finance_summary_classifies_sign_auth_schema_and_transport(self) -> None:
        scenarios = [
            (
                'sign',
                'qinqin.member.get_recharge_bill_list.v1_3',
                {
                    'Code': -500,
                    'Msg': '验签失败',
                    'RetData': {
                        'Total': 0,
                        'Data': [],
                    },
                },
                'sign',
                'source_sign_error',
            ),
            (
                'auth',
                'qinqin.member.get_recharge_bill_list.v1_3',
                {
                    'Code': 401,
                    'Msg': '未授权访问',
                },
                'auth',
                'source_auth_error',
            ),
            (
                'schema',
                'qinqin.member.get_user_trade_list.v1_4',
                {
                    'Code': 200,
                    'Msg': '操作成功',
                    'RetData': {
                        'unexpected': 'object'
                    },
                },
                'schema',
                'source_schema_error',
            ),
        ]

        for scenario_name, endpoint_contract_id, response_payload, expected_category, expected_taxonomy in scenarios:
            with self.subTest(scenario_name=scenario_name):
                fixture_bundle = self._fixture_bundle()
                fixture_bundle[endpoint_contract_id] = [response_payload]
                transport = FixtureQinqinTransport(fixture_bundle)
                result = run_finance_summary_vertical_slice(
                    transport=transport,
                    **self._base_run_kwargs(),
                )
                endpoint_run = [
                    item for item in result['historical_run_truth']['endpoint_runs']
                    if item['endpoint_contract_id'] == endpoint_contract_id
                ][0]
                blocking_dependency = [
                    item for item in result['latest_state_artifacts']['finance_summary_prerequisite_state']['blocking_dependencies']
                    if item['endpoint_contract_id'] == endpoint_contract_id
                ][0]

                self.assertEqual(endpoint_run['endpoint_status'], 'failed')
                self.assertEqual(endpoint_run['terminal_outcome_category'], expected_category)
                self.assertEqual(endpoint_run['error_taxonomy'], expected_taxonomy)
                self.assertEqual(blocking_dependency['blocking_category'], expected_category)

        timeout_transport = _TimeoutOnEndpointTransport(
            FixtureQinqinTransport(self._fixture_bundle()),
            'qinqin.member.get_user_trade_list.v1_4',
        )
        timeout_result = run_finance_summary_vertical_slice(
            transport=timeout_transport,
            **self._base_run_kwargs(),
        )
        timeout_endpoint_run = [
            item for item in timeout_result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_user_trade_list.v1_4'
        ][0]
        self.assertEqual(timeout_endpoint_run['endpoint_status'], 'failed')
        self.assertEqual(timeout_endpoint_run['terminal_outcome_category'], 'transport')
        self.assertEqual(timeout_endpoint_run['error_taxonomy'], 'transport_timeout_error')


if __name__ == '__main__':
    unittest.main()
