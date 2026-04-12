# Warehouse

本目录负责 canonical / structured fact truth。

当前已具备：

- `member_insight_canonical_backbone.py`
  - 已改为复用通用 structured-target landing，而不是继续维持 endpoint-specific canonicalizer
- `qinqin_structured_target_landing.py`
  - 直接读取 field catalog + landing policy
  - 将 manifest 中全部 `19` 个 structured targets 落成正式对象
  - 每行保留最小 lineage：`raw_page_id`、`replay_artifact_id`、`source_record_path`

当前边界：

- 这里表达结构化对象真相
- 不表达 field coverage / schema alignment / completeness
- 当前仍不实现 SQL / dbt 物理模型
