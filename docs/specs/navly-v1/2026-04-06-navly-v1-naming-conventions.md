# 2026-04-06 Navly_v1 命名规范

日期：2026-04-06  
状态：baseline-for-collaborative-implementation  
用途：定义 Navly_v1 在模块、目录、契约、对象、状态、ID 与文档命名上的统一规则，避免多窗口并行开发时语义漂移

---

## 1. 文档目的

本文档回答：

> 当多个 Codex 窗口并行设计和实现时，如何保证大家说的是同一套东西，而不是“名字相近、语义不同”的平行世界？

命名规范的目标不是追求形式统一，而是保护：

1. 真相边界
2. contracts 可复用性
3. 跨模块可集成性
4. 文档与代码的一致性

---

## 2. 总原则

### 2.1 先按语义命名，再按技术实现命名

优先使用：

- `capability_readiness_snapshot`
- `theme_service_object`
- `access_decision`
- `latest_sync_state`

不要优先使用：

- `graph_data`
- `temp_result`
- `agent_payload`
- `final_table`

### 2.2 名字必须表达“拥有哪一种真相”

例如：

- `raw_response_page` 表达原始页响应真相
- `latest_sync_state` 表达最新可用状态真相
- `capability_explanation` 表达解释对象

不能用一个模糊名字同时表达多种真相。

### 2.3 默认避免技术品牌进入业务命名

例如：

- 可以写 `theme_service_query`
- 不应把接口命名成 `hasura_theme_query`

因为技术选型可以替换，语义边界不能漂移。

### 2.4 默认使用英文作为代码 / contract 主命名，中文用于文档解释

原因：

- 代码与契约需要跨模块稳定复用
- 中文更适合架构说明与业务解释

---

## 3. 模块与目录命名规范

### 3.1 顶层模块

推荐固定命名：

- `data-platform`
- `auth-kernel`
- `openclaw-host-bridge`
- `agent-runtime`
- `apps`
- `ops`
- `shared/contracts`

### 3.2 目录命名

统一规则：

- 小写
- kebab-case 用于目录
- 不使用缩写，除非是通用标准缩写

推荐：

- `raw-store`
- `sync-state`
- `openclaw-host-bridge`

避免：

- `rawStore`
- `syncstate`
- `oc-bridge`

### 3.3 文档目录命名

spec 子目录优先按模块命名：

- `docs/specs/navly-v1/data-platform/`
- `docs/specs/navly-v1/auth-kernel/`
- `docs/specs/navly-v1/shared-contracts/`

---

## 4. 契约与对象命名规范

### 4.1 Registry

凡是“受治理清单 / 目录 / 台账”，统一使用：

- `*_registry`

例如：

- `endpoint_contract_registry`
- `field_landing_policy_registry`
- `capability_registry`

### 4.2 Snapshot

凡是“某一时刻的状态切面”，统一使用：

- `*_snapshot`

例如：

- `field_coverage_snapshot`
- `schema_alignment_snapshot`
- `capability_readiness_snapshot`

### 4.3 State

凡是“具有持续更新语义的当前状态”，统一使用：

- `*_state`

例如：

- `latest_sync_state`
- `backfill_progress_state`

### 4.4 Event

凡是“发生过的一次事件”，统一使用：

- `*_event`

例如：

- `raw_error_event`
- `data_access_audit_event`

### 4.5 Envelope

凡是“带上下文包装的请求/响应对象”，统一使用：

- `*_envelope`

例如：

- `raw_request_envelope`
- `raw_response_envelope`
- `access_context_envelope`

### 4.6 Object

凡是“供上层消费的服务对象”，统一使用：

- `*_object`

例如：

- `theme_service_object`
- `capability_explanation_object`

### 4.7 Query / Response

凡是显式接口契约，统一用：

- `*_query`
- `*_response`

例如：

- `capability_readiness_query`
- `theme_service_query`
- `theme_service_response`

---

## 5. ID / Ref / Key 命名规范

### 5.1 `*_id`

表示该对象自己的稳定主标识。

例如：

- `capability_id`
- `service_object_id`
- `event_id`

### 5.2 `*_ref`

表示对外部对象或另一层对象的引用。

例如：

- `actor_ref`
- `decision_ref`
- `session_ref`
- `trace_ref`

### 5.3 `*_key`

表示业务键、幂等键、聚合键。

例如：

- `business_key`
- `idempotency_key`
- `aggregation_key`

### 5.4 `*_code`

表示受控枚举代码，而不是自由文本。

例如：

- `reason_code`
- `error_code`
- `restriction_code`

---

## 6. 状态与枚举命名规范

### 6.1 readiness status

推荐统一：

- `ready`
- `pending`
- `failed`
- `unsupported_scope`

### 6.2 service status

推荐统一：

- `served`
- `not_ready`
- `scope_mismatch`
- `error`

### 6.3 access decision

推荐统一：

- `allow`
- `deny`
- `restricted`
- `escalation`

### 6.4 同一语义只允许一套主枚举

例如既然已经用 `pending`，就不要在相邻模块里再出现：

- `waiting`
- `not_yet_ready`
- `incomplete`

除非它们表达的是不同语义。

---

## 7. 分层命名规范

推荐固定：

- `C0`：contract / catalog
- `L0`：raw
- `L1`：core
- `L2`：state
- `L3`：service

说明：

- 在文档里可以写 `C0 + L0-L3`
- 在代码命名里优先写语义命名空间，例如 `contract/`, `raw/`, `core/`, `state/`, `service/`

---

## 8. Capability / Service Object 命名规范

### 8.1 `capability_id`

`capability_id` 是跨模块公共主标识，统一使用：

- 小写
- 点分层级命名
- `navly` 作为顶层前缀

推荐格式：

- `navly.<domain>.<capability_name>`

推荐：

- `navly.store.finance_summary`
- `navly.store.member_insight`
- `navly.store.staff_board`
- `navly.hq.network_overview`

避免：

- `store_finance_summary`
- `financeTool`
- `queryStoreMoney`
- `staffAgentAbility`

说明：

- `store_member_insight` 这类 snake_case 形式可以作为**文档短名 / 人类可读标签**
- 但它不应继续作为跨模块公共 `capability_id`

### 8.2 `service_object_id`

`service_object_id` 统一使用：

- 小写
- 点分层级命名
- `navly.service` 作为顶层前缀

推荐格式：

- `navly.service.<domain>.<object_name>`

推荐：

- `navly.service.store.daily_overview`
- `navly.service.store.member_insight`
- `navly.service.store.staff_board`
- `navly.service.store.finance_summary`
- `navly.service.system.capability_explanation`

避免：

- `store_daily_overview`
- `capability_explanation`
- `serviceStoreSummary`

---

## 9. 文档命名规范

正式 spec 文档统一使用：

- `YYYY-MM-DD-<topic>.md`

例如：

- `2026-04-06-navly-v1-design.md`
- `2026-04-06-navly-v1-naming-conventions.md`

子目录中的主题文档也保持同样规则。

---

## 10. 核心判断

在 Navly_v1 中，命名规范不是“文风问题”，而是：

> **保护双内核、公共契约和多窗口并行开发不发生语义漂移的基础设施。**
