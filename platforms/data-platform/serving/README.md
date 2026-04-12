# Serving

本目录负责 data-platform 默认读边界与 formal owner-side service surface。

当前已具备：

- `member_insight_theme_service_surface.py`
  - 为 `navly.service.store.member_insight` 产出 formal `theme_service_response`
  - 在非 ready 场景下返回 `not_ready` 与 explanation object
  - 在 capability / service object 不匹配时返回 `scope_mismatch`
- `qinqin_phase1_theme_service_surface.py`
  - 为 `navly.service.store.finance_summary` / `navly.service.store.staff_board` 产出 formal `theme_service_response`
  - 为 `navly.service.store.daily_overview` 产出 aggregate owner-side `theme_service_response`
  - 为 `navly.service.system.capability_explanation` 产出 formal fallback `theme_service_response`
  - 统一复用 `capability_explanation_object`，而不是让 runtime 自行回推内部 shape

当前边界：

- Copilot / runtime 仍不应默认穿透内部目录读 canonical/raw/state
- serving surface 表达的是 owner-governed service truth，不是最终自然语言回答
