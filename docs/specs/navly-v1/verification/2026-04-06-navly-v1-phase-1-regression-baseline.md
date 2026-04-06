# 2026-04-06 Navly_v1 Phase-1 回归基线方案

日期：2026-04-06  
状态：phase-1-regression-baseline  
用途：定义 `Navly_v1` phase-1 冻结后不可随意漂移的对象、最小回归基线、重新审核触发条件，以及哪些基线属于 P0

---

## 1. 文档目的

本文档回答：

> `Navly_v1` phase-1 一旦冻结，哪些对象可以继续演进，哪些对象一漂移就必须触发重新审核？

---

## 2. 什么是 phase-1 最小回归基线

phase-1 最小回归基线不是“所有字段都冻结”。

它的正式定义是：

> 使双内核、bridge、runtime 仍然能够以同一套共享语言完成 phase-1 最小闭环所必需的对象、枚举、追溯引用和 failure taxonomy。

也就是说，phase-1 baseline 冻结的是：

1. **主语义**
2. **主对象**
3. **主枚举**
4. **主 trace refs**
5. **主验收场景**

不是冻结每一个实现细节。

---

## 3. 本文档验证什么 / 不验证什么

### 3.1 验证对象

本文档验证：

- 哪些对象属于 phase-1 regression baseline
- 哪些枚举、接口、reason code、trace refs 不能随意漂移
- 哪些变更必须触发重新审核

### 3.2 不验证对象

本文档不冻结：

- 内部实现技术栈
- owner-local 的扩展字段
- richer orchestration、更多渠道或更多 service object 的未来扩展
- UI / ops console 细节

---

## 4. Phase-1 baseline 冻结范围

### 4.1 边界基线

以下边界属于 phase-1 P0 baseline：

1. `data-platform` 拥有 data truth / readiness truth
2. `auth-kernel` 拥有 access truth
3. `openclaw-host-bridge` 不是第三内核
4. `runtime` 不反向定义 kernel truth
5. `shared-contracts` 是跨模块共享对象与枚举的唯一主语义层

### 4.2 共享对象基线

以下对象属于 phase-1 最小冻结集：

- `capability_definition`
- `capability_id`
- `capability_scope_requirement`
- `access_context_envelope`
- `access_decision`
- `decision_ref`
- `binding_snapshot_ref`
- `capability_readiness_query`
- `capability_readiness_response`
- `theme_service_query`
- `theme_service_response`
- `capability_explanation_object`
- `trace_ref`
- `state_trace_ref`
- `run_trace_ref`
- `data_access_audit_event`

### 4.3 枚举基线

以下枚举属于 phase-1 P0 baseline：

- `access_decision_status = allow / deny / restricted / escalation`
- `readiness_status = ready / pending / failed / unsupported_scope`
- `service_status` 的主集合
- `runtime_result_status` 的主集合
- `scope_kind` 的主集合
- `readiness_reason_code` 主集合
- `restriction_code` / `obligation_code` 主集合

### 4.4 trace 基线

phase-1 P0 不能随意漂移的追溯主链：

- `ingress_ref`
- `request_id`
- `actor_ref`
- `binding_snapshot_ref`
- `session_ref`
- `conversation_ref`
- `decision_ref`
- `capability_id`
- `state_trace_ref`
- `run_trace_ref`
- final outcome event ref

### 4.5 e2e 场景基线

以下场景属于 phase-1 P0 regression baseline：

1. `allow + ready + served`
2. `allow + pending`
3. `restricted`
4. `deny / escalation`
5. trace closure

---

## 5. 哪些对象不能随意漂移

phase-1 冻结后，以下对象不得在不触发重新审核的情况下随意改名、改义或改 owner：

1. `capability_id`
2. `service_object_id`
3. `actor_ref` / `scope_ref` / `conversation_ref`
4. `decision_ref` / `binding_snapshot_ref` / `trace_ref` 族
5. `allow / deny / restricted / escalation`
6. `ready / pending / failed / unsupported_scope`
7. `reason_code` 主类和 failure family
8. phase-1 P0 service object 集：
   - `navly.service.store.daily_overview`
   - `navly.service.store.member_insight`
   - `navly.service.store.staff_board`
   - `navly.service.store.finance_summary`
   - `navly.service.system.capability_explanation`

原则：

- 可以扩展，但不能悄悄替换主语义
- 可以增加 owner-local 扩展，但不能破坏跨模块共同理解

---

## 6. 哪些变更必须触发重新审核

以下任一变更发生，必须回到总控窗口重新审核：

1. 双内核 / bridge / runtime 边界变化
2. `capability_id`、`service_object_id`、`scope_kind` 改名或改义
3. 新增或删除 `access_decision_status`、`readiness_status` 主枚举值
4. `reason_code` 主类变化，导致失败解释分类改变
5. `decision_ref`、`state_trace_ref`、`run_trace_ref` 的追溯关系变化
6. phase-1 P0 service object 集变化
7. 允许 runtime 直读 raw / facts，或允许 bridge 维护 access/data truth
8. 将 audit 结论升级为新的输入真相而未更新 api/spec 主文档

结论：

> 任何会改变“跨模块共同语言”或“主闭环追溯方式”的变更，都不是普通小改动，而是 baseline 级变更。

---

## 7. 哪些变更可以不触发 baseline 级重审

以下变更通常可后置或局部审核，不一定触发 baseline 级重审：

- owner-local 扩展字段增加
- 内部实现替换但外部 contract 不变
- richer explanation fragments，但不改变主 reason code
- 新增 phase-1 之外的非 P0 service object
- 新增运维视图、审计视图、dashboard

前提是：

- 不改变 owner
- 不改变共享枚举
- 不改变主 trace 链
- 不改变 phase-1 P0 最小闭环

---

## 8. 哪些问题说明基线已经坏了

任意一条成立，都说明当前 baseline 已被破坏：

1. 新窗口无法根据 README 和 shared-contracts 确认对象主定义
2. e2e answer path 无法稳定落到同一套 `decision_ref -> readiness/service trace` 链
3. access/readiness/service 的主状态集合在不同文档中不一致
4. phase-1 P0 service objects 被替换或改义，但未回写 baseline 文档
5. bridge/runtime 开始持有 kernel truth，导致主闭环还能跑但 owner 不再单一

---

## 9. Phase-1 P0 与可后置项

### 9.1 P0

以下属于 phase-1 P0 baseline：

- truth ownership 基线
- 共享对象最小冻结集
- access/readiness/service 主枚举
- trace 主链
- 5 个 P0 e2e 场景

### 9.2 可后置

以下可以后置：

- 更细粒度 reason code 扩展
- richer service objects
- 高级治理与回放工具
- 复杂 agent/runtime 分层
- bridge/runtime 专项 spec 之外的未来增强对象

---

## 10. 怎样定义 phase-1 的最小回归基线

最小回归基线可以压缩成一句话：

> 保证 `WeCom/OpenClaw -> bridge -> auth-kernel -> runtime -> data-platform -> answer/fallback` 仍然使用同一套 capability/access/readiness/service/trace 语言，并且成功与失败都能回到正确 owner 的那组最小对象集合。

只要这句话不再成立，phase-1 baseline 就应视为失效，必须重新审核后才能继续 implementation。
