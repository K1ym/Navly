# 2026-04-06 Navly_v1 OpenClaw 宿主桥接层 Phase-1 落地方案

日期：2026-04-06  
状态：phase-1-baseline  
用途：定义 `Navly_v1` `openclaw-host-bridge` 第一阶段必须闭合的宿主桥接链路、交付顺序、验收标准、后续增强与非目标

---

## 1. 文档目的

本文档回答：

> `Navly_v1` 的 `openclaw-host-bridge` phase-1 到底要落成什么，哪些能力是必须闭合，哪些能力只是后续增强，哪些耦合在第一阶段就必须禁止？

---

## 2. Phase-1 的正式定义

Phase-1 不是“把 OpenClaw 和 Navly 连起来就算完成”。

Phase-1 的正式定义是：

> 围绕 `WeCom + OpenClaw` 第一宿主接入域，打通 `gateway / message ingress / hook / session` 到 `auth-kernel`、thin `runtime shell`、`data-platform` 的第一条完整宿主桥接链路，并让该链路默认 fail closed、可追溯、可复用、可替换。

只有以下闭环同时成立，phase-1 才算完成：

```text
OpenClaw host ingress
  -> host_ingress_envelope
  -> auth-kernel Gate 0
  -> runtime_request_envelope
  -> thin runtime shell
  -> data-platform serving (经 runtime)
  -> host reply dispatch
  -> host trace + shared trace refs + outcome events
```

---

## 3. Phase-1 前提假设

### 3.1 宿主范围

phase-1 当前只覆盖：

- `OpenClaw` 作为第一宿主
- `WeCom + OpenClaw` 作为第一渠道 / 入口域
- OpenClaw 的 gateway、session、tool、hook 能力作为宿主承载能力

### 3.2 runtime 形态

phase-1 默认以 **thin runtime shell** 为目标。

也就是说：

- runtime 可以做 capability route、答案组织、fallback
- runtime 不要求 phase-1 一开始就具备复杂 multi-agent orchestration
- bridge 不能因为 runtime 还薄，就把 runtime 的职责接过去

### 3.3 data-platform 与 auth-kernel 形态

- `auth-kernel` 已提供 `Ingress Identity Envelope`、`Gate 0 Result`、`Access Context Envelope` 等正式边界
- `data-platform` 已提供 capability / readiness / theme service contracts
- phase-1 的 bridge 只消费这些稳定接口，不反向定义它们

### 3.4 secret 假设

phase-1 公开文档只描述：

- 宿主所需 secret contract
- runtime / auth / channel 运行时注入点
- host diagnostics 中必须屏蔽的 secret 类型

公开文档不保存真实 secret 值。

---

## 4. Phase-1 必须落地的能力

### 4.1 P0-1：gateway ingress normalization

必须具备：

1. 从 OpenClaw gateway message / session routing 获取宿主证据
2. 统一形成 `host_ingress_envelope`
3. 生成 `request_id` / `ingress_ref` / `host_trace_ref`
4. 附带 `host_delivery_context`

### 4.2 P0-2：auth bridge + Gate 0 enforce

必须具备：

1. 收消息后调用 `auth-kernel`
2. 透传 `actor_ref` / `session_ref` / `conversation_ref` / `decision_ref`
3. 在 `allow / deny / restricted / escalation` 上严格 fail closed
4. 支持 session resume / scope select 的 `conversation binding update`

### 4.3 P0-3：authorized runtime handoff

必须具备：

1. 将 Gate 0 通过的请求转换成 `runtime_request_envelope`
2. 明确 bridge 与 runtime 的责任切分
3. 所有运行时执行链默认挂带 `decision_ref`
4. runtime 返回结构化结果，而不是让 bridge 读 prompt 中的暗语

### 4.4 P0-4：capability tool publication

必须具备：

1. 从 shared contracts 读取 capability definition / service binding
2. 生成 capability-oriented host tools
3. 支持最小可用的 tool publication refresh / warmup
4. 禁止把 source endpoint / SQL / internal table 暴露为宿主 tool

### 4.5 P0-5：host reply dispatch

必须具备：

1. 根据 `host_delivery_context` 回写 OpenClaw host
2. 支持 direct / group / thread 等基础回复路径
3. 保持 reply dispatch 与 runtime answer composition 分离
4. 为 dispatch 结果生成 `host_dispatch_result`

### 4.6 P0-6：host trace + shared trace linking

必须具备：

1. 记录宿主 ingress / auth bridge / runtime handoff / dispatch trace
2. 将 `decision_ref`、`runtime_trace_ref`、`state_trace_ref`、`run_trace_ref` 关联到宿主 trace
3. 将必要 outcome event 回传 `auth-kernel` 或治理面
4. 提供 bounded operator diagnostics

---

## 5. Phase-1 不可缺少的完整能力链

Phase-1 必须至少支持以下 6 条完整能力链：

1. **普通消息链**
   - OpenClaw 收到 WeCom 消息
   - bridge 归一化 ingress
   - `auth-kernel` Gate 0
   - runtime 组织交互
   - data-platform 提供 capability serving
   - bridge dispatch reply

2. **受限消息链**
   - Gate 0 返回 `restricted`
   - bridge 透传 restriction / obligation
   - runtime 在受限上下文下执行或解释
   - bridge 回发受控结果

