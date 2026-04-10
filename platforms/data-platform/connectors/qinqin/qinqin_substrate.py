from __future__ import annotations

import copy
import hashlib
import json
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVE_TIMEOUT_MS = 15000
SENSITIVE_HEADER_NAMES = {
    'authorization',
    'cookie',
    'proxy-authorization',
    'set-cookie',
    'token',
    'x-api-key',
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@dataclass(frozen=True)
class EndpointContract:
    endpoint_contract_id: str
    source_system_id: str
    domain: str
    version: str
    display_name: str
    method: str | None
    path: str | None
    increment_strategy: str | None
    structured_targets: list[str]
    truth_source_doc: str
    status: str
    notes: str | None = None


@dataclass(frozen=True)
class EndpointGovernanceBinding:
    endpoint_contract_id: str
    auth_profile_id: str
    operational_window_profile_id: str
    signature_rule_id: str
    required_parameter_keys: list[str]
    optional_parameter_keys: list[str]
    field_catalog_entry_id: str
    landing_policy_ids: list[str]
    response_payload_shape: str
    variance_ids: list[str]


@dataclass(frozen=True)
class TransportError:
    taxonomy: str
    code: str
    message: str
    retryable: bool = False


class TransportConfigError(ValueError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.taxonomy = 'transport_config_error'
        self.retryable = False


class SeedBackedQinqinRegistry:
    def __init__(self, data_platform_root: Path = DATA_PLATFORM_ROOT) -> None:
        self.data_platform_root = data_platform_root
        endpoint_contract_registry = _load_json(
            data_platform_root / 'directory' / 'endpoint-contracts.seed.json'
        )
        self._endpoint_contracts = endpoint_contract_registry['entries']
        self._endpoint_governance_bindings = endpoint_contract_registry['endpoint_governance_bindings']
        self._parameters = _load_json(
            data_platform_root / 'directory' / 'endpoint-parameter-canonicalization.seed.json'
        )['entries']

    def endpoint_contract(self, endpoint_contract_id: str) -> EndpointContract:
        for entry in self._endpoint_contracts:
            if entry['endpoint_contract_id'] == endpoint_contract_id:
                return EndpointContract(**entry)
        raise KeyError(f'Unknown endpoint_contract_id: {endpoint_contract_id}')

    def preferred_wire_name(self, parameter_key: str) -> str:
        for entry in self._parameters:
            if entry['parameter_key'] == parameter_key:
                return entry.get('preferred_wire_name') or entry['known_wire_variants'][0]
        raise KeyError(f'Unknown parameter_key: {parameter_key}')

    def endpoint_governance_binding(self, endpoint_contract_id: str) -> EndpointGovernanceBinding:
        for entry in self._endpoint_governance_bindings:
            if entry['endpoint_contract_id'] == endpoint_contract_id:
                return EndpointGovernanceBinding(**entry)
        raise KeyError(f'Unknown endpoint_contract_id governance binding: {endpoint_contract_id}')

    def endpoint_response_payload_shape(self, endpoint_contract_id: str) -> str:
        return self.endpoint_governance_binding(endpoint_contract_id).response_payload_shape


def load_seed_backed_qinqin_registry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> SeedBackedQinqinRegistry:
    return SeedBackedQinqinRegistry(data_platform_root=data_platform_root)


def _signature_payload_items(unsigned_payload: Mapping[str, Any]) -> list[tuple[str, Any]]:
    return sorted(
        ((key, value) for key, value in unsigned_payload.items() if key.lower() != 'sign'),
        key=lambda item: item[0].lower(),
    )


def compute_signature(unsigned_payload: Mapping[str, Any], app_secret: str) -> str:
    signature_source = '&'.join(f'{key}={value}' for key, value in _signature_payload_items(unsigned_payload))
    signature_source = f'{signature_source}&AppSecret={app_secret}'
    return hashlib.md5(signature_source.encode('utf-8')).hexdigest().lower()


def build_signed_request(
    endpoint_contract_id: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    page_index: int | None = None,
    page_size: int | None = None,
    member_card_id: str | None = None,
    trade_type: int | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)
    contract = registry.endpoint_contract(endpoint_contract_id)
    binding = registry.endpoint_governance_binding(endpoint_contract_id)
    value_by_parameter_key = {
        'org_id': org_id,
        'start_time': start_time,
        'end_time': end_time,
        'page_index': page_index,
        'page_size': page_size,
        'member_card_id': member_card_id,
        'trade_type': trade_type,
    }
    payload: dict[str, Any] = {}
    for parameter_key in [*binding.required_parameter_keys, *binding.optional_parameter_keys]:
        if parameter_key == 'sign':
            continue
        value = value_by_parameter_key.get(parameter_key)
        if value is None:
            if parameter_key in binding.required_parameter_keys:
                raise ValueError(
                    f'Missing required parameter {parameter_key} for {endpoint_contract_id}.'
                )
            continue
        payload[registry.preferred_wire_name(parameter_key)] = value
    payload[registry.preferred_wire_name('sign')] = compute_signature(payload, app_secret)
    return {
        'endpoint_contract_id': endpoint_contract_id,
        'method': contract.method,
        'path': contract.path,
        'payload': payload,
    }


def _build_transport_error(
    taxonomy: str,
    code: str,
    message: str,
    *,
    retryable: bool = False,
) -> TransportError:
    return TransportError(
        taxonomy=taxonomy,
        code=code,
        message=message,
        retryable=retryable,
    )


def _redact_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    if not headers:
        return {}
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADER_NAMES:
            redacted[key] = '<redacted>'
        else:
            redacted[key] = value
    return redacted


def _synthetic_transport_error_envelope(error: TransportError) -> dict[str, Any]:
    return {
        'Code': None,
        'Msg': error.message,
        'RetData': {
            'Total': 0,
            'Data': [],
        },
        '_transport_error': asdict(error),
    }


def _best_effort_response_envelope(
    response_body: str | None,
    *,
    fallback_message: str,
    fallback_error: TransportError | None = None,
) -> dict[str, Any]:
    if response_body:
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    if fallback_error is not None:
        return _synthetic_transport_error_envelope(fallback_error)
    return {
        'Code': None,
        'Msg': fallback_message,
        'RetData': {
            'Total': 0,
            'Data': [],
        },
    }


def _build_transport_page_result(
    *,
    transport_kind: str,
    transport_outcome: str,
    request_method: str | None,
    request_url: str | None,
    request_headers: Mapping[str, Any] | None,
    request_payload: Mapping[str, Any],
    response_http_status: int | None,
    response_headers: Mapping[str, Any] | None,
    response_body: str | None,
    response_envelope: Mapping[str, Any],
    transport_error: TransportError | None = None,
) -> dict[str, Any]:
    response_envelope_dict = copy.deepcopy(dict(response_envelope))
    return {
        'response_envelope': response_envelope_dict,
        'transport_error': asdict(transport_error) if transport_error is not None else None,
        'replay_artifact': {
            'transport_kind': transport_kind,
            'transport_outcome': transport_outcome,
            'request_method': request_method,
            'request_url': request_url,
            'request_headers_redacted': _redact_headers(request_headers),
            'request_payload': copy.deepcopy(dict(request_payload)),
            'response_http_status': response_http_status,
            'response_headers': dict(response_headers or {}),
            'response_body': response_body,
            'source_response_code': response_envelope_dict.get('Code'),
            'source_response_message': response_envelope_dict.get('Msg'),
            'error_taxonomy': transport_error.taxonomy if transport_error is not None else None,
            'error_code': transport_error.code if transport_error is not None else None,
            'error_message': transport_error.message if transport_error is not None else None,
            'retryable': transport_error.retryable if transport_error is not None else None,
        },
    }


def _normalize_http_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    if not headers:
        return {}
    if hasattr(headers, 'items'):
        items = headers.items()
    else:
        items = headers
    return {str(key): str(value) for key, value in items}


def _response_charset(response_headers: Mapping[str, str] | None) -> str:
    content_type = (response_headers or {}).get('Content-Type') or (response_headers or {}).get('content-type') or ''
    for part in content_type.split(';'):
        key, _, value = part.strip().partition('=')
        if key.lower() == 'charset' and value:
            return value.strip()
    return 'utf-8'


def _exception_to_transport_error(exception: Exception) -> TransportError:
    if isinstance(exception, TransportConfigError):
        return _build_transport_error(
            exception.taxonomy,
            exception.code,
            str(exception),
            retryable=exception.retryable,
        )
    if isinstance(exception, socket.timeout):
        return _build_transport_error(
            'transport_timeout_error',
            'SOCKET_TIMEOUT',
            str(exception) or 'Socket timed out.',
            retryable=True,
        )
    if isinstance(exception, TimeoutError):
        return _build_transport_error(
            'transport_timeout_error',
            'TIMEOUT',
            str(exception) or 'Request timed out.',
            retryable=True,
        )
    if isinstance(exception, URLError):
        reason = getattr(exception, 'reason', exception)
        if isinstance(reason, socket.timeout):
            return _build_transport_error(
                'transport_timeout_error',
                'URL_TIMEOUT',
                str(reason) or 'Request timed out.',
                retryable=True,
            )
        return _build_transport_error(
            'transport_network_error',
            'URL_ERROR',
            str(reason) or str(exception),
            retryable=True,
        )
    return _build_transport_error(
        'transport_unexpected_exception',
        exception.__class__.__name__,
        str(exception) or exception.__class__.__name__,
        retryable=False,
    )


def build_exception_fetch_result(
    *,
    exception: Exception,
    request_envelope: Mapping[str, Any],
    default_transport_kind: str,
) -> dict[str, Any]:
    transport_error = _exception_to_transport_error(exception)
    response_envelope = _synthetic_transport_error_envelope(transport_error)
    return _build_transport_page_result(
        transport_kind=default_transport_kind,
        transport_outcome='transport_error',
        request_method=request_envelope.get('method'),
        request_url=request_envelope.get('path'),
        request_headers={},
        request_payload=request_envelope.get('payload', {}),
        response_http_status=None,
        response_headers={},
        response_body=None,
        response_envelope=response_envelope,
        transport_error=transport_error,
    )


def normalize_fetch_page_result(
    *,
    fetch_result: Any,
    request_envelope: Mapping[str, Any],
    default_transport_kind: str,
) -> dict[str, Any]:
    if isinstance(fetch_result, Mapping) and 'response_envelope' in fetch_result and 'replay_artifact' in fetch_result:
        normalized = copy.deepcopy(dict(fetch_result))
        normalized.setdefault('transport_error', None)
        replay_artifact = normalized['replay_artifact']
        replay_artifact.setdefault('transport_kind', default_transport_kind)
        replay_artifact.setdefault('transport_outcome', 'response_received')
        replay_artifact.setdefault('request_method', request_envelope.get('method'))
        replay_artifact.setdefault('request_url', request_envelope.get('path'))
        replay_artifact.setdefault('request_headers_redacted', {})
        replay_artifact.setdefault('request_payload', copy.deepcopy(dict(request_envelope.get('payload', {}))))
        replay_artifact.setdefault('response_http_status', None)
        replay_artifact.setdefault('response_headers', {})
        replay_artifact.setdefault('response_body', None)
        replay_artifact.setdefault('source_response_code', normalized['response_envelope'].get('Code'))
        replay_artifact.setdefault('source_response_message', normalized['response_envelope'].get('Msg'))
        replay_artifact.setdefault('error_taxonomy', None)
        replay_artifact.setdefault('error_code', None)
        replay_artifact.setdefault('error_message', None)
        replay_artifact.setdefault('retryable', None)
        return normalized

    if isinstance(fetch_result, Mapping):
        response_envelope = copy.deepcopy(dict(fetch_result))
        return _build_transport_page_result(
            transport_kind=default_transport_kind,
            transport_outcome='response_received',
            request_method=request_envelope.get('method'),
            request_url=request_envelope.get('path'),
            request_headers={},
            request_payload=request_envelope.get('payload', {}),
            response_http_status=200,
            response_headers={},
            response_body=json.dumps(response_envelope, ensure_ascii=False),
            response_envelope=response_envelope,
        )

    return build_exception_fetch_result(
        exception=TypeError(f'Unsupported transport fetch result type: {type(fetch_result).__name__}'),
        request_envelope=request_envelope,
        default_transport_kind=default_transport_kind,
    )


class FixtureQinqinTransport:
    transport_kind = 'fixture'

    def __init__(
        self,
        fixture_pages_by_endpoint: Mapping[str, Sequence[Mapping[str, Any]]],
        data_platform_root: Path = DATA_PLATFORM_ROOT,
    ) -> None:
        self._fixture_pages_by_endpoint = {
            endpoint_id: [copy.deepcopy(page) for page in pages]
            for endpoint_id, pages in fixture_pages_by_endpoint.items()
        }
        self._registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)

    def fetch_page(self, endpoint_contract_id: str, request_payload: Mapping[str, Any]) -> dict[str, Any]:
        contract = self._registry.endpoint_contract(endpoint_contract_id)
        page_index_wire = self._registry.preferred_wire_name('page_index')
        raw_page_index = request_payload.get(page_index_wire)
        page_index = int(raw_page_index) if raw_page_index is not None else 1
        endpoint_pages = self._fixture_pages_by_endpoint.get(endpoint_contract_id, [])
        if 1 <= page_index <= len(endpoint_pages):
            response_envelope = copy.deepcopy(endpoint_pages[page_index - 1])
        else:
            response_envelope = {'Code': 200, 'Msg': '操作成功', 'RetData': {'Total': len(endpoint_pages), 'Data': []}}
        return _build_transport_page_result(
            transport_kind=self.transport_kind,
            transport_outcome='response_received',
            request_method=contract.method,
            request_url=contract.path,
            request_headers={},
            request_payload=request_payload,
            response_http_status=200,
            response_headers={},
            response_body=json.dumps(response_envelope, ensure_ascii=False),
            response_envelope=response_envelope,
        )


class LiveQinqinTransport:
    transport_kind = 'live'

    def __init__(
        self,
        *,
        base_url: str,
        timeout_ms: int = DEFAULT_LIVE_TIMEOUT_MS,
        authorization: str | None = None,
        token: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
        data_platform_root: Path = DATA_PLATFORM_ROOT,
    ) -> None:
        normalized_base_url = (base_url or '').strip().rstrip('/')
        if not normalized_base_url:
            raise TransportConfigError(
                code='MISSING_BASE_URL',
                message='Live Qinqin transport requires a non-empty base_url or QINQIN_API_BASE_URL.',
            )
        if '://' not in normalized_base_url:
            raise TransportConfigError(
                code='INVALID_BASE_URL',
                message='Live Qinqin transport base_url must include the URL scheme, for example http://host.',
            )
        if timeout_ms <= 0:
            raise TransportConfigError(
                code='INVALID_TIMEOUT_MS',
                message='Live Qinqin transport timeout_ms must be a positive integer.',
            )
        self._base_url = normalized_base_url
        self._timeout_ms = timeout_ms
        self._authorization = authorization
        self._token = token
        self._extra_headers = dict(extra_headers or {})
        self._registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)

    def _request_url(self, endpoint_contract_id: str) -> str:
        contract = self._registry.endpoint_contract(endpoint_contract_id)
        if not contract.path:
            raise TransportConfigError(
                code='MISSING_ENDPOINT_PATH',
                message=f'Endpoint contract {endpoint_contract_id} does not define a path.',
            )
        return f'{self._base_url}{contract.path}'

    def _request_headers(self) -> dict[str, str]:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
        }
        if self._authorization:
            headers['Authorization'] = self._authorization
        if self._token:
            headers['Token'] = self._token
        headers.update(self._extra_headers)
        return headers

    def fetch_page(self, endpoint_contract_id: str, request_payload: Mapping[str, Any]) -> dict[str, Any]:
        contract = self._registry.endpoint_contract(endpoint_contract_id)
        if not contract.method:
            raise TransportConfigError(
                code='MISSING_ENDPOINT_METHOD',
                message=f'Endpoint contract {endpoint_contract_id} does not define an HTTP method.',
            )

        request_method = contract.method.upper()
        request_url = self._request_url(endpoint_contract_id)
        request_headers = self._request_headers()
        request_body = json.dumps(dict(request_payload), ensure_ascii=False).encode('utf-8')
        request = Request(
            url=request_url,
            data=request_body,
            headers=request_headers,
            method=request_method,
        )

        try:
            with urlopen(request, timeout=self._timeout_ms / 1000.0) as response:
                response_http_status = getattr(response, 'status', response.getcode())
                response_headers = _normalize_http_headers(response.headers)
                response_body = response.read().decode(_response_charset(response_headers), errors='replace')
        except HTTPError as exc:
            try:
                response_body = exc.read().decode('utf-8', errors='replace')
            finally:
                exc.close()
            transport_error = _build_transport_error(
                'transport_http_status_error',
                f'HTTP_{exc.code}',
                f'HTTP {exc.code} while calling {endpoint_contract_id}.',
                retryable=exc.code >= 500,
            )
            return _build_transport_page_result(
                transport_kind=self.transport_kind,
                transport_outcome='transport_error',
                request_method=request_method,
                request_url=request_url,
                request_headers=request_headers,
                request_payload=request_payload,
                response_http_status=exc.code,
                response_headers=_normalize_http_headers(exc.headers),
                response_body=response_body,
                response_envelope=_best_effort_response_envelope(
                    response_body,
                    fallback_message=transport_error.message,
                    fallback_error=transport_error,
                ),
                transport_error=transport_error,
            )
        except (URLError, TimeoutError, socket.timeout) as exc:
            return build_exception_fetch_result(
                exception=exc,
                request_envelope={
                    'method': request_method,
                    'path': request_url,
                    'payload': request_payload,
                },
                default_transport_kind=self.transport_kind,
            )

        try:
            parsed_response = json.loads(response_body)
        except json.JSONDecodeError:
            transport_error = _build_transport_error(
                'transport_invalid_json_error',
                'INVALID_JSON',
                f'Qinqin response for {endpoint_contract_id} was not valid JSON.',
                retryable=False,
            )
            return _build_transport_page_result(
                transport_kind=self.transport_kind,
                transport_outcome='transport_error',
                request_method=request_method,
                request_url=request_url,
                request_headers=request_headers,
                request_payload=request_payload,
                response_http_status=response_http_status,
                response_headers=response_headers,
                response_body=response_body,
                response_envelope=_synthetic_transport_error_envelope(transport_error),
                transport_error=transport_error,
            )

        if not isinstance(parsed_response, dict):
            transport_error = _build_transport_error(
                'transport_invalid_payload_error',
                'NON_OBJECT_JSON',
                f'Qinqin response for {endpoint_contract_id} must be a JSON object.',
                retryable=False,
            )
            return _build_transport_page_result(
                transport_kind=self.transport_kind,
                transport_outcome='transport_error',
                request_method=request_method,
                request_url=request_url,
                request_headers=request_headers,
                request_payload=request_payload,
                response_http_status=response_http_status,
                response_headers=response_headers,
                response_body=response_body,
                response_envelope=_synthetic_transport_error_envelope(transport_error),
                transport_error=transport_error,
            )

        return _build_transport_page_result(
            transport_kind=self.transport_kind,
            transport_outcome='response_received',
            request_method=request_method,
            request_url=request_url,
            request_headers=request_headers,
            request_payload=request_payload,
            response_http_status=response_http_status,
            response_headers=response_headers,
            response_body=response_body,
            response_envelope=parsed_response,
        )


__all__ = [
    'DEFAULT_LIVE_TIMEOUT_MS',
    'EndpointContract',
    'EndpointGovernanceBinding',
    'FixtureQinqinTransport',
    'LiveQinqinTransport',
    'SeedBackedQinqinRegistry',
    'TransportConfigError',
    'TransportError',
    'build_exception_fetch_result',
    'build_signed_request',
    'compute_signature',
    'load_seed_backed_qinqin_registry',
    'normalize_fetch_page_result',
]
