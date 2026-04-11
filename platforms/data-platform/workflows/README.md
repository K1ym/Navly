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

当前边界：

- 当前仍是本地 owner-side workflow，不是 Temporal / production scheduler 落地
- 不在这里实现 runtime / bridge 接面代码
