# 2026-04-06 Navly_v1 thin runtime shell 模块边界方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `thin runtime shell` 的职责边界、4 个核心模块、request lifecycle 主链路，以及与 `auth-kernel`、`data-platform`、`openclaw-host-bridge` 的责任分工

---

## 1. 文档目的

本文档回答一个问题：

> `Navly_v1` 为什么在 phase-1 就必须有 `thin runtime shell`，以及这层到底拥有什么、不拥有什么、内部应如何模块化拆分，才能既闭合最小执行链路，又不把双内核真相重新塞回 runtime？

本文档只讨论 `runtime` 本身，不讨论 `data-platform` 和 `auth-kernel` 的内部实现。

---

## 2. 为什么 phase-1 就必须有 thin runtime shell

### 2.1 phase-1 仍然需要一层“交互执行边界”

即使当前阶段不做 rich orchestration，系统仍然必须回答：

1. bridge 交来的请求要在哪里进入 Navly 的产品执行面
2. 当前交互应走哪个 `capability_id`
3. 什么顺序调用 `auth-kernel` 与 `data-platform`
4. `ready / pending / failed / unsupported_scope` 时如何统一组织 answer / fallback / escalation

如果没有这层，以上问题就会被迫落到：

- `openclaw-host-bridge`
- `data-platform`
- `auth-kernel`
- 或零散 prompt glue

这四种都不符合 Navly_v1 的边界设计。

### 2.2 runtime 不能等 rich orchestration 再出现

`runtime` 不能等 rich orchestration 的原因不是“以后迟早要做”，而是：

> **phase-1 现在就需要一层薄而正确的执行壳，来保护双内核不被上层交互逻辑污染。**

若等待 rich orchestration 再引入 runtime，当前阶段最容易发生的退化是：

1. `bridge` 直接硬编码 capability route 与 fallback
2. `data-platform` 被迫输出用户话术而不是服务对象
3. `auth-kernel` 被迫携带“问答流程里怎么继续”的逻辑
4. 旧 query glue / prompt glue 再次在宿主层或上层脚本中蔓延

因此 phase-1 需要的不是“复杂 runtime”，而是：

- 明确存在的 runtime 边界
- 最小可复用的 capability route
- 受保护的 readiness / service 调用顺序
- 可解释的 answer / fallback / escalation 组织

### 2.3 thin runtime shell 的定位

`thin runtime shell` 的定位不是“最终的智能编排层”，而是：

> **双内核之上的最小执行壳。**

它负责组织一次交互，但不负责定义：

- 数据真相
- 权限真相
- prompt 真相
- 多代理工作流真相

---

## 3. runtime 的总边界原则

### 3.1 runtime 拥有“交互组织真相”，不拥有“内核真相”

`runtime` 拥有的是：

1. 一次请求如何流转
2. 一次交互当前选中了什么 capability route
3. 当前应该请求哪个 `service_object_id`
4. 当前回答是 answer、fallback 还是 escalation
5. runtime 自身短生命周期的 trace / outcome

`runtime` 不拥有的是：

1. `actor / role / scope / conversation` 真相
2. `allow / deny / restricted / escalation` 的最终权限判定真相
3. canonical facts、latest state、readiness、theme service 真相
4. source endpoint、raw payload、physical tables 的理解权

### 3.2 runtime 必须 capability-first、service-object-first

`runtime` 只能围绕以下主语工作：

- `capability_id`
- `service_object_id`
- `access_context_envelope`
- `capability_readiness_response`
- `theme_service_response`
- `capability_explanation_object`

它不应围绕以下主语工作：

- `GetConsumeBillList`
- 某张事实表名
- 某段 SQL
- 某段 prompt 内嵌业务分支

### 3.3 runtime 必须 fail closed

如果缺少以下任一项，runtime 必须停止继续，而不是猜测：

- 有效 `access_context_envelope`
- capability 级 `access_decision`
- 已解析 `capability_id`
- `readiness` 的结构化结果

### 3.4 runtime 的表达层只能消费结构化解释，不应创造业务真相

对于 `pending / failed / unsupported_scope / deny / escalation`：

- `runtime` 可以组织最终用户表达
- 但不能自己发明“缺什么数据”“为何无权限”“该查哪张表”

