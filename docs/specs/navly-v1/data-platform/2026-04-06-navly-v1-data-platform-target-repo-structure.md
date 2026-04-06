# 2026-04-06 Navly_v1 数据中台目标目录骨架说明

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `platforms/data-platform/` 的目标目录骨架、目录职责、C0/L0/L1/L2/L3 写入边界、长期资产判断与默认读取边界

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 的数据中台在代码仓库里应该长成什么样，哪些目录负责哪一类真相，哪些目录属于长期资产，哪些只是实现手段？

本文档是结构边界文档，不锁死具体物理表名或具体框架文件名。

---

## 2. 结构设计原则

### 2.1 目录结构必须服从真相边界

`platforms/data-platform/` 的目录骨架应服务于以下 6 类真相，而不是服务于某个临时运行时：

1. contract truth
2. raw truth
3. canonical fact truth
4. latest state truth
5. readiness truth
6. theme / service truth

### 2.2 C0 与 L0-L3 必须在目录上可辨认

- `C0`：契约与治理控制层
- `L0`：原始执行与原始回放层
- `L1`：标准事实层
- `L2`：状态 / 质量 / readiness 层
- `L3`：theme / service 层

### 2.3 Copilot / runtime 默认只读服务边界

数据中台内部的物理实现目录，不应成为 Copilot 或 runtime 的默认直读路径。

默认规则：

- **只允许 `serving/` 成为默认消费边界**
- 其他目录只允许被数据中台内部模块、治理工具、审计工具或迁移流程访问

### 2.4 OpenClaw / LangGraph / Copilot runtime 不进入内核目录

`platforms/data-platform/` 只负责：

- data truth
- state truth
- readiness truth
- service truth

它不应承载：

- 权限 / 会话绑定内核
- agent orchestration
- prompt glue
- 上层问答运行时

---

## 3. 目标目录骨架

建议目标骨架如下：

```text
platforms/
  data-platform/
    README.md
    docs/
    contracts/
    directory/
    connectors/
      qinqin/
    ingestion/
    raw-store/
    warehouse/
    sync-state/
    quality/
    completeness/
    projections/
    serving/
    workflows/
    migration/
    scripts/
    tests/
```

说明：

- 本骨架是 **职责级骨架**，不是必须一次性把每个目录都做满的物理实现承诺。
- 其中 `connectors/qinqin/` 是当前 phase-1 的首个 source adapter；后续多 source 时可继续增加同级目录。

---

## 4. 目录分组

### 4.1 C0 契约与治理控制组

- `contracts/`
- `directory/`

### 4.2 Source 执行与 L0 组

- `connectors/qinqin/`
- `ingestion/`
- `raw-store/`
- `workflows/`

### 4.3 L1-L3 真相组

- `warehouse/`
- `sync-state/`
- `quality/`
- `completeness/`
- `projections/`
- `serving/`

### 4.4 迁移与支持组

- `migration/`
- `scripts/`
- `tests/`
- `docs/`

---

## 5. 各目录职责

### 5.1 `contracts/`

职责：

- 定义数据中台内部统一 contract shape
- 定义 source / endpoint / field / dataset / capability 的 schema、enum、interface
- 定义 **数据中台侧** 的 readiness / service / dataset contract
- 定义 data-platform owner 的 canonical object schema，但跨模块 shared contract 仍服从 `shared/contracts`

边界说明：

- 跨模块共享的 `access_context_envelope`、`access_decision`、`capability_readiness_query/response`、`theme_service_query/response`、`trace_ref` 等主 contract，应由 `shared/contracts` 定义
- `platforms/data-platform/contracts/` 只负责 **data-platform 内部 contract** 与 **data-platform owner 对象** 的 schema
- `platforms/data-platform/contracts/` 可以实现、扩展、适配 shared contracts，但不拥有 shared contracts 的主定义权

它回答的是：

> “允许有哪些受治理对象，以及这些对象长什么样？”

### 5.2 `directory/`

职责：

