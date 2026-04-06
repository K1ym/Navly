# 2026-04-06 Navly_v1 数据中台内部分层方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 数据中台内部控制层、原始层、事实层、状态层、服务层的分层结构，以及 4 个模块到分层的映射关系

---

## 1. 文档目的

本文档回答：

> 数据中台内部不是只有“采集 -> 落库 -> 查询”这么粗的三层，而是应当如何按真相边界分层，才能保证原始真相、事实真相、状态真相、可答真相不混淆？

---

## 2. 分层总图

建议采用 **C0 + L0-L3** 的逻辑分层：

```text
C0 契约与治理控制层
  -> L0 原始采集与回放层
  -> L1 标准事实层
  -> L2 状态与治理层
  -> L3 可答性与主题服务层
```

其中：

- `C0` 不是业务数据层，而是元数据与契约控制层
- `L0-L3` 是数据真相逐步收敛并对外服务的主链路

---

## 3. 分层原则

### 3.1 每层只表达一种主真相

- `C0`：契约真相
- `L0`：原始执行与原始回放真相
- `L1`：标准事实真相
- `L2`：状态、覆盖、质量、可答状态真相
- `L3`：主题服务与默认消费真相

### 3.2 readiness 必须与 projection 分开存放语义

虽然 readiness 与 theme service 同属 M4 模块，但它们不是同一种真相：

- readiness 是“是否能答、为什么不能答”的状态真相
- theme service 是“现在应该给上层什么对象”的服务真相

因此 readiness 结果应写入 `L2`，theme service 对象写入 `L3`。

### 3.3 上层默认只读 L3

Copilot 默认读取：

- `L3` 的 theme service object
- 由 `L3` 或其受控接口暴露的 explanation object

而不是直接读取 `L1` / `L2` 物理表。

### 3.4 权限内核不进入数据平台内部写路径

权限内核只在读边界提供 access context，不写 `C0-L3` 的业务真相表。

---

## 4. 分层总览表

| 层 | 逻辑命名空间（建议） | 拥有的真相 | 主要写入模块 | 主要读取模块 |
| --- | --- | --- | --- | --- |
| C0 | `contract` / `catalog` | source、endpoint、field、capability 契约真相 | M1 | M2、M3、M4 |
| L0 | `raw` | raw request/response、历史执行真相、回放索引 | M2 | M3、审计工具 |
| L1 | `core` | 维表、事实表、标准业务对象真相 | M3 | M4、审计/对账工具 |
| L2 | `state` | latest usable state、backfill progress、field coverage、schema alignment、capability readiness | M3、M4 | M4、运营治理工具 |
| L3 | `service` | theme snapshot、service object、default serving contract | M4 | Copilot、其他消费方 |

---

## 5. C0 契约与治理控制层

### 5.1 层职责

C0 负责把“输入真相源”与“内部治理口径”固定下来，供所有数据层共享。

至少包括：

- source system registry
- endpoint registry
- parameter canonicalization registry
- field catalog
- field landing policy
- capability registry
- capability dependency registry
- source variance register

### 5.2 这层为什么必须独立

如果没有 C0：

- M2 会自己发明参数名和请求语义
- M3 会自己猜字段落点
- M4 会自己猜 capability 依赖

这会重新回到旧系统的“隐式硬编码”状态。

### 5.3 读写规则

- 只允许 M1 写入 C0
- M2 / M3 / M4 只读 C0
- 审计材料可以触发 C0 更新，但不能绕过 M1 直接修改运行时 contract

---

## 6. L0 原始采集与回放层

### 6.1 层职责

L0 保存“数据源到底返回了什么、系统到底怎样调用过它”的原始执行真相。

至少包括：

- ingestion run
- endpoint run
- page run
- raw request envelope
- raw response envelope
- raw response page
- replay handle
- raw error event

### 6.2 这层的关键价值

L0 的目标不是给业务直接读，而是：

- 防丢字段
- 支持全历史重放
- 解释采集错误
- 证明 M3 / M4 的结论可追溯

### 6.3 读写规则

- 只允许 M2 写入 L0
- M3 可从 L0 提取、展开、标准化
- Copilot 不得直接读取 L0

---

## 7. L1 标准事实层

### 7.1 层职责

L1 是 Navly 数据中台的标准业务事实真相源。

当前 phase-1 至少要覆盖 `endpoint-manifest.md` 中声明的结构化目标：

- `customer`
- `customer_card`
- `customer_ticket`
- `customer_coupon`
- `consume_bill`
- `consume_bill_payment`
- `consume_bill_info`
- `recharge_bill`
- `recharge_bill_payment`
- `recharge_bill_ticket`
- `recharge_bill_sales`
- `account_trade`
- `staff`
- `staff_item`
- `tech_shift_item`
- `tech_shift_summary`
- `sales_commission`
- `commission_setting`
- `commission_setting_detail`

### 7.2 L1 的边界

L1 负责：

- 结构化事实
- 统一主键 / 业务键
- 跨页去重与幂等更新
- 时间与门店粒度归一

L1 不负责：

- 表达“当前是否 ready”
- 表达“某能力为什么不能答”
- 表达“最终给 Copilot 什么服务对象”

