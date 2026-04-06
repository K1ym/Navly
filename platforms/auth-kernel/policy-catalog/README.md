# policy-catalog

分层：C0  
用途：承载 auth-kernel 在 milestone A 需要冻结的 vocabulary / taxonomy seed。

## 当前 seed 范围

- actor type vocabulary
- role catalog
- scope taxonomy
- namespaced capability vocabulary
- access decision status alignment
- reason / restriction / obligation taxonomy

## 当前限制

- 这些文件是 milestone A seed，不是 policy engine
- 这些文件表达 vocabulary / taxonomy 方向，不表达最终动态授权逻辑
- `access_decision_status` 的 public owner 仍是 `shared-contracts`；这里仅做本模块对齐
