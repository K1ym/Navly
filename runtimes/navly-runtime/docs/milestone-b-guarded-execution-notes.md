# Runtime Milestone B Guarded Execution Notes

日期：2026-04-06  
状态：milestone-b

## 本轮交付

- route resolution closure（capability-first）
- default service binding selection closure（service-object-first）
- companion explanation service binding closure
- capability access decision call wiring
- readiness query wiring
- theme service query wiring
- readiness-blocked explanation companion query wiring
- `runtime_result_envelope` 主路径闭合
- `runtime_outcome_event` 输出闭合
- phase-1 store runtime surface：
  - `navly.store.member_insight`
  - `navly.store.daily_overview`
  - `navly.store.staff_board`
  - `navly.store.finance_summary`
- companion explanation service：
  - `navly.service.system.capability_explanation`

## 本轮未交付

- rich orchestration
- LangGraph
- 多 capability 编排
- milestone C / D 的扩展面（超出 ASP-18 Milestone B 的 richer 范围）

## 边界检查

- runtime 只消费 access/readiness/service truth
- runtime 不直读 data-platform 内部 truth layer
- runtime 不重写 shared `runtime_result_status` 主枚举
- runtime explanation path 优先消费 published explanation service / `explanation_object`
