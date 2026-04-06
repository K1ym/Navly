# Navly_v1 auth-kernel

状态：milestone-a-skeleton  
用途：建立 `platforms/auth-kernel/` 的 phase-1 / milestone A 目录骨架与 C0 seed

## 当前范围

本目录当前只实现 milestone A：

- 目录骨架
- C0 vocabulary / taxonomy seed
- 最小校验脚本

本轮**不**实现：

- policy engine
- actor resolution logic
- binding persistence logic
- Gate 0 runtime logic
- data-platform logic
- 任何 public shared contract owner implementation

## owning boundary

- `auth-kernel` 是 access truth 的 owner module
- 但 **shared contracts 的 public access contract 主定义权不在这里**
- `platforms/auth-kernel/contracts/` 当前只保留 owner-scope 说明，不在 milestone A 内私自定义 `access_context_envelope` / `access_decision` 公共契约
- OpenClaw 的 `host_session_ref` / `host_workspace_ref` 只能作为 ingress evidence，不能直接当 canonical truth

## 当前骨架

```text
platforms/auth-kernel/
  README.md
  docs/
  contracts/
  policy-catalog/
  ingress-evidence/
  actor-registry/
  bindings/
  decision/
  governance/
  serving/
  migration/
  scripts/
  tests/
```

## 当前 C0 seed

当前已建立：

- actor type vocabulary placeholder
- role catalog placeholder
- scope taxonomy placeholder
- namespaced capability vocabulary placeholder
- access decision status alignment
- reason taxonomy placeholder
- restriction taxonomy placeholder
- obligation taxonomy placeholder

## canonical freeze

当前冻结以下 canonical：

- `capability_id` 统一采用 namespaced canonical 风格
- `access_decision_status` 统一为：
  - `allow`
  - `deny`
  - `restricted`
  - `escalation`
- 不再使用旧的 legacy escalation 状态别名

## 参考文档

- `docs/specs/navly-v1/auth-kernel/2026-04-06-navly-v1-auth-kernel-phase-1.md`
- `docs/specs/navly-v1/auth-kernel/2026-04-06-navly-v1-auth-kernel-target-repo-structure.md`
- `docs/specs/navly-v1/2026-04-06-navly-v1-shared-contracts-layer.md`
