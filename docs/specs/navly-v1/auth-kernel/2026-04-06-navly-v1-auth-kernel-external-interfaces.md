# 2026-04-06 Navly_v1 权限与会话绑定内核外部接口方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `auth-kernel` 对外边界，尤其是与 `data-platform`、`openclaw-host-bridge`、`runtime` 的输入输出契约、责任归属和禁止耦合点

---

## 1. 文档目的

本文档回答：

> `auth-kernel` 对外应该暴露什么，不应该暴露什么；`openclaw-host-bridge`、`runtime`、`data-platform` 分别向 `auth-kernel` 提供什么，又从 `auth-kernel` 拿走什么？

---

## 2. 总体边界原则

### 2.1 `auth-kernel` 决定“谁能在什么绑定下继续往前走”

- `auth-kernel` 拥有：actor、role、scope、conversation、Gate 0、access decision、governance
- `data-platform` 拥有：数据事实、最新状态、readiness、theme / service object
- `runtime` 拥有：交互编排、能力选择、回答组织、fallback / escalation 表达
- `openclaw-host-bridge` 拥有：渠道接入、宿主 session / workspace 承载、消息转接

### 2.2 OpenClaw bridge 提供入口证据，不提供最终权限真相

bridge 可以提供：

- channel identity evidence
- host session / workspace ref
- conversation candidate
- ingress mode

bridge 不可以提供：

- 最终 actor 结论
- 最终 role / scope 结论
- 最终 capability allow / deny 结论

### 2.3 Gate 0 在入口边界执行，capability decision 在受保护调用边界执行

- **Gate 0**：在 `openclaw-host-bridge` 完成入口归一化之后、runtime / data-platform 之前执行
- **capability decision**：在 runtime 或 bridge 即将调用受保护 capability / tool / data service 之前执行

两者都属于 `auth-kernel`，都不能由上层替代。

### 2.4 capability 标识必须统一为 namespaced capability_id

跨 `auth-kernel`、`runtime`、`data-platform`、`openclaw-host-bridge` 的能力标识统一为 **namespaced capability_id**。

要求：

- registry、decision、envelope、audit 中使用同一 `capability_id`
- 禁止裸 capability 名在跨模块 contract 中直接出现
- 当前不引入第二套 `capability_name` canonical 主键

### 2.5 对外主语必须是 actor / scope / conversation / capability / decision

对外接口的主语应是：

- `actor_ref`
- `scope_ref` / `scope_kind`
- `conversation_ref`
- `capability_id`
- `decision_ref`
- `access_context_envelope`

而不是：

- 某个 OpenClaw session id 直接当 actor
- 某个 role 名直接被 data-platform 拿来做业务过滤
- 某段 prompt 文本当成权限授权

### 2.6 下游必须 fail closed

如果缺少：

- `decision_ref`
- 有效 `access_context_envelope`
- 必要的 scope / capability grant

则下游必须拒绝继续，而不是自行猜测默认允许。

---

## 3. 四方责任矩阵

| 问题 | auth-kernel | openclaw-host-bridge | runtime | data-platform |
| --- | --- | --- | --- | --- |
| 当前 actor 是谁 | 负责 | 提供入口证据 | 只消费 | 只消费 |
| 当前 role / scope / conversation 是什么 | 负责 | 提供宿主上下文证据 | 只消费 | 只消费 |
| 入口能否进入 Navly runtime | 负责（Gate 0） | 执行拦截与转发 | 不负责 | 不负责 |
| 某 capability 是否允许访问 | 负责 | 可作为调用方 | 可作为调用方 | 只校验 envelope |
| 数据是否 ready / 有没有数 | 不负责 | 不负责 | 只消费 | 负责 |
| 回答如何组织与表达 | 不负责 | 不负责 | 负责 | 不负责 |
| 权限审计与访问追踪 | 负责 | 回传使用结果 | 回传使用结果 | 回传数据访问结果 |

---

## 4. 跨模块共享标识与基础 contract

