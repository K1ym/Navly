# 2026-04-06 Navly_v1 权限与会话绑定内核 Phase-1 落地方案

日期：2026-04-06  
状态：phase-1-baseline  
用途：定义 `Navly_v1` `auth-kernel` 第一阶段的闭环范围、模块优先级、交付顺序、验收标准与非目标

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 权限与会话绑定内核第一阶段到底要落成什么，哪些是必须闭环，哪些是长期方向但当前不应假装已经属于 phase-1？

---

## 2. Phase-1 的正式定义

Phase-1 不是“先把 WeCom 接上，再靠运行时自己判断权限”。

Phase-1 的正式定义是：

> 围绕 `WeCom + OpenClaw` 第一接入域，打通“入口身份证据 -> actor 归一化 -> role / scope / conversation binding -> Gate 0 -> capability access decision -> access context envelope -> governance audit”的第一条完整可复用链路，并把它作为所有上层能力的默认权限依赖面。

只有这条链路闭合，`Navly_v1` 的 `auth-kernel` 才算进入可实施状态。

---

## 3. Phase-1 前提假设

### 3.1 接入域范围

当前 phase-1 只覆盖：

- `WeCom + OpenClaw` 作为第一入口域
- `openclaw-host-bridge` 作为宿主桥接层

### 3.2 actor 范围

当前 phase-1 至少覆盖：

- 门店店长 / 店员等人类 actor
- 少量系统 / 服务 actor（如需要做受控后台调用）

当前 phase-1 不要求一次性打通完整企业 IAM / HRIS 主数据。

### 3.3 capability 范围

当前 phase-1 至少覆盖两类能力：

1. `data-platform` 发布的数据读取能力
2. `runtime` 发布的受保护运行时动作能力

### 3.4 scope 假设

当前 phase-1 使用受控 `scope_ref` 契约：

- `store_ref`
- `org_ref`
- `hq_ref`

`auth-kernel` 只绑定这些引用，不在内核里维护业务主数据本体，也不允许硬编码门店 id。

### 3.5 安全假设

当前 phase-1 只在公开文档中描述 secret contract：

- 需要哪些配置
- 哪些属于 secret
- 哪些由运行时注入

公开文档不保存真实 secret 值。

---

## 4. Phase-1 完成态

Phase-1 完成时，至少要成立以下 6 条：

1. 每次入口请求都能形成标准化 ingress envelope，并进入 actor 解析流程
2. 每次请求都能得到 `actor_ref` 或显式的 `unknown / ambiguous / inactive` 结果，而不是让上层猜 actor
3. role / scope / conversation binding 已能形成受治理的 `binding_snapshot`
4. `Gate 0` 与 capability access decision 已能输出 `allow / deny / restricted / escalation`
5. `openclaw-host-bridge`、`runtime`、`data-platform` 默认消费 `auth-kernel` 签发的 envelope，而不是自己推断权限
6. 任意一次下游受保护调用都能追溯到 `decision_ref`、`binding_snapshot_ref` 和对应的治理审计记录

---

## 5. Phase-1 模块优先级矩阵

| 模块 | P0（phase-1 必须） | P1（phase-1 紧随其后） | 延后 |
| --- | --- | --- | --- |
| M1 actor registry / identity normalization | canonical actor id、alias registry、identity resolution status、actor lifecycle | 与更多身份源同步、批量 reconciliation、管理台 | 完整企业目录 / SSO 融合 |
| M2 role / scope / conversation binding | role / scope binding、conversation binding、binding snapshot、生效期与冲突语义 | delegated binding、复杂群聊策略、批量对账 | 层级继承 / 复杂临时授权图 |
| M3 Gate 0 / access decision / policy | Gate 0、namespaced capability registry、allow / deny / restricted / escalation、session grant expiry | 更细 obligation、审批链编排、风险分层 | 通用策略引擎 / 高级风险评分 |
| M4 governance / audit / external interfaces | access context envelope、audit ledger、trace view、下游强制携带 `decision_ref` | operator review UI、对账报表、policy simulation | 完整治理控制台 |

结论：

> 对 `Navly_v1` `auth-kernel` 来说，四个模块全部是 P0 主链路；差别只在同一模块内部哪些子能力先做、哪些后做。

---

## 6. Phase-1 闭环要求

### 6.1 M1：先让 actor 真相成立，再谈绑定和授权

Phase-1 必须先产出：

1. `actor_ref` 规则
2. `identity_alias_registry`
3. `identity_resolution_result`
4. `actor_lifecycle_state`

验收线：

- 任意入口请求都不能直接把 channel id 当 actor 真相
- 任意 unresolved actor 都必须显式进入 `deny` 或 `escalation` 路径，而不是静默放行

### 6.2 M2：先让 binding truth 成立，再让会话继续

Phase-1 必须具备：

1. `role_binding`
2. `scope_binding`
3. `conversation_binding`
4. `binding_snapshot`
5. binding 生效期 / 冲突 / 挂起语义

验收线：

- runtime 不再自己决定“当前是哪个店 / 哪个角色模式”
- conversation 若无法安全锚定 scope，必须停在 `pending_scope` 或 `escalation`

### 6.3 M3：先让 Gate 0 和 capability decision 成立，再谈丰富策略

Phase-1 必须具备：

