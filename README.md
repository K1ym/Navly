<div align="center">

# Navly

**A dual-kernel store copilot architecture for WeCom / OpenClaw, rebuilt around a data middle platform and a permission/session-binding kernel.**

<p>
  <a href="docs/specs/navly-v1/2026-04-06-navly-v1-design.md">
    <img src="https://img.shields.io/badge/spec-baseline_for_implementation-0F766E?style=flat-square" alt="spec baseline" />
  </a>
  <a href="docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md">
    <img src="https://img.shields.io/badge/architecture-dual_kernel-2563EB?style=flat-square" alt="dual kernel architecture" />
  </a>
  <a href="platforms/data-platform/README.md">
    <img src="https://img.shields.io/badge/data--platform-milestone_B-0EA5E9?style=flat-square" alt="data platform milestone B" />
  </a>
  <a href="platforms/auth-kernel/README.md">
    <img src="https://img.shields.io/badge/auth--kernel-milestone_B-7C3AED?style=flat-square" alt="auth kernel milestone B" />
  </a>
  <a href="docs/README.md">
    <img src="https://img.shields.io/badge/docs-purpose_first-F59E0B?style=flat-square" alt="purpose first docs" />
  </a>
</p>

<p>
  <a href="#中文版">中文版</a> |
  <a href="#english">English</a>
</p>

</div>

> [!IMPORTANT]
> Navly in this repository is at `baseline-for-implementation / active bootstrap`.
> This README documents the current, truthful state of the repo:
> meaningful module backbones, shared contracts, and a runnable data slice are already in place,
> and the repository serves as the implementation baseline for Navly_v1's dual-kernel architecture.

## 中文版

### 1. Navly 是什么

Navly 是一个围绕双内核重建的门店 Copilot 基础设施：

- **数据中台内核**
  - 负责 raw replay、canonical facts、latest usable state、readiness、projection / serving、审计与回放
- **权限与会话绑定内核**
  - 负责 actor identity、role / scope binding、conversation binding、Gate 0、访问治理
- **Thin Runtime Shell**
  - 负责 capability routing、guarded execution、answer / fallback / escalation
- **OpenClaw Host Bridge**
  - 负责 WeCom / OpenClaw 宿主接入、runtime handoff、dispatch trace

当前第一输入域是 **Qinqin**，第一宿主接入域是 **WeCom + OpenClaw**。

一句话概括：

> Navly 的重点落在 **data truth + access truth**。

### 2. 当前状态

当前仓库已经能支撑：

- `shared/contracts/` 的跨模块共享语言冻结
- `platforms/data-platform/` 的 milestone B backbone
- `platforms/auth-kernel/` 的 milestone B backbone
- `runtimes/navly-runtime/` 的 guarded execution backbone
- `bridges/openclaw-host-bridge/` 的 host handoff backbone
- `member_insight` 的 fixture / live 最小垂直切片

当前更适合把它理解为：

- 以 `data-platform`、`auth-kernel`、`runtime`、`host-bridge` 为主干的 Navly_v1 实现基线
- 带有 `member_insight` fixture / live 垂直切片的可验证仓库
- 围绕共享契约、source-of-truth 边界与模块 handoff 持续收敛的双内核实现面
- 可继续扩展到更完整 persistence、orchestration 与 serving topology 的当前 checkpoint

### 3. 当前功能矩阵

| 模块 | 当前能力 | 当前输出 | 当前状态 |
| --- | --- | --- | --- |
| `shared/contracts/` | capability / access / readiness / service / trace / interaction schema baseline | 共享 schema、canonical IDs、frozen enums | 可作为跨模块语言基线 |
| `platforms/data-platform/` | Qinqin v1.1 registry、member insight vertical slice、raw replay、canonical landing、latest usable state separation | `customer`、`customer_card`、`consume_bill`、`consume_bill_payment`、`consume_bill_info`、readiness / theme-service owner surface | milestone B backbone |
| `platforms/auth-kernel/` | actor resolution、role / scope / conversation binding、Gate 0、capability access decision skeleton | `access_context_envelope` owner-side path | milestone B backbone |
| `runtimes/navly-runtime/` | request ingress validation、capability route、access/readiness/service wiring、runtime result closure | `runtime_result_envelope`、`runtime_outcome_event` | milestone B guarded execution backbone |
| `bridges/openclaw-host-bridge/` | host ingress normalization、identity envelope assembly、Gate 0 enforce、runtime handoff、dispatch trace backbone | `runtime_request_envelope` handoff preparation、host dispatch trace | milestone B host handoff backbone |

