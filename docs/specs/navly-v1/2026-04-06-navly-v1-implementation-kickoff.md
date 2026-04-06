# 2026-04-06 Navly_v1 Implementation Kickoff

日期：2026-04-06  
状态：go-for-implementation  
用途：作为 Navly_v1 从 spec-only 阶段进入 implementation 的总控启动文档

---

## 1. 当前结论

当前 Navly_v1 进入 implementation 的结论是：

> **Go**，但只允许按 contract-first、skeleton-first、milestone-first 的方式启动。

---

## 2. 第一批实现模块

第一批应先启动：

1. `shared-contracts`
2. `data-platform`
3. `auth-kernel`

第二批再启动：

4. `openclaw-host-bridge`
5. `runtime`

`verification` 保持为总控验收基线，不先写业务代码。

---

## 3. 当前 implementation 主规则

1. 先建 repo skeleton，再写逻辑
2. 先冻结 shared contracts，再写跨模块代码
3. 先 Milestone A/B，再谈 richer feature
4. 每个 PR 只写自己的 owning 目录
5. 顶层 README / authoritative source 只由总控窗口收口

---

## 4. 推荐首批 PR 顺序

### PR 1
- `feat/shared-contracts-milestone-a`
- 目标：shared schema seed / interaction seed / enum seed

### PR 2
- `feat/data-platform-milestone-a`
- 目标：`platforms/data-platform/` skeleton + C0 seed

### PR 3
- `feat/auth-kernel-milestone-a`
- 目标：`platforms/auth-kernel/` skeleton + C0/L0/L1 seed

### PR 4
- `feat/openclaw-host-bridge-milestone-a`
- 目标：`bridges/openclaw-host-bridge/` skeleton + interaction alignment

### PR 5
- `feat/runtime-thin-shell-milestone-a`
- 目标：`runtimes/navly-runtime/` skeleton + route/interaction alignment

---

## 5. 不能做的事

- 不允许先写 rich orchestration 主干
- 不允许先写 UI / apps / ops 面
- 不允许绕过 shared contracts 临时定义 cross-module object
- 不允许把 OpenClaw / LangGraph 混入双内核 truth layer

---

## 6. implementation 准入判断

一个模块可以开始写代码，前提是：

- 有专项 spec
- 有 repo structure 文档
- 有 implementation plan
- 共享 contracts 已明确
- 总控未标记 No-Go

---

## 7. 核心结论

Navly_v1 现在已经不是“继续想 spec”的阶段，而是可以进入受控实现阶段；但只能按总控定义的批次、里程碑和 PR 纪律启动。
