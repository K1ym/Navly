# 2026-04-06 Navly_v1 权限与会话绑定内核内部分层方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `auth-kernel` 内部控制层、入口证据层、绑定层、决策层、治理与接口层的分层结构，以及 4 个模块到分层的映射关系

---

## 1. 文档目的

本文档回答：

> 权限内核内部不是只有“鉴权一下再放行”这么粗的两层，而是应当如何按真相边界分层，才能保证入口证据、身份真相、绑定真相、决策真相、治理真相不混淆？

---

## 2. 分层总图

建议采用 **C0 + L0-L3** 的逻辑分层：

```text
C0 权限契约与策略控制层
  -> L0 入口身份与会话证据层
  -> L1 Canonical Actor 与 Binding 层
  -> L2 Gate 0 / Access Decision / Session Control 层
  -> L3 Governance / Audit / External Serving 层
```

其中：

- `C0` 不是运行时决策结果，而是权限内核的元数据、词汇表与策略控制层
- `L0-L3` 是从入口证据逐步收敛到正式授权输出的主链路

---

## 3. 分层原则

### 3.1 每层只表达一种主真相

- `C0`：权限契约与策略控制真相
- `L0`：入口身份与宿主上下文证据真相
- `L1`：canonical actor 与 binding 真相
- `L2`：Gate 0 / access decision / session grant 真相
- `L3`：治理、审计与对外消费真相

### 3.2 原始入口证据必须与 canonical actor 分开

例如：

- WeCom peer id
- host session ref
- workspace ref
- 群聊 thread id

这些都属于 `L0` 证据，不属于 `L1` actor truth。

如果不分开：

- OpenClaw session 会被误当成 actor
- 群聊 thread 会被误当成 conversation truth
- 上层会沿用宿主 id 做永久判断

### 3.3 binding 真相必须与 decision 真相分开

虽然 `binding` 和 `decision` 都属于权限内核，但它们不是同一种真相：

- binding 是“谁被绑定到哪种 role / scope / conversation”
- decision 是“这次入口或能力调用被判定为什么结果”

因此：

- `binding_snapshot` 写入 `L1`
- `gate0_result` / `access_decision` / `session_grant_snapshot` 写入 `L2`

### 3.4 conversation binding 不是 transcript layer

`conversation_binding` 只表达：

- 当前 conversation 引用
- 它绑定到哪个 actor / scope 组合
- 当前 conversation 处于何种授权状态

它不保存：

- 全量聊天记录
- LLM 记忆
- 用户问题语义

这些属于 runtime，而不属于 `auth-kernel`。

### 3.5 上层默认只读 L3

`openclaw-host-bridge`、`runtime`、`data-platform` 默认应消费：

- `L3` 暴露的 `access_context_envelope`
- `L3` 暴露的 decision trace / audit contract
- 或由 `L3` 转发的受控 `L2` 决策结果

而不是直接读取 `L1` / `L2` 物理存储。

---

## 4. 分层总览表

| 层 | 逻辑命名空间（建议） | 拥有的真相 | 主要写入模块 | 主要读取模块 |
| --- | --- | --- | --- | --- |
| C0 | `auth_contract` / `policy_catalog` | identifier namespace、role catalog、scope taxonomy、capability policy、reason taxonomy | 受控治理流、M4 | M1、M2、M3、M4 |
| L0 | `ingress_evidence` | channel identity claim、host session/workspace、conversation candidate、entry trace | bridge 通过 M1/M4 入口 API 写入 | M1、M3、审计工具 |
| L1 | `binding` | actor registry、identity alias、role/scope/conversation binding、binding snapshot | M1、M2 | M3、M4 |
| L2 | `decision` | gate0 result、access decision、session grant、restriction / obligation / escalation | M3 | M4、bridge、runtime |
| L3 | `governance` / `serving` | access context envelope、audit ledger、decision trace、operator review view | M4 | bridge、runtime、data-platform、ops |

---

## 5. C0 权限契约与策略控制层

### 5.1 层职责

C0 负责把 `auth-kernel` 的词汇表、引用约定、能力声明与策略轮廓固定下来，供所有权限层共享。

至少包括：

- identifier namespace registry
- actor type registry
- role catalog
- scope kind taxonomy
- namespaced capability registry
- capability policy profile registry
- restriction / obligation taxonomy
- decision reason taxonomy
- conversation policy profile

### 5.2 这层为什么必须独立

如果没有 C0：

- M1 会自己发明 identity namespace
- M2 会自己发明 role / scope 语义
- M3 会自己在代码里硬写 capability 规则
- M4 会自己拼 reason code 和 envelope 字段

这会让权限内核重新退化为隐式 hardcode。

### 5.3 读写规则

- 只允许受控治理流写入 C0
- bridge / runtime / data-platform 不能直接改写 C0
- M1 / M2 / M3 / M4 只读 C0 或通过受控发布流程更新对应 registry

---

## 6. L0 入口身份与会话证据层

### 6.1 层职责

L0 保存“渠道 / 宿主到底带来了什么身份线索与会话线索”的原始入口证据。

至少包括：

- ingress request envelope
- channel identity evidence
- host session reference
- host workspace reference
- conversation candidate
- entry mode / channel mode
- raw context hash / trace ref

### 6.2 这层的关键价值

L0 的目标不是直接给下游当权限结论，而是：

- 证明 actor 是如何被解析出来的
- 解释 conversation 是如何被绑定出来的
- 支持治理追溯与排错
- 防止宿主上下文被误当长期真相