解释来源应来自：

- `auth-kernel` 的 `reason_codes` / `restriction_codes` / `obligation_codes`
- `data-platform` 的 `readiness_reason_code` / `capability_explanation_object`

### 3.5 rich orchestration 只能后置挂载，不能反向定义 thin shell

后续如果引入：

- LLM planner
- LangGraph
- multi-agent flow
- skills runtime

它们只能挂载在 `thin runtime shell` 之上，并继续服从同一套：

- capability route contract
- access decision contract
- readiness / service contract
- answer / fallback / escalation contract

rich orchestration 不能绕过 thin shell 直接读 raw truth、直接做权限猜测、直接把 prompt 变成业务路由中心。

---

## 4. runtime 的四个核心模块总览

```text
openclaw-host-bridge
  -> M1 runtime ingress / interaction context
  -> M2 capability routing / execution planning
  -> M3 guarded dependency orchestration
  -> M4 answer / fallback / escalation / outcome
  -> openclaw-host-bridge

M3
  -> auth-kernel
  -> data-platform
```

| 模块 | 拥有的运行时真相 | 主要输入 | 主要输出 | 直接下游 | phase-1 优先级 |
| --- | --- | --- | --- | --- | --- |
| M1 runtime ingress / interaction context | 一次请求的入口上下文真相（短生命周期） | `runtime_request_envelope`、`access_context_envelope`、bridge trace | `runtime_interaction_context`、`runtime_trace_ref`、validated request | M2、M3、M4 | P0 |
| M2 capability routing / execution planning | capability route 与执行计划真相（短生命周期） | `runtime_interaction_context`、`capability_definition`、route registry | `capability_route_result`、`runtime_execution_plan`、route fallback plan | M3、M4 | P0 |
| M3 guarded dependency orchestration | 受保护调用顺序与依赖结果真相（短生命周期） | `runtime_execution_plan`、`access_context_envelope`、auth/data shared contracts | `access_guard_result`、`capability_readiness_response`、`theme_service_response`、dependency outcome | M4 | P0 |
| M4 answer / fallback / escalation / outcome | 回答组织、解释路径、升级路径、runtime outcome 真相 | M1/M2/M3 输出、shared explanation / reason codes | `runtime_result_envelope`、`runtime_outcome_event`、bridge delivery payload | bridge、auth-kernel、ops | P0 |

结论：

> 对 `Navly_v1` phase-1 来说，这四个模块都是 P0；区别只在每个模块内部哪些子能力先做、哪些 rich 特性后做。

---

## 5. M1 runtime ingress / interaction context

### 5.1 模块职责

M1 负责把 bridge 交来的规范化请求，收口成 runtime 可以执行的交互上下文。

它至少负责：

1. 校验 `runtime_request_envelope` 是否完整
2. 校验是否携带可用 `access_context_envelope` / `decision_ref`
3. 形成 `runtime_interaction_context`
4. 分配 `runtime_trace_ref`
5. 明确记录请求是否来自显式 capability 调用、文本消息还是受控菜单动作

### 5.2 输入

- `runtime_request_envelope`
- `access_context_envelope`
- bridge 透传的 channel / ingress / response capability 元数据
- 显式 `requested_capability_id` 或 route hint（若有）

### 5.3 输出

推荐最小输出对象：

- `runtime_interaction_context`
- `runtime_trace_ref`
- `validated_runtime_request`
- `runtime_input_classification`

### 5.4 对下游的约束

- M2 只能消费已校验的请求上下文
- M3 不能在缺少 `access_context_envelope` 时继续调用下游
- M4 必须能回引到 `runtime_trace_ref`

### 5.5 明确不负责的事

M1 不负责：

- actor 归一化
- Gate 0 决策
- 数据 readiness 计算
- 最终回答表达

### 5.6 phase-1 优先级

**P0，必须先闭合。**

若没有 M1，`runtime` 入口会退化成：

- 直接吃宿主原始 session
- 在没有 access truth 时继续执行
- 让后续模块边校验边猜请求结构

---

## 6. M2 capability routing / execution planning

### 6.1 模块职责

M2 负责把一次交互组织成 capability-first 的执行计划。

它至少负责：

