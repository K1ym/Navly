# 2026-04-06 Navly_v1 模块化开发与 Vibe Coding 流程

日期：2026-04-06  
状态：baseline-for-collaborative-implementation  
用途：定义 Navly_v1 的模块化实现形状、多窗口协作方式与 Vibe Coding 开发流程

---

## 1. 文档目的

本文档补充 `Navly_v1` 正式方案中的实现侧思考。

它重点回答：

1. `Navly_v1` 在实现上应该拆成哪些模块
2. 哪些模块是长期真相源，哪些只是宿主、执行或运行平面
3. 多个 Codex 窗口如何并行设计和并行开发
4. 所谓 `vibe coding` 在 Navly 中到底应该是什么工作法，而不是什么工作法

配套主文档：

- `docs/specs/navly-v1/2026-04-06-navly-v1-design.md`
- `docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md`

---

## 2. Navly_v1 的模块化判断

### 2.1 两个长期内核

`Navly_v1` 的长期内核只有两个：

1. **数据中台内核**
2. **权限与会话绑定内核**

它们分别回答：

- 数据中台：**数据是什么、状态如何、能不能答、为什么能答/不能答**
- 权限内核：**你是谁、你能看什么、你能做什么**

### 2.2 OpenClaw 不是第三内核

OpenClaw 在 `Navly_v1` 中的正确定位不是第三内核，而是：

> **宿主桥接与接入承载层**

它负责：

- 接消息
- 维护宿主会话
- 暴露工具
- 把 Navly capability 接入宿主

它不负责：

- 数据真相
- 权限真相
- 业务能力真相

### 2.3 LLM / 编排层不是内核

LLM、LangGraph、multi-agent flow、skills runtime 都属于：

> **智能执行运行时**

它负责“怎么推理、怎么组织一次交互”，但不负责定义底层真相。

因此：

- kernel 里不要有 LLM 真相
- LLM / 编排层只能消费内核，不能反向定义内核

---

## 3. 推荐模块划分

建议将 `Navly_v1` 划分为 **6 个核心模块 + 1 个参考层 + 1 个公共契约层**。

### 3.1 核心模块 1：数据中台内核

建议名称：

- `data-platform`

职责：

- Qinqin API 接入
- 原始层
- 标准事实层
- sync state
- completeness
- projection / serving
- 全历史回溯
- 字段治理

### 3.2 核心模块 2：权限与会话绑定内核

建议名称：

- `auth-kernel`

职责：

- actor registry
- role binding
- scope binding
- conversation binding
- Gate 0
- 治理 / 审计

### 3.3 核心模块 3：OpenClaw 宿主桥接层

建议名称：

- `openclaw-host-bridge`

职责：

- 收消息时调用 `auth-kernel`
- Agent / tool 调用时连接 `data-platform`
- 把 Navly capability 暴露成 OpenClaw tools
- 通过 gateway / hook / tool method 接入 OpenClaw

约束：

- 它是适配层，不是 kernel

### 3.4 核心模块 4：智能执行运行时

建议名称：

- `agent-runtime`
- 或 `orchestration-runtime`

职责：

- thin runtime shell
- capability route
- LangGraph orchestrator
- multi-agent flow
- skills runtime
- 回答组织、解释、fallback、escalation

注意：

- 第一阶段必须先有 **thin runtime shell**
- 更复杂的 rich runtime / orchestration 可后续增强

### 3.5 核心模块 5：渠道与应用入口层

建议名称：

- `apps`
- `channels`

职责：

- WeCom 入口
- 未来 Web / Admin / Ops 入口
- 面向用户的可运行应用

第一阶段收口：

- 以 `WeCom + OpenClaw` 为主
- 其余入口默认后置

### 3.6 核心模块 6：运行与治理平面

建议名称：

- `ops`
- `governance-plane`

职责：

- 部署
- runbooks
- 数据质量巡检
- 回溯任务操作面
- 监控告警
- 版本切换

