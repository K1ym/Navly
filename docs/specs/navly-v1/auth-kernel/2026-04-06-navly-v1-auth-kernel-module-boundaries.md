# 2026-04-06 Navly_v1 权限与会话绑定内核模块边界方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` `auth-kernel` 的 4 个核心模块、模块职责、输入输出、依赖关系、phase-1 优先级与长期资产判断

---

## 1. 文档目的

本文档回答一个问题：

> `Navly_v1` 的权限与会话绑定内核在模块上应该如何拆，哪些模块拥有哪一种权限真相，模块之间如何依赖，才能既复用 OpenClaw / WeCom 接入能力，又不把宿主逻辑误当成权限真相源？

本文档只讨论 `auth-kernel` 本身，不讨论数据中台内部实现，也不讨论 Copilot / LLM 的交互编排实现。

---

## 2. 模块划分总原则

### 2.1 模块必须按“权限真相类型”拆分

`auth-kernel` 内至少区分四类真相：

1. **canonical actor 真相**
2. **role / scope / conversation binding 真相**
3. **Gate 0 / access decision / policy 真相**
4. **governance / audit / external serving 真相**

同一模块不能把这四件事混成一套隐式逻辑。

### 2.2 OpenClaw host session 不是权限真相本身

`OpenClaw Gateway / Session / Workspace` 在 `Navly_v1` 中属于：

- 入口上下文来源
- 宿主承载对象
- 受控集成对象

它们不是：

- actor 真相本身
- role / scope 绑定真相本身
- capability 授权真相本身

因此 `auth-kernel` 必须把“宿主上下文证据”转换成自己的 canonical identity 与 binding truth，而不是直接把 OpenClaw session 当最终答案。

### 2.3 绑定真相与运行时上下文必须分离

属于绑定真相的包括：

- `actor_ref`
- `identity_alias`
- `role_binding`
- `scope_binding`
- `conversation_binding`
- `binding_snapshot`

不属于绑定真相、只属于运行时上下文的包括：

- 当前消息文本
- 当前 websocket connection id
- runtime 推断的临时店铺
- LLM 记忆摘要
- prompt 中写出的“你应该能看这家店”

### 2.4 capability 标识必须统一为 namespaced capability_id

`auth-kernel` 及其外部消费者统一使用 **namespaced capability_id**。

要求：

- capability 不能只用裸名字，如 `store_daily_overview`
- capability 必须带命名空间，以避免 runtime、data-platform、bridge 之间冲突
- 同一 capability 在 registry、decision、audit、envelope 中使用同一标识

当前文档层只冻结一条规则：

> capability 标识统一服从 namespaced `capability_id`。

### 2.5 Gate 0 与 capability decision 必须由内核拥有

`auth-kernel` 必须显式拥有：

- 入口级 `Gate 0`
- capability 级 `access decision`
- `allow / deny / restricted / escalation` 语义
- `reason_code` / `obligation_code` / `restriction_code`

这些不能由：

- OpenClaw bridge 硬编码
- data-platform 逆向推断
- runtime prompt 文本猜测

### 2.6 长期资产与实现手段必须分离表达

Navly 长期保留的是：

- canonical actor id 语义
- binding ledger 语义
- policy registry 语义
- access decision schema
- audit / trace contract
- 外部消费 envelope contract

不是某个具体：

- OpenClaw hook 文件名
- admin 页面写法
- 某次 bootstrap 脚本
- 某个规则引擎库

---

## 3. 四个核心模块总览

```text
WeCom / OpenClaw host evidence
  -> M1 actor registry / identity normalization
  -> M2 role / scope / conversation binding
  -> M3 Gate 0 / access decision / policy
  -> M4 governance / audit / external interfaces
  -> openclaw-host-bridge / runtime / data-platform
```

