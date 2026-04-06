import { buildDecisionRef, buildDeterministicId } from '../contracts/shared-contract-alignment.mjs';
import { assertCatalogCodes, loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';

function expiresAt(now, minutes = 30) {
  return new Date(Date.parse(now) + minutes * 60 * 1000).toISOString();
}

function finalizeGate0Result(result, policyCatalog) {
  assertCatalogCodes('gate0.reason_codes', result.reason_codes ?? [], policyCatalog.decisionReasonCodes);
  assertCatalogCodes('gate0.restriction_codes', result.restriction_codes ?? [], policyCatalog.restrictionCodes);
  assertCatalogCodes('gate0.obligation_codes', result.obligation_codes ?? [], policyCatalog.obligationCodes);
  return result;
}

export function evaluateGate0({
  requestId,
  traceRef,
  ingressEvidence,
  actorResolutionResult,
  bindingSnapshot,
  now = new Date().toISOString(),
  policyCatalog = loadPolicyCatalog(),
}) {
  const decisionRef = buildDecisionRef(
    buildDeterministicId(
      'gate0',
      requestId,
      traceRef,
      ingressEvidence.channel_kind,
      ingressEvidence.host_conversation_ref || ingressEvidence.host_session_ref || requestId,
    ),
  );

  const baseResult = {
    decision_ref: decisionRef,
    request_id: requestId,
    trace_ref: traceRef,
    actor_ref: actorResolutionResult.actor_ref ?? null,
    session_ref: bindingSnapshot.session_ref ?? null,
    conversation_ref: bindingSnapshot.conversation_ref,
    binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
    reason_codes: [],
    restriction_codes: [],
    obligation_codes: [],
    issued_at: now,
    expires_at: expiresAt(now),
  };

  if (actorResolutionResult.resolution_status === 'unknown') {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'deny',
        reason_codes: ['actor_unresolved'],
      },
      policyCatalog,
    );
  }

  if (actorResolutionResult.resolution_status === 'ambiguous') {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'deny',
        reason_codes: ['actor_ambiguous'],
      },
      policyCatalog,
    );
  }

  if (actorResolutionResult.resolution_status === 'inactive') {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'deny',
        reason_codes: ['actor_inactive'],
      },
      policyCatalog,
    );
  }

  if (bindingSnapshot.conversation_binding_status === 'pending_scope') {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'restricted',
        reason_codes: ['scope_unbound'],
        restriction_codes: ['conversation_confirmation_required', 'scope_limited'],
        obligation_codes: ['confirm_scope_before_continue', 'attach_decision_ref'],
      },
      policyCatalog,
    );
  }

  if (bindingSnapshot.conversation_binding_status === 'suspended') {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'deny',
        reason_codes: [...(bindingSnapshot.reason_codes ?? ['invalid_scope_selection'])],
      },
      policyCatalog,
    );
  }

  if (!bindingSnapshot.role_ids.length || !bindingSnapshot.granted_scope_refs.length) {
    return finalizeGate0Result(
      {
        ...baseResult,
        decision_status: 'deny',
        reason_codes: ['binding_missing'],
      },
      policyCatalog,
    );
  }

  return finalizeGate0Result(
    {
      ...baseResult,
      decision_status: 'allow',
      obligation_codes: ['attach_decision_ref'],
    },
    policyCatalog,
  );
}