注意：

- 治理事实不在这里定义
- 数据质量真相仍属于 `data-platform`
- access decision / audit 真相仍属于 `auth-kernel`

### 3.7 参考层：upstreams

建议名称：

- `upstreams`

职责：

- 归档参考开源项目
- 保存 OpenClaw 本地源码
- 作为未来受控复用与裁剪的来源

### 3.8 不计入业务模块但必须存在：公共契约层

建议名称：

- `shared/contracts`

职责：

- capability definition
- access context
- scope / store / org id 约定
- readiness schema
- projection schema
- serving response schema
- bridge / tool contract

原因：

- 如果没有公共契约层，多窗口并行开发会快速漂移

配套文档见：

- `docs/specs/navly-v1/2026-04-06-navly-v1-shared-contracts-layer.md`
- `docs/specs/navly-v1/2026-04-06-navly-v1-naming-conventions.md`

---

## 4. 模块依赖关系

推荐依赖关系如下：

```text
Qinqin -> data-platform

WeCom / OpenClaw
  -> openclaw-host-bridge
  -> auth-kernel

openclaw-host-bridge
  -> auth-kernel
  -> thin runtime shell

thin runtime / agent-runtime
  -> auth-kernel
  -> data-platform

apps / channels
  -> bridge or runtime

ops / governance-plane
  -> observe / operate all modules
```

### 4.1 强约束

以下依赖必须禁止：

- runtime 直接读 raw layer
- runtime 直接拼 canonical facts
- bridge 持有业务真相
- apps 直接跨过 runtime 读内核内部状态
- LLM 层定义 permission / readiness 真相

---

## 5. 推荐的 spec 子目录布局

为了支持多窗口并行设计，建议 `Navly_v1` 的 spec 也模块化拆分。

建议布局：

```text
docs/specs/navly-v1/
  README.md
  2026-04-06-navly-v1-design.md
  2026-04-06-navly-v1-modular-development-and-vibe-coding.md
  data-platform/
  auth-kernel/
  openclaw-host-bridge/
  runtime/
```

当前第一优先子目录：

- `docs/specs/navly-v1/data-platform/`

原因：

- 第一阶段先做数据真相源内核
- 它的边界、分层、state/completeness/projection 必须先被讲清楚

---

## 6. Navly 的 Vibe Coding 方法论

### 6.1 可以开任意数量的 Codex 窗口，但不能无边界乱写

在 Navly 中，`vibe coding` 的含义不是“大家同时随便改”，而是：

> **在清晰边界、清晰 ownership、清晰契约之下，用多个 Codex 窗口高并发推进不同模块。**

因此：

- **窗口数量理论上可以任意多**
- **真正的并发上限，不是窗口数，而是可分离的写入边界和集成能力**

### 6.2 窗口类型

建议把窗口分成 4 类：

#### 1. 架构总控窗口

负责：

- 维护总方案
- 维护跨模块边界
- 收口公共契约
- 做集成判断

#### 2. 模块设计窗口

负责：

- 为一个模块写 spec
- 明确职责、输入输出、依赖、phase-1 范围

#### 3. 模块实现窗口

负责：

- 按已确认 spec 落代码
- 只在自己拥有的目录中写入

#### 4. 验证 / 审计窗口

负责：

- contract check
- e2e 验证
- runbook / docs 一致性检查

### 6.3 工作法核心规则

#### 规则 1：先定边界，再并行

没有边界就并行，最后只会得到更快的混乱。

#### 规则 2：一窗一主责，一窗一写入边界

同一时刻，一个窗口应该只拥有一个主责写入边界。

例如：

- 一个窗口只写 `data-platform/completeness/`
- 另一个窗口只写 `auth-kernel/policy/`

而不是两个窗口同时改同一层同一批文件。

#### 规则 3：contracts 先于实现

每个模块在开始大规模编码前，必须先明确：

- 输入 contract
- 输出 contract
- dependency contract

