# Navly_v1 openclaw-host-bridge

状态：milestone-b backbone / host handoff only

本目录是 `Navly_v1` `openclaw-host-bridge` 的实现骨架入口。

当前已完成：

- milestone A 目录骨架与 local placeholder
- milestone B host ingress normalization backbone
- milestone B ingress identity envelope assembly
- milestone B Gate 0 enforce backbone
- milestone B authorized session linkage backbone
- milestone B `runtime_request_envelope` assembly backbone
- milestone B host dispatch handoff backbone
- milestone B host trace event backbone
- milestone B validate 脚本与最小 node tests

当前**未完成**：

- 完整 host integration
- milestone C runtime execution closure
- milestone D dispatch execution / outcome forwarding closure
- 完整 capability tool publication
- 任何业务能力逻辑
- `data-platform` / `auth-kernel` / `runtime` 内部逻辑
- upstream OpenClaw patch

## 当前 owning boundary

- 本目录只实现 `openclaw-host-bridge` 的宿主适配 / handoff / dispatch / enforce backbone
- bridge 不拥有 access truth
- bridge 不拥有 data truth
- bridge 不把 OpenClaw session / workspace 当 canonical truth
- bridge local object 保持在 bridge 内部，不提升为 shared canonical contracts
- bridge <-> runtime 只消费 `shared/contracts/interaction/` 已冻结对象
- 不修改 `shared/contracts/**`
- 不修改 `platforms/data-platform/**`
- 不修改 `platforms/auth-kernel/**`
- 不修改 `runtimes/**`
- 不修改 `upstreams/openclaw/**`

## bridge local objects

以下对象当前仍只作为 bridge local object 保留：

- `host_ingress_envelope`
- `tool_publication_manifest`
- `host_dispatch_result`
- `host_trace_event`

说明：

- 它们服务于宿主适配内部
- 它们不是 shared primary contracts
- 本轮没有把它们升级成 shared canonical handoff / result objects

## shared interaction consumption

本目录当前只消费以下 shared interaction contracts：

- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

对应 schema 路径：

- `shared/contracts/interaction/runtime_request_envelope.schema.json`
- `shared/contracts/interaction/runtime_result_envelope.schema.json`
- `shared/contracts/interaction/runtime_outcome_event.schema.json`

## milestone B backbone

当前 backbone 已覆盖：

1. `host_ingress_envelope` 归一化
2. `ingress_identity_envelope` 组装
3. Gate 0 结果 enforce
4. `authorized_session_link` 生成
5. `runtime_request_envelope` 组装
6. `host_dispatch_result` handoff 准备
7. `host_trace_event` 生成

## 当前最小 cross-module canonical slice

当前 bridge/runtime 的最小 canonical 主链统一到：

- `capability_id = navly.store.member_insight`
- `service_object_id = navly.service.store.member_insight`

`daily_overview` 不再作为当前最小 cross-module 主链默认值。

## canonical freeze

- `runtime_request_envelope` 是 bridge -> runtime 的唯一 canonical handoff 名称
- 不再使用 legacy handoff alias
- bridge local objects 不得误写成 shared interaction canonical names

## validate

运行：

```bash
bridges/openclaw-host-bridge/scripts/validate-milestone-b.sh
```
