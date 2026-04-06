# 2026-04-06 Navly_v1 公共契约层方案

日期：2026-04-06  
状态：baseline-for-collaborative-implementation  
用途：定义 Navly_v1 的公共契约层边界、核心共享对象、phase-1 冻结范围与跨模块依赖规则

---

## 1. 文档目的

本文档回答：

> 在 data-platform、auth-kernel、openclaw-host-bridge、runtime 并行推进时，哪些对象必须先成为共享契约，而不能在各模块中各自发明一套？

---

## 2. 为什么公共契约层必须存在

如果没有公共契约层，多窗口并行开发很快会出现：

1. 数据中台一套 `capability_id`
2. 权限内核一套 capability 权限声明
3. bridge 一套 tool 参数
4. runtime 一套 readiness response

最后每层看起来都“差不多”，但无法稳定集成。

因此：

> `shared/contracts` 不是业务模块，但它是 Navly_v1 模块化开发的前提层。

---

## 3. 公共契约层的边界

公共契约层负责：

- 跨模块共享的对象定义
- 枚举与 reason code 主集合
- ID / ref / trace 规则
- 输入输出 envelope 规则

公共契约层不负责：

- 内部业务事实建模
- 权限策略本身
- readiness resolver 本身
- OpenClaw 接入细节
- 最终回答文本

---

## 4. phase-1 必须冻结的共享对象

### 4.1 capability 相关

- `capability_definition`
- `capability_id`
- `capability_scope_requirement`
- `capability_service_binding`

### 4.2 access 相关

- `access_context_envelope`
- `access_decision`
- `decision_ref`
- `scope_ref`

### 4.3 readiness / service 相关

- `capability_readiness_query`
- `capability_readiness_response`
- `theme_service_query`
- `theme_service_response`
- `capability_explanation_object`

### 4.4 trace / audit 相关

- `trace_ref`
- `state_trace_ref`
- `run_trace_ref`
- `data_access_audit_event`

### 4.5 runtime interaction 相关

- `runtime_request_envelope`
- `runtime_result_envelope`
- `runtime_outcome_event`
- `runtime_result_status`
- `delivery_hint`

### 4.6 reason code 相关

- `readiness_reason_code`
- `service_status`
- `access_decision_status`

---

## 5. 推荐的共享契约分组

```text
shared/contracts/
  capability/
  access/
  readiness/
  service/
  interaction/
  trace/
  enums/
```

### 5.1 capability

负责：

- capability 定义
- scope requirement
- service object 绑定

### 5.2 access

负责：

- access context
- access decision
- actor / session / scope 的标准引用形式

### 5.3 readiness

负责：

- readiness query / response
- readiness status
- blocking dependency 引用形式

### 5.4 service

负责：

- theme service query / response
- explanation object
- service status

### 5.5 interaction

负责：

- `runtime_request_envelope`
- `runtime_result_envelope`
- bridge-runtime edge 的投递提示与结果主语

### 5.6 trace

负责：

- trace refs
- 审计与追溯引用规则
- `runtime_outcome_event` 与 `data_access_audit_event` 的关联主语

### 5.7 enums

负责：

- 主枚举
- reason code 主集合

---

## 6. 与各模块的关系

### 6.1 data-platform

data-platform：

- 读取 shared contracts
- 落实 readiness / service / trace 契约
- 不私自扩写跨模块公共字段语义

### 6.2 auth-kernel

auth-kernel：

- 读取并实现 access contracts
- 输出 access context / decision
- 不私自发明另一套 capability 权限对象

### 6.3 openclaw-host-bridge

bridge：

- 读取 capability / access / interaction / service contracts
- 负责适配宿主，不改写主语义

### 6.4 runtime

runtime：

- 消费 shared contracts
- 组织交互
- 通过 interaction contracts 与 bridge 收口
- 不反向定义 readiness / access / service 真相

---

## 7. phase-1 冻结策略

### 7.1 先冻结“接口主语义”，不是先冻结所有字段

phase-1 应先冻结：

- capability id
- access context 主字段
- readiness 主字段
- service response 主字段
- interaction envelope 主字段
- trace ref 主字段
- 主枚举

而不是一开始冻结所有扩展字段。

### 7.2 可扩展字段必须显式标注

允许：

- `metadata`
- `extensions`

但核心字段不能隐藏在 `metadata` 里逃避治理。

---

## 8. 与命名规范的关系

公共契约层必须服从：

- `docs/specs/navly-v1/2026-04-06-navly-v1-naming-conventions.md`

特别是：

- `*_id`
- `*_ref`
- `*_state`
- `*_snapshot`
- `*_event`
- `*_query`
- `*_response`
- `*_envelope`

这些后缀语义必须稳定，不可在不同模块中随意变形。

---

## 9. 核心判断

Navly_v1 要想支持多窗口、高并发、低返工的模块化开发，就必须同时具备：

1. 双内核边界
2. 命名规范
3. 公共契约层

其中公共契约层的作用是：

> **把“多模块都要说的话”先收口成一套稳定语言，再让各模块各自实现自己的真相。**
