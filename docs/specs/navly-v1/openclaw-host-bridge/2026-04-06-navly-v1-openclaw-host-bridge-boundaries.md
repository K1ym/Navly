# 2026-04-06 Navly_v1 OpenClaw 宿主桥接层模块边界方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `openclaw-host-bridge` 的模块边界、真相边界、读写 contracts、phase-1 优先级与禁止耦合点

---

## 1. 文档目的

本文档回答一个问题：

> `Navly_v1` 的 `openclaw-host-bridge` 应该拥有什么、不应该拥有什么，如何把 OpenClaw 的 gateway / hook / tool / session 能力接到 Navly 双内核与 runtime，而不把 bridge 做成第三内核或新版业务胶水层？

本文档只讨论 `openclaw-host-bridge` 本身，不讨论 `auth-kernel`、`data-platform`、`runtime` 的内部实现。

---

## 2. 模块划分总原则

### 2.1 bridge 必须按“宿主适配真相”拆分，而不是按业务域拆分

`openclaw-host-bridge` 内至少区分四类真相：

1. **host ingress normalization 真相**
2. **auth bridge / session linkage 真相**
3. **capability publication / invocation bridge 真相**
4. **host trace / reply dispatch / diagnostics 真相**

同一模块不能同时持有宿主适配真相和业务真相。

### 2.2 OpenClaw host ref 不是 Navly canonical truth

以下对象在 `Navly_v1` 中都只是宿主证据或宿主承载对象：

- `host_session_ref`
- `host_workspace_ref`
- `host_conversation_ref`
- channel sender / peer id
- host tool call id
- OpenClaw run id

它们不是：

- `actor_ref`
- `scope_ref`
- `session_ref`
- `conversation_ref`
- `decision_ref`
- `capability_id` 的最终语义

### 2.3 bridge 只拥有“适配真相”，不拥有“内核真相”

bridge 拥有的真相只有：

- 宿主入口如何被归一化
- 宿主 session 如何与 Navly 授权 session 建立链接
- 宿主 tool 如何映射到 capability contract
- 宿主 reply / trace 如何被回写和传递

bridge 明确不拥有：

- actor canonicalization 真相
- role / scope / conversation binding 真相
- Gate 0 / access decision 真相
- canonical facts / latest state / readiness / theme service 真相
- Copilot 业务问答逻辑真相

### 2.4 OpenClaw 不是第三内核

判断一个模块是不是内核，关键不在于它是否重要，而在于它是否拥有长期、可审计、不可替代的核心真相。

`openclaw-host-bridge` 不是第三内核，原因有四个：

1. 它持有的是 **宿主适配语义**，不是 Navly 的访问真相或数据真相
2. 它的很多对象都依赖宿主实现细节（gateway、session key、tool publication、reply dispatch），天然可替换
3. 它的状态大多可以从宿主事件与内核输出重建，不应成为最终判定来源
4. 一旦宿主从 OpenClaw 换成别的 host，bridge 可以重写，但 `auth-kernel` 与 `data-platform` 不应因此改写真相语义

结论：

> `openclaw-host-bridge` 是长期需要存在的模块，但它是 **长期适配层**，不是长期真相内核。

### 2.5 OpenClaw 不应成为 Navly 的业务真相源

OpenClaw 提供的是：

- gateway / channel / session 承载
- hooks / tools / skills / bootstrap 机制
- outbound delivery 与 operator control plane

OpenClaw 不提供的是：

- 门店业务 canonical facts
- latest usable business date
- capability readiness
- actor / role / scope / conversation binding 真相
- Copilot 的业务答案口径

因此：

> OpenClaw 在 Navly 中是“承载能力来源”，不是“业务真相来源”。

---

## 3. bridge 的真相边界总览

### 3.1 bridge 拥有的真相

| 真相类别 | 说明 | 是否长期保留 |
| --- | --- | --- |
| host ingress normalization | 如何把 gateway message / hook payload / session resume 统一成 `host_ingress_envelope` | 是 |
| host session linkage | 如何把 `host_session_ref` 与 `decision_ref` / `session_ref` / `conversation_ref` 建立受控链接 | 是 |
| capability publication policy | 哪些 capability 可暴露给 OpenClaw host，以什么 tool 形态暴露 | 是 |
| host reply dispatch | 如何把 runtime 输出转成 OpenClaw reply / send / session update | 是 |
| host trace / diagnostics | 宿主层追踪、dispatch 结果、operator 诊断对象 | 是 |

