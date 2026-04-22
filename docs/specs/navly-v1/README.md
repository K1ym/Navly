# Navly_v1 文档包

本目录是 `Navly_v1` 的正式方案入口。

## 当前文件

- `2026-04-12-navly-v1-phase-1-closeout-spec.md`
  - Navly_v1 phase-1 收口规范：把当前 production drift、数据中台缺口、宿主链路缺口和 full closeout 验收门槛收敛成正式执行基线
- `2026-04-06-navly-v1-design.md`
  - Navly_v1 正式方案：定义当前可落地架构、目标架构、双内核边界、upstream 采用策略与版本路线
- `2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
  - Navly_v1 的模块化实现形状、多窗口协作方式与 Vibe Coding 开发流程
- `2026-04-06-navly-v1-naming-conventions.md`
  - Navly_v1 的模块、对象、状态、ID 与文档命名规范
- `2026-04-06-navly-v1-shared-contracts-layer.md`
  - Navly_v1 的公共契约层方案：跨模块共享对象、phase-1 冻结范围与依赖规则
- `2026-04-06-navly-v1-upstream-integration-policy.md`
  - Navly_v1 各 upstream 的统一采用方式：直接采用、适配包装、受控复用、后置增强与禁止进入内核
- `2026-04-06-navly-v1-implementation-kickoff.md`
  - Navly_v1 从 spec-only 进入 implementation 的总控启动文档与首批 PR 规则
- `shared-contracts/`
  - Navly_v1 公共契约层专项目录入口
- `data-platform/`
  - Navly_v1 数据中台专项方案包：模块边界、内部分层、repo structure、phase-1、implementation plan、外部接口、upstream 采用策略
- `auth-kernel/`
  - Navly_v1 权限与会话绑定内核专项方案包
- `openclaw-host-bridge/`
  - Navly_v1 OpenClaw 宿主桥接层专项方案包
- `runtime/`
  - Navly_v1 thin runtime shell 专项方案包：模块边界、内部分层、phase-1、外部接口
- `verification/`
  - Navly_v1 verification / e2e / docs consistency / regression baseline 方案包
- `openclaw-host-bridge/2026-04-12-navly-v1-host-skill-tool-capability-surface.md`
  - Navly_v1 在 OpenClaw / WeCom 宿主中的正式 skill list、tool list 与 `skill -> tool -> capability` 映射
- `openclaw-host-bridge/2026-04-12-navly-v1-permissions-and-agent-responsibility.md`
  - Navly_v1 权限与 OpenClaw agent 的责任分工 spec：谁负责授权真相、谁负责宿主隔离与承载

## 当前建议阅读顺序

1. `2026-04-06-navly-v1-design.md`
2. `2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
3. `2026-04-06-navly-v1-naming-conventions.md`
4. `2026-04-06-navly-v1-shared-contracts-layer.md`
5. `2026-04-06-navly-v1-upstream-integration-policy.md`
6. `2026-04-12-navly-v1-phase-1-closeout-spec.md`
7. `2026-04-06-navly-v1-implementation-kickoff.md`
8. `shared-contracts/README.md`
9. `shared-contracts/2026-04-06-navly-v1-shared-contracts-core-objects.md`
10. `shared-contracts/2026-04-06-navly-v1-shared-contracts-phase-1-freeze.md`
11. `shared-contracts/2026-04-06-navly-v1-shared-contracts-interaction.md`
12. `data-platform/README.md`
13. `auth-kernel/README.md`
14. `openclaw-host-bridge/README.md`
15. `runtime/README.md`
16. `verification/README.md`
17. `data-platform/2026-04-06-navly-v1-data-platform-module-boundaries.md`
18. `data-platform/2026-04-06-navly-v1-data-platform-internal-layers.md`
19. `data-platform/2026-04-06-navly-v1-data-platform-phase-1.md`
20. `data-platform/2026-04-06-navly-v1-data-platform-external-interfaces.md`
21. `auth-kernel/2026-04-06-navly-v1-auth-kernel-module-boundaries.md`
22. `auth-kernel/2026-04-06-navly-v1-auth-kernel-internal-layers.md`
23. `auth-kernel/2026-04-06-navly-v1-auth-kernel-phase-1.md`
24. `auth-kernel/2026-04-06-navly-v1-auth-kernel-external-interfaces.md`
25. `openclaw-host-bridge/2026-04-06-navly-v1-openclaw-host-bridge-boundaries.md`
26. `runtime/2026-04-06-navly-v1-thin-runtime-boundaries.md`
27. `verification/2026-04-06-navly-v1-phase-1-verification-checklist.md`
28. `../../architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
29. `../../api/qinqin/README.md`
30. `../../audits/qinqin/README.md`

## 文档包目标

`Navly_v1` 文档包用于统一说明：

- 当前版本到底要落地什么
- 双内核与上层执行壳的边界
- 模块化实现与多窗口协作流程
- 公共契约层如何冻结跨模块语言
- 各 upstream 应以什么方式被采用
- 数据中台如何作为长期资产成立
- 权限与会话绑定内核如何收口
- OpenClaw 宿主桥接层如何保持为适配层而不是第三内核
- thin runtime shell 为什么在 phase-1 就必须存在
- verification 如何定义 implementation 前的 go / no-go gate
- implementation kickoff 如何启动第一批 PR

## 当前范围

当前文档包聚焦：

- Navly_v1 正式版本设计
- 模块化实现与多窗口协作流程
- 命名规范与公共契约层
- upstream integration policy
- implementation kickoff
- 数据中台
- 权限与会话绑定内核
- OpenClaw 宿主桥接层
- thin runtime shell
- verification / regression baseline
- 架构图与参考栈

后续若进入实施阶段，可继续补充：

- runbooks
- migration docs
- implementation plans
