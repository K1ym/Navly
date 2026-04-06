# Navly_v1 数据中台方案包

日期：2026-04-06  
状态：baseline-for-implementation

本目录是 `Navly_v1` 的**数据中台专项正式方案包**。

范围严格限定为：

- 数据中台本身的模块设计、分层设计、repo structure、phase-1 落地方案
- 数据中台与权限内核 / Copilot 的接口边界
- 数据中台自身的 upstream 采用策略

本目录**不**负责：

- 权限内核自身实现
- 会话绑定实现
- Copilot 的问答编排、提示词、路由和表达层实现
- 任何 private secret 的公开化

---

## 当前前提

1. `docs/api/qinqin/` 是当前第一输入域的文档真相源。
2. `docs/audits/qinqin/` 只负责记录 live 行为偏差和历史审计，不取代 API 主文档。
3. 当前 phase-1 聚焦 `Qinqin v1.1` 的 8 个正式端点。
4. 公开文档只描述 secret contract，不保存真实 secret 值。
5. OpenClaw、LangGraph、Copilot runtime 不进入 data-platform 内核。

---

## 文档清单

- `2026-04-06-navly-v1-data-platform-module-boundaries.md`
  - 数据中台 4 个核心模块的职责、输入输出、依赖关系、phase-1 优先级、长期资产判断
- `2026-04-06-navly-v1-data-platform-internal-layers.md`
  - 数据中台内部控制层 / 数据层 / 状态层 / 服务层的分层设计，以及模块到分层的映射
- `2026-04-06-navly-v1-data-platform-target-repo-structure.md`
  - `platforms/data-platform/` 的目标目录骨架、目录职责、C0/L0/L1/L2/L3 写入边界、长期资产判断与默认读取边界
- `2026-04-06-navly-v1-data-platform-phase-1.md`
  - Navly_v1 数据中台第一阶段的闭环落地方案、优先级、验收条件与非目标
- `2026-04-06-navly-v1-data-platform-implementation-plan.md`
  - phase-1 的实施顺序、里程碑 A/B/C/D、串并行关系与 milestone checklist
- `2026-04-06-navly-v1-data-platform-external-interfaces.md`
  - 数据中台与权限内核 / Copilot 的正式接口边界、输入输出契约和责任矩阵
- `2026-04-06-navly-v1-data-platform-open-source-adoption.md`
  - 数据中台专项的 upstream 采用策略：phase-1 核心、可选扩展、后续增强、明确排除项

---

## 建议阅读顺序

1. `2026-04-06-navly-v1-data-platform-module-boundaries.md`
2. `2026-04-06-navly-v1-data-platform-internal-layers.md`
3. `2026-04-06-navly-v1-data-platform-target-repo-structure.md`
4. `2026-04-06-navly-v1-data-platform-phase-1.md`
5. `2026-04-06-navly-v1-data-platform-implementation-plan.md`
6. `2026-04-06-navly-v1-data-platform-external-interfaces.md`
7. `2026-04-06-navly-v1-data-platform-open-source-adoption.md`
8. `../2026-04-06-navly-v1-design.md`
9. `../../data-platform/2026-04-06-navly-data-middle-platform-design.md`
10. `../../../api/qinqin/README.md`

---

## 本方案包的核心判断

Navly_v1 数据中台不是“旧问答系统的数据附件”，而是 Navly 的长期数据真相内核。

因此它必须先把以下六类真相做清楚：

1. **contract truth**：哪些 source / endpoint / field / capability 在 Navly 范围内
2. **raw truth**：某店某日某端点到底采了什么、失败在哪一页、如何回放
3. **canonical fact truth**：哪些标准业务事实已经成立
4. **latest state truth**：最新可用业务日与数据集状态到底是什么
5. **readiness truth**：某 capability 为什么 ready / pending / failed
6. **theme / service truth**：上层默认应该读取什么主题对象 / 服务对象

只有这六类 truth 分开、闭合、可追溯，Navly_v1 的数据中台才算成立。
