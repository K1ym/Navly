# 2026-04-06 Navly_v1 Shared Contracts 枚举与 Trace 方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 公共契约层中的主枚举集合、`reason_code` 语义边界、`trace_ref` / `state_trace_ref` / `run_trace_ref` 传播规则与 `data_access_audit_event` 审计要求

---

## 1. 文档目的

本文档重点解决两个问题：

1. `trace / reason_code / service_status / access_decision_status` 如何避免语义漂移
2. 共享主枚举与 trace 规则如何收口成单一主集合，而不是每个模块一套词汇

---

## 2. 主枚举总原则

### 2.1 必须只有一套 master set

以下枚举在 `phase-1` 必须只有一套主集合：

- `capability_kind`
- `scope_kind`
- `freshness_mode`
- `readiness_status`
- `service_status`
- `access_decision_status`
- `runtime_result_status`
- `readiness_reason_code`

任何模块都不得：

- 发明同义新值
- 用自然语言替代枚举值
- 在 `extensions` 里偷偷塞另一套状态字典

### 2.2 状态必须边界正交

三类状态的边界如下：

| 状态 | 回答的问题 | owner | 绝不能表达的内容 |
| --- | --- | --- | --- |
| `access_decision_status` | 这个 actor 在这个 capability / scope 上能不能继续往前走？ | `auth-kernel` | 数据有没有 ready、服务有没有返回 |
| `readiness_status` | 这个 capability 在当前 scope/date 上是否可答？ | `data-platform` | allow / deny / escalation |
| `service_status` | 已经进入服务查询后，本次服务调用结果如何？ | `data-platform` | access 决策结果 |

这就是避免语义漂移的第一条规则：

> 一个状态只回答一个问题，不跨域借位。

---

## 3. Phase-1 主枚举集合

### 3.1 `capability_kind`

| 值 | 含义 |
| --- | --- |
| `data_read` | 由 `data-platform` 提供的读型能力 |
| `runtime_action` | 由 `runtime` 所有、但仍需进入统一授权语义的动作能力 |

### 3.2 `scope_kind`

| 值 | 含义 |
| --- | --- |
| `tenant` | 顶层租户范围 |
| `org` | 组织范围 |
| `store` | 门店范围 |
| `hq` | 总部范围 |

### 3.3 `freshness_mode`

| 值 | 含义 |
| --- | --- |
| `latest_usable` | 取当前最新可用业务日期 |
| `strict_date` | 严格要求目标业务日期 |

### 3.4 `readiness_status`

| 值 | 含义 |
| --- | --- |
| `ready` | 数据与状态已满足能力可答条件 |
| `pending` | 尚未满足，但预计通过后续同步或状态发布可满足 |
| `failed` | 当前因错误、缺失或未治理问题导致不可答 |
| `unsupported_scope` | 当前 capability 不支持该 scope 类型或 scope 组合 |

语义约束：

- `readiness_status` 不表达 access allow / deny
- `pending` 不等于“上层先随便答一下”
- `unsupported_scope` 是 capability-scope 语义，不是权限语义

### 3.5 `service_status`

| 值 | 含义 |
| --- | --- |
| `served` | 服务对象成功返回 |
| `not_ready` | 由于 readiness 不满足，未返回服务对象 |
| `scope_mismatch` | 目标 scope 与当前服务对象或请求边界不一致 |
| `error` | 服务查询过程中发生错误 |

语义约束：

- `service_status` 只表达服务查询的结果
- access 问题必须在进入 service query 之前被拦截
- `denied`、`restricted` 这类值不得出现在 `service_status`

### 3.6 `access_decision_status`

| 值 | 含义 |
| --- | --- |
| `allow` | 允许继续执行 |
| `deny` | 明确拒绝 |
| `restricted` | 允许继续，但带有明确收窄或义务 |
| `escalation` | 需要人工或额外流程升级 |

语义约束：

- `access_decision_status` 只表达访问边界，不表达数据 readiness 或服务结果
- `not_ready`、`pending` 不得作为 access decision 状态使用

### 3.7 `runtime_result_status`

| 值 | 含义 |
| --- | --- |
| `answered` | 已形成正式 answer 并可投递 |
| `fallback` | 未形成正式 answer，但形成可投递 fallback |
| `escalated` | 进入升级路径 |
| `rejected` | 因 access / contract / route 前置不足而被拒绝继续 |
| `runtime_error` | runtime 自身错误 |

语义约束：

- `runtime_result_status` 只表达 runtime 的交互执行结果
- `answered` 不等于 `served`，因为 runtime 可能在多个 service / explanation 结果上组织答案
- `rejected` 不等于 `deny`，因为 access `deny` 只是 runtime 被拒绝的一个来源

---

## 4. `readiness_reason_code` 主集合

`readiness_reason_code` 在 `phase-1` 只表达 **数据 readiness / service readiness 相关原因**，不表达 access 拒绝原因。

