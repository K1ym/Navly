# Navly Data Platform

状态：milestone-a skeleton / seed only

本目录是 `Navly_v1` 数据中台的实现骨架入口。

当前只完成：

- `platforms/data-platform/` 目录骨架
- C0 seed
  - data-platform owner contracts seed
  - directory / registry placeholder seed
- 与 `docs/specs/navly-v1/data-platform/` 的实现边界对齐

当前**未完成**：

- 完整 connector 逻辑
- 完整 ingestion 工作流
- 大量业务 SQL / dbt 模型
- latest state / readiness / projection 的真实实现
- 对外 serving API 实现

## 当前边界

- 跨模块 shared contracts owner：`shared/contracts`
- `platforms/data-platform/contracts/`：只保留 data-platform owner contracts
- `platforms/data-platform/directory/`：只保留 data-platform 当前纳管 registry seed / placeholder

## C0-L3 目录映射

- C0：`contracts/` + `directory/`
- L0：`connectors/` + `ingestion/` + `raw-store/`
- L1：`warehouse/`
- L2：`sync-state/` + `quality/` + `completeness/`
- L3：`projections/` + `serving/`
- 编排支撑：`workflows/`

## 重要说明

- 现在只是 milestone A skeleton / seed
- 这不代表 phase-1 已完成
- Copilot / runtime 默认仍不应直读本目录中的内部实现层
