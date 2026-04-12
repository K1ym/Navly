# Navly Data Platform

状态：milestone-b backbone

本目录是 `Navly_v1` 数据中台的实现骨架与 backbone 入口。

当前已经完成：

- `platforms/data-platform/` 目录骨架
- C0 contract governance freeze
  - data-platform owner contracts freeze
  - Qinqin v1.1 directory formal registry
- shared connector substrate（seed/backbone）
  - `backbone_support/qinqin_substrate.py`
  - `connectors/qinqin/qinqin_substrate.py`
- raw replay backbone
  - ingestion run / endpoint run 历史执行真相骨架
  - raw response page capture / replay artifact 写出能力
- first canonical landing（member insight vertical slice）
  - `GetCustomersList`
  - `GetConsumeBillList`
  - 当前最小 canonical outputs：`customer`、`customer_card`、`consume_bill`、`consume_bill_payment`、`consume_bill_info`
- latest usable state / historical run separation backbone
  - latest usable endpoint state 已与 historical run truth 分离承载
- vertical slice orchestration backbone
  - `navly.store.member_insight`
  - `navly.service.store.member_insight`
- first formal owner-side readiness / theme service surface
  - `completeness/member_insight_readiness_surface.py`
  - `serving/member_insight_theme_service_surface.py`
- phase-1 owner/service surface closure
  - `workflows/qinqin_phase1_owner_surface.py`
  - `serving/qinqin_phase1_theme_service_surface.py`
  - `completeness/qinqin_phase1_readiness_surface.py`
  - formal service set:
    - `navly.service.store.member_insight`
    - `navly.service.store.finance_summary`
    - `navly.service.store.staff_board`
    - `navly.service.store.daily_overview`
    - `navly.service.system.capability_explanation`
- 基础单测与 CLI runner
- Qinqin v1.1 contract governance consistency tests
- full structured-target landing backbone
  - `warehouse/qinqin_structured_target_landing.py`
  - 覆盖 manifest 中全部 `19` 个 structured targets
- endpoint governance proof backbone
  - `quality/qinqin_endpoint_governance.py`
  - 为全部 `8` 个 endpoint 产出 `field_coverage_snapshot` / `schema_alignment_snapshot` / `quality_issues`
- endpoint completeness closure backbone
  - `completeness/qinqin_endpoint_completeness.py`
  - 为全部 `8` 个 endpoint 产出 endpoint-scoped completeness objects
- five-store governance validation matrix
  - `build_five_store_endpoint_validation_matrix(...)`
  - 可同时回答 “did it run” 与 “did fields align”

当前**未完成**：

- live connector / real HTTP transport / 完整错误分类治理
- PostgreSQL / dbt / 持久化模型落地
- rich serving / UI / 多消费端接口
- phase-1 全链路闭合

## 当前边界

- 跨模块 shared contracts owner：`shared/contracts`
- `platforms/data-platform/contracts/`：只保留 data-platform owner contracts
- `platforms/data-platform/directory/`：承载 data-platform 当前纳管 registry；Qinqin v1.1 contract governance 已进入 formal registry，其余对象仍可能是 seed / placeholder
- data-platform 不拥有 access truth
- data-platform 当前实现已在自身 owner scope 内闭合 phase-1 service/serving 默认读边界，但这仍不等于 Postgres truth substrate、live host、或 full phase-1 acceptance 已完成

## C0-L3 目录映射

- C0：`contracts/` + `directory/`
- L0：`connectors/` + `ingestion/` + `raw-store/`
- L1：`warehouse/`
- L2：`sync-state/` + `quality/` + `completeness/`
- L3：`projections/` + `serving/`
- 编排支撑：`workflows/`
- Python backbone support：`backbone_support/`

## 对 runtime / Copilot 的默认读取边界

- 默认读取边界仍应是 `serving/`
- phase-1 默认 service set：
  - `navly.service.store.member_insight`
  - `navly.service.store.finance_summary`
  - `navly.service.store.staff_board`
  - `navly.service.store.daily_overview`
  - `navly.service.system.capability_explanation`
- runtime / Copilot 不应默认直读：
  - `connectors/`
  - `ingestion/`
  - `raw-store/`
  - `warehouse/`
  - `sync-state/`
  - `quality/`
  - `completeness/`
  - `projections/`
- 当前 milestone B 已具备 guarded owner-side surface set，但这**不等于** Postgres-first truth substrate、host publication、或 live runtime 已完成
- runtime 默认 owner-side data adapter 已切到上述 formal owner/service surfaces；默认路径不再直接读 artifact/backbone internals
- 当前 `quality/` 与 `completeness/` 已具备 endpoint-governance / completeness proof objects，并为 phase-1 service set 提供稳定依赖边界

## 重要说明

- 当前已不再只是 milestone A skeleton / seed only
- 当前状态更准确地说是：**milestone B backbone + phase-1 owner/service set 已建立，但 phase-1 远未完成**
- 现阶段不能把本目录描述成“完整 ingestion / readiness / serving / persistence / live closure 已完成”
