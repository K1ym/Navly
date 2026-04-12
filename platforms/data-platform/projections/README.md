# Projections

本目录负责 theme / service truth 的内部构建。

当前 closeout lane 已明确：

- `service_projection` 是 repo-authoritative persisted serving object
- nightly runner / status query / snapshot-backed owner surface 已消费或暴露该 truth

当前仍未完成：

- 独立 projection module fan-out
- 其余 capability 的 formal serving objects
