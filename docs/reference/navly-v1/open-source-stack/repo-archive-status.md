# Navly Upstreams 归档状态

日期：2026-04-06  
状态：reference  
用途：记录开源参考项目的本地归档状态，并按 Navly_v1 阶段采用策略重新分类

所有归档统一放在：

- `upstreams/`

---

## 1. 分类说明

本文件中的分类以 `Navly_v1` 的当前设计为准，而不是以“项目重要不重要”的抽象感觉为准。

当前统一分为：

- `phase-1-core`
  - 第一阶段必须进入实现主链路
- `phase-1-optional`
  - 第一阶段可以采用，但不是双内核成立的硬前提
- `phase-2-enhancement`
  - 第二阶段及以后再按需要接入
- `governance`
  - 长期治理与观测参考
- `infra`
  - 部署与网络基础设施参考

---

## 2. 归档清单

| Repo | Category | Archive Method | Local Path | Source |
| --- | --- | --- | --- | --- |
| `openclaw` | `phase-1-core` | `local_snapshot` | `upstreams/openclaw` | `current upstream source snapshot already present in project` |
| `postgres` | `phase-1-core` | `git` | `upstreams/postgres` | `https://github.com/postgres/postgres.git` |
| `dbt-core` | `phase-1-core` | `git` | `upstreams/dbt-core` | `https://github.com/dbt-labs/dbt-core.git` |
| `temporal` | `phase-1-core` | `git` | `upstreams/temporal` | `https://github.com/temporalio/temporal.git` |
| `langgraph` | `phase-1-optional` | `git` | `upstreams/langgraph` | `https://github.com/langchain-ai/langgraph.git` |
| `pgvector` | `phase-1-optional` | `git` | `upstreams/pgvector` | `https://github.com/pgvector/pgvector.git` |
| `cube` | `phase-1-optional` | `git` | `upstreams/cube` | `https://github.com/cube-js/cube.git` |
| `graphql-engine` | `phase-1-optional` | `manual_snapshot` | `upstreams/graphql-engine` | `manual root import from git-downloaded source` |
| `timescaledb` | `phase-2-enhancement` | `git` | `upstreams/timescaledb` | `https://github.com/timescale/timescaledb.git` |
| `debezium` | `phase-2-enhancement` | `git` | `upstreams/debezium` | `https://github.com/debezium/debezium.git` |
| `kafka` | `phase-2-enhancement` | `git` | `upstreams/kafka` | `https://github.com/apache/kafka.git` |
| `redpanda` | `phase-2-enhancement` | `manual_snapshot` | `upstreams/redpanda` | `manual root import from git-downloaded source` |
| `prophet` | `phase-2-enhancement` | `git` | `upstreams/prophet` | `https://github.com/facebook/prophet.git` |
| `lightgbm` | `phase-2-enhancement` | `git` | `upstreams/lightgbm` | `https://github.com/microsoft/LightGBM.git` |
| `langfuse` | `phase-2-enhancement` | `git` | `upstreams/langfuse` | `https://github.com/langfuse/langfuse.git` |
| `mem0` | `phase-2-enhancement` | `git` | `upstreams/mem0` | `https://github.com/mem0ai/mem0.git` |
| `redis` | `phase-2-enhancement` | `git` | `upstreams/redis` | `https://github.com/redis/redis.git` |
| `opentelemetry-collector` | `governance` | `git` | `upstreams/opentelemetry-collector` | `https://github.com/open-telemetry/opentelemetry-collector.git` |
| `openmetadata` | `governance` | `git` | `upstreams/openmetadata` | `https://github.com/open-metadata/OpenMetadata.git` |
| `compose` | `infra` | `git` | `upstreams/compose` | `https://github.com/docker/compose.git` |
| `tailscale` | `infra` | `git` | `upstreams/tailscale` | `https://github.com/tailscale/tailscale.git` |

---

## 3. 使用建议

### `phase-1-core`

这些项目直接对应：

- 数据中台内核
- 权限与会话绑定内核
- 全历史 / 补数 / reconcile 的主链路

### `phase-1-optional`

这些项目很有价值，但不应误解为：

- “不一起上就不算 Navly_v1”

它们主要服务于：

- semantic serving
- 上层执行增强
- 语义检索增强

### `phase-2-enhancement`

这些项目主要服务于：

- 实时事件
- 预测能力
- 执行体验增强

### `governance`

这些项目主要服务于：

- 治理
- 血缘
- 观测

### `infra`

这些项目主要服务于：

- 环境编排
- 网络打通

---

## 4. 说明

- `git` 表示以浅克隆方式归档。
- `manual_snapshot` 表示由用户手动下载后整理归档。
- `local_snapshot` 表示该目录是当前仓内已有源码快照。
- 归档存在不等于第一阶段就必须接入运行时。
