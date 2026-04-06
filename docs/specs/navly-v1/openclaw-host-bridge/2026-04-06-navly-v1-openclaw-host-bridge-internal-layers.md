# 2026-04-06 Navly_v1 OpenClaw 宿主桥接层内部分层方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `openclaw-host-bridge` 的内部 C0 + L0-L3 分层、gateway ingress、hook points、session handoff、tool bridge、runtime handoff 与 host trace 设计

---

## 1. 文档目的

本文档回答：

> `openclaw-host-bridge` 内部不应只是“收消息 -> 调 runtime”这样的一层薄壳，而应当如何按宿主适配真相分层，才能保证 gateway ingress、auth bridge、tool bridge、runtime handoff、trace / audit 各自边界清楚？

---

## 2. 分层总图

建议采用 **C0 + L0-L3** 的逻辑分层：

```text
C0 host adapter contracts / publication control
  -> L0 host ingress evidence / hook capture
  -> L1 auth bridge / authorized session linkage
  -> L2 capability bridge / runtime handoff
  -> L3 host dispatch / trace / operator diagnostics
```

其中：

- `C0` 不是运行时状态，而是宿主桥接层的 contract、policy 与 publication 控制层
- `L0-L3` 是从 OpenClaw host 入口一路收敛到 runtime handoff 与 reply dispatch 的主链路

---

## 3. 分层原则

### 3.1 每层只表达一种主真相

- `C0`：host adapter contract 与 publication control 真相
- `L0`：gateway / hook / session / message 的宿主入口证据真相
- `L1`：与 `auth-kernel` 的授权桥接与授权 session linkage 真相
- `L2`：capability tool publication 与 runtime handoff 真相
- `L3`：宿主 dispatch、trace、operator diagnostics 真相

### 3.2 宿主证据必须与 Navly canonical refs 分开

例如：

- `host_session_ref`
- `host_workspace_ref`
- `host_conversation_ref`
- `host_message_ref`
- `channel_account_ref`

这些都属于 `L0` 或 `L3` 的宿主对象，不属于：

- `actor_ref`
- `session_ref`
- `conversation_ref`
- `decision_ref`

### 3.3 Gate 0 前后边界必须清楚

Gate 0 前，bridge 只能：

- 收集证据
- 归一化入口
- 做基础格式校验 / host fail-closed 防护

Gate 0 后，bridge 才能：

- 取得 `decision_ref`
- 取得 `session_ref` / `conversation_ref`
- 将请求 handoff 给 runtime
- 记录授权后的 shared trace link

### 3.4 tool publication 必须独立于 capability semantics

bridge 可以：

- 为 capability 生成 OpenClaw tool surface
- 控制 visibility / operator-only / host labels
- 适配 tool input/output 的宿主包装

bridge 不可以：

- 重写 capability meaning
- 擅自把 source endpoint / SQL / table 暴露出去
- 用 tool description 偷塞业务权限逻辑

### 3.5 host trace 与 shared trace refs 必须分离

`host_trace_event` 记录的是宿主边界发生了什么。

它不是：

- `decision_ref` 本身
- `state_trace_ref` 本身
- `run_trace_ref` 本身

正确做法是：

- 宿主 trace 独立记录
- 同时附上 shared trace refs 作为链接字段

---

## 4. 分层总览表

| 层 | 逻辑命名空间（建议） | 拥有的真相 | 主要写入模块 | 主要读取模块 |
| --- | --- | --- | --- | --- |
| C0 | `host_adapter_contract` / `tool_publication_policy` | host event taxonomy、tool publication policy、host-to-capability binding policy、trace taxonomy | 受控配置 / bridge governance | L0、L1、L2、L3 |
| L0 | `host_ingress` | gateway entry、hook payload、host session candidate、message evidence、delivery context | M1 | M2、M4 |
| L1 | `auth_bridge` | ingress identity handoff、Gate 0 result、authorized session link、conversation update request | M2 | M3、M4 |
| L2 | `capability_bridge` | tool publication manifest、capability tool binding、authorized runtime handoff | M3 | runtime、M4、OpenClaw host |
| L3 | `host_dispatch` / `host_trace` | reply dispatch result、host trace event、shared trace link、operator diagnostics | M4 | OpenClaw host、ops、审计工具 |

