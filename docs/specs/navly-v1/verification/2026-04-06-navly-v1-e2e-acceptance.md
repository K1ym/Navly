# 2026-04-06 Navly_v1 E2E 验收方案

日期：2026-04-06  
状态：phase-1-acceptance-baseline  
用途：定义 `Navly_v1` phase-1 的最小闭环 e2e 验收链路、必须可追溯点、必须可解释失败，以及哪些验收是 P0、哪些可以后置

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 在 phase-1 最小闭环里，到底要怎样才算真正“跑通”，而不是只是几个模块各自看起来能工作？

---

## 2. 本文档验证什么 / 不验证什么

### 2.1 验证对象

本文档验证的是 **端到端验收口径**，包括：

1. `WeCom / OpenClaw -> bridge -> auth-kernel -> runtime -> data-platform -> answer / fallback` 是否形成单条闭环
2. 成功链路是否能从入口追到答案对象
3. 失败链路是否能明确解释失败属于 access、binding、readiness、service 还是 runtime
4. 上层是否真的依赖双内核稳定输出，而不是绕过它们直接“猜”结果

### 2.2 不验证对象

本文档不验证：

- 复杂多代理编排
- UI 体验、措辞优雅度
- 任意自然语言问题都能回答
- 非 `WeCom + OpenClaw` 渠道
- 非 phase-1 数据域

---

## 3. Phase-1 最小闭环定义

Phase-1 最小闭环不是“能收到消息并调到接口”。

Phase-1 最小闭环的正式定义是：

> 一次来自 `WeCom / OpenClaw` 的合法入口请求，能够经过 bridge 标准化、`auth-kernel` 绑定与访问判定、runtime capability 路由、`data-platform` readiness / service 查询，最终产出 **可审计 answer** 或 **可解释 fallback / refusal**，且整条链路可追溯、失败可归因。

---

## 4. Phase-1 e2e 主链路

```text
WeCom / OpenClaw
  -> openclaw-host-bridge
  -> auth-kernel
  -> thin runtime shell
  -> data-platform
  -> answer / fallback
  -> audit / trace closure
```

### 4.1 每一跳的 owner 判断

| 阶段 | owner | 该阶段必须回答的问题 | 该阶段不能回答的问题 |
| --- | --- | --- | --- |
| 入口接收 | `openclaw-host-bridge` | 这是什么入口、有哪些宿主证据 | actor 最终是谁、数据是否 ready |
| Gate 0 / access | `auth-kernel` | 谁能否继续、绑定是否成立、允许哪些 capability | 数据有没有、答案怎么组织 |
| orchestration | `runtime` | 用哪个 capability，如何组织调用与表达 | 谁被授权、数据真相是什么 |
| readiness / service | `data-platform` | 当前 capability 是否 ready、可服务什么对象 | 谁被授权、最终用户话术 |
| final answer/fallback | `runtime` | 如何把结构化结果转成回答/拒答/待答说明 | 不能重写 access/readiness 真相 |

---

## 5. E2E 验收步骤与必备输出

### 5.1 Step A：ingress normalization

输入：

- WeCom/OpenClaw 入口消息
- host session / workspace / conversation 线索

必备输出：

- `request_id`
- `ingress_ref`
- `host_session_ref`
- `host_workspace_ref`
- `host_conversation_ref`
- `message_mode`
- `trace_ref`

验收要求：

- bridge 只输出入口证据，不输出最终 actor 或最终 scope
- 若入口必要证据缺失，失败必须停在 ingress 层，并显式记录 bridge-side reason

### 5.2 Step B：actor resolution + binding + Gate 0

输入：

- ingress identity envelope
- channel / peer identity evidence
- role / scope / conversation binding rules

必备输出：

- `actor_ref` 或显式 `unknown / ambiguous / inactive`
- `binding_snapshot_ref`
- `conversation_ref`
- `session_ref`
- `decision_ref`
- `gate_status`
- `reason_codes`

验收要求：

- 入口请求不能在没有 `decision_ref` 的情况下进入 runtime
- unresolved actor 不能被 runtime 自行补救成“先继续试试看”
- `restricted` / `escalation` 必须带结构化限制或升级原因

### 5.3 Step C：runtime capability routing

输入：

- 用户意图
- `access_context_envelope`
- 上下文允许的 `capability_id`

必备输出：

- 选定 `capability_id`
- `runtime_trace_ref`
- `target_scope_ref`（若已由 binding 锚定）
- 结构化调用请求，而不是自由文本猜测

验收要求：

- runtime 不得选择不在 `granted_capability_ids` 里的 capability
- runtime 不得用会话文本直接覆盖 `scope_ref`
- runtime 的失败应归为 runtime failure，而不是冒充 access/readiness failure

### 5.4 Step D：data-platform readiness

输入：

- `capability_readiness_query`
- `access_context_envelope`
- `target_scope_ref`
- `target_business_date` 或 `freshness_mode`

必备输出：

