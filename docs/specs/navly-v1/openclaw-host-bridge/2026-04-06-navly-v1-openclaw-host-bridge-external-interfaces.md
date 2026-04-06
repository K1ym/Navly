# 2026-04-06 Navly_v1 OpenClaw 宿主桥接层外部接口方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `openclaw-host-bridge` 与 `OpenClaw host`、`auth-kernel`、`runtime`、`data-platform` 的正式接口边界、输入输出对象与责任矩阵

---

## 1. 文档目的

本文档回答：

> `openclaw-host-bridge` 对外应该暴露什么、不应该暴露什么；`OpenClaw host`、`auth-kernel`、`runtime`、`data-platform` 分别向 bridge 提供什么，又从 bridge 拿走什么？

---

## 2. 总体边界原则

### 2.1 OpenClaw host 负责承载，bridge 负责归一，auth-kernel 负责访问，runtime 负责组织，data-platform 负责数据真相

- `OpenClaw host` 拥有：gateway、channel ingress、host session / workspace、tool runtime、outbound delivery
- `openclaw-host-bridge` 拥有：host ingress normalize、auth bridge、tool publication、runtime handoff、host trace
- `auth-kernel` 拥有：actor、role、scope、conversation、Gate 0、access decision
- `runtime` 拥有：capability route、交互组织、answer / fallback / escalation 组织
- `data-platform` 拥有：canonical facts、latest state、readiness、theme service

### 2.2 bridge 默认主链路是 host -> bridge -> auth-kernel -> runtime -> data-platform -> bridge -> host

正确默认链路不是：

- host 直接碰 `auth-kernel`
- bridge 直接碰 data raw / facts
- host tool 直接碰 SQL / internal table

### 2.3 bridge 必须 fail closed

当以下任何对象缺失时，bridge 必须拒绝继续：

- 有效 `Gate 0 Result`
- 有效 `decision_ref`
- 有效 `session_ref` / `conversation_ref`
- runtime 所需的最小 `access_context_envelope`

### 2.4 OpenClaw tool 面只能看见 capability-oriented surface

宿主默认可以看到的是：

- `capability_id`
- `service_object_id`
- 受控 scope / date / mode 输入
- 结构化 explanation / trace refs

宿主默认不应看到的是：

- source endpoint 名
- raw SQL
- internal table 名
- raw secret

---

## 3. 五方责任矩阵

| 问题 | OpenClaw host | openclaw-host-bridge | auth-kernel | runtime | data-platform |
| --- | --- | --- | --- | --- | --- |
| 收到消息 / hook / session 事件 | 负责 | 归一化 | 不负责 | 不负责 | 不负责 |
| 当前 actor 是谁 | 提供证据 | 不负责最终判定 | 负责 | 只消费 | 只消费 |
| 当前 session / conversation 是否已授权 | 提供 host refs | 负责挂回授权链接 | 负责签发 | 只消费 | 只消费 |
| 入口能否进入 runtime | 不负责 | 执行拦截 | 负责（Gate 0） | 不负责 | 不负责 |
| 哪些 capability 暴露成 host tools | 提供 tool 承载 | 负责 publication | 只提供 access requirements | 只提供 owner / route metadata | 只提供 capability metadata |
| capability 如何执行 | 不负责 | handoff 与结果适配 | 负责 access decision | 负责组织执行 | 负责数据与可答真相 |
| reply 如何发回宿主 | 提供 send / chat / session update 能力 | 负责 dispatch | 不负责 | 返回结构化结果 | 不负责 |
| trace / audit 如何回链 | 提供宿主 receipt / run ids | 负责链接与回传 | 负责 access audit | 回传 runtime outcome | 回传 data access trace |

---

## 4. 共享标识、透传对象与归一对象

### 4.1 跨模块共享标识

推荐至少统一以下字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 一次入口或一次 tool / runtime 调用请求标识 |
| `ingress_ref` | 本次宿主入口引用 |
| `host_trace_ref` | 宿主 trace 引用 |
| `actor_ref` | canonical actor 引用 |
| `session_ref` | `auth-kernel` 签发的授权 session 引用 |
| `conversation_ref` | `auth-kernel` 确认的 conversation binding 引用 |
| `decision_ref` | Gate 0 或 capability decision 引用 |
| `capability_id` | 能力唯一标识 |
| `service_object_id` | 默认服务对象标识 |
| `trace_ref` / `state_trace_ref` / `run_trace_ref` | 跨层追溯引用 |

