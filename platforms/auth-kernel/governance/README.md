# governance

分层：L3
用途：承载 audit ledger、decision trace、override / review trail。

## 当前 backbone

- `audit-event-ledger-backbone.mjs`
- `downstream-outcome-linkage-backbone.mjs`

## 当前边界

- `audit_event_ledger` 收口 actor/binding/decision/grant/envelope/outcome 的治理事件
- downstream outcome linkage 必须同时对齐 `decision_ref`、`session_grant_snapshot_ref`、capability、scope
- linkage 缺失或不一致时直接 fail closed，不接受自然语言或业务特例补丁
- 这里不拥有 runtime/data-platform 业务结果真相，只负责权限链路的治理关联
