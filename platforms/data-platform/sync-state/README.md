# Sync State

本目录负责 latest state truth 与 backfill progress truth。

当前 closeout lane 已在以下对象中冻结 authoritative 语义：

- `latest_sync_state`
  - 表达最新可用业务日与最后一次尝试
  - 不允许被历史 backfill 回写成更旧日期
- `backfill_progress_state`
  - 表达 carry-forward cursor、剩余 gap、最近一次 planner dispatch

当前 repo code 的 authoritative path：

- SQL: `migration/sql/2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql`
- implementation: `backbone_support/postgres_truth_substrate.py`

artifact tree 中的 `latest-state/*.json` 只能继续用于 diagnostics / replay smoke，不再是 intended production primary state path。