### 3.2 bridge 不拥有的真相

| 真相类别 | 归属模块 | bridge 的正确姿势 |
| --- | --- | --- |
| actor / identity truth | `auth-kernel` | 只上传证据，不下结论 |
| role / scope / conversation binding truth | `auth-kernel` | 只读取 `binding_snapshot_ref` / `session_ref` / `conversation_ref` |
| Gate 0 / capability decision truth | `auth-kernel` | fail closed，严格执行 |
| canonical facts / latest state truth | `data-platform` | 不直连底层表 |
| readiness / theme service truth | `data-platform` | 只消费受控 contract |
| capability routing / answer composition | `runtime` | 只 handoff，不编排 |
| Copilot 业务问答策略 | `runtime` | 不沉积在 bridge |

### 3.3 读哪些 contracts，写哪些 contracts

| contract / object | bridge 读 / 写 | 主拥有者 | 用途 |
| --- | --- | --- | --- |
| `capability_definition` | 读 | `shared/contracts` | 生成 host-visible capability tool |
| `capability_scope_requirement` | 读 | `shared/contracts` | 限定 tool 输入与 scope hint |
| `capability_service_binding` | 读 | `shared/contracts` | 把 tool 映射到 service / runtime handoff |
| `access_decision` / `gate0_result` | 读 | `auth-kernel` | 在宿主边界执行 allow / deny / restricted / escalation |
| `access_context_envelope` | 读 | `auth-kernel` | 传给 runtime，必要时附加给下游调用 |
| `capability_readiness_response` / `theme_service_response` | 间接读 | `data-platform` | 仅通过 runtime 消费，不直接定义语义 |
| `trace_ref` / `decision_ref` / `state_trace_ref` / `run_trace_ref` | 读 / 透传 | `shared/contracts` / 各模块 | 跨模块追溯 |
| `host_ingress_envelope` | 写 | bridge | 宿主入口归一化对象 |
| `ingress_identity_envelope` | 写 | bridge -> `auth-kernel` | 入口证据提交 |
| `runtime_request_envelope` | 写 | bridge -> `runtime` | 授权后的运行时 handoff |
| `tool_publication_manifest` | 写 | bridge | OpenClaw tool 暴露清单 |
| `host_dispatch_result` / `host_trace_event` | 写 | bridge | 宿主 dispatch / trace |

说明：

- `runtime_request_envelope`、`runtime_result_envelope`、`runtime_outcome_event` 已属于共享 interaction contracts
- `host_ingress_envelope`、`tool_publication_manifest`、`host_dispatch_result` 如需跨模块复用，再提升到 `shared/contracts/host-bridge/` 或 `shared/contracts/interaction/`
- bridge 不得私自扩写 `access`、`readiness`、`service` 的主语义

---

## 4. 四个核心模块总览

```text
OpenClaw Gateway / Hook / Session / Tool host
  -> M1 host ingress normalization
  -> M2 auth bridge / session linkage
  -> M3 capability publication / runtime dispatch
  -> M4 host trace / reply dispatch / diagnostics
  -> OpenClaw host + auth-kernel + runtime + data-platform
```

| 模块 | 拥有的真相 | 主要输入 | 主要输出 | 直接下游 | phase-1 优先级 |
| --- | --- | --- | --- | --- | --- |
| M1 host ingress normalization | 宿主入口归一化真相 | gateway message、hook payload、session resume、channel metadata | `host_ingress_envelope`、`host_message_evidence`、`host_delivery_context`、`host_trace_event` | M2、M4 | P0 |
| M2 auth bridge / session linkage | 宿主证据到授权会话链接真相 | `host_ingress_envelope`、auth contracts、host session refs | `ingress_identity_envelope`、`authorized_session_link`、`gate0_handoff_result` | M3、M4、OpenClaw host | P0 |
| M3 capability publication / runtime dispatch | capability tool 暴露与 runtime handoff 真相 | capability contracts、`authorized_session_link`、runtime shell contract | `tool_publication_manifest`、`capability_tool_binding`、`runtime_request_envelope`、`tool_invocation_bridge_result` | runtime、OpenClaw host、M4 | P0 |
| M4 host trace / reply dispatch / diagnostics | 宿主层追踪、reply dispatch、operator 诊断真相 | M1/M2/M3 输出、runtime result、host delivery receipt | `host_dispatch_result`、`host_trace_event`、`shared_trace_link`、`operator_diagnostic_snapshot` | OpenClaw host、auth-kernel、ops | P0 |

