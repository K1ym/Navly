# 2026-04-06 Navly_v1 thin runtime shell Phase-1 落地方案

日期：2026-04-06  
状态：phase-1-baseline  
用途：定义 `Navly_v1` `thin runtime shell` 第一阶段必须闭合的最小功能、vertical slice、验收标准与延期项

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 的 `thin runtime shell` 在 phase-1 到底要落成什么，为什么这层现在就必须存在，以及哪些 richer orchestration 能力应该明确后置？

---

## 2. Phase-1 的正式定义

Phase-1 不是“先做一个临时问答转发器”。

Phase-1 的正式定义是：

> 围绕 `WeCom + OpenClaw` 第一入口域，打通“bridge ingress -> Gate 0 access context -> capability route -> capability access decision -> readiness query -> theme service query -> answer / fallback / escalation -> bridge delivery”的第一条最小可复用交互链路，并把它作为 Navly 所有后续 richer orchestration 的默认执行骨架。

只有这条链路闭合，`runtime` 才算成立。

---

## 3. 为什么 phase-1 必须先落 thin runtime shell

### 3.1 因为现在就需要一条闭合的用户交互主链路

当前 phase-1 已经明确存在：

- `openclaw-host-bridge`
- `auth-kernel`
- `data-platform`

但这三者加起来，并不能自动完成“交互组织”。

仍然需要一层回答：

- 请求应该进入哪个 capability
- 什么时候查 readiness
- 什么时候查 service
- 什么时候解释、fallback、escalation

这就是 `thin runtime shell`。

### 3.2 因为 bridge 不能代替 runtime

如果 phase-1 没有 runtime，最容易发生的是 bridge 直接长成业务路由器：

- 它开始维护 capability route
- 它开始决定何时 fallback
- 它开始在宿主层堆积 business glue

这与 `bridge` 的宿主适配定位冲突。

### 3.3 因为 rich orchestration 不是 phase-1 的前提，而是后续增强

phase-1 需要的是：

- 正确边界
- 最小执行壳
- 明确 contracts
- 完整 vertical slice

而不是：

- 多代理
- 长链工具规划
- 自由 prompt 推理
- 复杂状态机

所以 runtime 现在就必须出现，但它应是 `thin shell`，不是最终 rich orchestration。

---

## 4. Phase-1 前提假设

### 4.1 接入域范围

当前 phase-1 只覆盖：

- `WeCom + OpenClaw`
- `openclaw-host-bridge` 作为第一宿主桥接层

### 4.2 权限上下文假设

当前 phase-1 假设 bridge 在进入 runtime 前已完成：

- ingress identity evidence 收集
- `auth-kernel` Gate 0 调用
- `access_context_envelope` 与入口 `decision_ref` 获取

runtime 只消费这些结果，不回退去重做 Gate 0。

### 4.3 数据接口假设

当前 phase-1 假设 `data-platform` 至少已对外提供：

- `capability_readiness_query`
- `theme_service_query`
- `capability_explanation_object` 或等价 explanation 输出

### 4.4 能力范围假设

当前 phase-1 至少应覆盖：

- 一个 store 粒度 `capability_id`
- 由它绑定的一个默认 `service_object_id`
- `ready / pending / failed / unsupported_scope` readiness 路径
- `allow / deny / restricted / escalation` access 路径中的核心执行路径

### 4.5 安全假设

当前 phase-1 只在公开文档中描述 secret contract，不保存任何真实 secret 值。

---

## 5. Phase-1 完成态

Phase-1 完成时，至少要成立以下 7 条：

1. bridge 交来的每次请求都能形成标准 `runtime_request_envelope`
2. runtime 能在不理解 endpoint / physical tables 的前提下完成 capability route
3. runtime 在 capability 执行前会显式调用 `auth-kernel` 进行 capability access 决策
4. runtime 在取服务对象前会显式调用 `data-platform` 做 readiness check
5. readiness 为 `ready` 时，runtime 默认通过 `theme_service_query` 读取服务对象，而不是拼事实层
6. `pending / failed / unsupported_scope / deny / escalation` 都有统一的 explanation / fallback / escalation 输出路径
7. 任意一次交互都能回溯到 `request_id`、`decision_ref`、`capability_id`、`service_object_id`、`trace_ref`

---

## 6. Phase-1 功能优先级矩阵

| 能力 | P0（phase-1 必须） | P1（phase-1 紧随其后） | 延后 |
| --- | --- | --- | --- |
| bridge -> runtime 输入 contract | `runtime_request_envelope`、contract validation、response delivery hints | 更多 channel-specific rendering hints | 多渠道统一富媒体抽象 |
| capability route | 显式 capability 调用、受控 route registry、默认 service binding | 更丰富的 slot parsing、更多能力覆盖 | 自由 LLM intent planner |
| auth interaction | capability access request、access decision consume、fail closed | obligation-driven clarification | 高级 policy simulation |
| data interaction | readiness query、theme service query、explanation consume | 细粒度 retry / cache / concurrency control | 跨 capability 自动编排 |
| answer / fallback / escalation | 统一结果 envelope、pending/failed/unsupported_scope/deny/escalation 表达 | 更丰富的 UI fragment、operator handoff metadata | 多步 agent 对话编排 |
| trace / outcome | `runtime_trace_ref`、`runtime_outcome_event`、桥接回传主链路 | 更细粒度 metrics / dashboards | 长期会话记忆 / reasoning transcript |

