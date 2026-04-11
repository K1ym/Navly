# 2026-04-11 Navly_v1 Phase-1 Remaining Qinqin Live Transport Validation Matrix

日期：2026-04-11  
状态：phase-1-verification-governed  
用途：冻结 alpha 之后剩余 Qinqin Phase-1 端点的 live transport validation matrix、状态词汇与 expected classification matrix

---

## 1. 目标

`ASP-42` 不扩写 product logic。它只做一件事：

> 把 `recharge` / `account_trade` / `person` / `clock` / `market` / `commission` 这些剩余 Phase-1 Qinqin endpoint 的 transport 验证口径，收口成一份可审计、可复验、不会把 `fixture-only` 冒充成 `live-validated` 的 authoritative matrix。

---

## 2. Authoritative Status Vocabulary

### 2.1 `fixture-only`

含义：

- 当前只有 `FixtureQinqinTransport` 或 aggregate fixture surface 覆盖
- 还没有 `LiveQinqinTransport` loopback 证据

禁止误读：

- `fixture-only` 不是失败
- 但它也**不是** `live-validated`

### 2.2 `live-validated`

含义：

- 当前已经通过 `LiveQinqinTransport` 的真实 HTTP 代码路径
- 采用 repo 内 loopback harness 机械复验
- 验证 request assembly、HTTP / timeout / 404 / redaction 等 transport semantics

边界说明：

- `live-validated` 在这里指 **loopback live transport**
- 它不是对真实 upstream 凭证、真实门店、真实网络的成功承诺
- 因此它可以安全进入 reviewable docs / tests / runbooks，而不泄露 secrets

---

## 3. Remaining Endpoint Live Transport Validation Matrix

统一 safe entrypoint：

```bash
bash scripts/validate-remaining-phase1-live-transport.sh
```

| Slice | Endpoint Contract ID | Dataset Short Name | Current status | Current live path | Mechanical evidence |
| --- | --- | --- | --- | --- | --- |
| `finance_summary` | `qinqin.member.get_recharge_bill_list.v1_3` | `recharge` | `live-validated` | `response_received` | `platforms/data-platform/tests/test_finance_summary_vertical_slice.py::test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure` |
| `finance_summary` | `qinqin.member.get_user_trade_list.v1_4` | `account_trade` | `live-validated` | `source_empty` | `platforms/data-platform/tests/test_finance_summary_vertical_slice.py::test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure` |
| `staff_board` | `qinqin.staff.get_person_list.v1_5` | `person` | `live-validated` | `response_received` | `platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::test_staff_board_loopback_live_transport_paths` |
| `staff_board` | `qinqin.staff.get_tech_up_clock_list.v1_6` | `clock` | `live-validated` | `response_received` | `platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::test_staff_board_loopback_live_transport_paths` |
| `staff_board` | `qinqin.staff.get_tech_market_list.v1_7` | `market` | `live-validated` | `response_received` | `platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::test_staff_board_loopback_live_transport_paths` |
| `commission_setting` | `qinqin.staff.get_tech_commission_set_list.v1_8` | `commission` | `live-validated` | `source_empty` | `platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py::test_commission_setting_loopback_live_transport_source_empty_path` |

判断规则：

- 只有真正运行了 `LiveQinqinTransport` HTTP path 的 row 才能写成 `live-validated`
- 只跑 fixture regression 的 row 必须继续写成 `fixture-only`
- 当前 matrix 中剩余 direct Qinqin endpoint 已全部具备 loopback `live-validated` 证据
- `commission_setting` row 是 endpoint-scoped governance surface，不对应单独发布的 capability / default service object

---

## 4. Adjacent Fixture-Only Surfaces

下面这些对象不属于 direct Qinqin endpoint matrix，本轮仍然保持 `fixture-only`：

| Surface | Current status | Why it stays out of the direct transport matrix | Evidence |
| --- | --- | --- | --- |
| `navly.store.daily_overview` | `fixture-only` | 它是 projection / aggregate owner surface，不直接拥有 Qinqin transport | `platforms/data-platform/tests/test_daily_overview_owner_surface.py` |
| `navly.system.capability_explanation` | `fixture-only` | 它消费 owner surface 解释对象，不直接拥有 endpoint transport | `platforms/data-platform/tests/test_capability_explanation_owner_surface.py` |

这张表存在的原因只有一个：

> 明确告诉后续窗口：`fixture-only` 不是坏事，但也不能被 status board 偷偷写成 `live-validated`。

---

## 5. Classification Matrix

本节是剩余 slices 的 expected classification matrix。  
它回答的是：

> 当 live / fixture 结果落到 `source_empty / auth / sign / schema / transport` 这五条路径时，authoritative signal 到底应该落在哪里？

### 5.1 `finance_summary`

