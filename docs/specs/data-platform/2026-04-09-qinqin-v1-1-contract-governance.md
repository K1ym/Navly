# 2026-04-09 Qinqin v1.1 Contract Governance Freeze

日期：2026-04-09  
状态：phase-1-contract-frozen  
用途：冻结 Qinqin v1.1 在 Navly data-platform 中的 endpoint / parameter / field / landing / variance formal registry 语义

## 1. 文档目的

本文档定义：

- 哪些文件构成 `Qinqin v1.1` 的正式 contract governance registry
- 每个 registry 在 phase-1 中表达哪一种真相
- runtime / bridge / auth 应该读取哪些对象，而不是继续从 Markdown 或旧实现猜字段

## 2. 正式 registry 清单

`platforms/data-platform/directory/` 下以下文件属于本次 freeze 的正式对象：

- `source-systems.seed.json`
- `endpoint-contracts.seed.json`
- `endpoint-parameter-canonicalization.seed.json`
- `endpoint-field-catalog.seed.json`
- `field-landing-policy.seed.json`
- `source-variance.seed.json`

这些文件共同构成 `Qinqin v1.1` 的 C0 contract truth。

## 3. 每个 registry 的边界

### 3.1 `source-systems.seed.json`

表达 source-level truth：

- source system identity
- access window profile
- shared signature rule
- auth profile

本次 freeze 中，正式访问窗口按北京时间 / `Asia/Shanghai` 的 `03:00-04:00` 处理。

### 3.2 `endpoint-contracts.seed.json`

表达 endpoint identity truth：

- 8 个正式端点 + 1 个 shared virtual contract
- method / path / increment strategy / structured targets / truth source doc

同时通过 `endpoint_governance_bindings` 显式连接：

- endpoint -> parameter keys
- endpoint -> field catalog entry
- endpoint -> landing policies
- endpoint -> auth profile / signature rule / access window profile
- endpoint -> variance entries

之所以把 richer traceability 放在 registry root，而不是 entry 字段里，是为了保持现有 backbone 对 `entries` 的读取兼容。

### 3.3 `endpoint-parameter-canonicalization.seed.json`

表达 request parameter truth：

- canonical parameter key
- preferred wire name
- known wire variants
- request location
- value type / value source
- required / optional endpoint scope
- signature participation
- runtime secret ref

本次 freeze 明确把 `1.8` 的 `Authorization` / `Token` 作为 runtime secret header 纳入参数治理，而不是交给 auth 代码隐式补齐。

### 3.4 `endpoint-field-catalog.seed.json`

表达 documented response field truth。

字段 catalog 采用 **endpoint-scoped ledger**，每个 entry 对应一个 endpoint，内部列出完整 `response_fields`。

每个 `response_fields[]` 项至少包括：

- `field_path`
- `data_type`
- `path_kind`
- `landing_policy_id`

`path_kind` 用于消除未来消费方的猜测，当前至少覆盖：

- `response_status`
- `response_message`
- `payload_root`
- `page_total`
- `record_collection`
- `record_field`
- `nested_record_collection`
- `nested_record_field`
- `summary_object`
- `summary_field`

### 3.5 `field-landing-policy.seed.json`

表达字段落点真相：

- 哪些字段只保留在 raw truth
- 哪些字段进入 L1 structured datasets
- 一个 field group 对应哪个 canonical target dataset

`field_selector` 使用小型 selector 语法：

- `explicit:[...]`
- `prefix:...`
- `exclude_prefixes:[...]`
- `multi:[...]`

但 future consumer 不应依赖 selector 自行推断；应优先读取 field catalog 中已经指向的 `landing_policy_id`。

### 3.6 `source-variance.seed.json`

表达受治理差异真相：

- parameter name drift
- live path constraint
- response shape drift
- auth header requirement
- documented field name drift

任何已知差异都必须进入 variance register，而不是散在注释、调试脚本或 bridge 特判里。

## 4. 运行边界

本次 freeze 后：

- Markdown 仍然是输入文档真相源
- 机器消费的正式界面是 registry，不是 Markdown

因此：

- runtime 不应猜参数名 / path / response root shape
- bridge 不应猜 legacy path 或额外 header
- auth 不应猜哪些 header 需要 runtime secret 注入

如果 future implementation 发现 live 行为与 registry 不一致，处理顺序必须是：

1. 先补审计证据
2. 再补 variance register
3. 再更新对应 registry
4. 最后才允许实现层读取新的治理对象

## 5. 验收标准

本次 contract governance freeze 至少要满足：

1. `endpoint-contracts.seed.json` 中 8 个正式端点可完整追溯到 parameter / field / landing / variance 对象
2. `endpoint-field-catalog.seed.json` 不再存在 `placeholder_only`
3. `1.8` 的 runtime auth headers 已显式建模
4. `1.4` / `1.5` / `1.7` 的 `RetData` root shape drift 已进入 variance register
5. 相关测试能校验 registry 与 `docs/api/qinqin/**` 的一致性
