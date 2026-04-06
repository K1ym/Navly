# Navly Shared Contracts

本目录是 `Navly_v1` shared-contracts implementation phase-1 / milestone A 的代码骨架。

当前采用：

- **JSON Schema Draft 2020-12** 作为 schema seed 格式
- **family-first** 目录组织：`capability/`、`access/`、`readiness/`、`service/`、`interaction/`、`trace/`、`enums/`
- **seed + placeholder** 策略：P0 对象采用结构化 seed；非本轮重点对象先用 placeholder 收口目录与命名

## 当前范围

本轮只覆盖 milestone A/B 以及用户明确要求先冻结的主枚举 seed：

- capability family
- access family
- readiness family
- service family
- interaction family
- trace family
- enums family

## 当前优先完成的对象

- `capability_definition`
- `access_context_envelope`
- `access_decision`
- `capability_readiness_query`
- `capability_readiness_response`
- `theme_service_query`
- `theme_service_response`
- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

## 当前已冻结的主枚举 seed

- `access_decision_status`
- `readiness_status`
- `service_status`
- `runtime_result_status`
- `scope_kind`
- `freshness_mode`

## 当前仍保持 placeholder 的对象

以下对象本轮只做 seed/placeholder，不推进 full implementation：

- `capability_scope_requirement`
- `capability_service_binding`
- `blocking_dependency_ref`
- `capability_explanation_object`
- `data_access_audit_event`
- `readiness_reason_code`
- `capability_kind`

## 约束

- 不在此目录定义 data truth 或 access truth 算法
- 不在此目录落宿主私有对象、OpenClaw 内部对象或 runtime prompt 细节
- `metadata` / `extensions` 只作为受治理扩展位，不承担核心字段职责
