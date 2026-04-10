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