结论：

> phase-1 的 runtime 不求“聪明”，但必须“边界正确、链路闭合、默认可复用”。

---

## 7. Phase-1 最小 vertical slice

### 7.1 推荐最小 capability slice

推荐至少先闭合一条 store 粒度能力，例如：

- `capability_id`：`navly.store.member_insight`
- `service_object_id`：`navly.service.store.member_insight`

`daily_overview` 可保留为 secondary entry，但不再作为当前最小闭环 canonical slice。

注意：

- runtime 文档不定义 data-platform 内部对象实现
- 这里只要求 runtime 能围绕 `capability_id` / `service_object_id` 闭合请求链路

### 7.2 这条 slice 至少要走通的路径

```text
1. user request
2. bridge ingress normalization
3. auth Gate 0
4. runtime request acceptance
5. capability route
6. capability access decision
7. readiness query
8. theme service query 或 explanation path
9. answer / fallback / escalation
10. bridge delivery
```

### 7.3 必须覆盖的状态分支

至少覆盖：

- `ready` -> answer
- `pending` -> explanation + fallback
- `failed` -> explanation + fallback / escalation suggestion
- `unsupported_scope` -> explanation + scope correction suggestion
- `deny` -> access refusal
- `escalation` -> access escalation

这样才能证明 runtime 真正闭合了“交互壳”，而不是只在 happy path 上跑通一个 demo。

---

## 8. Phase-1 推荐实现顺序

### 里程碑 A：shared contracts + bridge-runtime edge freeze

目标：

- 冻结 `runtime_request_envelope`
- 冻结 `runtime_result_envelope`
- 冻结 `runtime_outcome_event`
- 对齐 `capability_id` / `service_object_id` / `access_context_envelope`

完成标志：

- bridge、runtime、auth、data 对主语一致

### 里程碑 B：route + auth guard 闭环

目标：

- runtime 能消费 request envelope
- runtime 能产出 `capability_route_result`
- runtime 能调用 capability access request

完成标志：

- 没有 capability access decision 就无法继续执行

### 里程碑 C：readiness + service 闭环

目标：

- runtime 能先做 readiness，再做 service
- runtime 能消费 explanation object

完成标志：

- 不再通过事实表 / SQL / endpoint 默认读取数据

### 里程碑 D：answer / fallback / escalation 闭环

目标：

- 统一 `runtime_result_envelope`
- 统一错误归属与用户表达
- 统一 bridge delivery 对接

完成标志：

- happy path 与非 ready path 都通过统一 runtime 结果输出

---

## 9. Phase-1 建议冻结的最小对象集合

### 9.1 来自 shared contracts 的对象

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

### 9.2 runtime 内部对象

- `runtime_interaction_context`
- `capability_route_result`
- `runtime_execution_plan`
- `runtime_dependency_outcome`
- `answer_fragment_set`

规则：

- 跨模块传递的对象优先进入 `shared/contracts`
- 只在 runtime 内部使用的对象留在 runtime 模块内

---

## 10. Phase-1 明确非目标

当前 phase-1 明确不做：

1. multi-agent orchestration
2. LangGraph / DAG planner 作为主干依赖
3. 通用自然语言 query planner
4. 直接基于 prompt 生成业务路由
5. runtime 自己拼 canonical facts
6. runtime 自己决定权限范围
7. 长期会话记忆、长期用户画像、长期工具状态
8. 将 private secrets 写入公开 spec

这些都可以是后续增强，但不属于 phase-1 完整性的定义。

---

## 11. Phase-1 验收标准

### 11.1 边界验收

- `bridge` 不再承担 capability route 主逻辑
- `runtime` 不直接读 raw layer / canonical facts
- `runtime` 不直接做 Gate 0 或 actor resolution

### 11.2 路由验收

- 至少一条 capability route 走通
- route 结果可稳定映射到 `service_object_id`
- route unresolved 时走 fallback，而不是盲查

### 11.3 执行验收

- capability access request 必须发生
- readiness query 必须先于 service query
- `ready / pending / failed / unsupported_scope` 都有结构化结果

### 11.4 输出验收

- 所有路径最终都返回统一 `runtime_result_envelope`
- `decision_ref`、`capability_id`、`trace_ref` 在输出中可追溯
- bridge 可仅靠 `runtime_result_envelope` 完成渠道投递，而不需要补写业务逻辑
