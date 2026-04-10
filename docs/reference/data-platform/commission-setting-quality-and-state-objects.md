# Commission Setting Quality And State Objects

本文件记录 `GetTechCommissionSetList` 当前已经落地的 L2 governed objects。

它们都是 data-platform owner objects，不是 runtime prompt glue。

## 对象清单

### `field_coverage_snapshot`

用途：

- 记录当前 snapshot 观测到哪些 governed fields
- 区分 full observation、partial observation、`source_empty_governed`、`blocked_upstream`

当前状态值：

- `covered`
- `partial_observation`
- `source_empty_governed`
- `blocked_upstream`

### `schema_alignment_snapshot`

用途：

- 记录当前 payload 是否仍与 field catalog / response shape 对齐
- 显式列出 mismatch 与 ungoverned observed fields

当前状态值：

- `aligned`
- `source_empty_governed`
- `blocked_upstream`
- `misaligned`

### `backfill_progress_state`

用途：

- 表达目标业务日 currentness
- 表达历史 backfill completeness
- 附带 business-day boundary policy ref

当前状态值：

- `backfill_progress_status = complete / incomplete / blocked`
- `currentness_status = current / stale / blocked`

### `commission_setting_completeness_state`

用途：

- 把 latest usable state、backfill、coverage、schema-alignment 收敛成 endpoint-scoped completeness truth

当前状态值：

- `complete`
- `incomplete`
- `blocked`

当前 reason codes：

- `source_empty_current`
- `latest_state_stale`
- `schema_alignment_gap`
- `upstream_unavailable`

## 质量问题代码

当前 `quality_issue.issue_code` 主集合：

- `source_empty_current_day_full_replace`
- `upstream_auth_headers_required`
- `upstream_endpoint_error`
- `field_coverage_partial`
- `schema_alignment_gap`
- `backfill_gap`

说明：

- `source_empty_current_day_full_replace` 是 info 级解释，不等于失败
- `upstream_auth_headers_required` 必须带出 `qinqin.auth.tech-commission-set-runtime-headers-required`
