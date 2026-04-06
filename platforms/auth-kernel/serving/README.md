# serving

分层：L3  
用途：承载 access serving boundary 与下游消费适配。

## 当前约束

- 下游默认只应通过本目录未来暴露的受控 boundary 消费 auth-kernel
- milestone A 不在这里定义 public access contract owner schema
- 与 `access_context_envelope` 相关的公共契约主定义权仍属于 `shared-contracts`
