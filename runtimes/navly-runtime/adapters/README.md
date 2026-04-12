# Runtime adapters

当前范围：

- owner-side auth adapter（capability access decision / access_context 调用面）
- owner-side data adapter（readiness / theme service 调用面）
- owner-side dependency client closure（runtime 默认可接入真实 owner surface）
- 当前 owner-side data adapter 默认支持完整 phase-1 service set，而不是只支持 `member_insight`
