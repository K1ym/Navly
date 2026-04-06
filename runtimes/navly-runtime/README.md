# Navly_v1 thin runtime shell

状态：milestone-a-skeleton  
用途：建立 `runtimes/navly-runtime/` 的 phase-1 / milestone A 最小执行壳骨架（interaction + route registry freeze）。

## 当前范围（Milestone A）

本目录当前只实现：

- runtime 目录骨架
- interaction 边界对齐（bridge -> runtime -> outcome）
- capability route registry seed
- 最小约束校验脚本

本轮明确不做：

- milestone B/C/D
- rich orchestration
- LangGraph integration
- 业务回答细节扩张

## runtime 当前只消费的 shared contracts

- `access_context_envelope`
- `access_decision`
- `capability_readiness_query` / `capability_readiness_response`
- `theme_service_query` / `theme_service_response`
- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

详见：`contracts/runtime-shared-contract-consumption.manifest.json`

## milestone A 冻结约束

- canonical `capability_id` 必须使用 namespaced 格式：`navly.<domain>.<capability_name>`
- canonical `service_object_id` 必须使用 namespaced 格式：`navly.service.<domain>.<object_name>`
- interaction contract 语义必须对齐 `shared/contracts/interaction/*`
- `runtime_result_status` 必须沿用 shared enum，不在 runtime 内扩写

## 当前骨架

```text
runtimes/navly-runtime/
  README.md
  docs/
  contracts/
  ingress/
  routing/
  execution/
  answering/
  outcome/
  adapters/
  migration/
  scripts/
  tests/
```