1. 依据显式 `capability_id` 或 route registry 选择 capability
2. 依据 `capability_service_binding` 选择默认 `service_object_id`
3. 从输入中提取 `target_scope_hint`、`target_business_date_hint`、`freshness_mode`
4. 形成 `runtime_execution_plan`
5. 在 route 无法解析时输出 runtime 自身 fallback，而不是盲目查数

### 6.2 capability routing 的核心原则

`runtime` 必须围绕：

- `capability_id`
- `service_object_id`
- `capability_scope_requirement`
- `capability_service_binding`

来组织执行，而不是围绕：

- source endpoint 名
- 物理表名
- 某个 prompt 里的业务关键词分支

### 6.3 输入

- `runtime_interaction_context`
- `capability_definition`
- `capability_service_binding`
- runtime 自身的 `capability_route_registry`
- 可选 `requested_capability_id` / `requested_service_object_id`

### 6.4 输出

推荐最小输出对象：

- `capability_route_result`
- `runtime_execution_plan`
- `runtime_route_fallback`
- `requested_scope_selector`

### 6.5 对下游的约束

- M3 只按 `runtime_execution_plan` 调用双内核
- M4 只消费 capability / service / explanation 结果，不反推 source endpoint

### 6.6 明确不负责的事

M2 不负责：

- 直接读 raw truth 或 canonical facts
- 决定权限是否允许
- 生成最终自然语言话术
- 维护“看起来能工作”的 prompt glue 业务分支

### 6.7 phase-1 优先级

**P0，必须先闭合。**

若没有 M2，系统会退化成：

- bridge 内写 capability 逻辑
- prompt 内写 endpoint 逻辑
- 数据平台被直接按 SQL / 表名调用

---

## 7. M3 guarded dependency orchestration

### 7.1 模块职责

M3 负责按受保护顺序调用 `auth-kernel` 与 `data-platform`。

它至少负责：

1. 在执行 capability 前向 `auth-kernel` 发起 capability access request
2. 在 access allow / restricted 后向 `data-platform` 发起 readiness query
3. 在 readiness `ready` 时发起 theme service query
4. 在 readiness 非 `ready` 时读取 explanation object 或 reason codes
5. 区分 dependency-owned failure 与 runtime-owned error

### 7.2 输入

- `runtime_execution_plan`
- `access_context_envelope`
- `decision_ref`
- `capability_readiness_query` / `theme_service_query` shared contracts

### 7.3 输出

推荐最小输出对象：

- `access_guard_result`
- `capability_readiness_response`
- `theme_service_response`
- `runtime_dependency_outcome`
- `capability_explanation_object`

### 7.4 对下游的约束

- M4 不允许把 auth/data 的错误归因为 runtime truth
- bridge 不允许绕过 M3 直接调 data-platform 作为默认交互路径

### 7.5 明确不负责的事

M3 不负责：

- 重新做 role / scope / capability 决策
- 重新做 readiness resolver
- 自行拼装 service object
- 直接读取 raw page 或 canonical table

### 7.6 phase-1 优先级

**P0，必须闭合。**

没有 M3，就没有真正的“受保护执行壳”，只会剩下多个模块之间各自乱连。

---

## 8. M4 answer / fallback / escalation / outcome

### 8.1 模块职责

M4 负责把结构化结果组织成最终可交付给 bridge 的运行时输出。

它至少负责：

1. `ready` 时组织 answer
2. `pending / failed / unsupported_scope` 时组织 explanation / fallback
3. `deny / escalation / restricted` 时组织权限侧拒答或升级表达
4. 区分 runtime 自身错误与依赖模块错误
5. 输出 `runtime_result_envelope`
6. 回传 `runtime_outcome_event`

### 8.2 输入

- `capability_route_result`
- `access_decision`
- `capability_readiness_response`
- `theme_service_response`
- `capability_explanation_object`
- `reason_codes` / `restriction_codes` / `trace_refs`

### 8.3 输出

推荐最小输出对象：

- `runtime_result_envelope`
- `runtime_outcome_event`
- `bridge_delivery_hints`
- `runtime_error_view`

### 8.4 对下游的约束

- bridge 负责最终渠道渲染，不改写主语义
- auth/data 的 reason codes 必须原样保留在结构化输出中