推荐至少统一以下引用：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 一次入口或一次受保护调用的请求标识 |
| `actor_ref` | canonical actor 引用 |
| `binding_snapshot_ref` | 本次决策依赖的 binding 快照引用 |
| `conversation_ref` | 由 `auth-kernel` 确认的 conversation 引用 |
| `session_ref` | `auth-kernel` 侧授权 session 引用 |
| `decision_ref` | 一次 Gate 0 或 capability decision 的正式引用 |
| `capability_id` | namespaced 能力唯一标识 |
| `scope_ref` | 受控范围引用，如 `store_ref` / `org_ref` / `hq_ref` |
| `tenant_ref` | 租户 / 组织顶层引用 |

说明：

- `host_session_ref` / `workspace_ref` 可以作为 bridge 输入证据，但不能替代上述正式引用
- `role` 名称可以透传做审计补充，但不应成为跨模块的主判断键

---

## 5. auth-kernel <-> openclaw-host-bridge

### 5.1 bridge -> auth-kernel：Ingress Identity Envelope

bridge 在入口边界应向 `auth-kernel` 提供 **Ingress Identity Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次入口请求 ID |
| `ingress_ref` | 入口事件引用 |
| `channel_kind` | 渠道类型，如 `wecom` |
| `channel_account_ref` | 宿主侧账户引用 |
| `peer_identity_evidence` | channel user / peer / sender 等身份线索 |
| `host_session_ref` | OpenClaw host session 引用 |
| `host_workspace_ref` | OpenClaw workspace 引用 |
| `host_conversation_ref` | 宿主会话 / thread / group 引用 |
| `message_mode` | 私聊 / 群聊 / thread / command 等入口形态 |
| `received_at` | 入口接收时间 |
| `trace_ref` | 原始入口追踪引用 |

说明：

- 这是**入口证据**，不是权限结论
- `auth-kernel` 必须自己做 actor normalization 与 binding resolution

### 5.2 auth-kernel -> bridge：Gate 0 Result

`auth-kernel` 在入口边界返回 **Gate 0 Result**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `decision_ref` | Gate 0 决策引用 |
| `gate_status` | `allow` / `deny` / `restricted` / `escalation` |
| `actor_ref` | 当前解析出的 canonical actor |
| `binding_snapshot_ref` | 本次入口使用的绑定快照 |
| `conversation_ref` | 经确认后的 conversation 引用 |
| `session_ref` | 授权后的 session 引用 |
| `restriction_codes` | 当前入口限制 |
| `obligation_codes` | 继续前需要满足的义务 |
| `reason_codes` | 拒绝 / 受限 / 升级原因 |
| `expires_at` | 本次入口授权结果的有效期 |

bridge 处理要求：

- `allow`：可继续把请求交给 runtime
- `restricted`：可继续，但必须附带 restriction / obligation 进入 runtime
- `deny`：直接在入口拦截
- `escalation`：停在授权边界，触发升级流或明确提示

### 5.3 bridge -> auth-kernel：Conversation Binding Update

当 bridge 侦测到会话切换、scope 选择或宿主 session 恢复时，应调用 **Conversation Binding Update**。

推荐字段：

- `session_ref`
- `conversation_ref`
- `trigger_type`（如 `new_thread` / `resume` / `scope_select`）
- `selected_scope_ref`（若有）
- `operator_action_ref`
- `occurred_at`

### 5.4 明确禁止的耦合

bridge 与 `auth-kernel` 之间禁止：

1. 直接把 OpenClaw session / workspace 当 actor 真相
2. 在 bridge 里硬编码 role -> capability 的最终授权关系
3. 把权限结论只写进自然语言 prompt，不写 `decision_ref`
4. 让 bridge 自己维护 conversation 的最终权限状态而不回写 `auth-kernel`

---

## 6. auth-kernel <-> runtime

### 6.1 runtime -> auth-kernel：Runtime Capability Declaration

runtime 中的受保护动作能力，应向 `auth-kernel` 发布 **Runtime Capability Declaration**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `capability_id` | namespaced 动作能力 ID |
| `capability_kind` | 如 `runtime_action` |
| `supported_scope_kind` | 支持的 scope 粒度 |
| `sensitivity_tier` | 风险或敏感级别 |
| `required_binding_predicates` | 需要满足的 binding 条件 |
| `default_restriction_profile` | 默认限制轮廓 |
| `owner_module` | 声明来源，如 `runtime` |