- `readiness_status`
- `latest_usable_business_date`
- `reason_codes`
- `blocking_dependencies`
- `state_trace_ref`

验收要求：

- `data-platform` 只返回 readiness/data 侧解释，不返回 access allow/deny
- readiness 为 `pending / failed / unsupported_scope` 时，必须能给出结构化 reason 与 trace
- runtime 不得跳过这一步直接读 service object

### 5.5 Step E：theme/service serving

前置条件：

- `readiness_status = ready`

输入：

- `theme_service_query`
- `service_object_id`
- `access_context_envelope`

必备输出：

- `service_status`
- `service_object`
- `trace_refs`
- `explanation_object`（若要求）

验收要求：

- service 输出必须能追到 `run_trace_ref` / `state_trace_ref`
- service 层不能暴露 source endpoint / 物理表 / 临时 SQL 作为对外主语

### 5.6 Step F：answer / fallback

输入：

- access decision
- readiness/service outputs
- explanation object

必备输出：

- answer / refusal / fallback
- 使用过的 `decision_ref`
- 使用过的 `trace_refs`
- `outcome_status`

验收要求：

- answer 必须可说明基于哪个 capability、哪个 scope、哪个 data trace
- refusal 必须能区分 access refusal 与 data not-ready
- fallback 不能伪装成真实已答复

---

## 6. 哪些点必须可追溯

phase-1 P0 必须可追溯以下对象：

1. `ingress_ref`
2. `request_id`
3. `actor_ref`
4. `binding_snapshot_ref`
5. `conversation_ref`
6. `session_ref`
7. `decision_ref`
8. `capability_id`
9. `state_trace_ref`
10. `run_trace_ref`（经由 data-platform service trace 间接可追）
11. 最终 answer/fallback outcome event

说明：

- phase-1 允许 trace 形态还比较朴素。
- 但不允许“答案出来了，却说不清依赖了哪次权限决策、哪个 readiness snapshot、哪条 raw run 链”。

---

## 7. 哪些失败必须可解释

以下失败属于 phase-1 P0，必须显式可解释：

1. **入口失败**：缺少必要 ingress evidence、bridge 无法形成标准入口 envelope
2. **actor 失败**：`unknown / ambiguous / inactive`
3. **binding 失败**：无有效 `scope_binding`、`conversation_binding` 停在 `pending_scope`
4. **access 失败**：`deny / restricted / escalation`
5. **readiness 失败**：`pending / failed / unsupported_scope`
6. **service 失败**：`not_ready / scope_mismatch / error`
7. **runtime 失败**：路由失败、答案组织失败、结构化调用失败

必须禁止的混淆：

- 不能把 access failure 说成“数据暂时没有”
- 不能把 readiness failure 说成“你没有权限”
- 不能把 runtime failure 回写成数据平台问题

---

## 8. Phase-1 P0 验收场景

### 8.1 场景 A：allow + ready + served

目标：

- 完整跑通 answer path

P0 要求：

- 有 `decision_ref`
- 有 `readiness_status = ready`
- 有 `service_status = served`
- 最终 answer 能追到 trace refs

### 8.2 场景 B：allow + pending

目标：

- 验证数据未 ready 时的受控 fallback

P0 要求：

- 最终输出不能伪装成已回答
- 必须返回 readiness reason 与 recheck / fallback 提示

### 8.3 场景 C：restricted / escalation

目标：

- 验证权限受限和升级路径不是统一模糊拒答

P0 要求：

- `restriction_code` / `reason_code` 明确
- runtime 和 bridge 不得自行扩权

### 8.4 场景 D：deny

目标：

- 验证 fail closed

P0 要求：

- 没有 `allow` 或 `restricted` 的有效决策，不得进入 data-platform serving

### 8.5 场景 E：trace closure

目标：

- 验证审计闭环

P0 要求：

- 任意一次 answer / fallback / refusal 都能回指 `decision_ref`
- 任意一次 data serve 或 not-ready 都能回指 `state_trace_ref`

---

## 9. 可以后置的验收项

以下不属于 phase-1 P0，可后置：

- 多 capability 组合回答
- 复杂多轮 scope 选择
- richer agent orchestration
- 非 WeCom 渠道
- HQ 网络级复杂聚合问答
- 高级运维与审计可视化界面

---

## 10. 哪些现象说明 e2e 其实没有闭环

任意一条成立，就说明当前“只是局部可运行”，不是正式 e2e 闭环：

1. runtime 可以在没有 `decision_ref` 的情况下继续
2. `data-platform` 可以在没有标准 access envelope 的情况下继续
3. readiness 和 answer 之间没有 trace refs
4. answer 能出来，但解释不清失败时属于 access 还是 readiness
5. bridge 或 runtime 通过本地 hardcode 修补 scope、date、capability，导致链路看似跑通

核心结论：

> phase-1 的 e2e 不是“回答出来”本身，而是“回答或拒答都来自双内核的正式输出，并且整条链路能被追溯和解释”。
