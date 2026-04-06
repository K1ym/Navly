# bindings

分层：L1
用途：承载 role / scope / conversation binding、binding_snapshot 与 conversation narrowing backbone。

## 当前 Milestone B 内容

- `role-binding.seed.json`
- `scope-binding.seed.json`
- `conversation-binding.seed.json`
- `binding-snapshot.contract.seed.json`
- `binding-backbone.mjs`

## 当前边界

- conversation binding 可以锚定、收窄、挂起
- conversation binding 不可扩权
- binding_snapshot 是 Gate 0 / capability access 的 owner-side输入
