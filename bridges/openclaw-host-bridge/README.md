# Navly_v1 openclaw-host-bridge

状态：phase-1 host publication + live handoff closeout slice

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
- first-party host skill surface
- first-party host tool surface
- real capability discovery -> host publication manifest
- live first-party tool handoff into runtime execution
- live OpenClaw first-party host plugin bundle
  - `extensions/navly-first-party-host`
  - carries bundled skills + runtime tool registration for prod profiles
- manager-facing `daily_overview` / `member_insight` / `finance_summary` / `staff_board` / `capability_explanation` formal answered surfaces on phase-1-ready data
- manager-facing surfaces在依赖缺数时仍 fail-close 为结构化 fallback / not-ready explanation
- operator-facing host tool publication with fail-closed pending surfaces
- milestone B validate 脚本与最小 node tests

当前**未完成**：

- upstream OpenClaw patch
- richer host lifecycle hooks / automatic live gateway bootstrap
- richer operator execution beyond structured pending responses
- real WeCom actor/scope bindings beyond sample auth seeds

## 当前 owning boundary

- 本目录只实现 `openclaw-host-bridge` 的宿主适配 / handoff / dispatch / enforce backbone
- bridge 不拥有 access truth
- bridge 不拥有 data truth
- bridge 不把 OpenClaw session / workspace 当 canonical truth
- bridge local object 保持在 bridge 内部，不提升为 shared canonical contracts
- bridge <-> runtime 只消费 `shared/contracts/interaction/` 已冻结对象
- bridge closeout 通过 formal registries / adapters 消费：
  - `platforms/data-platform/**`
  - `platforms/auth-kernel/**`
  - `runtimes/navly-runtime/**`
- bridge 不反向拥有这些模块的 source-of-truth 语义
- 不修改 `shared/contracts/**`
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

当前 bridge/runtime 的 first-party manager canonical surfaces 包括：

- `navly.store.daily_overview`
- `navly.store.member_insight`
- `navly.store.finance_summary`
- `navly.store.staff_board`
- `navly.system.capability_explanation`

其中 fully served 的 canonical minimal slice 仍是：

- `capability_id = navly.store.member_insight`
- `service_object_id = navly.service.store.member_insight`

`member_insight` 仍是最低层 canonical anchor slice；`finance_summary` / `staff_board` / `daily_overview` 已通过 formal owner surfaces 与 aggregate surface 接到同一条 first-party host path。

## canonical freeze

- `runtime_request_envelope` 是 bridge -> runtime 的唯一 canonical handoff 名称
- 在有效 handoff 路径中：
  - `runtime_request_envelope.decision_ref`
  - `runtime_request_envelope.access_context_envelope.decision_ref`
  必须一致
- 当前 canonical 规则是：
  - handoff 顶层 `decision_ref` 统一采用 `access_context_envelope.decision_ref`
  - `gate0_decision_ref` 继续只保留在 bridge local handoff metadata 中
- runtime ingress 会把上述一致性当成 hard precondition；bridge 不得把 raw Gate 0 ref 冒充成顶层 handoff `decision_ref`
- 不再使用 legacy handoff alias
- bridge local objects 不得误写成 shared interaction canonical names

## validate

运行：

```bash
node --test bridges/openclaw-host-bridge/tests/navly-first-party-host-plugin.test.mjs \
  bridges/openclaw-host-bridge/tests/first-party-host-surface.test.mjs \
  bridges/openclaw-host-bridge/tests/first-party-live-handoff.test.mjs \
  bridges/openclaw-host-bridge/tests/milestone-b-auth-linkage.test.mjs
```

插件安装：

```bash
node bridges/openclaw-host-bridge/scripts/install-navly-first-party-host-plugin.mjs \
  --repoRoot /opt/navly \
  --profileDir /root/.openclaw-prod \
  --dataPlatformEnvPath /etc/navly/data-platform.env \
  --defaultChannel wecom \
  --channelAccountRef openclaw-host-bridge:channel-account:wecom-main
```

然后重启：

```bash
systemctl restart openclaw-gateway.service
```

回归：

```bash
node --test bridges/openclaw-host-bridge/tests/first-party-host-surface.test.mjs \
  bridges/openclaw-host-bridge/tests/first-party-live-handoff.test.mjs \
  bridges/openclaw-host-bridge/tests/milestone-b-auth-linkage.test.mjs
```
