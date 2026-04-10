# Qinqin Connector

当前 phase-1 已落地的最小 source adapter。

当前职责：

- 从 `directory/` 读取 endpoint contract 与 parameter wire name
- 从 endpoint governance binding 读取每个接口的 required / optional parameter keys
- 按 endpoint governance binding 组装 body 参数并生成 Qinqin 签名 payload
  - 分页接口生成 `PageIndex` / `PageSize`
  - 非分页 finance / staff 接口只生成 window/filter/body 参数
- 提供统一的 `fetch_page()` abstraction
  - `FixtureQinqinTransport`
  - `LiveQinqinTransport`
- 对 transport 返回统一输出：
  - `response_envelope`
  - `transport_error`
  - `replay_artifact`

当前范围：

- `qinqin.member.get_customers_list.v1_1`
- `qinqin.member.get_consume_bill_list.v1_2`
- `qinqin.member.get_recharge_bill_list.v1_3`
- `qinqin.member.get_user_trade_list.v1_4`
- `qinqin.staff.get_person_list.v1_5`
- `qinqin.staff.get_tech_up_clock_list.v1_6`
- `qinqin.staff.get_tech_market_list.v1_7`

当前约束：

- 不再假设所有 endpoint 都有 `PageIndex` / `PageSize`
- fixture transport 会按 `response_payload_shape` 回放空页 / 空结果
