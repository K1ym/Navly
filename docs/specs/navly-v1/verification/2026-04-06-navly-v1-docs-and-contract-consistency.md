# 2026-04-06 Navly_v1 Docs / Contracts / Boundaries 一致性方案

日期：2026-04-06  
状态：baseline-for-implementation-gate  
用途：定义 `Navly_v1` 在多模块并行推进下的 docs consistency、contract consistency、boundary consistency 检查口径、联动更新规则与 implementation 进入条件

---

## 1. 文档目的

本文档回答：

> 当多个 spec 窗口并行推进时，如何尽早发现 `shared-contracts`、模块 spec、architecture、api、audits、README 之间开始互相打架？

---

## 2. 本文档验证什么 / 不验证什么

### 2.1 验证对象

本文档验证以下一致性：

1. **contract consistency**：`shared-contracts` 与各模块 spec 是否仍在说同一套对象
2. **boundary consistency**：主文档与模块文档是否仍在维护同一边界
3. **docs consistency**：`specs`、`architecture`、`reference`、`api`、`audits`、`README` 是否仍然各守其位
4. **change consistency**：某类变更发生时，是否同步回写到必须联动的文档

### 2.2 不验证对象

本文档不验证：

- 代码是否已实现
- 自动化工具是否已建设
- 具体数据库 schema 或接口路径
- private secrets、环境变量具体值

---

## 3. 文档层级与 authoritative precedence

Navly_v1 当前建议按以下顺序判断“谁说了算”：

1. **版本级方向与边界**：
   - `docs/specs/navly-v1/2026-04-06-navly-v1-design.md`
   - `docs/architecture/navly-v1/2026-04-06-navly-v1-architecture.md`
2. **跨模块共享语言**：
   - `docs/specs/navly-v1/2026-04-06-navly-v1-naming-conventions.md`
   - `docs/specs/navly-v1/2026-04-06-navly-v1-shared-contracts-layer.md`
3. **模块 owner 语义**：
   - `docs/specs/navly-v1/data-platform/*`
   - `docs/specs/navly-v1/auth-kernel/*`
   - 以及后续 bridge / runtime 模块 spec
4. **输入真相源**：
   - `docs/api/*`
5. **差异与现实偏差证据**：
   - `docs/audits/*`
6. **长期词典与字典**：
   - `docs/reference/*`
7. **入口索引与推荐阅读路径**：
   - `README.md` 类文档

核心原则：

- `audits` 记录偏差，不覆盖 `api` 作为输入真相源的角色
- `README` 负责入口导航，不应悄悄引入新的主语义
- 模块 spec 负责 owner 语义，不应推翻顶层边界

---

## 4. contract consistency：检查什么

### 4.1 必查共享对象组

phase-1 必须重点检查以下共享对象组是否一致：

1. `capability/*`
2. `access/*`
3. `readiness/*`
4. `service/*`
5. `trace/*`
6. `enums/*`

### 4.2 必查语义漂移类型

重点发现以下漂移：

1. **同名异义**：名字一样，含义不同
2. **异名同义**：含义一样，名字不同
3. **字段逃逸**：核心字段被藏进 `metadata` / `extensions`
4. **owner 漂移**：本该由 shared contracts 定义的对象，被模块私自重定义
5. **枚举分叉**：同一状态 / reason code 出现多套集合

### 4.3 capability / access / readiness / service / trace 漂移如何发现

建议逐个对象做五列校验：

| 校验项 | 要问的问题 |
| --- | --- |
| Canonical name | 当前名字是否与 naming/shared-contracts 保持一致 |
| Owner doc | 是否能指出唯一主定义文档 |
| Status / enum set | 状态和值集合是否一致 |
| Required refs | 必备 ref 是否一致，例如 `decision_ref`、`state_trace_ref` |
| Consumer interpretation | 下游模块是否按同一语义消费 |

如果任一对象回答不出这五列，就应视为 contract 漂移风险。

---

## 5. 如何发现同一语义出现多套枚举

这是多窗口推进下最常见的污染来源之一。

必须重点检查：

1. `access_decision_status`
2. `readiness_status`
3. `service_status`
4. `runtime_result_status`
5. `scope_kind`
6. `reason_code` 族
7. `restriction_code` / `obligation_code`

一旦出现以下任一情况，就判定为必须回收：

- A 文档写 `unsupported_scope`，B 文档写 `scope_mismatch`，但都指 readiness status
- A 文档写 `allow / deny / restricted / escalation`，B 文档改成 `granted / blocked`
- 同一个 `reason_code` 在 runtime 和 data-platform 中分属不同 failure family

最低成本做法：

- 对共享枚举维护单一主清单
- 模块文档只引用，不重抄一套可变版本
- 只允许模块增加 owner-local 的子类代码，不允许改写 shared 主类语义

---

## 6. docs consistency：不同文档域怎么检查是否打架

### 6.1 `specs` 与 `architecture`

必须一致的内容：

- 双内核 + bridge + thin runtime 的边界判断
- 谁拥有 data truth / access truth / orchestration truth
- phase-1 主链路定义

典型打架信号：

- `architecture` 说 bridge 只是接入层，某 spec 却把 bridge 写成 capability decision owner
- `design` 说 runtime 可替换，某 spec 却要求 runtime 内部逻辑成为长期 truth source

### 6.2 `specs` 与 `reference`

必须一致的内容：