说明：

- runtime 只声明“这个能力是什么、需要什么授权条件”
- 最终谁能用，由 `auth-kernel` 决定

### 6.2 runtime -> auth-kernel：Capability Access Request

在 runtime 调用受保护能力前，应发起 **Capability Access Request**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次调用请求 ID |
| `session_ref` | 当前授权 session |
| `conversation_ref` | 当前 conversation |
| `decision_ref` | 入口 Gate 0 或前置 decision 引用 |
| `requested_capability_id` | 目标 capability |
| `requested_scope_ref` | 希望作用的 scope |
| `operation_kind` | 如 `read` / `write` / `invoke` |
| `runtime_trace_ref` | runtime 当前执行链追踪引用 |

### 6.3 auth-kernel -> runtime：Access Decision / Access Context Envelope

`auth-kernel` 向 runtime 返回 **Access Decision** 与 **Access Context Envelope**。

推荐核心字段：

| 字段 | 说明 |
| --- | --- |
| `decision_ref` | 本次 capability decision 引用 |
| `access_decision_status` | `allow` / `deny` / `restricted` / `escalation` |
| `actor_ref` | 当前 actor |
| `session_ref` | 当前授权 session |
| `conversation_ref` | 当前 conversation |
| `tenant_ref` | 顶层租户 / 组织引用 |
| `scope_kind` | 当前 scope 类型 |
| `granted_scope_refs` | 当前正式授予的范围集合 |
| `granted_capability_ids` | 当前允许的 capability |
| `restriction_codes` | 被收窄的部分 |
| `obligation_codes` | 调用时必须满足的要求 |
| `reason_codes` | 拒绝 / 受限 / 升级原因 |
| `issued_at` / `expires_at` | 有效时间窗 |

### 6.4 runtime -> auth-kernel：Runtime Outcome Event

runtime 完成受保护调用后，应回传 **Runtime Outcome Event**，供治理审计闭环。

推荐字段：

- `event_id`
- `request_id`
- `decision_ref`
- `capability_id`
- `outcome_status`（如 `executed` / `blocked` / `failed` / `escalated`）
- `trace_refs`
- `occurred_at`

### 6.5 明确禁止的耦合

runtime 与 `auth-kernel` 之间禁止：

1. runtime 用 role 名或 prompt 自己推断 capability 是否允许
2. runtime 自己改写 scope 集合后继续调用下游
3. runtime 把自然语言解释当作权限正式 contract
4. runtime 将 conversation transcript 当作 conversation binding truth

---

## 7. auth-kernel <-> data-platform

### 7.1 data-platform -> auth-kernel：Capability Declaration

与 `docs/specs/navly-v1/data-platform/2026-04-06-navly-v1-data-platform-external-interfaces.md` 保持一致，数据中台应向 `auth-kernel` 发布 **Capability Declaration**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `capability_id` | namespaced 数据能力唯一标识 |
| `supported_scope_kind` | 能力支持的 scope 粒度 |
| `required_data_domains` | 能力依赖的数据域 |
| `service_object_id` | 默认输出对象 |
| `sensitivity_tier` | 数据敏感级别 |
| `default_filters` | 默认 scope 过滤键 |
| `owner_module` | 固定为 `data-platform` |

说明：

- data-platform 只声明能力与敏感级别
- 最终授权由 `auth-kernel` 决定

### 7.2 auth-kernel -> data-platform：Access Context Envelope

与数据中台专项文档保持兼容，`auth-kernel` 向数据中台提供 **Access Context Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次请求唯一标识 |
| `decision_ref` | 权限判定引用 |
| `session_ref` | 会话引用 |
| `conversation_ref` | conversation 引用 |
| `actor_ref` | 标准 actor 引用 |
| `tenant_ref` | 租户 / 组织级引用 |
| `scope_kind` | 当前 scope 类型 |
| `allowed_org_ids` | phase-1 对 org 范围的兼容投影 |
| `allowed_store_ids` | phase-1 对 store 范围的兼容投影 |
| `granted_scope_refs` | 通用 scope 授权集合 |
| `granted_capability_ids` | 当前允许调用的数据 capability 列表 |
| `restriction_codes` | 当前限制 |
| `issued_at` / `expires_at` | 上下文有效期 |

