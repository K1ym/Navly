# 2026-04-06 Navly_v1 数据中台 Phase-1 落地方案

日期：2026-04-06  
状态：phase-1-baseline  
用途：定义 `Navly_v1` 数据中台第一阶段的闭环范围、模块优先级、交付顺序、验收标准与延期项

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 数据中台第一阶段到底要落成什么，哪些是必须闭环，哪些是长期方向但当前不应假装已经属于 phase-1？

---

## 2. Phase-1 的正式定义

Phase-1 不是“先把 API 接上”。

Phase-1 的正式定义是：

> 围绕 `Qinqin v1.1` 8 个正式端点，打通“契约治理 -> 原始回放 -> 标准事实 -> 最新状态 -> 可答性 -> 主题服务”的第一条完整可复用链路，并把它作为 Copilot 的默认数据依赖面。

只有这条链路闭合，Navly_v1 数据中台才算进入可实施状态。

---

## 3. Phase-1 前提假设

### 3.1 输入域范围

当前 phase-1 只覆盖：

- `docs/api/qinqin/` 中冻结的 `Qinqin v1.1` 8 个正式端点

### 3.2 组织范围

当前 phase-1 覆盖：

- 文档白名单内的目标门店范围
- 以门店 / 业务日为核心粒度
- 支持后续扩展到 HQ 聚合，但 HQ 聚合不是 phase-1 的唯一交付重点

### 3.3 时间范围

当前 phase-1 必须支持：

- 每日主同步
- 历史补数与重跑
- 全历史回溯能力的结构准备

### 3.4 安全假设

当前 phase-1 只在公开文档中描述 secret contract：

- 必需哪些配置
- 哪些属于 secret
- 哪些由运行时注入

公开文档不保存真实 secret 值。

---

## 4. Phase-1 完成态

Phase-1 完成时，至少要成立以下 6 条：

1. `docs/api/qinqin/` 的 8 个端点已进入正式 contract registry
2. 每个端点都可以产生 raw replayable run 记录
3. `endpoint-manifest.md` 声明的结构化目标都已有 canonical landing
4. latest usable state 与历史 run truth 已拆开
5. 至少一组核心 capability readiness 与 theme service object 可以稳定输出
6. Copilot 默认从数据中台服务对象读取，而不是拼事实表或绕过 readiness

---

## 5. Phase-1 模块优先级矩阵

| 模块 | P0（phase-1 必须） | P1（phase-1 紧随其后） | 延后 |
| --- | --- | --- | --- |
| M1 数据契约与接口接入 | 8 个端点 contract 冻结、字段全量登记、landing policy、variance register | contract diff 自动化、字段分级 dashboard | 多源接入控制台 |
| M2 数据采集与原始回放 | 每日主同步、历史补数、raw replay、分页幂等、标准 error taxonomy | 限流自适应、执行成本分析 | CDC / 事件流 |
| M3 标准事实与状态治理 | canonical landing、latest state、field coverage、schema alignment、quality issue | 更完整数据评分、多源实体对齐 | 主数据管理 / 跨源主数据融合 |
| M4 可答性与主题服务 | capability registry、readiness resolver、核心 theme service objects、explanation object | HQ 聚合主题、更多 operator-facing 对象 | 通用 semantic layer、预测与推荐 |

结论：

> 对 Navly_v1 数据中台来说，四个模块全部是 P0 主链路；差别只在同一模块内部哪些子能力先做、哪些后做。

---

## 6. Phase-1 端点闭环要求

| 端点 | phase-1 级别 | 主要作用 | 特别要求 |
| --- | --- | --- | --- |
| `GetCustomersList` | P0 | 会员基础档案、会员主题基础 | 字段 catalog 与 card / ticket / coupon 子对象必须纳管 |
| `GetConsumeBillList` | P0 | 消费事实、财务摘要、会员洞察 | 业务时间增量、支付与明细拆分 |
| `GetRechargeBillList` | P0 | 充值事实、财务摘要 | 充值主单 / 支付 / 赠券 / 销售归属拆分 |
| `GetUserTradeList` | P0 | 账户流水、会员资产解释 | 与消费 / 充值事实可追溯关联 |
| `GetPersonList` | P0 | 员工档案、员工主题基础 | 员工与项目能力拆分 |
| `GetTechUpClockList` | P0 | 上钟事实、员工看板 | 明细与汇总对象分离 |
| `GetTechMarketList` | P0 | 推销提成事实 | 与员工 / 业务日 / 门店统一粒度 |
| `GetTechCommissionSetList` | P0 | 提成配置与配置解释 | 额外 header / auth 差异必须显式建模，禁止模糊 `partial` |

---

## 7. Phase-1 结构化落地要求

### 7.1 M1：先冻结 contract，再允许实现

Phase-1 必须先产出：

1. endpoint registry
2. canonical parameter registry
3. response field catalog
4. field landing policy
5. source variance register

验收线：

- `docs/api/qinqin/` 中已登记字段在 contract registry 中覆盖率达到 `100%`
- 任一 live 差异都有 variance 记录，而不是散落在代码注释里

