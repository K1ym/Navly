# 2026-04-06 Navly_v1 thin runtime shell 外部接口方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `thin runtime shell` 与 `openclaw-host-bridge`、`auth-kernel`、`data-platform` 的正式接口、request lifecycle、错误归属与禁止耦合点

---

## 1. 文档目的

本文档回答：

> `runtime` 对外应该暴露什么，不应该暴露什么；bridge、auth-kernel、data-platform 分别向 runtime 提供什么，又从 runtime 拿走什么？

---

## 2. 总体边界原则

### 2.1 runtime 负责组织交互，不负责定义内核真相

- `openclaw-host-bridge` 负责：渠道接入、宿主承载、入口转发、结果投递
- `auth-kernel` 负责：访问真相、Gate 0、capability access decision
- `data-platform` 负责：数据真相、readiness、service object、explanation object
- `runtime` 负责：capability route、guarded execution、answer / fallback / escalation

### 2.2 runtime 对外主语必须是 capability / service / access / readiness

`runtime` 对外应围绕：

- `capability_id`
- `service_object_id`
- `access_context_envelope`
- `access_decision`
- `capability_readiness_response`
- `theme_service_response`
- `runtime_result_envelope`

而不是围绕：

- source endpoint
- 物理表名
- role 名称本身
- prompt 文本本身

### 2.3 runtime 必须先消费 access truth，再消费 data truth

request lifecycle 中，runtime 必须遵守：

1. 先拿到 bridge 交来的 `access_context_envelope`
2. capability route 完成后，再向 `auth-kernel` 请求 capability access decision
3. access 允许后，再向 `data-platform` 先发 readiness query
4. readiness `ready` 后，才向 `data-platform` 发 service query

### 2.4 runtime 必须 fail closed

若出现以下任一情况，runtime 必须停止并返回结构化结果：

- 缺失 `access_context_envelope`
- capability route 无法安全解析
- capability access decision 未获允许
- data-platform 未返回可消费 readiness truth

---

## 3. 四方责任矩阵

| 问题 | openclaw-host-bridge | runtime | auth-kernel | data-platform |
| --- | --- | --- | --- | --- |
| 如何接入 WeCom / OpenClaw | 负责 | 不负责 | 不负责 | 不负责 |
| 入口请求如何规范化 | 负责 | 只消费 | 不负责 | 不负责 |
| actor / role / scope / conversation 是什么 | 提供证据 | 只消费 | 负责 | 只消费 |
| 入口能否继续进入 Navly | 执行拦截/转发 | 不负责 | 负责（Gate 0） | 不负责 |
| 当前交互选择哪个 capability | 不负责主逻辑 | 负责 | 只校验 capability 访问 | 不负责 |
| capability 当前是否允许调用 | 不负责主逻辑 | 发起请求并消费结果 | 负责 | 只校验 envelope |
| capability 当前是否 ready | 不负责 | 只消费 | 不负责 | 负责 |
| 主题服务对象是什么 | 不负责 | 只消费并组织表达 | 不负责 | 负责 |
| 最终 answer / fallback / escalation 怎么表达 | 只负责投递 | 负责 | 不负责 | 不负责 |
| 权限 / 数据 / 运行时错误怎么分类 | 只透传 | 负责分类与封装 | 负责权限侧原因 | 负责数据侧原因 |

---

## 4. 与 shared contracts 的关系

runtime phase-1 默认消费或输出以下 shared contracts：

- `capability_definition`
- `capability_service_binding`
- `access_context_envelope`
- `access_decision`
- `capability_readiness_query`
- `capability_readiness_response`
- `theme_service_query`
- `theme_service_response`
- `capability_explanation_object`
- `trace_ref` / `state_trace_ref` / `run_trace_ref`
- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

规则：

- 只在 runtime 内部使用的对象不必进入 shared contracts
- 任何 bridge <-> runtime、runtime <-> auth、runtime <-> data 的跨模块对象，都不应各写一套私有语义

---

## 5. runtime <-> openclaw-host-bridge

### 5.1 bridge -> runtime：Runtime Request Envelope

