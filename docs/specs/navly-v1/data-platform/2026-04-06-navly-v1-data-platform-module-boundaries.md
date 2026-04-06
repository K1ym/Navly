# 2026-04-06 Navly_v1 数据中台模块边界方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 数据中台的 4 个核心模块、模块职责、输入输出、依赖关系、phase-1 优先级与长期资产判断

---

## 1. 文档目的

本文档回答一个问题：

> `Navly_v1` 的数据中台在模块上应该如何拆，哪些模块拥有哪一种真相，模块之间如何依赖，而不把旧业务逻辑重新塞回来？

本文档是数据中台专项边界文档，不讨论权限内核内部实现，也不讨论 Copilot 的对话实现。

---

## 2. 模块划分总原则

### 2.1 模块必须按“真相类型”拆分

数据中台内至少区分四类真相：

1. **数据契约真相**
2. **原始采集与回放真相**
3. **标准事实与状态治理真相**
4. **可答性与主题服务真相**

同一模块不能同时把这四件事混在一起。

### 2.2 `docs/api/qinqin/` 是输入真相源，不是参考附件

当前 `Qinqin v1.1` 的 8 个正式端点、请求参数、响应字段和共享签名规则，必须从 `docs/api/qinqin/` 进入正式 contract registry。

`docs/audits/qinqin/` 只负责记录差异与风险，不直接替代正式 contract。

### 2.3 历史执行真相和最新可用状态真相必须分离

- 某次拉取是否成功：属于原始采集模块
- 目前最新可用业务日是什么：属于状态治理模块

两者不能复用同一张状态表表达。

### 2.4 长期资产与实现手段必须分离表达

Navly 长期保留的是：

- contract registry
- raw replay ledger
- canonical schema
- state semantics
- readiness reason taxonomy
- theme service contracts

不是某个临时脚本、某个 worker 进程名字、某个一次性的 cron 写法。

---

## 3. 四个核心模块总览

```text
Qinqin API docs / audits
  -> M1 数据契约与接口接入
  -> M2 数据采集与原始回放
  -> M3 标准事实与状态治理
  -> M4 可答性与主题服务
  -> Copilot / 其他消费方

Permission Kernel
  -> 受控 access context
  -> M4 读接口边界
```

| 模块 | 拥有的真相 | 主要输入 | 主要输出 | 直接下游 | phase-1 优先级 |
| --- | --- | --- | --- | --- | --- |
| M1 数据契约与接口接入 | source / endpoint / field contract 真相 | `docs/api/qinqin/`、`docs/audits/qinqin/` | endpoint registry、field catalog、landing policy、variance register | M2、M3、M4 | P0 |
| M2 数据采集与原始回放 | 历史执行真相、raw replay 真相 | M1 contract、运行时安全配置、调度计划 | ingestion run、endpoint run、raw request/response、replay handle | M3 | P0 |
| M3 标准事实与状态治理 | canonical facts、latest usable state、quality 真相 | M1 contract、M2 raw outputs | canonical facts、latest sync state、quality snapshots、field coverage | M4 | P0 |
| M4 可答性与主题服务 | capability readiness、theme service 真相 | M1 capability metadata、M3 facts/state、权限上下文 | readiness snapshot、theme objects、service objects、explanation objects | Copilot、其他消费方 | P0 |

---

## 4. M1 数据契约与接口接入模块

### 4.1 模块职责

M1 负责把“文档里写了什么、系统当前支持什么、字段应该落到哪里”变成可执行的受治理 contract。

它至少负责：

1. 冻结 `Qinqin v1.1` 的 8 个正式端点清单
2. 固化 canonical 请求参数名、分页语义、增量语义、业务时间语义
3. 维护 response field catalog 与 field path registry
4. 维护字段落点策略：原始层 / 事实层 / 主题层 / 暂不使用
5. 记录 doc 与 live 行为差异的受治理 variance register
6. 为后续模块提供稳定 contract，而不是让后续模块直接解析 Markdown

### 4.2 输入

| 输入 | 说明 |
| --- | --- |
| `docs/api/qinqin/endpoint-manifest.md` | 正式端点清单与结构化目标 |
| `docs/api/qinqin/member/*.md`、`staff/*.md` | 请求体、响应字段、示例 envelope |
| `docs/api/qinqin/auth-and-signing.md` | 共享签名、时间窗、白名单规则 |
| `docs/audits/qinqin/*` | 文档与 live 差异的审计证据 |
| source onboarding decision | 当前阶段纳入的数据源范围与版本冻结决定 |

### 4.3 输出

推荐最小输出对象：

- `source_system_registry`
- `endpoint_contract_registry`
- `endpoint_parameter_registry`
- `endpoint_field_registry`
- `field_landing_policy_registry`
- `source_variance_registry`
- `source_scope_registry`（例如当前允许接入的门店 / OrgId 范围）

