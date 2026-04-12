# PostgreSQL Temporal Nightly Sync

日期：2026-04-12  
状态：authoritative-closeout-path  
适用范围：ASP-44 / ASP-45 / ASP-46 data-truth lane

## 1. 目的

本手册定义当前 repo 内的 authoritative production intent：

- PostgreSQL-first truth substrate
- Temporal-native nightly / backfill / retry / rerun workflow plane
- repo code，而不是仓库外 wrapper，定义 expected business date、backfill、carry-forward cursor、retry 与 rerun 语义

## 2. Authoritative Modules

- SQL schema:
  - `platforms/data-platform/migration/sql/2026-04-12-navly-v1-phase1-postgres-truth-substrate.sql`
- truth substrate model:
  - `platforms/data-platform/backbone_support/postgres_truth_substrate.py`
- scheduler / worker path:
  - `platforms/data-platform/workflows/postgres_temporal_nightly_sync.py`
- policy seed:
  - `platforms/data-platform/directory/nightly-sync-policy.seed.json`

## 3. Frozen Semantics

### 3.1 PostgreSQL-first truth objects

- `scheduler_run`
- `ingestion_run`
- `ingestion_endpoint_run`
- `ingestion_page_run`
- `raw_replay_artifact`
- member insight canonical fact tables
- `latest_sync_state`
- `backfill_progress_state`
- `field_coverage_snapshot`
- `schema_alignment_snapshot`
- `quality_issue`
- `capability_readiness_snapshot`
- `service_projection`

### 3.2 Planner semantics

- planner mode: `currentness_first`
- backfill order: `latest_to_oldest`
- cursor mode: `carry_forward_cursor`
- older missing business dates must produce non-empty `backfill_tasks`
- historical backfill must not overwrite newer `latest_sync_state`

### 3.3 Temporal worker semantics

- task queue: `navly-data-platform-nightly`
- workflows:
  - `NightlySchedulerWorkflow`
  - `NightlyExecutionWorkflow`
  - `RetryWorkflow`
  - `RerunWorkflow`
- activities:
  - `run_member_insight_vertical_slice`
  - `persist_postgres_truth_substrate`
  - `reconcile_backfill_progress`

## 4. Verification

Targeted closeout verification:

```bash
python3 -m unittest platforms.data-platform.tests.test_postgres_temporal_nightly_sync
```

Full data-platform regression suite:

```bash
python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'
```

Repo-controlled nightly execution smoke:

```bash
python3 platforms/data-platform/scripts/run_postgres_temporal_nightly_sync.py \
  --request-id req-navly-nightly-001 \
  --trace-ref navly:trace:req-navly-nightly-001 \
  --org-id demo-org-001 \
  --target-business-date 2026-03-23 \
  --backfill-start-business-date 2026-03-20 \
  --app-secret '<redacted-app-secret>' \
  --state-snapshot /tmp/navly-nightly-snapshot.json \
  --output-dir /tmp/navly-nightly-status
```

Runner output now includes:

- `request_id`
- `trace_ref`
- `effective_policy.policy_id`
- `effective_policy.planner_mode`
- `effective_policy.backfill_order`
- `effective_policy.cursor_mode`
- `effective_policy.max_backfill_tasks_per_run`
- `output_dir` when status artifacts are written
- `state_snapshot` when repo-local resume state is persisted

If `--output-dir` is provided, the runner writes:

- `nightly-run-summary.json`
- `scheduler-runs.json`
- `latest-sync-states.json`
- `backfill-progress-states.json`
- `service-projections.json`
- `operator-sync-status.json`
- `operator-backfill-status.json`
- `operator-quality-report.json`

If `--state-snapshot` is provided, the runner reloads prior truth-store state before planning and writes the updated snapshot back after execution. This is a repo-local smoke/runtime aid that simulates carry-forward persistence between runs before a live PostgreSQL adapter is bound.

Transitional artifact import smoke:

```bash
python3 platforms/data-platform/scripts/migrate_member_insight_artifact_tree_to_postgres_truth.py \
  --request-id req-navly-bridge-001 \
  --trace-ref navly:trace:req-navly-bridge-001 \
  --artifact-root /tmp/member-insight-fixture \
  --workflow-id navly-migration-artifact-bridge \
  --state-snapshot /tmp/navly-nightly-snapshot.json \
  --output-dir /tmp/navly-bridge-status
```

该 bridge 输出：

- `request_id`
- `trace_ref`
- `artifact-bridge-summary.json`

说明：

- `request_id` / `trace_ref` 会同时出现在 stdout summary 与 `artifact-bridge-summary.json`
- `state_snapshot` / `output_dir` 也会在该 summary 中保留

Persisted operator status query smoke:

```bash
python3 platforms/data-platform/scripts/query_postgres_temporal_status.py \
  --request-id req-operator-status-001 \
  --trace-ref navly:trace:req-operator-status-001 \
  --state-snapshot /tmp/navly-nightly-snapshot.json \
  --org-id demo-org-001 \
  --output-dir /tmp/navly-status-query
```

该查询脚本返回：

- `request_id`
- `trace_ref`
- `sync_status`
- `backfill_status`
- `quality_report`

说明：

- `request_id` / `trace_ref` 会同时出现在 stdout bundle 与 `operator-status-bundle.json`
- split report files 继续只承载各自的状态对象，不重复顶层 request metadata

Persisted owner-surface smoke:

说明：

- runtime / adapter 若提供 `state_snapshot_path`
- owner surface 可以直接读取 persisted readiness / service projection
- 不需要重新触发 nightly 或 vertical slice sync

CLI 示例：

```bash
python3 platforms/data-platform/scripts/query_member_insight_owner_surface_from_snapshot.py \
  --request-id req-owner-surface-001 \
  --trace-ref navly:trace:req-owner-surface-001 \
  --state-snapshot /tmp/navly-nightly-snapshot.json \
  --org-id demo-org-001 \
  --target-business-date 2026-03-23 \
  --target-scope-ref navly:scope:store:demo-org-001 \
  --output-dir /tmp/navly-owner-surface
```

该查询脚本在 `--output-dir` 下会写出：

- `member-insight-owner-surface.json`
- `member-insight-readiness-response.json`
- `member-insight-theme-service-response.json`

说明：

- 这些文件不仅用于 served path
- 在 persisted state 缺失、projection 缺失、scope mismatch 等 fail-closed 场景下也会写出对应结构化结果
- `state_snapshot` 会保留在 owner-surface bundle stdout 与 `member-insight-owner-surface.json` 中
- `request_id` / `trace_ref` 会保留在 owner-surface bundle，以及 split readiness/theme response 文件中
- `output_dir` 只作为 bundle 级 runtime extension 出现在 stdout 与 `member-insight-owner-surface.json` 中

## 5. Operational Notes

- artifact tree output remains useful for replay inspection and smoke validation
- artifact tree is no longer the intended production primary truth substrate
- if artifact compatibility is temporarily required, use the explicit migration bridge under `platforms/data-platform/migration/`
- operator status 查询应读取 persisted truth substrate state，而不是重新触发 nightly scheduler
- quality report 查询也应读取 persisted truth substrate state，而不是重新触发 nightly scheduler
- systemd / wrapper / cron should only bootstrap the worker; business scheduling semantics must remain in repo workflow code
