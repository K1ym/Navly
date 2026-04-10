# Ingestion

本目录负责 run / endpoint run / page fetch 的执行组织。

当前已落地：

- `member_insight_vertical_slice.py`
  - 同一条 vertical slice 可在 `fixture` / `live` transport 下运行
  - endpoint run / ingestion run 历史执行真相持续写出
  - transport error 与 source business error 显式分类
  - 只把 `completed` / `source_empty` 端点送入 canonical landing
- `finance_summary_vertical_slice.py`
  - 覆盖 `GetRechargeBillList` / `GetUserTradeList`
  - 区分 paged 与 non-paged endpoint request semantics
  - endpoint run terminal outcome 分类显式写出：
    - `success`
    - `source_empty`
    - `auth`
    - `sign`
    - `schema`
    - `transport`
  - 只把 `completed` / `source_empty` 端点送入 finance canonical landing
- `staff_board_vertical_slice.py`
  - 把 `GetPersonList` / `GetTechUpClockList` / `GetTechMarketList` 串成 replayable runs
  - 失败分类细分到 `source_empty` / `source_auth_error` / `source_sign_error` / `source_schema_error` / `transport_*`
  - latest usable endpoint states 与 staff_board backbone state 分离输出

当前范围：

- `GetCustomersList`
- `GetConsumeBillList`
- `GetRechargeBillList`
- `GetUserTradeList`
- `GetPersonList`
- `GetTechUpClockList`
- `GetTechMarketList`
