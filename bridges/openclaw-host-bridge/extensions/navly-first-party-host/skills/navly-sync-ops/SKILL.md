---
description: Use for operator sync-state, rerun, and backfill operations. Call `navly_sync_status`, `navly_backfill_status`, `navly_rerun_sync`, or `navly_trigger_backfill`.
---

Use this skill for sync-ops requests.

- Primary tools: `navly_sync_status`, `navly_backfill_status`, `navly_rerun_sync`, `navly_trigger_backfill`
- Capability family: `navly.ops.*`
- Inputs vary by tool: `scope_ref`, `business_date`, `backfill_from`, `backfill_to`, `rerun_mode`, `include_explanation`

These tools remain operator-scoped and must still honor Navly authorization truth.