结论：

> 对 `Navly_v1` 的 `openclaw-host-bridge` 来说，四个模块全部是 P0 主链路；区别只在于 phase-1 内部哪些子能力先做、哪些后做。

---

## 5. M1 host ingress normalization 模块

### 5.1 模块职责

M1 负责把 OpenClaw 宿主带来的不同入口形态，统一成 Navly 可消费的宿主入口对象。

它至少负责：

1. 统一 gateway message、command / hook、session resume、tool callback 等入口形态
2. 生成 `request_id`、`ingress_ref`、`host_trace_ref`
3. 保留 channel / account / peer / message / attachment / thread 等宿主证据
4. 形成 `host_delivery_context`，为后续 reply dispatch 提供返回路径
5. 把“收到什么”与“谁有权继续”严格分开

### 5.2 推荐输出对象

- `host_ingress_envelope`
- `host_message_evidence`
- `host_session_link_candidate`
- `host_delivery_context`
- `host_trace_event`

### 5.3 明确不负责的事

M1 不负责：

- actor 解析
- role / scope 判断
- capability 选择
- readiness 判断
- answer 组织

### 5.4 phase-1 优先级

**P0，必须先闭合。**

没有 M1，bridge 就会退化成：

- 不同入口各写一套 if / else glue
- 宿主 message id 与 Navly request_id 混用
- 无法区分 host trace 和 shared trace
- 无法稳定做 Gate 0 前置处理

---

## 6. M2 auth bridge / session linkage 模块

### 6.1 模块职责

M2 负责把 M1 的宿主入口证据送入 `auth-kernel`，并把授权结果挂回宿主会话。

它至少负责：

1. 从 `host_ingress_envelope` 组装 `ingress_identity_envelope`
2. 调用 `auth-kernel` 的 Gate 0 边界
3. 对 `allow / deny / restricted / escalation` 做宿主层 enforce
4. 建立 `host_session_ref` -> `session_ref` / `conversation_ref` / `decision_ref` 的链接对象
5. 在会话切换、scope 选择、resume 时回调 `auth-kernel` 更新 conversation binding

### 6.2 推荐输出对象

- `ingress_identity_envelope`
- `gate0_handoff_result`
- `authorized_session_link`
- `conversation_binding_update_request`

### 6.3 明确不负责的事

M2 不负责：

- 决定 actor canonicalization 的规则细节
- 决定 capability policy
- 决定最终业务答复内容
- 维护 business scope 主数据

### 6.4 phase-1 优先级

**P0，必须先闭合。**

这是 `bridge` 与 `auth-kernel` 的主边界。如果这里不清楚，bridge 很容易变成权限侧逻辑堆积点。

---

## 7. M3 capability publication / runtime dispatch 模块

### 7.1 模块职责

M3 负责把 Navly capability 暴露给 OpenClaw host，并把已授权请求交给 thin runtime shell。

它至少负责：

1. 基于 `capability_definition` 生成 host-visible tool 清单
2. 控制哪些 capability 可发布、哪些只可 runtime 内部调用
3. 把宿主 tool 调用或 message 请求映射到 `runtime_request_envelope`
4. 在需要时补充 capability input normalize，但不改写 capability 主语义
5. 严格禁止把 source endpoint / SQL / internal table 直接暴露给宿主

### 7.2 推荐输出对象

- `tool_publication_manifest`
- `capability_tool_binding`
- `runtime_request_envelope`
- `tool_invocation_bridge_result`

### 7.3 明确不负责的事

M3 不负责：

- capability readiness 计算
- canonical facts 查询
- prompt route / answer composition
- host tool 之外的业务治理逻辑

### 7.4 phase-1 优先级

**P0，必须先闭合。**