### 7.2 M2：先让 raw replay 成立，再谈事实层稳定

Phase-1 必须具备：

1. run / endpoint run / page run 三层历史记录
2. 基于门店 + 业务日 + 端点的重跑能力
3. 可从 replay handle 取回原始 request / response
4. 对 source empty、auth failure、signature failure、schema drift、page partial 的明确分类

验收线：

- 任意一条主题结果都能追溯到对应 raw run
- 任意一次失败都能定位到端点级或分页级原因

### 7.3 M3：先做 canonical facts 和 latest state 分离

Phase-1 必须具备：

1. `endpoint-manifest.md` 中全部结构化目标的 canonical landing
2. latest usable state 与 historical run truth 分离
3. field coverage / schema alignment 快照
4. backfill progress 显式对象
5. 对 `commission_setting` 空返回 / 鉴权异常 / 文档偏差的状态归因能力

验收线：

- 不再使用单张状态表混表达 run truth 与 latest state
- 不再出现“历史 run 成功但 latest state 停在旧日期仍无法解释”的状态混乱

### 7.4 M4：先做少量稳定 service objects，不做大而全问答层

Phase-1 建议 P0 服务对象（使用 canonical `service_object_id = navly.service.<domain>.<object_name>`）：

- `navly.service.store.daily_overview`
- `navly.service.store.member_insight`
- `navly.service.store.staff_board`
- `navly.service.store.finance_summary`
- `navly.service.system.capability_explanation`

Phase-1 建议 P1 服务对象（仍使用 canonical `service_object_id`）：

- `navly.service.hq.network_overview`
- `navly.service.store.exception_digest`

验收线：

- Copilot 默认读取上述 canonical service objects
- `store_member_insight`、`store_daily_overview` 等短名仅作为文档短名存在
- readiness 结果可解释，且解释来自 reason code / trace ref，不来自上层 prompt 猜测

---

## 8. Phase-1 推荐实现顺序

### 里程碑 A：contract freeze

目标：

- 固定 `Qinqin v1.1` 范围
- 固定 8 个端点的 canonical 参数和字段台账
- 固定 field landing policy

完成标志：

- M1 可以独立产出 contract artifacts

### 里程碑 B：raw replay 闭环

目标：

- 跑通端点调用、分页、重试、回放索引
- 建立历史 run truth

完成标志：

- M2 可对任一业务日执行主同步或补数，并保留完整 raw trace

### 里程碑 C：canonical + state 闭环

目标：

- 完成全部 manifest target 的 canonical landing
- 建立 latest state / quality / coverage 语义

完成标志：

- M3 能输出 canonical facts 与 latest usable state

### 里程碑 D：readiness + theme service 闭环

目标：

- 产出 capability registry 与 dependency matrix
- 产出 readiness snapshot 和首批 service objects

完成标志：

- M4 可以作为 Copilot 的默认数据接口

---

## 9. Phase-1 长期资产判断

| 类别 | phase-1 应沉淀为长期资产 | phase-1 只是手段 |
| --- | --- | --- |
| 契约 | endpoint / field / capability registry | 文档解析脚本 |
| 原始层 | replay model、run model、error taxonomy | 调度器实现、HTTP client 细节 |
| 事实层 | canonical schema、业务键、去重口径 | dbt / SQL / 批处理编排方式 |
| 状态层 | latest state semantics、coverage / quality semantics | 某个 dashboard 页面 |
| 服务层 | readiness taxonomy、theme service contracts | REST / GraphQL / 缓存包装方式 |

---

## 10. Phase-1 非目标

当前 phase-1 明确不做：

1. CDC、事件总线、实时流预警
2. 预测、推荐、向量检索、长期记忆
3. 通用自然语言查数引擎
4. 把 Copilot 重新做成“可自由拼事实表”的上层
5. 把权限规则写入数据平台内部
6. 在公开 spec 中写真实 secret

这些都可以是后续增强，但不属于当前 phase-1 完整性的定义。

---

## 11. Phase-1 验收标准

### 11.1 契约验收

- 8 个端点全部登记
- API 文档字段全部有 registry 项
- 字段都有 landing policy

### 11.2 原始层验收

- 任意 endpoint run 可按门店 / 业务日回放
- 失败原因可定位到端点或分页
- 可区分 source empty 与 auth / sign / schema 问题

### 11.3 事实与状态验收

- manifest targets 全部有 canonical landing
- latest usable state 与 historical run 不再混用
- `commission_setting` 的异常语义可解释
- `navly.store.member_insight` 依赖不再停留在“等待代码实现”的隐式状态

### 11.4 服务层验收

- 首批 service objects 可稳定输出
- readiness response 带 reason code 与 trace ref
- Copilot 不再自己推断 latest business date 或 readiness

---

## 12. 核心判断

Navly_v1 数据中台 phase-1 的正确目标不是“做一个勉强能查数据的版本”，而是：

- 把长期边界一次做对
- 用第一条完整链路证明这些边界可运行
- 给未来权限内核和 Copilot 提供稳定依赖面

因此，phase-1 应优先建设长期资产，而不是优先堆上层功能或临时查询逻辑。