#### 规则 4：先做 vertical slice，再横向铺开

不要一开始就把所有模块全面铺开。

更稳的方式是：

1. 先打通一条最小闭环链路
2. 再按模块扩大覆盖面

#### 规则 5：kernel 永远不被 LLM 层反向定义

上层运行时可以很灵活，但：

- data truth 由 `data-platform` 定义
- access truth 由 `auth-kernel` 定义

#### 规则 6：文档、契约、代码同回合更新

模块边界变化时：

- spec 要改
- contract 要改
- code 要改
- runbook / docs 要补

不能只改代码不改文档。

### 6.4 推荐的多窗口推进流程

#### Round 0：总方案收口

由架构总控窗口完成：

- v1 模块定义
- 边界定义
- phase-1 范围
- 公共契约草案

#### Round 1：模块 spec 并行

多个窗口分别产出：

- data-platform spec
- auth-kernel spec
- openclaw-host-bridge spec
- thin runtime shell spec

#### Round 2：公共契约冻结到可用水平

收口：

- capability definition
- access context
- readiness schema
- serving response
- bridge / tool contracts

#### Round 3：先打最小 vertical slice

建议最小闭环：

```text
WeCom/OpenClaw
  -> host bridge
  -> auth-kernel
  -> thin runtime shell
  -> data-platform serving
  -> answer / fallback
```

#### Round 4：模块内部分叉并行编码

这时才适合继续拆出更多窗口，例如：

- data-platform connectors
- data-platform state
- data-platform completeness
- auth policy
- bridge tool adapter
- runtime answering

#### Round 5：回到总控窗口做集成收口

收口内容包括：

- 边界是否漂移
- contract 是否失配
- docs 是否过时
- runbooks / tests 是否缺失

---

## 7. 关于“任意数量窗口”的实际建议

### 7.1 设计窗口可以很多

spec / analysis / audit / exploration 类型窗口可以很多，因为它们主要产生文档与判断，不直接互相覆盖代码。

### 7.2 真正写代码的窗口必须按 ownership 控制

代码写入窗口是否能增加，只取决于一件事：

> **新窗口是否拥有清晰且不与别人冲突的写入范围。**

### 7.3 第一阶段推荐活跃窗口数

如果进入真正编码阶段，建议第一阶段活跃写入窗口控制在：

- **4 到 6 个**

典型配置：

1. data-platform
2. auth-kernel
3. openclaw-host-bridge
4. thin runtime shell
5. verification / docs

如果边界已经足够稳，再扩到：

- **6 到 8 个**

但不建议一开始就开十几个写代码窗口，因为收口成本会反噬并行收益。

---

## 8. 第一阶段推荐窗口分工

### 窗口 0：架构总控

负责：

- v1 总方案
- 公共契约
- 集成判断

### 窗口 1：数据中台 spec / implementation

负责：

- `docs/specs/navly-v1/data-platform/`
- 后续 `platforms/data-platform/`

### 窗口 2：权限内核 spec / implementation

负责：

- `docs/specs/navly-v1/auth-kernel/`
- 后续 `platforms/auth-kernel/`

### 窗口 3：OpenClaw 宿主桥接

负责：

- `docs/specs/navly-v1/openclaw-host-bridge/`
- 后续 `bridges/openclaw-host-bridge/`

### 窗口 4：thin runtime shell

负责：

- `docs/specs/navly-v1/runtime/`
- 后续 `runtimes/navly-runtime/`

### 窗口 5：验证与治理

负责：

- tests
- runbooks
- docs consistency
- e2e 验证

---

## 9. 核心判断

Navly 的 `vibe coding` 不应是：

- 多窗口随意开工
- 边界未定先堆代码
- 让 LLM 层顺手定义 kernel 真相
- 让 OpenClaw bridge 膨胀成第三内核

而应是：

> **先定双内核与宿主桥接边界，再以 contracts-first、ownership-first、vertical-slice-first 的方式，用多个 Codex 窗口并行推进。**
