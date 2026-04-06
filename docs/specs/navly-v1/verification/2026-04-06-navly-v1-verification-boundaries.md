# 2026-04-06 Navly_v1 Verification 边界方案

日期：2026-04-06  
状态：baseline-for-implementation-gate  
用途：定义 `Navly_v1` 在 phase-1 与后续 implementation 之前的 boundary verification 口径，明确哪些模块拥有哪些真相、哪些行为说明边界已经坏了

---

## 1. 文档目的

本文档回答：

> 在 `data-platform`、`auth-kernel`、`openclaw-host-bridge`、`thin runtime shell` 并行推进时，如何验证每个模块只拥有自己应拥有的真相，而不是在集成时偷偷长成新的内核？

本文档是 verification 方案，不是实现设计文档。

---

## 2. 本文档验证什么 / 不验证什么

### 2.1 验证对象

本文档验证以下 5 类对象：

1. **truth ownership**：哪一层拥有哪一种真相
2. **allowed dependency**：模块之间允许依赖什么，不允许依赖什么
3. **write authority**：哪些对象只能由唯一 owner 定义
4. **boundary vocabulary**：跨模块对象是否都通过 `shared-contracts` 表达
5. **boundary break signal**：哪些现象一出现，就说明模块边界已经被污染

### 2.2 不验证对象

本文档不验证：

- OpenClaw 内部 hook / gateway 的具体实现
- LLM prompt、agent flow、技能编排细节
- `data-platform` 内部 canonical schema 的实现方式
- `auth-kernel` 内部规则引擎或存储实现方式
- 性能、压测、UI、运维控制台
- private secrets 或运行时配置值

---

## 3. 当前 boundary authoritative sources

| 模块 | 当前 authoritative source | 说明 |
| --- | --- | --- |
| `data-platform` | `navly-v1-design`、`navly-v1-architecture`、`data-platform/*` | 已有专项方案包 |
| `auth-kernel` | `navly-v1-design`、`navly-v1-architecture`、`auth-kernel/*` | 已有专项方案包 |
| `openclaw-host-bridge` | `navly-v1-design`、`navly-v1-modular-development-and-vibe-coding`、`navly-v1-architecture`、`openclaw-host-bridge/*` | 以专项方案包为第一 authoritative source |
| `thin runtime shell` | `navly-v1-design`、`navly-v1-modular-development-and-vibe-coding`、`navly-v1-architecture`、`runtime/*` | 以专项方案包为第一 authoritative source |
| `shared-contracts` | `navly-v1-naming-conventions`、`navly-v1-shared-contracts-layer` | 当前共享词汇与对象真相源 |

结论：

- 当前 verification 既要求“有明确 authoritative source”，也要求 bridge/runtime 的专项 spec 不再缺位。

---

## 4. truth ownership 矩阵

| 模块 | 拥有的真相 | phase-1 必须产出的主对象 | 明确不拥有的真相 |
| --- | --- | --- | --- |
| `data-platform` | source contract truth、raw truth、canonical fact truth、latest state truth、readiness truth、theme/service truth | `capability_readiness_response`、`theme_service_response`、`capability_explanation_object`、`latest_sync_state`、`state_trace_ref` | actor truth、role/scope/conversation truth、access decision truth |
| `auth-kernel` | actor truth、binding truth、Gate 0 truth、access decision truth、governance truth | `access_decision`、`access_context_envelope`、`binding_snapshot`、`decision_ref` | canonical facts、latest business date、readiness truth、service object truth |
| `openclaw-host-bridge` | ingress normalization truth、host carrier truth、host trace truth | `ingress identity envelope`、`host_session_ref`、`ingress_ref` | actor truth、binding truth、access truth、data truth、readiness truth |
| `thin runtime shell` | orchestration truth、capability selection truth、answer/fallback expression truth | runtime request context、answer/fallback outcome、runtime trace | actor/binding/access truth、latest state truth、readiness truth、service truth |
| `shared-contracts` | shared vocabulary truth、enum truth、ref naming truth | capability/access/readiness/service/trace shared objects | 数据事实、权限策略、具体运行逻辑 |

最重要的判断是：

