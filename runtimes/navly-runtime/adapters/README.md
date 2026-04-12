# Runtime adapters

当前范围：

- owner-side auth adapter（capability access decision / access_context 调用面）
- owner-side data adapter（readiness / theme service 调用面）
- owner-side dependency client closure（runtime 默认可接入真实 owner surface）

当前 closeout lane 补充：

- owner-side data adapter 现在支持 `state_snapshot_path`
- 提供该路径时，adapter 可直接读取 persisted truth substrate owner surface，而不是重新触发 vertical slice sync
- persisted owner-surface 缺失时应 fail closed，返回 pending / not_ready，而不是隐式回退到重新同步
- `state_snapshot_path` 可以来自 repo-authoritative nightly path，也可以来自显式 transitional artifact bridge
- persisted readiness 存在但 service projection 缺失时，adapter 仍应返回 `not_ready`
