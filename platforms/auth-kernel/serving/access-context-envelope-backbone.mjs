import { validateAccessContextEnvelopeShape } from '../contracts/shared-contract-alignment.mjs';

function expiresAt(now, minutes = 30) {
  return new Date(Date.parse(now) + minutes * 60 * 1000).toISOString();
}

export function buildAccessContextEnvelope({
  requestId,
  traceRef,
  accessDecision,
  bindingSnapshot,
  sessionGrantSnapshot,
  now = new Date().toISOString(),
}) {
  if (!accessDecision?.decision_ref) {
    return null;
  }

  if (!sessionGrantSnapshot?.session_grant_snapshot_ref) {
    return null;
  }

  if (sessionGrantSnapshot.decision_ref !== accessDecision.decision_ref) {
    return null;
  }

  if (sessionGrantSnapshot.grant_status !== 'issued') {
    return null;
  }

  if (!['allow', 'restricted'].includes(accessDecision.decision_status)) {
    return null;
  }

  if (!bindingSnapshot.selected_scope_ref) {
    return null;
  }

  const accessContextEnvelope = {
    request_id: requestId,
    trace_ref: traceRef,
    decision_ref: accessDecision.decision_ref,
    actor_ref: bindingSnapshot.actor_ref,
    session_ref: bindingSnapshot.session_ref,
    conversation_ref: bindingSnapshot.conversation_ref,
    tenant_ref: bindingSnapshot.tenant_ref,
    primary_scope_ref: bindingSnapshot.selected_scope_ref,
    granted_scope_refs: sessionGrantSnapshot.granted_scope_refs,
    granted_capability_ids: sessionGrantSnapshot.granted_capability_ids,
    issued_at: now,
    expires_at: expiresAt(now),
    extensions: {
      binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
      session_grant_snapshot_ref: sessionGrantSnapshot.session_grant_snapshot_ref,
      conversation_binding_status: bindingSnapshot.conversation_binding_status,
      decision_chain_status: sessionGrantSnapshot.decision_chain_status,
    },
  };

  validateAccessContextEnvelopeShape(accessContextEnvelope);
  return accessContextEnvelope;
}