- `data-platform` 只定义 **data truth / readiness truth**
- `auth-kernel` 只定义 **access truth**
- `openclaw-host-bridge` 不是第三内核
- `runtime` 不反向定义 kernel truth

---

## 5. boundary verification 规则

### 5.1 如何验证 data-platform 只定义 data truth / readiness truth

必须同时满足：

1. 对外只声明 `capability_id`、`service_object_id`、`readiness_status`、`reason_code`、`trace_ref` 等数据侧对象
2. 不输出 `allow / deny / restricted / escalation` 作为最终权限结论
3. 不要求下游传入 role 名才能解释业务数据
4. 不在 spec 中持有 actor 授权规则、会话绑定规则或 Gate 0 规则
5. `latest usable state` 与 `historical run truth` 分离，不拿权限结果混入数据状态

以下现象任一出现，即判为边界污染：

- 数据中台 spec 里开始定义“哪些角色可以看哪些店”
- 数据中台返回最终 `deny` 代替 `not_ready` / `unsupported_scope`
- `readiness_reason_code` 混入 access reason
- `service_object` 依赖 bridge session id 或 runtime prompt 推断出的店铺

### 5.2 如何验证 auth-kernel 只定义 access truth

必须同时满足：

1. 输出主语是 `actor_ref`、`scope_ref`、`conversation_ref`、`binding_snapshot_ref`、`decision_ref`
2. 输出状态是 `allow / deny / restricted / escalation`，而不是业务数据 ready/not ready
3. 不定义 `latest_usable_business_date`、`field_coverage_snapshot`、`theme_service_object`
4. capability policy 基于 shared contracts 声明，不基于数据平台内部表或 source endpoint 名
5. 权限失败能解释为 actor/binding/policy 问题，而不是数据缺口问题

以下现象任一出现，即判为边界污染：

- `auth-kernel` 返回“因为昨日数据未同步所以 deny”
- `auth-kernel` 直接输出业务指标摘要或主题对象
- `auth-kernel` 要求直接读取 canonical facts 表才能做决策
- `auth-kernel` 自己定义另一套 capability readiness 状态

### 5.3 如何验证 openclaw-host-bridge 不是第三内核

必须同时满足：

1. bridge 只提供 ingress evidence、host refs、message mode、tool exposure
2. bridge 不持有 canonical actor registry、binding ledger、capability policy registry
3. bridge 不持有 latest state/readiness/service object truth
4. bridge 的拒绝或放行行为必须基于 `auth-kernel` 签发结果，而不是本地硬编码
5. bridge 的数据调用必须经 runtime / `data-platform` 正式接口，不直接拼 raw / facts / permissions

以下现象任一出现，即说明 bridge 正在膨胀成第三内核：

- bridge 缓存并最终裁决 actor / scope / capability 关系
- bridge 内维护“当前店长默认看本店全部财务”之类业务授权规则
- bridge 内维护“昨日数据不可用时用前日替代”之类 readiness 逻辑
- bridge 成为多个共享枚举或 reason code 的实际 owner

### 5.4 如何验证 runtime 不反向定义 kernel truth

必须同时满足：

1. runtime 只能消费 `access_context_envelope`、`access_decision`、`capability_readiness_response`、`theme_service_response`
2. runtime 不直读 raw layer 或 canonical facts 作为默认路径
3. runtime 不自己推断当前店、当前 actor、当前允许 capability
4. runtime 的 fallback 只能解释 owner 模块已给出的结构化 reason，不得改写 owner truth
5. runtime 错误要归类为 runtime failure，而不是回写成 access failure / readiness failure

以下现象任一出现，即判为 runtime 侵入内核真相：

- runtime 用 prompt 或对话上下文自行切换 `scope_ref`
- runtime 把 `pending` 数据缺口改写成 `allow with stale answer`
- runtime 定义另一套 `capability_id`、`service_object_id` 或 trace refs
- runtime 直接读 source endpoint 或内部表并绕过 readiness / service 层

### 5.5 如何验证 shared-contracts 没有被掏空或膨胀

必须同时满足：

1. capability / access / readiness / service / trace 的共享对象都能在 shared contracts 文档中找到主定义
2. shared contracts 只定义共享语言，不定义模块内部算法
3. 同一共享枚举不在多个模块 spec 中各自造一份“稍有不同”的版本
4. 模块 spec 只能收窄到自己模块的 owner 语义，不能扩写成跨模块主语义