| 模块 | 拥有的真相 | 主要输入 | 主要输出 | 直接下游 | phase-1 优先级 |
| --- | --- | --- | --- | --- | --- |
| M1 actor registry / identity normalization | canonical actor 真相 | WeCom / OpenClaw identity evidence、受控 actor seed、identifier vocabulary | `actor_registry`、`identity_alias_registry`、`identity_resolution_result`、`actor_lifecycle_state` | M2、M3、M4 | P0 |
| M2 role / scope / conversation binding | binding 真相 | `actor_ref`、role catalog、scope reference contract、conversation context policy | `role_binding`、`scope_binding`、`conversation_binding`、`binding_snapshot` | M3、M4 | P0 |
| M3 Gate 0 / access decision / policy | decision 与 policy 真相 | M1/M2 输出、capability declaration、policy profile、ingress context | `gate0_result`、`access_decision`、`session_grant_snapshot`、`restriction_set`、`escalation_ticket` | M4、bridge、runtime、data-platform | P0 |
| M4 governance / audit / external interfaces | 治理与受控对外消费真相 | M1/M2/M3 输出、下游 access outcome event、override / review event | `audit_event_ledger`、`access_context_envelope`、`decision_trace_view`、`operator_review_view`、external contracts | bridge、runtime、data-platform、ops | P0 |

结论：

> 对 `Navly_v1` 的 `auth-kernel` 来说，四个模块全部是 P0 主链路；区别只在于同一模块内部哪些子能力先做、哪些后做。

---

## 4. M1 actor registry / identity normalization 模块

### 4.1 模块职责

M1 负责把渠道 / 宿主传入的身份线索，收敛成 `Navly_v1` 自己的 canonical actor 真相。

它至少负责：

1. 定义 `actor_ref` 的统一命名和生命周期语义
2. 维护外部标识到 `actor_ref` 的 alias 映射
3. 定义身份归一化规则，避免同一人因多种外部 id 被视为多个 actor
4. 处理 `resolved / ambiguous / unknown / inactive` 等 actor 解析状态
5. 输出后续 binding / decision 可依赖的 canonical actor 引用，而不是让后续模块直接读原始 channel id

### 4.2 输入

| 输入 | 说明 |
| --- | --- |
| WeCom / OpenClaw identity evidence | 例如 `corp`、channel peer、host account、session owner 等入口线索 |
| actor seed registry | 受控初始化或人工纳管的 actor 基础资料 |
| identifier namespace vocabulary | 哪些外部标识类型被允许进入归一化流程 |
| actor lifecycle rules | actor 激活、停用、冻结、人工复核规则 |

### 4.3 输出

推荐最小输出对象：

- `actor_registry`
- `identity_alias_registry`
- `identity_resolution_result`
- `actor_lifecycle_state`
- `identity_normalization_rule_registry`

### 4.4 对下游的约束

- M2 只能绑定 `actor_ref`，不能绑定裸 `wecom_userid` 或 host session id
- M3 只能基于 M1 的解析结果做决策，不能自己再猜 actor
- M4 的审计轨迹必须能回指到 `actor_ref` 与 alias 解析证据

### 4.5 明确不负责的事

M1 不负责：

- 决定 actor 在哪家店有权限
- 决定某 capability 是否允许访问
- 保存聊天内容或对话记忆
- 定义数据平台的业务实体口径

### 4.6 phase-1 优先级

**P0，必须先闭合。**

若没有 M1，系统会退化成：

- 用渠道 id 直接当 actor
- 用 session id 代替 identity
- 同一人多个身份无法归并
- 上层靠 prompt 猜“这大概是谁”

这与 Navly 的长期权限内核目标冲突。

### 4.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| `actor_ref` 语义 | 某次 Excel 导入脚本 |
| alias / normalization contract | 某次人工补录流程 |
| actor lifecycle state | 某个临时同步任务 |
| identity resolution status 语义 | 某个 OpenClaw hook 文件 |

---

## 5. M2 role / scope / conversation binding 模块

### 5.1 模块职责

M2 负责把“这个 actor 在什么角色、什么范围、什么会话里行使权限”变成显式 binding truth。

它至少负责：

1. 维护 `role_binding`，表达 actor 在 Navly 内的权限角色身份
2. 维护 `scope_binding`，表达 actor 可作用的组织 / 门店 / HQ 范围
3. 维护 `conversation_binding`，表达某个会话载体如何绑定到 actor 与 scope
4. 输出一次决策可消费的 `binding_snapshot`
5. 维护 binding 的生效时间、失效时间、来源与治理状态

### 5.2 关键边界