- 存放当前已纳入系统的具体 registry 实例
- 包括：source registry、endpoint registry、field catalog、field landing policy、capability registry、dependency registry、variance register

它回答的是：

> “当前版本实际纳管了哪些对象？”

### 5.3 `connectors/qinqin/`

职责：

- 封装 `Qinqin v1.1` 的 source adapter
- 实现签名、分页、时间窗、header 差异、response envelope 解析、source 错误归类
- 严格读取 `contracts/` 与 `directory/`，不自行发明 endpoint / field / scope 规则

它回答的是：

> “如何按照 C0 规定的 contract 去接入当前 source？”

### 5.4 `ingestion/`

职责：

- 组织每日同步、补数、重跑、分页执行
- 管理 run plan / endpoint plan / page execution
- 产出历史执行真相的主体记录

它回答的是：

> “什么时候、以什么计划、对哪个 source / store / date 执行了一次采集？”

### 5.5 `raw-store/`

职责：

- 保存 raw request / raw response / raw page payload
- 保存 replay handle 与原始 trace 索引
- 为 L0 提供统一原始回放读取能力

它回答的是：

> “原始 source 到底返回了什么，如何精确回放？”

### 5.6 `warehouse/`

职责：

- 从 L0 提取并沉淀 canonical facts
- 完成维表、事实表、业务键、幂等归一、跨页归并
- 使 `endpoint-manifest.md` 中的结构化目标有统一 landing

它回答的是：

> “哪些标准业务事实已经成立？”

### 5.7 `sync-state/`

职责：

- 表达 latest usable state
- 表达 dataset availability、backfill progress、source window coverage
- 保证历史 run truth 与 latest state truth 分离

它回答的是：

> “当前哪天的数据可用，最新可用状态是什么？”

### 5.8 `quality/`

职责：

- 表达 field coverage、schema alignment、quality issue
- 记录字段纳管、结构对齐、质量缺口
- 为 latest state 与 readiness 提供质量解释输入

它回答的是：

> “当前数据虽然落了，但是否足够可信、是否和 contract 对齐？”

### 5.9 `completeness/`

职责：

- 维护 capability dependency registry 的执行侧逻辑
- 计算 readiness truth
- 输出 reason code、blocking dependency、recheck hint

它回答的是：

> “某个 capability 现在能不能答，为什么能答或不能答？”

### 5.10 `projections/`

职责：

- 构建 theme snapshot 与 service truth
- 将 L1/L2 收敛为稳定 theme object / service object
- 保持 theme/service 可追溯到 L1/L2/L0

它回答的是：

> “当前应该向消费方提供什么主题对象 / 服务对象？”

### 5.11 `serving/`

职责：

- 暴露数据中台的默认读边界
- 封装 readiness query、theme service query、explanation query
- 对 Copilot 或其他消费者提供稳定 API / SDK / query boundary

它回答的是：

> “上层应该如何受控地读取数据中台，而不穿透内部物理实现？”

### 5.12 `workflows/`

职责：

- 放置工作流定义、调度流程、任务编排、重试策略的实现
- 驱动 `ingestion/`、`warehouse/`、`sync-state/`、`quality/`、`completeness/`、`projections/` 的执行顺序

它回答的是：

> “系统如何可靠地调度这些模块？”

它**不**拥有任何数据真相。

### 5.13 `migration/`

职责：

- 承接 legacy 表、legacy 状态、legacy projection 的一次性迁移与清理
- 做 schema / state / data backfill 的迁移脚本与核对逻辑

它是过渡目录，不是长期默认运行路径。

### 5.14 `scripts/`

职责：

- 放置开发辅助、诊断、批量修复、生成器等工具脚本
- 只能作为辅助手段，不能成为事实真相的默认生产路径

### 5.15 `tests/`

职责：

- 放置 contract test、connector test、replay test、canonicalization test、state test、readiness test、serving test
- 保证 C0-L3 的边界可回归验证

### 5.16 `docs/`

职责：