### 6.3 读写规则

- 只允许 `openclaw-host-bridge` 通过 `auth-kernel` 入口 API 写入 L0
- M1 读取 L0 做 identity normalization
- M3 读取 L0 做 Gate 0 入口检查
- runtime / data-platform 不得直接读取 L0

---

## 7. L1 Canonical Actor 与 Binding 层

### 7.1 层职责

L1 是 `auth-kernel` 的核心绑定真相层。

至少包括：

- `actor_registry`
- `identity_alias_registry`
- `actor_lifecycle_state`
- `role_binding`
- `scope_binding`
- `conversation_binding`
- `binding_snapshot`

### 7.2 这层的边界

L1 负责：

- canonical actor 与 alias 归一
- role / scope / conversation 的显式绑定
- binding 冲突与有效期治理
- 为决策层提供稳定快照

L1 不负责：

- 做最终 access decision
- 输出最终用户可见拒答话术
- 保存对话 transcript 或 LLM memory
- 保存业务数据实体主数据

### 7.3 读写规则

- M1 写 actor / alias / lifecycle
- M2 写 role / scope / conversation binding 与 snapshot
- M3 只读 L1，不反向写 binding truth
- 上层不得绕过 envelope 直接把 L1 当默认接口

---

## 8. L2 Gate 0 / Access Decision / Session Control 层

### 8.1 层职责

L2 负责表达“当前请求到底能不能继续、能以什么限制继续”。

至少包括四类对象：

1. **Gate 0 决策**
   - 入口是否允许进入 Navly 运行时
2. **capability access decision**
   - 某个受保护能力是否允许调用
3. **session grant / restriction / obligation**
   - 当前 session 被授予什么范围、受到什么限制、必须履行什么义务
4. **escalation state**
   - 当前是否需要人工确认、owner 放行或更高安全会话

### 8.2 为什么 decision 属于独立层

如果把 decision 直接混进 binding：

- 历史 binding 与一次性 decision 会混淆
- 无法表达 `allow` 与 `restricted` 的时效差异
- 无法回溯“绑定没变但 decision 变了”的情况

因此：

- binding 固定在 L1
- 每次 decision 固定在 L2

### 8.3 推荐最小对象

- `gate0_result`
- `access_decision`
- `session_grant_snapshot`
- `restriction_set`
- `obligation_set`
- `escalation_ticket`
- `decision_expiry_state`

### 8.4 读写规则

- 只允许 M3 写入 L2
- bridge / runtime 通过受控接口读取 L2 结果
- data-platform 不直接读 L2 物理层，只读 L3 envelope 投影

---

## 9. L3 Governance / Audit / External Serving 层

### 9.1 层职责

L3 是 `auth-kernel` 默认对外消费层。

它把 L0-L2 的内部复杂性收敛成：

- access context envelope
- audit event ledger
- decision trace view
- operator review view
- reconciliation / override view

### 9.2 为什么这层必须独立

如果没有 L3：

- bridge 会直接依赖内部 decision 表结构
- runtime 会直接读取 binding 事实猜授权
- data-platform 会自行定义 access context 形状
- 审计会退化成拼日志

### 9.3 读写规则

- M4 写入 L3
- bridge / runtime / data-platform / ops 只读 L3
- 自然语言话术可消费 L3 的 reason codes，但不能反向写 L3 真相

---

## 10. 模块到分层的映射

| 模块 | 主写层 | 主要读取层 | 说明 |
| --- | --- | --- | --- |
| M1 actor registry / identity normalization | L1 | C0、L0 | 读入口证据和词汇表，写 canonical actor |
| M2 role / scope / conversation binding | L1 | C0、L1 | 读 actor 与策略轮廓，写 binding truth |
| M3 Gate 0 / access decision / policy | L2 | C0、L0、L1 | 读策略、入口证据、binding，写 decision |
| M4 governance / audit / external interfaces | L3 | C0、L0、L1、L2 | 读全链路结果，写治理与对外消费层 |

---

## 11. conversation binding 与 actor / scope binding 的层内协同

推荐协同方式如下：

1. **M1 / L1 先确定 actor**
   - 先知道“是谁”
2. **M2 / L1 再确定 role 与 scope**
   - 再知道“原本能覆盖哪些范围”
3. **M2 / L1 再把 conversation 绑定到 actor + scope snapshot**
   - 再知道“当前会话锚定的是哪个范围 / 是否仍待确认”
4. **M3 / L2 基于该 snapshot 产出 decision**
   - 最后知道“这次到底 allow / deny / restricted / escalation”

关键规则：

- conversation binding **不创建新的 actor 权限**
- conversation binding 可以在已授权 scope 中做**选择、锚定、收窄、挂起**
- 若 conversation 无法安全锚定到唯一 scope，应进入 `pending_scope` 或 `escalation`，而不是交给 runtime 猜

---

## 12. 推荐的上层消费姿势

上层的正确姿势不是：

- 读取 `L1` binding 表猜当前店铺
- 读取 `L2` 决策表猜当前 role 能不能干某事
- 用对话内容倒推 actor 权限

而是：

- bridge 调用 `L3` 发布的 Gate 0 / access envelope 接口
- runtime 调用 `L3` / 受控 `L2` 接口获得 capability decision
- data-platform 只消费 `L3` envelope 并回传 audit event

这样才能保证 `auth-kernel` 成为唯一权限真相源，而不是若干内部表被各层分别“部分理解”。