bridge 在完成入口标准化、并拿到 Gate 0 结果后，应向 runtime 提供 **Runtime Request Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次 runtime 请求 ID |
| `ingress_ref` | bridge 侧入口事件引用 |
| `channel_kind` | 渠道类型，如 `wecom` |
| `message_mode` | 私聊 / 群聊 / thread / command |
| `user_input_text` | 规范化后的用户输入文本 |
| `structured_input_slots` | 结构化输入槽位，例如显式日期、显式 scope hint |
| `requested_capability_id` | 若来自菜单/按钮/命令入口，则显式给出 |
| `requested_service_object_id` | 若来自明确服务对象入口，可显式给出 |
| `target_scope_hint` | 交互想指向的 scope 提示，不代表授权结果 |
| `target_business_date_hint` | 期望业务日期提示 |
| `response_channel_capabilities` | 当前渠道可投递的响应形式 |
| `access_context_envelope` | 来自 `auth-kernel` 的标准访问上下文 |
| `decision_ref` | 入口 Gate 0 决策引用 |
| `trace_ref` | bridge 侧追踪引用 |

说明：

- bridge 提供的是 **已规范化的入口请求**，不是业务路由结论
- `target_scope_hint` 只是 hint，最终以 `auth-kernel` 授权与 `data-platform` scope 校验为准
- runtime 不需要理解 OpenClaw 内部 session 结构，只需消费受控引用和宿主能力元数据

### 5.2 runtime -> bridge：Runtime Result Envelope

runtime 完成后，应向 bridge 返回 **Runtime Result Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 对应请求 ID |
| `runtime_trace_ref` | runtime 执行追踪引用 |
| `result_status` | `answered` / `fallback` / `escalated` / `rejected` / `runtime_error` |
| `selected_capability_id` | 实际执行的 capability |
| `selected_service_object_id` | 实际读取的服务对象 |
| `answer_fragments` | 渠道无关的回答片段 |
| `explanation_fragments` | explanation / fallback 片段 |
| `escalation_action` | 若需要升级，给出结构化动作建议 |
| `reason_codes` | 结构化原因码 |
| `trace_refs` | 对应 access / readiness / service / run trace |
| `delivery_hints` | 给 bridge 的投递提示 |

说明：

- bridge 负责最终渠道渲染与投递
- bridge 不应根据 `result_status` 再写一套业务含义相同但语义不同的逻辑

### 5.3 明确禁止的耦合

bridge 与 runtime 之间禁止：

1. 在 bridge 里硬编码 capability route 主逻辑
2. 让 bridge 直接调用 data-platform 默认回答用户
3. 让 runtime 依赖 OpenClaw 内部对象结构作为主 contract
4. 用自然语言 prompt 在 bridge 与 runtime 之间传递业务判断

---

## 6. runtime <-> auth-kernel

### 6.1 runtime 如何消费 access_context / access_decision

runtime 必须把 `access_context_envelope` 当作：

- access truth 的唯一受控入口
- scope / session / conversation / capability grant 的正式来源
- 所有后续 capability 调用的前提

runtime 不应把以下内容当权限真相：

- user message 自带的“我是某店长”
- bridge 私有 session 字段
- 历史对话里某段自然语言

### 6.2 runtime -> auth-kernel：Capability Access Request

在实际调用 capability 前，runtime 应发起 **Capability Access Request**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次调用请求 ID |
| `session_ref` | 当前授权 session |
| `conversation_ref` | 当前 conversation |
| `prior_decision_ref` | 入口 Gate 0 决策引用 |
| `requested_capability_id` | 目标 capability |
| `requested_scope_ref` | 期望作用范围 |
| `requested_service_object_id` | 可选，便于审计与受限能力解释 |
| `operation_kind` | 如 `read` / `invoke` |
| `runtime_trace_ref` | runtime 执行链追踪引用 |

### 6.3 auth-kernel -> runtime：Access Decision / Access Context

`auth-kernel` 向 runtime 返回：

- `access_decision`
- 更新后的 `access_context_envelope`（若有收窄）
- `reason_codes` / `restriction_codes` / `obligation_codes`

runtime 要求：

- `allow`：继续执行
- `restricted`：只在授权收窄范围内继续执行
- `deny`：停止并走拒答路径
- `escalation`：停止数据调用并走升级路径

