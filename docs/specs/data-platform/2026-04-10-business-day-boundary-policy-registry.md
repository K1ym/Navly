# 2026-04-10 Business-Day Boundary Policy Registry

日期：2026-04-10  
状态：phase-1-contract-frozen  
用途：冻结 Navly data-platform 的 business-day boundary policy registry 语义

## 1. 文档目的

本文档定义：

- business-day boundary policy registry 为什么属于 data-platform governed object
- `global_default / org_ref / store_ref` override hierarchy 的正式语义
- phase-1 当前默认 boundary 为什么冻结为 `Asia/Shanghai` / `03:00:00`
- 当前阶段哪些内容仍然故意不做

## 2. 为什么它必须是 governed object

business date 不是运行时小配置，而是数据中台的基础真相之一。

如果 business-day boundary 被散落在：

- runtime config
- ingestion 常量
- completeness 私有逻辑
- serving 的日期回退代码

那么同一个时间戳可能在不同层被切成不同 business date，最终会直接污染：

- ingestion run 的业务日归属
- latest usable business date
- completeness 判断
- projection / serving 输出
- audit / replay 解释

因此 phase-1 把 boundary policy 放进 `platforms/data-platform/directory/`，并用 owner contract 冻结 entry shape。

## 3. Registry 边界

正式对象：

- `platforms/data-platform/directory/business-day-boundary-policy.seed.json`
- `platforms/data-platform/contracts/business-day-boundary-policy-entry.contract.seed.json`

它表达的是：

- 某个 scope 应采用哪个时区解释 business date
- 业务日在哪个本地时间切换
- 当 `store_ref`、`org_ref`、全局默认同时存在时，哪个 policy 生效

它不表达：

- 调度 cron
- runtime UI 设置
- 单次任务临时覆盖参数
- connector / ingestion 细节实现

## 4. Override Hierarchy

registry root 固定声明：

- `resolution_hierarchy = ["store_ref", "org_ref", "global_default"]`

解释规则：

1. 先尝试命中 `store_ref`
2. 若无 store 级 policy，再尝试命中 `org_ref`
3. 若仍无命中，再退回 `global_default`

唯一性要求：

- 全局默认层最多一个 active/frozen `global_default`
- 同一个 `org_ref` 最多一个 active/frozen `org_ref` policy
- 同一个 `store_ref` 最多一个 active/frozen `store_ref` policy

当前 formal seed 只包含 `global_default`。  
这不是缺功能，而是刻意避免在没有审计证据时捏造 org/store 差异。  
hierarchy 本身已经在 registry root、owner contract 和独立测试中被冻结；后续出现真实 override 时，只需追加对应 entry。

## 5. Phase-1 Default Boundary

phase-1 默认 policy 当前冻结为：

- `timezone = Asia/Shanghai`
- `business_day_boundary_local_time = 03:00:00`

这里的 `03:00:00` 是**从现有仓内输入文档推导出的显式治理选择**，不是 API 文档直接给出的字段。

推导依据：

- `docs/api/qinqin/auth-and-signing.md` 把正式访问窗口写成 `03:00-04:00`
- `docs/api/qinqin/endpoint-manifest.md` 把主同步时间写成 `03:10`

因此 phase-1 先把 `03:00:00` 冻结为默认 cutover：

- `03:00:00` 及之后的本地时间，归到当天 business date
- `03:00:00` 之前的本地时间，归到前一 business date

如果未来 live evidence 证明某个 org/store 的 cutover 不是 `03:00:00`，处理顺序必须是：

1. 先补审计或输入真相
2. 再补 `org_ref` / `store_ref` policy entry
3. 最后才允许消费者使用新的 boundary

## 6. 当前刻意不做的事

本次 ASP-21 故意停在最小 registry / contract / docs / test 范围，不做：

- runtime 消费接线
- ingestion / completeness / serving 下游改造
- UI 配置入口
- connector 特判

如果后续消费者接入需要改别的目录，应另开变更，不在本次 seed freeze 中顺手混入。

## 7. 验收标准

本次 freeze 至少满足：

1. `business-day-boundary-policy.seed.json` 已存在且声明 `store_ref -> org_ref -> global_default`
2. `business-day-boundary-policy-entry.contract.seed.json` 已冻结 entry shape
3. `contract-ownership.seed.json` 已把 `business_day_boundary_policy_entry` 纳入 data-platform owned contracts
4. reference/spec 已明确说明这是 governed object，不是 runtime config
5. 独立测试已验证 root/contract/docs 一致性，以及 hierarchy 语义
