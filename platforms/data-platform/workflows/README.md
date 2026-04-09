# Workflows

本目录负责 data-platform 的 owner-side workflow orchestration。

当前已具备：

- `member_insight_owner_surface.py`
  - 调用 member insight vertical slice
  - 组装 readiness response
  - 组装 theme service response

当前边界：

- 当前仍是本地 owner-side workflow，不是 Temporal / production scheduler 落地
- 不在这里实现 runtime / bridge 接面代码
