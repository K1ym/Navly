# Runtime Handoff Backbone

本目录承载 bridge <-> runtime interaction handoff backbone。

当前 milestone B 已实现：

- `runtime_request_envelope` assembly backbone
- canonical `decision_ref` handoff closure
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

## canonical decision_ref handoff

- `runtime_request_envelope` 是 bridge -> runtime 的唯一 canonical handoff object
- `runtime_request_envelope.decision_ref` 必须等于 `access_context_envelope.decision_ref`
- `gate0_decision_ref` 只保留在 bridge local metadata 中，例如：
  - `authorized_session_link`
  - `delivery_hint`
  - host trace / dispatch 侧本地关联字段
- 如果 Gate 0、`authorized_session_link`、`access_context_envelope` 之间的 decision refs 缺失或不一致，则本目录必须 fail closed，不得产出 handoff envelope
