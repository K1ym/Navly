# Migration

本目录承接 legacy -> new data-platform 的迁移脚本、DDL 与核对逻辑。

当前 closeout lane 已落地：

- `sql/2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql`
  - PostgreSQL-first truth substrate DDL
  - 覆盖 scheduler run / ingestion run / endpoint run / page run / raw replay / canonical facts / latest sync state / backfill progress / quality / readiness / service projection
- `artifact_tree_bridge.py`
  - transitional artifact -> PostgreSQL truth import bridge
  - 明确把 artifact compatibility 限制在迁移目录，不让它继续冒充 production primary path

说明：

- 这份 SQL 是当前 repo-authoritative production schema intent
- runtime artifact tree 与 SQLite-style ledger 不再允许被描述成 production primary path
- 如果必须承接旧 artifact tree，只能通过 `migration/artifact_tree_bridge.py` 这类显式过渡层
