# Quality

本目录负责数据中台的 endpoint governance truth。

当前已具备：

- `qinqin_endpoint_governance.py`
  - 为 Qinqin `v1.1` 全部 `8` 个 endpoint 产出 machine-readable governance result
  - 固定 `field_coverage_snapshot`
  - 固定 `schema_alignment_snapshot`
  - 固定 `quality_status` / `quality_issues`
  - 统一 `source_empty / auth_failure / sign_failure / schema_failure / business_failure`
- `build_five_store_endpoint_validation_matrix(...)`
  - 为五店验证输出 store x endpoint 质量矩阵
  - 同时回答 `did_run` 与 `fields_aligned`

当前边界：

- 这里只表达治理真相，不表达 capability service object
- 这里只依赖受治理 field catalog / landing policy / endpoint runs
- 不要求上层回 raw replay 重新解释字段对齐
