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

当前边界：

- 这里的脚本用于本地验证与示例产物写出，不是 live connector 或通用生产入口
- 当前 sample 实际写出的是 `raw-replay/`、`historical-run-truth/`、`canonical/`、`latest-state/`
- 当前 sample 不会写出 `projections/` 或 `serving/`
- remaining Phase-1 matrix helper 只服务 verification / docs / tests，不是生产 runtime 入口
