# Serving

本目录负责 data-platform 默认读边界与 formal owner-side service surface。

当前已具备：

- `member_insight_theme_service_surface.py`
  - 为 `navly.service.store.member_insight` 产出 formal `theme_service_response`
  - 在非 ready 场景下返回 `not_ready` 与 explanation object
  - 在 capability / service object 不匹配时返回 `scope_mismatch`
- `finance_summary_theme_service_surface.py`
  - 为 `navly.service.store.finance_summary` 发布 formal owner-side service surface
- `staff_board_theme_service_surface.py`
  - 为 `navly.service.store.staff_board` 发布 formal owner-side service surface
- `daily_overview_theme_service_surface.py`
  - 为 `navly.service.store.daily_overview` 聚合已发布 store service objects
  - 在 service object 中显式携带 governed business-day boundary policy
- `capability_explanation_service_surface.py`
  - 为 `navly.service.system.capability_explanation` 发布 companion explanation service surface
- `persisted_owner_surface_snapshot_store.py`
  - 为 manager-facing capability / service object 提供 persisted snapshot store
  - nightly runtime 将 member_insight / finance_summary / staff_board / daily_overview 物化到该 store
  - owner-side runtime 默认从该 store 读取 latest-usable readiness / service snapshots

当前边界：

- Copilot / runtime 默认不再实时重跑 live vertical slice；默认消费 persisted owner-surface snapshots
- Copilot / runtime 仍不应默认穿透内部目录读 canonical/raw/state
- serving surface 表达的是 owner-governed service truth，不是最终自然语言回答
