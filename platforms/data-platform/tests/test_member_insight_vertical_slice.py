from __future__ import annotations

import json
import os
import subprocess
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

from connectors.qinqin.qinqin_substrate import (  # noqa: E402
    FixtureQinqinTransport,
    LiveQinqinTransport,
    TransportConfigError,
    build_signed_request,
)
from ingestion.member_insight_vertical_slice import _run_status, run_member_insight_vertical_slice  # noqa: E402


class _QinqinTestServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], responses_by_path: dict[str, object]) -> None:
        super().__init__(server_address, _QinqinTestRequestHandler)
        self.responses_by_path = responses_by_path
        self.requests: list[dict[str, object]] = []


class _QinqinTestRequestHandler(BaseHTTPRequestHandler):
    server: _QinqinTestServer

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get('Content-Length') or '0')
        raw_body = self.rfile.read(content_length).decode('utf-8')
        try:
            parsed_body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            parsed_body = {'_invalid_json_body': raw_body}

        self.server.requests.append({
            'path': self.path,
            'headers': dict(self.headers.items()),
            'payload': parsed_body,
        })

        response_entry = self.server.responses_by_path.get(self.path)
        if response_entry is None:
            status_code = 404
            response_payload: object = {'error': 'not found'}
        elif isinstance(response_entry, tuple):
            status_code, response_payload = response_entry
        else:
            status_code = 200
            response_payload = response_entry

        if isinstance(response_payload, (dict, list)):
            response_body = json.dumps(response_payload, ensure_ascii=False).encode('utf-8')
            content_type = 'application/json; charset=utf-8'
        else:
            response_body = str(response_payload).encode('utf-8')
            content_type = 'text/plain; charset=utf-8'

        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
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
        yield f'http://{host}:{port}', server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class MemberInsightVerticalSliceTest(unittest.TestCase):
    def _fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _base_run_kwargs(self) -> dict[str, object]:
        return {
            'org_id': 'demo-org-001',
            'start_time': '2026-03-20 09:00:00',
            'end_time': '2026-03-24 09:00:00',
            'requested_business_date': '2026-03-23',
            'app_secret': 'test-secret',
        }

    def test_qinqin_substrate_uses_registry_preferred_wire_names(self) -> None:
        request = build_signed_request(
            endpoint_contract_id='qinqin.member.get_customers_list.v1_1',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            page_index=1,
            page_size=20,
            app_secret='test-secret',
        )
        self.assertEqual(sorted(request['payload'].keys()), sorted(['OrgId', 'Stime', 'Etime', 'PageIndex', 'PageSize', 'Sign']))
        self.assertTrue(request['payload']['Sign'])

    def test_vertical_slice_separates_historical_run_truth_and_latest_state(self) -> None:
        fixture_bundle = self._fixture_bundle()
        transport = FixtureQinqinTransport(fixture_bundle)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_member_insight_vertical_slice(
                transport=transport,
                output_root=tmpdir,
                **self._base_run_kwargs(),
            )
            self.assertEqual(result['transport_kind'], 'fixture')
            self.assertEqual(result['capability_id'], 'navly.store.member_insight')
            self.assertEqual(result['service_object_id'], 'navly.service.store.member_insight')
            self.assertEqual(result['dependency_entry']['dependency_status'], 'phase_1_contract_frozen')
            self.assertEqual(
                result['dependency_entry']['required_endpoint_contract_ids'],
                [
                    'qinqin.member.get_customers_list.v1_1',
                    'qinqin.member.get_consume_bill_list.v1_2',
                ],
            )
            self.assertEqual(result['historical_run_truth']['ingestion_run']['transport_kind'], 'fixture')
            self.assertEqual(len(result['historical_run_truth']['endpoint_runs']), 2)
            self.assertEqual(len(result['raw_replay']['raw_response_pages']), 2)
            self.assertEqual(len(result['raw_replay']['transport_replay_artifacts']), 2)
            self.assertEqual(len(result['canonical_artifacts']['customer']), 1)
            self.assertEqual(len(result['canonical_artifacts']['consume_bill']), 1)
            self.assertEqual(len(result['canonical_artifacts']['consume_bill_payment']), 1)
            self.assertEqual(len(result['latest_state_artifacts']['latest_usable_endpoint_states']), 2)
            self.assertEqual(
                result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
                'backbone_ready',
            )
            self.assertTrue(Path(tmpdir, 'historical-run-truth', 'ingestion-runs.json').exists())
            self.assertTrue(Path(tmpdir, 'latest-state', 'latest-usable-endpoint-state.json').exists())
            self.assertTrue(Path(tmpdir, 'canonical', 'customer.json').exists())
            self.assertTrue(Path(tmpdir, 'raw-replay', 'transport-replay-artifacts.json').exists())

    def test_empty_trailing_page_finishes_completed_not_source_empty(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_customers_list.v1_1'] = [
            {
                'Code': 200,
                'Msg': '操作成功',
                'RetData': {
                    'Total': 2,
                    'Data': [
                        {
                            'Id': 'cust_001',
                            'OrgId': 'demo-org-001',
                            'Phone': '13900000000',
                            'Name': '示例用户A',
                            'Storeds': [],
                        }
                    ],
                },
            },
            {
                'Code': 200,
                'Msg': '操作成功',
                'RetData': {
                    'Total': 2,
                    'Data': [],
                },
            },
        ]
        transport = FixtureQinqinTransport(fixture_bundle)
        result = run_member_insight_vertical_slice(
            transport=transport,
            page_size=1,
            **self._base_run_kwargs(),
        )
        customer_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_customers_list.v1_1'
        ][0]
        self.assertEqual(customer_endpoint['endpoint_status'], 'completed')
        self.assertEqual(customer_endpoint['record_count'], 1)

    def test_source_business_error_is_taxonomized_and_excluded_from_canonical_output(self) -> None:
        fixture_bundle = self._fixture_bundle()
        fixture_bundle['qinqin.member.get_consume_bill_list.v1_2'] = [
            {
                'Code': -500,
                'Msg': '验签失败',
                'RetData': {
                    'Total': 0,
                    'Data': [],
                },
            }
        ]
        transport = FixtureQinqinTransport(fixture_bundle)
        result = run_member_insight_vertical_slice(
            transport=transport,
            **self._base_run_kwargs(),
        )
        consume_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_consume_bill_list.v1_2'
        ][0]
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'partial_failed')
        self.assertEqual(consume_endpoint['endpoint_status'], 'failed')
        self.assertEqual(consume_endpoint['error_taxonomy'], 'source_business_error')
        self.assertEqual(consume_endpoint['error_code'], '-500')
        self.assertEqual(len(result['canonical_artifacts']['customer']), 1)
        self.assertEqual(len(result['canonical_artifacts']['consume_bill']), 0)
        self.assertEqual(
            result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
            'backbone_incomplete',
        )

    def test_live_transport_runs_and_redacts_sensitive_headers_in_replay_artifacts(self) -> None:
        fixture_bundle = self._fixture_bundle()
        responses_by_path = {
            '/api/thirdparty/GetCustomersList': fixture_bundle['qinqin.member.get_customers_list.v1_1'][0],
            '/api/thirdparty/GetConsumeBillList': fixture_bundle['qinqin.member.get_consume_bill_list.v1_2'][0],
        }
        with _serve_qinqin_responses(responses_by_path) as (base_url, server):
            transport = LiveQinqinTransport(
                base_url=base_url,
                timeout_ms=3000,
                authorization='Bearer live-secret',
                token='live-token',
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                result = run_member_insight_vertical_slice(
                    transport=transport,
                    output_root=tmpdir,
                    **self._base_run_kwargs(),
                )
                self.assertEqual(result['transport_kind'], 'live')
                self.assertEqual(len(server.requests), 2)
                self.assertEqual(server.requests[0]['path'], '/api/thirdparty/GetCustomersList')
                self.assertEqual(server.requests[0]['payload']['OrgId'], 'demo-org-001')
                self.assertIn('Sign', server.requests[0]['payload'])

                replay_artifact = result['raw_replay']['transport_replay_artifacts'][0]
                self.assertEqual(replay_artifact['transport_kind'], 'live')
                self.assertEqual(replay_artifact['response_http_status'], 200)
                self.assertTrue(replay_artifact['request_url'].startswith(base_url))
                self.assertEqual(replay_artifact['request_headers_redacted']['Authorization'], '<redacted>')
                self.assertEqual(replay_artifact['request_headers_redacted']['Token'], '<redacted>')
                self.assertTrue(Path(tmpdir, 'raw-replay', 'transport-replay-artifacts.json').exists())

    def test_live_transport_http_error_is_taxonomized_and_keeps_run_chain(self) -> None:
        fixture_bundle = self._fixture_bundle()
        responses_by_path = {
            '/api/thirdparty/GetCustomersList': (502, {'error': 'bad gateway'}),
            '/api/thirdparty/GetConsumeBillList': fixture_bundle['qinqin.member.get_consume_bill_list.v1_2'][0],
        }
        with _serve_qinqin_responses(responses_by_path) as (base_url, _server):
            transport = LiveQinqinTransport(base_url=base_url, timeout_ms=3000)
            result = run_member_insight_vertical_slice(
                transport=transport,
                **self._base_run_kwargs(),
            )

        customer_endpoint = [
            item for item in result['historical_run_truth']['endpoint_runs']
            if item['endpoint_contract_id'] == 'qinqin.member.get_customers_list.v1_1'
        ][0]
        self.assertEqual(result['historical_run_truth']['ingestion_run']['run_status'], 'partial_failed')
        self.assertEqual(customer_endpoint['endpoint_status'], 'failed')
        self.assertEqual(customer_endpoint['error_taxonomy'], 'transport_http_status_error')
        self.assertEqual(customer_endpoint['error_code'], 'HTTP_502')
        self.assertTrue(customer_endpoint['retryable'])
        self.assertEqual(len(result['raw_replay']['transport_replay_artifacts']), 2)
        self.assertEqual(result['raw_replay']['transport_replay_artifacts'][0]['response_http_status'], 502)
        self.assertEqual(len(result['canonical_artifacts']['customer']), 0)
        self.assertEqual(len(result['canonical_artifacts']['consume_bill']), 1)

    def test_live_transport_requires_base_url(self) -> None:
        with self.assertRaisesRegex(TransportConfigError, 'base_url'):
            LiveQinqinTransport(base_url='')

    def test_zero_endpoint_runs_are_failed(self) -> None:
        self.assertEqual(_run_status([]), 'failed')

    def test_cli_runner_writes_artifact_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = DATA_PLATFORM_ROOT / 'scripts' / 'run_member_insight_vertical_slice.py'
            fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'member_insight' / 'qinqin_fixture_pages.bundle.json'
            env = dict(os.environ)
            env['PYTHONPATH'] = str(DATA_PLATFORM_ROOT)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    '--org-id', 'demo-org-001',
                    '--start-time', '2026-03-20 09:00:00',
                    '--end-time', '2026-03-24 09:00:00',
                    '--requested-business-date', '2026-03-23',
                    '--app-secret', 'test-secret',
                    '--fixtures', str(fixture_path),
                    '--output-dir', tmpdir,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload['transport_kind'], 'fixture')
            self.assertEqual(payload['capability_id'], 'navly.store.member_insight')
            self.assertEqual(payload['transport_replay_artifacts'], 2)
            self.assertTrue(Path(tmpdir, 'raw-replay', 'raw-response-pages.json').exists())
            self.assertTrue(Path(tmpdir, 'raw-replay', 'transport-replay-artifacts.json').exists())


if __name__ == '__main__':
    unittest.main()
