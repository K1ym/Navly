# 2026-04-06 Navly_v1 Upstream Integration Policy

日期：2026-04-06  
状态：implementation-baseline  
用途：统一定义 Navly_v1 对各 upstream 的采用方式：直接采用、适配包装、受控复用/裁剪、后置增强、禁止进入内核

---

## 1. 文档目的

本文档回答两个 implementation 前必须冻结的问题：

1. 各模块引用的开源项目，到底是 **直接采用**、**适配包装**，还是 **受控复用/裁剪**
2. 哪些 upstream 明确 **不得进入双内核 truth layer**

---

## 2. 采用方式分类

### 2.1 `direct_adopt`

含义：

- 直接作为运行时依赖或基础设施采用
- 不以 fork / patch upstream 为默认路径
- Navly 只在自己的目录中做配置、封装和适配

适用例子：

- PostgreSQL
- dbt Core
- Temporal
- Hasura
- Cube
- pgvector
- Debezium
- Kafka / Redpanda
- TimescaleDB
- LangGraph

### 2.2 `adapter_wrap`

含义：

- upstream 本身不应直接暴露给业务层
- Navly 通过 adapter / bridge / serving boundary 使用它
- 业务主语义以 Navly contracts 为准，不以上游接口形状为准

适用例子：

- Hasura（站在 `serving/` 之后）
- Cube（站在 semantic serving 之后）
- LangGraph（站在 runtime 之后）

### 2.3 `controlled_reuse`

含义：

- upstream 源码会被明确参考、复用、裁剪或受控集成
- 但 Navly 业务逻辑不回写进 upstream 目录
- 复用的是能力，不是把 upstream 当产品主边界

适用例子：

- OpenClaw

### 2.4 `deferred_enhancement`

含义：

- 当前不进入 phase-1 主链路
- 先保留参考与采用策略
- 真正接入要等对应 truth boundary 先稳定

适用例子：

- Debezium
- Kafka / Redpanda
- TimescaleDB
- LangGraph（rich orchestration 层面）

### 2.5 `forbidden_in_truth_layer`

含义：

- 可以存在于 Navly 整体系统中
- 但明确不能进入 data truth / access truth 本体

适用例子：

- OpenClaw 不能进入 `data-platform` truth layer
- LangGraph 不能进入 `data-platform` / `auth-kernel` truth layer

---

## 3. Upstream 采用矩阵

| Upstream | 当前模块位置 | phase 判断 | 采用方式 | 当前规则 |
| --- | --- | --- | --- | --- |
| PostgreSQL | data-platform | phase-1 核心 | `direct_adopt` | 直接采用，作为 C0-L3 统一 truth substrate |
| dbt Core | data-platform | phase-1 核心 | `direct_adopt` | 直接采用，作为 L1-L3 建模/测试平面 |
| Temporal | data-platform | phase-1 核心 | `direct_adopt` | 直接采用，作为 backfill / rerun / reconcile workflow 平面 |
| GraphQL Engine / Hasura | data-platform | phase-1 可选扩展 | `adapter_wrap` | 可采用，但只能站在 `serving/` 之后 |
| Cube | data-platform | phase-1 可选扩展 | `adapter_wrap` | 可采用，但只能作为 semantic serving 增强 |
| pgvector | data-platform | phase-1 可选扩展 | `direct_adopt` | 可采用，但只作检索增强，不改写 truth |
| Debezium | data-platform | phase-2 / 后续增强 | `deferred_enhancement` | 暂不进入 phase-1 |
| Kafka / Redpanda | data-platform | phase-2 / 后续增强 | `deferred_enhancement` | 暂不进入 phase-1 |
| TimescaleDB | data-platform | phase-2 / 后续增强 | `deferred_enhancement` | 暂不替代 PostgreSQL 主 truth substrate |
| OpenClaw | auth-kernel / openclaw-host-bridge | phase-1 核心（系统层） | `controlled_reuse` | 可参考、复用、裁剪、集成；Navly 业务逻辑不写回 upstream |
| LangGraph | runtime | 后续增强 | `direct_adopt` + `adapter_wrap` | rich orchestration 时可采用，但不进入 kernel truth layer |