### 4.4 对下游的约束

- M2 只能基于 M1 冻结的 contract 去采集，不能私自发明 endpoint 名和字段名
- M3 只能基于 M1 的 field catalog 去解释“字段是否已落地”
- M4 的 capability dependency 必须引用 M1 已登记的 dataset / field，不允许引用临时脚本口径

### 4.5 明确不负责的事

M1 不负责：

- 保存真实 secret
- 直接发 HTTP 请求
- 事实层建模
- readiness 计算
- 权限决策

### 4.6 phase-1 优先级

**P0，必须先闭合。**

若没有 M1，后续所有模块都会退化成：

- 根据代码猜字段
- 根据错误日志猜参数名
- 根据历史习惯猜增量语义

这与 Navly 的长期中台目标冲突。

### 4.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| endpoint registry | Markdown parser / generator 脚本 |
| field catalog | 某次人工整理 Excel |
| field landing policy | 某个一次性的导入脚本 |
| variance register | 某个调试 worker 的内部日志 |

---

## 5. M2 数据采集与原始回放模块

### 5.1 模块职责

M2 负责把 contract 变成可重跑、可回放、可审计的原始执行链路。

它至少负责：

1. 基于 contract 生成 run plan 与 endpoint plan
2. 处理时间窗、分页、重试、节流和补数重跑
3. 保存 raw request / raw response / raw page payload
4. 保存历史执行事实：run、endpoint run、page run、error taxonomy
5. 为任意一次结果提供 replay handle
6. 保证“同一业务日期重跑”不会破坏历史执行真相

### 5.2 输入

| 输入 | 说明 |
| --- | --- |
| M1 endpoint contract | 调用路径、请求参数、分页策略、增量策略 |
| 运行时安全配置 | base URL、鉴权相关 secret contract 的运行时注入值 |
| 调度 / backfill plan | 每日同步、补数、全历史回溯计划 |
| source scope registry | 当前纳入的门店 / 组织范围 |

### 5.3 输出

推荐最小输出对象：

- `ingestion_run`
- `ingestion_endpoint_run`
- `ingestion_page_run`
- `raw_request_envelope`
- `raw_response_envelope`
- `raw_response_page`
- `raw_replay_handle`
- `raw_error_event`

### 5.4 对下游的约束

- M3 读取 M2 的 raw outputs 时，只能把它们当作原始真相，不得直接把 run 状态等同于 latest usable state
- M4 不得直接依赖 M2 的 page 级日志判断 readiness，必须经由 M3 的状态治理结果

### 5.5 明确不负责的事

M2 不负责：

- 事实口径统一
- readiness 解释
- 主题服务对象构建
- 权限范围判断

### 5.6 phase-1 优先级

**P0，必须闭合。**

Navly 的长期中台要求“全历史、可回放、可补数”。没有 M2，就没有可信的原始执行真相。

### 5.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| run / endpoint run / page run 语义 | Temporal worker / cron job 的具体实现 |
| raw replay ledger | Postgres JSONB 或对象存储的具体落地方式 |
| error taxonomy | 某个 HTTP client 库 |
| idempotent rerun contract | 某次临时补数脚本 |

---

## 6. M3 标准事实与状态治理模块

### 6.1 模块职责

M3 负责把 raw source 真相转成 Navly 长期可复用的 canonical facts 与 state truth。

它至少负责：

1. 建立统一 canonical entity / fact 模型
2. 将 8 个端点映射到结构化事实对象与维表对象
3. 维护 latest usable sync state，而不是复用历史 run 状态
4. 维护 backfill progress、schema alignment、field coverage、quality issue 等治理对象
5. 输出“哪个门店 / 哪个业务日 / 哪个 dataset 当前可用”的状态真相
6. 为 M4 提供稳定的事实与状态输入，不让 M4 直读 raw payload 猜状态

### 6.2 输入

| 输入 | 说明 |
| --- | --- |
| M1 field catalog / landing policy | 字段落点和结构化优先级 |
| M2 raw replay outputs | 原始页数据、历史运行结果、错误事件 |
| quality rules | 唯一键、时间覆盖、结构对齐、枚举约束等治理规则 |

### 6.3 输出

推荐最小输出对象：

- canonical dimensions / facts
- `latest_sync_state`
- `backfill_progress_state`
- `field_coverage_snapshot`
- `schema_alignment_snapshot`
- `quality_issue`
- `dataset_availability_snapshot`

### 6.4 对下游的约束

- M4 的 readiness 计算必须建立在 M3 的 dataset availability 和 latest state 之上
- Copilot 不能直接穿透到 M3 事实表，把它当问答底座

