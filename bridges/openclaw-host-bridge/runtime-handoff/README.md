# Runtime Handoff Skeleton

本目录预留给 bridge <-> runtime interaction boundary。

当前 milestone A 只允许：

- 读取 shared interaction contracts
- 记录 `runtime_request_envelope` 是唯一 canonical handoff 名称
- 记录 `runtime_result_envelope` / `runtime_outcome_event` 是消费对象

当前**不**实现：

- runtime request assembly logic
- runtime result rendering logic
- fail-closed execution path

## shared interaction consumption only

本目录只消费以下 shared schema：

- `shared/contracts/interaction/runtime_request_envelope.schema.json`
- `shared/contracts/interaction/runtime_result_envelope.schema.json`
- `shared/contracts/interaction/runtime_outcome_event.schema.json`

禁止：

- 在本目录重新定义同名 schema
- 使用 legacy handoff alias
