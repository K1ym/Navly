# auth-kernel contracts

本目录保留 `auth-kernel` own-scope contract 与 shared contract alignment 消费层。

## 当前范围

- `contract-ownership.seed.json`：说明 auth-kernel 自有对象与 shared contracts 依赖面
- `shared-contract-alignment.mjs`：读取 `shared/contracts/**` 的 schema pattern / enum，用于 owner-side backbone 校验与 ref 构造

## 当前约束

- milestone B 仍然**不**在这里重定义 public `access_context_envelope` / `access_decision` / `decision_ref`
- `auth-kernel` 只能消费 shared public schema，并输出与其对齐的 owner-side object
