# Qinqin API 共享认证与签名

来源阶段：legacy W2


## 文档定位

- 类型：API 输入文档
- 状态：当前有效（需结合 live audit 持续校验）
- 用途：共享认证、签名、访问时间窗、门店白名单
- 关联审计：`docs/audits/qinqin/2026-03-30-qinqin-api-web-doc.md`

## 来源

本页只整理共享规则，不发明新内容。

来源分两类：

- 原始导出：[../../reference/raw-sources/qinqin/自定义分享.md](../../reference/raw-sources/qinqin/自定义分享.md)
- 渲染恢复：[../../audits/qinqin/2026-03-30-qinqin-api-web-doc.md](../../audits/qinqin/2026-03-30-qinqin-api-web-doc.md)

说明：

- 原始导出中的 `1.1 用户（会员）基础信息` 共享说明部分出现了多处 `[object Object]`，因此这里优先使用已渲染恢复的网页内容。
- 各接口页中的请求体、响应示例、字段表仍以原始导出为准。

## 原始导出的全局说明

原始导出文件开头写的是：

- 全局 Header 参数：暂无参数
- 全局 Query 参数：暂无参数
- 全局 Body 参数：暂无参数
- 全局认证方式：`无需认证`

这个全局说明与各接口页实际内容存在冲突：

- 各接口都带 `Sign`
- 各接口认证方式显示 `继承父级`
- 实际空请求探测会返回 `验签失败`

因此不能把“全局无需认证”当作可执行结论。

## 访问时间限制

根据网页恢复内容：

- 正式访问窗口：每日 `03:00-04:00`，按北京时间 / `Asia/Shanghai` 处理
- 数据对接调试阶段：每日 `03:00-18:00`，按北京时间 / `Asia/Shanghai` 处理

## 凭证信息

根据网页恢复内容：

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `OrgID` | `demo-org-001` | 门店白名单 OrgID |
| `AppSecret` | `<redacted-app-secret>` | 真实值已脱敏，运行时应通过安全配置提供 |

## 门店白名单

根据网页恢复内容：

| 机构名称 | OrgId |
| --- | --- |
| 示例门店A | `demo-org-001` |
| 示例门店B | `demo-org-002` |
| 示例门店C | `demo-org-003` |
| 示例门店D | `demo-org-004` |
| 示例门店E | `demo-org-005` |

## 签名生成算法

根据网页恢复内容：

### 步骤 1：收集请求参数

- 收集所有请求参数
- 排除 `Sign` 字段

网页给出的说明示例：

```json
{
  "OrgId": "demo-org-005",
  "Page": 1,
  "PageSize": 10,
  "STime": "2026-02-01 09:00:00",
  "ETime": "2026-04-01 09:00:00"
}
```

### 步骤 2：参数排序

- 所有参数按参数名 ASCII 码升序排序
- 忽略大小写

### 步骤 3：拼接签名字符串

- 使用 `&` 拼接排序后的参数
- 末尾追加 `AppSecret`

网页示例：

```text
ETime=2026-04-01 09:00:00&OrgId=demo-org-005&Page=1&PageSize=10&STime=2026-02-01 09:00:00&AppSecret=<redacted-app-secret>
```

### 步骤 4：MD5

- 对待签名字符串做 `MD5`
- 输出小写十六进制字符串

网页说明：

```text
string sign = MD5(待签名字符串).ToLower();
```

## 已确认的字段不一致风险

当前至少有以下不一致：

- `Page` vs `PageIndex`
- `STime` vs `Stime`
- `ETime` vs `Etime`
- `OrgID` vs `OrgId`

由于签名依赖参数名排序，这些差异会直接影响签名结果。  
实现 live adapter 前必须先对真实接口做一次签名实测。

## 治理落点

为避免 runtime、bridge、auth 再猜参数名或签名口径，当前正式治理落点固定为：

- source system / access window / auth profile：`platforms/data-platform/directory/source-systems.seed.json`
- endpoint 参数 canonicalization：`platforms/data-platform/directory/endpoint-parameter-canonicalization.seed.json`
- 已知命名漂移 / path / shape / auth 差异：`platforms/data-platform/directory/source-variance.seed.json`

说明：

- 本页继续作为共享输入文档真相源
- 跨模块机器消费应读取上述 registry，而不是重复解析 Markdown

## 连通性验证

已验证：

- `rept.qqinsoft.cn` 可解析并可 `ping`
- `POST http://rept.qqinsoft.cn/api/thirdparty/GetCustomersList` 可达
- 空请求返回：

```json
{"Code":-500,"Msg":"验签失败","Result":"验签失败","ReturnStatus":0}
```

结论：

- 传输层可达
- 当前拦点是应用层验签，而不是网络问题