---

## 4. 各模块的 upstream 使用规则

## 4.1 data-platform

### phase-1 核心

- PostgreSQL：直接采用
- dbt Core：直接采用
- Temporal：直接采用

### phase-1 可选扩展

- Hasura：适配包装
- Cube：适配包装
- pgvector：直接采用

### 明确禁止

- OpenClaw 不进入 data-platform truth layer
- LangGraph 不进入 data-platform truth layer

### implementation 规则

- 不 fork PostgreSQL / dbt / Temporal 源码
- 所有实现都落在 `platforms/data-platform/`
- 任何 upstream 只可作为手段，不可替代 C0/L0/L1/L2/L3 所有权边界

## 4.2 auth-kernel

### phase-1 核心

- OpenClaw：受控复用其 WeCom / Gateway / Session / Workspace / 宿主语义

### implementation 规则

- 允许参考和受控复用 `upstreams/openclaw/` 中与接入、session、workspace、gateway 相关能力
- 不把 `auth-kernel` 产品逻辑直接写入 `upstreams/openclaw/`
- 不把 OpenClaw session / workspace 当 access truth 本体

## 4.3 openclaw-host-bridge

### phase-1 核心

- OpenClaw：受控复用 / 裁剪 / 集成

### implementation 规则

- bridge 可以引用 OpenClaw host / gateway / hook / tool 承载能力
- bridge 不直接成为 OpenClaw 的 patch dump
- 若必须 patch upstream，应最小化、显式记录、并优先评估能否先在 Navly 侧 adapter 解决

## 4.4 runtime

### phase-1

- 不要求 LangGraph
- 先做 thin runtime shell

### phase-2 / 后续增强

- LangGraph 可作为 rich orchestration 采用

### implementation 规则

- LangGraph 采用方式默认是 `direct_adopt` + `adapter_wrap`
- 运行时逻辑仍以 Navly capability / service / interaction contracts 为主语
- 不允许让 LangGraph graph state 成为 capability / readiness / access 真相

---

## 5. OpenClaw 的特别规则

OpenClaw 是当前唯一明确属于 `controlled_reuse` 的 upstream。

### 5.1 允许的方式

- 参考上游源码
- 复用 host / gateway / session / workspace / tool 承载能力
- 必要时做受控裁剪和受控集成

### 5.2 不允许的方式

- 把 `upstreams/openclaw/` 变成 Navly 业务实现目录
- 在 upstream 目录里持续沉积 Navly 产品逻辑
- 把 OpenClaw 内部对象直接升级成 Navly canonical truth

### 5.3 默认优先级

优先顺序应是：

1. Navly 侧 adapter / bridge 解决
2. Navly 侧 wrapper / contract 解决
3. 必要时才评估 upstream patch

---

## 6. implementation 审核规则

任何实现 PR 只要涉及 upstream，都必须回答：

1. 这个 upstream 属于哪种采用方式
2. 为什么不能只做 adapter / wrapper
3. 是否改动了 upstream 本体
4. 是否把 upstream 对象错误提升为 Navly canonical truth
5. 是否需要在 spec 中同步回写采用方式变化

---

## 7. 核心结论

1. `data-platform` 的 upstream 采用策略已经以 PostgreSQL / dbt Core / Temporal 为 phase-1 核心冻结。
2. OpenClaw 不是黑盒依赖，也不是直接魔改目标，而是 **受控复用 / 裁剪 / 集成来源**。
3. LangGraph 是 runtime 后续增强手段，不是 kernel truth layer 组件。
4. 后续所有实现窗口都应先按本文件判断 upstream 采用方式，再写代码。
