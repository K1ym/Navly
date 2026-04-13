# Workflows

本目录负责 data-platform 的 owner-side workflow orchestration。

当前已具备：

- `member_insight_owner_surface.py`
  - 调用 member insight vertical slice
  - 组装 readiness response
  - 组装 theme service response
- `finance_summary_owner_surface.py`
  - 调用 finance summary vertical slice
  - 组装 readiness response
  - 组装 theme service response
- `staff_board_owner_surface.py`
  - 调用 staff board vertical slice
  - 组装 readiness response
  - 组装 theme service response
- `daily_overview_owner_surface.py`
  - 聚合 member / staff / finance owner surfaces
  - 读取 governed business-day boundary policy
- `capability_explanation_owner_surface.py`
  - 为已发布 capability surfaces 提供 companion explanation query boundary
- `nightly_sync_scheduler.py`
  - 把 nightly planner + cursor state + cursor ledger 收敛成 scheduler snapshot
  - 产出 currentness-first 的 dispatch plan
  - 为后续 Temporal worker 保持稳定输入边界
- `nightly_sync_worker.py`
  - 读取 persisted cursor ledger
  - 执行 scheduler snapshot 构建
  - 回写最新 ledger 状态
- `postgres_temporal_nightly_sync.py`
  - 提供 repo-authoritative nightly / retry / rerun / manual backfill workflow plane
  - 持有 PostgreSQL-first truth substrate 下的 scheduler / carry-forward cursor / backfill semantics
- `postgres_temporal_operator_surface.py`
  - 提供 operator-facing `sync_status` / `backfill_status` / `quality_report` persisted read surface
  - 提供 operator-facing `sync_rerun` / `sync_backfill` action surface
  - 动作完成后回写 persisted truth snapshot，并返回 post-action status reports

当前边界：

- 当前 workflow 仍是 repo-controlled implementation，不直接替代 live Temporal worker binding
- 不在这里实现 runtime / bridge 接面代码
