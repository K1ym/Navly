# 2026-04-06 Navly_v1 Shared Contracts Interaction 方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `openclaw-host-bridge` 与 `thin runtime shell` 之间必须冻结的 interaction contracts，避免 bridge/runtime 各自发明一套边界对象

---

## 1. 文档目的

本文档回答：

> bridge 和 runtime 之间哪些对象必须进入 shared contracts，才能保证宿主交接、运行时执行和结果投递使用的是同一套语言？

---

## 2. 为什么 interaction contracts 必须独立说明

当前 phase-1 已经明确：

- bridge 负责宿主适配
- runtime 负责交互组织

但如果两者之间没有冻结的 interaction contracts，就会出现：

1. bridge 一套 handoff envelope
2. runtime 另一套 request envelope
3. bridge 一套 result envelope
4. runtime 另一套 outcome event

因此，interaction contracts 必须作为 shared contracts 的独立家族存在。

---

## 3. Phase-1 必须冻结的 interaction 对象

### 3.1 `runtime_request_envelope`

这是 bridge -> runtime 的正式交接对象。

说明：

- 它是跨模块公共对象
- 它是 bridge -> runtime 的统一 canonical 名称

推荐最小字段：

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 本次 runtime 请求标识 |
| `ingress_ref` | `string` | freeze | 对应宿主入口引用 |
| `trace_ref` | `string` | freeze | 顶层交互追踪引用 |
| `channel_kind` | `enum` | freeze | 来源渠道 |
| `message_mode` | `enum` | freeze | 私聊 / 群聊 / thread / command 等 |
| `user_input_text` | `string` | freeze | 规范化后的用户输入 |
| `structured_input_slots` | `object` | extend | 显式槽位，如日期、scope hint |
| `requested_capability_id` | `string` | extend | 若入口显式指定 capability |
| `requested_service_object_id` | `string` | extend | 若入口显式指定服务对象 |
| `target_scope_hint` | `string` | extend | 宿主侧 scope 提示，不代表授权结果 |
| `target_business_date_hint` | `date` | extend | 宿主侧业务日期提示 |
| `response_channel_capabilities` | `object` | freeze | 当前渠道可支持的响应能力 |
| `access_context_envelope` | `object` | freeze | 由 `auth-kernel` 签发的访问上下文 |
| `decision_ref` | `string` | freeze | 当前 handoff 的 canonical 决策引用；必须与 `access_context_envelope.decision_ref` 一致 |
| `delivery_hint` | `object` | extend | 给 bridge 的投递偏好提示 |

约束：

- bridge 只能组装和透传，不得把宿主私有字段升级为核心字段
- runtime 只能消费，不得重新定义其主字段语义
- `runtime_request_envelope` 是 bridge -> runtime 的唯一 canonical handoff object
- 顶层 `decision_ref` 的 canonical 语义是当前 handoff 绑定的 `access_context_envelope.decision_ref`，不再默认表示原始 `Gate 0 Result.decision_ref`
- 若 bridge 需要保留 `gate0_decision_ref`，只能放在 bridge local metadata、`authorized_session_link`、`delivery_hint` 等宿主适配上下文中
- runtime 在 `decision_ref` 缺失或与 `access_context_envelope.decision_ref` 失配时必须 fail closed

### 3.2 `runtime_result_envelope`

这是 runtime -> bridge 的正式返回对象。

其中 `result_status` 使用共享主枚举 `runtime_result_status`。

推荐最小字段：

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 对应请求 ID |
| `runtime_trace_ref` | `string` | freeze | runtime 执行追踪引用 |
| `result_status` | `runtime_result_status` | freeze | 运行时结果主状态 |
| `selected_capability_id` | `string` | freeze | 实际执行的 capability |
| `selected_service_object_id` | `string` | extend | 实际读取的服务对象 |
| `answer_fragments` | `object[]` | freeze | 渠道无关回答片段；每个 fragment 至少是结构化对象 |
| `explanation_fragments` | `object[]` | extend | fallback / explanation 片段；每个 fragment 至少是结构化对象 |
| `escalation_action` | `object` | extend | 升级动作建议 |
| `reason_codes` | `string[]` | freeze | 结构化原因代码 |
| `trace_refs` | `string[]` | freeze | access / readiness / service / run 追踪引用 |
| `delivery_hints` | `object` | extend | 供 bridge 渲染 / 投递时参考 |

约束：

- bridge 负责渠道渲染与投递
- bridge 不得改写 `result_status` 和 `reason_codes` 的主语义

### 3.3 `runtime_outcome_event`

这是 runtime -> governance / auth / ops 的正式 outcome 事件。

推荐最小字段：

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `event_id` | `string` | freeze | 事件标识 |
| `request_id` | `string` | freeze | 请求标识 |
| `trace_ref` | `string` | freeze | 顶层追踪引用 |
| `runtime_trace_ref` | `string` | freeze | runtime 内部追踪引用 |
| `decision_ref` | `string` | freeze | 对应授权决策引用 |
| `selected_capability_id` | `string` | freeze | 最终执行 capability |
| `selected_service_object_id` | `string` | extend | 最终服务对象 |
| `result_status` | `runtime_result_status` | freeze | 与 `runtime_result_envelope.result_status` 一致 |
| `reason_codes` | `string[]` | extend | 结果相关原因代码 |
| `occurred_at` | `datetime` | freeze | 发生时间 |

---

## 4. bridge 局部对象与共享对象的边界

以下对象当前仍可由 bridge 局部拥有，不必进入 shared contracts 主集：

- `host_ingress_envelope`
- `tool_publication_manifest`
- `host_dispatch_result`

原因：

- 它们主要服务于宿主适配内部
- 目前不是 data-platform / auth-kernel / runtime 的共同输入输出

但如果将来出现：

- 第二个桥接宿主
- 第二个运行时消费者
- 或 ops / verification 需要把这些对象当正式跨模块主语义消费

则应把它们提升到 `shared/contracts/interaction` 或 `shared/contracts/host-bridge`。

---

## 5. `runtime_result_status` 主集合

| 值 | 含义 |
| --- | --- |
| `answered` | 已成功组织出回答并可投递 |
| `fallback` | 未形成正式 answer，但形成了结构化 fallback |
| `escalated` | 进入升级路径，需更高权限或人工处理 |
| `rejected` | 因 access / contract / route 等前置条件不足而被拒绝继续 |
| `runtime_error` | runtime 自身发生错误 |

---

## 6. 核心结论

1. `runtime_request_envelope` 是 bridge -> runtime 的 canonical handoff object。
2. `runtime_result_envelope` 是 runtime -> bridge 的 canonical result object。
3. `runtime_outcome_event` 是 runtime 的跨模块治理事件。
4. `runtime_result_status` 必须作为 interaction family 的共享主枚举维护。
5. bridge -> runtime 的跨模块 canonical 名称统一为 `runtime_request_envelope`。
6. `runtime_request_envelope.decision_ref` 的 canonical 语义已经收口为 `access_context_envelope.decision_ref`。
7. `gate0_decision_ref` 继续留在 bridge local metadata，不进入 runtime handoff 顶层 canonical 字段。
