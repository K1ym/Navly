# 2026-04-12 Qinqin Endpoint Governance Proof And Structured Target Closure

日期：2026-04-12  
状态：implemented-in-phase1-lane  
范围：`ASP-47` / `ASP-48`

---

## 1. 文档目的

本文档冻结 Qinqin `v1.1` 八条正式 endpoint 在 Navly 数据中台中的：

- structured target formal landing
- field coverage / schema alignment proof object
- endpoint-scoped completeness object
- five-store validation matrix

它回答的是：

> phase-1 的 governance / structured-target lane 现在到底落成了哪些正式对象，
> 这些对象之间怎么分层，
> 上层如何证明“跑过了”和“字段对齐了”是两件不同但都可回答的事。

---

## 2. 正式对象

### 2.1 L1 Structured Target Objects

实现入口：

- `platforms/data-platform/warehouse/qinqin_structured_target_landing.py`

职责：

- 把 `endpoint-manifest.md` / `field-landing-policy.seed.json` 中纳管的全部 `19` 个 structured targets 落成正式对象
- 输出 dataset-scoped rows，而不是要求上层回 raw replay 取字段
- 保留最小 lineage：`raw_page_id`、`replay_artifact_id`、`source_record_path`

当前正式对象集合：

- `customer`
- `customer_card`
- `customer_ticket`
- `customer_coupon`
- `consume_bill`
- `consume_bill_payment`
- `consume_bill_info`
- `recharge_bill`
- `recharge_bill_payment`
- `recharge_bill_ticket`
- `recharge_bill_sales`
- `account_trade`
- `staff`
- `staff_item`
- `tech_shift_item`
- `tech_shift_summary`
- `sales_commission`
- `commission_setting`
- `commission_setting_detail`

### 2.2 L2 Governance Proof Objects

实现入口：

- `platforms/data-platform/quality/qinqin_endpoint_governance.py`

每个 endpoint 都会产出：

1. `field_coverage_snapshot`
2. `schema_alignment_snapshot`
3. `quality_status`
4. `quality_issues`

约束：

- 所有字段都来自 `endpoint-field-catalog.seed.json`
- 所有 landing 归属都来自 `field-landing-policy.seed.json`
- `quality_status` 必须能统一表达：
  - `source_empty`
  - `auth_failure`
  - `sign_failure`
  - `schema_failure`
  - `business_failure`

### 2.3 L2 Completeness Objects

实现入口：

- `platforms/data-platform/completeness/qinqin_endpoint_completeness.py`

每个 endpoint 都会产出：

- `completeness_status`
- `landing_status`
- `formalized_target_ids`
- `latest_usable_business_date`
- `backfill_progress_state`

说明：

- 这里表达的是 endpoint-scoped completeness truth
- 它不同于 capability readiness，也不同于 raw run truth

### 2.4 Five-Store Validation Matrix

实现入口：

- `build_five_store_endpoint_validation_matrix(...)`

它的目标不是重放 raw payload，而是回答两类治理问题：

1. `did_run`
2. `fields_aligned`

因此每一行至少固定输出：

- `org_id`
- `endpoint_contract_id`
- `run_status`
- `did_run`
- `schema_alignment_status`
- `fields_aligned`
- `quality_status`
- `completeness_status`

---

## 3. 分层边界

### 3.1 L0 不再是上层 reachability 的唯一入口

raw replay 仍然保留，但它只负责：

- 历史执行真相
- 回放与审计

它不再是 structured targets 的正式消费面。

### 3.2 L1 / L2 明确分离

- `warehouse/qinqin_structured_target_landing.py`：表达结构化对象真相
- `quality/qinqin_endpoint_governance.py`：表达字段覆盖 / 结构对齐 / 质量归因真相
- `completeness/qinqin_endpoint_completeness.py`：表达 endpoint completeness 真相

这三层不能混成同一个“状态 JSON”。

### 3.3 上层默认不需要回 raw replay 翻字段

当上层需要：

- `customer_coupon`
- `recharge_bill_sales`
- `commission_setting_detail`

等对象时，正式来源已经是 structured target artifacts，而不是 raw payload leftover。

---

## 4. 验证口径

当前 lane 的机械验证落在：

- `platforms/data-platform/tests/test_qinqin_endpoint_governance_closure.py`

覆盖：

- `19/19` structured target landing
- `8/8` endpoint governance proof
- `8/8` endpoint completeness result
- 五店 validation matrix
- `source_empty / auth / sign / schema / business` taxonomy

---

## 5. 非目标

本次 closure 不负责：

- runtime 默认 serving read path 闭合
- host publication
- WeCom live host closure

这些能力仍应在各自 workstream 中消费本次落成的 proof objects，而不是要求本次 lane 顺带完成。
