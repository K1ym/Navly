import {
  ensureObject,
  normalizeDecisionStatus,
  validateAccessContextEnvelopeShape,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

function buildBaseResult({ hostIngressEnvelope, gate0Result, decisionStatus, now }) {
  return {
    object_name: 'gate0_enforcement_result',
    object_scope: 'bridge_local',
    request_id: hostIngressEnvelope.request_id,
    trace_ref: hostIngressEnvelope.trace_ref,
    host_trace_ref: hostIngressEnvelope.host_trace_ref,
    decision_ref: gate0Result.decision_ref ?? null,
    decision_status: decisionStatus,
    actor_ref: gate0Result.actor_ref ?? null,
    session_ref: gate0Result.session_ref ?? null,
    conversation_ref: gate0Result.conversation_ref ?? null,
    binding_snapshot_ref: gate0Result.binding_snapshot_ref ?? null,
    reason_codes: gate0Result.reason_codes ?? [],
    restriction_codes: gate0Result.restriction_codes ?? [],
    obligation_codes: gate0Result.obligation_codes ?? [],
    expires_at: gate0Result.expires_at ?? null,
    enforced_at: now,
  };
}

function validateAccessContextAlignment({ gate0Result, accessContextEnvelope }) {
  if (!accessContextEnvelope) {
    return { ok: false, reason: 'missing_access_context' };
  }

  validateAccessContextEnvelopeShape(accessContextEnvelope);

  for (const [key, label] of [
    ['actor_ref', 'actor_ref'],
    ['session_ref', 'session_ref'],
    ['conversation_ref', 'conversation_ref'],
  ]) {
    if (gate0Result[key] && accessContextEnvelope[key] && gate0Result[key] !== accessContextEnvelope[key]) {
      return { ok: false, reason: `misaligned_${label}` };
    }
  }

  return { ok: true };
}

export function enforceGate0Result({
  hostIngressEnvelope,
  gate0Result,
  accessContextEnvelope = null,
  now = new Date().toISOString(),
}) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);
  const result = ensureObject('gate0Result', gate0Result);
  const decisionStatus = normalizeDecisionStatus(result);
  const baseResult = buildBaseResult({ hostIngressEnvelope: ingress, gate0Result: result, decisionStatus, now });

  if (!result.decision_ref) {
    return {
      ...baseResult,
      enforcement_status: 'invalid_gate0_result',
      should_handoff_to_runtime: false,
      reason_codes: [...(baseResult.reason_codes ?? []), 'missing_decision_ref'],
    };
  }

  if (decisionStatus === 'deny') {
    return {
      ...baseResult,
      enforcement_status: 'host_rejected',
      should_handoff_to_runtime: false,
    };
  }

  if (decisionStatus === 'escalation') {
    return {
      ...baseResult,
      enforcement_status: 'host_escalation',
      should_handoff_to_runtime: false,
    };
  }

  const accessAlignment = validateAccessContextAlignment({
    gate0Result: result,
    accessContextEnvelope,
  });

  if (!accessAlignment.ok && decisionStatus === 'restricted') {
    return {
      ...baseResult,
      enforcement_status: 'host_scope_confirmation',
      should_handoff_to_runtime: false,
      reason_codes: [...new Set([...(baseResult.reason_codes ?? []), accessAlignment.reason])],
    };
  }

  if (!accessAlignment.ok) {
    return {
      ...baseResult,
      enforcement_status: 'blocked_missing_access_context',
      should_handoff_to_runtime: false,
      reason_codes: [...new Set([...(baseResult.reason_codes ?? []), accessAlignment.reason])],
    };
  }

  return {
    ...baseResult,
    enforcement_status: decisionStatus === 'restricted' ? 'ready_for_runtime_restricted' : 'ready_for_runtime',
    should_handoff_to_runtime: true,
  };
}