### 4. 架构图

```mermaid
flowchart LR
    U[Store manager / staff] --> W[WeCom]
    W --> B[OpenClaw Gateway / Host Bridge]
    B --> A[Permission Kernel]
    A --> R[Navly Runtime]
    R --> D[Data Platform Serving]
    D --> S[Theme objects / readiness / projections]
    A -. actor / role / scope / conversation .-> R
    D -. canonical facts / latest usable state / audit .-> R
```

更完整的正式设计与图示请看：

- [docs/specs/navly-v1/2026-04-06-navly-v1-design.md](docs/specs/navly-v1/2026-04-06-navly-v1-design.md)
- [docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md](docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md)
- [docs/architecture/navly-v1/diagrams/navly-v1-target-blueprint.svg](docs/architecture/navly-v1/diagrams/navly-v1-target-blueprint.svg)

### 5. 仓库结构

| 路径 | 责任 | 说明 |
| --- | --- | --- |
| [`shared/contracts/`](shared/contracts/README.md) | 跨模块共享契约 | capability / access / readiness / service / interaction / trace |
| [`platforms/data-platform/`](platforms/data-platform/README.md) | 数据中台内核 | connectors、ingestion、raw-store、warehouse、sync-state、completeness、serving |
| [`platforms/auth-kernel/`](platforms/auth-kernel/README.md) | 权限与会话绑定内核 | actor、binding、Gate 0、access context |
| [`runtimes/navly-runtime/`](runtimes/navly-runtime/README.md) | 薄执行壳 | route、guarded execution、result / outcome |
| [`bridges/openclaw-host-bridge/`](bridges/openclaw-host-bridge/README.md) | 宿主桥接层 | OpenClaw / WeCom ingress、runtime handoff、dispatch trace |
| [`docs/`](docs/README.md) | 文档体系 | specs / architecture / api / audits / runbooks / reference |

### 6. 当前已实现的关键能力

#### 6.1 数据中台

当前已经落地的最小可用 slice：

- Qinqin v1.1 formal registry
- `member_insight` fixture / live transport vertical slice
- governed nightly sync planner / carry-forward backfill cursor / full-history bootstrap default
- raw response page capture / replay artifact
- historical run truth 与 latest usable state 分离
- formal owner-side readiness / theme service surface
- live endpoint-level concurrent fetch fanout for Qinqin owner surfaces

当前范围请以 [platforms/data-platform/README.md](platforms/data-platform/README.md) 为准。

#### 6.2 权限内核

当前已闭合的最小 access 链路：

```text
host evidence
  -> actor resolution
  -> role / scope / conversation binding
  -> binding_snapshot
  -> Gate 0
  -> capability access decision
  -> access_context_envelope
```

详见 [platforms/auth-kernel/README.md](platforms/auth-kernel/README.md)。

#### 6.3 Runtime

当前 runtime 已能围绕 `capability_id` / `service_object_id` 完成：

- `runtime_request_envelope` 校验
- capability route
- access decision wiring
- readiness query wiring
- theme service query wiring
- `runtime_result_envelope` 输出闭合

详见 [runtimes/navly-runtime/README.md](runtimes/navly-runtime/README.md)。

#### 6.4 OpenClaw Host Bridge

当前 bridge 以 **宿主 handoff backbone** 为主线，当前已覆盖：

- host ingress normalization
- Gate 0 enforce backbone
- authorized session linkage
- `runtime_request_envelope` 组装
- host dispatch handoff
- host trace event generation

详见 [bridges/openclaw-host-bridge/README.md](bridges/openclaw-host-bridge/README.md)。

### 7. 快速开始

#### 7.1 环境要求

当前仓库默认假设你至少具备：

- `bash`
- `python3`
- `node`
- `rg`

仓库当前主要使用 Python / Node 标准能力和内置测试命令，不依赖一整套复杂的本地框架启动器。

#### 7.2 拉取仓库

```bash
git clone https://github.com/K1ym/Navly.git
cd Navly
```

#### 7.3 验证当前基线

```bash
bash platforms/auth-kernel/scripts/validate-milestone-b.sh
bash runtimes/navly-runtime/scripts/validate-milestone-b.sh
bash bridges/openclaw-host-bridge/scripts/validate-milestone-b.sh
python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'
```

如果你只想先验证当前仓库是否在一个健康的 baseline 上，这组命令是最先要跑的。

