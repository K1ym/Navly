# Qinqin v1.1 Endpoint Manifest

本文件冻结 `v1.1` 的 8 个正式端点，供 `packages/contracts`、`services/connector-qinqin-real`、`services/data-ingestion`、`services/data-warehouse` 统一复用。

## 端点清单

| Domain | Version | Endpoint Contract ID | Name | Method | Path | Increment Strategy | Structured Targets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| member | 1.1 | `qinqin.member.get_customers_list.v1_1` | 用户（会员）基础信息 | `POST` | `/api/thirdparty/GetCustomersList` | 基础档案近窗口刷新 / 必要时全量刷新 | `customer` `customer_card` `customer_ticket` `customer_coupon` |
| member | 1.2 | `qinqin.member.get_consume_bill_list.v1_2` | 用户消费明细数据 | `POST` | `/api/thirdparty/GetConsumeBillList` | 按业务时间窗增量拉取 | `consume_bill` `consume_bill_payment` `consume_bill_info` |
| member | 1.3 | `qinqin.member.get_recharge_bill_list.v1_3` | 用户充值明细数据 | `POST` | `/api/thirdparty/GetRechargeBillList` | 按业务时间窗增量拉取 | `recharge_bill` `recharge_bill_payment` `recharge_bill_ticket` `recharge_bill_sales` |
| member | 1.4 | `qinqin.member.get_user_trade_list.v1_4` | 用户账户流水数据 | `POST` | `/api/thirdparty/GetUserTradeList` | 按业务时间窗增量拉取 | `account_trade` |
| staff | 1.5 | `qinqin.staff.get_person_list.v1_5` | 技师基础信息数据 | `POST` | `/api/thirdparty/GetPersonList` | 基础档案近窗口刷新 / 必要时全量刷新 | `staff` `staff_item` |
| staff | 1.6 | `qinqin.staff.get_tech_up_clock_list.v1_6` | 技师上钟明细数据 | `POST` | `/api/thirdparty/GetTechUpClockList` | 按业务时间窗增量拉取 | `tech_shift_item` `tech_shift_summary` |
| staff | 1.7 | `qinqin.staff.get_tech_market_list.v1_7` | 技师推销提成数据 | `POST` | `/api/thirdparty/GetTechMarketList` | 按业务时间窗增量拉取 | `sales_commission` |
| staff | 1.8 | `qinqin.staff.get_tech_commission_set_list.v1_8` | 技师基本提成设置数据 | `POST` | `/api/thirdparty/GetTechCommissionSetList` | 日级全量覆盖 | `commission_setting` `commission_setting_detail` |

## 统一规则

- 统一鉴权与签名规则以 `docs/api/qinqin/auth-and-signing.md` 为准。
- 统一按参数名排序后拼接 `&AppSecret=...` 生成小写 MD5 签名。
- 文档中的参数大小写不一致问题，统一由 `platforms/data-platform/directory/endpoint-parameter-canonicalization.seed.json` 和 `source-variance.seed.json` 治理。
- `v1.1` 的 ingestion / runtime / bridge / auth 不直接依赖文档命名漂移，统一依赖 registry。

## 调度口径

- 主同步：每天 `03:10` 启动，按北京时间 / `Asia/Shanghai` 处理。
- 交易类：按时间窗增量拉取并允许补采重跑。
- 档案类：默认近窗口刷新，必要时支持全量刷新。
- 配置类：按天全量覆盖。

## 备注

- 2026-03-31 live 实测确认：除 `GetCustomersList` 外，其余 7 个接口必须继续使用文档页中的旧名 path；若改成 `GetConsumptionList/GetRechargeList/GetAccountList/GetStaffList/GetTechClockList/GetSalesCommissionList/GetStaffBaseCommissionList` 会返回 `404`。
- `1.8` 的额外运行时鉴权 header 已进入正式 parameter / auth profile registry，不再允许在 bridge 或 auth 代码里隐式补齐。
