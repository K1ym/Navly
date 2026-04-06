# 2026-04-06 Navly_v1 数据中台 Phase-1 Implementation Plan

日期：2026-04-06  
状态：phase-1-executable-plan  
用途：把 `Navly_v1` 数据中台 phase-1 方案细化为可执行的实施顺序、里程碑 A/B/C/D、串并行关系与 milestone checklist

---

## 1. 文档目的

本文档回答：

> 在已经明确模块边界、内部分层、phase-1 范围和外部接口后，数据中台第一阶段应该如何真正实施？

本文档强调：

- 写成 **可执行 plan**
- 但不提前锁死到过细物理表实现

---

## 2. 实施总原则

### 2.1 先冻结边界，再扩实现

顺序必须是：

1. 先冻结 C0
2. 再闭合 L0
3. 再沉淀 L1/L2
4. 最后暴露 L3 与服务边界

### 2.2 先打一条 vertical slice，再扩全域

phase-1 不应一开始就 8 个端点同时平均推进。

正确顺序是：

- 先打一条最能证明边界正确的 vertical slice
- 再把同样的结构扩到剩余 member / staff 域
- 最后专门 burn down 特殊风险端点 `1.8`

### 2.3 batch-first，event-later

当前 phase-1 以：

- 每日主同步
- 历史补数
- 可重跑回放

为主，不以 CDC / 事件流为主。

### 2.4 先闭合 truth，再接入消费方

Copilot 接入只能发生在：

- readiness truth 已稳定
- service truth 已稳定
- serving 边界已稳定

之后。

### 2.5 Canonical ID 规则先冻结

在 phase-1 中，以下命名规则应视为先冻结的跨模块语言：

- `capability_id = navly.<domain>.<capability_name>`
- `service_object_id = navly.service.<domain>.<object_name>`

说明：

- `store_member_insight`、`store_daily_overview`、`store_staff_board`、`store_finance_summary` 仅作为文档短名
- milestone artifact、shared contracts、registry、audit event、serving response 中一律使用 canonical ID

---

## 3. 推荐的第一条 vertical slice

### 3.1 推荐 slice

推荐第一条 vertical slice 为：

> `GetCustomersList + GetConsumeBillList -> customer / consume facts -> latest state -> navly.store.member_insight readiness -> navly.service.store.member_insight service object`

### 3.2 为什么是这条 slice

原因：

1. 同时覆盖档案类与交易类端点
2. 同时覆盖分页、时间窗、字段治理、canonical landing、latest state、readiness、service object
3. 能证明 member 域最核心的可答链路
4. 避免一开始就被 `1.8 GetTechCommissionSetList` 的特殊 header / auth 差异绑住节奏

### 3.3 这条 slice 要证明什么

它必须一次证明：

- C0 contract 冻结有效
- L0 raw replay 可用
- L1 canonical fact 落地清晰
- L2 latest state 与 readiness 分离
- L3 service truth 可稳定对外

### 3.4 这条 slice 不要求什么

它不要求：

- 一开始就覆盖所有 8 个端点的全部主题
- 一开始就做 HQ 全景对象
- 一开始就接入 GraphQL / Cube / 向量检索

---

## 4. 实施工作流总图

```text
Milestone A 结构与 contract freeze
  -> Milestone B raw replay backbone
  -> Milestone C canonical fact + latest state
  -> Milestone D readiness + theme/service + serving boundary
```

这是主串行链。

在每个 milestone 内部，允许做有限并行；但 milestone gate 不允许跳过。

---

## 5. 串行与并行规则

### 5.1 必须串行的部分

以下内容必须串行：

1. `Milestone A -> B`
   - 没有 contract freeze，就不允许大规模写 connector / ingestion
2. `Milestone B -> C`
   - 没有可回放 raw truth，就不允许声称 canonical facts 稳定
3. `Milestone C -> D`
   - 没有 latest state / availability，就不允许 readiness 稳定
4. `Milestone D -> Copilot 默认接入`
   - 没有 serving 边界，就不允许上层默认直读数据中台内部目录

### 5.2 可以并行的部分

以下内容可以并行，但前提是共享前置已经冻结：

