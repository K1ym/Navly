# Navly 数据中台：Qinqin Secrets 与运行时配置规范

日期：2026-04-06  
状态：draft-for-review  
适用范围：Navly 数据中台（Qinqin API 接入、同步、回溯、审计）

---

## 1. 文档目的

本文档定义 Navly 数据中台在接入 Qinqin API 时所需的：

- 密钥类配置
- 普通运行时配置
- 推荐环境变量命名
- 注入方式
- 安全规则
- 当前 legacy 代码中的已知读取入口

本文件的目标不是保存秘密，而是明确：

> 系统**需要什么配置**、**配置从哪里来**、**代码如何读取**、**文档为什么必须脱敏**。

---

## 2. 核心原则

### 2.1 文档不保存真实秘密

以下值不得在公开文档、设计稿、审计稿、README、spec 中保存真实值：

- `AppSecret`
- `Authorization Bearer ...`
- `Token`
- 任意等价访问凭证

文档中只能写：

- `<redacted-app-secret>`
- `Bearer <redacted-access-token>`
- `<redacted-token>`

### 2.2 真值只走运行时安全配置

真实值只能通过以下途径之一提供：

- 本地私有 `.env` / secrets 文件
- 服务器环境变量
- 部署平台 secret
- 容器 secret
- vault / 密钥管理系统

### 2.3 代码从配置读取，不从文档读取

文档负责说明：

- 需要哪些配置
- 配置用途是什么
- 哪些是必需、哪些是可选

代码负责：

- 在运行时读取这些值
- 校验是否存在
- 在缺失时做出明确状态返回

### 2.4 配置必须区分“秘密”和“普通参数”

不是所有配置都属于 secret。

例如：

- `QINQIN_API_ORG_ID`：业务配置，不是秘密
- `QINQIN_API_APP_SECRET`：秘密
- `QINQIN_API_LOOKBACK_DAYS`：普通运行参数

这种区分必须体现在：

- 文档
- 运维配置
- 代码校验逻辑

### 2.5 禁止把运行时真相硬编码进代码

Qinqin 接入相关的运行时真相不得散落硬编码在实现中。

尤其不能写死：

- `OrgId`、门店 / 区域 / HQ / manager 等语义标识
- `base URL`、路径、header 组合、私有路由目标
- secret、token、authorization 值
- endpoint 级别特殊行为、状态映射、权限判断
- 本应来自字段治理或 manifest 的字段清单

推荐做法：

- 连接参数走配置模块
- secret 走运行时注入
- endpoint / field / route 规则走 manifest、metadata 或受治理配置
- 临时兼容逻辑集中在单点适配层，不分散在业务调用代码里

---

## 3. 当前 legacy 代码中的配置读取入口

当前历史 connector 实现（尚未迁入 Navly 数据中台新目录）中，Qinqin 配置主要集中在以下模块入口：

- `services/connector-qinqin-real/src/config.ts`
- `services/connector-qinqin-real/src/index.ts`

当前 `resolveQinqinApiConfig()` 已实现的环境变量读取包括：

### 必需主配置

- `QINQIN_API_BASE_URL`
- `QINQIN_REAL_DATA_URL`（兼容旧名）
- `QINQIN_API_ORG_ID`
- `QINQIN_API_APP_SECRET`

### 凭证相关

- `QINQIN_API_AUTHORIZATION`
- `QINQIN_REAL_DATA_TOKEN`（兼容旧名，当前同时参与 authorization 兜底）
- `QINQIN_API_TOKEN`

### 重试与超时

- `QINQIN_API_RETRY_COUNT`
- `QINQIN_API_RETRY_DELAY_MS`
- `QINQIN_API_REQUEST_TIMEOUT_MS`

### 拉取窗口与分页

- `QINQIN_API_LOOKBACK_DAYS`
- `QINQIN_API_PAGE_SIZE`
- `QINQIN_API_ACCESS_MODE`
- `QINQIN_API_TIME_WINDOW_START_HOUR`
- `QINQIN_API_TIME_WINDOW_END_HOUR`
- `QINQIN_API_TIME_WINDOW_TZ`

### 语义 scope 相关

- `QINQIN_SCOPE_HQ_ID`
- `QINQIN_SCOPE_REGION_ID`
- `QINQIN_SCOPE_STORE_ID`
- `QINQIN_SCOPE_STORE_NAME`
- `QINQIN_SCOPE_MANAGER_NAME`
- `QINQIN_SCOPE_CITY`

当前 `createQinqinConnectorService()` / `createQinqinRealConnectorService()` 还会依据这些值判断：

- 是否具备 live source
- 是否回退到 mock
- 是否允许 `mode=real`

## 3.1 当前 Navly data-platform member_insight live slice 已读取的最小配置

