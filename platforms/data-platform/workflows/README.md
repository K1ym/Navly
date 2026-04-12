# Workflows

本目录负责 data-platform 的 owner-side workflow orchestration。

当前已具备：

- `member_insight_owner_surface.py`
  - 调用 member insight vertical slice
  - 组装 readiness response
  - 组装 theme service response
- `qinqin_phase1_owner_surface.py`
  - 保持 `member_insight` owner surface authoritative
  - 组装 `finance_summary` / `staff_board` / `daily_overview` / `capability_explanation` formal owner surface
  - 对 runtime 暴露统一 phase-1 owner-side read boundary

当前边界：

- 当前仍是本地 owner-side workflow，不是 Temporal / production scheduler 落地
- 不在这里实现 runtime / bridge 接面代码