| classification path | expected classification | mechanical evidence |
| --- | --- | --- |
| `source_empty` | `endpoint_status=source_empty` + `terminal_outcome_category=source_empty` + `availability_status=source_empty` | `test_finance_summary_live_404_no_data_is_source_empty_not_transport_failure` |
| `auth` | `endpoint_status=failed` + `terminal_outcome_category=auth` + `error_taxonomy=source_auth_error` | `test_finance_summary_classifies_sign_auth_schema_and_transport` |
| `sign` | `endpoint_status=failed` + `terminal_outcome_category=sign` + `error_taxonomy=source_sign_error` | `test_finance_summary_classifies_sign_auth_schema_and_transport` |
| `schema` | `endpoint_status=failed` + `terminal_outcome_category=schema` + `error_taxonomy=source_schema_error` | `test_finance_summary_classifies_sign_auth_schema_and_transport` |
| `transport` | `endpoint_status=failed` + `terminal_outcome_category=transport` + `error_taxonomy=transport_timeout_error` | `test_finance_summary_classifies_sign_auth_schema_and_transport` |

### 5.2 `staff_board`

| classification path | expected classification | mechanical evidence |
| --- | --- | --- |
| `source_empty` | `endpoint_status=source_empty` + `availability_status=source_empty` + `vertical_slice_backbone_state.backbone_status=backbone_ready` | `test_source_empty_is_latest_usable_and_keeps_backbone_ready` |
| `auth` | `endpoint_status=failed` + `error_taxonomy=source_auth_error` | `test_source_auth_error_is_classified` |
| `sign` | `endpoint_status=failed` + `error_taxonomy=source_sign_error` | `test_source_sign_error_is_classified` |
| `schema` | `endpoint_status=failed` + `error_taxonomy=source_schema_error` | `test_source_schema_error_is_classified` |
| `transport` | `endpoint_status=failed` + `error_taxonomy=transport_timeout_error` | `test_transport_error_is_classified` |

说明：

- `staff_board` 当前不强制额外写 `terminal_outcome_category`
- 它的 authoritative signal 以 `endpoint_status` + `error_taxonomy` + latest-state/backbone truth 为主
- `staff_board` 当前 live loopback 证据冻结的是 successful transport path；`source_empty` classification 仍通过 fixture regression 保持显式，不在本 ASP 中伪装成已 live-promoted semantics

### 5.3 `commission_setting`

| classification path | expected classification | mechanical evidence |
| --- | --- | --- |
| `source_empty` | `endpoint_status=source_empty` + `terminal_outcome_category=source_empty` + `field_coverage_snapshot.coverage_status=source_empty_governed` + `commission_setting_completeness_state.reason_codes=source_empty_current` | `test_source_empty_is_current_zero_row_state` |
| `auth` | `endpoint_status=failed` + `terminal_outcome_category=auth` + `error_taxonomy=source_auth_error` + `schema_alignment_snapshot.alignment_status=blocked_upstream` | `test_auth_failure_points_to_runtime_header_variance` |
| `sign` | `endpoint_status=failed` + `terminal_outcome_category=sign` + `error_taxonomy=source_sign_error` + `schema_alignment_snapshot.alignment_status=blocked_upstream` | `test_commission_setting_sign_classification_stays_distinct_from_auth` |
| `schema` | `endpoint_status=completed` + `terminal_outcome_category=success` + `schema_alignment_snapshot.alignment_status=misaligned` + `commission_setting_completeness_state.completeness_status=blocked` | `test_schema_alignment_flags_type_and_governance_gaps` |
| `transport` | `endpoint_status=failed` + `terminal_outcome_category=transport` + `error_taxonomy=transport_timeout_error` + `commission_setting_completeness_state.reason_codes=latest_state_stale` | `test_stale_target_business_date_uses_prior_latest_usable_state` |

关键边界：

- `commission_setting` 的 `schema` path 不应被伪装成 generic upstream failure
- `commission_setting` 的 `auth` path 必须保留 runtime header variance 线索
- `commission_setting` 的 `sign` path 必须和 `auth` 分开，不得共享同一条 fake fallback

---

## 6. Runbook Linkage

操作说明见：

- `docs/runbooks/data-platform/remaining-phase-1-live-transport-validation.md`

该 runbook 负责：

- 如何安全执行 loopback live transport
- 如何读取 `fixture-only` / `live-validated`
- 如何判断某条结果该落到哪条 classification path

---

## 7. 结论

`ASP-42` 的 authoritative answer 不是“剩余 slices 都做成真实 upstream smoke”。

它的 authoritative answer 是：

1. direct Qinqin remaining endpoints 已有明确 live transport validation matrix
2. `fixture-only` 和 `live-validated` 的边界已经写死，不能再混写
3. `source_empty / auth / sign / schema / transport` 的 expected classification 路径已显式冻结
4. 这些输出可以被 `ASP-40` 的 full phase-1 acceptance gate 继续消费
