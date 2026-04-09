# Scripts

本目录承载 data-platform 的开发与验证脚本。

当前可用：

- `run_member_insight_vertical_slice.py`：使用 fixture transport 跑当前 member insight milestone B sample，并把实际 artifact tree 写到 `--output-dir`

当前边界：

- 这里的脚本用于本地验证与示例产物写出，不是 live connector 或通用生产入口
- 当前 sample 实际写出的是 `raw-replay/`、`historical-run-truth/`、`canonical/`、`latest-state/`
- 当前 sample 不会写出 `projections/` 或 `serving/`
