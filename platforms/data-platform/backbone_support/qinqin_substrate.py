from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


class SeedBackedQinqinRegistry:
    def __init__(self, data_platform_root: Path = DATA_PLATFORM_ROOT) -> None:
        self.data_platform_root = data_platform_root
        self._endpoint_contracts = _load_json(
            data_platform_root / 'directory' / 'endpoint-contracts.seed.json'
        )['entries']
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
    page_index: int,
    page_size: int,
    app_secret: str,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_seed_backed_qinqin_registry(data_platform_root=data_platform_root)
    contract = registry.endpoint_contract(endpoint_contract_id)
    payload = {
        registry.preferred_wire_name('org_id'): org_id,
        registry.preferred_wire_name('start_time'): start_time,
        registry.preferred_wire_name('end_time'): end_time,
        registry.preferred_wire_name('page_index'): page_index,
        registry.preferred_wire_name('page_size'): page_size,
    }
    payload[registry.preferred_wire_name('sign')] = compute_signature(payload, app_secret)
    return {
        'endpoint_contract_id': endpoint_contract_id,
        'method': contract.method,
        'path': contract.path,
        'payload': payload,
    }


class FixtureQinqinTransport:
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
        page_index_wire = self._registry.preferred_wire_name('page_index')
        page_index = int(request_payload[page_index_wire])
        endpoint_pages = self._fixture_pages_by_endpoint.get(endpoint_contract_id, [])
        if 1 <= page_index <= len(endpoint_pages):
            return copy.deepcopy(endpoint_pages[page_index - 1])
        return {'Code': 200, 'Msg': '操作成功', 'RetData': {'Total': len(endpoint_pages), 'Data': []}}