1. 在 `Milestone A` 中：
   - member 域 field catalog
   - staff 域 field catalog
2. 在 `Milestone B` 中：
   - member 域 connector lane
   - staff 域 connector lane
   - `1.8` 特殊风险 lane
3. 在 `Milestone C` 中：
   - member canonical lane
   - staff canonical lane
   - sync-state lane
   - quality lane
4. 在 `Milestone D` 中：
   - readiness resolver lane
   - member service object lane
   - staff service object lane
   - finance service object lane

### 5.3 哪些并行不能过早开始

以下任务即使可并行，也必须等待前置冻结：

- endpoint-specific connector，必须等待 canonical parameter / variance freeze
- canonical fact fan-out，必须等待 grain / business key freeze
- service object fan-out，必须等待 capability dependency matrix freeze

---

## 6. 里程碑 A：结构与 Contract Freeze

### 6.1 目标

建立 `platforms/data-platform/` 的骨架，并把 `Qinqin v1.1` 的 phase-1 C0 冻结下来。

### 6.2 输入

- `docs/api/qinqin/README.md`
- `docs/api/qinqin/auth-and-signing.md`
- `docs/api/qinqin/endpoint-manifest.md`
- `docs/api/qinqin/member/*.md`
- `docs/api/qinqin/staff/*.md`
- `docs/audits/qinqin/*`
- 本轮已完成的 data-platform spec 文档

### 6.3 主要工作包

#### A1. 建立 repo skeleton

- 以 target repo structure 文档为准建立目录骨架
- 明确每个目录 owner 和 truth boundary

#### A2. 冻结 source / endpoint registry

- 固定 `Qinqin v1.1` source entry
- 固定 8 个正式 endpoint entry
- 固定增量策略 / 档案刷新策略 / 配置覆盖策略

#### A3. 冻结 parameter / field catalog

- 固定 canonical parameter registry
- 记录 `Page/PageIndex`、`STime/Stime`、`ETime/Etime`、`OrgID/OrgId` 等 variance
- 完成 8 个端点字段全量登记

#### A4. 冻结 field landing policy

- 把 manifest target 对应字段先标记为 Tier A
- 明确 Tier B / Tier C 的保存策略

#### A5. 产出 phase-1 capability seeds

- 至少登记：
  - `navly.store.member_insight`
  - `navly.store.daily_overview`
  - `navly.store.staff_board`
  - `navly.store.finance_summary`

补充说明：

- `navly.service.system.capability_explanation` 是 companion explanation object，不应与 capability seed 混淆

### 6.4 输出

- 目标目录骨架
- source / endpoint / parameter / field / capability registry
- canonical capability_id / service_object_id naming freeze
- field landing policy
- variance register
- phase-1 capability seed set

### 6.5 前置依赖

- 无代码前置依赖
- 以现有 docs 为唯一输入前提

### 6.6 可并行项

- member/staff field catalog 可并行
- capability seed 与 field landing policy 可并行

### 6.7 进入下一里程碑前的 checklist

- [ ] 8 个端点全部进入 registry
- [ ] 字段登记覆盖 `docs/api/qinqin/` 中当前文档字段
- [ ] 所有已知命名漂移都进入 variance register
- [ ] manifest structured targets 有明确 landing policy
- [ ] phase-1 capability seed 已冻结
- [ ] canonical `capability_id` / `service_object_id` 规则已冻结并进入 shared contracts / registry
- [ ] 没有把真实 secret 写入公开 spec 或 registry

### 6.8 里程碑验收条件

> 任意后续模块都可以只读 C0，而不再需要直接解析 Markdown 文档或从旧代码猜字段。

---

## 7. 里程碑 B：Raw Replay Backbone

### 7.1 目标

打通可回放、可补数、可分页追溯的 L0 主链路。

### 7.2 输入

- Milestone A 产出的全部 C0 artifact
- 运行时 secret contract（仅 contract，不在 spec 中保存真值）
- phase-1 的调度窗口与 backfill 策略

### 7.3 主要工作包

#### B1. 建立 shared connector substrate

