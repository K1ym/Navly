# Qinqin Connector

当前 phase-1 已落地的最小 source adapter。

当前职责：

- 从 `directory/` 读取 endpoint contract 与 parameter wire name
- 按共享签名规则生成 Qinqin 请求 payload
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