### 6.4 runtime 不应重做的权限判断

runtime 不应重做：

1. actor identity resolution
2. role -> capability 授权映射
3. conversation binding 决策
4. scope grant 计算
5. Gate 0 的 allow / deny / escalation 判定

### 6.5 runtime -> auth-kernel：Runtime Outcome Event

runtime 在请求结束后应回传 **Runtime Outcome Event**，供审计闭环。

推荐字段：

- `event_id`
- `request_id`
- `decision_ref`
- `runtime_trace_ref`
- `capability_id`
- `result_status`
- `reason_codes`
- `occurred_at`

### 6.6 明确禁止的耦合

runtime 与 `auth-kernel` 之间禁止：

1. 通过 role 名称直接在 runtime 里写业务 if/else
2. 让 runtime 直接读 binding truth 内表
3. 让 `auth-kernel` 输出自然语言 prompt 代替结构化 decision
4. 让 runtime 在没有 `decision_ref` 时继续查数据

---

## 7. runtime <-> data-platform

### 7.1 runtime 如何调用 readiness query

runtime 在 capability access 获得允许后，应先调用 **Capability Readiness Query**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 请求 ID |
| `capability_id` | 目标 capability |
| `service_object_id` | 期望服务对象，可选但推荐带上 |
| `target_scope_ref` | 希望查询的 scope |
| `target_business_date` | 希望读取的业务日期 |
| `freshness_mode` | 如 `latest_usable` / `strict_date` |
| `access_context_envelope` | 标准访问上下文 |
| `runtime_trace_ref` | runtime 追踪引用 |

推荐返回字段：

| 字段 | 说明 |
| --- | --- |
| `readiness_status` | `ready` / `pending` / `failed` / `unsupported_scope` |
| `latest_usable_business_date` | 当前可用业务日期 |
| `reason_codes` | readiness 原因码 |
| `blocking_dependencies` | 未满足依赖 |
| `state_trace_refs` | readiness 追踪引用 |
| `capability_explanation_object` | 可选，直接用于 fallback 说明 |

### 7.2 runtime 如何调用 theme service query

当 readiness 为 `ready` 时，runtime 应通过 **Theme Service Query** 获取默认服务对象。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 请求 ID |
| `service_object_id` | 需要读取的服务对象 |
| `capability_id` | 所属 capability |
| `target_scope_ref` | 目标范围 |
| `target_business_date` | 目标业务日期 |
| `access_context_envelope` | 标准访问上下文 |
| `include_explanation` | 是否同时返回解释对象 |
| `runtime_trace_ref` | runtime 追踪引用 |

推荐返回字段：

| 字段 | 说明 |
| --- | --- |
| `service_status` | `served` / `not_ready` / `scope_mismatch` / `error` |
| `service_object` | 主题服务对象本体 |
| `data_window` | 实际覆盖业务时间范围 |
| `trace_refs` | 对应 facts / state / run 的追溯引用 |
| `explanation_object` | 可选结构化解释对象 |

### 7.3 runtime 可以拿什么、不可以拿什么

runtime **可以拿**：

- `capability_readiness_response`
- `theme_service_response`
- `capability_explanation_object`
- `latest_usable_business_date`
- `data_window`
- `trace_refs`

runtime **不可以拿**：

- source endpoint 名称作为默认调用主语
- raw payload 作为默认回答来源
- canonical facts 物理表名
- ingestion worker 内部状态作为 readiness 替代
- “captured in payload_json” 这类非服务层真相直接冒充 answer-ready 结果

### 7.4 runtime 不应重做的数据判断

runtime 不应重做：

1. `latest usable business date` 计算
2. readiness resolver
3. service object 拼装
4. 数据字段治理判断
5. source window 是否已经就绪的内部判定

### 7.5 明确禁止的耦合

runtime 与 `data-platform` 之间禁止：

1. 直接调用 source endpoint 名称
2. 直接执行事实层 SQL 作为默认路径
3. 把 service query 退化成“把表查出来给我”
4. 在 runtime 中硬编码 store / date fallback 掩盖 readiness 缺口
5. 把 prompt 文本当成 readiness 规则引擎

---

## 8. request lifecycle 详细时序

