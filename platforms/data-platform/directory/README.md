# Data Platform Registry Directory

本目录存放 data-platform 当前纳管对象的 registry。

当前与 Qinqin v1.1 contract governance 直接相关的正式对象包括：

- source system registry
- endpoint contract registry
- parameter canonicalization registry
- endpoint field catalog
- field landing policy registry
- source variance registry

其余 capability 相关对象仍可能保留 seed / placeholder 状态：

- capability registry seed
- capability service binding seed
- capability dependency placeholder

维护约束：

- runtime / bridge / auth 不应再从 Markdown 或旧代码猜参数名、字段名、path、header 组合
- 如果某个治理对象已进入本目录的 formal registry，就应优先读取本目录，而不是重复解析 `docs/api/qinqin/**`
- 不允许把 live secret 或 tenant/store 常量写进这些 registry
