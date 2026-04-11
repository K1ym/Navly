# Navly_v1 thin runtime shell

状态：phase-1 multi-capability guarded execution surface
用途：在 `runtimes/navly-runtime/` 内闭合 Phase-1 store runtime surface：route closure + guarded execution + runtime result closure。

## 当前范围（ASP-18 / Milestone B）

本目录当前实现：

- `runtime_request_envelope` ingress 校验与 `runtime_interaction_context` 归一化
  - 顶层 `decision_ref` 与 `access_context_envelope.decision_ref` 失配时 fail closed
- capability route resolution closure（`capability_id`）
- default service binding selection closure（`service_object_id`）
- companion explanation service binding closure（`navly.service.system.capability_explanation`）
- capability access decision call wiring（消费 access truth）
- capability readiness query wiring（消费 readiness truth）
- theme service query wiring（消费 service truth）
- readiness-blocked explanation companion query wiring
- owner-side auth/data adapter closure（可消费真实 owner surface）
  - `member_insight` / `daily_overview` / `staff_board` / `finance_summary` 默认不再消费内部 summary/backbone shape，而是消费 data-platform formal owner-side readiness / theme service surface
- `runtime_result_envelope` 主路径闭合（answered / fallback / escalated / rejected / runtime_error）
- `runtime_outcome_event` 对齐输出
- Milestone A/B 自检脚本与最小链路测试

本轮明确不做：

- rich orchestration
- LangGraph integration
- 跨 capability 编排
- prompt glue / query glue 回归

## owning boundary

- 只写 `runtimes/navly-runtime/**`
- runtime 只消费：
  - access truth（`access_context_envelope` / `access_decision`）
  - readiness truth（`capability_readiness_response`）
  - service truth（`theme_service_response`）
- runtime 不直读 raw / warehouse / auth internal state

## 当前 Phase-1 capability surface

当前默认支持的 store capability：

- `navly.store.member_insight`
- `navly.store.daily_overview`
- `navly.store.staff_board`
- `navly.store.finance_summary`

默认 `service_object_id`：

- `navly.service.store.member_insight`
- `navly.service.store.daily_overview`
- `navly.service.store.staff_board`
- `navly.service.store.finance_summary`

companion explanation binding：

- `navly.service.system.capability_explanation`
- 仅在 capability 显式可判定时作为受控 companion service binding 使用

主链路：

```text
runtime_request_envelope
  -> runtime_interaction_context
  -> capability_route_result
  -> runtime_execution_plan
  -> capability access decision
  -> capability readiness query
  -> theme service query
  -> runtime_result_envelope
  -> runtime_outcome_event
```

## 当前 backbone 文件

- `contracts/shared-contract-alignment.mjs`
- `ingress/runtime-ingress-backbone.mjs`
- `routing/capability-route-backbone.mjs`
- `execution/guarded-execution-backbone.mjs`
- `execution/runtime-chain-backbone.mjs`
- `answering/runtime-result-backbone.mjs`
- `outcome/runtime-outcome-event-backbone.mjs`

## 自检

- `scripts/validate-milestone-a.sh`
- `scripts/validate-milestone-b.sh`
- `node --test tests/milestone-b-guarded-execution.test.mjs`

## canonical freeze

- `runtime_result_status` 只允许 shared 主枚举：
  - `answered`
  - `fallback`
  - `escalated`
  - `rejected`
  - `runtime_error`
- `runtime_request_envelope.decision_ref` 的 canonical 语义是当前 handoff 绑定的 `access_context_envelope.decision_ref`
- `gate0_decision_ref` 不是 runtime handoff 顶层 canonical 字段；bridge 若要保留，只能放在 bridge local metadata / `delivery_hint`
- runtime route 只围绕 `capability_id` / `service_object_id`
- `navly.service.system.capability_explanation` 是 companion service binding，不是 bridge-side补丁逻辑
- 没有有效 access context / decision 时 fail closed

## 参考文档

- `docs/specs/navly-v1/runtime/2026-04-06-navly-v1-thin-runtime-phase-1.md`
- `docs/specs/navly-v1/runtime/2026-04-06-navly-v1-thin-runtime-external-interfaces.md`
- `docs/specs/navly-v1/runtime/2026-04-06-navly-v1-thin-runtime-implementation-plan.md`
- `docs/specs/navly-v1/shared-contracts/2026-04-06-navly-v1-shared-contracts-interaction.md`
