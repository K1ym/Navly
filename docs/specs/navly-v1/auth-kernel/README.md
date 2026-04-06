# Navly_v1 权限与会话绑定内核方案包

日期：2026-04-06  
状态：baseline-for-implementation

本目录是 `Navly_v1` 的**权限与会话绑定内核专项正式方案包**。

范围严格限定为：

- `auth-kernel` 本身的模块设计、内部分层、phase-1 落地方案
- actor / role / scope / conversation / Gate 0 / access decision / governance 的正式语义
- `auth-kernel` 与 `data-platform`、`openclaw-host-bridge`、`runtime` 的接口边界

本目录**不**负责：

- 数据中台内部事实、状态、readiness、projection 的设计
- Copilot / LLM / orchestration 的提示词、路由、回答编排逻辑
- 把 OpenClaw 宿主逻辑膨胀成权限真相源
- 任何 private secret 的公开化

---

## 当前前提

1. `WeCom + OpenClaw` 是当前第一接入域，但 **OpenClaw 只是宿主 / 接入 / 桥接承载来源**，不是权限真相源本身。
2. `auth-kernel` 是 `Navly_v1` 的权限真相源；`data-platform` 是数据真相源；`runtime` 只能消费二者，不能反向定义二者。
3. `scope` 实体本身的业务主数据不归 `auth-kernel` 所有；`auth-kernel` 拥有的是 **actor 到 scope / conversation / capability 的绑定真相**。
4. 公开文档只描述 secret contract，不保存真实 secret 值。

---

## 文档清单

- `2026-04-06-navly-v1-auth-kernel-module-boundaries.md`
  - `auth-kernel` 4 个核心模块的职责、输入输出、依赖关系、phase-1 优先级与长期资产判断
- `2026-04-06-navly-v1-auth-kernel-internal-layers.md`
  - `auth-kernel` 的控制层、入口证据层、绑定层、决策层、治理与接口层设计，以及模块到分层的映射
- `2026-04-06-navly-v1-auth-kernel-phase-1.md`
  - `Navly_v1` 权限与会话绑定内核第一阶段的闭环范围、交付顺序、验收标准与非目标
- `2026-04-06-navly-v1-auth-kernel-external-interfaces.md`
  - `auth-kernel` 与 `data-platform`、`openclaw-host-bridge`、`runtime` 的正式接口边界、输入输出契约与责任矩阵

---

## 建议阅读顺序

1. `2026-04-06-navly-v1-auth-kernel-module-boundaries.md`
2. `2026-04-06-navly-v1-auth-kernel-internal-layers.md`
3. `2026-04-06-navly-v1-auth-kernel-phase-1.md`
4. `2026-04-06-navly-v1-auth-kernel-external-interfaces.md`
5. `../2026-04-06-navly-v1-design.md`
6. `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
7. `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
8. `../../../reference/navly-v1/open-source-stack/openclaw-local-source.md`

---

## 本方案包的核心判断

Navly_v1 的权限内核不是“渠道 session 管理附件”，而是 Navly 的长期权限真相内核。

因此它必须先把以下五类真相做清楚：

1. **actor 真相**：当前访问主体的 canonical identity 到底是谁
2. **binding 真相**：该 actor 在什么 role / scope / conversation 下被授权或被限制
3. **policy 真相**：某 capability 在什么条件下 allow / deny / restricted / escalation
4. **decision 真相**：某次入口或能力调用到底被如何判定、何时失效、附带什么约束
5. **governance 真相**：上述判定如何被审计、追踪、对账与对外受控消费

进一步地：

- 原始 channel peer id、宿主 session id、workspace id 只是**入口证据**，不是 actor 真相本身
- conversation binding 不是“聊天记录真相”，而是 **actor 如何在某个会话载体中行使既有 scope/capability 的绑定真相**
- Gate 0 的主执行边界是 **openclaw-host-bridge 完成入口归一化之后、runtime / data-platform 之前**
- `capability_id` 统一使用 **namespaced capability_id**，作为跨模块唯一能力标识
- `access_decision_status` canonical 统一为 **`allow / deny / restricted / escalation`**，不再使用 `escalation_required`
- 上层只能消费 `auth-kernel` 签发的 access context / decision ref，不能自己猜 role、scope、store、conversation 或 capability 许可

只有这几类真相分开、闭合、可追溯，`Navly_v1` 的 `auth-kernel` 才算成立。
