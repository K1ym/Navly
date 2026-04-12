# Scripts

本目录承载 data-platform 的开发与验证脚本。

当前可用：

- `run_member_insight_vertical_slice.py`
  - 支持 `fixture` transport
  - 支持 `live` transport
  - 把实际 artifact tree 写到 `--output-dir`
  - 同时写出 `vertical-slice-summary.json`
  - 支持自定义 `--request-id` / `--trace-ref`
- `run_postgres_temporal_nightly_sync.py`
  - 运行 repo-authoritative nightly scheduler
  - 输出当前 run 的 workflow / backfill / state summary
  - 输出 effective policy，明确显示本次执行使用的 repo-governed planner semantics
  - 支持自定义 `--request-id` / `--trace-ref`
  - 可通过 `--output-dir` 写出 sync/backfill/service status artifacts
  - 可通过 `--output-dir` 写出 operator sync/backfill/quality status reports
  - 可通过 `--state-snapshot` 在 repo-local smoke / foreground runs 中跨进程续跑 carry-forward state
  - 用于验证 PostgreSQL-first / Temporal-first closeout path
- `migrate_member_insight_artifact_tree_to_postgres_truth.py`
  - 把 legacy artifact tree 导入 PostgreSQL truth substrate model
  - 支持 `--state-snapshot` 续写 persisted truth state
  - 支持 `--output-dir` 写出 `artifact-bridge-summary.json`
  - 支持自定义 `--request-id` / `--trace-ref`
  - 只允许作为 transitional migration aid
- `query_postgres_temporal_status.py`
  - 从 persisted truth snapshot 中读取 operator sync/backfill/quality status
  - 为 `sync_status` / `backfill_status` / `quality_report` 类 operator surface 提供 repo-controlled query path
  - 可通过 `--output-dir` 写出 `operator-status-bundle.json` 及分拆后的 report files
  - 支持自定义 `--request-id` / `--trace-ref`
- `query_member_insight_owner_surface_from_snapshot.py`
  - 从 persisted truth snapshot 中读取 member_insight owner surface
  - 返回 readiness / theme service response
  - top-level bundle 会回显 `state_snapshot`
  - 支持自定义 `--request-id` / `--trace-ref`
  - 可通过 `--output-dir` 写出：
    - `member-insight-owner-surface.json`
    - `member-insight-readiness-response.json`
    - `member-insight-theme-service-response.json`
  - 即使结果为 `not_ready` / `scope_mismatch`，上述文件仍会按 fail-closed 结果写出

当前边界：

- 这里的脚本用于本地验证与示例产物写出，不是 live connector 或通用生产入口
- 当前 sample 实际写出的是 `raw-replay/`、`historical-run-truth/`、`canonical/`、`latest-state/`
- 当前 sample 不会写出 `projections/` 或 `serving/`
- systemd / wrapper 若存在，只应把调度转交给这里对应的 repo workflow semantics，而不是自己发明业务日期或 backfill 逻辑
- artifact migration 如果必须发生，应通过显式 migration bridge，而不是在运行时偷偷回退到 artifact-first
- operator status 查询应优先读取 persisted truth snapshot / PostgreSQL truth substrate，而不是重新触发 nightly 调度
