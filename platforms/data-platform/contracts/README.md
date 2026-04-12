# Data Platform Owner Contracts

本目录只存放 **data-platform owner contracts**。

不在此定义跨模块 shared contracts；跨模块主定义权属于 `shared/contracts`。

当前 contract-governance 约束包括：

- owner contract ownership freeze
- source / endpoint / parameter / field / landing / variance entry shape
- PostgreSQL-first truth substrate entry shape
- Temporal-native scheduler / worker state entry shape
- 对 registry root 附加元数据的说明

Qinqin v1.1 的 formal registry root 语义由 `docs/specs/data-platform/` 下的对应规格补充说明。

closeout lane 重要说明：

- milestone-B artifact/backbone contracts 仍可保留用于 diagnostics 兼容
- 生产 authoritative path 必须以 PostgreSQL truth substrate / Temporal workflow contracts 为准
