# Qinqin Live API Gap Audit

日期：2026-03-28  
来源阶段：legacy W2

## 文档定位

- 类型：历史审计快照
- 状态：历史材料，不代表 Navly 当前实现结论
- 用途：记录 2026-03-28 时点的 live API 差距判断

## 1. 当前实现结论

在该历史快照时间点，项目实现并不是完整的亲亲管家 live API client，而是：

- 从 `QINQIN_REAL_DATA_URL` 拉取 JSON
- 将外部导出数据标准化为 `MockFixtureBundle`
- 继续走 `connector-core` 的 `sync / replay / health / audit`
- 在缺真实来源时支持 `auto -> mock fallback`

对应代码位置：

- `services/data-ingestion / connector-qinqin-real/src/adapter.ts`
- `services/data-ingestion / connector-qinqin-real/src/index.ts`

## 2. 已具备能力

- `mode=mock | real | auto`
- `authToken` bearer header
- raw bundle 标准化
- fixture / snapshot / replay
- `connectorMode`、`fallbackToMock` 健康标记

## 3. 与 live API 的缺口

| 维度 | 当前实现 | live API 需要 | 结论 |
| --- | --- | --- | --- |
| 数据入口 | 单个 JSON URL | 真实 HTTP API / SDK | 未完成 |
| 鉴权 | 可选 bearer token | 正式认证、刷新、失效处理 | 未完成 |
| 拉取模式 | 全量导入 | 分页 / 游标 / 增量同步 | 未完成 |
| 错误处理 | `fetch` + 状态码失败 | 401 / 429 / 5xx 分类、重试、熔断 | 未完成 |
| 来源标记 | 复用现有 `source` | 精确标记真实系统来源 | 受 contract 约束 |
| 限流治理 | 无 | 速率限制与退避策略 | 未完成 |
| 观测 | connector-core 基础健康 | live API 指标、错误率、延迟 | 未完成 |

## 4. contract 影响判断

- 当前结论：`none`
- 原因：
  - 当前仓库已可在不改 `packages/contracts` 的前提下完成 import adapter + fallback
  - 若后续需要在共享 contract 中精确标记真实来源、游标、分页或 live API 元数据，才需要按需开启 `W1`
- 若开启 `W1`，建议按最小 delta 处理：
  - `non-breaking`：新增可选的 source / connector metadata
  - 避免把具体第三方 API 响应直接暴露成共享 contract

## 5. 执行结论

- `ISV-006` 已完成：gap audit 已明确
- `ISV-007` 当前阻塞：
  - 缺亲亲管家 live API 文档
  - 缺测试凭据
  - 缺认证、分页、限流真实约束

## 5.1 2026-03-30 新增文档核查结果

已通过 Chrome 渲染方式读取 Apipost 文档：

- 文档页：`https://docs.apipost.net/docs/detail/5ff9e93d70ca000?target_id=3bec3710b2a10e`
- 当前接口：`1.1 用户（会员）基础信息`
- 方法：`POST`
- 地址：`http://rept.qqinsoft.cn/api/thirdparty/GetCustomersList`
- 页面更新时间：`2026-03-30 11:41:35 CST`

从页面正文确认到的口径：

- 这不是离线导出文件接口，而是一组真实在线 HTTP API。
- 当前文档至少公开了 `1.1 ~ 1.8` 共 8 个接口：
  - 用户（会员）基础信息
  - 用户消费明细数据
  - 用户充值明细数据
  - 用户账户流水数据
  - 技师基础信息数据
  - 技师上钟明细数据
  - 技师推销提成数据
  - 技师基本提成设置数据
- 接口访问时间受限：
  - 正式访问：每日 `03:00-04:00`
  - 调试阶段：每日 `03:00-18:00`
- 鉴权不是 OAuth / bearer token，而是：
  - `OrgId` 白名单
  - 固定 `AppSecret`
  - 请求参数排序后拼接 `&AppSecret=...`
  - `MD5` 小写十六进制签名
- 文档明确列出了门店白名单 `OrgId`。

当前已确认的实现风险：

- 文档中的线上地址是 `http://`，不是 `https://`；需要先确认这是否只用于内网或调试环境。
- 文档示例存在字段命名不一致：
  - 签名说明里使用 `Page` / `STime` / `ETime`
  - 请求示例里使用 `PageIndex` / `Stime` / `Etime`
  - `OrgID` / `OrgId` 也存在大小写差异
- 因为签名算法要求按参数名排序，字段大小写与命名不一致会直接影响签名结果，必须先做一次实测确认。

对 `W2` 的直接影响：

- `ISV-007` 不再是“完全未知 API”，已经可以开始设计正式 client 骨架。
- `data-ingestion / connector-qinqin-real` 需要从 `URL JSON import` 升级为：
  - `POST` JSON 请求
  - 参数签名
  - `OrgId` 白名单管理
  - 时间窗内拉取
  - 多端点分页同步
- 在未确认字段命名与签名细节前，仍不建议直接把 live API adapter 写死为生产可用。

## 5.2 2026-03-30 连通性验证

基于正式地址 `http://rept.qqinsoft.cn/api/thirdparty/GetCustomersList` 已完成最小连通性验证：

- `ping -c 3 rept.qqinsoft.cn`
  - 解析地址：`198.18.0.28`
  - `3/3` 收到回包
  - `0.0% packet loss`
- 空 body 探测：

```http
POST /api/thirdparty/GetCustomersList HTTP/1.1
Host: rept.qqinsoft.cn
Content-Type: application/json

{}
```

返回：

```json
{"Code":-500,"Msg":"验签失败","Result":"验签失败","ReturnStatus":0}
```

结论：

- 主机、DNS、HTTP 服务均可达
- 当前失败点已缩小到应用层签名，不是网络不可达

## 6. 后续最小实施顺序

1. 拿到 live API 文档与测试凭据
2. 在 `services/data-ingestion / connector-qinqin-real/*` 内补正式 client
3. 保持 `createQinqinConnectorService()` 入口不变
4. 用现有 `connector-core` 健康、回放、fallback 机制复用上层链路
