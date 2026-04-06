# Navly_v1 openclaw-host-bridge

状态：milestone-a skeleton / seed only

本目录是 `Navly_v1` `openclaw-host-bridge` 的实现骨架入口。

当前只完成：

- `bridges/openclaw-host-bridge/` 目录骨架
- host ingress + host trace skeleton
- bridge local object placeholder
- bridge <-> runtime shared interaction consumption 对齐
- 最小 validate 脚本

当前**未完成**：

- milestone B `auth-linkage` 闭环
- milestone C `runtime handoff` 执行闭环
- milestone D `dispatch + host trace linkage` 完整闭环
- 完整 host integration
- 任何业务能力逻辑
- `data-platform` / `auth-kernel` / `runtime` 内部逻辑
- upstream OpenClaw patch

## 当前 owning boundary

- 本目录只实现 `openclaw-host-bridge` 的宿主适配 skeleton
- bridge local object 保持在 bridge 内部，不提升为 shared canonical contracts
- bridge <-> runtime 只消费 `shared/contracts/interaction/` 已冻结对象
- 不修改 `shared/contracts/**`
- 不修改 `platforms/data-platform/**`
- 不修改 `platforms/auth-kernel/**`
- 不修改 `runtimes/**`
- 不修改 `upstreams/openclaw/**`

## 当前骨架

```text
bridges/openclaw-host-bridge/
  README.md
  docs/
  adapters/
    openclaw/
  ingress/
  auth-linkage/
  tool-publication/
  runtime-handoff/
  dispatch/
  diagnostics/
  migration/
  scripts/
  tests/
```

## bridge local objects

以下对象当前只作为 bridge local skeleton 保留：

- `host_ingress_envelope`
- `tool_publication_manifest`
- `host_dispatch_result`

说明：

- 它们服务于宿主适配内部
- 它们不是当前 milestone A 的 shared primary contracts
- 如后续出现新的 bridge consumer，再评估是否提升为公共契约

## shared interaction consumption

本目录当前只消费以下 shared interaction contracts：

- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

对应 schema 路径：

- `shared/contracts/interaction/runtime_request_envelope.schema.json`
- `shared/contracts/interaction/runtime_result_envelope.schema.json`
- `shared/contracts/interaction/runtime_outcome_event.schema.json`

## canonical freeze

- `runtime_request_envelope` 是 bridge -> runtime 的唯一 canonical handoff 名称
- 不再使用 legacy handoff alias
- bridge local objects 不得误写成 shared interaction canonical names

## validate

运行：

```bash
bridges/openclaw-host-bridge/scripts/validate-milestone-a.sh
```
