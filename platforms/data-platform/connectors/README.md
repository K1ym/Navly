# Source Connectors

本目录承载 source adapter。

当前已落地：

- `connectors/qinqin/qinqin_substrate.py`
  - seed-backed endpoint / parameter registry 读取
  - Qinqin 签名请求构造
  - `fixture` transport
  - `live` HTTP transport
  - transport-level error taxonomy
  - replay artifact 所需的结构化 fetch result

当前边界：

- live scope 只覆盖 `GetCustomersList` + `GetConsumeBillList`
- 不在 connector 层扩成 8 端点全量 canonical