### 8.5 明确不负责的事

M4 不负责：

- 重新推断 capability
- 直接访问业务数据
- 替双内核编造 reason code
- 在公开文档或输出中泄露 secrets

### 8.6 phase-1 优先级

**P0，必须闭合。**

没有 M4，系统就会重新退化成每个调用点自己拼回答、自己拼拒答、自己写一套 fallback。

---

## 9. request lifecycle 的最小主链路

```text
bridge
  -> runtime_request_envelope + access_context_envelope
  -> M1 validate + interaction context
  -> M2 capability route + execution plan
  -> M3 capability access request to auth-kernel
  -> M3 readiness query to data-platform
  -> M3 theme service query to data-platform (if ready)
  -> M4 answer / fallback / escalation
  -> runtime_result_envelope
  -> bridge delivery
```

核心要求：

1. bridge 负责交付，不负责 capability route 真相
2. runtime 负责组织，不负责访问真相或数据真相
3. `auth-kernel` 负责 access truth
4. `data-platform` 负责 readiness truth 与 service truth

---

## 10. runtime 和 bridge / data-platform / auth-kernel 的边界

### 10.1 runtime 和 bridge 的边界

`bridge` 负责：

- 渠道接入
- 宿主会话承载
- 入口标准化
- Gate 0 之前后的宿主侧拦截与转发
- 最终渠道响应投递

`runtime` 负责：

- capability route
- capability 级受保护调用组织
- readiness / service 调用顺序
- answer / fallback / escalation 组织

一句话：

> bridge 负责“把请求送进来、把结果送出去”；runtime 负责“把一次交互组织完”。

### 10.2 runtime 和 data-platform 的边界

`data-platform` 负责：

- readiness truth
- latest usable state
- service object
- explanation object

`runtime` 负责：

- 先查 readiness
- 再查 service
- 把结构化结果组织成交互输出

`runtime` 不得：

- 直接理解 source endpoint
- 直接理解 physical tables
- 直接绕过 readiness 去查 service 以外对象

### 10.3 runtime 和 auth-kernel 的边界

`auth-kernel` 负责：

- `actor / role / scope / conversation`
- `Gate 0`
- `access_decision`
- `access_context_envelope`

`runtime` 负责：

- 消费 access truth
- 请求 capability 级 access decision
- 按决策结果组织下一步

`runtime` 不得：

- 重新判断 actor 是谁
- 重新推断 scope
- 用 prompt 或代码分支重做权限决策

---

## 11. 如何防止 thin runtime 再次长成旧式 query glue / prompt glue 层

必须同时成立以下 6 条：

1. **capability-first**：所有路由都先落到 `capability_id`，不落到 endpoint 或 SQL。
2. **service-object-first**：上层默认读取 `service_object_id`，不拼事实表。
3. **registry-first**：route 规则来自 `capability_definition`、`capability_service_binding`、`capability_route_registry`，不来自 prompt 散文。
4. **structured explanation first**：缺口解释来自 reason code / explanation object，不来自运行时瞎编。
5. **fail closed**：没有 access truth、没有 readiness truth、没有 capability route 时直接停，不走“差不多就答”。
6. **rich orchestration must plug in, not take over**：后续 rich runtime 只能调用 thin shell 的稳定接口，不能绕过双内核边界。

---

## 12. phase-1 最小 vertical slice 应如何通过 runtime 闭合

phase-1 推荐最小闭环：

```text
WeCom / OpenClaw
  -> openclaw-host-bridge
  -> auth-kernel Gate 0
  -> thin runtime shell
  -> capability access decision
  -> capability_readiness_query
  -> theme_service_query
  -> answer / fallback / escalation
  -> bridge delivery
```

最小闭环至少应覆盖：

1. 一个 `store` 粒度的受支持 capability
2. `ready / pending / failed / unsupported_scope` 四种 readiness 路径
3. `allow / deny / restricted / escalation` 四种 access 路径中的至少核心子集
4. runtime 输出的统一 `runtime_result_envelope`

只要这条链路成立，后续 richer orchestration 就有了正确挂载位；如果这条链路不成立，rich orchestration 只会建立在错误边界之上。
