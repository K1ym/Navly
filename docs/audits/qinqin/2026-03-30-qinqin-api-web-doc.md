# Qinqin API Web 文档整理版

日期：2026-03-30  
来源阶段：legacy W2

## 文档定位

- 类型：历史网页恢复快照
- 状态：历史材料，不是当前 API 主入口
- 用途：补充共享说明、页面状态与网页原始呈现

## 1. 来源

- 原始文档页：`https://docs.apipost.net/docs/detail/5ff9e93d70ca000?target_id=3bec3710b2a10e`
- 抽取方式：Chrome headless 渲染后的 DOM 整理
- 本次对齐的网页状态：
  - 文档名：`荷塘悦色足疗连锁门店API数据对接(main)`
  - 当前页：`1.1 用户（会员）基础信息`
  - 页面创建时间：`2026-03-24 17:18:01`
  - 页面更新时间：`2026-03-30 11:41:35`

说明：

- 本文档按网页结构重排为 Markdown。
- 该网页恢复快照在当时只完整整理了 `1.1 用户（会员）基础信息`。
- 当前 Navly 已另行将 `1.2 ~ 1.8` 整理为分页 API 输入文档；本文件仅保留网页恢复快照用途。

## 2. 接口目录

当前页面左侧树中可见的接口如下，均为 `POST`：

1. `1.1 用户（会员）基础信息`
2. `1.2 用户消费明细数据`
3. `1.3 用户充值明细数据`
4. `1.4 用户账户流水数据`
5. `1.5 技师基础信息数据`
6. `1.6 技师上钟明细数据`
7. `1.7 技师推销提成数据`
8. `1.8 技师基本提成设置数据`

## 3. 1.1 用户（会员）基础信息

### 3.1 基本信息

- 接口名称：`1.1 用户（会员）基础信息`
- 方法：`POST`
- 地址：`http://rept.qqinsoft.cn/api/thirdparty/GetCustomersList`
- 状态：`开发中`
- 认证方式：网页显示为 `继承父级`

### 3.2 详细说明

#### 访问时间限制

- 正式访问窗口：每日 `03:00-04:00`
- 数据对接调试阶段：每日 `03:00-18:00`

#### 凭证信息

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `OrgID` | `627149864218629` | 门店白名单 OrgID |
| `AppSecret` | `<redacted-app-secret>` | 固定值，所有门店一致 |

#### 门店白名单

| 机构名称 | OrgId |
| --- | --- |
| 荷塘悦色迎宾店 | `627149864218629` |
| 荷塘悦色义乌店 | `627150985244677` |
| 荷塘悦色园中园店 | `627153074147333` |
| 荷塘悦色锦苑店 | `627152677269509` |
| 荷塘悦色华美店 | `627152412155909` |

### 3.3 签名生成算法

网页正文明确要求使用自定义签名，不是 bearer token。

#### 步骤 1：收集请求参数

- 收集所有请求参数
- 排除 `Sign` 字段

网页给出的说明示例：

```json
{
  "OrgId": "627152412155909",
  "Page": 1,
  "PageSize": 10,
  "STime": "2026-02-01 09:00:00",
  "ETime": "2026-04-01 09:00:00"
}
```

#### 步骤 2：参数排序

- 按参数名 ASCII 升序排序
- 忽略大小写

#### 步骤 3：拼接待签名字符串

- 使用 `&` 连接排序后的参数
- 末尾追加固定 `AppSecret`

网页示例：

```text
ETime=2026-04-01 09:00:00&OrgId=627152412155909&Page=1&PageSize=10&STime=2026-02-01 09:00:00&AppSecret=<redacted-app-secret>
```

#### 步骤 4：MD5

- 对待签名字符串做 `MD5`
- 输出小写十六进制字符串

网页说明：

```text
string sign = MD5(待签名字符串).ToLower();
```

### 3.4 请求参数

网页请求示例显示该接口使用 `raw-json` body，示例如下：

```json
{
  "Sign": "d03e7bd50f8c364e249ec18658d3d902",
  "OrgId": "627149864218629",
  "Stime": "2026-02-24 09:00:00",
  "Etime": "2026-03-24 09:00:00",
  "PageIndex": 1,
  "PageSize": 20
}
```

按网页表格与示例整理：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `Sign` | `string` | 是 | 签名 |
| `OrgId` | `string` | 是 | 操作门店 ID |
| `Stime` | `string` | 是 | 开始时间 |
| `Etime` | `string` | 是 | 结束时间 |
| `PageIndex` | `number` | 是 | 页码 |
| `PageSize` | `number` | 是 | 每页数据量 |

### 3.5 响应示例

网页成功响应的 envelope 结构：

