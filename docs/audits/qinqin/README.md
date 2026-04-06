# Qinqin Audits

本目录存放 Qinqin API 的审计、差距分析、网页恢复材料。

## 当前内容

- `2026-03-28-qinqin-live-api-gap-audit.md`
  - live API 与实现链路的差距审计
- `2026-03-30-qinqin-api-web-doc.md`
  - 网页恢复版文档整理

## 使用原则

- 本目录用于记录“文档事实”和“真实行为”的差异
- 不与 `docs/api/qinqin/` 的正式输入文档混放
- 如果后续新增 live audit、字段覆盖审计、行为偏差审计，都放在这里


## 当前正式输入文档

当前正式 Qinqin API 输入文档位于：

- `docs/api/qinqin/`

本目录中的文件只负责说明历史审计与差异，不应被当作 API 主入口。
