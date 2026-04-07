# Auth Linkage Backbone

本目录承载 bridge -> auth-kernel linkage backbone。

当前 milestone B 已实现：

- `ingress_identity_envelope` assembly
- Gate 0 enforce backbone
- `authorized_session_link` backbone

当前**不**实现：

- auth-kernel 内部 actor resolution logic
- auth-kernel 内部 binding persistence
- capability access decision engine
- conversation binding write-back
