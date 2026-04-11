# Sync State Skeleton

本目录未来负责 latest state truth。

当前已落地：

- `latest_usable_state_backbone.py`
  - latest usable endpoint state
  - vertical slice backbone state
  - 当前已被 `member_insight` / `staff_board` vertical slices 复用
- `finance_summary_latest_state.py`
  - latest observed run 与 latest usable state 分离表达
  - `availability_status` 区分 `available` / `source_empty` / `unavailable`
  - prerequisite state 为 `finance_summary` 提供 blocking dependency 视图
- `commission_setting_sync_state.py`
  - 为 `GetTechCommissionSetList` 产出 latest usable endpoint state
  - 产出 business-day-policy-aware `backfill_progress_state`
  - 明确区分 currentness 与历史 backfill completeness
- `nightly_sync_cursor_state.py`
  - 把 nightly planner 输出收敛成 endpoint-scoped cursor state
  - 区分 `currentness_pending` / `backfill_pending` / `current_and_complete`
  - 明确给出 next currentness date 与 next backfill date
