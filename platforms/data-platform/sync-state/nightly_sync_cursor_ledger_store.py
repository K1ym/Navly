from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nightly_sync_cursor_ledger_entries (
    ledger_entry_id TEXT PRIMARY KEY,
    ledger_trace_ref TEXT NOT NULL,
    source_system_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    endpoint_contract_id TEXT NOT NULL,
    target_business_date TEXT NOT NULL,
    cursor_status TEXT NOT NULL,
    last_completed_business_date TEXT,
    last_attempted_business_date TEXT,
    next_currentness_business_date TEXT,
    next_backfill_business_date TEXT,
    covered_business_dates_json TEXT NOT NULL,
    pending_business_dates_json TEXT NOT NULL,
    carry_forward_cursor INTEGER NOT NULL,
    backfill_fill_direction TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nightly_sync_cursor_lookup
ON nightly_sync_cursor_ledger_entries (
    source_system_id,
    org_id,
    target_business_date,
    endpoint_contract_id
);
"""


@dataclass(frozen=True)
class LedgerStoreTarget:
    backend: str
    dsn: str | None
    path: Path | None


def _resolve_target(db_target: str | Path) -> LedgerStoreTarget:
    if isinstance(db_target, Path):
        return LedgerStoreTarget(backend='sqlite', dsn=None, path=db_target)

    raw = str(db_target)
    if raw.startswith('postgresql://') or raw.startswith('postgres://'):
        return LedgerStoreTarget(backend='postgres', dsn=raw, path=None)
    if raw.startswith('sqlite:///'):
        return LedgerStoreTarget(backend='sqlite', dsn=None, path=Path(raw.removeprefix('sqlite:///')))
    return LedgerStoreTarget(backend='sqlite', dsn=None, path=Path(raw))


class NightlySyncCursorLedgerStore:
    def __init__(self, db_target: str | Path) -> None:
        self.target = _resolve_target(db_target)
        if self.target.backend == 'sqlite':
            assert self.target.path is not None
            self.db_path = self.target.path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._backend = 'sqlite'
        else:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError(
                    'PostgreSQL ledger store requires psycopg. Install platforms/data-platform/requirements-runtime.txt.'
                ) from exc
            assert self.target.dsn is not None
            self.db_path = None
            self._connection = psycopg.connect(self.target.dsn, row_factory=dict_row)
            self._backend = 'postgres'

    def close(self) -> None:
        self._connection.close()

    def ensure_schema(self) -> None:
        if self._backend == 'sqlite':
            self._connection.executescript(SCHEMA_SQL)
        else:
            cursor = self._connection.cursor()
            try:
                for statement in [entry.strip() for entry in SCHEMA_SQL.split(';') if entry.strip()]:
                    cursor.execute(statement)
            finally:
                cursor.close()
        self._connection.commit()

    def _backend_sql(self, statement: str) -> str:
        if self._backend == 'sqlite':
            return statement
        return statement.replace('?', '%s')

    def _fetchall(self, statement: str, params: tuple[Any, ...]) -> list[Any]:
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._backend_sql(statement), params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute(self, statement: str, params: tuple[Any, ...]) -> None:
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._backend_sql(statement), params)
        finally:
            cursor.close()

    def _executemany(self, statement: str, params: list[tuple[Any, ...]]) -> None:
        if not params:
            return
        cursor = self._connection.cursor()
        try:
            cursor.executemany(self._backend_sql(statement), params)
        finally:
            cursor.close()

    def load_entries(
        self,
        *,
        source_system_id: str,
        org_id: str,
        target_business_date: str,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        rows = self._fetchall(
            """
            SELECT *
            FROM nightly_sync_cursor_ledger_entries
            WHERE source_system_id = ?
              AND org_id = ?
              AND target_business_date = ?
            ORDER BY endpoint_contract_id ASC
            """,
            (source_system_id, org_id, target_business_date),
        )
        return [self._row_to_entry(row) for row in rows]

    def load_effective_entries(
        self,
        *,
        source_system_id: str,
        org_id: str,
        as_of_target_business_date: str,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        rows = self._fetchall(
            """
            SELECT *
            FROM (
                SELECT
                    nightly_sync_cursor_ledger_entries.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY endpoint_contract_id
                        ORDER BY target_business_date DESC, updated_at DESC
                    ) AS endpoint_rank
                FROM nightly_sync_cursor_ledger_entries
                WHERE source_system_id = ?
                  AND org_id = ?
                  AND target_business_date <= ?
            ) ranked_entries
            WHERE endpoint_rank = 1
            ORDER BY endpoint_contract_id ASC
            """,
            (source_system_id, org_id, as_of_target_business_date),
        )
        return [self._row_to_entry(row) for row in rows]

    def save_ledger(self, ledger: dict[str, Any]) -> None:
        self.ensure_schema()
        entries = list(ledger.get('entries', []))
        source_system_id = ledger['source_system_id']
        org_id = ledger['org_id']
        target_business_date = ledger['target_business_date']
        keep_ids = {entry['ledger_entry_id'] for entry in entries}

        for entry in entries:
            self._execute(
                """
                INSERT INTO nightly_sync_cursor_ledger_entries (
                    ledger_entry_id,
                    ledger_trace_ref,
                    source_system_id,
                    org_id,
                    endpoint_contract_id,
                    target_business_date,
                    cursor_status,
                    last_completed_business_date,
                    last_attempted_business_date,
                    next_currentness_business_date,
                    next_backfill_business_date,
                    covered_business_dates_json,
                    pending_business_dates_json,
                    carry_forward_cursor,
                    backfill_fill_direction,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ledger_entry_id) DO UPDATE SET
                    ledger_trace_ref = excluded.ledger_trace_ref,
                    source_system_id = excluded.source_system_id,
                    org_id = excluded.org_id,
                    endpoint_contract_id = excluded.endpoint_contract_id,
                    target_business_date = excluded.target_business_date,
                    cursor_status = excluded.cursor_status,
                    last_completed_business_date = excluded.last_completed_business_date,
                    last_attempted_business_date = excluded.last_attempted_business_date,
                    next_currentness_business_date = excluded.next_currentness_business_date,
                    next_backfill_business_date = excluded.next_backfill_business_date,
                    covered_business_dates_json = excluded.covered_business_dates_json,
                    pending_business_dates_json = excluded.pending_business_dates_json,
                    carry_forward_cursor = excluded.carry_forward_cursor,
                    backfill_fill_direction = excluded.backfill_fill_direction,
                    updated_at = excluded.updated_at
                """,
                self._entry_values(entry),
            )

        existing_ids = {
            row['ledger_entry_id']
            for row in self._fetchall(
                """
                SELECT ledger_entry_id
                FROM nightly_sync_cursor_ledger_entries
                WHERE source_system_id = ?
                  AND org_id = ?
                  AND target_business_date = ?
                """,
                (source_system_id, org_id, target_business_date),
            )
        }
        stale_ids = existing_ids.difference(keep_ids)
        if stale_ids:
            self._executemany(
                "DELETE FROM nightly_sync_cursor_ledger_entries WHERE ledger_entry_id = ?",
                [(ledger_entry_id,) for ledger_entry_id in stale_ids],
            )
        self._connection.commit()

    def _entry_values(self, entry: dict[str, Any]) -> tuple[Any, ...]:
        return (
            entry['ledger_entry_id'],
            entry['ledger_trace_ref'],
            entry['source_system_id'],
            entry['org_id'],
            entry['endpoint_contract_id'],
            entry['target_business_date'],
            entry['cursor_status'],
            entry.get('last_completed_business_date'),
            entry.get('last_attempted_business_date'),
            entry.get('next_currentness_business_date'),
            entry.get('next_backfill_business_date'),
            json.dumps(entry.get('covered_business_dates', []), ensure_ascii=False),
            json.dumps(entry.get('pending_business_dates', []), ensure_ascii=False),
            1 if entry.get('carry_forward_cursor') else 0,
            entry['backfill_fill_direction'],
            entry['updated_at'],
        )

    def _row_to_entry(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            'ledger_entry_id': row['ledger_entry_id'],
            'ledger_trace_ref': row['ledger_trace_ref'],
            'source_system_id': row['source_system_id'],
            'org_id': row['org_id'],
            'endpoint_contract_id': row['endpoint_contract_id'],
            'target_business_date': row['target_business_date'],
            'cursor_status': row['cursor_status'],
            'last_completed_business_date': row['last_completed_business_date'],
            'last_attempted_business_date': row['last_attempted_business_date'],
            'next_currentness_business_date': row['next_currentness_business_date'],
            'next_backfill_business_date': row['next_backfill_business_date'],
            'covered_business_dates': json.loads(row['covered_business_dates_json']),
            'pending_business_dates': json.loads(row['pending_business_dates_json']),
            'carry_forward_cursor': bool(row['carry_forward_cursor']),
            'backfill_fill_direction': row['backfill_fill_direction'],
            'updated_at': row['updated_at'],
        }


__all__ = ['LedgerStoreTarget', 'NightlySyncCursorLedgerStore']
