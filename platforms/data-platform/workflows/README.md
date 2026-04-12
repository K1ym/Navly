# Workflows

本目录负责 data-platform 的 owner-side workflow orchestration。

当前已具备：

- `member_insight_owner_surface.py`
  - sync-backed owner surface：调用 member insight vertical slice
  - snapshot-backed owner surface：读取 persisted truth substrate
  - 组装 readiness response
  - 组装 theme service response
- `postgres_temporal_nightly_sync.py`
  - `NightlySyncPlanner`
  - `NightlySyncRuntime`
  - `TemporalNightlySyncPlane`
  - nightly / backfill / retry / rerun 的 repo-authoritative workflow path

当前边界：

- `member_insight_owner_surface.py` 同时承载：
  - owner-side local sync path
  - persisted snapshot query path
- `postgres_temporal_nightly_sync.py` 是当前 intended production orchestration path
- workflow 仍不拥有数据真相；run/state/quality/readiness/projection 必须写回 PostgreSQL truth substrate
- 不在这里实现 runtime / bridge 接面代码
