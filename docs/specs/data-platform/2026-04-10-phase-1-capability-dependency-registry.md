# 2026-04-10 Phase-1 Capability Dependency Registry

日期：2026-04-10  
状态：phase-1-contract-frozen  
用途：冻结 Navly data-platform Phase-1 capability dependency matrix 的正式 registry 语义

---

## 1. 文档目的

本文档回答：

1. capability dependency matrix 为什么必须成为 data-platform governed object
2. `member_insight` / `finance_summary` / `staff_board` / `daily_overview` 的 dependency truth 应如何正式表达
3. 为什么不能继续把 dependency truth 留在 placeholder JSON、slice-local 常量或 field-landing 推导逻辑里

---

## 2. 为什么它必须进入 formal registry

如果 Phase-1 capability dependency truth 被散落在：

- `capability-dependency-registry.placeholder.json`
- `finance_summary_vertical_slice.py` 内的局部常量
- `staff_board_vertical_slice.py` 内的 field-landing 推导逻辑
- `daily_overview` 聚合层的私有列表

那么 data-platform 会同时失去：

- 一份统一可审计的 dependency matrix
- readiness / serving / workflow 之间共享的主语义
- 对“谁是 authoritative dependency truth”的明确回答

因此，Phase-1 必须把 capability dependency matrix 升级成 formal registry。

---

## 3. 正式文件

- `platforms/data-platform/directory/capability-dependency-registry.seed.json`
- `platforms/data-platform/directory/capability_dependency_registry.py`
- `platforms/data-platform/contracts/capability-dependency-entry.contract.seed.json`

其中：

- `.seed.json` 是当前 formal registry root 与 entries
- `.py` 是读取 formal registry 的受控 helper
- `contract.seed.json` 冻结 entry shape 与 allowed values

---

## 4. Registry Root 语义

`capability-dependency-registry.seed.json` root 当前冻结以下语义：

| 字段 | 含义 |
| --- | --- |
| `registry_name` | 固定为 `capability_dependency_registry` |
| `status` | 当前冻结为 `phase_1_contract_frozen` |
| `governance_scope` | 当前为 `data-platform-only` |
| `entries` | capability dependency entries |
| `shared_contract_owner_path` | shared contracts 所在路径提示 |

核心判断：

> 这个 registry 是 governed object，不是 placeholder，不是 runtime config，也不是 slice-local helper cache。

---

## 5. Entry 语义

每个 entry 由 `capability-dependency-entry.contract.seed.json` 冻结以下字段：

| 字段 | 含义 |
| --- | --- |
| `capability_id` | 目标 capability |
| `default_service_object_id` | capability 的 canonical default service object |
| `dependency_status` | 当前固定为 `phase_1_contract_frozen` |
| `dependency_kind` | `input_data` 或 `projection` |
| `required_endpoint_contract_ids` | 输入端点依赖 |
| `required_canonical_datasets` | canonical dataset 依赖 |
| `required_service_object_ids` | projection/service 依赖 |
| `truth_source_docs` | 输入依据文档 |
| `notes` | 说明与约束 |

约束：

- `input_data` entry 必须显式给出 endpoint + canonical dataset 依赖
- `projection` entry 必须显式给出 required service object 依赖
- 不适用的 dependency vector 必须显式写空数组

---

## 6. 当前 Phase-1 冻结范围

当前 formal registry 至少覆盖：

- `navly.store.member_insight`
- `navly.store.finance_summary`
- `navly.store.staff_board`
- `navly.store.daily_overview`

其中：

- `member_insight` / `finance_summary` / `staff_board` 使用 `dependency_kind = input_data`
- `daily_overview` 使用 `dependency_kind = projection`

---

## 7. 实施约束

一旦本 registry 进入 formal 状态，以下实现必须改为读取它：

- `member_insight_vertical_slice`
- `finance_summary_vertical_slice`
- `staff_board_vertical_slice`
- 依赖 `daily_overview` dependency truth 的 readiness / serving 聚合层

不允许继续保留：

- `capability-dependency-registry.placeholder.json`
- finance slice 的局部 dependency boundary 常量
- staff slice 的 field-landing-derived authoritative dependency 定义
- 对 aggregate capability 的私有 dependency list 作为主真相

---

## 8. 结论

Phase-1 的 capability dependency matrix 已不再是 planning note，而是 formal registry truth。

这意味着：

- readiness truth 必须从这份 registry 出发
- serving truth 只能消费这份 registry 派生的 dependency semantics
- 后续如果新增 Phase-1 capability 或调整 dependency matrix，必须先改 formal registry，再改 consumer
