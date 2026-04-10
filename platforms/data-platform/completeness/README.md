# Completeness

本目录负责 data-platform 的 readiness truth。

当前已具备：

- `member_insight_readiness_surface.py`
  - 为 `navly.store.member_insight` 产出 formal `capability_readiness_response`
  - 复用 latest-state、state traces、run traces
  - 区分 `ready / pending / failed / unsupported_scope`
- `commission_setting_completeness.py`
  - 为 `GetTechCommissionSetList` 产出 endpoint-scoped `commission_setting_completeness_state`
  - 消费 latest state / backfill progress / quality snapshots
  - 不把 completeness truth 混写成 service truth
- `finance_summary_readiness_surface.py`
  - 为 `navly.store.finance_summary` 复用 prerequisite state 与 endpoint latest-state 输出 readiness truth
- `staff_board_readiness_surface.py`
  - 为 `navly.store.staff_board` 把 vertical-slice backbone state 收敛成 readiness truth
- `daily_overview_readiness_surface.py`
  - 为 `navly.store.daily_overview` 聚合 member / staff / finance owner surfaces
  - 明确把 aggregate 依赖表达成 projection-level blocking dependencies

当前边界：

- 这里只表达 data readiness / dependency truth
- 不持有 access truth
- 不替 runtime 组织最终回答文本
