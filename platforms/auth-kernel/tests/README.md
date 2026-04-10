# tests

用途：保留 auth-kernel 的模块内测试目录。

当前提供：

- `milestone-b-backbone.test.mjs`
  - 覆盖 actor resolution / binding snapshot / Gate 0 / capability access / fail closed 最小链路
- `milestone-d-governance-backbone.test.mjs`
  - 覆盖 session grant / audit ledger / decision trace / downstream outcome linkage 的 machine-readable 与 fail-closed 行为
