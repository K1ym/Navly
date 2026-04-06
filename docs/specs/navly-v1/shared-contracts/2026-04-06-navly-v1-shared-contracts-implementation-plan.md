# 2026-04-06 Navly_v1 shared-contracts Implementation Plan

日期：2026-04-06  
状态：phase-1-executable-plan  
用途：把 shared-contracts 从文档方案推进到 schema seed / enum seed / interaction seed 的实施顺序

---

## 1. 实施目标

phase-1 的 shared-contracts 先完成：

- namespaced IDs
- refs
- access/readiness/service 主 envelope
- interaction 主 envelope
- 主枚举

---

## 2. 里程碑

### Milestone A：schema family skeleton

输出：
- capability/access/readiness/service/interaction/trace/enums 目录骨架
- 每个 family 的 schema placeholder

### Milestone B：P0 object seed

输出：
- capability_definition
- access_context_envelope
- access_decision
- capability_readiness_query/response
- theme_service_query/response
- runtime_request_envelope
- runtime_result_envelope
- runtime_outcome_event

### Milestone C：enum seed

输出：
- access_decision_status
- readiness_status
- service_status
- runtime_result_status
- readiness_reason_code
- scope_kind
- freshness_mode

### Milestone D：trace / audit seed

输出：
- trace_ref family
- data_access_audit_event shared fields
- outcome-to-trace linkage notes

---

## 3. 串并行规则

### 必须串行
- A -> B -> C -> D

### 可并行
- capability / access family
- readiness / service family
- interaction family
- trace / enums family

---

## 4. implementation 前置

- 命名规范已冻结
- shared-contracts core objects / phase-1 freeze / interaction docs 已冻结

---

## 5. checklist

- [ ] namespaced capability_id / service_object_id 已进入 schema seed
- [ ] refs 采用统一格式
- [ ] interaction family 已进入 shared/contracts/interaction
- [ ] runtime_result_status 已进入 enums family
- [ ] 没有让 metadata/extensions 承担核心字段

---

## 6. 核心结论

shared-contracts 的实现不是“把文档抄成 schema”，而是先把 phase-1 真正跨模块共用的最小对象冻结成可被实现窗口安全引用的 schema seed。