`conversation binding` 的职责不是定义 actor 的根权限，而是：

- 把 actor 已有的 role / scope 绑定锚定到某个 conversation / session 载体中
- 在 conversation 内选择、收窄或等待确认某个 scope
- 记录该会话当前是否处于 `bound / pending_scope / suspended / escalated` 等状态

换言之：

> conversation binding 可以**收窄、锚定、挂起**权限，但不能凭空扩张 actor 原本没有的 scope / capability。

### 5.3 输入

| 输入 | 说明 |
| --- | --- |
| `actor_ref` | 来自 M1 的 canonical actor |
| role catalog | Navly 允许的角色语义与最小权限轮廓 |
| scope reference contract | `org_ref` / `store_ref` / `hq_ref` 等可绑定范围引用 |
| conversation context evidence | 来自 bridge 的会话、群聊、私聊、thread、peer 线索 |
| binding governance rules | 生效期、冲突、优先级、人工复核规则 |

### 5.4 输出

推荐最小输出对象：

- `role_binding`
- `scope_binding`
- `conversation_binding`
- `binding_snapshot`
- `binding_conflict_event`
- `binding_resolution_rule_registry`

### 5.5 对下游的约束

- M3 只能读取 `binding_snapshot` 判断当前能力是否可进入，不能自己拼 role + scope + conversation
- M4 的审计记录必须能指出某个 decision 用的是哪一个 binding snapshot
- runtime 不能绕过 M2 直接在 conversation 内“切店”或“借角色”

### 5.6 明确不负责的事

M2 不负责：

- 定义店铺 / 组织主数据本体
- 输出业务数据过滤结果
- 决定某个能力的最终 allow / deny
- 存放聊天 transcript 或 LLM 记忆

### 5.7 phase-1 优先级

**P0，必须闭合。**

Navly 的权限内核不是“只知道是谁”，还必须知道：

- 他以什么角色访问
- 他能看哪些 scope
- 他当前在哪个 conversation 里行使这些权限

### 5.8 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| `role_binding` / `scope_binding` / `conversation_binding` 语义 | 某个后台表单页面 |
| `binding_snapshot` 语义 | 某次 bootstrap YAML |
| binding 生效期与冲突规则 | 某个临时 reconciliation 脚本 |
| conversation state 语义 | 宿主 session cache 写法 |

---

## 6. M3 Gate 0 / access decision / policy 模块

### 6.1 模块职责

M3 负责把 actor 与 binding 真相变成入口和能力级的正式权限决策。

它至少负责：

1. 在入口边界执行 `Gate 0`
2. 在 capability 调用边界执行 `access decision`
3. 维护 capability policy registry、restriction profile、escalation 触发规则
4. 输出 `allow / deny / restricted / escalation` 四类正式状态
5. 生成带失效时间和 reason code 的 `session_grant_snapshot` / `access_decision`

### 6.2 Gate 0 的边界

`Gate 0` 的主执行边界应当是：

> `openclaw-host-bridge` 完成入口归一化之后、runtime / data-platform / capability 调用之前。

也就是说：

1. bridge 先把渠道消息包装成标准入口 envelope
2. `auth-kernel` 先执行 `Gate 0`
3. 只有在 `allow` 或 `restricted` 下，bridge 才能把请求继续送入 runtime
4. 任何 data-platform 或 runtime capability 的真正调用前，还要通过 M3 的 capability 级 decision

因此：

- `Gate 0` 是入口门
- `access decision` 是受保护能力门
- 两者都属于 `auth-kernel`

### 6.3 access decision 的正式表达

推荐最小枚举：

| 状态 | 含义 | 系统效果 |
| --- | --- | --- |
| `allow` | 允许按当前请求能力与范围继续执行 | 继续，附带标准 envelope |
| `deny` | 明确拒绝，不允许进入下一层 | 立即失败，返回 machine-readable reason |
| `restricted` | 允许继续，但必须收窄 scope / capability / interaction mode | 继续，但带受限授权与 obligation |
| `escalation` | 当前不能自动授予，需要更高权限、人工确认或更安全会话 | 停在授权边界，生成 escalation ticket 或引导 |

推荐最小决策对象字段：

