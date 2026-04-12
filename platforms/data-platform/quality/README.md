# Quality

本目录负责 field coverage、schema alignment、quality issue。

当前 closeout lane 已明确：

- `field_coverage_snapshot`
- `schema_alignment_snapshot`
- `quality_issue`
- operator-facing `quality_report`

这些对象已经在 PostgreSQL truth substrate model、nightly runner、status query path 中具备 repo-authoritative 语义。

当前仍未完成：

- 全 8 端点治理矩阵
- live PostgreSQL adapter / operator tool publication
