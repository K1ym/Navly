# Navly_v1 Verification 方案包

日期：2026-04-06  
状态：baseline-for-implementation-gate

本目录是 `Navly_v1` 的 **verification / e2e / docs consistency** 正式方案包。

它不设计新的业务内核，也不替代 `data-platform`、`auth-kernel`、`openclaw-host-bridge`、`thin runtime shell` 的模块方案。
它负责定义：

1. 什么叫边界正确
2. 什么叫 e2e 链路闭合
3. 什么叫 docs / contracts / boundaries 一致
4. phase-1 冻结后哪些对象属于回归基线

---

## 目录定位

本目录验证的对象是：

- `data-platform` 是否只定义 data truth / readiness truth
- `auth-kernel` 是否只定义 access truth
- `openclaw-host-bridge` 是否只是宿主桥接层，而不是第三内核
- `runtime` 是否只做 orchestration / answer organization，而不反向定义 kernel truth
- `shared-contracts`、模块 spec、architecture、api、audits、README 之间是否语义一致

本目录不验证：

- LLM 提示词质量
- 具体代码实现、框架选型或表结构落地方式
- OpenClaw 内部实现细节
- 数据中台和权限内核的内部算法细节
- private secrets

---

## 文档清单

- `2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md`
  - 定义 first usable alpha 的 smoke baseline、当前状态板与它和 full phase-1 的边界
- `2026-04-06-navly-v1-verification-boundaries.md`
  - 定义 verification 的边界对象、真相归属、边界污染识别规则、P0 边界验收线
- `2026-04-06-navly-v1-e2e-acceptance.md`
  - 定义 phase-1 最小闭环链路、e2e 验收步骤、必须可追溯点、必须可解释失败
- `2026-04-06-navly-v1-docs-and-contract-consistency.md`
  - 定义 specs / architecture / reference / api / audits / README 的一致性检查方案与联动更新规则
- `2026-04-06-navly-v1-phase-1-regression-baseline.md`
  - 定义 phase-1 冻结后不可随意漂移的对象、最小回归基线、重新审核触发条件
- `2026-04-06-navly-v1-phase-1-verification-checklist.md`
  - 供总控窗口在 implementation 前使用的 go/no-go checklist

---

## 当前 authoritative documents

本方案包遵守并收口以下主文档：

- `../2026-04-06-navly-v1-design.md`
- `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
- `../2026-04-06-navly-v1-naming-conventions.md`
- `../2026-04-06-navly-v1-shared-contracts-layer.md`
- `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
- `../data-platform/README.md`
- `../data-platform/2026-04-06-navly-v1-data-platform-module-boundaries.md`
- `../data-platform/2026-04-06-navly-v1-data-platform-phase-1.md`
- `../auth-kernel/README.md`
- `../auth-kernel/2026-04-06-navly-v1-auth-kernel-module-boundaries.md`
- `../auth-kernel/2026-04-06-navly-v1-auth-kernel-phase-1.md`
- `../openclaw-host-bridge/README.md`
- `../openclaw-host-bridge/2026-04-06-navly-v1-openclaw-host-bridge-boundaries.md`
- `../runtime/README.md`
- `../runtime/2026-04-06-navly-v1-thin-runtime-boundaries.md`

说明：

- `openclaw-host-bridge` 与 `thin runtime shell` 现在已经拥有独立专项 spec 子目录。
- verification 的 authoritative source 应优先指向这些专项方案包，再向上回链到 design / architecture / shared-contracts 主文档。

---

## 建议阅读顺序

1. `../2026-04-06-navly-v1-design.md`
2. `../../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
3. `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
4. `../2026-04-06-navly-v1-naming-conventions.md`
5. `../2026-04-06-navly-v1-shared-contracts-layer.md`
6. `../data-platform/README.md`
7. `../auth-kernel/README.md`
8. `2026-04-06-navly-v1-verification-boundaries.md`
9. `2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md`
10. `2026-04-06-navly-v1-e2e-acceptance.md`
11. `2026-04-06-navly-v1-docs-and-contract-consistency.md`
12. `2026-04-06-navly-v1-phase-1-regression-baseline.md`
13. `2026-04-06-navly-v1-phase-1-verification-checklist.md`

---

## 本方案包的核心判断

Navly_v1 在多模块并行推进下，最容易失控的不是“某个功能没做完”，而是：

1. 真相归属开始漂移
2. 共享对象开始分叉
3. README 和主入口没有及时回写，导致后续窗口读错 authoritative source
4. e2e 能跑通，但无法解释为什么成功 / 为什么失败

因此，`verification/` 的职责不是补实现，而是：

> 在 implementation 之前，先把边界、契约、追溯链和回归基线冻结成一套统一验收口径。
