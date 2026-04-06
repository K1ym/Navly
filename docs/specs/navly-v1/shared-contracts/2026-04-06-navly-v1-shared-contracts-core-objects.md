# 2026-04-06 Navly_v1 Shared Contracts 核心共享对象清单

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 公共契约层的核心共享对象、字段骨架、真相 owner、phase-1 冻结字段与允许扩展边界

---

## 1. 文档目的

本文档回答三个问题：

1. 哪些对象属于跨模块公共契约
2. 每个对象的最小核心字段是什么
3. 哪些字段必须 `phase-1` 冻结，哪些只能作为扩展存在而不能混进核心契约

---

## 2. 共享对象总表

| 对象 | 家族 | 是否跨模块公共契约 | 真相 owner | 主要发布方 | 主要消费方 |
| --- | --- | --- | --- | --- | --- |
| `capability_id` | capability | 是 | capability owner | `data-platform` / 受治理 owner | `auth-kernel` / `bridge` / `runtime` |
| `capability_definition` | capability | 是 | capability owner | `data-platform` / 受治理 owner | 全部模块 |
| `capability_scope_requirement` | capability | 是 | capability owner | `data-platform` / 受治理 owner | `auth-kernel` / `runtime` / `bridge` |
| `capability_service_binding` | capability | 是 | capability owner | `data-platform` / 受治理 owner | `runtime` / `bridge` / `auth-kernel` |
| `actor_ref` | access | 是 | `auth-kernel` | `auth-kernel` | 其余模块 |
| `session_ref` | access | 是 | `auth-kernel` | `auth-kernel` | 其余模块 |
| `decision_ref` | access | 是 | `auth-kernel` | `auth-kernel` | 其余模块 |
| `scope_ref` | access | 是 | `auth-kernel` | `auth-kernel` | 其余模块 |
| `access_context_envelope` | access | 是 | `auth-kernel` | `auth-kernel` | `data-platform` / `bridge` / `runtime` |
| `access_decision` | access | 是 | `auth-kernel` | `auth-kernel` | `bridge` / `runtime` / `data-platform` |
| `capability_readiness_query` | readiness | 是 | shared schema；调用方写入 | `runtime` / `bridge` | `data-platform` |
| `capability_readiness_response` | readiness | 是 | `data-platform` | `data-platform` | `runtime` / `bridge` |
| `theme_service_query` | service | 是 | shared schema；调用方写入 | `runtime` / `bridge` | `data-platform` |
| `theme_service_response` | service | 是 | `data-platform` | `data-platform` | `runtime` / `bridge` |
| `capability_explanation_object` | service | 是 | `data-platform` | `data-platform` | `runtime` / `bridge` |
| `runtime_request_envelope` | interaction | 是 | shared schema；bridge 写入 | `openclaw-host-bridge` | `runtime` |
| `runtime_result_envelope` | interaction | 是 | `runtime` | `runtime` | `openclaw-host-bridge` |
| `runtime_outcome_event` | interaction / audit | 是 | `runtime` | `runtime` | `auth-kernel` / ops / bridge |
| `trace_ref` | trace | 是 | shared trace rule | ingress owner | 全部模块 |
| `state_trace_ref` | trace | 是 | `data-platform` | `data-platform` | `runtime` / `auth-kernel` / ops |
| `run_trace_ref` | trace | 是 | `data-platform` | `data-platform` | `runtime` / `auth-kernel` / ops |
| `data_access_audit_event` | audit | 是 | `data-platform` | `data-platform` | `auth-kernel` / ops |

结论：

- 上表对象全部属于跨模块公共契约。
- 它们的 schema 由 `shared-contracts` 收口。
- 它们的 truth owner 仍由对应模块拥有。

---

## 3. capability contracts

### 3.1 `capability_id`

`capability_id` 是 capability 的稳定主标识。

#### 规则

- 类型：`string`
- `phase-1` 推荐格式：`navly.<domain>.<capability_name>`
- 必须小写
- 必须由 `Navly` 作为顶层主语义前缀
- 不允许把 OpenClaw host 名、Qinqin endpoint 名、LLM skill 名直接当 `capability_id`

#### 允许示意

- `navly.store.daily_summary`
- `navly.member.consume_overview`

#### 禁止示意

- `GetConsumeBillList`
- `openclaw.wecom.store_tool`
- `gpt_answer_store_report`

### 3.2 `capability_definition`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `capability_id` | `string` | freeze | 唯一能力标识 |
| `capability_kind` | `enum` | freeze | `data_read` / `runtime_action` |
| `owner_module` | `string` | freeze | 当前 capability 的 owner，如 `data-platform` |
| `contract_status` | `string` | freeze | `active` / `deprecated`，用于避免调用未启用 contract |
| `summary` | `string` | extend | 文档说明文字，不得作为逻辑分支键 |
| `metadata` / `extensions` | `object` | extend | 命名空间化扩展区 |

