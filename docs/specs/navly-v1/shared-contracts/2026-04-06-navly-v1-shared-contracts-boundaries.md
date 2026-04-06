# 2026-04-06 Navly_v1 Shared Contracts 模块边界方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 公共契约层的存在必要性、职责边界、模块关系、读写规则与治理原则

---

## 1. 文档目的

本文档回答四个问题：

1. 为什么 `shared-contracts` 必须存在，而不能由各模块各自维护一套
2. `shared-contracts` 到底负责什么，不负责什么
3. `data-platform`、`auth-kernel`、`openclaw-host-bridge`、`runtime` 分别可以读写哪些 shared contracts
4. 如何保证公共契约层不被 runtime、宿主细节、临时业务胶水或黑箱扩展污染

相关主文档：

- `../2026-04-06-navly-v1-design.md`
- `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
- `../2026-04-06-navly-v1-naming-conventions.md`
- `../2026-04-06-navly-v1-shared-contracts-layer.md`
- `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`

---

## 2. 为什么 shared-contracts 必须存在

`shared-contracts` 必须作为单独一层存在，而不能交给各模块“自己维护自己那份”，原因不是形式统一，而是系统可集成性。

### 2.1 如果没有 shared-contracts，会立即出现四类漂移

1. **capability 漂移**  
   `data-platform` 会定义一套 `capability_id`，`auth-kernel` 会维护另一套授权 capability，`runtime` 会再发明一套路由 key，最后看起来都像同一个能力，实际却无法稳定对齐。

2. **状态语义漂移**  
   `readiness_status`、`service_status`、`access_decision_status` 如果没有统一主集合，很快会出现 `pending / waiting / not_ready / blocked / denied` 混用，导致跨模块逻辑分叉。

3. **trace 漂移**  
   没有统一的 `trace_ref` / `state_trace_ref` / `run_trace_ref` 规则时，审计链路会被切断；`decision_ref`、数据状态引用、历史 run 引用将无法在一次交互内闭环。

4. **宿主与运行时污染**  
   如果 bridge 或 runtime 可以反向定义 contract，`host_session_id`、prompt 特例、LLM 临时字段会很快进入公共接口，污染长期稳定语义。

### 2.2 shared-contracts 的真正作用

`shared-contracts` 的作用不是“替各模块实现真相”，而是：

> 把多模块都必须说的一套话，先固定成一套稳定语言，再让各模块在这套语言之下各自实现自己的真相。

因此它是：

- 多模块并行开发的前提层
- 双内核集成的语言层
- trace / enum / naming 的主语义层

它不是：

- 第三个内核
- 业务模块
- data truth 或 access truth 的替代品

---

## 3. 公共契约层的职责边界

### 3.1 shared-contracts 负责的内容

`shared-contracts` 负责定义且只负责定义：

1. 跨模块共享对象的名称、最小字段骨架与后缀语义
2. `capability_id`、`*_ref`、`*_query`、`*_response`、`*_event` 的统一命名规则
3. `readiness_status`、`service_status`、`access_decision_status`、`readiness_reason_code` 等主枚举集合
4. `trace_ref` / `state_trace_ref` / `run_trace_ref` 的传播与引用规则
5. `metadata` / `extensions` 的治理边界

### 3.2 shared-contracts 不负责的内容

`shared-contracts` 不负责：

- `data-platform` 的 canonical facts、latest state、projection、theme payload 细节
- `auth-kernel` 的 actor normalization、binding ledger、policy 规则、最终 access truth
- `openclaw-host-bridge` 的宿主 session / workspace / gateway 接入细节
- `runtime` 的 LLM、prompt、orchestration、tool scheduling 细节
- 任何 private secrets、host token、签名参数、真实数据库物理名

### 3.3 一条总原则：共享语言与真相所有权必须分离

| 对象家族 | shared-contracts 的角色 | 真相所有模块 |
| --- | --- | --- |
| capability contracts | 定义 schema 与命名 | `data-platform` 或受治理的 capability owner |
| access contracts | 定义共享 envelope 与引用形态 | `auth-kernel` |
| readiness / service contracts | 定义跨模块消费接口 | `data-platform` |
| trace / enums | 定义统一语义与字典 | 由 `shared-contracts` 主持，具体事件分别由各 owner 模块发出 |

结论：

> `shared-contracts` 决定“这句话怎么说”；各模块决定“这件事是真是假”。

---

## 4. 与四个模块的关系

### 4.1 data-platform

`data-platform` 是 readiness / service / data lineage 的真相拥有者。

它必须：

- 发布自己拥有的 `capability_definition`
- 发布 `capability_scope_requirement`
- 发布 `capability_service_binding`
- 响应 `capability_readiness_query`
- 响应 `theme_service_query`
- 产出 `capability_explanation_object`
- 产出 `state_trace_ref`、`run_trace_ref`
- 产出 `data_access_audit_event`

它不得：

- 自己发明另一套 access object
- 用 role 名或 host session id 代替 `actor_ref` / `scope_ref`
- 用内部表名、source endpoint 名污染公共 contract 主语义

### 4.2 auth-kernel

`auth-kernel` 是 access truth 的拥有者。

它必须：

- 产出 `actor_ref`、`session_ref`、`decision_ref`、`scope_ref`
- 产出 `access_decision`
- 产出 `access_context_envelope`
- 消费 `capability_definition` 与 `capability_scope_requirement` 作为授权输入之一
- 消费 `data_access_audit_event` 做治理闭环

它不得：

- 改写 `readiness_status` / `service_status`
- 直接定义 data readiness reason
- 让宿主 session / workspace 成为正式 actor/session/scope 语义

### 4.3 openclaw-host-bridge

`openclaw-host-bridge` 是宿主适配层，不是真相层。

它可以：

- 读取 `capability_definition` 以暴露受保护 capability 入口
- 读取 `access_decision` / `access_context_envelope` 执行 Gate 0 或 capability 调用转发
- 透传或构造 `capability_readiness_query`、`theme_service_query`
- 读取 `capability_readiness_response`、`theme_service_response`

它不可以：

- 写入新的 `capability_id` 主集合
- 写入新的 `access_decision_status` 或 `service_status`
- 把 `host_session_ref`、`workspace_ref`、OpenClaw tool 名直接升级为 shared contracts 主语义

### 4.4 runtime

`runtime` 是交互组织层，不是真相定义层。

它可以：

- 读取 `capability_definition` 做 capability routing
- 读取 `access_context_envelope` / `access_decision`
- 发起 `capability_readiness_query`
- 发起 `theme_service_query`
- 读取 `capability_readiness_response`、`theme_service_response`、`capability_explanation_object`

它不可以：

- 自己定义 `readiness_status` / `service_status`
- 用 prompt rule 反向定义 capability contract
- 把 LLM memory、tool scratchpad、临时路由 hint 写进 shared-contracts 核心字段

---

## 5. 四模块读写矩阵

| 模块 | 可发布 / 写入的 shared contracts | 只读 / 消费的 shared contracts | 明确禁止 |
| --- | --- | --- | --- |
| `data-platform` | `capability_definition`、`capability_scope_requirement`、`capability_service_binding`、`capability_readiness_response`、`theme_service_response`、`capability_explanation_object`、`state_trace_ref`、`run_trace_ref`、`data_access_audit_event` | `access_context_envelope`、`access_decision`、`access_decision_status`、`scope_ref`、`trace_ref` | 写 access truth；发明私有 status / reason_code 主集合 |
| `auth-kernel` | `actor_ref`、`session_ref`、`decision_ref`、`scope_ref`、`access_decision`、`access_context_envelope` | `capability_definition`、`capability_scope_requirement`、`capability_service_binding`、`data_access_audit_event`、`trace_ref` | 定义 readiness / service truth；把 host 证据直接当正式 ref |
| `openclaw-host-bridge` | `capability_readiness_query`、`theme_service_query`（仅在其直接转发调用时） | `capability_definition`、`access_decision`、`access_context_envelope`、`capability_readiness_response`、`theme_service_response`、`trace_ref` | 写 capability 主集合；写主枚举；让 OpenClaw 术语成为共享主语义 |
| `runtime` | `capability_readiness_query`、`theme_service_query`；未来若存在受治理的 runtime capability，可按同一 schema 发布 `capability_definition` | `capability_definition`、`capability_scope_requirement`、`capability_service_binding`、`access_context_envelope`、`access_decision`、`capability_readiness_response`、`theme_service_response`、`capability_explanation_object`、`trace_ref` | 反向定义 contract；用 LLM/提示词结果替代内核真相 |

约束：

- **一个对象可以有多个消费者，但只能有一个真相 owner。**
- **bridge / runtime 可以构造 request envelope，但不能篡改 response 语义。**
- **shared-contracts 里的主枚举只能有一套 master set。**

---

## 6. 命名与命名空间边界

### 6.1 项目命名优先使用 Navly 主语义

如果需要给包、schema、registry、目录或生成物命名，应优先使用：

- `navly_shared_contracts`
- `navly_capability_registry`
- `navly_access_contracts`
- `navly_trace_catalog`

不应优先使用：

- `openclaw_capability_contracts`
- `qinqin_runtime_contracts`
- `wecom_data_response`

### 6.2 核心对象名保持通用语义

共享对象本身仍然使用稳定英文通用名：

- `capability_definition`
- `access_context_envelope`
- `capability_readiness_response`
- `theme_service_response`
- `data_access_audit_event`

原因：

- 这些对象要跨 `data-platform` / `auth-kernel` / `bridge` / `runtime` 长期复用
- 它们不应该被具体上游系统、宿主品牌或 LLM 运行时绑死

### 6.3 后缀语义必须只有一套解释

以下后缀在全系统内只能有一套主语义：

- `*_id`：对象自己的稳定标识
- `*_ref`：对其他对象的标准引用
- `*_state`：持续更新的当前状态真相
- `*_snapshot`：某时刻切面
- `*_event`：一次已发生事件
- `*_query`：请求 envelope
- `*_response`：响应 envelope

任何模块都不能把同一个后缀改成另一种意思。

---

## 7. 如何防止 metadata / extensions 变成逃避治理的黑箱

### 7.1 允许扩展，但不允许借扩展逃避主契约

`metadata` / `extensions` 在 shared contracts 中允许存在，但必须满足：

1. 不能承载本应进入核心字段的东西
2. 不能改变核心字段语义
3. 不能成为另一个模块的必需分支判断输入
4. 不能携带 live secrets、host token、prompt 文本、物理表名、临时 SQL

### 7.2 扩展字段必须命名空间化

推荐格式：

- `extensions.data_platform.*`
- `extensions.auth_kernel.*`
- `extensions.bridge.*`
- `extensions.runtime.*`

禁止：

- 无前缀的自由 key
- `metadata.foo = ...` 这种无法判断 owner 的字段

### 7.3 触发升级规则

当某个扩展字段满足以下任一条件时，必须被提升为正式 contract 或被删除：

1. 被第二个模块消费
2. 被用于稳定逻辑分支
3. 进入审计、运维或回放主链路
4. 在两个以上 capability / service 中重复出现

---

## 8. 核心结论

1. `shared-contracts` 必须独立存在，因为没有它，双内核与上层模块会迅速形成四套不同语言。
2. `shared-contracts` 只收口共享语言，不替代 `data-platform` 与 `auth-kernel` 的真相拥有权。
3. `phase-1` 必须先冻结 capability / access / readiness / service / trace / enums 主骨架，保证多模块并行开发不漂移。
4. `bridge` 与 `runtime` 是消费者和请求构造者，不是 contract 的真相定义者。
5. 扩展必须被治理、命名空间化、可升级，不能成为黑箱逃生舱。
