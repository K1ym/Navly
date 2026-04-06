# 2026-04-06 Navly_v1 auth-kernel 目标目录骨架说明

日期：2026-04-06  
状态：implementation-baseline  
用途：定义 `platforms/auth-kernel/` 的目标目录骨架、目录职责、C0/L0-L3 写入边界与默认消费边界

---

## 1. 目标

`auth-kernel` 的代码目录必须直接映射它的真相分层：

- C0：权限契约与策略控制
- L0：入口证据
- L1：actor / binding
- L2：Gate 0 / access decision
- L3：governance / serving

---

## 2. 推荐骨架

```text
platforms/
  auth-kernel/
    README.md
    docs/
    contracts/
    policy-catalog/
    ingress-evidence/
    actor-registry/
    bindings/
    decision/
    governance/
    serving/
    migration/
    scripts/
    tests/
```

---

## 3. 目录职责

### `contracts/`
- auth-kernel 内部 contract
- access owner 对象 schema
- 不拥有 shared contracts 主定义权

### `policy-catalog/`
- C0 registry
- role catalog
- capability policy profile
- reason / restriction / obligation taxonomy

### `ingress-evidence/`
- L0
- ingress identity evidence
- host / channel / conversation candidate evidence

### `actor-registry/`
- L1
- canonical actor
- identity alias
- actor lifecycle

### `bindings/`
- L1
- role binding
- scope binding
- conversation binding
- binding snapshot

### `decision/`
- L2
- gate0_result
- access_decision
- session_grant_snapshot
- restriction / obligation / escalation state

### `governance/`
- L3
- audit ledger
- decision trace
- override / review trail

### `serving/`
- L3
- access_context_envelope publish boundary
- decision trace view
- downstream consumption API / SDK boundary

---

## 4. 写入边界

| 目录 | 分层 | 可写对象 |
| --- | --- | --- |
| `contracts/` | C0 | auth-kernel owner contracts |
| `policy-catalog/` | C0 | policy / taxonomy / role vocab |
| `ingress-evidence/` | L0 | ingress evidence |
| `actor-registry/` | L1 | actor / alias / lifecycle |
| `bindings/` | L1 | role/scope/conversation binding |
| `decision/` | L2 | Gate 0 / access decision |
| `governance/` | L3 | governance / audit ledger |
| `serving/` | L3 | envelope / serving adapters |

---

## 5. 默认读取边界

- `openclaw-host-bridge`
- `runtime`
- `data-platform`

默认只应读取：

- `serving/` 暴露的受控 access boundary

不得默认直读：

- `bindings/`
- `decision/`
- `ingress-evidence/`

---

## 6. 长期资产 vs 实现手段

### 长期资产
- actor / binding / decision / governance 语义
- policy taxonomy
- access_context_envelope contract

### 实现手段
- 某个规则引擎库
- 某个缓存方案
- 某个 admin UI

---

## 7. 核心结论

`platforms/auth-kernel/` 必须让 access truth 在目录结构上可见，而不是把 binding、decision、governance 混在一个 service 目录里。
