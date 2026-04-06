# Navly_v1 开源依赖与采用策略

日期：2026-04-06  
状态：reference-aligned-with-v1-design  
用途：说明 Navly_v1 中各 upstream 的架构位置、采用时机与阶段优先级

---

## 1. 文档目的

本文件不是“全部一起上线清单”，而是回答：

1. 哪些 upstream 属于 Navly_v1 第一阶段核心
2. 哪些 upstream 只是第一阶段可选扩展
3. 哪些 upstream 属于后续增强、治理或基础设施参考

它与正式方案文档配套使用：

- `docs/specs/navly-v1/2026-04-06-navly-v1-design.md`
- `docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md`

---

## 2. 第一阶段核心 upstream

### OpenClaw

- GitHub: `https://github.com/openclaw/openclaw`
- 本地源码：`upstreams/openclaw`
- 架构位置：接入层 + 权限/会话绑定内核
- 第一阶段定位：**必用**
- 采用原因：
  - 承担 WeCom 接入、Gateway、Session/Workspace、Gate 0、actor/role/scope/conversation 绑定
  - 是 Navly 的长期权限与会话资产来源

### PostgreSQL

- GitHub: `https://github.com/postgres/postgres`
- 架构位置：数据中台统一主存储
- 第一阶段定位：**必用**
- 采用原因：
  - 承担原始层、事实层、状态层、projection 层统一承载
  - 当前阶段先统一真相源比多存储扩展更重要

### dbt Core

- GitHub: `https://github.com/dbt-labs/dbt-core`
- 架构位置：数据中台建模与质量层
- 第一阶段定位：**必用**
- 采用原因：
  - 把事实、维度、主题、质量校验从脚本堆积提升为显式建模
  - 对 Navly 当前的数据中台建设，重要性高于高级智能编排

### Temporal

- GitHub: `https://github.com/temporalio/temporal`
- 架构位置：后台工作流与补数编排
- 第一阶段定位：**必用**
- 采用原因：
  - 全门店、全历史、可重跑、可 reconcile 需要可靠后台编排
  - 比临时 cron + 脚本更能支撑长期回溯与治理

---

## 3. 第一阶段可选扩展 upstream

以下 upstream 在第一阶段是合理的，但不是双内核成立的硬前提。

### Cube

- GitHub: `https://github.com/cube-js/cube`
- 架构位置：semantic serving / 主题查询层
- 第一阶段定位：**可选扩展**
- 适合何时采用：
  - 需要统一指标语义、预聚合、多消费端稳定查询时

### GraphQL Engine（Hasura）

- GitHub: `https://github.com/hasura/graphql-engine`
- 本地源码：`upstreams/graphql-engine`
- 架构位置：serving API / 对外读接口
- 第一阶段定位：**可选扩展**
- 适合何时采用：
  - 需要把 projection / serving objects 暴露给多个消费者，并叠加访问控制时

### pgvector

- GitHub: `https://github.com/pgvector/pgvector`
- 架构位置：语义检索增强
- 第一阶段定位：**可选扩展**
- 适合何时采用：
  - 需要对文档、解释材料、审计结果做语义检索时

### LangGraph

- GitHub: `https://github.com/langchain-ai/langgraph`
- 架构位置：上层执行层编排
- 第一阶段定位：**可选扩展**
- 适合何时采用：
  - 上层执行链复杂到单 pipeline 难以稳定治理时

---

## 4. 第二阶段与后续增强 upstream

### Debezium

- GitHub: `https://github.com/debezium/debezium`
- 架构位置：CDC
- 定位：实时增强

### Kafka / Redpanda

- GitHub: `https://github.com/apache/kafka`
- GitHub: `https://github.com/redpanda-data/redpanda`
- 架构位置：事件总线
- 定位：实时增强

### TimescaleDB

- GitHub: `https://github.com/timescale/timescaledb`
- 架构位置：时序分析增强
- 定位：分析增强

### Prophet / LightGBM

- GitHub: `https://github.com/facebook/prophet`
- GitHub: `https://github.com/microsoft/LightGBM`
- 架构位置：预测层
- 定位：智能增强

### Langfuse

- GitHub: `https://github.com/langfuse/langfuse`
- 架构位置：智能层观测
- 定位：观测增强

### OpenMetadata / OpenTelemetry Collector

- GitHub: `https://github.com/open-metadata/OpenMetadata`
- GitHub: `https://github.com/open-telemetry/opentelemetry-collector`
- 架构位置：治理与观测
- 定位：治理增强

### Mem0 / Redis

- GitHub: `https://github.com/mem0ai/mem0`
- GitHub: `https://github.com/redis/redis`
- 架构位置：长期记忆 / 缓存
- 定位：执行层增强

---

## 5. 基础设施参考 upstream

### Compose

- GitHub: `https://github.com/docker/compose`
- 架构位置：环境编排
- 定位：基础设施参考

### Tailscale

- GitHub: `https://github.com/tailscale/tailscale`
- 架构位置：网络与安全
- 定位：基础设施参考

---

## 6. 阶段性判断总结

### 6.1 第一阶段必用

- OpenClaw
- PostgreSQL
- dbt Core
- Temporal

### 6.2 第一阶段可选扩展

- Cube
- GraphQL Engine（Hasura）
- pgvector
- LangGraph

### 6.3 第二阶段与后续增强

- Debezium
- Kafka
- Redpanda
- TimescaleDB
- Prophet
- LightGBM
- Langfuse
- OpenMetadata
- OpenTelemetry Collector
- Mem0
- Redis

### 6.4 基础设施参考

- Compose
- Tailscale

---

## 7. 使用原则

这份清单的作用不是“堆栈越多越先进”，而是：

1. 防止把所有 upstream 都误判为第一阶段必做
2. 防止把真正核心的双内核依赖与增强依赖混在一起
3. 保证 Navly_v1 的第一阶段先做结构正确，而不是先做技术名词堆叠
