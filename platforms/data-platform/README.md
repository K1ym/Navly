# Navly Data Platform

状态：milestone-b backbone

本目录是 `Navly_v1` 数据中台的实现骨架与 backbone 入口。

当前已经完成：

- `platforms/data-platform/` 目录骨架
- C0 seed
  - data-platform owner contracts seed
  - directory / registry seed / placeholder
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
- 基础单测与 CLI runner

当前**未完成**：

- live connector / real HTTP transport / 完整错误分类治理
- 全量 endpoint 铺开
- PostgreSQL / dbt / 持久化模型落地
- 完整 latest state / quality / readiness / projection runtime 逻辑
- rich serving / UI / 多消费端接口
- phase-1 全链路闭合

## 当前边界

- 跨模块 shared contracts owner：`shared/contracts`
- `platforms/data-platform/contracts/`：只保留 data-platform owner contracts
- `platforms/data-platform/directory/`：承载 data-platform 当前纳管 registry、seed 与 placeholder
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

## 重要说明

- 当前已不再只是 milestone A skeleton / seed only
- 当前状态更准确地说是：**milestone B backbone 已建立，但 phase-1 远未完成**
- 现阶段不能把本目录描述成“完整 ingestion / readiness / serving / persistence 已完成”
