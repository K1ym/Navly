from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def load_capability_dependency_registry(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    return _load_json(data_platform_root / 'directory' / 'capability-dependency-registry.seed.json')


def load_capability_dependency_entry(
    capability_id: str,
    *,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_capability_dependency_registry(data_platform_root=data_platform_root)
    for entry in registry['entries']:
        if entry['capability_id'] == capability_id:
            return entry
    raise KeyError(f'Missing capability dependency entry for {capability_id}')
