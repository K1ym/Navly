# Data Platform Business-Day Boundary Policy

类型：reference  
状态：phase-1-policy-frozen  
用途：说明 data-platform C0 中受治理的业务日边界 policy object

---

## 1. 定位

业务日边界 policy 用来回答：

- 某个指标域按什么本地时间切日
- 当存在 global / org / store 多层覆盖时，谁优先
- 哪个 policy 在某个生效时间点应被下游采用

它属于：

- data-platform C0 governed registry layer

它**不**属于：

- auth-kernel
- runtime config
- prompt / SQL / connector 内的硬编码

---

## 2. 当前 authoritative objects

当前 authoritative registry：

- `platforms/data-platform/directory/business-day-boundary-policy.seed.json`

当前 entry contract：

- `platforms/data-platform/contracts/business-day-boundary-policy-entry.contract.seed.json`

---

## 3. 当前 override hierarchy

当前固定：

```text
store_ref > org_ref > global_default
```

同一层级内的选择规则：

1. 只取当前已生效的 policy
2. 若多条都生效，则优先 `effective_from` 更晚的一条
3. `effective_to` 若存在，则按 exclusive end 解释

---

## 4. 当前边界

本轮只完成：

- governed registry object
- override hierarchy shape
- basic validation baseline

本轮不完成：

- ingestion / warehouse / serving 的全面消费
- Web/Admin 编辑面
- 多时区复杂推导引擎
