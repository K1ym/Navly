# 2026-04-06 Navly_v1 数据中台与权限内核 / Copilot 接口方案

日期：2026-04-06  
状态：baseline-for-implementation  
用途：定义 `Navly_v1` 数据中台对外边界，尤其是与权限内核和 Copilot 的输入输出契约、责任归属和禁止耦合点

---

## 1. 文档目的

本文档回答：

> 数据中台对外应该暴露什么，不应该暴露什么；权限内核和 Copilot 分别向数据中台提供什么，又从数据中台拿走什么？

---

## 2. 总体边界原则

### 2.1 权限内核决定“能不能进”，数据中台决定“有没有数、能不能答”

- 权限内核拥有：actor、role、scope、conversation、Gate 0、access decision
- 数据中台拥有：canonical facts、latest state、readiness、theme service

### 2.2 Copilot 负责组织交互，不负责定义数据真相

Copilot 可以：

- 选择 capability
- 组织问题与输出
- 决定如何表达 ready / pending / failed

Copilot 不可以：

- 自己拼事实层
- 自己判断 latest usable business date
- 自己推断 readiness

### 2.3 数据中台只接收标准化访问上下文，不理解权限实现细节

数据中台接收的是：

- 谁在访问（标准引用）
- 当前 scope 是什么
- 当前会话 / 决策引用是什么
- 当前 capability 请求是什么

数据中台不负责解释：

- 这个决策是怎么做出来的
- 角色绑定规则如何配置
- Gate 0 具体策略是什么

### 2.4 数据平台对外接口使用 capability 与 service object，不暴露 source endpoint

对外接口的主语应是：

- `capability_id`
- `service_object_id`
- `reason_code`

其中 canonical ID 规则固定为：

- `capability_id = navly.<domain>.<capability_name>`
- `service_object_id = navly.service.<domain>.<object_name>`

说明：

- `store_member_insight`、`store_daily_overview` 等仅保留作文档短名
- 跨模块交互、shared contracts、registry、审计事件中都应使用 canonical ID，而不是短名

而不是：

- `GetConsumeBillList`
- `fct_consume_bill` 的物理表名
- 某次 SQL 语句

---

## 3. 三方责任矩阵

| 问题 | 权限内核 | 数据中台 | Copilot |
| --- | --- | --- | --- |
| 当前 actor 是谁 | 负责 | 不负责 | 只消费 |
| 当前 scope 是什么 | 负责 | 只消费 | 只消费 |
| 当前 capability 是否允许访问 | 负责 | 只验证上下文完整性 | 只消费 |
| 某 capability 当前是否 ready | 不负责 | 负责 | 只消费 |
| latest usable business date 是什么 | 不负责 | 负责 | 只消费 |
| 事实层口径 | 不负责 | 负责 | 不负责 |
| 回答内容组织与表达 | 不负责 | 不负责 | 负责 |
| 为什么拒答 / 待答 | 访问类拒答由其负责 | 数据缺口类拒答由其负责 | 负责最终用户表达 |

---

## 4. 数据中台 <-> 权限内核

### 4.1 权限内核 -> 数据中台：标准化访问上下文

数据中台要求权限内核在读请求边界提供 **Access Context Envelope**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次请求唯一标识 |
| `decision_ref` | 权限判定引用 |
| `session_ref` | 会话引用 |
| `actor_ref` | 标准 actor 引用 |
| `tenant_ref` | 租户 / 组织级引用 |
| `scope_kind` | 当前 scope 类型，如 `store` / `hq` |
| `allowed_org_ids` | 允许访问的组织范围 |
| `allowed_store_ids` | 允许访问的门店范围 |
| `granted_capability_ids` | 当前允许调用的数据 capability 列表 |
| `issued_at` / `expires_at` | 上下文有效期 |

说明：

- `role` 可作为审计附带字段透传，但数据中台不应以具体 role 名做业务判断
- 数据中台只使用该 envelope 做 scope 过滤、审计归档、边界校验
- 数据中台不重做权限决策

### 4.2 数据中台 -> 权限内核：能力声明

数据中台需要向权限内核发布 **Capability Declaration**，供权限内核建立授权策略。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `capability_id` | 数据能力唯一标识；canonical 形如 `navly.<domain>.<capability_name>` |
| `supported_scope_kind` | 能力支持的 scope 粒度 |
| `required_data_domains` | 能力依赖的数据域 |
| `service_object_id` | 默认输出对象；canonical 形如 `navly.service.<domain>.<object_name>` |
| `sensitivity_tier` | 数据敏感级别 |
| `default_filters` | 默认的 scope 过滤键 |

说明：

- 数据中台只声明“此能力是什么、需要什么数据范围”
- 权限内核负责决定“谁能用此能力”

### 4.3 数据中台 -> 权限内核：数据访问审计事件

每次数据读请求结束后，数据中台应向权限内核或统一治理面输出 **Data Access Audit Event**。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `event_id` | 审计事件 ID |
| `request_id` | 请求 ID |
| `decision_ref` | 对应的权限决策引用 |
| `actor_ref` | 访问主体 |
| `capability_id` | 访问的数据能力 |
| `scope_ref` | 实际命中的 scope |
| `business_date` | 读取的数据业务日期 |
| `result_status` | `served` / `not_ready` / `scope_mismatch` / `error` |
| `trace_refs` | 对应 readiness / theme / run 的追溯引用 |