---

## 5. C0 host adapter contracts / publication control 层

### 5.1 层职责

C0 负责固定 bridge 的宿主适配词汇表、tool publication policy 与 trace taxonomy。

至少包括：

- `host_event_kind_registry`
- `tool_publication_policy_registry`
- `host_to_capability_binding_registry`
- `host_reply_mode_registry`
- `host_trace_reason_taxonomy`
- `operator_diagnostic_view_policy`

### 5.2 这层为什么必须独立

如果没有 C0：

- L0 会各入口各造事件名
- L1 会自己扩写 ingress identity 字段
- L2 会直接在代码里写 tool 暴露规则
- L3 会各自发明 trace reason 和 operator 视图

bridge 会再次退化成散落 glue 代码。

### 5.3 phase-1 需要冻结的 host-bridge shared contracts

建议在 phase-1 至少冻结以下 bridge 专属跨模块对象：

- `host_ingress_envelope`
- `runtime_request_envelope`
- `tool_publication_manifest`
- `host_dispatch_result`
- `shared_trace_link`

这些对象的落点建议是：

```text
shared/contracts/interaction/   # runtime_request_envelope 等跨模块交接对象
openclaw-host-bridge local      # host_ingress_envelope / tool_publication_manifest / host_dispatch_result 等宿主局部对象
```

注意：

- 只有真正跨模块共享的对象才进入 `shared/contracts`
- 纯宿主局部对象不应过早提升为公共契约
- 它们不能改写 `access`、`readiness`、`service` 的主语义

---

## 6. L0 host ingress evidence / hook capture 层

### 6.1 层职责

L0 保存 OpenClaw host 在入口边界给出的原始宿主证据与归一化入口对象。

至少包括：

- gateway entry evidence
- message ingress evidence
- hook trigger evidence
- host session / workspace / conversation candidate
- reply route / delivery context
- host ingress trace

### 6.2 gateway entry

phase-1 中，bridge 的主入口应优先建立在 OpenClaw 的 gateway ingress 之上，而不是把 HOOK.md 当主聊天链路。

L0 对 gateway entry 的处理要求：

1. 记录 `channel_kind`、`channel_account_ref`、`host_message_ref`
2. 记录 `host_session_ref`、`host_workspace_ref`、`host_conversation_ref`
3. 标记入口模式：`direct_message` / `group_message` / `thread_message` / `command` / `hook`
4. 把 message text、attachment refs、reply context 收敛到统一 envelope

### 6.3 message ingress

message ingress 进入 L0 后，应形成统一的 `host_ingress_envelope`。

建议核心字段：

- `request_id`
- `ingress_ref`
- `host_event_kind`
- `channel_kind`
- `channel_account_ref`
- `host_session_ref`
- `host_workspace_ref`
- `host_conversation_ref`
- `host_message_ref`
- `peer_identity_evidence`
- `message_text`
- `attachment_refs`
- `host_delivery_context`
- `received_at`
- `host_trace_ref`

### 6.4 hook points

OpenClaw 当前 upstream 已提供的 hook 能力主要适合生命周期、bootstrap 与 bounded external ingress，而不是承载 Navly 业务逻辑。

因此 bridge 对 hook points 的原则应是：

#### A. phase-1 可用的 OpenClaw host hooks

- `gateway:startup`
  - 用于 bridge bootstrap、tool publication warmup、registry 健康检查
- `agent:bootstrap`
  - 仅用于注入 bridge 所需的宿主使用说明，不注入业务问答逻辑
- external `/hooks` ingress
  - 用于 bounded external trigger、非聊天入口、系统唤醒，不替代正常 message ingress
- command / session lifecycle hooks
  - 仅用于 session reset / resume 同步，不承载业务流程编排

#### B. bridge 内部应暴露的宿主桥接 hook points

- `host_ingress_received`
- `host_ingress_normalized`
- `gate0_result_received`
- `runtime_handoff_created`
- `host_reply_dispatching`
- `host_reply_dispatched`

用途：

- 便于宿主 trace / diagnostics
- 便于后续运维扩展
- 明确这些是 **桥接生命周期钩子**，不是业务工作流钩子

### 6.5 session handoff 前的证据边界

L0 只能保存：

