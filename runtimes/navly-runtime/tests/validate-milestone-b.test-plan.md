# Validate Milestone B Test Plan

- 运行 `scripts/validate-milestone-b.sh`
- 验证 route resolution closure（含 unresolved fallback）
- 验证 default service binding selection
- 验证 access decision wiring（deny / escalation fail-closed）
- 验证 readiness query wiring（pending fallback）
- 验证 theme service query wiring（served / scope_mismatch）
- 验证统一 `runtime_result_envelope` 输出主路径
