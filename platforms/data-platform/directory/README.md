# Data Platform Registry Directory

本目录存放 data-platform 当前纳管对象的 registry。

当前与 Qinqin v1.1 contract governance 直接相关的正式对象包括：

- source system registry
- endpoint contract registry
- parameter canonicalization registry
- endpoint field catalog
- field landing policy registry
- source variance registry

其余 capability 相关对象仍可能保留 seed / deferred 状态：

- capability registry seed
- capability service binding seed
- capability dependency registry

当前 closeout lane 的明确约束：

- `navly.store.member_insight` 在上述三个 registry 中已经是 authoritative path
- 其余 capability 仍然是 deferred / seeded state，不应被误读为本 lane 已完成
- nightly sync policy seed

维护约束：

- runtime / bridge / auth 不应再从 Markdown 或旧代码猜参数名、字段名、path、header 组合
- 如果某个治理对象已进入本目录的 formal registry，就应优先读取本目录，而不是重复解析 `docs/api/qinqin/**`
- 不允许把 live secret 或 tenant/store 常量写进这些 registry
- nightly sync 的 planner / queue / retry / cron 语义应优先读取本目录 seed，而不是在 workflow 代码里散落字面量
- member insight 的 capability dependency / capability registry / service binding 已进入 closeout authoritative seed path
- 其余 capability 若仍未闭合，应保持 `seeded_not_implemented` / `deferred_not_implemented` 这类显式状态，而不是回到 placeholder 文件