1. 入口级 `Gate 0`
2. capability 级 `access decision`
3. `access_decision_status` canonical：`allow / deny / restricted / escalation`
4. 不再使用旧的 legacy escalation 状态别名
5. `reason_code` / `restriction_code` / `obligation_code`
6. `session_grant_snapshot` 与 `expires_at`

验收线：

- 受保护调用不能在没有 `decision_ref` 的情况下继续
- `restricted` 必须能明确表达被收窄了什么，而不是模糊“差不多能看”
- `escalation` 必须能明确表达为什么要升级，而不是统一返回“权限不足”

### 6.4 M4：先让外部接口和治理闭环成立，再谈漂亮后台

Phase-1 必须具备：

1. `access_context_envelope`
2. `audit_event_ledger`
3. `decision_trace_view`
4. 下游回传的 access outcome event
5. 基本 override / review 记录

验收线：

- 任意 bridge / runtime / data-platform 访问都能关联到某次 decision
- 权限拒绝与权限受限都能从治理链路中追溯到 binding / policy / reason code

---

## 7. Phase-1 推荐实现顺序

### 里程碑 A：identity + policy vocabulary freeze

目标：

- 固定 actor / alias / role / scope / capability 的基础词汇表
- 固定 `allow / deny / restricted / escalation` 与 reason code 基础枚举

完成标志：

- C0 registry 可以稳定服务 M1 / M2 / M3

### 里程碑 B：actor + binding 闭环

目标：

- 形成 canonical actor 解析
- 形成 role / scope / conversation binding snapshot

完成标志：

- 任意入口请求都能形成 `binding_snapshot` 或显式失败状态

### 里程碑 C：Gate 0 + access decision 闭环

目标：

- 入口先过 Gate 0
- capability 调用先过 access decision
- 产出统一的 decision ref / session grant

完成标志：

- bridge 与 runtime 不再能绕过 M3 直接放行

### 里程碑 D：external interface + governance 闭环

目标：

- data-platform / runtime / bridge 都消费 `auth-kernel` envelope
- 审计、trace、override、outcome event 收口

完成标志：

- 任意一次下游调用都可回溯至 `decision_ref`

---

## 8. Phase-1 推荐最小对象集合

Phase-1 建议至少具备以下正式对象：

- `actor_registry`
- `identity_alias_registry`
- `actor_lifecycle_state`
- `role_binding`
- `scope_binding`
- `conversation_binding`
- `binding_snapshot`
- `capability_registry`
- `gate0_result`
- `access_decision`
- `session_grant_snapshot`
- `restriction_set`
- `obligation_set`
- `escalation_ticket`
- `access_context_envelope`
- `audit_event_ledger`
- `decision_trace_view`

这些对象中，长期资产是：

- 语义与 contract 本身
- 引用关系与追溯关系
- 状态枚举与治理分类

不是：

- 某个表名
- 某个 HTTP API 路径
- 某个 bridge 插件文件

---

## 9. Phase-1 长期资产判断

| 类别 | phase-1 应沉淀为长期资产 | phase-1 只是手段 |
| --- | --- | --- |
| identity | `actor_ref` 语义、alias 规则、解析状态 | 某次导入脚本、某个手工录入页面 |
| binding | `role/scope/conversation binding` 语义、snapshot 规则 | 某次 bootstrap 文件 |
| policy / decision | capability registry、状态枚举、reason / restriction / obligation taxonomy | 某个规则引擎库、某段 if/else |
| governance | `access_context_envelope`、audit / trace contract | 某个 dashboard、导出脚本 |

---

## 10. Phase-1 非目标

当前 phase-1 明确不做：

1. 完整企业 IAM / HRIS / SSO 一次性融合
2. 把 data-platform 的数据过滤或业务规则写进 `auth-kernel`
3. 把 LLM / prompt / orchestration 逻辑混入 `auth-kernel`
4. 让 OpenClaw session / workspace 直接成为权限真相源
5. 高级风险评分、复杂审批引擎、策略模拟平台
6. 在公开 spec 中保存任何真实 secret

这些都可以是后续增强，但不属于当前 phase-1 完整性的定义。

---

## 11. Phase-1 验收标准

### 11.1 actor 验收

- 任意入口请求可解析为 `resolved / ambiguous / unknown / inactive`
- 不再用裸 channel id 作为 actor 真相

### 11.2 binding 验收

- role / scope / conversation 三类 binding 都有正式对象
- `binding_snapshot` 可追溯且有生效期
- conversation 无法安全锚定时会停住，而不是继续猜

### 11.3 decision 验收

- `Gate 0` 在入口边界执行
- capability 调用前必有 `access_decision`
- `allow / deny / restricted / escalation` 四类状态可机器读取

### 11.4 interface / governance 验收

- bridge / runtime / data-platform 默认消费 `auth-kernel` envelope
- 任意受保护调用必须带 `decision_ref`
- 任意访问结果可回追到 `actor_ref`、`binding_snapshot_ref`、`decision_ref`

---

## 12. Phase-1 的关键判断

`auth-kernel` phase-1 的目标不是做一个“差不多能拦一下”的鉴权壳，而是先把以下三件事打穿：

1. **谁在访问**：actor 真相要成立
2. **他在什么绑定里访问**：binding 真相要成立
3. **这次为什么被放行 / 拒绝 / 受限 / 升级**：decision 与 governance 真相要成立

只要这三件事成立，后续 richer policy、审批流、治理台、更多接入域都可以在正确边界上扩展；否则上层只会继续靠宿主逻辑和 prompt 猜权限。