### 6.5 明确不负责的事

M3 不负责：

- 上层 capability 路由
- 对话解释措辞
- actor / role / scope 决策
- 原始 secret 管理

### 6.6 phase-1 优先级

**P0，必须闭合。**

如果没有 M3，Navly 只有原始日志，没有可复用的数据真相，也无法把“历史执行真相”与“最新可用状态真相”分开。

### 6.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| canonical schema | dbt model / SQL job 的具体组织方式 |
| latest usable state semantics | 某一张旧状态表的兼容写法 |
| field coverage / schema alignment 规则 | 某次临时对账脚本 |
| dataset availability truth | 某个 dashboard 的展示形状 |

---

## 7. M4 可答性与主题服务模块

### 7.1 模块职责

M4 负责把“已有事实 + 已有状态”变成上层真正可消费的 capability readiness 与 theme service object。

它至少负责：

1. 维护数据平台内部的 capability registry
2. 维护 capability -> dataset dependency matrix
3. 计算 capability readiness，并产出明确 reason code
4. 构建主题快照、服务对象、解释对象
5. 对外暴露稳定读接口，默认屏蔽事实层复杂性
6. 保证 readiness truth 与 theme service truth 都可追溯到 M3 / M2

### 7.2 输入

| 输入 | 说明 |
| --- | --- |
| M1 contract metadata | capability 引用的数据集与字段只能来自受治理元数据 |
| M3 canonical facts | 主题构建的事实基础 |
| M3 latest state / quality | readiness 判断、缺口解释、staleness 解释 |
| 权限上下文 | 来自权限内核的标准化 scope / access context |

### 7.3 输出

推荐最小输出对象：

- `capability_registry`
- `capability_dependency_registry`
- `capability_readiness_snapshot`
- `theme_snapshot`
- `theme_service_object`
- `capability_explanation_object`
- `serving_trace_ref`

说明：

- `store_member_insight`、`store_daily_overview` 等只保留作文档短名
- registry、snapshot、serving contract 中必须使用 canonical `capability_id` / `service_object_id`

### 7.4 对下游的约束

- Copilot 默认只读取 M4 暴露的 readiness / theme / explanation 接口
- Copilot 不得绕过 M4 直读事实层“自己拼一个差不多答案”
- 权限内核只提供 access context，不拥有 readiness 逻辑

### 7.5 明确不负责的事

M4 不负责：

- actor 身份识别
- Gate 0 判定
- 对话组织和回答措辞
- 原始数据采集
- 事实层主建模

### 7.6 phase-1 优先级

**P0，必须闭合。**

Navly_v1 的上层不能再建立在“旧问答 glue + 临时 SQL”上。没有 M4，就没有稳定的数据中台默认消费入口。

### 7.7 长期资产 vs 实现手段

| 长期资产 | 只是实现手段 |
| --- | --- |
| capability registry | 某个 API gateway / GraphQL 包装层 |
| readiness reason taxonomy | 某段 prompt 文本里的解释语句 |
| theme service contract | 某个 materialized view 的具体实现 |
| serving traceability contract | 某个缓存层或 BFF 的临时字段 |

---

## 8. 模块依赖关系

### 8.1 强依赖链

```text
M1 -> M2 -> M3 -> M4
```

### 8.2 允许的横向依赖

- M3 可读取 M1 的 field catalog / landing policy
- M4 可读取 M1 的 capability metadata / dataset registry

### 8.3 禁止的跨越依赖

- M2 不得直接依赖 M4 的 theme service 定义来决定如何采集
- M4 不得直接依赖 raw payload 推导 latest usable state
- Copilot 不得跳过 M4 直读 M2 / M3
- 权限内核不得直接拥有 canonical business facts

---

## 9. phase-1 优先级总结

| 模块 | phase-1 级别 | 原因 |
| --- | --- | --- |
| M1 | P0 | 不先冻结 contract，就没有后续长期边界 |
| M2 | P0 | 不先闭合 raw replay，就没有全历史与可审计 |
| M3 | P0 | 不先建立 canonical facts / latest state，就没有数据真相源 |
| M4 | P0 | 不先建立 readiness / theme service，就没有上层默认消费入口 |

结论：

> 对 Navly_v1 而言，这四个模块不是“可选增强”，而是 phase-1 就必须一起闭合的完整 slice。

---

## 10. 核心判断

Navly_v1 数据中台的正确模块边界不是：

- “connector 一层 + 几张事实表 + 上层自己拼回答”

而是：

- M1：定义边界
- M2：保存原始执行真相
- M3：沉淀标准事实与状态真相
- M4：提供可答性与主题服务真相

只有这样，数据中台才会成为 Navly 的长期资产，而不是旧业务实现的附属层。
