# Navly_v1 auth-kernel

状态：milestone-d-backbone
用途：在 `platforms/auth-kernel/` 下推进 phase-1 从 binding/decision 到 serving/governance 的闭环，实现 machine-readable、fail-closed 的权限主链路。

## 当前范围

本目录当前实现到 Milestone D：

- milestone A 目录骨架与 C0 seed
- actor resolution backbone
- role / scope / conversation binding backbone
- binding_snapshot generation
- Gate 0 closure
- capability access decision skeleton
- session_grant_snapshot closure
- access_context_envelope owner-side consumption mapping
- audit_event_ledger / decision_trace_view / downstream outcome linkage skeleton
- milestone A / B 自检脚本与 phase-1 backbone tests

本轮**不**实现：

- rich policy engine
- admin UI
- external governance surface
- bridge/runtime/data-platform 模块逻辑
- 任何 public shared contract owner rewrite

## owning boundary

- `auth-kernel` 是 access truth owner module
- `shared/contracts` 仍然拥有 public access / capability / trace 契约主定义权
- `auth-kernel` 在本目录中只做 owner-side backbone、shared contract alignment 与受控输出构造
- OpenClaw 的 `host_session_ref` / `host_workspace_ref` / `host_conversation_ref` 只作为 host evidence 进入解析链，不能直接升级为 canonical access truth

## 当前链路闭合范围

当前已能闭合的最小 access 链路：

```text
host evidence
  -> actor resolution
  -> role / scope / conversation binding
  -> binding_snapshot
  -> Gate 0
  -> capability access decision
  -> session_grant_snapshot
  -> access_context_envelope
  -> audit_event_ledger
  -> decision_trace_view
```

## 当前 backbone 文件

- `contracts/shared-contract-alignment.mjs`
- `policy-catalog/policy-catalog-loader.mjs`
- `actor-registry/actor-resolution-backbone.mjs`
- `bindings/binding-backbone.mjs`
- `decision/gate0-backbone.mjs`
- `decision/capability-access-decision-backbone.mjs`
- `decision/session-grant-snapshot-backbone.mjs`
- `governance/audit-event-ledger-backbone.mjs`
- `governance/downstream-outcome-linkage-backbone.mjs`
- `serving/access-context-envelope-backbone.mjs`
- `serving/access-chain-backbone.mjs`
- `serving/decision-trace-view-backbone.mjs`

## 自检

- `platforms/auth-kernel/scripts/validate-milestone-a.sh`
- `platforms/auth-kernel/scripts/validate-milestone-b.sh`

## canonical freeze

当前继续冻结以下 canonical：

- `access_decision_status` 只能是：
  - `allow`
  - `deny`
  - `restricted`
  - `escalation`
- `capability_id` 必须保持 namespaced canonical 风格
- 没有 `decision_ref` 就必须 fail closed
- 没有 `session_grant_snapshot_ref` 或 linkage 不匹配时，下游 outcome 不能挂回治理链
- conversation binding 只能锚定/收窄/挂起，不能扩权

## 参考文档

- `docs/specs/navly-v1/auth-kernel/2026-04-06-navly-v1-auth-kernel-phase-1.md`
- `docs/specs/navly-v1/auth-kernel/2026-04-06-navly-v1-auth-kernel-external-interfaces.md`
- `docs/specs/navly-v1/auth-kernel/2026-04-06-navly-v1-auth-kernel-implementation-plan.md`
- `docs/specs/navly-v1/shared-contracts/2026-04-06-navly-v1-shared-contracts-core-objects.md`
