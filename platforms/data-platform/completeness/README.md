# Completeness

本目录负责 data-platform 的 readiness truth。

当前已具备：

- `member_insight_readiness_surface.py`
  - 为 `navly.store.member_insight` 产出 formal `capability_readiness_response`
  - 复用 latest-state、state traces、run traces
  - 区分 `ready / pending / failed / unsupported_scope`
- `qinqin_endpoint_completeness.py`
  - 为 Qinqin `v1.1` 全部 `8` 个 endpoint 产出 endpoint-scoped completeness objects
  - 固定 `landing_status`
  - 固定 `formalized_target_ids`
  - 固定 `completeness_status`
  - 固定最小 `backfill_progress_state`

当前边界：

- 这里只表达 data readiness / dependency truth
- 不持有 access truth
- 不替 runtime 组织最终回答文本
- endpoint completeness 与 capability readiness 分离表达，不再混成单一 slice 状态