#### 7.4 运行数据中台最小样例

Fixture 模式：

```bash
OUTPUT_DIR="$(mktemp -d)"
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --transport fixture \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir "$OUTPUT_DIR"
```

Live 模式：

```bash
QINQIN_API_BASE_URL='http://<redacted-host>' \
QINQIN_API_REQUEST_TIMEOUT_MS='15000' \
QINQIN_API_AUTHORIZATION='Bearer <redacted-access-token>' \
QINQIN_API_TOKEN='<redacted-token>' \
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --transport live \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir "$OUTPUT_DIR"
```

运行细节请看：

- [docs/runbooks/data-platform/member-insight-live-transport.md](docs/runbooks/data-platform/member-insight-live-transport.md)

### 8. 配置与 Secrets

当前最重要的 live 配置项：

| 变量 | 是否必需 | 说明 |
| --- | --- | --- |
| `QINQIN_API_BASE_URL` | 是 | Qinqin API 基础地址 |
| `QINQIN_API_APP_SECRET` | 是 | Qinqin 签名密钥 |
| `QINQIN_API_ORG_ID` | 视调用路径而定 | 当前组织 / 门店标识 |
| `QINQIN_API_AUTHORIZATION` | 可选 / 条件必需 | 某些接口的 header 授权 |
| `QINQIN_API_TOKEN` | 可选 / 条件必需 | 某些接口的 header token |
| `QINQIN_API_REQUEST_TIMEOUT_MS` | 可选 | 请求超时 |
| `QINQIN_HISTORY_START_BUSINESS_DATE` | 可选 | 未显式指定 backfill window 时的受控全历史起点 |
| `NAVLY_QINQIN_MAX_CONCURRENT_ENDPOINT_FETCHES` | 可选 | live Qinqin endpoint 抓取并发度覆盖值 |

配置原则：

- 真实 secret 只能走本地私有 `.env`、服务器环境变量、部署平台 secret、容器 secret 或 vault
- 不要把真实 `AppSecret` / `Authorization` / `Token` 写进 README、spec、runbook 或审计文档
- 不要把 `OrgId`、host、route、permission 规则硬编码到产品逻辑

完整配置规范请看：

- [docs/reference/data-platform/secrets-and-config.md](docs/reference/data-platform/secrets-and-config.md)

### 9. 部署流程

这一节分成 **当前仓库可直接落地的部署方式** 与 **目标生产拓扑扩展方向**。

#### 9.1 当前可直接落地的部署方式

| 部署模式 | 当前适配度 | 适合场景 | 说明 |
| --- | --- | --- | --- |
| 本地验证部署 | 已提供 | 开发、评审、验证 schema / backbone / tests | 最稳定、最推荐 |
| 单机样例部署 | 已提供 | 跑 `member_insight` fixture / live slice | 通过环境变量或 secret 注入 Qinqin 配置 |
| OpenClaw / WeCom 分层联调部署 | 可按模块推进 | 宿主接入联调、handoff 验证、trace 链路检查 | 以 bridge / auth / runtime / data-platform 分层衔接为主 |
| 标准化工程部署扩展 | 可沿目标拓扑持续补齐 | 对外服务、规模化运维、标准化交付 | 可继续沉淀 Docker / Compose / Helm / K8s、数据库、调度与 richer serving substrate |

#### 9.2 推荐的当前部署顺序

如果你要在一台干净机器上把当前仓库跑起来，建议按这个顺序：

1. 准备基础环境  
   安装 `bash`、`python3`、`node`、`rg`。

2. 拉取仓库  
   `git clone` 后进入仓库目录。

3. 先跑 baseline validation  
   不要先接 live host 或 live source，先确认本地 backbone 和测试是绿的。

4. 配置数据中台 live 参数  
   只注入最小 Qinqin 配置，不要把 secrets 写入 git tracked 文件。

5. 跑 data-platform vertical slice  
   先用 `fixture`，再切 `live`；先验证 raw replay / canonical / latest state 输出是否正常。

6. 再接 runtime / auth / bridge  
   runtime 只应消费 owner-side readiness / service surface；bridge 只应做 host handoff，不要让它直接拥有数据真相或权限真相。

#### 9.3 当前单机部署示例

这是一条当前仓库可落地、但仍偏“验证环境”的流程：