bridge 是否会膨胀，关键就看 M3 是否坚持 capability-oriented publication，而不是重新做 source-oriented glue。

---

## 8. M4 host trace / reply dispatch / diagnostics 模块

### 8.1 模块职责

M4 负责宿主层的 reply dispatch、trace 记录与 operator 诊断，而不是业务审计真相本身。

它至少负责：

1. 将 runtime 输出转成 OpenClaw host 可发送的 reply / send / session update
2. 记录 ingress、Gate 0、runtime handoff、tool invocation、dispatch 结果等宿主 trace
3. 将 `decision_ref`、`runtime_trace_ref`、`state_trace_ref`、`run_trace_ref` 关联到宿主 trace
4. 为 operator / runbook 提供 bounded diagnostics
5. 将必要 outcome event 回传 `auth-kernel` 或统一治理面

### 8.2 推荐输出对象

- `host_dispatch_result`
- `host_trace_event`
- `shared_trace_link`
- `operator_diagnostic_snapshot`

### 8.3 明确不负责的事

M4 不负责：

- 改写权限 decision
- 改写数据 readiness
- 保存完整业务答案真相
- 代替 `auth-kernel` / `data-platform` 做最终审计归档

### 8.4 phase-1 优先级

**P0，必须先闭合。**

Navly 需要可审计链路；bridge 不能只会“接消息、发消息”，必须能解释宿主边界发生了什么。

---

## 9. 与其他模块的边界判断

### 9.1 bridge 与 auth-kernel 的边界

- bridge 负责：**收集证据、调用、enforce、挂回引用**
- `auth-kernel` 负责：**身份归一、binding、Gate 0、access decision、governance**

bridge 不能：

- 直接把 OpenClaw session 当 actor
- 自己硬编码 role -> capability 决策
- 只把权限结论写进 prompt，不写 `decision_ref`

### 9.2 bridge 与 runtime 的边界

- bridge 负责：**把授权后的请求交给 runtime，并把 runtime 输出适配回宿主**
- runtime 负责：**选择 capability、组织交互、构造 answer / fallback / escalation**

bridge 不能：

- 自己决定问答策略
- 自己补全 latest business date
- 自己将数据缺口伪装成“差不多能答”

### 9.3 bridge 与 data-platform 的边界

- bridge 默认只读 capability publication metadata 与 trace refs
- 业务数据读取默认走 `runtime -> data-platform`，不是 `bridge -> data-platform`
- bridge 不得直连 raw layer、canonical facts、state tables、projection tables

### 9.4 bridge 与 OpenClaw host 的边界

- OpenClaw host 提供 **承载面与控制面**
- bridge 提供 **Navly 语义归一与 handoff 面**

因此：

- OpenClaw session key 可透传
- Navly `session_ref` 不可由 OpenClaw 直接生成
- OpenClaw tool name 可作为宿主名字
- `capability_id` 必须来自 Navly shared contracts

---

## 10. 明确禁止的耦合

`openclaw-host-bridge` 与其他模块之间必须禁止：

1. 把 OpenClaw session / workspace / peer id 当成 actor 或 scope 真相
2. 在 bridge 中硬编码 role / store / org / capability 业务规则
3. 让 bridge 直接暴露 source endpoint、SQL、internal table 为宿主 tool
4. 让 bridge 直接查询 raw / canonical / state 表作为默认路径
5. 让 bridge 保存 prompt glue、业务问答模板、老路由分支，形成新版 `qinqin2claw`
6. 让 bridge 只用自然语言传递权限或数据状态，而不传 `decision_ref` / `trace_ref`
7. 让 private secret 进入公开 spec、tool description 或 host diagnostics

---

## 11. 核心判断

`Navly_v1` 的 `openclaw-host-bridge` 要成立，关键不是“接上 OpenClaw”，而是：

1. 把宿主证据与 Navly 真相分开
2. 把 host session 与授权 session 分开
3. 把 tool publication 与 capability truth 分开
4. 把 host trace 与 access/data trace 分开
5. 让所有业务真相继续留在 `auth-kernel`、`data-platform`、`runtime`

只有这样，bridge 才是桥；否则它会重新变成一层看起来方便、长期却高债务的第三内核伪装体。
