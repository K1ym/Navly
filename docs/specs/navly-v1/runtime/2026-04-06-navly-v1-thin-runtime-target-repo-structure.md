# 2026-04-06 Navly_v1 thin runtime shell 目标目录骨架说明

日期：2026-04-06  
状态：implementation-baseline  
用途：定义 `runtimes/navly-runtime/` 的目标目录骨架、目录职责与 runtime 的最小执行壳边界

---

## 1. 目标

runtime 的目录结构必须直接体现：

- ingress 校验
- capability route
- guarded execution
- answer/fallback/outcome

而不是回到旧 query glue / prompt glue 结构。

---

## 2. 推荐骨架

```text
runtimes/
  navly-runtime/
    README.md
    docs/
    contracts/
    ingress/
    routing/
    execution/
    answering/
    outcome/
    adapters/
    migration/
    scripts/
    tests/
```

---

## 3. 目录职责

### `contracts/`
- runtime internal contract
- route registry / answer fragment internal types
- 不拥有 shared contracts 主定义权

### `ingress/`
- `runtime_request_envelope` 校验
- runtime interaction context

### `routing/`
- capability route
- service binding selection
- route fallback planning

### `execution/`
- access guard call
- readiness query
- theme service query
- guarded dependency orchestration

### `answering/`
- answer fragments
- fallback fragments
- escalation action

### `outcome/`
- `runtime_result_envelope`
- `runtime_outcome_event`
- trace closure

### `adapters/`
- channel-neutral output adapters
- future richer runtime adapters

---

## 4. 默认读取边界

runtime 默认可读：
- shared contracts
- auth-kernel serving boundary
- data-platform serving boundary

runtime 默认不可直读：
- data-platform raw-store / warehouse
- auth-kernel bindings / decision internals
- OpenClaw host internals

---

## 5. 核心结论

runtime 的 repo structure 必须让“route / execute / answer / outcome”成为主干，而不是让 prompt glue 重新变成默认目录。
