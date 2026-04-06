# actor-registry

分层：L1
用途：承载 canonical actor、identity alias、actor lifecycle 与 actor resolution backbone。

## 当前 Milestone B 内容

- `actor-registry.seed.json`
- `identity-alias-registry.seed.json`
- `identity-resolution-result.contract.seed.json`
- `actor-resolution-backbone.mjs`

## 当前边界

- actor resolution 只消费 host evidence 中的 identity evidence
- host session / workspace 不是 canonical actor truth
- 当前只做 backbone，不做外部目录系统同步
