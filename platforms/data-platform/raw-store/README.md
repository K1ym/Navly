# Raw Store

本目录负责 raw request / response / replay 的持久化与读取。

当前 closeout lane 的 authoritative production intent：

- raw replay truth 应落到 PostgreSQL
- runtime artifact tree 只保留为 diagnostics / replay helper / smoke path
- page run 不再隐含在 artifact 文件结构里，而是有正式 `ingestion_page_run` 语义

当前已落地的事实边界：

- `historical-run-truth/ingestion-runs.json`
- `historical-run-truth/endpoint-runs.json`
- `raw-replay/raw-response-pages.json`
  - source page truth
- `raw-replay/transport-replay-artifacts.json`
  - transport replay truth
  - request URL / method / payload
  - redacted request headers
  - HTTP status / headers / body
  - explicit error taxonomy

设计约束：

- 不把 transport replay truth 和 source page truth 混成一个表意层
- replay artifact 不写明文敏感 header 值
- intended production primary path 见：
  - `migration/sql/2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql`
  - `backbone_support/postgres_truth_substrate.py`
