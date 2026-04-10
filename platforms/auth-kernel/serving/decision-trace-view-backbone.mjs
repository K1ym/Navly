import { assertMatchesSharedPattern, sharedPatterns } from '../contracts/shared-contract-alignment.mjs';
import { assertCatalogCodes, loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter((value) => value != null).map((value) => String(value)))];
}

function assertNonEmptyString(label, value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function deriveDecisionChainStatus(accessDecision, sessionGrantSnapshot, accessContextEnvelope) {
  if (!accessDecision?.decision_ref || !sessionGrantSnapshot?.session_grant_snapshot_ref) {
    return 'fail_closed';
  }

  if (sessionGrantSnapshot.grant_status === 'withheld' && ['allow', 'restricted'].includes(accessDecision.decision_status)) {
    return 'fail_closed';
  }

  if (!accessContextEnvelope && sessionGrantSnapshot.grant_status === 'issued') {
    return 'fail_closed';
  }

  return sessionGrantSnapshot.decision_chain_status ?? accessDecision.decision_chain_status ?? 'fail_closed';
}

export function validateDecisionTraceViewShape(decisionTraceView) {
  if (!decisionTraceView || typeof decisionTraceView !== 'object') {
    throw new Error('decision_trace_view must be an object');
  }

  assertMatchesSharedPattern('trace_ref', decisionTraceView.trace_ref, sharedPatterns.traceRef);
  assertNonEmptyString('request_id', decisionTraceView.request_id);
  assertMatchesSharedPattern('actor_ref', decisionTraceView.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', decisionTraceView.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('conversation_ref', decisionTraceView.conversation_ref, sharedPatterns.conversationRef);
  assertMatchesSharedPattern('tenant_ref', decisionTraceView.tenant_ref, sharedPatterns.tenantRef);

  if (
    typeof decisionTraceView.binding_snapshot_ref !== 'string' ||
    !decisionTraceView.binding_snapshot_ref.startsWith('navly:binding-snapshot:')
  ) {
    throw new Error('binding_snapshot_ref must be a navly:binding-snapshot:* ref');
  }

  if (
    typeof decisionTraceView.session_grant_snapshot_ref !== 'string' ||
    !decisionTraceView.session_grant_snapshot_ref.startsWith('navly:session-grant-snapshot:')
  ) {
    throw new Error('session_grant_snapshot_ref must be a navly:session-grant-snapshot:* ref');
  }

  if (!Array.isArray(decisionTraceView.audit_event_refs) || !Array.isArray(decisionTraceView.timeline)) {
    throw new Error('decision_trace_view audit_event_refs and timeline must be arrays');
  }

  return decisionTraceView;
}

export function buildDecisionTraceView({
  ingressEvidence,
  actorResolutionResult,
  bindingSnapshot,
  gate0Result,
  accessDecision,
  sessionGrantSnapshot,
  accessContextEnvelope,
  auditEventLedger,
  downstreamOutcomeLinkage = null,
  policyCatalog = loadPolicyCatalog(),
}) {
  const reasonCodes = uniqueStrings([
    ...(gate0Result.reason_codes ?? []),
    ...(accessDecision.reason_codes ?? []),
    ...(sessionGrantSnapshot.reason_codes ?? []),
  ]);
  const restrictionCodes = uniqueStrings([
    ...(gate0Result.restriction_codes ?? []),
    ...(accessDecision.restriction_codes ?? []),
    ...(sessionGrantSnapshot.restriction_codes ?? []),
  ]);
  const obligationCodes = uniqueStrings([
    ...(gate0Result.obligation_codes ?? []),
    ...(accessDecision.obligation_codes ?? []),
    ...(sessionGrantSnapshot.obligation_codes ?? []),
  ]);

  assertCatalogCodes('decisionTrace.reason_codes', reasonCodes, policyCatalog.decisionReasonCodes);
  assertCatalogCodes('decisionTrace.restriction_codes', restrictionCodes, policyCatalog.restrictionCodes);
  assertCatalogCodes('decisionTrace.obligation_codes', obligationCodes, policyCatalog.obligationCodes);

  const decisionTraceView = {
    trace_ref: ingressEvidence.trace_ref,
    request_id: ingressEvidence.request_id,
    actor_ref: accessDecision.actor_ref,
    session_ref: accessDecision.session_ref,
    conversation_ref: bindingSnapshot.conversation_ref,
    tenant_ref: sessionGrantSnapshot.tenant_ref,
    binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
    gate0_decision_ref: gate0Result.decision_ref,
    access_decision_ref: accessDecision.decision_ref,
    session_grant_snapshot_ref: sessionGrantSnapshot.session_grant_snapshot_ref,
    actor_resolution_status: actorResolutionResult.resolution_status,
    conversation_binding_status: bindingSnapshot.conversation_binding_status,
    gate0_decision_status: gate0Result.decision_status,
    access_decision_status: accessDecision.decision_status,
    session_grant_status: sessionGrantSnapshot.grant_status,
    access_context_status: accessContextEnvelope ? 'issued' : 'withheld',
    decision_chain_status: deriveDecisionChainStatus(accessDecision, sessionGrantSnapshot, accessContextEnvelope),
    target_capability_id: sessionGrantSnapshot.target_capability_id,
    target_scope_ref: sessionGrantSnapshot.target_scope_ref,
    reason_codes: reasonCodes,
    restriction_codes: restrictionCodes,
    obligation_codes: obligationCodes,
    audit_ledger_ref: auditEventLedger.ledger_ref,
    audit_event_refs: auditEventLedger.events.map((event) => event.audit_event_ref),
    downstream_outcome_status: downstreamOutcomeLinkage?.downstream_result_status ?? 'pending',
    downstream_outcome_ref: downstreamOutcomeLinkage?.outcome_linkage_ref ?? null,
    timeline: auditEventLedger.events.map((event) => ({
      audit_event_ref: event.audit_event_ref,
      event_kind: event.event_kind,
      event_status: event.event_status,
      occurred_at: event.occurred_at,
    })),
  };

  validateDecisionTraceViewShape(decisionTraceView);
  return decisionTraceView;
}