- 统一签名生成
- 统一时间窗解释
- 统一分页策略与 page cursor 语义
- 统一 error taxonomy

#### B2. 打通第一条 vertical slice raw path

- 先完成 `GetCustomersList`
- 再完成 `GetConsumeBillList`
- 跑通 run / endpoint run / page run / raw replay handle

#### B3. 扩展到剩余 member 域

- `GetRechargeBillList`
- `GetUserTradeList`

#### B4. 扩展到 staff 域

- `GetPersonList`
- `GetTechUpClockList`
- `GetTechMarketList`

#### B5. 单独 burn down `1.8` 特殊风险

- `GetTechCommissionSetList`
- 明确 header / auth 差异
- 禁止以“先标 partial”掩盖真实失败类型

#### B6. 建立 daily sync + rerun + backfill workflow

- 主同步
- 补数重跑
- 失败重试
- replay retrieval

### 7.4 输出

- shared qinqin connector substrate
- L0 run / endpoint run / page run model
- raw replay model
- daily sync / rerun / backfill backbone
- 全 8 端点的 raw acquisition capability

### 7.5 前置依赖

- Milestone A 完成

### 7.6 可并行项

- 在 B1 完成后：member / staff 域可以并行
- `1.8` 可以作为独立风险 lane 并行推进
- workflow 定义可与 endpoint fan-out 并行，但必须基于统一 run model

### 7.7 进入下一里程碑前的 checklist

- [ ] 第一条 vertical slice 可完整回放
- [ ] 全 8 端点均可生成 endpoint run 记录
- [ ] 分页级失败可定位
- [ ] source empty / sign failure / auth failure / schema drift / timeout 等错误已分类
- [ ] rerun 不覆盖历史执行真相
- [ ] `1.8` 的失败语义不再落成模糊 `partial`

### 7.8 里程碑验收条件

> 任意一条 phase-1 主题结果都能够回指到对应 raw run / endpoint run / page run / raw payload。

---

## 8. 里程碑 C：Canonical Fact + Latest State

### 8.1 目标

在 L0 基础上建立 canonical fact truth 与 latest state truth，并完成质量闭环。

### 8.2 输入

- Milestone B 的 raw replay outputs
- Milestone A 的 field landing policy / capability seed / variance register

### 8.3 主要工作包

#### C1. 冻结 canonical grain / business key 规则

- customer domain 粒度
- consume / recharge / trade 粒度
- staff / shift / commission / commission setting 粒度

#### C2. 完成第一条 vertical slice 的 L1/L2 闭环

- `customer`
- `consume_bill`
- `consume_bill_payment`
- `consume_bill_info`
- latest state
- dataset availability
- 初始质量快照

#### C3. 扩展到剩余 member 域 canonical landing

- recharge facts
- account trade facts
- 对应 latest state / availability

#### C4. 扩展到 staff 域 canonical landing

- staff facts
- shift facts
- sales commission facts
- commission setting facts

#### C5. 建立 L2 治理对象

- latest sync state
- backfill progress state
- field coverage snapshot
- schema alignment snapshot
- quality issue

### 8.4 输出

- manifest structured targets 的 canonical landing
- latest sync state
- dataset availability snapshots
- field coverage / schema alignment / quality issue
- backfill progress state

### 8.5 前置依赖

- Milestone B 完成
- C1 grain / key 规则先冻结，才能大规模扩展 canonical models

### 8.6 可并行项

- 在 C1 完成后：member / staff canonicalization 可并行
- sync-state 与 quality 可以并行推进，但都依赖已有 L1 landing

### 8.7 进入下一里程碑前的 checklist

- [ ] manifest 声明的 structured targets 都已有 canonical landing
- [ ] latest state 与 historical run truth 已明确分离
- [ ] dataset availability 可解释到 store / date / dataset 粒度
- [ ] field coverage / schema alignment 快照可用
- [ ] `commission_setting` 状态语义已能区分真实空返回、鉴权异常和实现缺口
- [ ] 不再把投影状态冒充 latest state

### 8.8 里程碑验收条件

> 系统已经能清楚回答“哪些事实已经成立、最新可用业务日是什么、为什么可用或不可用”。

---

