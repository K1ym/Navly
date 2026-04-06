# auth-kernel contracts

本目录只保留 `auth-kernel` own-scope contract 说明。

## 当前约束

- milestone A **不**在这里定义跨模块 public access contract
- `access_context_envelope` / `access_decision` / `decision_ref` 等跨模块公共对象，主定义权属于 `shared-contracts`
- 本模块后续只能在 shared contracts 冻结后实现 owner-side mapping / persistence / serving

## 当前状态

- 仅保留目录骨架
- 不新增 public schema，避免越过 `shared-contracts`
