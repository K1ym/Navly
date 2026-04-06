# 2026-04-06 Navly_v1 数据中台开源项目采用策略

日期：2026-04-06  
状态：phase-1-adoption-baseline  
用途：定义 `Navly_v1` 数据中台在 phase-1 与后续阶段对 upstream 的采用策略，明确哪些属于核心依赖、可选实现手段、后续增强，以及哪些明确不属于 data-platform 内核

---

## 1. 文档目的

本文档回答：

> 数据中台为了实现 contract truth / raw truth / canonical fact truth / latest state truth / readiness truth / theme-service truth，当前应采用哪些 upstream，为什么采用，放在哪一层，以及哪些 upstream 明确不应进入内核？

---

## 2. 采用原则

### 2.1 truth boundary 先于技术组件

所有 upstream 的采用都必须服从以下真相边界：

1. contract truth
2. raw truth
3. canonical fact truth
4. latest state truth
5. readiness truth
6. theme / service truth

技术组件只是实现这些 truth 的手段，不能反过来用组件名字重命名 truth boundary。

### 2.2 phase-1 只采用闭合主链路所需的最小核心集

phase-1 的目标是闭合：

- C0
- L0
- L1
- L2
- L3

而不是把所有看起来先进的 upstream 一起堆进去。

### 2.3 执行依赖与真相依赖必须区分

- 有些组件是 **长期真相层依赖**
- 有些组件只是 **当前阶段偏好的执行 / 编排 / 建模手段**
- 有些组件只是 **后续增强**
- 有些组件 **明确不属于数据中台内核**

### 2.4 OpenClaw / LangGraph 的边界必须明确排除

尽管它们可能在 Navly_v1 整体系统中出现，但它们不应进入 data-platform 内核的 truth layer。

---

## 3. 数据中台 phase-1 推荐基线

当前推荐的 phase-1 基线是：

- **PostgreSQL**
- **dbt Core**
- **Temporal**

说明：

- PostgreSQL：统一 truth substrate
- dbt Core：L1-L3 的显式建模与测试手段
- Temporal：后台编排与补数工作流手段

phase-1 不要求默认引入：

- Hasura
- Cube
- pgvector
- Debezium
- Kafka / Redpanda
- TimescaleDB

更不应把以下组件并入 data-platform 内核：

- OpenClaw
- LangGraph

---

## 4. 采用分类总览

| Upstream | phase 判断 | 放置位置 | 分类 | 核心判断 |
| --- | --- | --- | --- | --- |
| PostgreSQL | phase-1 核心 | C0-L3 统一持久化 substrate | 长期内核依赖 | 必用 |
| dbt Core | phase-1 核心 | `warehouse/`、`sync-state/`、`quality/`、`projections/` 的建模与测试平面 | 核心实现手段 | 必用 |
| Temporal | phase-1 核心 | `workflows/`、`ingestion/`、补数与重算编排 | 核心实现手段 | 必用 |
| GraphQL Engine / Hasura | phase-1 可选扩展 | `serving/` 外侧的 GraphQL 读边界 | 可选实现手段 | 不必用 |
| Cube | phase-1 可选扩展 | semantic serving / metrics layer | 可选实现手段 | 不必用 |
| pgvector | phase-1 可选扩展 | explanation / audit / docs 检索增强 | 可选实现手段 | 不必用 |
| Debezium | phase-2 / 后续增强 | future CDC ingress | 后续增强 | 当前不必用 |
| Kafka / Redpanda | phase-2 / 后续增强 | future event bus | 后续增强 | 当前不必用 |
| TimescaleDB | phase-2 / 后续增强 | future temporal analytics adjunct | 后续增强 | 当前不必用 |
| OpenClaw | 明确不属内核 | permission kernel / gateway | 内核外组件 | 不应进入 data-platform truth layer |
| LangGraph | 明确不属内核 | Copilot runtime / orchestration | 内核外组件 | 不应进入 data-platform truth layer |

---

## 5. Phase-1 核心 upstream

### 5.1 PostgreSQL

### 放置位置

- `contracts/`、`directory/` 的 registry persistence（如需持久化）
- `raw-store/` 的 raw payload / replay index
- `warehouse/` 的 canonical facts
- `sync-state/`、`quality/`、`completeness/` 的 L2 truth objects
- `projections/` 的 theme / service snapshots

### 为什么选

1. phase-1 需要统一承载 C0-L3
2. 同时支持 relational truth 与 JSONB raw preservation
3. 对 batch-first、backfill-first、audit-first 的当前策略最稳妥
4. 能避免 phase-1 过早把 truth 分散到多存储

### 分类判断

- **phase-1 核心**
- **长期内核依赖**

### 关键边界提醒

PostgreSQL 是 truth substrate，但不是 truth semantics 本身。