说明：

- `capability_definition` 是跨模块公共契约。
- 它只定义 capability 的公共身份，不定义具体数据真相或 prompt 逻辑。
- `summary` 仅用于文档与可读性，不用于授权、路由或 readiness 分支。

### 3.3 `capability_scope_requirement`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `capability_id` | `string` | freeze | 所属 capability |
| `scope_kind` | `enum` | freeze | `tenant` / `org` / `store` / `hq` |
| `requirement_level` | `enum` | freeze | `required` / `optional` |
| `selection_mode` | `enum` | freeze | `single` / `multiple` / `tenant_wide` |
| `is_default_scope_kind` | `boolean` | freeze | 多 scope 能力时的默认 scope 选择 |
| `extensions` | `object` | extend | 模块私有补充，不得改变上表语义 |

说明：

- `auth-kernel` 用它理解 capability 需要什么范围；`runtime` 用它决定是否要显式补 scope。
- `selection_mode` 是公共语义，不能被宿主 UI 或 prompt 文本替代。

### 3.4 `capability_service_binding`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `capability_id` | `string` | freeze | 所属 capability |
| `service_object_id` | `string` | freeze | 绑定的服务对象标识，推荐格式 `navly.service.<domain>.<object_name>` |
| `service_kind` | `enum` | freeze | `theme_service` |
| `is_default_binding` | `boolean` | freeze | 是否为默认服务输出 |
| `include_explanation_supported` | `boolean` | freeze | 是否支持附带 `capability_explanation_object` |
| `extensions` | `object` | extend | 非核心补充字段 |

说明：

- `capability_service_binding` 决定“同一个 capability 对外默认提供什么服务对象”。
- 它不定义服务 payload 内部结构；payload 结构属于 `data-platform` 服务对象目录。

---

## 4. access contracts

### 4.1 共享引用对象总原则

`actor_ref`、`session_ref`、`decision_ref`、`scope_ref` 在 `phase-1` 均采用 **标准化字符串引用**。

| 引用 | 推荐格式 | owner | 说明 |
| --- | --- | --- | --- |
| `actor_ref` | `navly:actor:<actor_id>` | `auth-kernel` | canonical actor 引用 |
| `session_ref` | `navly:session:<session_id>` | `auth-kernel` | 授权 session 引用，不等于 host session |
| `decision_ref` | `navly:decision:<decision_id>` | `auth-kernel` | 一次 Gate 0 或 capability decision 引用 |
| `scope_ref` | `navly:scope:<scope_kind>:<scope_id>` | `auth-kernel` | 受控范围引用 |

规则：

- `*_ref` 不能用 display name、自然语言文本或宿主内部 id 替代。
- `session_ref` 不能直接等于 `host_session_ref`。
- `scope_ref` 不能写成 `store_name=...` 这类自由文本。

### 4.2 `access_context_envelope`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 本次调用请求标识 |
| `trace_ref` | `string` | freeze | 当前交互追踪引用 |
| `decision_ref` | `string` | freeze | 当前生效 access decision 引用 |
| `actor_ref` | `string` | freeze | 当前 actor |
| `session_ref` | `string` | freeze | 当前授权 session |
| `conversation_ref` | `string` | freeze | 当前 conversation 绑定引用 |
| `tenant_ref` | `string` | freeze | 顶层租户 / 组织引用 |
| `primary_scope_ref` | `string` | freeze | 当前默认 scope |
| `granted_scope_refs` | `string[]` | freeze | 当前授予的 scope 集合 |
| `granted_capability_ids` | `string[]` | freeze | 当前允许调用的 capability 集合 |
| `issued_at` | `datetime` | freeze | 签发时间 |
| `expires_at` | `datetime` | freeze | 过期时间 |
| `extensions` | `object` | extend | 审计或模块补充信息 |

说明：

- 这是跨模块公共契约。
- `data-platform` 只能消费它，不能自己推导或补造它。
- `role` 名、host workspace、群聊 thread 等只允许作为扩展或上游证据，不能成为 core field。

### 4.3 `access_decision`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `decision_ref` | `string` | freeze | 决策引用 |
| `request_id` | `string` | freeze | 对应请求 |
| `trace_ref` | `string` | freeze | 交互追踪引用 |
| `decision_status` | `enum` | freeze | `allow` / `deny` / `restricted` / `escalation` |
| `actor_ref` | `string` | freeze | 当前 actor |
| `session_ref` | `string` | freeze | 当前 session |
| `target_capability_id` | `string` | freeze | 当前判定目标 capability |
| `target_scope_ref` | `string` | freeze | 当前判定目标 scope |
| `reason_codes` | `string[]` | extend | 访问原因代码，phase-1 由 `auth-kernel` 专项治理 |
| `restriction_codes` | `string[]` | extend | 受限条件 |
| `obligation_codes` | `string[]` | extend | 调用义务 |
| `decided_at` | `datetime` | freeze | 决策时间 |
| `expires_at` | `datetime` | freeze | 决策有效期 |

