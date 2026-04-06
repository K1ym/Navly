# 2026-04-06 Navly_v1 Phase-1 Verification Checklist

日期：2026-04-06  
状态：review-checklist  
用途：供总控窗口在 `Navly_v1` 进入 implementation 前做 go/no-go 审核使用

---

## 使用方式

- 本清单是 **spec-only 阶段** 的审核清单
- 任一 P0 项未满足，都不应进入 implementation
- 本清单不替代正文方案文档；它只是总控审核入口

---

## A. Boundary verification

### P0

- [ ] `data-platform` 的 owner truth 只包括 data truth / readiness truth
- [ ] `auth-kernel` 的 owner truth 只包括 access truth
- [ ] `openclaw-host-bridge` 被明确定义为宿主桥接层，而不是第三内核
- [ ] `runtime` 被明确定义为 orchestration shell，而不是 kernel truth owner
- [ ] `shared-contracts` 是 capability/access/readiness/service/trace 的主共享语义层
- [ ] bridge 与 runtime 的当前 authoritative source 已明确写入文档
- [ ] 禁止依赖关系已写清：runtime 不直读 raw / facts，bridge 不持有 access/data truth

### 非 P0 / 可后置

- [ ] 自动化 boundary lint 方案
- [ ] richer boundary simulation / policy playground

---

## B. Contract consistency

### P0

- [ ] `capability_id` 有唯一 owner 文档
- [ ] `access_context_envelope` / `access_decision` 有唯一 owner 文档
- [ ] `capability_readiness_query/response` 有唯一 owner 文档
- [ ] `theme_service_query/response` 有唯一 owner 文档
- [ ] `trace_ref` / `state_trace_ref` / `run_trace_ref` 有唯一 owner 文档
- [ ] `access_decision_status` 主集合唯一
- [ ] `readiness_status` 主集合唯一
- [ ] `service_status` 主集合唯一
- [ ] `runtime_result_status` 主集合唯一
- [ ] `reason_code` 主类没有分叉
- [ ] 没有出现同义不同名或同名不同义的 P0 对象

### 非 P0 / 可后置

- [ ] 自动化 enum diff / contract diff 工具

---

## C. Docs consistency

### P0

- [ ] `navly-v1-design`、`navly-v1-architecture`、模块 boundary docs 之间没有边界冲突
- [ ] `specs`、`api`、`audits` 的角色分工清楚且不混用
- [ ] `README` / 索引已包含 verification 文档包
- [ ] 影响 shared object / phase-1 / boundary 的文档都有联动更新规则
- [ ] 新窗口按照 README 可读到正确 authoritative source

### 非 P0 / 可后置

- [ ] 文档自动化索引或站点化展示

---

## D. E2E acceptance

### P0

- [ ] phase-1 最小闭环链路已正式定义
- [ ] `allow + ready + served` 场景已定义
- [ ] `allow + pending` 场景已定义
- [ ] `restricted` 场景已定义
- [ ] `deny / escalation` 场景已定义
- [ ] trace closure 场景已定义
- [ ] `decision_ref` 是 runtime 继续前的硬前提
- [ ] `state_trace_ref` / `run_trace_ref` 可用于 data-platform 追溯
- [ ] access failure 与 readiness failure 的边界可明确解释

### 非 P0 / 可后置

- [ ] 多 capability 复杂编排验收
- [ ] 多渠道 e2e 验收
- [ ] richer fallback orchestration

---

## E. Regression baseline

### P0

- [ ] phase-1 baseline 文档已冻结主语义、主对象、主枚举、主 trace refs、主场景
- [ ] P0 service object 集已明确
- [ ] baseline 级变更触发条件已明确
- [ ] 不触发 baseline 重审的局部扩展范围已明确

### 非 P0 / 可后置

- [ ] 更细粒度 reference 字典和词典化管理

---

## F. Go / No-Go 判断

只有当以下条件全部满足时，才建议进入 implementation：

- [ ] A/B/C/D/E 中所有 P0 项都已满足
- [ ] 没有发现 bridge/runtime 正在侵入 kernel truth
- [ ] 没有发现同一语义存在多套 owner 或多套枚举
- [ ] 没有发现 README 仍会把新窗口引导到错误入口

如果以上任一条不成立，则当前结论应为：

> **No-Go：先修正文档边界与共享语义，再进入 implementation。**
