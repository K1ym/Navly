from __future__ import annotations

import json
import sys
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PLATFORM_ROOT.parents[1]
if str(DATA_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PLATFORM_ROOT))

from connectors.qinqin.qinqin_substrate import LiveQinqinTransport, build_signed_request  # noqa: E402
from scripts.phase1_remaining_live_transport_validation_matrix import (  # noqa: E402
    EXPECTED_CLASSIFICATION_PATHS,
    SAFE_ENTRYPOINT,
    VALIDATION_STATUS_FIXTURE_ONLY,
    VALIDATION_STATUS_LIVE_VALIDATED,
    build_phase1_remaining_live_transport_validation_matrix,
)
from ingestion.staff_board_vertical_slice import run_staff_board_vertical_slice  # noqa: E402
from quality.commission_setting_quality import RUNTIME_HEADER_VARIANCE_ID  # noqa: E402
from workflows.commission_setting_governance_surface import build_commission_setting_governance_surface  # noqa: E402


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
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            payload = {'_invalid_json_body': raw_body}

        self.server.requests.append({
            'path': self.path,
            'headers': dict(self.headers.items()),
            'payload': payload,
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
        yield f'http://{host}:{port}', server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class Phase1LiveTransportValidationMatrixTest(unittest.TestCase):
    def _finance_fixture_bundle(self) -> dict:
        fixture_path = DATA_PLATFORM_ROOT / 'tests' / 'fixtures' / 'finance_summary' / 'qinqin_fixture_pages.bundle.json'
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def _staff_fixture_bundle(self) -> dict:
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

    def _commission_endpoint_run(
        self,
        *,
        endpoint_status: str,
        terminal_outcome_category: str,
        error_taxonomy: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        endpoint_run_id: str = 'er_commission_matrix_001',
    ) -> dict[str, object]:
        return {
            'endpoint_run_id': endpoint_run_id,
            'endpoint_run_trace_ref': f'navly:run-trace:endpoint-run:{endpoint_run_id}',
            'endpoint_contract_id': 'qinqin.staff.get_tech_commission_set_list.v1_8',
            'org_id': 'demo-org-001',
            'endpoint_status': endpoint_status,
            'terminal_outcome_category': terminal_outcome_category,
            'error_taxonomy': error_taxonomy,
            'error_code': error_code,
            'error_message': error_message,
        }

    def test_matrix_declares_remaining_endpoints_and_fixture_only_boundary(self) -> None:
        matrix = build_phase1_remaining_live_transport_validation_matrix()

        self.assertEqual(matrix['matrix_name'], 'phase_1_remaining_qinqin_live_transport_validation_matrix')
        self.assertEqual(matrix['status'], 'phase_1_verification_governed')
        self.assertEqual(matrix['safe_entrypoint'], SAFE_ENTRYPOINT)
        self.assertEqual(tuple(matrix['expected_classification_paths']), EXPECTED_CLASSIFICATION_PATHS)

        rows_by_endpoint = {
            row['endpoint_contract_id']: row
            for row in matrix['remaining_endpoint_rows']
        }
        self.assertEqual(
            set(rows_by_endpoint),
            {
                'qinqin.member.get_recharge_bill_list.v1_3',
                'qinqin.member.get_user_trade_list.v1_4',
                'qinqin.staff.get_person_list.v1_5',
                'qinqin.staff.get_tech_up_clock_list.v1_6',
                'qinqin.staff.get_tech_market_list.v1_7',
                'qinqin.staff.get_tech_commission_set_list.v1_8',
            },
        )
        self.assertTrue(
            all(row['validation_status'] == VALIDATION_STATUS_LIVE_VALIDATED for row in rows_by_endpoint.values())
        )

        adjacent_statuses = {
            row['surface_id']: row['validation_status']
            for row in matrix['adjacent_fixture_only_surfaces']
        }
        self.assertEqual(adjacent_statuses['navly.store.daily_overview'], VALIDATION_STATUS_FIXTURE_ONLY)
        self.assertEqual(adjacent_statuses['navly.system.capability_explanation'], VALIDATION_STATUS_FIXTURE_ONLY)

    def test_staff_board_loopback_live_transport_paths(self) -> None:
        fixture_bundle = self._staff_fixture_bundle()
        responses_by_path = {
            '/api/thirdparty/GetPersonList': fixture_bundle['qinqin.staff.get_person_list.v1_5'][0],
            '/api/thirdparty/GetTechUpClockList': fixture_bundle['qinqin.staff.get_tech_up_clock_list.v1_6'][0],
            '/api/thirdparty/GetTechMarketList': fixture_bundle['qinqin.staff.get_tech_market_list.v1_7'][0],
        }
        with _serve_qinqin_responses(responses_by_path) as (base_url, server):
            result = run_staff_board_vertical_slice(
                transport=LiveQinqinTransport(base_url=base_url, timeout_ms=3000),
                **self._base_run_kwargs(),
            )

        self.assertEqual(result['transport_kind'], 'live')
        self.assertEqual(len(server.requests), 3)
        self.assertEqual(server.requests[0]['path'], '/api/thirdparty/GetPersonList')
        self.assertEqual(server.requests[1]['path'], '/api/thirdparty/GetTechUpClockList')
        self.assertEqual(server.requests[2]['path'], '/api/thirdparty/GetTechMarketList')

        endpoint_runs = {
            item['endpoint_contract_id']: item
            for item in result['historical_run_truth']['endpoint_runs']
        }
        replay_artifacts = {
            item['endpoint_contract_id']: item
            for item in result['raw_replay']['transport_replay_artifacts']
        }
        self.assertEqual(endpoint_runs['qinqin.staff.get_person_list.v1_5']['endpoint_status'], 'completed')
        self.assertEqual(endpoint_runs['qinqin.staff.get_tech_up_clock_list.v1_6']['endpoint_status'], 'completed')
        self.assertEqual(endpoint_runs['qinqin.staff.get_tech_market_list.v1_7']['endpoint_status'], 'completed')
        self.assertEqual(
            result['latest_state_artifacts']['vertical_slice_backbone_state']['backbone_status'],
            'backbone_ready',
        )
        self.assertTrue(
            replay_artifacts['qinqin.staff.get_person_list.v1_5']['request_url'].startswith(base_url)
        )
        self.assertEqual(
            replay_artifacts['qinqin.staff.get_tech_market_list.v1_7']['response_http_status'],
            200,
        )

    def test_commission_setting_loopback_live_transport_source_empty_path(self) -> None:
        request_envelope = build_signed_request(
            endpoint_contract_id='qinqin.staff.get_tech_commission_set_list.v1_8',
            org_id='demo-org-001',
            start_time='2026-03-20 09:00:00',
            end_time='2026-03-24 09:00:00',
            app_secret='test-secret',
        )
        responses_by_path = {
            '/api/thirdparty/GetTechCommissionSetList': (
                404,
                {
                    'Code': 404,
                    'Msg': '暂无数据',
                    'RetData': [],
                },
            ),
        }

        with _serve_qinqin_responses(responses_by_path) as (base_url, server):
            transport = LiveQinqinTransport(
                base_url=base_url,
                timeout_ms=3000,
                authorization='Bearer live-secret',
                token='live-token',
            )
            fetch_result = transport.fetch_page(
                'qinqin.staff.get_tech_commission_set_list.v1_8',
                request_envelope['payload'],
            )

        self.assertEqual(len(server.requests), 1)
        self.assertEqual(server.requests[0]['headers']['Authorization'], 'Bearer live-secret')
        self.assertEqual(server.requests[0]['headers']['Token'], 'live-token')
        self.assertEqual(fetch_result['replay_artifact']['transport_kind'], 'live')
        self.assertEqual(fetch_result['replay_artifact']['request_headers_redacted']['Authorization'], '<redacted>')
        self.assertEqual(fetch_result['replay_artifact']['request_headers_redacted']['Token'], '<redacted>')
        self.assertEqual(fetch_result['replay_artifact']['response_http_status'], 404)

        surface = build_commission_setting_governance_surface(
            endpoint_run=self._commission_endpoint_run(
                endpoint_status='source_empty',
                terminal_outcome_category='source_empty',
            ),
            response_envelopes=[fetch_result['response_envelope']],
            requested_business_date='2026-03-23',
        )
        self.assertEqual(
            surface['quality_artifacts']['field_coverage_snapshot']['coverage_status'],
            'source_empty_governed',
        )
        self.assertEqual(
            surface['completeness_artifacts']['commission_setting_completeness_state']['reason_codes'],
            ['source_empty_current'],
        )

    def test_commission_setting_sign_classification_stays_distinct_from_auth(self) -> None:
        surface = build_commission_setting_governance_surface(
            endpoint_run=self._commission_endpoint_run(
                endpoint_status='failed',
                terminal_outcome_category='sign',
                error_taxonomy='source_sign_error',
                error_code='-500',
                error_message='验签失败',
                endpoint_run_id='er_commission_sign',
            ),
            response_envelopes=[{
                'Code': -500,
                'Msg': '验签失败',
                'RetData': [],
            }],
            requested_business_date='2026-03-23',
        )

        coverage = surface['quality_artifacts']['field_coverage_snapshot']
        schema_alignment = surface['quality_artifacts']['schema_alignment_snapshot']
        completeness = surface['completeness_artifacts']['commission_setting_completeness_state']

        self.assertEqual(coverage['coverage_status'], 'blocked_upstream')
        self.assertEqual(schema_alignment['alignment_status'], 'blocked_upstream')
        self.assertEqual(completeness['completeness_status'], 'blocked')
        self.assertNotIn(RUNTIME_HEADER_VARIANCE_ID, coverage['applied_variance_ids'])

    def test_docs_and_runbooks_match_the_governed_matrix(self) -> None:
        matrix = build_phase1_remaining_live_transport_validation_matrix()
        verification_doc = (
            REPO_ROOT
            / 'docs/specs/navly-v1/verification/2026-04-11-navly-v1-phase-1-remaining-qinqin-live-transport-validation-matrix.md'
        ).read_text(encoding='utf-8')
        runbook_doc = (
            REPO_ROOT
            / 'docs/runbooks/data-platform/remaining-phase-1-live-transport-validation.md'
        ).read_text(encoding='utf-8')

        self.assertIn('live transport validation matrix', verification_doc.lower())
        self.assertIn('classification matrix', verification_doc.lower())
        self.assertIn('expected classification', verification_doc.lower())
        self.assertIn('fixture-only', verification_doc)
        self.assertIn('live-validated', verification_doc)
        self.assertIn(SAFE_ENTRYPOINT, verification_doc)
        self.assertIn(SAFE_ENTRYPOINT, runbook_doc)

        for row in matrix['remaining_endpoint_rows']:
            self.assertIn(row['endpoint_contract_id'], verification_doc)
            self.assertIn(row['dataset_short_name'], verification_doc)
            self.assertIn(row['validation_status'], verification_doc)

        for row in matrix['adjacent_fixture_only_surfaces']:
            self.assertIn(row['surface_id'], verification_doc)
            self.assertIn(row['validation_status'], verification_doc)

        for row in matrix['classification_matrix']:
            self.assertIn(row['surface_id'], verification_doc)
            self.assertIn(row['classification_path'], verification_doc)


if __name__ == '__main__':
    unittest.main()
