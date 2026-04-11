from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
NON_RESOLVABLE_POLICY_STATUSES = {'policy_draft', 'policy_deprecated'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


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
        and entry.get('increment_strategy_policies')
        and entry.get('notes') is not None
        and entry.get('status') not in NON_RESOLVABLE_POLICY_STATUSES
    ]
    if len(matches) != 1:
        raise ValueError(
            f'Expected exactly one nightly sync policy for {source_system_id}, got {matches!r}'
        )
    return matches[0]


__all__ = [
    'load_nightly_sync_policy_entry',
    'load_nightly_sync_policy_registry',
]
