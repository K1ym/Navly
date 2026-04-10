# decision

分层：L2
用途：承载 Gate 0、capability access decision、session grant / fail-closed 逻辑骨架。

## canonical freeze

`access_decision_status` 对齐为：

- `allow`
- `deny`
- `restricted`
- `escalation`

禁止：

- retired legacy escalation alias

## 当前 phase-1 backbone 内容

- `gate0-result.contract.seed.json`
- `access-decision-owner-view.contract.seed.json`
- `gate0-backbone.mjs`
- `capability-access-decision-backbone.mjs`
- `session-grant-snapshot-backbone.mjs`

## 当前边界

- 已实现 Gate 0 与 capability access 的 backbone 级可执行逻辑
- 已实现 `session_grant_snapshot` 的 machine-readable owner-side 闭合
- `allow` 路径默认追加 `emit_audit_event` obligation，要求下游回传 outcome linkage
- 仍未实现 rich policy engine / approval flow / admin surface
- 没有 `decision_ref` 时能力访问必须 fail closed
