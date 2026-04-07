# 2026-04-06 Navly_v1 thin runtime shell Phase-1 Implementation Plan

日期：2026-04-06  
状态：phase-1-executable-plan  
用途：把 thin runtime shell phase-1 方案细化为可执行实施顺序、里程碑与验收 gate

---

## 1. 实施目标

phase-1 先闭合：

`runtime_request_envelope -> capability route -> capability access -> readiness -> service -> answer/fallback/escalation -> runtime_result_envelope`

---

## 2. 里程碑

### Milestone A：interaction + route registry freeze

输出：
- runtime ingress skeleton
- capability route registry skeleton
- shared interaction alignment

### Milestone B：capability route closure

输出：
- route resolution
- service binding selection
- route fallback plan

### Milestone C：guarded execution closure

输出：
- access decision call
- readiness query
- theme service query
- fail-closed orchestration

### Milestone D：answer / fallback / outcome closure

输出：
- runtime_result_envelope
- runtime_outcome_event
- answer/fallback/escalation organization

---

## 3. 推荐第一条 vertical slice

`navly.store.member_insight -> navly.service.store.member_insight`

`navly.store.daily_overview` 可作为 secondary entry 保留，但不再作为当前最小 canonical slice。

优先证明：
- runtime 以 capability-first 工作
- runtime 不直接碰 endpoint/table/raw truth
- runtime 不重做 access / readiness 真相

---

## 4. implementation 前置

- shared interaction contracts 已冻结
- auth-kernel external interfaces 已稳定
- data-platform external interfaces 已稳定

---

## 5. checklist

- [ ] route registry 存在
- [ ] runtime 不再以 endpoint / table 为主语
- [ ] 没有 access_context_envelope 不继续执行
- [ ] runtime_result_status 主集合未分叉
- [ ] runtime_result_envelope / runtime_outcome_event 已统一

---

## 6. 核心结论

runtime 的实现应该先证明它能保护双内核边界，而不是先追求 richer orchestration。
