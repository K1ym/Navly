# Warehouse

本目录负责 canonical fact truth。

当前 closeout lane 已明确：

- member insight canonical facts 已在 repo code 内具备正式持久化语义
- PostgreSQL truth substrate 已冻结对应 fact table 形状
- persisted snapshot / nightly runner / bridge path 都会写入 canonical fact truth

当前仍未完成：

- live PostgreSQL adapter 绑定
- dbt runtime / warehouse model materialization
- 其余 capability 的 canonical fact fan-out