- 存放 package-local 设计说明、runbook、目录内说明
- 不替代 `docs/specs/` 下的正式规格入口

---

## 6. 长期资产 / 实现手段判断

### 6.1 主分类表

| 目录 | 主分类 | 原因 |
| --- | --- | --- |
| `contracts/` | 长期资产 | contract truth 的形状定义是长期边界 |
| `directory/` | 长期资产 | 当前纳管对象与政策目录是 C0 真相的一部分 |
| `connectors/qinqin/` | 实现手段 | 是 source-specific adapter，不是系统最终真相本体 |
| `ingestion/` | 混合，但以实现手段为主 | run semantics 重要，但调度与执行代码可替换 |
| `raw-store/` | 长期资产 | raw truth 与 replayability 是中台长期资产 |
| `warehouse/` | 长期资产 | canonical fact truth 是长期资产 |
| `sync-state/` | 长期资产 | latest state truth 是长期资产 |
| `quality/` | 长期资产 | 质量与字段治理结果是长期资产 |
| `completeness/` | 长期资产 | readiness truth 是长期资产 |
| `projections/` | 长期资产 | theme / service truth 是长期资产 |
| `serving/` | 长期资产（接口层面） | 默认消费边界必须长期稳定 |
| `workflows/` | 实现手段 | 编排器可替换，不应被误当成真相源 |
| `migration/` | 过渡性目录 | 服务于迁移，不是长期内核组成 |
| `scripts/` | 实现手段 | 只能辅助，不能拥有真相 |
| `tests/` | 质量保障资产 | 长期必要，但不拥有业务真相 |
| `docs/` | 文档资产 | 说明边界，但不参与运行时真相写入 |

### 6.2 一个重要补充

`ingestion/` 和 `serving/` 都有“目录是实现手段，但其对外语义是长期边界”的特点。

因此判断时要区分：

- **语义是否长期保留**
- **当前目录中的实现是否可替换**

---

## 7. C0 / L0-L3 读写矩阵

### 7.1 steady-state 读写矩阵

| 目录 | 读 `contracts/` / `directory/` | 写 C0 | 写 L0 | 写 L1 | 写 L2 | 写 L3 |
| --- | --- | --- | --- | --- | --- | --- |
| `contracts/` | - | 是 | 否 | 否 | 否 | 否 |
| `directory/` | 是 | 是 | 否 | 否 | 否 | 否 |
| `connectors/qinqin/` | 是 | 否 | 否 | 否 | 否 | 否 |
| `ingestion/` | 是 | 否 | 是（执行真相） | 否 | 否 | 否 |
| `raw-store/` | 是 | 否 | 是（raw truth） | 否 | 否 | 否 |
| `warehouse/` | 是 | 否 | 否 | 是 | 否 | 否 |
| `sync-state/` | 是 | 否 | 否 | 否 | 是（latest state） | 否 |
| `quality/` | 是 | 否 | 否 | 否 | 是（quality truth） | 否 |
| `completeness/` | 是 | 否 | 否 | 否 | 是（readiness truth） | 否 |
| `projections/` | 是 | 否 | 否 | 否 | 否 | 是 |
| `serving/` | 是 | 否 | 否 | 否 | 否 | 否（默认只读暴露） |
| `workflows/` | 是 | 否 | 否（不直接拥有） | 否 | 否 | 否 |
| `migration/` | 是 | 条件性一次性写入 | 条件性一次性写入 | 条件性一次性写入 | 条件性一次性写入 | 条件性一次性写入 |
| `scripts/` | 条件性 | 否 | 否 | 否 | 否 | 否 |
| `tests/` | 是 | 否 | 否 | 否 | 否 | 否 |

### 7.2 关键解释

- `connectors/qinqin/` 不直接拥有任何 truth layer；它的责任是 **按 C0 规则调用 source**。
- `ingestion/` 与 `raw-store/` 共同构成 L0，但职责不同：
  - `ingestion/` 拥有执行过程真相
  - `raw-store/` 拥有原始 payload / replay 真相