### 4.2 可以从宿主透传的对象

以下对象可以作为 **宿主证据或宿主承载引用** 透传：

- `channel_kind`
- `channel_account_ref`
- `peer_identity_evidence`
- `host_session_ref`
- `host_workspace_ref`
- `host_conversation_ref`
- `host_message_ref`
- `thread_ref`
- `host_tool_call_ref`
- `host_run_ref`
- `host_delivery_context`
- `delivery_receipt_ref`

### 4.3 必须在 Navly 内部重新归一的对象

以下对象必须由 Navly 内部模块重新归一，不能直接沿用宿主值：

- `actor_ref`
- `scope_ref`
- `session_ref`
- `conversation_ref`
- `decision_ref`
- `capability_id`（若宿主传的是 alias / tool name）
- `service_object_id`
- `readiness_status`
- `reason_code`

### 4.4 必须直接禁止的对象

以下对象不得作为默认宿主接口的一部分：

- `source_endpoint_name`
- `raw_sql_text`
- `internal_table_name`
- raw credential / token / secret
- role 名称驱动的业务过滤条件

---

## 5. bridge 读哪些 contracts，写哪些 contracts

| contract / object | bridge 读 / 写 | 方向 | 说明 |
| --- | --- | --- | --- |
| `capability_definition` | 读 | shared -> bridge | 发布 capability tools |
| `capability_scope_requirement` | 读 | shared -> bridge | 形成 tool 输入约束 |
| `capability_service_binding` | 读 | shared -> bridge | 绑定 runtime / service object |
| `Ingress Identity Envelope` | 写 | bridge -> auth-kernel | 提交入口证据 |
| `Gate 0 Result` | 读 | auth-kernel -> bridge | 入口授权结果 |
| `Access Context Envelope` | 读 / 透传 | auth-kernel -> bridge -> runtime | runtime 调用上下文 |
| `runtime_request_envelope` | 写 | bridge -> runtime | 授权后的运行时 handoff |
| `runtime_result_envelope` | 读 | runtime -> bridge | 结构化回复 / fallback / escalation |
| `host_dispatch_result` | 写 | bridge -> host / ops | 宿主回写结果 |
| `host_trace_event` | 写 | bridge -> host / ops | 宿主 trace |
| `data_access_audit_event` / `runtime_outcome_event` / `auth_outcome_event` | 写 / 转发 | runtime / data / bridge -> governance | 审计闭环 |

说明：

- `runtime_request_envelope`、`runtime_result_envelope`、`runtime_outcome_event` 应在实现前冻结到 `shared/contracts/interaction/`
- bridge 不拥有这些共享对象的真相语义，只负责正确读写和透传

---

## 6. OpenClaw host <-> openclaw-host-bridge

### 6.1 OpenClaw host -> bridge：Host Ingress Envelope

OpenClaw host 在入口边界应向 bridge 提供 **Host Ingress Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次入口请求 ID |
| `ingress_ref` | 宿主入口引用 |
| `host_event_kind` | `chat_message` / `hook_event` / `session_resume` / `tool_call` |
| `channel_kind` | 如 `wecom` |
| `channel_account_ref` | 宿主账户引用 |
| `peer_identity_evidence` | sender / peer / account identity evidence |
| `host_session_ref` | OpenClaw session key / session ref |
| `host_workspace_ref` | OpenClaw workspace ref |
| `host_conversation_ref` | 宿主 thread / group / conversation ref |
| `host_message_ref` | 宿主消息引用 |
| `message_text` | 文本消息 |
| `attachment_refs` | 附件引用 |
| `host_delivery_context` | 默认回复路径、目标、thread 等 |
| `received_at` | 接收时间 |
| `host_trace_ref` | 宿主 trace 引用 |

说明：

- 这是宿主证据，不是授权结论
- `host_event_kind` 应覆盖 gateway message、external hook、session resume、tool callback 等主入口

### 6.2 OpenClaw host -> bridge：Host Hook Trigger

OpenClaw host 的 hook 能力在 phase-1 应只用于 bounded lifecycle / external trigger。

推荐范围：

- `gateway:startup`
- `agent:bootstrap`
- external `/hooks` trigger
- session / command lifecycle trigger