```bash
git clone https://github.com/K1ym/Navly.git
cd Navly

bash platforms/auth-kernel/scripts/validate-milestone-b.sh
bash runtimes/navly-runtime/scripts/validate-milestone-b.sh
bash bridges/openclaw-host-bridge/scripts/validate-milestone-b.sh
python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'

export QINQIN_API_BASE_URL='http://<redacted-host>'
export QINQIN_API_APP_SECRET='<redacted-app-secret>'
export QINQIN_API_ORG_ID='demo-org-001'

OUTPUT_DIR="$(mktemp -d)"
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --transport live \
  --org-id "$QINQIN_API_ORG_ID" \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret "$QINQIN_API_APP_SECRET" \
  --output-dir "$OUTPUT_DIR"
```

#### 9.4 当前交付重心

当前仓库的交付重心集中在：

- milestone B backbone、共享契约与模块边界收敛
- `member_insight` fixture / live 垂直切片与 owner-side surface 验证
- bridge / auth / runtime / data-platform 的受控 handoff 主链
- 本地验证、单机样例与分层联调三类最直接的使用方式
- 面向 PostgreSQL、dbt、Temporal、richer serving substrate 与标准化部署产物的后续扩展接口

#### 9.5 目标生产拓扑

Navly 的目标生产拓扑围绕清晰分层展开：

```text
WeCom / OpenClaw host
  -> openclaw-host-bridge
  -> auth-kernel
  -> thin runtime shell
  -> data-platform serving
  -> projection / service objects
  -> reply dispatch / audit / replay
```

在更完整的 phase-1 / closeout 形态中，通常还会补齐：

- PostgreSQL truth substrate
- dbt / canonical persistence
- Temporal scheduler / worker plane
- first-party host capability publication
- live WeCom / OpenClaw end-to-end closure

这些共同构成了 Navly 面向更完整生产拓扑的扩展面，可沿现有双内核边界继续补齐。

### 10. 文档索引

推荐阅读顺序：

| 目标 | 文档 |
| --- | --- |
| 了解 Navly_v1 总体目标 | [docs/specs/navly-v1/2026-04-06-navly-v1-design.md](docs/specs/navly-v1/2026-04-06-navly-v1-design.md) |
| 了解整体结构与图示 | [docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md](docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md) |
| 了解数据中台现状 | [platforms/data-platform/README.md](platforms/data-platform/README.md) |
| 了解权限内核现状 | [platforms/auth-kernel/README.md](platforms/auth-kernel/README.md) |
| 了解 runtime 现状 | [runtimes/navly-runtime/README.md](runtimes/navly-runtime/README.md) |
| 了解 host bridge 现状 | [bridges/openclaw-host-bridge/README.md](bridges/openclaw-host-bridge/README.md) |
| 了解运行手册 | [docs/runbooks/README.md](docs/runbooks/README.md) |
| 了解配置与 secrets | [docs/reference/data-platform/secrets-and-config.md](docs/reference/data-platform/secrets-and-config.md) |

### 11. 工作原则

如果你要继续推进这个仓库，请默认遵守：

- 优先系统边界正确，而不是最小 diff
- 优先 source-of-truth 语义正确，而不是局部补丁
- 不混淆 raw truth / latest state / readiness truth / projection truth
- 不硬编码 tenant、store、route、permission、secret
- 改动架构边界时，代码与文档一起更新

更多仓库协作约束请看 [AGENTS.md](AGENTS.md)。

---

## English

### 1. What Navly Is

Navly is a store copilot foundation being rebuilt around two long-term kernels:

- **Data Platform Kernel**
  - raw replay, canonical facts, latest usable state, readiness, projection / serving, auditability
- **Permission & Session-Binding Kernel**
  - actor identity, role / scope binding, conversation binding, Gate 0, governance
- **Thin Runtime Shell**
  - capability routing, guarded execution, answer / fallback / escalation
- **OpenClaw Host Bridge**
  - WeCom / OpenClaw ingress, runtime handoff, dispatch trace

Current primary source domain: **Qinqin**  
Current primary host domain: **WeCom + OpenClaw**

### 2. Current Truthful Status

This repository already contains meaningful working slices:

- shared contract baseline
- milestone B data-platform backbone
- milestone B auth-kernel backbone
- milestone B runtime guarded-execution backbone
- milestone B host-bridge handoff backbone
- a runnable `member_insight` vertical slice

The repository is best read today as:

- an implementation baseline for Navly_v1's dual-kernel architecture
- a verifiable codebase with a runnable `member_insight` vertical slice
- a structured foundation for continued expansion into richer persistence, orchestration, and serving layers
- a practical checkpoint for local validation, module integration, and architecture convergence

