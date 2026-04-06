# Navly_v1 OpenClaw 宿主桥接层方案包

日期：2026-04-06  
状态：baseline-for-implementation

本目录是 `Navly_v1` 的 **OpenClaw 宿主桥接层（`openclaw-host-bridge`）专项正式方案包**。

范围严格限定为：

- `openclaw-host-bridge` 本身的模块边界、内部分层、phase-1 落地方案
- `OpenClaw host` 的 gateway / hook / tool / session 能力，如何接到 `auth-kernel`、`runtime`、`data-platform`
- 宿主 ingress、Gate 0 前后边界、tool capability 暴露、runtime handoff、宿主 trace / audit 的正式语义
- `openclaw-host-bridge` 需要读取和写出的 shared contracts 边界

本目录 **不** 负责：

- `auth-kernel` 内部的 actor / role / scope / conversation / Gate 0 真相实现
- `data-platform` 内部的 canonical facts / latest state / readiness / theme service 实现
- `runtime` 内部的 capability route、回答编排、prompt、LLM orchestration 细节
- 把 OpenClaw upstream 源码目录变成 Navly 产品逻辑目录
- 任何 private secret 的公开化

---

## 当前前提

1. `OpenClaw` 在 `Navly_v1` 中只承担 **宿主 / 接入 / session / tool 承载能力**，不是权限真相源，也不是数据真相源。
2. `auth-kernel` 是访问真相源；`data-platform` 是数据与可答真相源；`runtime` 负责交互组织；`openclaw-host-bridge` 只负责适配与 handoff。
3. `openclaw-host-bridge` 默认消费 `shared/contracts`；bridge <-> runtime 的公共交接对象优先进入 `shared/contracts/interaction/`，其余纯宿主局部对象如需跨模块复用再评估是否单列 `shared/contracts/host-bridge/`。
4. `upstreams/openclaw/` 是可参考、可裁剪、可受控集成的上游源码，不是 Navly 业务实现目录。
5. 公开 spec 只描述 secret contract，不保存真实 secret 值。

---

## 文档清单

- `2026-04-06-navly-v1-openclaw-host-bridge-boundaries.md`
  - `openclaw-host-bridge` 的模块边界、真相边界、读写 contracts、禁止耦合与“为什么它不是第三内核”
- `2026-04-06-navly-v1-openclaw-host-bridge-internal-layers.md`
  - `openclaw-host-bridge` 的 C0 + L0-L3 分层、gateway ingress、hook points、session handoff、tool bridge、runtime handoff、host trace 设计
- `2026-04-06-navly-v1-openclaw-host-bridge-phase-1.md`
  - `Navly_v1` 第一阶段必须闭合的宿主桥接链路、交付顺序、验收标准、后续增强与非目标
- `2026-04-06-navly-v1-openclaw-host-bridge-external-interfaces.md`
  - `openclaw-host-bridge` 与 `OpenClaw host`、`auth-kernel`、`runtime`、`data-platform` 的正式接口边界与对象约定

---

## 建议阅读顺序

1. `2026-04-06-navly-v1-openclaw-host-bridge-boundaries.md`
2. `2026-04-06-navly-v1-openclaw-host-bridge-internal-layers.md`
3. `2026-04-06-navly-v1-openclaw-host-bridge-phase-1.md`
4. `2026-04-06-navly-v1-openclaw-host-bridge-external-interfaces.md`
5. `../2026-04-06-navly-v1-design.md`
6. `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
7. `../2026-04-06-navly-v1-naming-conventions.md`
8. `../2026-04-06-navly-v1-shared-contracts-layer.md`
9. `../auth-kernel/README.md`
10. `../data-platform/README.md`
11. `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
12. `../../../reference/navly-v1/open-source-stack/openclaw-local-source.md`
13. `../../../../upstreams/openclaw/docs/concepts/architecture.md`
14. `../../../../upstreams/openclaw/docs/concepts/session.md`
15. `../../../../upstreams/openclaw/docs/gateway/protocol.md`

---

## 本方案包的核心判断

`Navly_v1` 的 `openclaw-host-bridge` 不是第三内核，而是 **宿主桥接 / 适配层**。

因此它必须先把以下五类边界做清楚：

1. **host ingress truth**：OpenClaw 宿主到底带来了什么 channel / message / hook / session 证据
2. **auth bridge truth**：这些宿主证据如何被送入 `auth-kernel`，以及 `decision_ref` / `session_ref` / `conversation_ref` 如何被挂回宿主会话
3. **capability publication truth**：哪些 Navly capability 可以被暴露为 OpenClaw tools，以什么契约暴露，而不是暴露 source endpoint / SQL / internal table
4. **runtime handoff truth**：已授权请求如何交给 thin runtime shell，桥接职责与 runtime 组织职责如何切开
5. **host trace truth**：宿主层到底记录哪些 trace，哪些 trace 只属于宿主，哪些必须回链到 shared trace refs

进一步地：

- `host_session_ref`、`host_workspace_ref`、`channel peer` 只是 **宿主证据与承载引用**，不是 `actor_ref`、`session_ref`、`conversation_ref` 真相本身
- `OpenClaw tool` 只是宿主调用面，不是 capability 真相本身
- `bridge` 只能做 **normalize / route / enforce / relay / dispatch**，不能做业务权限猜测、数据口径拼接、问答业务胶水沉积
- phase-1 的正确目标不是“把 OpenClaw 接上就算完”，而是打通 **host ingress -> auth-kernel -> thin runtime shell -> data-platform serving -> host reply dispatch -> trace/audit** 的完整闭环

只有这样，`openclaw-host-bridge` 才会成为 Navly 的长期可替换宿主适配层，而不会膨胀成“新版 qinqin2claw”。