3. **拒绝 / 升级链**
   - Gate 0 返回 `deny` / `escalation`
   - bridge 不进入 runtime
   - 直接返回宿主层可解释拒绝 / 升级提示
   - 写入 trace 与 outcome

4. **session resume / handoff 链**
   - OpenClaw 恢复宿主 session
   - bridge 回链 `authorized_session_link`
   - 必要时更新 conversation binding
   - 再交由 runtime

5. **capability tool 调用链**
   - OpenClaw host tool 被触发
   - bridge 按 capability contract 归一化输入
   - 附带 access context handoff 给 runtime
   - runtime 触发 data-platform / action capability
   - bridge 回发 tool / reply 结果

6. **trace / audit 链**
   - 每次 ingress、每次 Gate 0、每次 runtime handoff、每次 dispatch 都能找到 trace
   - `decision_ref`、`runtime_trace_ref` 等能跨层回链

---

## 6. Phase-1 交付顺序

### Milestone A：host ingress + trace skeleton

目标：

- 完成 `host_ingress_envelope`
- 完成基础 `host_trace_event`
- 打通 OpenClaw gateway ingress 到 bridge 主入口

验收重点：

- direct / group / thread 入口都能得到统一 ingress object
- 不同入口不再各写一套 glue

### Milestone B：auth bridge + session linkage

目标：

- 接通 `Ingress Identity Envelope`
- 接收 `Gate 0 Result`
- 建立 `authorized_session_link`

验收重点：

- deny / escalation 可在宿主边界拦截
- resume / scope change 可更新 conversation binding

### Milestone C：runtime handoff + capability publication

目标：

- 完成 `runtime_request_envelope`
- 发布最小可用 capability tools
- 与 thin runtime shell 建立正式边界

验收重点：

- tool publication 主语是 capability，不是 source
- runtime 不再依赖宿主 raw refs 做核心判断

### Milestone D：reply dispatch + audit closure

目标：

- 完成 `host_dispatch_result`
- 完成 shared trace refs linkage
- 回传 outcome events

验收重点：

- 宿主 dispatch 与 shared trace 能闭环
- operator 能知道失败发生在 host、auth、runtime 还是 data side

---

## 7. Phase-1 必须禁止的耦合

第一阶段就必须禁止以下耦合：

1. 在 bridge 中保存 role -> capability 的最终判定逻辑
2. 在 bridge 中写 store / org / date 业务推断分支
3. 让 bridge 直接走 source endpoint / SQL / internal table 获取答案
4. 让 OpenClaw tool 暴露 `GetConsumeBillList` 之类 source-oriented 名字作为默认对外主语
5. 让 runtime 依赖 host raw ids 代替 `session_ref` / `conversation_ref`
6. 让 reply prompt 或 tool description 成为唯一权限 / 数据状态载体
7. 在 hook 中沉积业务流程、旧问答 glue、临时路由逻辑

---

## 8. 哪些能力只是后续增强

以下能力可以后置，不属于 phase-1 硬前提：

1. 多宿主并行支持（不只 OpenClaw）
2. capability tool 的热更新与复杂可视化管理
3. 更复杂的 operator dashboard / diagnostics UI
4. 更细粒度的 hook workflow 编排
5. host 级 richer streaming UI blocks / cards
6. 多 agent / rich orchestration handoff
7. 复杂 host failover、跨 host session migration
8. host 侧 capability sandbox / tenancy federation

这些都只能建立在 phase-1 主边界已经做对的前提上。

---

## 9. Phase-1 非目标

phase-1 明确不做：

1. 把 bridge 做成第三内核
2. 把 OpenClaw 做成 Navly 业务真相源
3. 把 `upstreams/openclaw/` 变成 Navly 业务代码目录
4. 在 bridge 中承接 Copilot 问答逻辑、prompt glue、deep-query glue
5. 用 hook / tool 机制偷偷绕过 `auth-kernel` 或 `data-platform`
6. 公开任何 private secret 或把 secret 泄漏进 host diagnostics

---

## 10. Phase-1 验收标准

Phase-1 完成时，至少要同时满足以下 10 条：

1. 每次宿主入口都能形成统一 `host_ingress_envelope`
2. 每次入口都必须先经过 `auth-kernel` Gate 0，再进入 runtime
3. `decision_ref`、`session_ref`、`conversation_ref` 能稳定透传
4. direct / group / thread / resume 场景都能建立宿主到授权 session 的链接
5. bridge 到 runtime 的 handoff 使用正式 envelope，而不是临时字段拼装
6. capability tool 面已经 capability-oriented，且不暴露 source endpoint / SQL / internal table
7. bridge 默认不直连 data-platform 底层表
8. 宿主 dispatch 已可回写，并能区分 host failure / runtime failure
9. 宿主 trace 与 shared trace refs 可以回链
10. 文档已明确哪些能力属于后续增强，哪些耦合必须持续禁止

---

## 11. 核心判断

`openclaw-host-bridge` 的 phase-1 不是一个“简单接线工程”，而是 Navly 在宿主边界上建立 **结构正确的第一条可运行骨架**。

这条骨架一旦做对：

- OpenClaw 可以继续作为宿主能力来源
- `auth-kernel` 与 `data-platform` 的真相边界不会被侵蚀
- runtime 可以在不破坏宿主边界的情况下继续升级

如果这条骨架做错，bridge 就会重新长成一个新的中间业务层，最终再次失去边界与可维护性。