截至 2026-04-09，`platforms/data-platform/scripts/run_member_insight_vertical_slice.py`
在 `--transport live` 下会读取以下最小配置：

### 必需

- `QINQIN_API_BASE_URL`（推荐）或 `QINQIN_REAL_DATA_URL`（兼容旧名，二选一）

### 可选

- `QINQIN_API_REQUEST_TIMEOUT_MS`
- `QINQIN_API_AUTHORIZATION`
- `QINQIN_API_TOKEN`
- `QINQIN_REAL_DATA_TOKEN`（兼容旧名）

当前约束：

- live mode 不会因为缺少 live 配置而自动回退到 fixture
- 真实 secret 仍然只允许通过运行时注入，不允许进入文档或 git tracked 文件
- 当前最小 live slice 只覆盖 `GetCustomersList` 与 `GetConsumeBillList`

---

## 4. Navly 推荐配置分层

建议将 Qinqin 配置分成 4 层。

### 4.1 Layer A：连接与身份参数

这层定义“访问哪个 API、代表哪个门店/租户”。

#### 字段

- `QINQIN_API_BASE_URL`
- `QINQIN_API_ORG_ID`

#### 性质

- 不是严格意义上的秘密
- 但属于业务环境配置

#### 要求

- 必须为每个运行环境显式配置
- 不应硬编码在代码中

---

### 4.2 Layer B：密钥与认证参数

这层定义“如何通过鉴权”。

#### 字段

- `QINQIN_API_APP_SECRET`
- `QINQIN_API_AUTHORIZATION`
- `QINQIN_API_TOKEN`

#### 性质

- 均视为 secret

#### 说明

- `AppSecret`：用于签名
- `Authorization`：主要用于 `1.8 GetTechCommissionSetList` header
- `Token`：主要用于 `1.8 GetTechCommissionSetList` header

#### 要求

- 绝不写入 docs 的真实值
- 绝不写入 git tracked 明文配置
- 绝不出现在日志里

---

### 4.3 Layer C：运行行为参数

这层定义“怎么拉、多久超时、如何分页、时间窗怎么解释”。

#### 字段

- `QINQIN_API_RETRY_COUNT`
- `QINQIN_API_RETRY_DELAY_MS`
- `QINQIN_API_REQUEST_TIMEOUT_MS`
- `QINQIN_API_LOOKBACK_DAYS`
- `QINQIN_API_PAGE_SIZE`
- `QINQIN_API_ACCESS_MODE`
- `QINQIN_API_TIME_WINDOW_START_HOUR`
- `QINQIN_API_TIME_WINDOW_END_HOUR`
- `QINQIN_API_TIME_WINDOW_TZ`

#### 性质

- 普通运行参数，不是 secret

#### 要求

- 应有默认值
- 可被环境覆盖
- 修改必须有审计说明

---

### 4.4 Layer D：语义映射参数

这层定义“拉回来的数据在 Navly 中按什么语义解释”。

#### 字段

- `QINQIN_SCOPE_HQ_ID`
- `QINQIN_SCOPE_REGION_ID`
- `QINQIN_SCOPE_STORE_ID`
- `QINQIN_SCOPE_STORE_NAME`
- `QINQIN_SCOPE_MANAGER_NAME`
- `QINQIN_SCOPE_CITY`

#### 性质

- 非 secret
- 但会影响数据中台的目录、事实层归属和主题层解释

#### 要求

- 明确区分“来源事实字段”和“运行环境补充语义”
- 不能用这些值偷偷覆盖真实事实字段

---

## 5. 推荐环境变量清单

以下是 Navly 数据中台的推荐保留变量清单。

