from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METRIC_DOMAIN = 'store_operating_day'
NON_RESOLVABLE_POLICY_STATUSES = {'policy_draft', 'policy_deprecated'}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def load_business_day_boundary_policy_registry(
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    return _load_json(data_platform_root / 'directory' / 'business-day-boundary-policy.seed.json')


def _is_resolvable_policy(entry: dict[str, Any]) -> bool:
    return entry.get('policy_status') not in NON_RESOLVABLE_POLICY_STATUSES


def _resolution_order(registry: dict[str, Any]) -> list[str]:
    return list(
        registry.get('override_resolution_order')
        or registry.get('resolution_hierarchy')
        or ['store_ref', 'org_ref', 'global_default']
    )


def _scope_kind(entry: dict[str, Any]) -> str | None:
    return entry.get('scope_kind') or entry.get('selector_kind')


def _scope_ref(entry: dict[str, Any], scope_kind: str | None) -> str | None:
    if entry.get('scope_ref'):
        return str(entry['scope_ref'])
    if scope_kind == 'store_ref':
        return entry.get('store_ref')
    if scope_kind == 'org_ref':
        return entry.get('org_ref')
    if scope_kind == 'global_default':
        return 'navly:scope:global:default'
    return None


def _hhmm(value: str | None) -> str | None:
    if not value:
        return None
    return value[:5]


def _hhmmss(value: str | None) -> str | None:
    if not value:
        return None
    return value if len(value) == 8 else f'{value}:00'


def _normalize_policy_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(entry)
    scope_kind = _scope_kind(entry)
    scope_ref = _scope_ref(entry, scope_kind)
    start_local_time = _hhmm(
        entry.get('business_day_start_local_time') or entry.get('business_day_boundary_local_time')
    )
    end_local_time = _hhmm(
        entry.get('business_day_end_exclusive_local_time')
        or entry.get('business_day_boundary_local_time')
    )

    normalized['metric_domain'] = entry.get('metric_domain') or DEFAULT_METRIC_DOMAIN
    normalized['scope_kind'] = scope_kind
    normalized['scope_ref'] = scope_ref
    normalized['selector_kind'] = scope_kind
    normalized['business_day_start_local_time'] = start_local_time
    normalized['business_day_end_exclusive_local_time'] = end_local_time or start_local_time
    normalized['business_day_boundary_local_time'] = _hhmmss(start_local_time)

    if scope_kind == 'store_ref':
        normalized.setdefault('store_ref', scope_ref)
        normalized.setdefault('org_ref', None)
    elif scope_kind == 'org_ref':
        normalized.setdefault('org_ref', scope_ref)
        normalized.setdefault('store_ref', None)
    else:
        normalized.setdefault('org_ref', None)
        normalized.setdefault('store_ref', None)

    return normalized


def _select_best_match(matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        raise ValueError('Expected at least one matching business-day boundary policy.')
    return max(matches, key=lambda entry: (str(entry.get('effective_from') or ''), str(entry['policy_id'])))


def resolve_business_day_boundary_policy(
    *,
    store_ref: str | None,
    org_ref: str | None,
    metric_domain: str = DEFAULT_METRIC_DOMAIN,
    data_platform_root: Path = DATA_PLATFORM_ROOT,
) -> dict[str, Any]:
    registry = load_business_day_boundary_policy_registry(data_platform_root=data_platform_root)
    resolution_order = _resolution_order(registry)
    matches_by_selector: dict[str, list[dict[str, Any]]] = {
        selector: []
        for selector in resolution_order
    }

    for entry in registry['entries']:
        if not _is_resolvable_policy(entry):
            continue
        if entry.get('metric_domain') and entry['metric_domain'] != metric_domain:
            continue

        selector_kind = _scope_kind(entry)
        if selector_kind not in matches_by_selector:
            continue

        normalized_entry = _normalize_policy_entry(entry)
        selector_scope_ref = normalized_entry.get('scope_ref')
        if selector_kind == 'store_ref' and store_ref and selector_scope_ref == store_ref:
            matches_by_selector[selector_kind].append(normalized_entry)
        elif selector_kind == 'org_ref' and org_ref and selector_scope_ref == org_ref:
            matches_by_selector[selector_kind].append(normalized_entry)
        elif selector_kind == 'global_default':
            matches_by_selector[selector_kind].append(normalized_entry)

    for selector_kind in resolution_order:
        matches = matches_by_selector[selector_kind]
        if not matches:
            continue
        return _select_best_match(matches)

    raise ValueError('Expected at least one matching business-day boundary policy.')
