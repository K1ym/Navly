# Navly Data Platform

状态：milestone-b backbone with published phase-1 owner surfaces

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
  - 当前最小 canonical outputs：`customer`、`customer_card`、`customer_ticket`、`customer_coupon`、`consume_bill`、`consume_bill_payment`、`consume_bill_info`
- latest usable state / historical run separation backbone
  - latest usable endpoint state 已与 historical run truth 分离承载
- commission-setting state / quality governance slice
  - endpoint-scoped canonical outputs：`commission_setting`、`commission_setting_detail`
  - `GetTechCommissionSetList` 的 `field_coverage_snapshot`
  - `schema_alignment_snapshot`
  - business-day-aware `backfill_progress_state`
  - endpoint-scoped `commission_setting_completeness_state`
- vertical slice orchestration backbone
  - `navly.store.member_insight`
  - `navly.service.store.member_insight`
- formal owner-side readiness / service surfaces
  - `completeness/member_insight_readiness_surface.py`
  - `serving/member_insight_theme_service_surface.py`
  - `completeness/finance_summary_readiness_surface.py`
  - `serving/finance_summary_theme_service_surface.py`
  - `completeness/staff_board_readiness_surface.py`
  - `serving/staff_board_theme_service_surface.py`
  - `completeness/daily_overview_readiness_surface.py`
  - `serving/daily_overview_theme_service_surface.py`
  - `serving/capability_explanation_service_surface.py`
- owner-side orchestration
  - `workflows/member_insight_owner_surface.py`
  - `workflows/finance_summary_owner_surface.py`
  - `workflows/staff_board_owner_surface.py`
  - `workflows/daily_overview_owner_surface.py`
  - `workflows/capability_explanation_owner_surface.py`
- service projections
  - `projections/finance_summary_service_projection.py`
  - `projections/staff_board_service_projection.py`
  - `projections/daily_overview_service_projection.py`
  - `projections/capability_explanation_service_projection.py`
- 基础单测与 CLI runner
- Qinqin v1.1 contract governance consistency tests
- capability dependency registry freeze
  - `contracts/capability-dependency-entry.contract.seed.json`
  - `directory/capability-dependency-registry.seed.json`
  - `directory/capability_dependency_registry.py`
- nightly sync planner policy
  - `contracts/nightly-sync-policy-entry.contract.seed.json`
  - `directory/nightly-sync-policy.seed.json`
  - `directory/nightly_sync_policy_registry.py`
  - `ingestion/nightly_sync_planner.py`
- nightly sync cursor state
  - `contracts/nightly-sync-cursor-state-entry.contract.seed.json`
  - `sync-state/nightly_sync_cursor_state.py`

当前**未完成**：

- live connector / real HTTP transport / 完整错误分类治理
- production scheduler / Temporal execution plane
- persisted nightly sync cursor ledger storage
- 全量 endpoint 铺开
- PostgreSQL / dbt / 持久化模型落地
- 完整 latest state / quality / readiness / projection runtime 逻辑
- rich serving / UI / 多消费端接口
- phase-1 全链路闭合

## 当前边界

- 跨模块 shared contracts owner：`shared/contracts`
- `platforms/data-platform/contracts/`：只保留 data-platform owner contracts
- `platforms/data-platform/directory/`：承载 data-platform 当前纳管 registry；Qinqin v1.1 contract governance、business-day boundary policy、capability dependency matrix 已进入 formal registry，其余 capability 元数据仍可能保留 seed 状态
- readiness / serving / ingestion 若需要 capability dependency truth，应读取 `capability-dependency-registry.seed.json`
- data-platform 不拥有 access truth
- data-platform 当前实现仍然只是在自身 owner scope 内推进 raw truth / canonical fact truth / latest state backbone

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
- runtime / Copilot 不应默认直读：
  - `connectors/`
  - `ingestion/`
  - `raw-store/`
  - `warehouse/`
  - `sync-state/`
  - `quality/`
  - `completeness/`
  - `projections/`
- 当前 milestone B 已具备 backbone，但这**不等于** ready / service runtime 已完成
- 当前已对 `member_insight` / `finance_summary` / `staff_board` / `daily_overview` 发布 formal owner-side readiness / theme service surface
- `navly.service.system.capability_explanation` 作为 companion service surface 已可从 serving boundary 受控读取
- runtime 还未在默认路径消费完整 phase-1 service set

## 重要说明

- 当前已不再只是 milestone A skeleton / seed only
- 当前状态更准确地说是：**phase-1 acceptance 已闭合，但 productionized scheduler / persistence / long-running execution plane 仍未完成**
- 现阶段不能把本目录描述成“完整 production night-run / persistence / adaptive backfill engine 已完成”
