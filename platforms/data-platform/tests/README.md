# Data Platform Tests

本目录承载 data-platform 的 contract / replay / state 回归测试。

当前已覆盖：

- fixture transport regression
- live transport happy path
- transport HTTP error taxonomy
- source business error taxonomy
- replay artifact 写出
- CLI runner artifact tree
- member insight vertical slice / replay / artifact tree
- finance summary vertical slice / replay / canonical / prerequisite state
- remaining phase-1 live transport validation matrix
  - `recharge` / `account_trade` / `person` / `clock` / `market` / `commission`
  - `fixture-only` vs `live-validated`
  - expected classification path:
    - `source_empty`
    - `auth`
    - `sign`
    - `schema`
    - `transport`
- full phase-1 acceptance suite doc consistency
  - authoritative acceptance suite
  - completion board
  - go/no-go answer
- finance terminal outcome taxonomy:
  - source empty
  - auth
  - sign
  - schema
  - transport
- staff board vertical slice / canonical landing / latest-state semantics
- source empty / auth / sign / schema / transport taxonomy regression
- Qinqin v1.1 contract governance registry completeness
- capability dependency registry contract, docs, and consumer linkage
- field catalog / landing policy / variance register consistency
- commission setting quality / schema-alignment / backfill / completeness surface
- member insight owner-side readiness / theme service surface
- finance summary owner-side readiness / theme service surface
- staff board owner-side readiness / theme service surface
- daily overview aggregate readiness / theme service surface
- capability explanation companion service surface
- phase-1 service-surface registry status and shared explanation dependency wiring
