from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso

SNAPSHOT_VERSION = 'navly.phase1_owner_surface_snapshot.v1'
DEFAULT_PERSISTED_OWNER_SURFACE_ROOT = Path('/var/lib/navly/data-platform/serving-store')


def _normalize_root(root: str | Path | None) -> Path:
    if root is None:
        return DEFAULT_PERSISTED_OWNER_SURFACE_ROOT
    return Path(root)


def _snapshot_path(root: Path, org_id: str, business_date: str, capability_id: str) -> Path:
    return root / org_id / business_date / 'owner-surfaces' / f'{capability_id}.json'


def _index_path(root: Path, org_id: str) -> Path:
    return root / org_id / 'index.json'


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


@dataclass(frozen=True)
class PersistedOwnerSurfaceSnapshotStore:
    root: Path = DEFAULT_PERSISTED_OWNER_SURFACE_ROOT

    def __init__(self, root: str | Path | None = None) -> None:
        object.__setattr__(self, 'root', _normalize_root(root))

    def save_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        org_id = str(snapshot['org_id'])
        business_date = str(snapshot['snapshot_business_date'])
        capability_id = str(snapshot['capability_id'])
        persisted_snapshot = {
            **snapshot,
            'snapshot_version': SNAPSHOT_VERSION,
            'persisted_at': snapshot.get('persisted_at') or utcnow_iso(),
        }
        _write_json(_snapshot_path(self.root, org_id, business_date, capability_id), persisted_snapshot)
        self._refresh_index(org_id)
        return persisted_snapshot

    def load_snapshot(
        self,
        *,
        org_id: str,
        capability_id: str,
        target_business_date: str,
        freshness_mode: str = 'latest_usable',
    ) -> dict[str, Any] | None:
        index = self._load_index(org_id)
        capability_entry = index.get('capabilities', {}).get(capability_id)
        if not capability_entry:
            return None

        available_business_dates = list(capability_entry.get('available_business_dates', []))
        if freshness_mode == 'strict_date':
            selected_business_date = (
                target_business_date if target_business_date in available_business_dates else None
            )
        else:
            selected_business_date = None
            for business_date in reversed(available_business_dates):
                if business_date <= target_business_date:
                    selected_business_date = business_date
                    break
        if not selected_business_date:
            return None

        snapshot_path = _snapshot_path(self.root, org_id, selected_business_date, capability_id)
        if not snapshot_path.exists():
            return None
        return _load_json(snapshot_path)

    def _load_index(self, org_id: str) -> dict[str, Any]:
        index_path = _index_path(self.root, org_id)
        if not index_path.exists():
            return {
                'snapshot_version': SNAPSHOT_VERSION,
                'org_id': org_id,
                'capabilities': {},
                'updated_at': utcnow_iso(),
            }
        return _load_json(index_path)

    def _refresh_index(self, org_id: str) -> None:
        org_root = self.root / org_id
        capabilities: dict[str, dict[str, Any]] = {}
        if org_root.exists():
            for business_date_dir in sorted(
                [entry for entry in org_root.iterdir() if entry.is_dir() and entry.name != 'owner-surfaces']
            ):
                owner_surface_dir = business_date_dir / 'owner-surfaces'
                if not owner_surface_dir.exists():
                    continue
                for snapshot_file in sorted(owner_surface_dir.glob('*.json')):
                    snapshot = _load_json(snapshot_file)
                    capability_id = str(snapshot['capability_id'])
                    capability_entry = capabilities.setdefault(capability_id, {
                        'service_object_id': snapshot.get('service_object_id'),
                        'available_business_dates': [],
                    })
                    capability_entry['service_object_id'] = snapshot.get(
                        'service_object_id',
                        capability_entry.get('service_object_id'),
                    )
                    capability_entry['available_business_dates'].append(snapshot['snapshot_business_date'])
        normalized_capabilities = {
            capability_id: {
                **entry,
                'available_business_dates': sorted(set(entry.get('available_business_dates', []))),
                'latest_persisted_business_date': (
                    max(entry.get('available_business_dates', []))
                    if entry.get('available_business_dates')
                    else None
                ),
            }
            for capability_id, entry in capabilities.items()
        }
        _write_json(_index_path(self.root, org_id), {
            'snapshot_version': SNAPSHOT_VERSION,
            'org_id': org_id,
            'capabilities': normalized_capabilities,
            'updated_at': utcnow_iso(),
        })


__all__ = [
    'DEFAULT_PERSISTED_OWNER_SURFACE_ROOT',
    'PersistedOwnerSurfaceSnapshotStore',
    'SNAPSHOT_VERSION',
]
