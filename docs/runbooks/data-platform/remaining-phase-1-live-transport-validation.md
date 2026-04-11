# Remaining Phase-1 Live Transport Validation

日期：2026-04-11  
状态：active-verification-runbook  
适用范围：`finance_summary` / `staff_board` / `commission_setting` 的 remaining Phase-1 live transport validation matrix

## 1. 目的

本手册说明如何安全复验 `ASP-42` 的 remaining Phase-1 Qinqin live transport validation matrix。

这里的“safe live execution”指：

- 使用 `LiveQinqinTransport`
- 走真实 HTTP request / response / timeout / header redaction 代码路径
- 但通过本地 loopback harness 复验
- 不要求真实 upstream 凭证
- 不把 `fixture-only` 伪装成 `live-validated`

## 2. 单一入口

```bash
bash scripts/validate-remaining-phase1-live-transport.sh
```

当前 entrypoint 会运行：

- `platforms/data-platform/tests/test_finance_summary_vertical_slice.py`
- `platforms/data-platform/tests/test_staff_board_vertical_slice.py`
- `platforms/data-platform/tests/test_commission_setting_governance_surface.py`
- `platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py`

## 3. 结果怎么读

### 3.1 `live-validated`

当验证资产写成 `live-validated` 时，含义是：

- `LiveQinqinTransport` 的 HTTP path 已被机械执行
- request path、response HTTP status、transport replay artifact、header redaction 都有证据

它**不是**：

- 真实 upstream 网络一定可用
- 真实门店 secrets 已通过

### 3.2 `fixture-only`

当验证资产写成 `fixture-only` 时，含义是：

- 当前只有 fixture regression 或 aggregate surface coverage
- 没有 direct endpoint live transport 证据

当前仍保持 `fixture-only` 的 adjacent surfaces：

- `navly.store.daily_overview`
- `navly.system.capability_explanation`

## 4. Classification Path 读法

当前剩余 slices 的 classification matrix 固定为：

- `source_empty`
- `auth`
- `sign`
- `schema`
- `transport`

读法规则：

- `finance_summary`
  - 以 `endpoint_status` + `terminal_outcome_category` + `error_taxonomy` 为主
- `staff_board`
  - 以 `endpoint_status` + `error_taxonomy` + latest-state/backbone truth 为主
- `commission_setting`
  - 以 `endpoint_run` truth 加上 `field_coverage_snapshot` / `schema_alignment_snapshot` / `commission_setting_completeness_state` 为主

## 5. 常见结论

### 5.1 `source_empty`

不要把它判成 transport failure。

authoritative examples：

- `account_trade`
  - `endpoint_status=source_empty`
- `market`
  - `endpoint_status=source_empty` 且 `backbone_status=backbone_ready`
- `commission`
  - `coverage_status=source_empty_governed`

### 5.2 `auth`

不要把它写成“暂时没数据”。

authoritative examples：

- `finance_summary`
  - `terminal_outcome_category=auth`
- `staff_board`
  - `error_taxonomy=source_auth_error`
- `commission`
  - `terminal_outcome_category=auth`
  - 保留 runtime header variance

### 5.3 `sign`

不要和 `auth` 合并。

当前 `commission` 的 sign path 明确要求：

- `terminal_outcome_category=sign`
- `error_taxonomy=source_sign_error`
- 不附带 auth header variance

### 5.4 `schema`

不要和 generic upstream failure 合并。

尤其 `commission`：

- `schema_alignment_snapshot.alignment_status=misaligned`
- `commission_setting_completeness_state.completeness_status=blocked`

### 5.5 `transport`

transport failure 只能在 transport layer 落地，不允许被改写成 source_empty。

authoritative signal：

- `error_taxonomy=transport_timeout_error`

## 6. Secrets 约束

- 不要把真实 `Authorization`、`Token`、`AppSecret` 写入 repo artifact
- loopback tests 可以验证 header redaction，但必须用 demo 值
- 当前 runbook 不要求真实 upstream credentials

## 7. Source Of Truth

authoritative docs / helpers：

- `docs/specs/navly-v1/verification/2026-04-11-navly-v1-phase-1-remaining-qinqin-live-transport-validation-matrix.md`
- `platforms/data-platform/scripts/phase1_remaining_live_transport_validation_matrix.py`