其中 `access_decision_status` canonical 统一为：`allow / deny / restricted / escalation`，不再使用旧的 legacy escalation 状态别名。

- `decision_ref`
- `access_decision_status`
- `request_id`
- `actor_ref`
- `binding_snapshot_ref`
- `conversation_ref`
- `requested_capability_id`
- `granted_capability_ids`
- `granted_scope_refs`
- `restriction_codes`
- `obligation_codes`
- `reason_codes`
- `escalation_ref`
- `issued_at` / `expires_at`

### 6.4 输入

| 输入 | 说明 |
| --- | --- |
| M1 actor resolution | 当前请求的 canonical actor 与生命周期状态 |
| M2 binding snapshot | 当前 role / scope / conversation 的有效绑定快照 |
| capability declaration | 数据能力或 runtime 动作能力的声明 |
| policy profile | 入口、能力、conversation、升级、限制规则 |
| ingress context | 当前入口模式、渠道类型、会话形态等受控上下文 |

### 6.5 输出

推荐最小输出对象：

- `gate0_result`
- `access_decision`
- `session_grant_snapshot`
- `restriction_set`
- `obligation_set`
- `escalation_ticket`
- `decision_reason_taxonomy`

### 6.6 对下游的约束

- bridge 不能绕过 `gate0_result` 直接放行 runtime
- runtime 不能在没有 `decision_ref` 的情况下调用受保护 capability
- data-platform 不能自行根据 role 名推断 capability 访问权
- M4 必须能把下游访问结果回挂到 `decision_ref`

### 6.7 明确不负责的事

M3 不负责：

- 输出最终用户答案文案
- 解释数据为什么 `ready / pending / failed`
- 执行人工审批流程本身
- 保存业务事实或对话内容

### 6.8 phase-1 优先级

**P0，必须闭合。**

若没有 M3，系统表面上虽然“知道是谁、知道在哪个会话”，但仍没有正式权限内核，因为：

- 没有入口门
- 没有 capability 级授权
- 没有标准拒绝 / 受限 / 升级语义

### 6.9 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| `allow / deny / restricted / escalation` 语义 | 某个规则引擎库 |
| `access_decision` schema | 某个 TypeScript service 进程 |
| reason / restriction / obligation taxonomy | 某个 if/else 组合 |
| capability policy registry | 某个管理后台页面 |

---

## 7. M4 governance / audit / external interfaces 模块

### 7.1 模块职责

M4 负责把 `auth-kernel` 的内部真相变成可审计、可追溯、可受控消费的外部表面。

它至少负责：

1. 保存 actor / binding / decision / downstream access 的治理轨迹
2. 输出跨模块使用的 `access_context_envelope`
3. 输出 operator-facing 的 review / trace 视图
4. 维护 override、review、reconciliation 的治理对象
5. 保证上层消费的是正式 envelope，而不是自己猜测权限真相

### 7.2 输入

| 输入 | 说明 |
| --- | --- |
| M1 actor / alias outputs | actor 真相与解析轨迹 |
| M2 binding outputs | 绑定快照与冲突事件 |
| M3 decision outputs | Gate 0 / capability 决策结果 |
| downstream outcome event | bridge、runtime、data-platform 回传的访问使用结果 |
| governance action | 人工复核、override、审批、撤销 |

### 7.3 输出

推荐最小输出对象：

- `audit_event_ledger`
- `decision_trace_view`
- `access_context_envelope`
- `operator_review_view`
- `override_event`
- `governance_reconciliation_report`

### 7.4 对下游的约束

- openclaw-host-bridge、runtime、data-platform 只能消费 `auth-kernel` 发布的 envelope / trace contract
- 下游所有受保护调用都必须携带 `decision_ref` 或 `session_grant_ref`
- 自然语言解释不是权限真相；machine-readable envelope 和 audit trace 才是权限真相消费面

### 7.5 明确不负责的事

M4 不负责：

- 代替 host logs 成为唯一运行日志系统
- 代替数据中台保存业务数据访问结果本体
- 代替 runtime 组织回答话术
- 在公开 spec 中保存 secret

### 7.6 phase-1 优先级

**P0，必须闭合。**