## 9. 里程碑 D：Readiness + Theme/Service + Serving Boundary

### 9.1 目标

在 L1/L2 已稳定的前提下，建立 readiness truth、theme/service truth 与默认 serving boundary。

### 9.2 输入

- Milestone A 的 capability seeds
- Milestone C 的 canonical facts / latest state / quality artifacts
- external interface spec 中的 serving/readiness contract

### 9.3 主要工作包

#### D1. 冻结 capability dependency matrix

- capability -> dataset dependency
- capability -> scope kind
- capability -> freshness rule

#### D2. 建立 readiness resolver

- 输出 `ready / pending / failed / unsupported_scope`
- 输出 reason code / blocking dependency / trace ref

#### D3. 完成第一条 vertical slice 的 service truth

- `navly.service.store.member_insight`
- explanation object
- readiness + service + traceability 闭环

#### D4. 扩展到剩余 phase-1 service objects

- `navly.service.store.daily_overview`
- `navly.service.store.finance_summary`
- `navly.service.store.staff_board`
- `navly.service.system.capability_explanation`

#### D5. 建立 default serving boundary

- readiness query
- theme service query
- explanation query
- 明确 Copilot 默认只能从此边界读

### 9.4 输出

- capability dependency matrix
- capability readiness snapshots
- 首批 phase-1 canonical service objects
- explanation objects
- serving boundary

### 9.5 前置依赖

- Milestone C 完成
- D1 dependency matrix 冻结后，D3/D4 才允许大规模 fan-out

### 9.6 可并行项

- 在 D1/D2 冻结后：member / finance / staff service object 可并行
- serving transport shape 可与 service object 并行，但不能先于 service truth

### 9.7 Phase-1 完结前的 checklist

- [ ] readiness truth 已有稳定 status + reason code
- [ ] 第一条 vertical slice 已通过 readiness + service 闭环验证
- [ ] phase-1 核心 service objects 可稳定输出
- [ ] explanation object 不依赖 prompt glue 生成核心判断
- [ ] Copilot / runtime 默认只通过 serving boundary 消费
- [ ] 没有默认直读 raw-store / warehouse / sync-state / completeness / projections 的上层路径

### 9.8 里程碑验收条件

> 数据中台已经能作为 Copilot 的默认数据依赖面，而不是让 Copilot 自己重建数据解释逻辑。

---

## 10. 推荐的 domain 扩展顺序

在第一条 vertical slice 成立之后，推荐扩展顺序为：

1. `member-finance slice`
   - `GetRechargeBillList`
   - `GetUserTradeList`
   - 对应 `navly.service.store.finance_summary`
2. `staff-ops slice`
   - `GetPersonList`
   - `GetTechUpClockList`
   - `GetTechMarketList`
   - 对应 `navly.service.store.staff_board`
3. `commission-setting risk slice`
   - `GetTechCommissionSetList`
   - 对应配置解释与 readiness 去歧义
4. `navly.service.store.daily_overview`
   - 在 member + finance + staff 域都已有稳定 truth 后再汇总

原因：

- 先从一个有代表性的 member slice 验证主链路
- 再扩到财务与 staff 域
- 最后处理最特殊、最容易污染状态语义的 `1.8`

---

## 11. A/B/C/D Gate Summary

| Gate | 必须满足 |
| --- | --- |
| A -> B | C0 完整，8 端点 contract 与 field catalog 已冻结 |
| B -> C | L0 可回放，8 端点 raw run 已闭合，错误分类成立 |
| C -> D | L1/L2 已闭合，manifest targets landed，latest state / quality / availability 成立 |
| D -> phase-1 done | readiness truth、service truth、serving boundary 已稳定，上层不再默认穿透内部目录 |

---

## 12. 核心判断

这份 implementation plan 的核心不是“把任务拆得越碎越好”，而是：

- 用 A/B/C/D 四个 gate 保护真相边界
- 用一条 vertical slice 先证明结构正确
- 再把同样的结构扩展到完整 phase-1 范围

这样推进，Navly_v1 数据中台才会先成为长期资产，再成为可运行系统；而不是先堆出可运行的临时实现，再回头补边界。
