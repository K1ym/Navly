# 2026-04-06 Navly_v1 正式方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 Navly_v1 的当前可落地架构、目标架构、内核边界、upstream 采用策略与版本落地路径

---

## 1. 文档目的

本文档是 `Navly_v1` 的正式方案文档。

它回答五个核心问题：

1. `Navly_v1` 当前应该落成什么系统，而不是什么系统
2. 当前第一阶段真正必须落地的架构是什么
3. 目标架构与第一阶段架构相比多了什么
4. 数据中台、OpenClaw 权限/会话内核、上层智能执行层的边界分别是什么
5. 哪些 upstream 是第一阶段必用，哪些只是参考、增强或后续选配

本文档是：

- `docs/specs/data-platform/2026-04-06-navly-data-middle-platform-design.md` 的版本级上层方案
- `docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md` 的正式规格补充
- `docs/api/qinqin/`、`docs/audits/qinqin/`、`docs/reference/navly-v1/open-source-stack/` 的统一收口文档

模块化实现方式与多窗口协作流程见：

- `docs/specs/navly-v1/2026-04-06-navly-v1-modular-development-and-vibe-coding.md`

---

## 2. 核心结论

`Navly_v1` 应被定义为一个 **双内核 + 可替换执行壳层** 的系统：

1. **数据中台内核**
2. **权限与会话绑定内核**
3. **建立在这两个内核之上的上层智能执行层**

其中：

- 双内核是长期资产
- 上层执行层是第一阶段需要存在、但默认可重构的产品层
- 旧业务问答、旧 prompt glue、旧 deep-query 路径不再被视为架构基石

一句话定义：

> Navly_v1 是一个以数据中台和权限/会话绑定内核为长期资产、以智能执行层为可替换上层的门店 Copilot 第一代版本。

---

## 3. 版本范围与前提假设

### 3.1 当前版本范围

`Navly_v1` 当前版本明确覆盖：

1. 以 `Qinqin` 为第一输入域的数据中台建设
2. 以 `WeCom + OpenClaw` 为第一接入域的权限与会话绑定内核
3. 以上述两者为基础的门店 Copilot 上层执行壳层

### 3.2 当前版本不追求

当前版本不追求：

1. 沿用旧业务问答实现形状
2. 一次性把所有归档 upstream 都变成运行时依赖
3. 一开始就做成复杂多代理系统
4. 一开始就补齐所有预测、实时流、长期记忆、治理平台

### 3.3 明确假设

本文档基于以下假设继续推进：

1. `docs/api/qinqin/` 是当前第一输入真相源目录之一
2. `docs/audits/qinqin/` 是输入文档与 live 行为偏差的历史审计区，而不是 API 主入口
3. `upstreams/openclaw/` 是可参考、可裁剪、可受控集成的上游源码，不是 Navly 产品实现目录
4. 公开文档不得包含 `docs/reference/data-platform/private/` 中的真实 secrets

---

## 4. Navly_v1 当前可落地架构

### 4.1 当前落地总原则

当前最正确的落地方式不是“先做一个很聪明的 Copilot，再慢慢补数据”，而是：

> 先做强内核，再做薄上层。

也就是：

1. 数据中台先成为数据真相与可答真相源
2. 权限/会话绑定内核先成为访问真相源
3. 上层智能执行层先做薄、做稳、做可替换

### 4.2 当前落地总图

```text
店长 / 店员
  -> 企业微信 WeCom
  -> OpenClaw Gateway / WeCom Adapter
  -> Permission Kernel
       - actor / role / scope / conversation binding
       - Gate 0 access control
       - governance / audit
  -> Execution Shell
       - intent routing
       - capability selection
       - answer composition
       - fallback / escalation
  -> Data Platform Serving
       - theme objects / projections
       - completeness / readiness reasons
       - canonical facts (restricted direct access)
       - raw replay / audit
```

### 4.3 第一阶段必须形成的完整链路

第一阶段不是只做“接上 API”。

必须闭合以下链路：

1. `Qinqin API docs` 作为输入字段真相源
2. connector / ingestion 拉取与原始回放留存
3. 标准事实层建模
4. 最新可用状态、历史执行状态、completeness 分离
5. 主题层 / projection / serving objects 产出
6. 上层执行壳默认从 serving / projection 读取
7. OpenClaw 侧完成 actor / role / scope / conversation / Gate 0 收口

只有这条链路闭合，Navly_v1 才算“当前可落地”。

### 4.4 当前阶段的上层执行层应该有多薄

当前阶段的智能执行层只需要稳定完成以下职责：

1. 识别访问主体与会话上下文
2. 判断当前问题对应的 capability / theme
3. 调用数据中台的稳定输出对象
4. 在 `ready / pending / failed / insufficient_scope` 之间做受控解释
5. 输出可审计答案或拒答原因

当前阶段不应让它承担以下职责：

