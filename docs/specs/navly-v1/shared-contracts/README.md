# Navly_v1 / Shared Contracts Specs

本目录存放 `Navly_v1` 的公共契约层专项方案。

## 当前文件

- `2026-04-06-navly-v1-shared-contracts-boundaries.md`
  - 公共契约层的存在必要性、边界、读写规则与治理原则
- `2026-04-06-navly-v1-shared-contracts-core-objects.md`
  - capability / access / readiness / service / trace 的核心共享对象清单
- `2026-04-06-navly-v1-shared-contracts-phase-1-freeze.md`
  - phase-1 必须冻结的对象、字段、枚举与扩展治理规则
- `2026-04-06-navly-v1-shared-contracts-enums-and-trace.md`
  - 主枚举、reason code、trace / audit 规则
- `2026-04-06-navly-v1-shared-contracts-interaction.md`
  - bridge <-> runtime 需要冻结的 interaction contracts

## 目录定位

这里关注的是：

- 双内核、桥接层、运行时之间共享的 contract
- capability / access / readiness / service / trace / interaction 等跨模块稳定对象
- 命名、字段、枚举、引用方式的一致性

这里不负责：

- data-platform 内部事实建模细节
- auth-kernel 内部策略实现细节
- OpenClaw bridge 的宿主接入细节
- Copilot 话术与 prompt 组织

## 建议产出

至少包括：

1. 共享契约层边界
2. 核心共享对象清单
3. phase-1 需要冻结的 contract
4. 与 data-platform / auth-kernel / bridge / runtime 的关系
5. bridge-runtime edge 需要冻结的 interaction contracts

## 相关主文档

- `../2026-04-06-navly-v1-design.md`
- `../2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
- `../2026-04-06-navly-v1-naming-conventions.md`
- `../2026-04-06-navly-v1-shared-contracts-layer.md`
