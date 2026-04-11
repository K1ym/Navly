# Navly Docs

Navly 的文档按 **用途优先** 组织，按 **业务域** 细分。

## 目录约定

- `api/`：外部接口文档与输入真相源
- `specs/`：正式方案文档，描述“要做什么”
- `architecture/`：架构、分层、边界与数据流
- `runbooks/`：运行、补数、巡检、迁移操作手册
- `audits/`：现状审计、差距分析、对齐报告
- `reference/`：字段字典、表字典、状态说明等长期参考资料

## 当前建议阅读顺序

1. `specs/navly-v1/2026-04-06-navly-v1-design.md`
2. `specs/navly-v1/2026-04-06-navly-v1-modular-development-and-vibe-coding.md`
3. `specs/navly-v1/2026-04-06-navly-v1-naming-conventions.md`
4. `specs/navly-v1/2026-04-06-navly-v1-shared-contracts-layer.md`
5. `specs/navly-v1/2026-04-06-navly-v1-upstream-integration-policy.md`
6. `specs/navly-v1/2026-04-06-navly-v1-implementation-kickoff.md`
7. `specs/navly-v1/data-platform/README.md`
8. `specs/navly-v1/auth-kernel/README.md`
9. `specs/navly-v1/openclaw-host-bridge/README.md`
10. `specs/navly-v1/runtime/README.md`
11. `specs/navly-v1/verification/README.md`
12. `specs/navly-v1/verification/2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md`
13. `specs/navly-v1/verification/2026-04-11-navly-v1-phase-1-remaining-qinqin-live-transport-validation-matrix.md`
14. `architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
15. `api/qinqin/README.md`
16. `api/qinqin/endpoint-manifest.md`
17. `api/qinqin/auth-and-signing.md`
18. `specs/navly-v1/README.md`
19. `architecture/navly-v1/README.md`
20. `reference/navly-v1/2026-04-06-navly-v1-canonical-ids-and-glossary.md`
21. `audits/qinqin/README.md`

## 当前文档域

- `data-platform/`：Navly 数据中台
- `navly-v1/`：Navly_v1 总体版本设计、公共契约与模块专项方案
- `qinqin/`：Qinqin API 输入文档

## 维护规则

- 输入文档和系统设计文档必须分开
- 审计文档不与正式方案混放
- 一个文档只保留一个正式位置
- 新文档优先采用 `YYYY-MM-DD-<topic>.md` 命名