1. 自己拼事实层
2. 自己推断最新业务日
3. 自己绕过 completeness 生成“看起来差不多”的答案
4. 继续把历史业务胶水塞进 OpenClaw 或 runtime 主链路

---

## 5. Navly_v1 目标架构

### 5.1 目标架构定位

目标态仍然保持 **双内核 + 可替换执行层**，但会在执行层、实时层、治理层、预测层上继续增强。

目标态不是推翻当前态，而是：

- 保持数据中台是数据真相与答案就绪真相源
- 保持权限内核是访问与会话真相源
- 允许上层智能执行层持续重构

### 5.2 目标态相对当前态新增的能力

目标态可继续增加：

1. 更强的语义服务层与指标治理
2. 更复杂的执行编排 / agent orchestration
3. CDC + event bus 驱动的实时预警
4. 更完整的治理与观测平台
5. 时序预测、推荐、长期记忆等增强能力

### 5.3 当前态与目标态的关系

关系应理解为：

- 当前态：先把“可审计、可解释、可复用”的主干打通
- 目标态：在不破坏双内核边界的前提下继续扩展

换言之：

> 当前态追求结构正确；目标态追求能力丰富；两者不能互相替代。

---

## 6. 三层边界与真相源分工

### 6.1 边界总原则

三层边界必须清楚：

1. 数据中台回答“数据是什么、能不能答、为什么能答/不能答”
2. 权限内核回答“谁能在什么会话/范围内访问什么能力”
3. 上层执行层回答“如何组织一次交互和结果表达”

### 6.2 真相源矩阵

| 边界层 | 拥有的真相 | 典型输入 | 典型输出 | 明确不拥有的真相 |
| --- | --- | --- | --- | --- |
| 数据中台 | 原始数据、标准事实、最新可用状态、completeness、projection | `docs/api/qinqin/`、ingestion runs、历史回放 | 主题对象、服务对象、可答状态、审计链路 | actor 访问权限、会话路由策略 |
| 权限与会话绑定内核 | actor、role、scope、conversation、Gate 0、访问审计 | WeCom 身份、OpenClaw session/workspace、绑定规则 | access decision、session context、governance trail | 业务事实、字段治理、答案数据口径 |
| 上层智能执行层 | 当前交互编排、能力选择、答案组织、fallback 行为 | 用户问题、session context、serving outputs | 回答文本、引用对象、拒答说明、任务转交 | 原始数据真相、最终权限真相 |

### 6.3 数据中台与权限内核的直接边界

数据中台与权限内核之间只交换 **受控上下文**，不交换业务胶水。

允许交换的内容：

1. actor / role / scope / conversation 的标准上下文
2. store / org / tenant 的访问范围
3. capability 所需的 scope 声明
4. 访问审计所需的 query / capability metadata

不允许交换的内容：

1. 散落的 prompt 特例
2. 旧 query glue 中的业务分支
3. 隐式 hardcode 的 tenant / store / app 映射
4. 上层猜出来的权限决定

### 6.4 上层执行层如何建立在两个内核之上

上层执行层必须同时依赖两个内核，但只依赖它们的 **稳定接口**：

1. 先从权限内核拿到：
   - actor identity
   - role / scope binding
   - conversation binding
   - access decision
2. 再从数据中台拿到：
   - capability readiness
   - latest usable business date
   - theme / projection result
   - explanation / insufficiency reason

因此，上层执行层的正确姿势不是：

- “我自己去理解数据库和权限细节”

而是：

- “我在双内核之上做一次可重构的智能组织与表达”

---

## 7. 第一阶段 upstream 采用策略

### 7.1 第一阶段必用 upstream

以下 upstream 属于 **第一阶段必须纳入实现主链路** 的组件：

#### 1. OpenClaw

用途：

- WeCom 接入
- Gateway
- Session / Workspace 语义
- actor / role / scope / conversation 绑定
- Gate 0 / 治理 / 审计主入口

理由：

- 权限与会话绑定内核是长期资产
- 这部分不应重新发明，也不应继续散落在旧业务胶水里

#### 2. PostgreSQL

用途：

- 原始层、事实层、状态层、projection 层的统一主存储

理由：

- Navly_v1 当前最重要的是建立稳定真相源，而不是堆叠过多存储组件

#### 3. dbt Core

用途：

- 事实层、维表、主题层、质量校验与建模发布

理由：

- 如果没有显式建模与测试边界，数据中台很容易重新退回“脚本堆积”
- 对 Navly 当前阶段而言，dbt 比预测或多代理更接近内核能力

#### 4. Temporal

用途：

- backfill、重试、补数、reconcile、长任务编排

理由：

- Navly_v1 的主任务之一是全门店、全历史、可重跑、可解释
- 这类工作流需要稳定的后台编排内核，而不是临时 cron 和脚本堆叠

### 7.2 第一阶段条件性采用 upstream

以下 upstream 在第一阶段 **可以采用，但不应被当作所有工作同时阻塞的硬前提**：

#### 1. Cube

适用条件：

