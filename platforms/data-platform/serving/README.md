# Serving

本目录负责 data-platform 默认读边界与 formal owner-side service surface。

当前已具备：

- `member_insight_theme_service_surface.py`
  - 为 `navly.service.store.member_insight` 产出 formal `theme_service_response`
  - 在非 ready 场景下返回 `not_ready` 与 explanation object
  - 在 capability / service object 不匹配时返回 `scope_mismatch`

当前边界：

- Copilot / runtime 仍不应默认穿透内部目录读 canonical/raw/state
- serving surface 表达的是 owner-governed service truth，不是最终自然语言回答