| 变量名 | 是否必需 | 类型 | 是否 secret | 用途 |
| --- | --- | --- | --- | --- |
| `QINQIN_API_BASE_URL` | 是 | string | 否 | API 基础地址 |
| `QINQIN_API_ORG_ID` | 是 | string | 否 | 当前门店 / 组织标识 |
| `QINQIN_API_APP_SECRET` | 是 | string | 是 | 签名密钥 |
| `QINQIN_API_AUTHORIZATION` | 条件必需 | string | 是 | `1.8` Header 授权 |
| `QINQIN_API_TOKEN` | 条件必需 | string | 是 | `1.8` Header Token |
| `QINQIN_API_RETRY_COUNT` | 否 | int | 否 | 重试次数 |
| `QINQIN_API_RETRY_DELAY_MS` | 否 | int | 否 | 重试间隔 |
| `QINQIN_API_REQUEST_TIMEOUT_MS` | 否 | int | 否 | 请求超时 |
| `QINQIN_API_LOOKBACK_DAYS` | 否 | int | 否 | 默认回看天数 |
| `QINQIN_API_PAGE_SIZE` | 否 | int | 否 | 默认分页大小 |
| `QINQIN_API_ACCESS_MODE` | 否 | string | 否 | `production` / `debug` |
| `QINQIN_API_TIME_WINDOW_START_HOUR` | 否 | int | 否 | 时间窗开始小时 |
| `QINQIN_API_TIME_WINDOW_END_HOUR` | 否 | int | 否 | 时间窗结束小时 |
| `QINQIN_API_TIME_WINDOW_TZ` | 否 | string | 否 | 时间窗时区 |
| `QINQIN_SCOPE_HQ_ID` | 否 | string | 否 | HQ 语义 scope |
| `QINQIN_SCOPE_REGION_ID` | 否 | string | 否 | Region 语义 scope |
| `QINQIN_SCOPE_STORE_ID` | 否 | string | 否 | Store 语义 scope |
| `QINQIN_SCOPE_STORE_NAME` | 否 | string | 否 | Store name 补充语义 |
| `QINQIN_SCOPE_MANAGER_NAME` | 否 | string | 否 | Manager 补充语义 |
| `QINQIN_SCOPE_CITY` | 否 | string | 否 | City 补充语义 |

---

## 6. 兼容旧变量策略

当前 legacy 代码里还兼容一些旧名：

- `QINQIN_REAL_DATA_URL`
- `QINQIN_REAL_DATA_TOKEN`

建议在 Navly 数据中台中采取以下策略：

### 6.1 短期

- 允许兼容旧变量
- 但必须在代码和文档中标注为 `legacy alias`

### 6.2 中期

- 所有部署环境迁移到新变量名
- 审计日志中提示旧变量名已被弃用

### 6.3 长期

- 删除 legacy alias 支持

---

## 7. 推荐注入方式

### 7.1 本地开发

建议：

- `.env.example` 只列变量名，不给真实值
- `.env.local` / `.env.secrets` 只保存在本机
- `.gitignore` 必须覆盖这些本地 secret 文件

### 7.2 服务器 / 容器

建议：

- 环境变量注入
- Docker secret / k8s secret / 平台 secret
- 不在 compose 文件中直接写真实 secret

### 7.3 CI / 审计环境

建议：

- mock 模式默认可运行
- 只有 live 校验任务才注入真实 secret
- 审计输出必须脱敏

---

## 8. 文档与代码的边界

### 文档应该写什么

- 需要哪些配置
- 每个配置的用途
- 哪些是必需、哪些是可选
- 配置从哪里注入
- 如何安全管理

### 文档不应该写什么

- 真实 `AppSecret`
- 真实 `Authorization Bearer ...`
- 真实 `Token`
- 可以直接复制调用的生产凭证

### 代码应该做什么

- 从环境读取值
- 校验缺失
- 在必要时拒绝进入 live mode
- 在日志中对 secret 脱敏
- 把 legacy alias、默认值、兼容映射集中在单一配置边界

### 代码不应该做什么

- 把真实 secret、org/store 标识、环境地址写死在源码里
- 在多个调用点重复拼接私有 header / route 规则
- 用散落的 `if/else` 特判代替 manifest / metadata / config
- 用“先写死能跑”替代可审计的配置来源

---

## 9. 当前已知问题

基于历史代码与现有文档，当前已知有三个问题：

### 9.1 文档历史上曾直接暴露 secret 示例

尤其是：

- `AppSecret`
- `Authorization`
- `Token`

这在 Navly 中已改为脱敏显示，但运行时真实值仍需由配置提供。

### 9.2 `commission_setting_list` 对 header secret 的依赖比其他接口强

当前 `1.8 GetTechCommissionSetList` 需要：

- `Authorization`
- `Token`
- 以及一组固定 Header

因此不能简单把所有接口看成只依赖 `Sign + OrgId`。

### 9.3 旧变量命名混乱

当前 legacy 代码同时支持：

- `QINQIN_API_*`
- `QINQIN_REAL_DATA_*`

Navly 数据中台必须逐步统一到一套正式命名。

---

## 10. 推荐下一步

建议后续在 Navly 数据中台建设中同步完成：

1. 在新数据中台目录中重建 `qinqin/config` 模块
2. 明确区分：
   - 连接参数
   - secret 参数
   - 运行参数
   - 语义参数
3. 为 live mode 增加启动前配置校验
4. 为 secret 使用增加脱敏日志策略
5. 为 `.env.example` 产出模板文件
6. 将 endpoint 特例、字段清单、兼容映射逐步迁入 manifest / metadata / registry

---

## 11. 一句话规则

> 文档说明“需要什么秘密”，配置提供“真实秘密”，代码只在运行时读取秘密，而不是把秘密写进文档。 
