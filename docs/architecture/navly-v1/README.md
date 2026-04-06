# Navly v1 Architecture

本目录存放 `Navly_v1` 的架构资料与配套图示。

## 当前正式文档

- `2026-04-06-navly-v1-architecture.md`
  - Navly_v1 的结构分层、系统边界、当前落地子集、目标蓝图与图示使用说明

## 当前图示

- `diagrams/navly-v1-interaction-sequence.svg`
  - 说明店长/店员 → 企业微信 → OpenClaw Gateway → Hybrid 大脑 → Skills → 数据中台 的一次交互时序
- `diagrams/navly-v1-data-platform-core.svg`
  - 说明数据中台核心结构：业务原始表、CDC、Kafka、dbt、Cube.js、Hasura、Temporal、治理与监控
- `diagrams/navly-v1-target-blueprint.svg`
  - 说明 Navly 的目标全景蓝图，适合做愿景图或最终版架构图

## 使用建议

- 正式版本方案先读 `../../specs/navly-v1/2026-04-06-navly-v1-design.md`
- 架构主文档第一页优先引用 `navly-v1-data-platform-core.svg`
- 交互链路说明优先引用 `navly-v1-interaction-sequence.svg`
- 愿景 / roadmap / 最终形态说明引用 `navly-v1-target-blueprint.svg`

## 当前定位

本目录当前负责：

- Navly_v1 结构架构文档
- 架构图示归档
- 当前态与目标态的图示解释
