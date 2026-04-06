# serving

分层：L3
用途：承载 auth-kernel 对下游的 owner-side access serving boundary。

## 当前 Milestone B 内容

- `access-context-envelope-backbone.mjs`
- `access-chain-backbone.mjs`

## 当前约束

- 这里不拥有 public `access_context_envelope` schema 主定义权
- 当前只负责基于 shared contract 构造 owner-side envelope 输出
- 只有在 Gate 0 / capability access 成立且 scope 已绑定时才会签发 envelope
