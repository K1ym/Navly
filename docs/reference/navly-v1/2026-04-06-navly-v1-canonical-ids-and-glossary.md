# 2026-04-06 Navly_v1 Canonical IDs And Glossary

日期：2026-04-06  
状态：reference  
用途：集中列出 Navly_v1 当前冻结的 capability IDs、service object IDs、ref 格式与主术语

---

## 1. Capability IDs

当前 canonical `capability_id` 采用：

- `navly.<domain>.<capability_name>`

### 当前 phase-1 主集合

- `navly.store.daily_overview`
- `navly.store.member_insight`
- `navly.store.staff_board`
- `navly.store.finance_summary`
- `navly.system.capability_explanation`

### 当前 host/operator 扩展集合

- `navly.ops.sync_status`
- `navly.ops.backfill_status`
- `navly.ops.sync_rerun`
- `navly.ops.sync_backfill`
- `navly.ops.quality_report`

说明：
- `store_daily_overview`、`store_member_insight` 等可作为文档短名
- 不再作为跨模块 canonical ID

---

## 2. Service Object IDs

当前 canonical `service_object_id` 采用：

- `navly.service.<domain>.<object_name>`

### 当前 phase-1 主集合

- `navly.service.store.daily_overview`
- `navly.service.store.member_insight`
- `navly.service.store.staff_board`
- `navly.service.store.finance_summary`
- `navly.service.system.capability_explanation`

### 当前 host/operator 扩展集合

- `navly.service.ops.sync_status`
- `navly.service.ops.backfill_status`
- `navly.service.ops.sync_rerun`
- `navly.service.ops.sync_backfill`
- `navly.service.ops.quality_report`

### phase-1 扩展候选

- `navly.service.hq.network_overview`
- `navly.service.store.exception_digest`

---

## 3. Ref 格式

### access refs
- `actor_ref = navly:actor:<actor_id>`
- `session_ref = navly:session:<session_id>`
- `decision_ref = navly:decision:<decision_id>`
- `scope_ref = navly:scope:<scope_kind>:<scope_id>`

### trace refs
- `trace_ref = navly:trace:<trace_id>`
- `state_trace_ref = navly:state-trace:<state_type>:<state_id>`
- `run_trace_ref = navly:run-trace:<run_type>:<run_id>`

---

## 4. 主状态集合

### access_decision_status
- `allow`
- `deny`
- `restricted`
- `escalation`

### readiness_status
- `ready`
- `pending`
- `failed`
- `unsupported_scope`

### service_status
- `served`
- `not_ready`
- `scope_mismatch`
- `error`

### runtime_result_status
- `answered`
- `fallback`
- `escalated`
- `rejected`
- `runtime_error`

---

## 5. 核心术语

### 双内核
- `data-platform`
- `auth-kernel`

### 宿主桥接层
- `openclaw-host-bridge`

### 最小执行壳
- `thin runtime shell`

### 当前 phase-1 最小闭环
- `bridge -> Gate 0 -> runtime route -> capability access -> readiness -> service -> answer/fallback/escalation -> bridge delivery`

---

## 6. 核心结论

这个 reference 文件的作用不是替代 shared-contracts，而是让实现窗口快速查 canonical IDs 和主术语，减少在 PR 中临时造名。
