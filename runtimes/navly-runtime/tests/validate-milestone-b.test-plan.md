# Validate Milestone B Test Plan

- 运行 `scripts/validate-milestone-b.sh`
- 验证 multi-capability route resolution closure（含 unresolved fallback）
- 验证 default service binding 与 companion explanation service binding 选择
- 验证 access decision wiring（deny / escalation fail-closed）
- 验证 restricted access 仍受控执行并保留 restriction metadata
- 验证 readiness query wiring（pending / failed / unsupported_scope explanation fallback）
- 验证 theme service query wiring（served / capability_explanation / scope_mismatch）
- 验证统一 `runtime_result_envelope` 输出主路径