bridge 处理原则：

- 可以用来 warmup、注册、同步、唤醒
- 不得把它们发展为业务工作流主链路

### 6.3 bridge -> OpenClaw host：Tool Publication Manifest

bridge 应向 OpenClaw host 发布 **Tool Publication Manifest**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `tool_name` | 宿主 tool 名 |
| `capability_id` | 对应 capability |
| `service_object_id` | 默认输出对象 |
| `input_schema_ref` | 输入 schema 引用 |
| `visibility_scope` | `host_visible` / `runtime_only` / `operator_only` |
| `tool_description` | host 可见说明 |
| `owner_module` | capability owner，如 `runtime` / `data-platform` |
| `publication_version` | 发布版本 |

### 6.4 bridge -> OpenClaw host：Reply Dispatch Contract

bridge 把 runtime 结果发回宿主时，应通过 **Reply Dispatch Contract** 适配。

推荐字段：

- `request_id`
- `host_session_ref`
- `host_delivery_context`
- `reply_blocks`
- `dispatch_mode`
- `idempotency_key`
- `host_trace_ref`

### 6.5 明确禁止的耦合

OpenClaw host 与 bridge 之间禁止：

1. 让宿主直接生成 `actor_ref` / `session_ref` / `conversation_ref`
2. 让宿主 tool 直接暴露 data source endpoint / SQL / internal table
3. 让宿主 hook 直接写业务判断结果而不经过 `auth-kernel` / `runtime`
4. 让宿主 reply dispatch 反向定义 runtime 组织逻辑

---

## 7. openclaw-host-bridge <-> auth-kernel

### 7.1 bridge -> auth-kernel：Ingress Identity Envelope

bridge 应按 `auth-kernel` 已定义的 `Ingress Identity Envelope` 提交入口证据。

推荐字段见 `auth-kernel` 外部接口文档，bridge 重点负责：

- 正确填充 `peer_identity_evidence`
- 正确透传 `host_session_ref` / `host_workspace_ref` / `host_conversation_ref`
- 不提前做 actor / scope / capability 结论

### 7.2 auth-kernel -> bridge：Gate 0 Result

bridge 应接收 `Gate 0 Result` 并严格执行：

- `allow`：可 handoff 给 runtime
- `restricted`：附 restriction / obligation 继续 handoff
- `deny`：宿主边界直接拦截
- `escalation`：停在授权边界，触发升级流

### 7.3 bridge -> auth-kernel：Conversation Binding Update

当桥接层观测到以下事件时，应回调 `Conversation Binding Update`：

- 新 thread / 新 group context
- session resume
- scope select / scope shrink
- operator handoff / escalation resolution

### 7.4 bridge -> auth-kernel：Host Outcome Event

bridge 在以下时机应回传 host 侧 outcome：

- dispatch 成功 / 失败
- deny / escalation 已向宿主提示
- host tool 调用完成
- host session 恢复失败或过期

### 7.5 边界结论

bridge 与 `auth-kernel` 的边界是：

> bridge 提供宿主证据与宿主 enforce；`auth-kernel` 提供访问真相与正式引用。

---

## 8. openclaw-host-bridge <-> runtime

### 8.1 bridge -> runtime：Authorized Runtime Handoff Envelope

bridge 应向 runtime 提供 **Authorized Runtime Handoff Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次运行时请求 ID |
| `ingress_ref` | 宿主入口引用 |
| `decision_ref` | Gate 0 决策引用 |
| `actor_ref` | 当前 actor |
| `session_ref` | 授权 session |
| `conversation_ref` | 授权 conversation |
| `access_context` | 标准访问上下文 |
| `message_payload` | 用户消息与必要上下文 |
| `attachment_refs` | 附件引用 |
| `host_session_ref` | 宿主 session 引用 |
| `host_delivery_context` | 默认返回路径 |
| `host_trace_ref` | 宿主 trace 引用 |

### 8.2 runtime -> bridge：Runtime Result Envelope

runtime 应向 bridge 返回 **Runtime Result Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 对应运行时请求 ID |
| `runtime_trace_ref` | runtime 执行追踪引用 |
| `result_kind` | `reply` / `fallback` / `escalation` / `tool_result` |
| `reply_blocks` | 结构化回复块 |
| `capability_refs` | 本次用到的 capability 列表 |
| `reason_codes` | fallback / escalation / failure 原因 |
| `state_trace_refs` | readiness / state 追踪引用 |
| `run_trace_refs` | data run / audit 追踪引用 |
| `dispatch_hints` | 宿主回复提示，如 thread reply / private reply |

