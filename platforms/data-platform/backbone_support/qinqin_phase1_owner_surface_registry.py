from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

MEMBER_INSIGHT_CAPABILITY_ID = 'navly.store.member_insight'
MEMBER_INSIGHT_SERVICE_OBJECT_ID = 'navly.service.store.member_insight'
DAILY_OVERVIEW_CAPABILITY_ID = 'navly.store.daily_overview'
DAILY_OVERVIEW_SERVICE_OBJECT_ID = 'navly.service.store.daily_overview'
STAFF_BOARD_CAPABILITY_ID = 'navly.store.staff_board'
STAFF_BOARD_SERVICE_OBJECT_ID = 'navly.service.store.staff_board'
FINANCE_SUMMARY_CAPABILITY_ID = 'navly.store.finance_summary'
FINANCE_SUMMARY_SERVICE_OBJECT_ID = 'navly.service.store.finance_summary'
CAPABILITY_EXPLANATION_CAPABILITY_ID = 'navly.system.capability_explanation'
CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation'


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _is_supported_status(value: str | None) -> bool:
    normalized = str(value or '').strip().lower()
    return bool(normalized) and not normalized.startswith('retired')


@lru_cache(maxsize=4)
def capability_registry(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    entries = _load_json(data_platform_root / 'directory' / 'capability-registry.seed.json')['entries']
    return {
        entry['capability_id']: entry
        for entry in entries
        if _is_supported_status(entry.get('status'))
    }


@lru_cache(maxsize=4)
def capability_service_bindings(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    entries = _load_json(data_platform_root / 'directory' / 'capability-service-bindings.seed.json')['entries']
    return {
        entry['capability_id']: entry
        for entry in entries
        if _is_supported_status(entry.get('status'))
    }


@lru_cache(maxsize=4)
def service_object_bindings(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    return {
        entry['service_object_id']: entry
        for entry in capability_service_bindings(data_platform_root=data_platform_root).values()
    }


@lru_cache(maxsize=4)
def capability_dependencies(data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, dict[str, Any]]:
    entries = _load_json(data_platform_root / 'directory' / 'capability-dependency-registry.placeholder.json')['entries']
    return {
        entry['capability_id']: entry
        for entry in entries
        if _is_supported_status(entry.get('dependency_status'))
    }


def supported_capability_ids(data_platform_root: Path = DATA_PLATFORM_ROOT) -> tuple[str, ...]:
    return tuple(capability_registry(data_platform_root=data_platform_root).keys())


def supported_service_object_ids(data_platform_root: Path = DATA_PLATFORM_ROOT) -> tuple[str, ...]:
    return tuple(service_object_bindings(data_platform_root=data_platform_root).keys())


def capability_entry(capability_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    entry = capability_registry(data_platform_root=data_platform_root).get(capability_id)
    if entry is None:
        raise KeyError(f'Unsupported capability_id: {capability_id}')
    return entry


def capability_service_binding(capability_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    entry = capability_service_bindings(data_platform_root=data_platform_root).get(capability_id)
    if entry is None:
        raise KeyError(f'Missing capability service binding for capability_id: {capability_id}')
    return entry


def service_object_binding(service_object_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    entry = service_object_bindings(data_platform_root=data_platform_root).get(service_object_id)
    if entry is None:
        raise KeyError(f'Unsupported service_object_id: {service_object_id}')
    return entry


def capability_dependency_entry(capability_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> dict[str, Any]:
    entry = capability_dependencies(data_platform_root=data_platform_root).get(capability_id)
    if entry is None:
        raise KeyError(f'Missing capability dependency entry for capability_id: {capability_id}')
    return entry


def default_service_object_id_for_capability(capability_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> str:
    binding = capability_service_binding(capability_id, data_platform_root=data_platform_root)
    return str(binding['service_object_id'])


def capability_id_for_service_object(service_object_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> str:
    binding = service_object_binding(service_object_id, data_platform_root=data_platform_root)
    return str(binding['capability_id'])


def is_data_backed_capability(capability_id: str, *, data_platform_root: Path = DATA_PLATFORM_ROOT) -> bool:
    dependency_entry = capability_dependency_entry(capability_id, data_platform_root=data_platform_root)
    return bool(dependency_entry.get('endpoint_contract_ids'))


def owner_surface_name(capability_id: str) -> str:
    return capability_id.split('.')[-1].replace('-', '_')

