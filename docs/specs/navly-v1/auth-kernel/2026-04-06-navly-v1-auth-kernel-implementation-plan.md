# 2026-04-06 Navly_v1 auth-kernel Phase-1 Implementation Plan

日期：2026-04-06  
状态：phase-1-executable-plan  
用途：把 auth-kernel 的 phase-1 方案细化为可执行实施顺序、里程碑与验收 gate

---

## 1. 实施目标

phase-1 先闭合：

`ingress evidence -> actor resolution -> binding snapshot -> Gate 0 -> capability access decision -> access_context_envelope -> governance trace`

---

## 2. 里程碑

### Milestone A：vocabulary freeze

输出：
- actor / role / scope / capability vocabulary
- `allow / deny / restricted / escalation`
- reason / restriction / obligation taxonomy

### Milestone B：identity + binding backbone

输出：
- actor registry
- identity alias registry
- role/scope/conversation binding
- binding_snapshot

### Milestone C：Gate 0 + capability decision

输出：
- gate0_result
- access_decision
- decision_ref
- session_grant_snapshot

### Milestone D：serving + governance closure

输出：
- access_context_envelope
- audit ledger
- decision trace view
- downstream outcome closure

---

## 3. 串并行规则

### 必须串行
- A -> B
- B -> C
- C -> D

### 可并行
- role catalog 和 reason taxonomy
- actor registry 与 binding persistence skeleton
- governance ledger 与 serving adapter skeleton（在 C 之后）

---

## 4. 推荐第一条 vertical slice

`WeCom/OpenClaw ingress -> actor_ref -> scope/store binding -> Gate 0 -> data read capability decision -> access_context_envelope`

优先证明：
- host evidence 不等于 actor truth
- conversation binding 不扩权
- downstream 没有 `decision_ref` 就 fail closed

---

## 5. implementation 前置

- shared contracts baseline 已冻结
- namespaced `capability_id` 已冻结
- bridge/runtime external interfaces 已稳定到可实现水平

---

## 6. 进入代码阶段的 checklist

- [ ] 目录骨架建立
- [ ] C0 registry 冻结
- [ ] actor / binding object skeleton 就位
- [ ] decision object skeleton 就位
- [ ] access_context_envelope mapping 明确
- [ ] 不再保留旧的 legacy escalation 状态别名

---

## 7. 核心结论

auth-kernel 的实现不应从“先写鉴权 if/else”开始，而应从 vocabulary、binding、decision object 和 serving boundary 开始。
