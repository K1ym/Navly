# Business-Day Boundary Policy Registry

状态：`phase_1_contract_frozen`  
对象类型：data-platform governed object  
正式文件：

- `platforms/data-platform/directory/business-day-boundary-policy.seed.json`
- `platforms/data-platform/contracts/business-day-boundary-policy-entry.contract.seed.json`

## 1. 用途

本 registry 用来表达 **business date 是如何从本地时间戳切出来的**，属于 data-platform 的受治理真相。

它明确**不是 runtime config**，也不是以下局部约定：

- 调度器本地常量
- bridge / ingestion / completeness 私有约定

任何上层或下游如果需要 business-day boundary，都应读取本 registry，而不是在代码里硬编码 `03:00`、`04:00` 或其他 cutover 常量。

## 2. Root 语义

`business-day-boundary-policy.seed.json` root 当前冻结以下语义：

| 字段 | 含义 |
| --- | --- |
| `registry_name` | 正式对象名，固定为 `business_day_boundary_policy_registry` |
| `resolution_hierarchy` | override 解析顺序，当前固定为 `store_ref -> org_ref -> global_default` |
| `boundary_interpretation` | 统一换算公式：若本地时间 `>= business_day_boundary_local_time`，business date 取本地日历日；否则回退到前一日 |
| `entries` | 具体 policy entry 列表 |

## 3. Entry 语义

每个 entry 字段由 `business-day-boundary-policy-entry.contract.seed.json` 冻结。

| 字段 | 含义 |
| --- | --- |
| `policy_id` | policy 的稳定标识 |
| `selector_kind` | 匹配层级，允许值：`global_default`、`org_ref`、`store_ref` |
| `org_ref` | org 级覆盖时命中的 org；`global_default` 必须为空 |
| `store_ref` | store 级覆盖时命中的 store；非 `store_ref` entry 必须为空 |
| `timezone` | 本 policy 解释业务日的本地时区 |
| `business_day_boundary_local_time` | 本地 cutover 时间，格式 `HH:MM:SS` |
| `policy_status` | policy 生命周期，当前正式值使用 `policy_frozen` |
| `truth_source_docs` | 该 policy 的审计/输入依据 |
| `notes` | 说明与限定条件 |

## 4. Override 规则

解析目标时间戳时，消费者应：

1. 先确定目标 `store_ref`、`org_ref`
2. 按 `store_ref -> org_ref -> global_default` 查单个最具体命中项
3. 用命中项的 `timezone` 和 `business_day_boundary_local_time` 换算 business date

约束：

- `global_default` entry 不得携带 `org_ref` 或 `store_ref`
- `org_ref` entry 必须携带 `org_ref`，且 `store_ref = null`
- `store_ref` entry 必须携带 `store_ref`；可额外带 `org_ref` 作为审计锚点

## 5. 当前 phase-1 默认值

当前 formal seed 只冻结一个全局默认 policy：

- `timezone = Asia/Shanghai`
- `business_day_boundary_local_time = 03:00:00`

这个 `03:00:00` 不是 runtime 临时设定，而是 data-platform 当前显式治理选择。依据来自：

- `docs/api/qinqin/auth-and-signing.md` 中的正式访问窗口 `03:00-04:00`
- `docs/api/qinqin/endpoint-manifest.md` 中的主同步时间 `03:10`

换言之，phase-1 当前把 `03:00:00` 作为业务日切换点冻结为 registry truth；如果后续有 org 或 store 的差异，再通过 `org_ref` / `store_ref` entry 补充，而不是让 runtime 读环境变量覆盖。

## 6. 变更规则

如果未来发现某个 org/store 需要不同 boundary：

1. 先补审计证据或输入真相
2. 再在本 registry 增加对应 `org_ref` 或 `store_ref` entry
3. 再让下游消费者读取新增 policy

不允许跳过 registry，直接把 override 写进 runtime config 或代码分支。
