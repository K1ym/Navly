# 2026-04-06 Navly_v1 shared-contracts 目标目录骨架说明

日期：2026-04-06  
状态：implementation-baseline  
用途：定义 `shared/contracts/` 的目标目录骨架、对象分组与 schema 文件落位原则

---

## 1. 目标

`shared/contracts/` 必须让跨模块共享语言在目录上可见，而不是把所有 schema 堆在一个文件夹里。

---

## 2. 推荐骨架

```text
shared/
  contracts/
    README.md
    capability/
    access/
    readiness/
    service/
    interaction/
    trace/
    enums/
```

---

## 3. 分组职责

### `capability/`
- capability_definition
- capability_scope_requirement
- capability_service_binding

### `access/`
- actor/session/decision/scope refs
- access_context_envelope
- access_decision

### `readiness/`
- capability_readiness_query
- capability_readiness_response
- blocking_dependency_ref

### `service/`
- theme_service_query
- theme_service_response
- capability_explanation_object

### `interaction/`
- runtime_request_envelope
- runtime_result_envelope
- runtime_outcome_event

### `trace/`
- trace_ref
- state_trace_ref
- run_trace_ref
- audit event shared fields

### `enums/`
- access_decision_status
- readiness_status
- service_status
- runtime_result_status
- readiness_reason_code
- scope_kind
- freshness_mode

---

## 4. 文件组织原则

- 一个对象家族一个目录
- 主 schema 与样例分开
- 核心对象优先落 JSON Schema / YAML Schema 均可，但必须统一
- `extensions` 不得代替核心字段

---

## 5. 核心结论

shared-contracts 的目录骨架本身就是防漂移手段；只有把 capability/access/readiness/service/interaction/trace/enums 分开，跨模块 schema 才能长期稳定演进。
