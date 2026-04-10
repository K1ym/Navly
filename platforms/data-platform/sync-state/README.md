# Sync State Skeleton

本目录未来负责 latest state truth。

当前已落地：

- `finance_summary_latest_state.py`
  - latest observed run 与 latest usable state 分离表达
  - `availability_status` 区分 `available` / `source_empty` / `unavailable`
  - prerequisite state 为 `finance_summary` 提供 blocking dependency 视图

`member_insight` 仍保持 milestone A 的最小 backbone 状态表达。