Navly 的权限内核若不可审计、不可对账、不可外部受控消费，就仍然只是“内部实现细节”，不能作为长期真相源。

### 7.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| `access_context_envelope` contract | REST / gRPC / WS 的具体包装 |
| `audit_event_ledger` 语义 | 某个 dashboard |
| decision trace 语义 | 某个导出脚本 |
| governance override / reconciliation 语义 | 某个审计后台页面 |

---

## 8. 权限内核的长期真相到底是什么

`Navly_v1` 的权限内核长期真相，不是“谁的消息从哪个 channel 进来”，而是以下五类对象：

| 真相类别 | 具体内容 |
| --- | --- |
| actor 真相 | `actor_ref`、alias 映射、生命周期状态、解析状态 |
| binding 真相 | `role_binding`、`scope_binding`、`conversation_binding`、`binding_snapshot` |
| policy 真相 | capability 声明、策略轮廓、restriction / escalation / reason taxonomy |
| decision 真相 | `gate0_result`、`access_decision`、`session_grant_snapshot`、失效时间 |
| governance 真相 | 审计事件、override、review、trace refs、外部消费 envelope |

相反，以下内容**不是**权限内核长期真相：

- 单条消息文本
- LLM 推理过程
- runtime 记忆摘要
- OpenClaw 临时 session cache
- 下游根据业务语义猜出来的“可能门店”

---

## 9. 哪些数据属于绑定真相，哪些只是运行时上下文

| 对象 | 归类 | 说明 |
| --- | --- | --- |
| `actor_ref` | 绑定真相 | canonical actor 主键 |
| `identity_alias` | 绑定真相 | 外部身份到 actor 的治理映射 |
| `role_binding` | 绑定真相 | actor 在 Navly 内的角色授权 |
| `scope_binding` | 绑定真相 | actor 可作用的组织 / 门店 / HQ 范围 |
| `conversation_binding` | 绑定真相 | conversation 如何锚定 actor 与 scope |
| `selected_scope_ref`（经内核确认并持久化） | 绑定真相 | conversation 内确认后的目标范围 |
| `host_session_ref` | 运行时上下文 | 宿主提供的会话引用，不等于权限真相 |
| `workspace_ref` | 运行时上下文 | 宿主隔离上下文，不等于授权结果 |
| 用户消息文本 | 运行时上下文 | 交互内容，不是 binding truth |
| runtime 猜测的目标门店 | 运行时上下文 | 未经内核确认前不能当真相 |
| LLM 对角色的自然语言判断 | 运行时上下文 | 永远不能替代 binding truth |

---

## 10. 模块依赖关系

推荐依赖关系如下：

```text
OpenClaw / WeCom ingress evidence
  -> M1 actor registry / identity normalization
  -> M2 role / scope / conversation binding
  -> M3 Gate 0 / access decision / policy
  -> M4 governance / audit / external interfaces

openclaw-host-bridge
  -> 调用 M3 / M4

runtime
  -> 读取 M4 envelope
  -> 再调用 M3 capability decision

data-platform
  -> 只消费 M4 envelope
  -> 回传 M4 audit event
```

### 10.1 强约束

以下依赖必须禁止：

- runtime 直接读取 M1 / M2 内部表来猜权限
- data-platform 直接读取 role 名做业务过滤
- bridge 自己持有 capability policy 真相
- OpenClaw session / workspace 直接被当成 actor 真相
- prompt / 自然语言文本被当成 access decision

---

## 11. 如何保证上层不自己推断权限真相

必须同时满足以下条件：

1. **统一引用**：所有下游都只能拿 `actor_ref`、`conversation_ref`、`decision_ref`、`access_context_envelope`
2. **强制携带**：受保护调用必须带 `decision_ref`，否则 fail closed
3. **机器可读**：允许、拒绝、受限、升级都用结构化状态和 reason code，不用 prompt 文本传递
4. **只读外表面**：上层只读 M4 输出，不读 M1/M2/M3 内部事实
5. **可追溯审计**：任何一次运行时调用都能回追到某个 decision 和 binding snapshot

如果任一上层还需要“自己看 role 名、自己猜 store、自己猜 conversation 归属”，说明 `auth-kernel` 还没有真正收口。
