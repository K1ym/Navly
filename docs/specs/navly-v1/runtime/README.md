# Navly_v1 thin runtime shell 方案包

日期：2026-04-06  
状态：baseline-for-implementation

本目录是 `Navly_v1` 的 **thin runtime shell 专项正式方案包**。

范围严格限定为：

- `runtime` 本身的模块边界、内部分层、phase-1 落地方案
- `runtime` 与 `auth-kernel`、`data-platform`、`openclaw-host-bridge` 的正式接口边界
- `request lifecycle`、`capability routing`、`answer / fallback / escalation` 的 phase-1 组织方式
- phase-1 最小执行壳需要冻结的共享契约与禁止耦合点

本目录 **不** 负责：

- 数据中台内部事实、状态、readiness resolver、theme service 内部实现
- 权限内核内部 actor / role / scope / conversation / Gate 0 / policy 实现
- Rich orchestration、LLM planner、multi-agent flow、长期记忆、prompt 系统
- 将 private secrets 扩散到公开 spec

---

## 当前前提

1. `openclaw-host-bridge` 是第一接入宿主桥接层，但不是业务真相源，也不是权限真相源。
2. `auth-kernel` 是访问真相源；`data-platform` 是数据与 readiness 真相源；`runtime` 只能消费二者，不能反向定义二者。
3. 当前 phase-1 只要求 **thin runtime shell**：能稳定闭合交互主链路，但不提前引入 rich orchestration。
4. `runtime` 必须通过 `capability_id` / `service_object_id` 工作，不能理解 source endpoint、物理表名或旧 query glue。
5. 公开文档只描述 secret contract，不保存真实 secret 值。

---

## 文档清单

- `2026-04-06-navly-v1-thin-runtime-boundaries.md`
  - `runtime` 的职责边界、4 个核心模块、与 bridge / auth / data 的主责任划分，以及为什么 phase-1 必须先有 thin runtime shell
- `2026-04-06-navly-v1-thin-runtime-internal-layers.md`
  - `runtime` 的内部分层、对象流转、rich orchestration 的后置挂载位与禁止越层规则
- `2026-04-06-navly-v1-thin-runtime-phase-1.md`
  - `runtime` 第一阶段必须闭合的最小 vertical slice、能力优先级、验收标准与延期项
- `2026-04-06-navly-v1-thin-runtime-external-interfaces.md`
  - `runtime` 与 `openclaw-host-bridge`、`auth-kernel`、`data-platform` 的正式接口、request lifecycle、错误归属与禁止耦合点
- `2026-04-06-navly-v1-thin-runtime-target-repo-structure.md`
  - `runtimes/navly-runtime/` 的目标目录骨架、职责与默认读取边界
- `2026-04-06-navly-v1-thin-runtime-implementation-plan.md`
  - `thin runtime shell` phase-1 的可执行 implementation plan、里程碑与 gate

---

## 建议阅读顺序

1. `2026-04-06-navly-v1-thin-runtime-boundaries.md`
2. `2026-04-06-navly-v1-thin-runtime-internal-layers.md`
3. `2026-04-06-navly-v1-thin-runtime-phase-1.md`
4. `2026-04-06-navly-v1-thin-runtime-external-interfaces.md`
5. `2026-04-06-navly-v1-thin-runtime-target-repo-structure.md`
6. `2026-04-06-navly-v1-thin-runtime-implementation-plan.md`
7. `../2026-04-06-navly-v1-design.md`
8. `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
9. `../2026-04-06-navly-v1-naming-conventions.md`
10. `../2026-04-06-navly-v1-shared-contracts-layer.md`
11. `../auth-kernel/README.md`
12. `../data-platform/README.md`
13. `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`

---

## 本方案包的核心判断

`Navly_v1` 在 phase-1 就必须有 `thin runtime shell`，原因不是为了“做复杂编排”，而是为了：

1. 让 `bridge` 不膨胀成业务路由层
2. 让 `data-platform` 不被迫直接承担用户交互表达
3. 让 `auth-kernel` 不被迫携带回答组织逻辑
4. 先把“受控访问上下文 + readiness truth + service object + answer / fallback”闭成最小执行壳
5. 为后续 rich orchestration 预留正确挂载位，而不是再次长回旧式 prompt glue / query glue 层

因此，`runtime` 的正确定位是：

> **建立在 `auth-kernel` 与 `data-platform` 之上的最小交互执行壳。**

它拥有的不是内核真相，而是：

- 一次交互的 capability route
- 一次受保护调用的组织顺序
- answer / fallback / escalation 的表达组织
- runtime 自身的短生命周期 trace 与 outcome

只有这层先成立，`Navly_v1` 的 phase-1 最小 vertical slice 才能闭合而不污染双内核边界。
