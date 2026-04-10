# serving

分层：L3
用途：承载 auth-kernel 对下游的 owner-side access serving boundary。

## 当前 phase-1 backbone 内容

- `access-context-envelope-backbone.mjs`
- `access-chain-backbone.mjs`
- `decision-trace-view-backbone.mjs`

## canonical entrypoint

- `runAuthKernelAccessChain` 是 serving 层当前唯一 canonical access-chain entrypoint
- `runMilestoneBAccessChain` 仅保留为 deprecated compatibility alias，供尚未迁移的 runtime / bridge 调用方过渡

## 当前约束

- 这里不拥有 public `access_context_envelope` schema 主定义权
- 当前只负责基于 shared contract 构造 owner-side envelope 输出与 trace view
- 只有在 Gate 0 / capability access 成立、`session_grant_snapshot` 已签发且 scope 已绑定时才会签发 envelope
- envelope extension 默认携带 `binding_snapshot_ref` 与 `session_grant_snapshot_ref`