- `host_session_ref`
- `host_conversation_ref`
- session routing hints
- peer / sender evidence

L0 不能保存：

- 最终 `session_ref`
- 最终 `conversation_ref`
- 最终 `scope_ref`
- capability allow / deny 结果

这些必须等到 L1 调用 `auth-kernel` 后再成立。

---

## 7. L1 auth bridge / authorized session linkage 层

### 7.1 层职责

L1 是 `bridge` 与 `auth-kernel` 的主边界。

至少包括：

- `ingress_identity_envelope`
- `gate0_result`
- `authorized_session_link`
- `conversation_binding_update_request`

### 7.2 收消息后如何调用 auth-kernel

bridge 在收消息后，应按照以下顺序调用 `auth-kernel`：

1. 从 L0 读取 `host_ingress_envelope`
2. 组装 `Ingress Identity Envelope`
3. 调用 `auth-kernel` 入口级 Gate 0
4. 获取 `decision_ref`、`actor_ref`、`session_ref`、`conversation_ref`
5. 在 bridge 内部建立 `authorized_session_link`
6. 再决定是否 handoff 给 runtime

### 7.3 Gate 0 前后边界分工

| 阶段 | bridge 负责什么 | bridge 不得做什么 |
| --- | --- | --- |
| Gate 0 前 | 收集宿主证据、格式校验、生成 request / ingress refs、基础 fail-closed | 猜 actor、猜 scope、猜 capability allow |
| Gate 0 后 | 按 `gate_status` enforce、挂回 `decision_ref` / `session_ref` / `conversation_ref`、把授权结果附到 runtime handoff | 改写 decision、跳过 deny / escalation、自己扩权 |

### 7.4 actor / session / decision refs 的透传

L1 透传原则：

- `actor_ref`：只透传 `auth-kernel` 已确认的 canonical actor
- `session_ref`：只透传 `auth-kernel` 已签发的授权 session
- `conversation_ref`：只透传 `auth-kernel` 已确认的 conversation binding
- `decision_ref`：所有后续受保护调用都必须挂带

L1 不允许透传为正式真相的对象：

- raw peer id
- raw host session key
- role 名称猜测
- group id / thread id 直接当 `scope_ref`

### 7.5 session handoff

L1 的 session handoff 不是“把 OpenClaw session 直接交给 runtime”，而是：

> 把 `host_session_ref` 链接到 `session_ref` / `conversation_ref` / `decision_ref`，让 runtime 在 Navly 授权语义下继续工作。

建议 `authorized_session_link` 至少包含：

- `host_session_ref`
- `host_conversation_ref`
- `session_ref`
- `conversation_ref`
- `decision_ref`
- `binding_snapshot_ref`
- `expires_at`

---

## 8. L2 capability bridge / runtime handoff 层

### 8.1 层职责

L2 负责两个关键动作：

1. 把 Navly capability 暴露成 OpenClaw host 可见工具
2. 把已授权请求交给 thin runtime shell

### 8.2 如何把 Navly capability 暴露为 OpenClaw tools

正确做法是：

1. 读取 `capability_definition`
2. 读取 `capability_scope_requirement`
3. 读取 `capability_service_binding`
4. 结合 `tool_publication_policy_registry` 生成 `tool_publication_manifest`
5. 将 host-visible tool 绑定到 `capability_id`

错误做法是：

- 把 source endpoint 直接暴露成 tool
- 把 SQL 暴露成 tool
- 把 internal table name 暴露成 tool
- 把 capability 语义藏在自由文本 prompt 里

### 8.3 tool contract 如何映射到 shared contracts

推荐映射关系：

| OpenClaw host tool 面 | shared contracts 主语 | 说明 |
| --- | --- | --- |
| tool name / description | `capability_definition` | tool 对外名字来自 capability，而不是 source endpoint |
| tool input schema | `capability_scope_requirement` + service input schema | host 参数是 capability-oriented 输入，不是 SQL / endpoint 参数 |
| tool output schema | `theme_service_response` / runtime result schema | 输出面是 service / explanation，不是 raw payload |
| authorization attachment | `access_context_envelope` / `decision_ref` | 每次调用都必须挂带授权上下文 |
| trace link | `trace_ref` / `state_trace_ref` / `run_trace_ref` | 所有 tool 结果都可追溯 |

