# Qinqin Connector

当前 phase-1 已落地的最小 source adapter。

当前职责：

- 从 `directory/` 读取 endpoint contract 与 parameter wire name
- 从 endpoint governance binding 读取每个接口的 required / optional parameter keys
- 按共享签名规则生成 Qinqin 请求 payload
  - 分页接口生成 `PageIndex` / `PageSize`
  - 非分页 finance 接口只生成 window/filter 参数
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
