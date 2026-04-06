# decision

分层：L2  
用途：承载 Gate 0、access decision、session grant、restriction / obligation / escalation state。

## canonical freeze

`access_decision_status` 对齐为：

- `allow`
- `deny`
- `restricted`
- `escalation`

禁止：

- retired legacy escalation alias

当前 milestone A 只建立目录骨架，不实现 policy engine 或 runtime decision flow。
