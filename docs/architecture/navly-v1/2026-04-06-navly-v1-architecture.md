# 2026-04-06 Navly_v1 架构文档

日期：2026-04-06  
状态：baseline-aligned  
用途：定义 Navly_v1 的结构分层、系统边界、当前落地子集、目标蓝图与图示使用方式

---

## 1. 文档目的

本文档回答的是“Navly_v1 在结构上应该长什么样”。

它与正式方案文档分工如下：

- `docs/specs/navly-v1/2026-04-06-navly-v1-design.md`
  - 定义版本目标、upstream 采用策略、阶段路线与验收标准
- `docs/specs/navly-v1/2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
  - 定义模块化实现形状、多窗口协作方式与 Vibe Coding 开发流程
- 本文档
  - 定义系统边界、分层结构、图示定位与当前/目标两种架构视图

---

## 2. Navly_v1 的架构判断

Navly_v1 不是旧业务问答系统的延长线。

它应该被建成一个：

> 以数据中台和权限/会话绑定内核为长期基础、以上层智能执行层为可替换产品层的双内核系统。

因此，Navly_v1 的结构核心不是“问答流程”，而是两个内核：

1. **数据中台内核**
2. **权限与会话绑定内核**

上层 Copilot、智能执行、编排、解释、预测都建立在这两个内核之上。

---

## 3. 当前可落地架构

### 3.1 当前可落地主链路

```text
WeCom User
  -> WeCom Channel
  -> OpenClaw Gateway / Adapter
  -> Permission Kernel
       - actor / role / scope / conversation binding
       - Gate 0
       - governance / audit
  -> Execution Shell
       - capability routing
       - answer composition
       - fallback / escalation
  -> Data Platform Serving
       - theme / projection objects
       - completeness / readiness
       - canonical facts
       - raw replay / audit
```

### 3.2 分层说明

#### A. 用户与接入层

包含：

- 店长 / 店员
- 企业微信 WeCom
- OpenClaw WeCom Adapter
- OpenClaw Gateway

职责：

- 接受输入
- 形成会话入口
- 把请求送入权限与会话绑定内核

#### B. 权限与会话绑定内核

包含：

- actor identity
- role binding
- scope binding
- conversation binding
- Gate 0 access control
- governance / audit trail

职责：

- 决定“谁在什么范围、什么会话、什么能力入口下可以继续往前走”
- 输出上层执行可消费的受控上下文

#### C. 智能执行壳层

包含：

- capability selection
- answering orchestration
- fallback / escalation
- 轻量工具与技能调用

职责：

- 组织一次交互
- 选择 capability
- 读取双内核的稳定输出
- 产出回答或拒答解释

关键限制：

- 不能自己成为数据真相源
- 不能自己成为权限真相源
- 不能继续承接旧业务问答胶水作为永久基础

#### D. 数据中台内核

包含：

- L0 原始层
- L1 标准事实层
- L2 状态 / 质量 / completeness 层
- L3 projection / theme / serving 层

职责：

- 原始数据保真
- 事实建模
- 最新可用状态表达
- answer readiness 表达
- 稳定服务对象产出

---

## 4. 当前架构的关键边界

### 4.1 数据中台负责什么

数据中台负责：

- `Qinqin` 等输入域的原始与结构化真相
- 字段治理
- 全门店 / 全历史回溯
- 历史执行事实与最新可用状态
- completeness / readiness
- 主题与 projection 输出

数据中台不负责：

- 用户身份判定
- 会话入口控制
- 上层回答措辞

### 4.2 权限与会话绑定内核负责什么

权限内核负责：

- actor / role / scope / conversation
- Gate 0
- access decision
- 治理与访问审计

权限内核不负责：

- 数据事实口径
- projection 结果
- 业务指标解释

### 4.3 上层执行壳负责什么

上层执行壳负责：

- 编排一次交互
- 选择一个或多个 capability
- 读取 readiness 与 projection
- 输出答案或拒答原因

上层执行壳不负责：

- 直接拼装事实层
- 绕过 readiness 判断
- 隐式写死 tenant / store / route / permission 逻辑

---

## 5. 当前态与目标态

### 5.1 当前态

当前态追求的是一个 **结构正确的可运行骨架**。

它必须优先闭合：

1. Qinqin 输入真相源
2. 数据中台 L0-L3 主链路
3. OpenClaw 权限/会话绑定主链路
4. 上层执行壳对双内核的稳定依赖

当前态不要求一次性引入全部增强组件。

### 5.2 目标态

目标态在不破坏双内核的前提下继续扩展：

1. 更强的 semantic serving
2. 更复杂的 agent / workflow orchestration
3. 实时事件驱动能力
4. 预测与推荐能力
5. 更完整的观测与治理体系

### 5.3 当前态与目标态的边界原则

当前态和目标态的关系不是“先凑合，后重做”，而是：

- 当前态先把边界做对
- 目标态在正确边界上扩容

这也是为什么：

- 旧业务问答链路不能再充当架构骨架
- 所有增强能力都只能挂载在双内核之上

---

## 6. 图示使用方式

### 6.1 交互时序图

文件：

- `docs/architecture/navly-v1/diagrams/navly-v1-interaction-sequence.svg`

适合说明：

- 一次用户交互如何经过 WeCom、Gateway、执行层与数据中台

不适合说明：

- 当前第一阶段哪些组件是硬前置

### 6.2 数据中台核心架构图

文件：

- `docs/architecture/navly-v1/diagrams/navly-v1-data-platform-core.svg`

适合说明：

- Navly_v1 的主结构重心在数据中台
- 目标结构如何围绕数据治理、建模、服务、观测展开

必须补充说明：

- 该图是“结构主图”，不是“第一阶段全部必上清单”

### 6.3 目标全景蓝图图

文件：

- `docs/architecture/navly-v1/diagrams/navly-v1-target-blueprint.svg`

适合说明：

- 目标态全景蓝图
- 长期增强路线

不适合说明：

- 当前第一阶段的最小正确落地子集

---

## 7. upstream 在架构中的位置

### 7.1 第一阶段架构核心

第一阶段真正构成架构核心的 upstream 是：

- OpenClaw
- PostgreSQL
- dbt Core
- Temporal

### 7.2 第一阶段可选扩展

第一阶段可选扩展 upstream：

- Cube
- GraphQL Engine（Hasura）
- pgvector
- LangGraph

这些组件都合理，但不应把它们误写成“双内核成立的前提”。

### 7.3 后续增强

后续增强 upstream：

- Debezium
- Kafka
- Redpanda
- TimescaleDB
- Prophet
- LightGBM
- Langfuse
- OpenMetadata
- OpenTelemetry Collector
- Mem0
- Redis

它们主要服务于实时、预测、治理、观测、长期记忆等增强面。

---

## 8. 推荐阅读入口

建议阅读顺序：

1. `docs/specs/navly-v1/2026-04-06-navly-v1-design.md`
2. `docs/specs/data-platform/2026-04-06-navly-data-middle-platform-design.md`
3. `docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
4. `docs/reference/navly-v1/open-source-stack/2026-04-06-navly-open-source-dependencies.md`
5. `docs/reference/navly-v1/open-source-stack/openclaw-local-source.md`
6. `docs/api/qinqin/README.md`
7. `docs/audits/qinqin/README.md`

---

## 9. 一句话定义

> Navly_v1 的正确架构形状，是双内核稳固、上层可替换，而不是旧业务问答链路继续占据系统中心。