### 4.4 明确禁止的耦合

权限内核与数据中台之间禁止：

1. 用 role 名称硬编码数据过滤逻辑
2. 让权限内核直连 canonical facts 表
3. 让数据中台保存权限策略原文
4. 用 prompt 或自然语言文本传递权限决策

---

## 5. 数据中台 <-> Copilot

### 5.1 Copilot -> 数据中台：能力就绪查询

Copilot 在组织回答前，应先调用 **Capability Readiness Query**。

推荐请求字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 请求 ID |
| `capability_id` | 目标 capability；使用 canonical `navly.<domain>.<capability_name>` |
| `target_scope` | 目标门店 / HQ 范围 |
| `target_business_date` | 希望读取的业务日期 |
| `freshness_mode` | 例如 `latest_usable` / `strict_date` |
| `access_context` | 来自权限内核的标准化 envelope |

推荐响应字段：

| 字段 | 说明 |
| --- | --- |
| `readiness_status` | `ready` / `pending` / `failed` / `unsupported_scope` |
| `latest_usable_business_date` | 当前可用业务日期 |
| `reason_codes` | 阻塞或可答原因代码 |
| `blocking_dependencies` | 未满足的数据依赖 |
| `state_trace_refs` | 对应 L2 状态引用 |

### 5.2 Copilot -> 数据中台：主题服务对象查询

当 readiness 为 `ready` 时，Copilot 应通过 **Theme Service Query** 读取默认服务对象。

推荐请求字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 请求 ID |
| `service_object_id` | 需要的服务对象；使用 canonical `navly.service.<domain>.<object_name>` |
| `capability_id` | 所属 capability |
| `target_scope` | 目标范围 |
| `target_business_date` | 目标业务日期 |
| `access_context` | 标准化访问上下文 |
| `include_explanation` | 是否同时返回解释对象 |

推荐响应字段：

| 字段 | 说明 |
| --- | --- |
| `service_status` | `served` / `not_ready` / `scope_mismatch` / `error` |
| `service_object` | 主题服务对象本体 |
| `data_window` | 服务对象实际覆盖的业务时间范围 |
| `trace_refs` | 指向 facts / state / run 的追溯引用 |
| `explanation_object` | 可选的解释对象 |

### 5.3 Copilot -> 数据中台：缺口解释查询

当 readiness 为 `pending` 或 `failed` 时，Copilot 可以读取 **Capability Explanation Query**。

推荐响应内容：

- `reason_codes`
- `human-readable explanation fragments`
- `recommended fallback action`
- `next_recheck_hint`
- `trace_refs`

说明：

- 这里返回的是结构化解释片段，不是最终用户话术
- 最终用户话术由 Copilot 负责组合

### 5.4 明确禁止的耦合

Copilot 与数据中台之间禁止：

1. 直接调用 source endpoint 名称
2. 直接执行事实层 SQL 作为默认路径
3. 以 prompt 规则替代 readiness resolver
4. 把数据中台 response 当成权限决策结果
5. 在上层写死 store / org / date fallback 逻辑掩盖数据缺口

---

## 6. 状态语义边界

| 场景 | 应由谁判断 | 对 Copilot 的返回 |
| --- | --- | --- |
| actor 无访问权限 | 权限内核 | 由权限内核拦截，数据中台不提供业务数据 |
| scope 与请求不匹配 | 数据中台边界校验 | `unsupported_scope` / `scope_mismatch` |
| 数据源窗口尚未可用 | 数据中台 readiness | `pending` + `source_window_not_ready` |
| 端点失败或 schema 漂移 | 数据中台 readiness | `failed` + 对应 `reason_code` |
| 数据已 ready，但上层组织回答失败 | Copilot | 上层自有错误，不回写为数据 readiness |

---

## 7. 推荐 reason code 方向

当前阶段建议把 reason code 规范成数据平台内部标准，而不是把解释写死成自然语言。

最小可用集合可包括：

- `source_window_not_open`
- `endpoint_run_failed`
- `endpoint_schema_misaligned`
- `dataset_not_materialized`
- `missing_dependency`
- `scope_out_of_contract`
- `stale_latest_state`
- `capability_not_registered`

这些 code 由数据中台维护，Copilot 只做表达映射。

---

## 8. 接口稳定性规则

### 8.1 对外稳定的主键应是 capability / service object

稳定接口优先暴露：

- `capability_id`
- `service_object_id`
- `reason_code`
- `trace_ref`

并且其中：

- `capability_id` 固定遵循 `navly.<domain>.<capability_name>`
- `service_object_id` 固定遵循 `navly.service.<domain>.<object_name>`

而不是物理表、原始 endpoint 或内部 job 名称。

### 8.2 所有响应都应可追溯

数据中台对外响应至少应能追溯到：

- readiness state ref
- latest sync state ref
- theme snapshot ref
- raw / run ref

### 8.3 secret 永不出接口

任何面向权限内核或 Copilot 的接口都不应暴露：

- `AppSecret`
- `Authorization`
- `Token`
- 任意等价 raw credential

---

## 9. 核心判断

Navly_v1 的正确边界不是：

- 权限、数据、问答三方都能碰一点对方的真相

而是：

- 权限内核掌握访问真相
- 数据中台掌握数据与可答真相
- Copilot 掌握交互与表达真相

只有这样，三者才能各自演化，而不重新耦合成旧系统那种“谁都能改一点、谁也说不清真相”的结构。