- `serving/` 只暴露受控读边界，不应发明新的业务真相层。
- `migration/` 只允许在受控的一次性迁移场景下写真相层，不能成为 steady-state writer。

---

## 8. 哪些目录读 contracts

### 8.1 必须读 C0 的目录

以下目录必须显式读取 `contracts/` 与 `directory/`：

- `connectors/qinqin/`
- `ingestion/`
- `raw-store/`
- `warehouse/`
- `sync-state/`
- `quality/`
- `completeness/`
- `projections/`
- `serving/`
- `workflows/`
- `tests/`
- `migration/`

### 8.2 为什么必须这样做

这样做的目的不是形式统一，而是防止：

- connector 写死 endpoint / field 规则
- state 层自己发明 dataset 或 scope 语义
- readiness 层自己写一套 capability dependency
- service 层自己拼装未登记字段

---

## 9. Copilot / runtime 默认读取边界

### 9.1 默认允许直读的目录

只有：

- `serving/`

### 9.2 明确禁止默认直读的目录

Copilot / runtime 默认**绝不能**直读：

- `contracts/`
- `directory/`
- `connectors/qinqin/`
- `ingestion/`
- `raw-store/`
- `warehouse/`
- `sync-state/`
- `quality/`
- `completeness/`
- `projections/`
- `workflows/`
- `migration/`
- `scripts/`
- `tests/`

### 9.3 为什么 `projections/` 也不能默认直读

因为 `projections/` 是 L3 的**内部构建目录**，不是对外稳定边界。

对外稳定边界应由 `serving/` 统一完成，以便：

- 限制物理实现泄漏
- 限制上层绕过 readiness / explanation contract
- 让 service truth 与 transport shape 分离

---

## 10. 目录与模块映射

| 目录 | 主要模块归属 |
| --- | --- |
| `contracts/` | M1 数据契约与接口接入 |
| `directory/` | M1 数据契约与接口接入 |
| `connectors/qinqin/` | M2 数据采集与原始回放 |
| `ingestion/` | M2 数据采集与原始回放 |
| `raw-store/` | M2 数据采集与原始回放 |
| `warehouse/` | M3 标准事实与状态治理 |
| `sync-state/` | M3 标准事实与状态治理 |
| `quality/` | M3 标准事实与状态治理 |
| `completeness/` | M4 可答性与主题服务（readiness 部分） |
| `projections/` | M4 可答性与主题服务（theme/service 部分） |
| `serving/` | M4 可答性与主题服务（默认读边界） |
| `workflows/` | 模块外编排支撑 |
| `migration/` | 迁移支撑 |
| `scripts/` | 开发 / 运维辅助 |
| `tests/` | 全模块验证 |

---

## 11. 推荐落地顺序

在真正创建 `platforms/data-platform/` 目录时，推荐按以下顺序建立：

1. `contracts/`
2. `directory/`
3. `connectors/qinqin/`
4. `ingestion/`
5. `raw-store/`
6. `warehouse/`
7. `sync-state/`
8. `quality/`
9. `completeness/`
10. `projections/`
11. `serving/`
12. `workflows/`
13. `migration/`
14. `scripts/`
15. `tests/`

原因：

- 先固定 C0
- 再闭合 L0
- 再沉淀 L1/L2
- 最后再暴露 L3 和读边界

---

## 12. 核心判断

`platforms/data-platform/` 的正确骨架不是：

- 一个混杂 connector、ETL、SQL、Copilot query glue 的大目录

而是：

- `contracts/` + `directory/` 固定 C0
- `ingestion/` + `raw-store/` 闭合 L0
- `warehouse/` 闭合 L1
- `sync-state/` + `quality/` + `completeness/` 闭合 L2
- `projections/` + `serving/` 闭合 L3 与默认读边界

只有这种骨架，数据中台才会成为 Navly 的长期资产，而不是下一轮重构时又要整体推倒的过渡实现。
