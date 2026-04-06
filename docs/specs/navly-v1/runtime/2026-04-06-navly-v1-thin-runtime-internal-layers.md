# 2026-04-06 Navly_v1 thin runtime shell 内部分层方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `thin runtime shell` 的内部分层、对象流转、越层禁止规则，以及 rich orchestration 的后置挂载方式

---

## 1. 文档目的

本文档回答：

> `thin runtime shell` 内部应该如何分层，才能既足够薄、足够清晰，又能为后续 richer runtime 留出扩展位，而不重新变成“所有东西都堆在一个问答路由器里”的旧式层？

---

## 2. 分层总原则

### 2.1 runtime 只保存短生命周期状态，不保存长期真相

`runtime` 内部的对象都是一次交互的短生命周期对象，例如：

- `runtime_interaction_context`
- `capability_route_result`
- `runtime_execution_plan`
- `runtime_result_envelope`

它不应保存长期真相对象，例如：

- `access policy`
- `binding truth`
- `latest_sync_state`
- `canonical facts`

### 2.2 层与层之间只通过命名稳定的对象传递

建议在 runtime 内部固定以下对象流：

```text
runtime_request_envelope
  -> runtime_interaction_context
  -> capability_route_result
  -> runtime_execution_plan
  -> dependency results
  -> runtime_result_envelope
```

这样做的目的不是“多定义几个名字”，而是防止：

- 上层直接篡改 access truth
- route 层直接跳过 readiness
- answer 层反过来发起业务查询

### 2.3 rich orchestration 只能作为扩展层，不是 phase-1 内核层

phase-1 的 runtime 内核只需要：

- 确定 capability route
- 执行 guard
- 调 data-platform
- 组织 answer / fallback / escalation

richer orchestration 以后可以存在，但必须插在明确的扩展位上，而不是从 day-1 进入主干。

---

## 3. 推荐分层总览

```text
L0 ingress contract layer
  -> L1 interaction context layer
  -> L2 capability route layer
  -> L3 guarded execution layer
  -> L4 answer assembly / outcome layer

E1 rich orchestration extension plane (post-phase-1 only)
  -> 挂在 L2/L3 之上，但不得绕过 L3/L4 contract
```

| 层 | 作用 | 主要输入 | 主要输出 | phase-1 必须性 |
| --- | --- | --- | --- | --- |
| L0 ingress contract layer | 接受并校验 bridge -> runtime 输入 contract | `runtime_request_envelope`、`access_context_envelope` | validated request、contract errors | P0 |
| L1 interaction context layer | 形成一次交互的运行时上下文 | validated request | `runtime_interaction_context`、`runtime_trace_ref` | P0 |
| L2 capability route layer | 解析 capability / service route 并生成执行计划 | interaction context、capability contracts | `capability_route_result`、`runtime_execution_plan` | P0 |
| L3 guarded execution layer | 执行 capability access、readiness、service 调用 | execution plan、access context | access/readiness/service results | P0 |
| L4 answer assembly / outcome layer | 组织 answer / fallback / escalation 并输出结果 | route + dependency results | `runtime_result_envelope`、`runtime_outcome_event` | P0 |
| E1 rich orchestration extension plane | richer planner / agent / skill 等增强能力 | L1/L2 上下文 | richer plan / substeps | 延后 |

---

## 4. L0 ingress contract layer

### 4.1 层职责

L0 是 `runtime` 的 contract 守门层。

它负责：

1. 接收 `runtime_request_envelope`
2. 校验 `access_context_envelope` / `decision_ref` 是否存在且未失配
3. 校验请求是否满足 runtime phase-1 支持的输入模式
4. 形成结构化 contract error，而不是让后续层在半残请求上继续工作

### 4.2 允许依赖

- shared contracts 的 `access/`、`capability/`、`interaction/trace` 定义
- runtime 自身的输入校验器

### 4.3 禁止依赖

- `auth-kernel` 内部绑定表
- `data-platform` 任何查询接口
- rich orchestration planner

### 4.4 产出对象

- `validated_runtime_request`
- `runtime_contract_error`
- `request_validation_snapshot`

---

## 5. L1 interaction context layer

### 5.1 层职责

L1 负责把“一个有效请求”变成“一次 runtime 交互上下文”。

它负责：

1. 分配 `runtime_trace_ref`
2. 固化本次交互的 `request_id`、`conversation_ref`、`session_ref`
3. 固化显式 capability hint、scope hint、business date hint
4. 形成 `runtime_interaction_context`

### 5.2 关键边界

L1 可以保存：

- 当前输入文本
- 当前显式 capability hint
- 当前期望业务日期 hint
- 当前响应通道能力

L1 不可以保存为真相：

- “这个人应该就是店长”
- “默认店铺大概是某门店”
- “既然上次查过这个指标，这次也沿用”

这些都必须经过 `auth-kernel` 或更上游受控输入，而不是在 runtime 里沉淀成隐式真相。

### 5.3 产出对象

- `runtime_interaction_context`
- `runtime_trace_ref`
- `interaction_input_snapshot`