说明：

- `decision_status` 是共享主枚举；`reason_codes` 的详细字典仍由 `auth-kernel` 专项文档治理。
- `data-platform` 只能校验 envelope 完整性与 capability/scope 一致性，不能重做 access decision。

---

## 5. readiness contracts

### 5.1 `capability_readiness_query`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 请求标识 |
| `trace_ref` | `string` | freeze | 当前交互追踪引用 |
| `capability_id` | `string` | freeze | 目标 capability |
| `access_context` | `access_context_envelope` | freeze | 标准访问上下文 |
| `target_scope_ref` | `string` | freeze | 目标 scope |
| `target_business_date` | `date` | freeze | 请求业务日期 |
| `freshness_mode` | `enum` | freeze | `latest_usable` / `strict_date` |
| `extensions` | `object` | extend | 调用方可选补充 |

### 5.2 `blocking_dependency_ref`

`blocking_dependency_ref` 是 `capability_readiness_response.blocking_dependencies` 的标准元素形态。

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `dependency_kind` | `enum` | freeze | `input_data` / `state_gate` / `projection` |
| `dependency_ref` | `string` | freeze | 依赖对象引用，不得使用物理表名或 SQL 文本 |
| `blocking_reason_code` | `readiness_reason_code` | freeze | 当前阻塞原因 |
| `state_trace_refs` | `string[]` | extend | 可选的状态追踪引用 |
| `run_trace_refs` | `string[]` | extend | 可选的历史执行引用 |

### 5.3 `capability_readiness_response`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 对应请求 |
| `trace_ref` | `string` | freeze | 当前交互追踪引用 |
| `capability_id` | `string` | freeze | 目标 capability |
| `readiness_status` | `enum` | freeze | `ready` / `pending` / `failed` / `unsupported_scope` |
| `evaluated_scope_ref` | `string` | freeze | 实际评估的 scope |
| `requested_business_date` | `date` | freeze | 请求业务日期 |
| `latest_usable_business_date` | `date` | freeze | 当前最新可用业务日期 |
| `reason_codes` | `readiness_reason_code[]` | freeze | readiness 原因主集合 |
| `blocking_dependencies` | `blocking_dependency_ref[]` | freeze | 阻塞依赖引用方式 |
| `state_trace_refs` | `string[]` | freeze | 命中的状态追踪引用 |
| `run_trace_refs` | `string[]` | freeze | 相关历史 run 追踪引用；若当前无 run trace 也应返回空数组 |
| `evaluated_at` | `datetime` | freeze | 评估时间 |

说明：

- `readiness_status` 只表达“当前能力在该 scope/date 是否可答”。
- 它不表达 access allow / deny，不表达最终用户话术。
- `run_trace_refs` 在 phase-1 进入必填主骨架；若当前无历史执行引用，也应显式返回空数组。
- `reason_codes` 与 `blocking_dependencies` 必须可审计，不能退化成自由文本解释。

---

## 6. service contracts

### 6.1 `theme_service_query`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 请求标识 |
| `trace_ref` | `string` | freeze | 当前交互追踪引用 |
| `capability_id` | `string` | freeze | 所属 capability |
| `service_object_id` | `string` | freeze | 目标服务对象；默认 binding 应在 runtime route 阶段完成，进入 `theme_service_query` 时必须已带出 canonical `service_object_id` |
| `access_context` | `access_context_envelope` | freeze | 标准访问上下文 |
| `target_scope_ref` | `string` | freeze | 目标范围 |
| `target_business_date` | `date` | freeze | 目标业务日期 |
| `include_explanation` | `boolean` | freeze | 是否附带 explanation |
| `extensions` | `object` | extend | 非核心补充 |

### 6.2 `theme_service_response`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | freeze | 对应请求 |
| `trace_ref` | `string` | freeze | 当前交互追踪引用 |
| `capability_id` | `string` | freeze | 所属 capability |
| `service_object_id` | `string` | freeze | 实际返回的服务对象 |
| `service_status` | `enum` | freeze | `served` / `not_ready` / `scope_mismatch` / `error` |
| `service_object` | `object` | freeze-envelope | 服务对象 payload 槽位；payload 内部 schema 不在 shared-contracts 冻结 |
| `data_window` | `object` | freeze | 实际覆盖的业务日期窗口 |
| `explanation_object` | `capability_explanation_object` | freeze | 可选解释对象 |
| `state_trace_refs` | `string[]` | freeze | 状态追踪引用 |
| `run_trace_refs` | `string[]` | freeze | 历史执行追踪引用 |
| `served_at` | `datetime` | freeze | 返回时间 |