真正的 truth 仍然必须按：

- contract
- raw
- canonical fact
- latest state
- readiness
- theme/service

分开建模，不能因为都放在 Postgres 里就混表。

---

### 5.2 dbt Core

### 放置位置

优先放在：

- `warehouse/`
- `sync-state/`
- `quality/`
- `projections/`

并服务于：

- canonical models
- dataset availability models
- quality tests
- projection / theme snapshot models

### 为什么选

1. phase-1 需要显式的模型定义、测试与 lineage
2. 能把 L1/L2/L3 从“脚本堆积”提升为受治理建模
3. 与 Git 版本化协同更自然
4. 对 Navly 当前的可审计、可补数、可回归目标更合适

### 分类判断

- **phase-1 核心**
- **核心实现手段**

### 关键边界提醒

dbt Core 用来实现 L1-L3 的建模，但不应成为外部稳定 API 本身。

也就是说：

- dbt model 名不是 Copilot 默认接口
- dbt 结果仍需通过 `serving/` 暴露

---

### 5.3 Temporal

### 放置位置

优先放在：

- `workflows/`
- `ingestion/`
- 补数重算、projection refresh、quality reconcile 的编排层

### 为什么选

1. phase-1 需要可靠的 daily sync / rerun / backfill / retry
2. 需要把 run 组织、补数、重算从 ad-hoc 脚本提升为受控工作流
3. 对长时间、多门店、全历史任务更稳妥

### 分类判断

- **phase-1 核心**
- **核心实现手段**

### 关键边界提醒

Temporal workflow history 不是 latest state truth。

不能把：

- workflow status
- activity retry status
- workflow history

直接当成：

- latest usable sync state
- readiness truth

这些 truth 仍必须落回 `sync-state/`、`quality/`、`completeness/`。

---

## 6. Phase-1 可选扩展 upstream

### 6.1 GraphQL Engine / Hasura

### 放置位置

若采用，建议位于：

- `serving/` 之外的对外 GraphQL 读接口层

### 为什么可选

它适合：

1. 多消费方需要统一 GraphQL 读接口
2. L3 service object 已稳定，需要更标准的对外查询层
3. 明确需要 schema introspection 与 API 网关能力

### 分类判断

- **phase-1 可选扩展**
- **可选实现手段**

### 为什么不是内核必需

phase-1 的关键是先把 service truth 建立起来。

即使没有 Hasura，数据中台也必须能成立；否则说明 truth boundary 还没成立，只是依赖外部 API 形状强行包装。

### 关键边界提醒

- Hasura 不应直接把 `raw-store/`、`warehouse/`、`sync-state/`、`quality/`、`completeness/` 物理表暴露给 Copilot
- Hasura 不应取代权限内核成为访问真相源
- Hasura 若采用，也只能站在 `serving/` 之后，而不能穿透到 data-platform 内核定义 truth

---

### 6.2 Cube

### 放置位置

若采用，建议位于：

- `projections/` 与 `serving/` 之上的 semantic serving / metrics 层

### 为什么可选

它适合：

1. 指标语义需要统一定义
2. 需要预聚合与多消费端一致口径
3. HQ / 跨店查询负载显著增长

### 分类判断

- **phase-1 可选扩展**
- **可选实现手段**

### 为什么不是内核必需

当前 phase-1 首先要确定的是 canonical facts、latest state、readiness、service truth。

如果这些 truth 还没稳定，就不应把 Cube 当成“先给个 query layer 再说”的替代方案。

### 关键边界提醒

- Cube 不能取代 canonical fact truth
- Cube 不能定义 readiness truth
- Cube 可以服务 metrics / semantic query，但不能改写 C0-L3 的所有权边界

---

### 6.3 pgvector

### 放置位置

若采用，建议用于：

- explanation object 检索增强
- audit 文档 / variance 说明 / 运行手册的语义检索

### 为什么可选

它适合：

1. 解释材料需要语义检索
2. 审计材料和 runbook 需要辅助召回
3. 将来 operator-facing 解释对象需要更强检索

### 分类判断

- **phase-1 可选扩展**
- **可选实现手段**

### 为什么不是内核必需

phase-1 的 readiness / explanation 必须先有结构化 truth。

向量检索只能增强解释材料的查找，不应替代：

- readiness reason code
- structured explanation object
- service truth

---

## 7. Phase-2 / 后续增强 upstream

### 7.1 Debezium

### 放置位置

若未来 source 进入可 CDC 的数据库接入形态，可位于：

- future raw ingress / CDC capture layer

### 为什么延后

当前 phase-1 的第一 source 是 `Qinqin HTTP API`，不是数据库 CDC source。

因此 Debezium 与当前主链路不匹配。