---

## 6. L2 capability route layer

### 6.1 层职责

L2 是 thin runtime 的核心：

- 它把输入组织成 `capability_id`
- 它把 capability 组织成默认 `service_object_id`
- 它把 route 组织成受保护执行计划

### 6.2 route 的输入来源顺序

phase-1 推荐固定以下优先级：

1. **显式 `requested_capability_id`**：来自桥接菜单、工具入口、结构化命令
2. **受控 `capability_route_registry`**：基于明确规则将文本输入映射到 capability
3. **runtime fallback**：当 route 无法安全解析时，走解释 / 澄清 / 升级，不查数

当前 phase-1 不推荐将自由 LLM 推断作为默认 route 主机制。

### 6.3 route 层必须消费的共享对象

- `capability_definition`
- `capability_scope_requirement`
- `capability_service_binding`
- `capability_id`
- `service_object_id`

### 6.4 route 层明确禁止

- 直接选择 source endpoint
- 直接选择物理表
- 让 prompt 文本直接定义 capability 规则
- 将 store / org / tenant 的默认推断写死在 route 代码里

### 6.5 产出对象

- `capability_route_result`
- `runtime_execution_plan`
- `route_resolution_reason`
- `route_fallback_plan`

---

## 7. L3 guarded execution layer

### 7.1 层职责

L3 把 `runtime_execution_plan` 转成真实的受保护调用链。

它执行固定顺序：

1. capability access request -> `auth-kernel`
2. `capability_readiness_query` -> `data-platform`
3. `theme_service_query` -> `data-platform`（仅 readiness 为 `ready`）
4. explanation fetch / reason code consume（readiness 非 `ready`）

### 7.2 关键边界

L3 可以做：

- 调用顺序控制
- timeout / retry policy（基础级）
- dependency outcome 分类

L3 不可以做：

- 用 role 名或 host session 重新做权限判断
- 用 raw truth 重新做 readiness 判断
- 自己拼 service object

### 7.3 产出对象

- `access_guard_result`
- `capability_readiness_response`
- `theme_service_response`
- `capability_explanation_object`
- `runtime_dependency_outcome`

---

## 8. L4 answer assembly / outcome layer

### 8.1 层职责

L4 负责把 L2/L3 的结构化结果组织成 runtime 最终输出。

它负责：

1. `ready` 时把 service object 组织成 answer fragments
2. `pending / failed / unsupported_scope` 时把 explanation object 组织成 fallback
3. `deny / escalation / restricted` 时把 access reason 组织成拒答或升级说明
4. 形成 `runtime_result_envelope`
5. 发送 `runtime_outcome_event`

### 8.2 关键边界

L4 只应做：

- 结构化片段拼装
- 文案模板选择
- 交互下一步建议

L4 不应做：

- 再次查询 data-platform
- 再次查询 auth-kernel
- 在自然语言模板中偷偷塞入业务路由规则

### 8.3 产出对象

- `runtime_result_envelope`
- `runtime_outcome_event`
- `answer_fragment_set`
- `fallback_fragment_set`
- `escalation_fragment_set`

---

## 9. E1 rich orchestration extension plane（后置）

### 9.1 这一层为什么必须后置

richer runtime 的价值是真实存在的，但它应建立在 thin shell 已稳定之后。

否则很容易发生：

- planner 直接决定权限
- agent 直接读数据库
- prompt 直接替代 capability registry
- tool flow 直接绕过 readiness

### 9.2 后续允许挂载的能力

后续可以挂载：

- richer intent planner
- multi-capability orchestration
- multi-step clarification
- skill runtime
- agent graph

但必须满足：

1. 最终仍落到 `capability_id`
2. 最终仍走 capability access request
3. 最终仍先走 readiness，再走 service
4. 最终仍返回 `runtime_result_envelope`

### 9.3 明确禁止的 bypass

richer orchestration 禁止：

- 直接调用 source endpoint
- 直接调用 canonical facts 表
- 直接读取 `auth-kernel` 内部表
- 直接把 prompt 变成权限或数据真相源

---

## 10. 模块到层的映射

| 模块 | 主要落层 |
| --- | --- |
| M1 runtime ingress / interaction context | L0 + L1 |
| M2 capability routing / execution planning | L2 |
| M3 guarded dependency orchestration | L3 |
| M4 answer / fallback / escalation / outcome | L4 |
| richer orchestration（后续） | E1 |

---

## 11. phase-1 必须冻结的最小对象流

phase-1 建议至少冻结以下对象流：

- `runtime_request_envelope`
- `runtime_interaction_context`
- `capability_route_result`
- `runtime_execution_plan`
- `access_guard_result`
- `capability_readiness_response`
- `theme_service_response`
- `runtime_result_envelope`
- `runtime_outcome_event`

其中：

- 跨模块对象应进入 `shared/contracts`
- runtime 内部对象可留在 `runtime` 模块内部

这样可以保证 future rich runtime 扩展时，仍然插在稳定骨架上，而不是重新发明一条新链路。
