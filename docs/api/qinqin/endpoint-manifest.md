# Qinqin v1.1 Endpoint Manifest

本文件冻结 `v1.1` 的 8 个正式端点，供 `packages/contracts`、`services/connector-qinqin-real`、`services/data-ingestion`、`services/data-warehouse` 统一复用。

## 端点清单

| Domain | Version | Name | Method | Path | Increment Strategy | Structured Targets |
| --- | --- | --- | --- | --- | --- | --- |
| member | 1.1 | 用户（会员）基础信息 | `POST` | `/api/thirdparty/GetCustomersList` | 基础档案近窗口刷新 / 必要时全量刷新 | `customer` `customer_card` `customer_ticket` `customer_coupon` |
| member | 1.2 | 用户消费明细数据 | `POST` | `/api/thirdparty/GetConsumeBillList` | 按业务时间窗增量拉取 | `consume_bill` `consume_bill_payment` `consume_bill_info` |
| member | 1.3 | 用户充值明细数据 | `POST` | `/api/thirdparty/GetRechargeBillList` | 按业务时间窗增量拉取 | `recharge_bill` `recharge_bill_payment` `recharge_bill_ticket` `recharge_bill_sales` |
| member | 1.4 | 用户账户流水数据 | `POST` | `/api/thirdparty/GetUserTradeList` | 按业务时间窗增量拉取 | `account_trade` |
| staff | 1.5 | 技师基础信息数据 | `POST` | `/api/thirdparty/GetPersonList` | 基础档案近窗口刷新 / 必要时全量刷新 | `staff` `staff_item` |
| staff | 1.6 | 技师上钟明细数据 | `POST` | `/api/thirdparty/GetTechUpClockList` | 按业务时间窗增量拉取 | `tech_shift_item` `tech_shift_summary` |
| staff | 1.7 | 技师推销提成数据 | `POST` | `/api/thirdparty/GetTechMarketList` | 按业务时间窗增量拉取 | `sales_commission` |
| staff | 1.8 | 技师基本提成设置数据 | `POST` | `/api/thirdparty/GetTechCommissionSetList` | 日级全量覆盖 | `commission_setting` `commission_setting_detail` |

## 统一规则

- 统一鉴权与签名规则以 `docs/api/qinqin/auth-and-signing.md` 为准。
- 统一按参数名排序后拼接 `&AppSecret=...` 生成小写 MD5 签名。
- 文档中的参数大小写不一致问题，以 `connector` 代码实测结果为准，但 manifest 内部需固定一个 canonical 参数名集合。
- `v1.1` 的 ingestion 与 warehouse 不直接依赖文档命名漂移，统一依赖本 manifest。

## 调度口径

- 主同步：每天 `03:10` 启动。
- 交易类：按时间窗增量拉取并允许补采重跑。
- 档案类：默认近窗口刷新，必要时支持全量刷新。
- 配置类：按天全量覆盖。

## 备注

- 2026-03-31 live 实测确认：除 `GetCustomersList` 外，其余 7 个接口必须继续使用文档页中的旧名 path；若改成 `GetConsumptionList/GetRechargeList/GetAccountList/GetStaffList/GetTechClockList/GetSalesCommissionList/GetStaffBaseCommissionList` 会返回 `404`。