### 3. Current Feature Matrix

| Module | Current scope | Current output | Status |
| --- | --- | --- | --- |
| `shared/contracts/` | shared schemas and canonical IDs | frozen cross-module language | baseline ready |
| `platforms/data-platform/` | Qinqin registry, `member_insight` slice, raw replay, canonical landing, latest-state separation | readiness / theme-service owner surface for `member_insight` | milestone B backbone |
| `platforms/auth-kernel/` | actor resolution, bindings, Gate 0, capability access skeleton | access-context owner path | milestone B backbone |
| `runtimes/navly-runtime/` | request validation, routing, access/readiness/service wiring, result closure | `runtime_result_envelope`, `runtime_outcome_event` | milestone B backbone |
| `bridges/openclaw-host-bridge/` | ingress normalization, Gate 0 enforce, runtime handoff, trace backbone | host-side handoff / trace preparation | milestone B backbone |

### 4. Quick Start

#### Prerequisites

- `bash`
- `python3`
- `node`
- `rg`

#### Validate the current baseline

```bash
bash platforms/auth-kernel/scripts/validate-milestone-b.sh
bash runtimes/navly-runtime/scripts/validate-milestone-b.sh
bash bridges/openclaw-host-bridge/scripts/validate-milestone-b.sh
python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'
```

#### Run the current data-platform sample slice

Fixture mode:

```bash
OUTPUT_DIR="$(mktemp -d)"
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --transport fixture \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir "$OUTPUT_DIR"
```

Live mode:

```bash
QINQIN_API_BASE_URL='http://<redacted-host>' \
QINQIN_API_REQUEST_TIMEOUT_MS='15000' \
QINQIN_API_AUTHORIZATION='Bearer <redacted-access-token>' \
QINQIN_API_TOKEN='<redacted-token>' \
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --transport live \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir "$OUTPUT_DIR"
```

See:

- [docs/runbooks/data-platform/member-insight-live-transport.md](docs/runbooks/data-platform/member-insight-live-transport.md)
- [docs/reference/data-platform/secrets-and-config.md](docs/reference/data-platform/secrets-and-config.md)

### 5. Deployment Guide

#### Current deployment fit

| Deployment mode | Current fit | Use case | Notes |
| --- | --- | --- | --- |
| Local validation deployment | Ready | development, review, backbone verification | the most direct starting point |
| Single-host sample deployment | Ready | running the current `member_insight` slice | inject Qinqin config through environment variables or secrets |
| Layered host-integration exercise | Available by composing bridge / auth / runtime / data slices | handoff verification, trace inspection, access/data alignment | centered on backbone integration |
| Standardized production-topology expansion | Open as the next engineering lane | external service delivery, scaled operations, standardized packaging | extend with deployment manifests, databases, schedulers, and richer serving substrate |

#### Recommended deployment sequence

1. Provision a host with `bash`, `python3`, `node`, and `rg`.
2. Clone the repository.
3. Run the baseline validation commands first.
4. Inject Qinqin configuration through environment variables or secrets management.
5. Run the data-platform slice in `fixture` mode first, then `live`.
6. Only after the data slice is healthy, integrate runtime / auth / bridge layers.

#### Current delivery focus

- milestone-B backbone, shared contracts, and boundary convergence
- the `member_insight` fixture / live vertical slice and its owner-side surfaces
- the controlled handoff chain across bridge / auth / runtime / data-platform
- local validation, single-host samples, and layered integration as the most direct operating modes
- forward expansion points for PostgreSQL, dbt, Temporal, richer serving substrate, and standardized deployment assets

### 6. Recommended Reading

- [docs/specs/navly-v1/2026-04-06-navly-v1-design.md](docs/specs/navly-v1/2026-04-06-navly-v1-design.md)
- [docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md](docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md)
- [platforms/data-platform/README.md](platforms/data-platform/README.md)
- [platforms/auth-kernel/README.md](platforms/auth-kernel/README.md)
- [runtimes/navly-runtime/README.md](runtimes/navly-runtime/README.md)
- [bridges/openclaw-host-bridge/README.md](bridges/openclaw-host-bridge/README.md)
- [docs/runbooks/README.md](docs/runbooks/README.md)
- [AGENTS.md](AGENTS.md)

### 7. Final Framing

If you remember only one sentence, let it be this:

> Navly is being rebuilt around data truth and access truth.
