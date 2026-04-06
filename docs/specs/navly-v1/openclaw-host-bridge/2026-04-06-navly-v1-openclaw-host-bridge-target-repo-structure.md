# 2026-04-06 Navly_v1 openclaw-host-bridge 目标目录骨架说明

日期：2026-04-06  
状态：implementation-baseline  
用途：定义 `bridges/openclaw-host-bridge/` 的目标目录骨架、目录职责与 bridge local / shared interaction 边界

---

## 1. 目标

bridge 目录结构必须让人一眼看出：

- 哪些是宿主局部对象
- 哪些是 auth bridge
- 哪些是 runtime handoff
- 哪些只读 shared contracts

---

## 2. 推荐骨架

```text
bridges/
  openclaw-host-bridge/
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

---

## 3. 目录职责

### `adapters/openclaw/`
- 对上游 OpenClaw gateway / session / hook / tool 能力做受控适配
- 不写 Navly 业务真相

### `ingress/`
- host ingress normalization
- host evidence capture
- host_ingress_envelope（bridge local）

### `auth-linkage/`
- ingress_identity_envelope 组装
- Gate 0 调用
- authorized session linkage

### `tool-publication/`
- capability -> host tool publication
- tool_publication_manifest（bridge local）

### `runtime-handoff/`
- 组装 `runtime_request_envelope`
- 消费 `runtime_result_envelope`

### `dispatch/`
- runtime 结果投递到 host
- host_dispatch_result（bridge local）

### `diagnostics/`
- host trace
- operator diagnostics
- shared trace linkage

---

## 4. shared vs local 边界

### 共享 interaction contracts
- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`

### bridge local objects
- `host_ingress_envelope`
- `tool_publication_manifest`
- `host_dispatch_result`

---

## 5. 核心结论

bridge 的 repo structure 必须突出“宿主适配是局部层、shared interaction 是跨模块层”，防止宿主局部对象被误升格成公共契约。