### 分类判断

- **phase-2 / 后续增强**

### 关键边界提醒

即使未来引入 Debezium，它也只负责 change capture，不负责：

- latest state truth
- readiness truth
- service truth

---

### 7.2 Kafka / Redpanda

### 放置位置

若未来进入实时事件模式，可位于：

- future event bus
- CDC fan-out
- alert / downstream async distribution

### 为什么延后

当前 phase-1 以 batch-first 为主。

在 contract、raw replay、canonical facts、latest state、readiness 还未稳定时，引入事件总线只会提前扩大复杂度。

### 分类判断

- **phase-2 / 后续增强**

### 关键边界提醒

事件流不是 latest state truth 的替代物。

也就是说：

- topic 里的事件不等于 latest usable state
- consumer lag 不等于 readiness truth

---

### 7.3 TimescaleDB

### 放置位置

若未来时序分析复杂度显著提升，可位于：

- future temporal analytics adjunct

### 为什么延后

当前 phase-1 的主问题不是高阶时序压缩，而是：

- truth boundary 是否成立
- backfill / replay 是否成立
- latest state / readiness 是否成立

因此不应过早把 TimescaleDB 引入为主存储。

### 分类判断

- **phase-2 / 后续增强**

### 关键边界提醒

TimescaleDB 若采用，也应是 PostgreSQL phase-1 baseline 的增强，而不是绕过现有 truth boundary 另起一套主真相源。

---

## 8. 明确不属于 data-platform 内核的 upstream

### 8.1 OpenClaw

### 放置位置

OpenClaw 的正确位置是：

- 接入层
- permission kernel
- 会话与治理边界

### 为什么不应进入 data-platform 真相层

原因：

1. OpenClaw 拥有的是 access truth / session truth，不是 data truth
2. 若把 OpenClaw 混入 data-platform 内核，会把权限 / 会话语义带入 C0-L3 真相层
3. 数据中台只应消费受控 access context，不应承接 gateway / agent / session 运行时细节

### 明确结论

- OpenClaw 可以位于 Navly_v1 整体系统中
- 但 **不属于 data-platform phase-1 核心 upstream**
- 更 **不应进入 data-platform truth layer**

---

### 8.2 LangGraph

### 放置位置

LangGraph 的正确位置是：

- Copilot runtime
- 上层 execution shell
- agent/workflow orchestration

### 为什么不应进入 data-platform 真相层

原因：

1. LangGraph 解决的是交互编排，不是 data truth 建模
2. readiness truth 不应由 agent graph 推导并持有
3. canonical facts / latest state / service truth 必须是稳定数据对象，而不是某次 runtime graph 的副产物

### 明确结论

- LangGraph 可以在上层能力复杂后作为执行层工具引入
- 但 **不应进入 data-platform kernel**
- 更不能用 LangGraph 替代 `completeness/`、`projections/`、`serving/` 的 truth boundary

---

## 9. layer / 目录放置建议

| truth / 目录 | 推荐 upstream |
| --- | --- |
| C0 `contracts/` + `directory/` | 以 Git-tracked contract / registry 为主，必要时持久化于 PostgreSQL |
| L0 `ingestion/` + `raw-store/` | PostgreSQL + Temporal；`connectors/qinqin/` 为 source adapter |
| L1 `warehouse/` | PostgreSQL + dbt Core |
| L2 `sync-state/` + `quality/` + `completeness/` | PostgreSQL + dbt Core + 必要应用逻辑 |
| L3 `projections/` | PostgreSQL + dbt Core |
| 默认读边界 `serving/` | 先用内核自有 serving contract；Hasura / Cube 仅在需要时上接 |
| future realtime | Debezium + Kafka / Redpanda（后续） |
| future advanced analytics | TimescaleDB（后续） |
| permission / session | OpenClaw（内核外） |
| runtime orchestration | LangGraph（内核外） |

---

## 10. phase-1 推荐决策

当前建议明确采用：

1. PostgreSQL
2. dbt Core
3. Temporal

当前建议明确不默认采用：

1. Hasura
2. Cube
3. pgvector
4. Debezium
5. Kafka / Redpanda
6. TimescaleDB

当前建议明确排除出 data-platform 内核：

1. OpenClaw
2. LangGraph

---

## 11. 核心判断

Navly_v1 数据中台的 upstream 采用策略不应写成：

- “我们有什么开源组件，就都归到数据中台里”

而应写成：

- 先用最小核心集闭合 contract/raw/canonical/state/readiness/service 六类 truth
- 再按需要增加 serving、semantic、realtime、analytics 增强
- 并明确把 OpenClaw、LangGraph 这类内核外组件挡在 data-platform truth layer 之外

这才符合 Navly_v1 “数据中台是长期资产”的方向。
