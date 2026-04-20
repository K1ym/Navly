from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from datetime import date

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
NON_RESOLVABLE_POLICY_STATUSES = {'policy_draft', 'policy_deprecated'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _normalize_optional_iso_date(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        raise ValueError(f'{field_name} must be an ISO business date, got {value!r}') from exc


def _normalize_positive_int(value: Any, *, field_name: str) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field_name} must be a positive integer, got {value!r}') from exc
    if resolved <= 0:
        raise ValueError(f'{field_name} must be a positive integer, got {value!r}')
    return resolved


@lru_cache(maxsize=1)
def load_nightly_sync_policy_registry(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    return _load_json(data_platform_root / 'directory' / 'nightly-sync-policy.seed.json')


def load_nightly_sync_policy_entry(
    source_system_id: str,
    *,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_nightly_sync_policy_registry(data_platform_root=data_platform_root)
    matches = [
        entry
        for entry in registry['entries']
        if entry['source_system_id'] == source_system_id
        and entry['sync_policy_id']
        and entry.get('activation_local_time')
        and entry.get('default_page_size') is not None
        and entry.get('currentness_priority')
        and entry.get('backfill_fill_direction')
        and entry.get('operator_backfill_defaults_to_full_history') is not None
        and entry.get('max_concurrent_endpoint_fetches') is not None
        and entry.get('increment_strategy_policies')
        and entry.get('notes') is not None
        and entry.get('status') not in NON_RESOLVABLE_POLICY_STATUSES
    ]
    if len(matches) != 1:
        raise ValueError(
            f'Expected exactly one nightly sync policy for {source_system_id}, got {matches!r}'
        )
    return matches[0]


def resolve_nightly_sync_history_start_business_date(
    source_system_id: str,
    *,
    explicit_history_start_business_date: str | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
    environ: dict[str, str] | None = None,
) -> str | None:
    explicit = _normalize_optional_iso_date(
        explicit_history_start_business_date,
        field_name='explicit_history_start_business_date',
    )
    if explicit:
        return explicit

    entry = load_nightly_sync_policy_entry(
        source_system_id,
        data_platform_root=data_platform_root,
    )
    env = environ or os.environ
    env_var_name = str(entry.get('runtime_history_start_business_date_env_var') or '').strip()
    if env_var_name:
        env_value = _normalize_optional_iso_date(
            env.get(env_var_name),
            field_name=env_var_name,
        )
        if env_value:
            return env_value

    return _normalize_optional_iso_date(
        entry.get('default_history_start_business_date'),
        field_name='default_history_start_business_date',
    )


def resolve_nightly_sync_endpoint_fetch_concurrency(
    source_system_id: str,
    *,
    requested_max_concurrent_endpoint_fetches: int | None = None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
    environ: dict[str, str] | None = None,
) -> int:
    if requested_max_concurrent_endpoint_fetches is not None:
        return _normalize_positive_int(
            requested_max_concurrent_endpoint_fetches,
            field_name='requested_max_concurrent_endpoint_fetches',
        )

    entry = load_nightly_sync_policy_entry(
        source_system_id,
        data_platform_root=data_platform_root,
    )
    env = environ or os.environ
    env_var_name = str(entry.get('runtime_max_concurrent_endpoint_fetches_env_var') or '').strip()
    if env_var_name and env.get(env_var_name) not in {None, ''}:
        return _normalize_positive_int(
            env.get(env_var_name),
            field_name=env_var_name,
        )
    return _normalize_positive_int(
        entry.get('max_concurrent_endpoint_fetches'),
        field_name='max_concurrent_endpoint_fetches',
    )


def should_default_operator_backfill_to_full_history(
    source_system_id: str,
    *,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> bool:
    entry = load_nightly_sync_policy_entry(
        source_system_id,
        data_platform_root=data_platform_root,
    )
    return bool(entry.get('operator_backfill_defaults_to_full_history'))


__all__ = [
    'load_nightly_sync_policy_entry',
    'load_nightly_sync_policy_registry',
    'resolve_nightly_sync_endpoint_fetch_concurrency',
    'resolve_nightly_sync_history_start_business_date',
    'should_default_operator_backfill_to_full_history',
]
