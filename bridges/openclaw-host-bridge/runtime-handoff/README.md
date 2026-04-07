# Runtime Handoff Backbone

本目录承载 bridge <-> runtime interaction handoff backbone。

当前 milestone B 已实现：

- `runtime_request_envelope` assembly backbone
- shared interaction consumption only
- fail-closed handoff preconditions

当前**不**实现：

- runtime execution
- runtime result rendering logic
- runtime outcome forwarding

## shared interaction consumption only

本目录只消费以下 shared schema：

- `shared/contracts/interaction/runtime_request_envelope.schema.json`
- `shared/contracts/interaction/runtime_result_envelope.schema.json`
- `shared/contracts/interaction/runtime_outcome_event.schema.json`

禁止：

- 在本目录重新定义同名 schema
- 使用 legacy handoff alias