### 7.3 读写规则

- 只允许 M3 写入 L1
- M4 只读 L1，不反向写业务事实
- 临时分析可以读 L1，但不能绕过 L3 成为上层默认接口

---

## 8. L2 状态与治理层

### 8.1 层职责

L2 负责表达“现在数据平台处于什么状态、能不能用、缺了什么、为什么缺”。

至少包括四类对象：

1. **latest usable state**
   - 某 dataset / store / business_date 当前是否可用
2. **历史回溯与覆盖状态**
   - backfill progress、source window coverage
3. **质量与对齐状态**
   - field coverage、schema alignment、quality issue
4. **capability readiness**
   - 某 capability 为什么 ready / pending / failed

### 8.2 为什么 readiness 属于 L2

readiness 是状态真相，而不是展示对象。

如果把 readiness 直接混进 projection / theme service：

- 会导致解释与对象耦合
- 会让“为什么不能答”和“当前返回什么对象”混成同一张表
- 会破坏“状态真相”和“服务真相”分离

### 8.3 推荐最小对象

- `latest_sync_state`
- `dataset_availability_snapshot`
- `backfill_progress_state`
- `field_coverage_snapshot`
- `schema_alignment_snapshot`
- `quality_issue`
- `capability_readiness_snapshot`

### 8.4 读写规则

- M3 写入 dataset / sync / quality 类状态
- M4 写入 capability readiness
- Copilot 不直接读 L2 物理表，只读其受控暴露结果

---

## 9. L3 可答性与主题服务层

### 9.1 层职责

L3 是数据中台默认对外消费层。

它把 L1 / L2 的复杂性收敛成：

- theme snapshot
- service object
- explanation object
- trace reference

### 9.2 phase-1 推荐主题对象

phase-1 建议至少沉淀：

- `navly.service.store.daily_overview`
- `navly.service.store.member_insight`
- `navly.service.store.staff_board`
- `navly.service.store.finance_summary`
- `navly.service.system.capability_explanation`

其中 `navly.service.system.capability_explanation` 是解释对象，不是上层 prompt 文本。  
如需文档短名，可使用：

- `store_daily_overview`
- `store_member_insight`
- `store_staff_board`
- `store_finance_summary`
- `capability_explanation`

但这些短名不应继续作为跨模块 canonical `service_object_id`。

### 9.3 读写规则

- 只允许 M4 写入 L3
- Copilot 默认只读 L3
- 其他消费者若确需直读 L1 / L2，必须作为显式审计 / 治理场景列外，不可成为默认模式

---

## 10. 模块与分层映射

| 模块 | C0 | L0 | L1 | L2 | L3 |
| --- | --- | --- | --- | --- | --- |
| M1 数据契约与接口接入 | 主写入 | - | - | - | - |
| M2 数据采集与原始回放 | 只读 | 主写入 | - | 仅写历史执行辅助状态（如 run metadata） | - |
| M3 标准事实与状态治理 | 只读 | 只读 | 主写入 | 主写入（sync / quality / coverage） | - |
| M4 可答性与主题服务 | 只读 | 禁止直连作为默认路径 | 只读 | 写 readiness | 主写入 |

---

## 11. 跨层依赖规则

### 11.1 允许的依赖方向

```text
C0 -> L0 -> L1 -> L2 -> L3
```

同时允许：

- `C0 -> L1`
- `C0 -> L2`
- `C0 -> L3`

因为 contract / capability metadata 会影响所有后续层。

### 11.2 禁止的依赖方向

- `L3 -> L1` 的反向写入
- `L3 -> L0` 的直接 raw 依赖
- `L2` 直接替代 `L1` 成为事实真相源
- `L1` 直接替代 `L2` 表达 readiness

### 11.3 典型错误写法

以下写法都应视为架构错误：

1. 用 `raw_response_page` 直接给 Copilot 拼答案
2. 用事实表更新时间冒充 latest usable state
3. 用 projection 表状态冒充 readiness state
4. 在 Copilot 内自己写一套 capability dependency 判断

---

## 12. 长期资产与可替换实现的分层判断

| 层 | 长期资产 | 可替换实现 |
| --- | --- | --- |
| C0 | registry、catalog、policy、dependency contract | 文档解析器、registry 生成脚本 |
| L0 | raw replay model、historical run semantics | 调度器、HTTP client、payload 存储介质 |
| L1 | canonical schema、业务键、幂等规则 | dbt / SQL / batch engine 的具体实现 |
| L2 | state semantics、reason taxonomy、coverage rules | 某个 dashboard、某个质量框架 |
| L3 | service contract、theme object schema、traceability contract | REST / GraphQL / cache / BFF 包装方式 |

---

## 13. 核心判断

Navly_v1 数据中台内部不应被建成：

- 一个大 ETL 目录
- 一套混杂的状态表
- 一层随用随拼的 query glue

而应被建成：

- `C0` 固定边界
- `L0` 保真回放
- `L1` 沉淀事实
- `L2` 表达状态
- `L3` 稳定供用

这也是数据中台能长期复用、可审计、可回溯、可替换上层的前提。