### 8.4 如何避免 source endpoint / SQL / internal table 直暴露给宿主

L2 必须坚持以下约束：

1. tool 主语只能是 `capability_id` / `service_object_id`
2. tool 参数只能是 scope / date / freshness / mode / explanation 等受控字段
3. 任何 `source_system`、`endpoint_name`、`table_name`、`sql_text` 都只能出现在内部诊断层，不能出现在默认宿主 tool surface
4. operator-only 诊断工具也不能绕过 shared contracts 主语义

### 8.5 runtime handoff

bridge 应向 runtime 交付 `runtime_request_envelope`，而不是交付一堆宿主原始字段。

建议核心字段：

- `request_id`
- `ingress_ref`
- `decision_ref`
- `actor_ref`
- `session_ref`
- `conversation_ref`
- `access_context`
- `message_payload`
- `attachment_refs`
- `host_delivery_context`
- `host_session_ref`
- `host_trace_ref`

### 8.6 什么属于宿主适配，什么属于 runtime 组织逻辑

| 事项 | bridge | runtime |
| --- | --- | --- |
| OpenClaw session / reply target / thread id 解析 | 负责 | 不负责 |
| Gateway message normalize | 负责 | 不负责 |
| Gate 0 前证据收集与 enforce | 负责 | 不负责 |
| capability route / intent 分解 | 不负责 | 负责 |
| answer composition / fallback wording | 不负责 | 负责 |
| host send / reply / session patch | 负责 | 只返回结构化意图 |
| scope / permission final decision | 不负责 | 不负责，依赖 `auth-kernel` |

---

## 9. L3 host dispatch / trace / operator diagnostics 层

### 9.1 层职责

L3 负责把 runtime 结果安全地适配回 OpenClaw host，并留下宿主边界 trace。

至少包括：

- reply dispatch
- dispatch retry / failure reason
- host trace aggregation
- shared trace refs linkage
- operator diagnostics

### 9.2 bridge 应记录哪些宿主层 trace

bridge 至少应记录以下宿主 trace：

1. `host_ingress_received`
2. `host_ingress_normalized`
3. `gate0_requested`
4. `gate0_resolved`
5. `runtime_handoff_started`
6. `runtime_handoff_completed`
7. `tool_published`
8. `tool_invoked`
9. `host_reply_dispatch_started`
10. `host_reply_dispatch_completed`
11. `host_reply_dispatch_failed`

### 9.3 哪些 trace 只是宿主 trace，哪些要传入 shared trace refs

| 类型 | 示例 | 是否进入 shared refs |
| --- | --- | --- |
| 宿主 trace | `host_session_ref`、OpenClaw run id、host tool call id、delivery receipt id | 否，保留在 bridge / host logs |
| shared trace link | `decision_ref`、`runtime_trace_ref`、`state_trace_ref`、`run_trace_ref` | 是，必须挂链 |
| 混合型链接字段 | `ingress_ref`、`request_id` | 是，用于跨层关联 |

### 9.4 operator diagnostics 的边界

L3 可以提供：

- host route 是否建立
- Gate 0 是否返回
- runtime handoff 是否成功
- dispatch 是否失败
- 关联到哪些 shared trace refs

L3 不可以提供：

- raw secret
- 原始 SQL / internal table 调试入口
- 绕过权限的业务明细

---

## 10. 模块到分层的映射

| 模块 | 主要层 | 次要层 |
| --- | --- | --- |
| M1 host ingress normalization | L0 | C0、L3 |
| M2 auth bridge / session linkage | L1 | C0、L0 |
| M3 capability publication / runtime dispatch | L2 | C0、L1 |
| M4 host trace / reply dispatch / diagnostics | L3 | L0、L1、L2 |

---

## 11. 核心判断

`openclaw-host-bridge` 的正确内部分层，不是为了把桥做厚，而是为了把“宿主证据、授权链接、capability 暴露、runtime handoff、host trace”这五件事清楚切开。

只有切开后，bridge 才能：

- 继续复用 OpenClaw host 能力
- 严格依赖 Navly 双内核与 runtime 的稳定接口
- 保持自己始终是适配层，而不是新的业务真相堆积层
