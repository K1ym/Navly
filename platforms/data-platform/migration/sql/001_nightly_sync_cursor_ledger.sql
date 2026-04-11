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
    carry_forward_cursor BOOLEAN NOT NULL,
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
