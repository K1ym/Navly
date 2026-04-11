# Scripts

本目录承载 data-platform 的开发与验证脚本。

当前可用：

- `run_member_insight_vertical_slice.py`
  - 支持 `fixture` transport
  - 支持 `live` transport
  - 把实际 artifact tree 写到 `--output-dir`
- `phase1_remaining_live_transport_validation_matrix.py`
  - 输出 remaining Phase-1 Qinqin direct endpoint 的 live transport validation matrix
  - 冻结 `fixture-only` / `live-validated` 状态词汇与 expected classification path
- `run_nightly_sync_scheduler.py`
  - 读取 latest-state / prior-ledger JSON
  - 输出 scheduler snapshot / dispatch plan / cursor ledger
  - 作为后续 Temporal worker 对接前的本地 planning entrypoint
- `run_nightly_sync_worker.py`
  - 读取 persisted cursor ledger store
  - 运行 scheduler + ledger persistence
  - 输出 worker result / dispatch plan / cursor ledger
- `run_nightly_sync_runtime.py`
  - 执行 dispatch plan 对应的 actual nightly sync slice
  - 回写 final cursor ledger
  - 输出 runtime result 与本轮 artifact

当前边界：

- 这里的脚本用于本地验证与示例产物写出，不是 live connector 或通用生产入口
- 当前 sample 实际写出的是 `raw-replay/`、`historical-run-truth/`、`canonical/`、`latest-state/`
- 当前 sample 不会写出 `projections/` 或 `serving/`
- remaining Phase-1 matrix helper 只服务 verification / docs / tests，不是生产 runtime 入口
- nightly sync scheduler helper 当前只做 planning / ledger / dispatch snapshot，不直接发起真实 source sync
- nightly sync worker helper 当前已持久化 cursor ledger，但仍是本地 worker slice，不是完整 Temporal runtime
- nightly sync runtime helper 已可本地执行实际 slice，但仍未接到正式 Temporal cluster / deployed scheduler
