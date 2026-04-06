# 2026-04-06 Navly_v1 Shared Contracts Phase-1 冻结方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `phase-1` 必须先冻结的公共契约、字段、枚举、命名后缀语义与扩展治理规则

---

## 1. 文档目的

本文档回答：

1. `phase-1` 应先冻结哪些对象，为什么
2. 哪些字段必须冻结，哪些字段可扩展但不能进入核心契约
3. 哪些枚举必须只有一套主集合
4. 命名后缀语义应该冻结到什么程度，才能支持多模块并行开发

---

## 2. Phase-1 冻结原则

`phase-1` 的目标不是“一次冻结所有未来细节”，而是优先冻结 **多模块立即共用的主骨架**。

冻结优先级如下：

1. **先冻结对象身份**：`capability_id`、`*_ref`、`service_object_id`
2. **再冻结访问与调用 envelope**：`access_context_envelope`、`access_decision`、`*_query`、`*_response`
3. **再冻结主枚举**：`readiness_status`、`service_status`、`access_decision_status`、`readiness_reason_code`
4. **最后留出受治理扩展区**：`metadata` / `extensions`

核心原因：

- 如果对象身份不冻结，后续所有表、接口、日志、审计都会漂移
- 如果 request / response envelope 不冻结，多模块并行开发无法无缝集成
- 如果状态枚举不冻结，逻辑判断会立刻分叉
- 如果扩展区不治理，所有人都会把临时字段塞进去逃避 contract 评审

---

## 3. Phase-1 必须冻结的对象清单

### 3.1 capability family

`phase-1` 必须冻结：

- `capability_id`
- `capability_definition`
- `capability_scope_requirement`
- `capability_service_binding`

原因：

- 这是 `data-platform`、`auth-kernel`、`runtime`、`bridge` 四方对 capability 说同一套话的前提
- 如果 capability 标识与 scope/service 绑定不冻结，授权、readiness、service query 会全部错位

### 3.2 access family

`phase-1` 必须冻结：

- `actor_ref`
- `session_ref`
- `decision_ref`
- `scope_ref`
- `access_context_envelope`
- `access_decision`

原因：

- `data-platform` 只能消费 access truth，不能重做 access truth
- `runtime` / `bridge` 必须拿到同一份 `access_context_envelope`
- 如果 `decision_ref` 不冻结，审计与访问回溯无法闭环

### 3.3 readiness family

`phase-1` 必须冻结：

- `capability_readiness_query`
- `capability_readiness_response`
- `readiness_status`
- `blocking_dependency_ref` 的引用方式
- `readiness_reason_code`

原因：

- runtime 不能自行发明 readiness 语义
- `data-platform` 必须用统一 contract 回答“能不能答、为什么不能答”
- `blocking_dependency` 必须可追溯、可审计、可治理，而不是自由文本

### 3.4 service family

`phase-1` 必须冻结：

- `theme_service_query`
- `theme_service_response`
- `capability_explanation_object`
- `service_status`

原因：

- runtime / bridge 必须面对同一套服务查询语义
- explanation 只能是结构化对象，不能退化成自然语言拼接产物
- `service_status` 必须与 `readiness_status`、`access_decision_status` 保持边界分离

### 3.5 trace / audit family

`phase-1` 必须冻结：

- `trace_ref`
- `state_trace_ref`
- `run_trace_ref`
- `data_access_audit_event`

原因：

- 没有统一 trace，就没有可信审计
- 没有 `state_trace_ref` / `run_trace_ref`，readiness 和 service 只能给出“看起来像原因”的解释，不能回到状态真相与历史执行真相

### 3.6 interaction family

`phase-1` 必须冻结：

- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`
- `runtime_result_status`

原因：

- bridge 与 runtime 已经共享这组对象
- 如果它们不冻结，bridge/runtime 会各自实现一套 handoff / result / outcome 语义
- 这会直接破坏 phase-1 最小 vertical slice 的交接稳定性

---

## 4. 字段冻结矩阵

### 4.1 capability family

| 对象 | 必须冻结字段 | 可扩展但不能进入核心契约 | 明确不进入 shared-contracts 核心 |
| --- | --- | --- | --- |
| `capability_definition` | `capability_id`、`capability_kind`、`owner_module`、`contract_status` | `summary`、命名空间化 `extensions` | prompt 路由 hint、LLM 配置、内部实现类名 |
| `capability_scope_requirement` | `capability_id`、`scope_kind`、`requirement_level`、`selection_mode`、`is_default_scope_kind` | module extension | host UI 选店策略、临时对话猜测规则 |
| `capability_service_binding` | `capability_id`、`service_object_id`、`service_kind`、`is_default_binding`、`include_explanation_supported` | module extension | 物理表名、endpoint 名、SQL 名 |

### 4.2 access family

| 对象 | 必须冻结字段 | 可扩展但不能进入核心契约 | 明确不进入 shared-contracts 核心 |
| --- | --- | --- | --- |
| `actor_ref` / `session_ref` / `decision_ref` / `scope_ref` | 引用格式本身 | 无 | host session id、workspace id、自由文本 scope |
| `access_context_envelope` | `request_id`、`trace_ref`、`decision_ref`、`actor_ref`、`session_ref`、`conversation_ref`、`tenant_ref`、`primary_scope_ref`、`granted_scope_refs`、`granted_capability_ids`、`issued_at`、`expires_at` | `extensions.*` | role 名主判断、host 原始 payload、prompt note |
| `access_decision` | `decision_ref`、`request_id`、`trace_ref`、`decision_status`、`actor_ref`、`session_ref`、`target_capability_id`、`target_scope_ref`、`decided_at`、`expires_at` | `reason_codes`、`restriction_codes`、`obligation_codes` | 自然语言授权说明、私有 policy 脚本文本 |

### 4.3 readiness family

| 对象 | 必须冻结字段 | 可扩展但不能进入核心契约 | 明确不进入 shared-contracts 核心 |
| --- | --- | --- | --- |
| `capability_readiness_query` | `request_id`、`trace_ref`、`capability_id`、`access_context`、`target_scope_ref`、`target_business_date`、`freshness_mode` | `extensions.*` | runtime prompt、自然语言问题文本 |
| `capability_readiness_response` | `request_id`、`trace_ref`、`capability_id`、`readiness_status`、`evaluated_scope_ref`、`requested_business_date`、`latest_usable_business_date`、`reason_codes`、`blocking_dependencies`、`state_trace_refs`、`run_trace_refs`、`evaluated_at` | `extensions.*` | 内部 SQL、调度器临时状态、自由文本说明 |
| `blocking_dependency_ref` | `dependency_kind`、`dependency_ref`、`blocking_reason_code` | `state_trace_refs`、`run_trace_refs` | 物理表名、文件路径、脚本名 |

### 4.4 service / trace family

| 对象 | 必须冻结字段 | 可扩展但不能进入核心契约 | 明确不进入 shared-contracts 核心 |
| --- | --- | --- | --- |
| `theme_service_query` | `request_id`、`trace_ref`、`capability_id`、`service_object_id`、`access_context`、`target_scope_ref`、`target_business_date`、`include_explanation` | `extensions.*` | runtime prompt 参数、host ingress 特殊字段 |
| `theme_service_response` | `request_id`、`trace_ref`、`capability_id`、`service_object_id`、`service_status`、`service_object` 槽位、`data_window`、`explanation_object`、`state_trace_refs`、`run_trace_refs`、`served_at` | payload 内部 schema、`extensions.*` | 物理表列、原始接口分页内容 |
| `capability_explanation_object` | `capability_id`、`explanation_scope`、`reason_codes`、`state_trace_refs`、`run_trace_refs` | `summary_tokens`、`extensions.*` | 最终用户话术、prompt 拼装文本 |
| `data_access_audit_event` | `event_id`、`request_id`、`trace_ref`、`decision_ref`、`actor_ref`、`session_ref`、`capability_id`、`scope_ref`、`service_object_id`、`business_date`、`readiness_status`、`service_status`、`state_trace_refs`、`run_trace_refs`、`occurred_at` | `extensions.*` | secret、token、原始 HTTP body |

### 4.5 interaction family

| 对象 | 必须冻结字段 | 可扩展但不能进入核心契约 | 明确不进入 shared-contracts 核心 |
| --- | --- | --- | --- |
| `runtime_request_envelope` | `request_id`、`ingress_ref`、`trace_ref`、`channel_kind`、`message_mode`、`user_input_text`、`response_channel_capabilities`、`access_context_envelope`、`decision_ref` | `structured_input_slots`、`requested_capability_id`、`requested_service_object_id`、`target_scope_hint`、`target_business_date_hint`、`delivery_hint` | host 私有 session 结构、workspace 内部对象、prompt 原文 |
| `runtime_result_envelope` | `request_id`、`runtime_trace_ref`、`result_status`、`selected_capability_id`、`answer_fragments`、`reason_codes`、`trace_refs` | `selected_service_object_id`、`explanation_fragments`、`escalation_action`、`delivery_hints` | 渠道渲染细节、宿主 SDK 参数；`answer_fragments` / `explanation_fragments` 元素至少是结构化对象 |
| `runtime_outcome_event` | `event_id`、`request_id`、`trace_ref`、`runtime_trace_ref`、`decision_ref`、`selected_capability_id`、`result_status`、`occurred_at` | `selected_service_object_id`、`reason_codes`、`extensions.*` | 宿主 token、未治理调试文本 |

---

## 5. 哪些枚举必须只有一套主集合

`phase-1` 必须只有一套 master set 的枚举包括：

- `capability_kind`
- `scope_kind`
- `freshness_mode`
- `readiness_status`
- `service_status`
- `access_decision_status`
- `runtime_result_status`
- `readiness_reason_code`

原因：

- 这些枚举一旦分叉，任何一层的分支判断、审计和回放都会失真
- 特别是 `readiness_status` / `service_status` / `access_decision_status` 三者必须保持边界正交，不能互相替代

---

## 6. 必须冻结的命名后缀语义

`phase-1` 必须冻结以下命名语义：

| 后缀 | 固定语义 | 禁止行为 |
| --- | --- | --- |
| `*_id` | 对象自己的稳定标识 | 用作外部对象引用 |
| `*_ref` | 对其他对象的标准引用 | 塞入自然语言、display name、host id |
| `*_state` | 持续更新的当前状态真相 | 用来表达历史事件 |
| `*_snapshot` | 某时刻切面 | 当成可持续变化状态 |
| `*_event` | 已发生的一次事件 | 混入当前状态真相 |
| `*_query` | 请求 envelope | 塞入响应字段 |
| `*_response` | 响应 envelope | 当成内部状态对象 |

这是 `phase-1` 必须冻结的命名底座；否则即使字段名相同，也会因后缀语义漂移而无法长期复用。

---

## 7. 如何防止 metadata / extensions 变成黑箱

### 7.1 允许的扩展规则

- 扩展字段必须位于 `metadata` 或 `extensions`
- 扩展字段必须带 owner 命名空间
- 扩展字段不能替代已有核心字段
- 扩展字段不能定义新的 status / reason_code 主集合

### 7.2 触发晋升或清理的条件

满足任一条件时，扩展字段必须进入 shared-contracts 评审：

1. 第二个模块开始依赖它
2. 它被用作稳定分支逻辑
3. 它需要出现在审计、runbook、运维或复盘主链路中
4. 它需要进入文档对外说明

### 7.3 明确禁止

不允许把以下内容塞进扩展区并当成“以后再治理”：

- live secrets
- host token / cookie / signing material
- prompt 原文
- 未受控的自然语言 explanation
- 物理表名 / SQL / 调试文件路径

---

## 8. 核心结论

1. `phase-1` 先冻结对象身份、核心 envelope、主枚举、trace 规则。
2. 先冻结 capability / access / readiness / service / trace 这五组对象，是因为它们是多模块并行开发的共同语言底座。
3. payload 细节、host 细节、prompt 细节、实现细节都不应挤进 shared-contracts 核心。
4. `metadata` / `extensions` 可以存在，但必须是受治理的过渡区，而不是长期黑箱。
