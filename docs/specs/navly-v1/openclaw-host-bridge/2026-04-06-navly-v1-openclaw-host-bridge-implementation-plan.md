# 2026-04-06 Navly_v1 openclaw-host-bridge Phase-1 Implementation Plan

日期：2026-04-06  
状态：phase-1-executable-plan  
用途：把 OpenClaw 宿主桥接层 phase-1 方案细化为可执行实施顺序、里程碑与验收 gate

---

## 1. 实施目标

phase-1 先闭合：

`host ingress -> Gate 0 handoff -> runtime_request_envelope -> runtime_result_envelope -> host reply dispatch -> host trace`

---

## 2. 里程碑

### Milestone A：host ingress + interaction contract freeze

输出：
- host ingress normalization skeleton
- bridge local object skeleton
- shared interaction contract alignment

### Milestone B：auth linkage closure

输出：
- ingress_identity_envelope assembly
- Gate 0 enforcement
- authorized session link

### Milestone C：runtime handoff closure

输出：
- runtime_request_envelope assembly
- runtime_result_envelope consumption
- fail-closed path

### Milestone D：dispatch + host trace closure

输出：
- reply dispatch
- host dispatch result
- host trace linkage
- outcome forwarding

---

## 3. 串并行规则

### 必须串行
- A -> B -> C -> D

### 可并行
- adapters/openclaw skeleton
- tool publication skeleton
- diagnostics skeleton

---

## 4. 推荐第一条 vertical slice

`WeCom/OpenClaw chat message -> host_ingress_envelope -> Gate 0 -> runtime_request_envelope -> runtime_result_envelope -> host reply`

优先证明：
- bridge 不是第三内核
- bridge 不需要直连 data truth
- bridge 只做 handoff / dispatch / enforce

---

## 5. implementation 前置

- auth-kernel serving boundary 已稳定
- runtime interaction contracts 已冻结
- shared contracts interaction family 已可读

---

## 6. checklist

- [ ] 不再使用 `authorized_runtime_handoff_envelope`
- [ ] `runtime_request_envelope` 成为唯一 canonical handoff
- [ ] host local objects 未被误提升为 shared primary contracts
- [ ] host -> bridge -> auth -> runtime 链路 fail closed

---

## 7. 核心结论

bridge 的实现应该从 interaction contract 和 fail-closed ingress 开始，而不是从 host 业务胶水开始。