```text
1. bridge 接到用户请求并完成 ingress normalization
2. bridge 调用 auth-kernel 做 Gate 0
3. auth-kernel 返回 gate decision + access_context_envelope
4. bridge 组装 runtime_request_envelope -> runtime
5. runtime 校验 request envelope
6. runtime 解析 capability route，得到 capability_id / service_object_id
7. runtime 向 auth-kernel 发起 capability access request
8. auth-kernel 返回 access_decision
9. 若 deny / escalation -> runtime 直接组织拒答或升级
10. 若 allow / restricted -> runtime 调用 capability_readiness_query
11. 若 readiness = ready -> runtime 调用 theme_service_query
12. 若 readiness != ready -> runtime 组织 explanation / fallback
13. runtime 返回 runtime_result_envelope 给 bridge
14. bridge 负责最终渠道渲染与投递
15. runtime / data-platform / bridge 回传 outcome / audit event
```

核心要求：

- bridge 之后先有 access truth，再有 runtime 执行
- runtime 里先有 capability route，再有 access decision
- 数据读取前先有 readiness，再有 service
- fallback / escalation 的结构化原因必须保留到最终输出

---

## 9. answer / fallback / escalation 规则

### 9.1 ready 时怎么组织输出

当 `readiness_status = ready` 且 `service_status = served` 时：

1. runtime 以 `service_object` 为主要内容来源
2. runtime 可附带 `data_window` 与必要 explanation fragments
3. runtime 输出结构化 answer fragments，交由 bridge 渲染

### 9.2 pending / failed / unsupported_scope 时怎么走 explanation / fallback

当 `readiness_status` 为：

- `pending`
- `failed`
- `unsupported_scope`

runtime 应：

1. 优先消费 `capability_explanation_object` 或 `reason_codes`
2. 输出结构化 explanation fragments
3. 给出受控 fallback，例如：
   - 建议稍后重试
   - 建议切换到已授权 scope
   - 建议使用另一受支持 capability
4. 禁止虚构答案填补数据空缺

### 9.3 deny / escalation 时怎么处理

当 access 为：

- `deny`
- `escalation`

runtime 应：

1. 不再调用 data-platform
2. 直接消费 `auth-kernel` 的 reason / restriction / obligation
3. 组织拒答或升级输出
4. 如需要，输出 `escalation_action`

---

## 10. 错误归属矩阵

| 场景 | 归属 | runtime 应如何处理 |
| --- | --- | --- |
| 缺失 `access_context_envelope` | bridge / auth 集成错误 | 直接返回 `runtime_error`，不查数据 |
| Gate 0 deny / escalation | auth-kernel | 组织拒答 / 升级，不查数据 |
| capability access deny / restricted / escalation | auth-kernel | 依 decision 组织后续，不重做权限判断 |
| readiness = `pending` / `failed` / `unsupported_scope` | data-platform | 组织 explanation / fallback，不伪造 answer |
| `theme_service_response.service_status = scope_mismatch` | data-platform | 组织 scope mismatch explanation |
| runtime route 无法解析 | runtime | 走 runtime 自身 fallback / 澄清路径 |
| runtime answer 模板缺失或组装失败 | runtime | 返回 `runtime_error`，保留 trace |
| auth/data 接口超时或 transport error | 依赖调用失败，但在 runtime 边界观测到 | 返回 dependency error 视图，不编造成 readiness truth |

规则：

- runtime 负责 **分类与表达**
- 但不应把 `auth-kernel` 或 `data-platform` 的错误改写成新的内核真相

---

## 11. 哪些耦合必须禁止

必须禁止：

1. bridge 持有 capability route 或 fallback 真相
2. runtime 直接理解 source endpoint / physical tables
3. runtime 把 role 名称直接当业务逻辑开关
4. runtime 用 prompt glue 替代 capability registry
5. runtime 把 data-platform 的 readiness 缺口用默认 SQL 或默认日期掩盖
6. runtime 在没有 `decision_ref` 时默认放行
7. `auth-kernel` 用自然语言 prompt 而不是结构化 decision 与 runtime 交互
8. 将 secrets、tokens、cookies 写入公开 spec 或 cross-module payload 示例