- 冻结枚举
- frozen reason code
- id/ref 命名
- registry / snapshot / state / event 后缀语义

典型打架信号：

- reference 词典和 spec 中同一枚举的名字或含义不同
- reference 仍保留旧命名，spec 已切换新命名但未回写

### 6.3 `specs` 与 `api`

必须一致的内容：

- 纳入 phase-1 的 source / endpoint / field 范围
- 输入语义与字段治理口径

典型打架信号：

- spec 假定某字段已存在，但 `api` 文档未声明
- spec 用 `audits` 的 live 偏差反向覆盖 `api` 正式输入定义

### 6.4 `api` 与 `audits`

必须保持的关系：

- `api` 是输入真相源
- `audits` 是偏差证据

典型打架信号：

- 审计结论直接被当成永久 API 契约
- spec 只引用 audit，不再引用 api 正式文档

### 6.5 `README` / 入口索引 与正文

`README` 必须做到：

- 能正确导航到 authoritative docs
- 不遗漏新增文档包
- 不保留会误导读者进入旧入口的顺序

`README` 不应该做到：

- 偷偷引入正文没有定义的新语义
- 用“简介化表述”替代正文正式结论

---

## 7. 哪些变化必须联动更新

| 变化类型 | 必须联动更新的文档 |
| --- | --- |
| 双内核 / bridge / runtime 边界变化 | `navly-v1-design`、`navly-v1-architecture`、相关模块 boundary spec、`verification-boundaries`、相关 README |
| 新增 / 重命名共享对象 | `navly-v1-shared-contracts-layer`、相关模块 spec、`verification-boundaries`、`phase-1-regression-baseline` |
| 新增 / 重命名枚举或 reason code | `navly-v1-shared-contracts-layer`、未来 `reference` 词典、受影响模块 spec、`phase-1-regression-baseline` |
| phase-1 最小闭环变化 | `data-platform-phase-1`、`auth-kernel-phase-1`、`e2e-acceptance`、`phase-1-verification-checklist`、`navly-v1/README.md` |
| capability / service object 范围变化 | `shared-contracts`、`data-platform`、`auth-kernel` capability 声明相关文档、`e2e-acceptance`、`phase-1-regression-baseline` |
| 输入域 / endpoint freeze 变化 | `docs/api/*`、`docs/audits/*`、`data-platform` spec、`e2e-acceptance`、相关 README |
| 新增专项文档包（如 bridge/runtime） | `docs/README.md`、`docs/specs/README.md`、`docs/specs/navly-v1/README.md`、`verification/README.md` |

结论：

> 文档联动更新不是润色工作，而是防止 authoritative source 分叉的结构性动作。

---

## 8. 什么时候需要回写 README / 入口索引

至少以下场景必须回写：

1. 新增一个正式 spec 子目录
2. 新增 implementation gate 文档包
3. 推荐阅读顺序已经改变
4. 某 README 仍指向旧路径或遗漏新的 authoritative source
5. 当前入口描述已足以误导新窗口读错主文档

简化原则：

> 只要一个新窗口按照 README 阅读会读错 authoritative source，就必须回写 README。

---

## 9. 怎样判断一个文档包已经足够进入 implementation

一个文档包进入 implementation，至少要满足以下 5 条：

1. **boundary closed**：owner 与非 owner 说法一致
2. **shared vocabulary frozen**：P0 共享对象和枚举已冻结
3. **e2e closed**：最小闭环成功路径与失败路径都有明确 owner 和 trace
4. **drift visible**：如果发生漂移，能够立刻指出落在哪个对象、哪个枚举、哪个文档域
5. **index updated**：README / 索引已把正确入口暴露给后续窗口

反过来，以下任一情况都说明还不够进入 implementation：

- 还在争论同一对象到底叫什么
- 还说不清 bridge/runtime 的当前 authoritative source
- 还无法区分 access failure 与 readiness failure
- 改了共享对象却没法列出需要回写哪些文档

---

## 10. Phase-1 P0 consistency checks 与可后置项

### 10.1 P0

以下属于 phase-1 P0 一致性检查：

1. 顶层 `design` / `architecture` / 模块 boundary docs 对双内核边界表述一致
2. `shared-contracts` 已冻结 capability / access / readiness / service / trace 的主对象与主枚举
3. `api` 与 `audits` 的职责分工清楚，没有出现 audit 覆盖 api 的情况
4. README / 入口索引已把 verification 文档包和当前 authoritative source 暴露出来
5. 任一共享对象变更都能立刻列出必须联动更新的文档集合

### 10.2 可以后置

以下可以后置：

- 文档自动化 lint / diff 工具
- 自动化 enum registry 导出
- richer reference dictionaries
- spec 站点化、可视化 diff 和依赖图

---

## 11. 用最小成本发现 docs / contracts / boundaries 漂移

推荐采用 **三表一索引** 的最小成本控制法：

1. **boundary ownership table**：谁拥有什么真相
2. **shared object / enum table**：哪些对象与枚举被冻结
3. **change trigger table**：哪类变化必须联动更新哪些文档
4. **README index**：把 authoritative reading path 暴露出去

这是最小成本，因为：

- 不要求先写代码
- 不要求先做自动化工具
- 只要求主文档、共享对象、入口索引三者能互相对上

核心结论：

> 多窗口 spec 并行推进时，首先要防止的不是“写得慢”，而是“每个窗口都以为自己说的是同一套东西”。