| 代码 | 含义 | 常见对应状态 |
| --- | --- | --- |
| `source_window_not_ready` | 数据源业务窗口尚未成熟 | `pending` |
| `upstream_sync_in_progress` | 上游同步正在进行 | `pending` |
| `required_dataset_missing` | 必需数据集尚未具备 | `failed` |
| `required_field_not_governed` | 必需字段尚未进入治理范围 | `failed` |
| `projection_not_available` | 目标服务 / projection 尚未产出 | `failed` |
| `latest_state_not_published` | 最新可用状态尚未发布 | `pending` |
| `schema_variance_unresolved` | 文档 / live 行为差异尚未消化 | `failed` |
| `capability_scope_not_supported` | 当前 capability 不支持请求 scope | `unsupported_scope` |
| `upstream_error` | 上游采集或处理链路出现错误 | `failed` |
| `internal_state_error` | 状态解析、状态发布或服务装配出现内部错误 | `failed` |

规则：

- `readiness_reason_code` 不用于 access 决策
- `readiness_reason_code` 不能被自由文本替代
- 若未来新增 reason code，必须在 shared-contracts 主集合中评审，而不能先在某模块私自上线

---

## 5. Trace 规则

### 5.1 `trace_ref`、`state_trace_ref`、`run_trace_ref` 的分工

| 引用 | 回答的问题 | 创建方 | 是否可多值 |
| --- | --- | --- | --- |
| `trace_ref` | 这一次跨模块交互链路是谁？ | ingress owner（通常由 bridge / runtime 入口生成） | 单值 |
| `state_trace_ref` | 当前 readiness / service 结论依赖了哪个状态真相？ | `data-platform` | 可多值 |
| `run_trace_ref` | 当前结论可回指到哪些历史执行 run？ | `data-platform` | 可多值 |

### 5.2 传播规则

1. 一次用户交互进入系统后，应尽快生成一个顶层 `trace_ref`
2. `auth-kernel`、`runtime`、`data-platform` 跨模块调用时必须原样透传该 `trace_ref`
3. `data-platform` 在 readiness / service response 中附加 `state_trace_ref` 与 `run_trace_ref`
4. `decision_ref` 不是 `trace_ref` 的替代品；两者必须并存
5. 同一次交互可产生多个 `decision_ref`、多个 `run_trace_ref`，但顶层 `trace_ref` 应保持稳定

### 5.3 命名与格式规则

推荐格式：

- `trace_ref = navly:trace:<trace_id>`
- `state_trace_ref = navly:state-trace:<state_type>:<state_id>`
- `run_trace_ref = navly:run-trace:<run_type>:<run_id>`

规则：

- 不允许把日志文件路径、SQL id、OpenTelemetry span id 直接冒充 shared-contracts 主 trace
- 具体 tracing 技术可以变化，但 shared-contracts 暴露给跨模块的引用语义必须稳定

---

## 6. `data_access_audit_event` 的审计要求

`data_access_audit_event` 是把 access truth、interaction trace、data trace 接起来的关键事件。

### 6.1 最小审计闭环

一条合格的 `data_access_audit_event` 至少要能把以下对象串起来：

- 谁访问：`actor_ref`
- 在哪个授权下访问：`decision_ref`
- 访问哪个能力：`capability_id`
- 命中哪个范围：`scope_ref`
- 本次交互是哪条链路：`trace_ref`
- 用到哪个状态真相：`state_trace_refs`
- 可回到哪些历史执行：`run_trace_refs`
- 最终服务结果如何：`service_status`

### 6.2 明确禁止

`data_access_audit_event` 不得直接包含：

- live secrets
- prompt 原文
- 原始 host cookie / token
- 物理表名或 SQL 文本
- 未治理的自然语言 reason 文本

---

## 7. 如何避免 trace / reason_code / status 语义漂移

### 7.1 单一主词表

所有 shared enums 和 `readiness_reason_code` 必须只维护一份主文档和一份 schema 源。

### 7.2 一条值只表达一层语义

- `allow` 永远只表示 access 允许
- `ready` 永远只表示 readiness 就绪
- `served` 永远只表示 service 返回成功
- `source_window_not_ready` 永远只表示数据窗口问题

### 7.3 不允许“状态借位”

禁止写法：

- 用 `service_status = denied` 表达权限拒绝
- 用 `access_decision_status = pending` 表达数据未就绪
- 用 `readiness_reason_code = access_denied` 混入访问原因

### 7.4 扩展区不得定义新主集合

`extensions` 中不允许出现：

- `extensions.runtime_status = waiting_for_tool`
- `extensions.bridge_reason = host_not_bound`
- `extensions.data_platform_reason = partial_ready`

这类字段如果需要跨模块消费，必须回到主集合评审。

---

## 8. 核心结论

1. `trace_ref`、`state_trace_ref`、`run_trace_ref` 分别对应交互链路、状态真相、历史执行真相，三者不能互相替代。
2. `readiness_status`、`service_status`、`access_decision_status` 必须保持边界正交，避免状态借位。
3. `readiness_reason_code` 只表达数据 readiness 原因，不表达 access 原因。
4. 审计闭环依赖 `decision_ref + trace_ref + state_trace_refs + run_trace_refs` 同时存在。
5. 任何新增 status / reason_code / trace 公开语义，都必须先回到 shared-contracts 主集合治理，而不是在模块私有扩展中先行分叉。