- 当主题层需要统一指标语义、预聚合和多消费端稳定查询接口时启用

当前判断：

- 推荐作为第一阶段后半段或第一阶段扩展项
- 不应阻塞原始层、事实层、状态层与 projection 闭合

#### 2. GraphQL Engine（Hasura）

适用条件：

- 当需要把 serving 对象稳定暴露给多个上层消费者，并叠加访问控制时启用

当前判断：

- 可作为 serving 接口候选
- 但不是双内核成形的前置条件

#### 3. pgvector

适用条件：

- 当上层需要面向文档、解释对象、审计材料做语义检索时启用

当前判断：

- 有价值，但不属于当前数据中台主闭环的硬前置条件

#### 4. LangGraph

适用条件：

- 当上层执行链复杂到单 pipeline 难以稳定治理时启用

当前判断：

- 它属于上层执行层增强，不是当前双内核成立的必要条件

### 7.3 第二阶段及后续增强 upstream

以下 upstream 统一视为增强路线：

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

它们都合理，但不应被错误地包装成“第一阶段不做就不完整”。

### 7.4 基础设施参考 upstream

以下 upstream 属于基础设施参考，而不是业务内核：

- Compose
- Tailscale

它们解决的是部署和网络问题，不应被写进 Navly 业务边界本身。

---

## 8. 仓库目标结构

为了让 Navly_v1 的边界在代码层也成立，建议未来仓库结构以“长期内核优先”组织：

```text
platforms/
  data-platform/
    contracts/
    ingestion/
    raw-store/
    warehouse/
    quality/
    completeness/
    projections/
    serving/
    migration/
    scripts/
    tests/
  permission-kernel/
    contracts/
    gateway/
    bindings/
    session/
    governance/
    adapters/
    audit/
applications/
  navly-copilot/
    runtime/
    capabilities/
    answering/
    escalation/
docs/
upstreams/
  openclaw/
```

### 8.1 `platforms/data-platform`

这是数据真相、状态真相、completeness 真相、projection 真相的唯一长期归属。

### 8.2 `platforms/permission-kernel`

这是 actor / role / scope / conversation / Gate 0 / 治理审计的唯一长期归属。

### 8.3 `applications/navly-copilot`

这是产品执行层，不应反向侵入双内核，也不应变成新的硬编码真相源。

### 8.4 `upstreams/openclaw`

只作为上游参考与受控集成来源，不作为 Navly 产品逻辑落点。

---

## 9. 当前态到目标态的分阶段路线

### 阶段 1：双内核建骨架，做薄执行壳

目标：

1. 数据中台主闭环成立
2. 权限与会话绑定主闭环成立
3. 上层先做薄执行壳

阶段完成标志：

1. 问题进入后先过 Gate 0 与绑定校验
2. 数据平台能给出 readiness 与 projection
3. 回答链路不再直接依赖旧 query glue

### 阶段 2：补强服务层与解释层

目标：

1. 稳定主题对象 / semantic serving
2. 补强可答解释与拒答解释
3. 增加更多 operator-facing 对象

阶段完成标志：

1. 上层基本不直读事实层
2. 主题与 capability 的映射稳定
3. projection / serving 成为默认消费入口

### 阶段 3：增强实时、预测、治理与复杂编排

目标：

1. 引入事件流与实时预警
2. 引入预测能力
3. 引入更强编排、观测、长期记忆

阶段完成标志：

1. 增强能力建立在双内核之上
2. 没有破坏双内核边界
3. 没有把新能力重新做成硬编码耦合

---

## 10. 验收标准

### 10.1 架构验收

必须能清楚指出：

1. 哪部分是数据中台
2. 哪部分是权限/会话绑定内核
3. 哪部分是上层执行壳
4. 哪些能力是长期资产，哪些是可替换层

### 10.2 数据验收

必须能清楚回答：

1. 某店某能力为什么 `ready / pending / failed`
2. 最新可用业务日是什么
3. 哪些字段已结构化，哪些只保留原始层，哪些暂不使用
4. 某次结果可追溯到哪次 ingestion / projection / audit

### 10.3 权限验收

必须能清楚回答：

1. 当前 actor 是谁
2. 当前 role / scope / conversation 绑定是什么
3. 为什么当前请求被允许或拒绝
4. 是否留下治理审计记录

### 10.4 上层验收

必须能清楚回答：

1. 上层是否仍在直接拼事实层
2. 上层是否仍在自己推断权限或数据 readiness
3. 上层是否仍依赖旧业务问答主链路

如果答案是“是”，则 `Navly_v1` 尚未完成正确收口。

---

## 11. 核心判断

`Navly_v1` 不应再被表述为：

- “旧系统修修补补后的下一版”
- “把旧问答路径换个名字继续跑”
- “先把智能层做起来，数据慢慢补”

而应被表述为：

> 用数据中台与权限/会话绑定内核重建 Navly 的第一代正式版本；上层智能执行只是建立在双内核之上的可替换产品层。