说明：

- 这里冻结的是 **response envelope**，不是主题 payload 的字段级 schema。
- 主题 payload 的内部结构由 `data-platform` 服务对象目录单独治理。

### 6.3 `capability_explanation_object`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `capability_id` | `string` | freeze | 所属 capability |
| `explanation_scope` | `enum` | freeze | `readiness` / `service` |
| `reason_codes` | `readiness_reason_code[]` | freeze | 结构化原因代码 |
| `summary_tokens` | `string[]` | extend | 模块自有解释 token；不得作为跨模块逻辑条件 |
| `state_trace_refs` | `string[]` | freeze | 状态追踪引用 |
| `run_trace_refs` | `string[]` | freeze | 历史执行追踪引用 |
| `extensions` | `object` | extend | 结构化参数、提示信息 |

说明：

- `capability_explanation_object` 是跨模块公共契约。
- 它提供结构化解释，不提供最终用户话术。
- `runtime` 只能消费 `reason_codes` 与 trace，不应把 `summary_tokens` 当成新的主语义。

---

## 7. interaction contracts

### 7.1 `runtime_request_envelope`

- 这是 bridge -> runtime 的 canonical request envelope
- 详细字段方案见：
  - `2026-04-06-navly-v1-shared-contracts-interaction.md`

### 7.2 `runtime_result_envelope`

- 这是 runtime -> bridge 的 canonical result envelope
- 详细字段方案见：
  - `2026-04-06-navly-v1-shared-contracts-interaction.md`

### 7.3 `runtime_outcome_event`

- 这是 runtime 对外发布的 canonical outcome event
- 详细字段方案见：
  - `2026-04-06-navly-v1-shared-contracts-interaction.md`

---

## 8. trace / audit objects

### 8.1 `trace_ref`

- 类型：`string`
- 推荐格式：`navly:trace:<trace_id>`
- 含义：一次跨模块交互链路的顶层追踪引用
- owner：当前入口 / 调用链的 ingress owner

### 8.2 `state_trace_ref`

- 类型：`string`
- 推荐格式：`navly:state-trace:<state_type>:<state_id>`
- 含义：数据中台某个状态对象、状态发布或状态快照的追踪引用
- owner：`data-platform`

### 8.3 `run_trace_ref`

- 类型：`string`
- 推荐格式：`navly:run-trace:<run_type>:<run_id>`
- 含义：数据中台某次 ingestion / endpoint / replay run 的历史执行追踪引用
- owner：`data-platform`

### 8.4 `data_access_audit_event`

| 字段 | 类型 | phase-1 | 说明 |
| --- | --- | --- | --- |
| `event_id` | `string` | freeze | 审计事件主标识 |
| `request_id` | `string` | freeze | 对应请求 |
| `trace_ref` | `string` | freeze | 顶层交互追踪引用 |
| `decision_ref` | `string` | freeze | 对应 access decision |
| `actor_ref` | `string` | freeze | 访问主体 |
| `session_ref` | `string` | freeze | 访问 session |
| `capability_id` | `string` | freeze | 被访问 capability |
| `scope_ref` | `string` | freeze | 实际命中范围 |
| `service_object_id` | `string` | freeze | 实际访问的服务对象 |
| `business_date` | `date` | freeze | 读取业务日期 |
| `readiness_status` | `enum` | freeze | 查询时的 readiness 结果 |
| `service_status` | `enum` | freeze | 服务调用结果 |
| `state_trace_refs` | `string[]` | freeze | 状态追踪引用 |
| `run_trace_refs` | `string[]` | freeze | 历史执行追踪引用 |
| `occurred_at` | `datetime` | freeze | 事件发生时间 |
| `extensions` | `object` | extend | 模块补充审计字段 |

说明：

- `data_access_audit_event` 是跨模块公共契约；truth owner 为 `data-platform`。
- `auth-kernel` 与 ops 读取它做治理闭环，但不改写其主语义。

---

## 9. 哪些字段可以扩展，但不能进入核心契约

以下内容允许存在于模块自有扩展区，但不能进入 shared-contracts 核心字段：

- OpenClaw `host_session_ref`、`workspace_ref`、gateway message id
- WeCom 原始 sender / chat payload
- prompt 模板名、LLM model 名、tool scratchpad、agent memory 摘要
- 物理表名、SQL 文本、临时缓存 key、分页 token
- private secret、签名串、真实 access token、cookie
- 仅供单模块内部使用的解释文本或调试字段

这些信息一旦需要被第二个模块稳定消费，应进入正式 contract 评审，而不是继续藏在 `extensions` 中。