说明：

- `allowed_org_ids` / `allowed_store_ids` 是 phase-1 的兼容字段
- 长期上更推荐下游基于 `granted_scope_refs` 和 `scope_kind` 统一消费
- data-platform 只使用该 envelope 做 scope 过滤、审计归档、边界校验
- data-platform 不重做权限决策

### 7.3 data-platform -> auth-kernel：Data Access Audit Event

与数据中台专项文档保持一致，每次数据读请求结束后，数据中台应向 `auth-kernel` 或统一治理面输出 **Data Access Audit Event**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `event_id` | 审计事件 ID |
| `request_id` | 请求 ID |
| `decision_ref` | 对应的权限决策引用 |
| `actor_ref` | 访问主体 |
| `capability_id` | 访问的数据能力 |
| `scope_ref` | 实际命中的 scope |
| `business_date` | 读取的数据业务日期 |
| `result_status` | `served` / `not_ready` / `scope_mismatch` / `error` |
| `trace_refs` | 对应 readiness / theme / run 的追溯引用 |

### 7.4 明确禁止的耦合

`auth-kernel` 与 data-platform 之间禁止：

1. data-platform 直接根据 role 名硬编码业务过滤逻辑
2. `auth-kernel` 直连 data-platform 内部事实表做权限判断
3. data-platform 在缺少有效 envelope 时默许访问
4. 用自然语言 prompt 传递权限结论

---

## 8. access decision 的正式表达

`access_decision_status` canonical 统一为：`allow / deny / restricted / escalation`。

明确约束：

- 不再使用 `escalation_required`
- 如需表达需要升级，统一使用 `access_decision_status = escalation`

推荐所有外部消费者统一理解如下语义：

| 状态 | 说明 | 对调用方要求 |
| --- | --- | --- |
| `allow` | 当前 capability / scope / conversation 组合被正式授权 | 按 envelope 继续 |
| `deny` | 当前请求明确不被授权 | 立即停止，返回 reason codes |
| `restricted` | 可以继续，但只能在被收窄的范围或模式下继续 | 严格遵守 `restriction_codes` / `obligation_codes` |
| `escalation` | 需要更高权限、人工确认或更安全会话 | 不得继续自动执行，应转入升级流程 |

说明：

- `restricted` 不是“差不多 allow”，而是**正式受限授权**
- `escalation` 不是“语义更友好的 deny”，而是**需要进入另一授权路径**

---

## 9. 如何保证上层不自己推断权限真相

必须同时满足以下机制：

1. **统一注册 capability**
   - runtime / data-platform 的能力都先向 `auth-kernel` 声明，再由 `auth-kernel` 决定授权
2. **统一签发 envelope**
   - 下游只认 `auth-kernel` 签发的 `access_context_envelope`
3. **统一强制携带 `decision_ref`**
   - 任意受保护调用若无 `decision_ref`，必须 fail closed
4. **统一 machine-readable 状态**
   - `allow / deny / restricted / escalation`、reason / restriction / obligation 都必须结构化
5. **统一审计回写**
   - bridge / runtime / data-platform 都必须回传 outcome event，形成 decision-to-usage 闭环
6. **统一禁止越权推断**
   - role 名、消息文本、host session id、prompt 规则都不能替代权限真相

只要这些机制成立，上层就不能把“自己猜出来的权限结论”伪装成系统正式真相。

---

## 10. 接口边界的关键判断

`auth-kernel` 对外不是暴露一堆内部表，而是暴露：

- 标准化入口检查
- 标准化 capability 授权检查
- 标准化 access context envelope
- 标准化治理与审计回路

这也是 `Navly_v1` 保证“权限真相属于 auth-kernel，而不是属于 OpenClaw host、runtime prompt 或 data-platform 过滤层”的关键边界。
