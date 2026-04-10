# Capability Dependency Registry

状态：`phase_1_contract_frozen`  
对象类型：data-platform governed object  
正式文件：

- `platforms/data-platform/directory/capability-dependency-registry.seed.json`
- `platforms/data-platform/directory/capability_dependency_registry.py`
- `platforms/data-platform/contracts/capability-dependency-entry.contract.seed.json`

## 1. 用途

本 registry 用来表达 **Phase-1 capability dependency matrix**，属于 data-platform 的受治理真相。

它明确不是：

- placeholder
- runtime config
- slice-local 常量
- 由 field landing policy 临时推导出的私有列表

任何 ingestion / completeness / serving / workflow 如果需要 capability dependency truth，都应读取这份 registry。

## 2. 当前覆盖范围

当前 formal entries 包括：

- `navly.store.member_insight`
- `navly.store.finance_summary`
- `navly.store.staff_board`
- `navly.store.daily_overview`

## 3. 依赖类型

当前 `dependency_kind` 只冻结两类：

- `input_data`
  - 表示 capability 依赖正式 endpoint / canonical dataset
- `projection`
  - 表示 aggregate capability 依赖已发布 service object

## 4. 当前关键结论

- `member_insight` / `finance_summary` / `staff_board` 的 dependency truth 已进入 formal registry
- `daily_overview` 的 aggregate dependency truth 也已进入 formal registry
- `capability-dependency-registry.placeholder.json` 已移除，不再允许作为 dependency matrix placeholder

## 5. 变更规则

如果未来 capability dependency 需要变化：

1. 先更新 formal registry 与 contract
2. 再更新 consumer
3. 再更新相关 tests / docs

不允许跳过 registry，直接在单个 slice 内修改 authoritative dependency truth
