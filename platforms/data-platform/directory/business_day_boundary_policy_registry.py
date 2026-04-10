from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
NON_RESOLVABLE_POLICY_STATUSES = {'policy_draft', 'policy_deprecated'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def load_business_day_boundary_policy_registry(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    return _load_json(data_platform_root / 'directory' / 'business-day-boundary-policy.seed.json')


def _is_resolvable_policy(entry: dict[str, Any]) -> bool:
    return entry.get('policy_status') not in NON_RESOLVABLE_POLICY_STATUSES


def resolve_business_day_boundary_policy(
    *,
    store_ref: str | None,
    org_ref: str | None,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_business_day_boundary_policy_registry(data_platform_root=data_platform_root)
    matches_by_selector: dict[str, list[dict[str, Any]]] = {
        selector: []
        for selector in registry['resolution_hierarchy']
    }

    for entry in registry['entries']:
        if not _is_resolvable_policy(entry):
            continue

        selector_kind = entry['selector_kind']
        if selector_kind not in matches_by_selector:
            continue

        if selector_kind == 'store_ref' and store_ref and entry.get('store_ref') == store_ref:
            matches_by_selector[selector_kind].append(entry)
        elif selector_kind == 'org_ref' and org_ref and entry.get('org_ref') == org_ref:
            matches_by_selector[selector_kind].append(entry)
        elif selector_kind == 'global_default':
            matches_by_selector[selector_kind].append(entry)

    for selector_kind in registry['resolution_hierarchy']:
        matches = matches_by_selector[selector_kind]
        if not matches:
            continue
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one {selector_kind} policy match, got {matches!r}')
        return matches[0]

    raise ValueError('Expected at least one matching business-day boundary policy.')