```json
{
  "Code": 200,
  "Msg": "操作成功",
  "RetData": {
    "Total": 86,
    "Data": [
      {
        "Id": "a9040b63-e76e-4e71-b08a-dad001cd3d3c",
        "Avatar": "",
        "Name": "",
        "OrgId": "a382075a-8e74-4359-b311-dc355523663e",
        "Phone": "18670475200",
        "Labels": [],
        "Assets": ["储值卡 1张"],
        "StoredAmount": 1000,
        "ConsumeAmount": 0,
        "CTime": "2025-04-10",
        "LastConsumeTime": "2025-04-10",
        "SilentDays": 349,
        "MarketerId": "",
        "MarketerCode": "",
        "MarketerName": "",
        "Cards": {
          "Stores": [
            {
              "Id": "561a38fd-68cd-4bab-a6cf-ace187fc2476",
              "Name": "荷塘悦色华美店"
            }
          ],
          "Storeds": [
            {
              "Balance": 1799,
              "DonateBalance": 400,
              "Total": 2300,
              "Reality": 1900,
              "Donate": 400,
              "Consume": 201,
              "IsOverdue": false,
              "Overdue": 0,
              "IsDonate": false,
              "IsGift": false,
              "IsBindSMS": true,
              "OpenTime": "2026-01-29 14:45:13",
              "ExpireTime": "2126-01-29 00:00:00",
              "LastUseTime": "2026-01-29 14:46:26",
              "Remark": "",
              "OptId": "561a38fd-68cd-4bab-a6cf-ace187fc2476",
              "Operator": "军座",
              "OptTime": "2026-01-29 14:45:13",
              "State": 1,
              "WX_CardId": "",
              "OpenId": "",
              "OpenCode": "",
              "OpenName": "",
              "InviteIntegral": 0
            }
          ],
          "Equitys": [],
          "Tickets": [],
          "Coupons": []
        }
      }
    ]
  }
}
```

网页表格中明确可见的响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `Code` | `number` | 状态码，成功示例为 `200` |
| `Msg` | `string` | 结果消息，成功示例为 `操作成功` |
| `RetData` | `object` | 返回体 |
| `RetData.Total` | `number` | 总数据量 |
| `RetData.Data` | `array` | 数据列表 |
| `RetData.Data[].Id` | `string` | 用户 ID |
| `RetData.Data[].Avatar` | `string` | 头像 |
| `RetData.Data[].Name` | `string` | 名称 |
| `RetData.Data[].OrgId` | `string` | 门店 ID |
| `RetData.Data[].Phone` | `string` | 手机 |

说明：

- 网页中的响应示例比表格字段更多，至少还包含 `Labels`、`Assets`、`StoredAmount`、`ConsumeAmount`、`CTime`、`LastConsumeTime`、`SilentDays`、`Marketer*`、`Cards.Storeds`、`Equitys`、`Tickets`、`Coupons`。
- 当前 Markdown 已保留网页中可见的主要响应结构，后续若逐页抽取，可再拆成共享 schema。

### 3.6 Mock 地址

- 云端 Mock：
  - `https://mock.apipost.net/mock/5fbebeaaf0ca000/api/thirdparty/GetCustomersList?apipost_id=3bec3710b2a10e`

## 4. 连通性验证

验证时间：`2026-03-30 12:37:22 CST`

### DNS / ICMP

- 已验证 `rept.qqinsoft.cn` 可解析
- `ping -c 3 rept.qqinsoft.cn` 结果：
  - 解析地址：`198.18.0.28`
  - 丢包率：`0.0%`
  - RTT：`min/avg/max = 0.253 / 0.643 / 0.869 ms`

### HTTP

已对 1.1 接口做空 body 探测：

```bash
curl -i -X POST 'http://rept.qqinsoft.cn/api/thirdparty/GetCustomersList' \
  -H 'Content-Type: application/json' \
  --data '{}'
```

返回：

```json
{"Code":-500,"Msg":"验签失败","Result":"验签失败","ReturnStatus":0}
```

这说明：

- 传输层可达
- 服务端正常接收请求
- 当前失败原因是应用层验签，不是网络不通

## 5. 当前实现影响

对 `W2` 的直接含义：

- 可以开始把 `data-ingestion / connector-qinqin-real` 从 `URL JSON import` 升级为正式 HTTP client 骨架
- 需要新增：
  - 参数签名器
  - `OrgId` 白名单配置
  - 按接口分页同步
  - 时间窗与访问时间限制处理

## 6. 已知风险

- 文档中存在字段命名不一致：
  - 签名说明用 `Page / PageSize / STime / ETime`
  - 请求示例用 `PageIndex / PageSize / Stime / Etime`
  - `OrgID / OrgId` 大小写也有差异
- 由于签名依赖参数名排序，这个差异必须在正式接入前用真实请求实测确认
- 当前网页地址使用 `http://`，需确认是否仅用于特定网络环境，或后续是否会切到 `https://`
