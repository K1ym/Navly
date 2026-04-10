# Raw Store

本目录负责 raw request / response / replay 的持久化与读取。

当前已落地的事实边界：

- `historical-run-truth/ingestion-runs.json`
- `historical-run-truth/endpoint-runs.json`
  - 包含 endpoint terminal outcome category
- `raw-replay/raw-response-pages.json`
  - source page truth
- `raw-replay/transport-replay-artifacts.json`
  - transport replay truth
  - request URL / method / payload
  - redacted request headers
  - HTTP status / headers / body
  - explicit error taxonomy

设计约束：

- 不把 transport replay truth 和 source page truth 混成一个表意层
- 不把 latest usable state 写回 historical run truth
- replay artifact 不写明文敏感 header 值