以下现象任一出现，即说明 shared-contracts 已失效：

- 同一 `reason_code` 在不同 spec 中含义不同
- 同一 `scope_kind` 在不同模块中出现不同值集合
- 同一 `trace_ref` 在不同模块中指代不同层级对象

---

## 6. 多窗口并行推进时，最容易漂移的对象

最容易漂移的不是大模块名，而是以下“跨模块、看似简单、最容易被顺手重定义”的对象：

1. `capability_id`
2. `service_object_id`
3. `actor_ref` / `scope_ref` / `conversation_ref`
4. `decision_ref` / `binding_snapshot_ref` / `trace_ref`
5. `readiness_status` / `service_status` / `access_decision_status`
6. `reason_code` / `restriction_code` / `obligation_code`
7. `latest_usable_business_date` 与 `historical run state` 的语义边界
8. “谁决定默认 scope / 默认日期 / fallback 日期” 这种隐式语义

原因很简单：

- 这些对象跨模块传播
- 它们很容易被实现窗口为了省事临时补一版
- 一旦分叉，e2e 还能“看起来可运行”，但已经不可长期维护

---

## 7. 用最小成本发现边界污染的方法

phase-1 推荐采用 **四步低成本检查**：

1. **owner check**：每个跨模块对象必须能指出唯一 owner 文档
2. **forbidden verb check**：看文档里有没有写出不该由该模块做的动词，例如 `decide access`、`infer latest date`、`derive actor`、`rewrite readiness`
3. **duplicate enum check**：同一语义是否出现多套枚举、多套 reason code
4. **trace chain check**：成功 / 失败是否都能回到 owner 模块的正式引用，而不是停在 bridge/runtime 的临时上下文

这是最小成本，因为它不要求先写实现，只要求：

- 有主文档
- 有共享对象清单
- 有统一命名
- 有验收链路

---

## 8. 怎样判断一个模块是不是正在偷偷侵入另一个模块的真相

只要出现以下任一模式，就应判定为“正在侵入”：

1. **它开始定义不属于自己的状态枚举**
2. **它开始生成不属于自己的主引用**
3. **它开始解释不属于自己的失败原因**
4. **它开始要求下游相信它的临时上下文而不是 owner 的正式对象**
5. **它的 README / spec 必须引用别人的内部细节才能说明自己成立**

简化判断法：

> 如果一个模块要想说清楚自己做什么，必须先把另一个模块的内部逻辑也复述一遍，那它大概率已经越界了。

---

## 9. Phase-1 P0 边界验收

以下属于 phase-1 P0：

1. 双内核与桥接层、运行时的 truth ownership 矩阵冻结
2. `capability/access/readiness/service/trace` 共享对象 owner 明确
3. 禁止依赖关系明确：
   - runtime 不直读 raw / canonical facts
   - bridge 不持有 access truth / data truth
   - `data-platform` 不持有 access truth
   - `auth-kernel` 不持有 data truth / readiness truth
4. 成功链路和失败链路都必须能定位 owner 模块
5. 桥接层和运行时当前 authoritative source 明确，不能处于“谁都能解释一点”的状态

以下可以后置：

- 自动化 doc lint
- 更丰富的策略模拟
- 多 capability 编排和复杂 multi-agent 路径
- richer host adapters / richer runtime variants

---

## 10. 哪些问题一旦出现，说明模块边界已经坏了

任意一条成立，就说明当前 spec 不能直接进入 implementation：

1. 同一语义存在两套 owner 文档
2. bridge 或 runtime 开始产出 kernel 级决定
3. `data-platform` 开始定义 access decision，或 `auth-kernel` 开始定义 readiness decision
4. 同一 `capability_id`、`scope_kind`、`reason_code` 在不同文档中含义不同
5. e2e 追溯链在 bridge/runtime 处断掉，无法回到 `decision_ref` 或 `state_trace_ref`
6. 某个模块必须通过读取另一个模块的内部表 / 内部 prompt / 内部会话状态才能成立

核心结论：

> 只要“谁定义真相”这件事开始不再清晰，Navly_v1 的 implementation 就不该启动。
