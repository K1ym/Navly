# 2026-04-10 Navly Data Platform Business-Day Boundary Policy Registry

日期：2026-04-10  
状态：phase-1-policy-frozen  
用途：定义业务日边界 policy object 在 data-platform C0 中的正式落点、覆盖层级与当前非目标

---

## 1. 目标

把“业务日按几点切换”从零散实现细节提升为正式的 data-platform governed policy object。

本轮要求：

1. registry root 可被机器读取
2. entry contract 明确字段边界
3. 能表达 global / org / store override
4. 不要求本轮一次性打通所有下游消费方

---

## 2. 为什么它属于 data-platform

业务日边界会影响：

- ingestion window attribution
- canonical facts 的业务日归属
- latest usable state 的日期解释
- daily / finance / staff 类 service object 的日期口径

因此它必须属于：

- data-platform C0 governed registry layer

而不是：

- auth-kernel
- runtime route / prompt
- 某个 SQL / connector 内的硬编码常量

---

## 3. 当前正式对象

### 3.1 Registry root

- `platforms/data-platform/directory/business-day-boundary-policy.seed.json`

### 3.2 Entry contract

- `platforms/data-platform/contracts/business-day-boundary-policy-entry.contract.seed.json`

### 3.3 当前 override hierarchy

```text
store_ref > org_ref > global_default
```

当前 selection rules：

1. 先取更具体 scope
2. 同 scope 下取已生效且 `effective_from` 更晚的 policy
3. `effective_to` 若存在，则按 exclusive end 处理

---

## 4. 当前 metric domains

本轮先冻结以下 metric domains：

- `store_operating_day`
- `store_daily_overview`
- `store_finance_summary`
- `store_staff_board`

说明：

- 这些 domain 是当前受治理集合
- 不代表本轮已经把所有下游消费链打通

---

## 5. 当前非目标

本轮明确不做：

1. runtime 直接消费该 policy
2. auth-kernel 感知该 policy
3. Web/Admin 编辑面
4. 历史回填任务的全面改造
5. 多时区复杂推导引擎

---

## 6. 验收线

本轮通过线：

1. registry root 已正式落在 `directory/`
2. entry contract 已正式落在 `contracts/`
3. contract ownership 已登记该对象
4. 有 dedicated test 校验 registry 结构、override 层级与基本字段合法性

满足以上条件后，业务日边界 policy 就从“概念”变成“正式可治理对象”。