### 8.3 runtime 与 bridge 的责任切分

runtime 负责：

- capability route
- 问题理解
- answer / fallback / escalation 组织
- 调 `auth-kernel` capability decision（如需要）
- 调 `data-platform` readiness / service

bridge 负责：

- host ingress normalize
- Gate 0 结果 enforce
- host tool publication
- host reply dispatch
- host trace / audit link

### 8.4 边界结论

bridge 与 runtime 的边界是：

> bridge 负责“怎么把授权后的请求送进 runtime、怎么把 runtime 结果送回宿主”；runtime 负责“这次交互要怎样组织”。

---

## 9. openclaw-host-bridge <-> data-platform

### 9.1 phase-1 的默认边界

phase-1 默认不建立 `bridge -> data-platform` 的直接业务数据读取路径。

默认链路必须是：

```text
bridge -> runtime -> data-platform
```

### 9.2 bridge 可读取的 data-platform 相关对象

bridge 只允许读取：

- `capability_definition` 中由 `data-platform` 发布的 capability metadata
- `capability_service_binding`
- runtime 返回的 `state_trace_refs` / `run_trace_refs`
- operator-only 的 publication health metadata（若后续需要）

### 9.3 bridge 不得直接读取的对象

bridge 不得直接读取：

- source endpoint
- raw response payload
- canonical fact tables
- latest state tables
- projection / serving tables
- internal SQL / query text

### 9.4 为什么 bridge 与 data-platform 必须保持这样边界

因为：

1. `data-platform` 定义的是数据与可答真相
2. bridge 定义的是宿主适配真相
3. 一旦 bridge 直接碰 data truth，它就会快速长成新的业务中间层

### 9.5 边界结论

bridge 与 `data-platform` 的边界是：

> bridge 只负责为 runtime 与 host 建桥，不负责直接读取或解释数据真相。

---

## 10. audit / trace 边界

### 10.1 bridge 必须记录的宿主 trace

- ingress received / normalized
- Gate 0 requested / resolved
- runtime handoff started / completed
- tool published / invoked
- reply dispatch started / completed / failed
- session resume / binding update

### 10.2 哪些 trace 只是宿主 trace

以下 trace 只属于宿主边界：

- OpenClaw run id
- host tool call id
- host session key
- delivery receipt id
- gateway client / connection id
- hook path / hook transform id

### 10.3 哪些 trace 必须进入 shared refs

以下 trace 必须进入 shared refs 或挂链字段：

- `decision_ref`
- `session_ref`
- `conversation_ref`
- `runtime_trace_ref`
- `state_trace_ref`
- `run_trace_ref`
- `data_access_audit_event` / `runtime_outcome_event` 的 refs

### 10.4 宿主 trace 与 shared refs 的关系

正确关系不是二选一，而是：

- 宿主 trace 描述“桥接层做了什么”
- shared refs 描述“下游真相层产出了什么”
- 两者通过 `request_id` / `ingress_ref` / `host_trace_ref` 关联

---

## 11. 如何防止 bridge 膨胀成“新版 qinqin2claw”

必须同时坚持以下 8 条：

1. bridge 只接受 capability-oriented contracts，不接受 source-oriented default interfaces
2. bridge 不保存业务 prompt glue
3. bridge 不保存旧问答路由分支
4. bridge 不做 role / store / date 业务推断
5. bridge 不直连 data-platform 底层 truth
6. bridge 不重写 `auth-kernel` 的 decision semantics
7. bridge 的 hook 只做 host lifecycle / bounded trigger，不做业务编排骨架
8. bridge 的 operator diagnostics 不暴露 raw secret / raw source internals

---

## 12. 核心判断

`openclaw-host-bridge` 的外部接口设计，核心不是“接口够多”，而是：

- 宿主能接进来
- 授权能挂上去
- runtime 能稳定接手
- data truth 不被 bridge 污染
- trace 能完整回链

只有这样，OpenClaw 才会持续是宿主；Navly 的长期真相仍然留在双内核里，而不是被桥接层吞进去。
