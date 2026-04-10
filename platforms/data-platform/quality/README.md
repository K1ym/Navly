# Quality

本目录负责 data-platform 的 field coverage、schema alignment 与 quality issue。

当前已落地：

- `commission_setting_quality.py`
  - 为 `GetTechCommissionSetList` 产出 `field_coverage_snapshot`
  - 为 `GetTechCommissionSetList` 产出 `schema_alignment_snapshot`
  - 把 `source_empty` 与 runtime header auth variance 转成 machine-explainable `quality_issue`

当前边界：

- 这里只表达质量真相，不改写 historical run truth
- quality issue 只解释数据与治理问题，不生成上层 service 对象
