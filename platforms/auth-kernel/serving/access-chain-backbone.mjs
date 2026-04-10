import { normalizeHostEvidence } from '../ingress-evidence/host-evidence-normalizer.mjs';
import { resolveActorFromIngress } from '../actor-registry/actor-resolution-backbone.mjs';
import { buildBindingSnapshot } from '../bindings/binding-backbone.mjs';
import { evaluateGate0 } from '../decision/gate0-backbone.mjs';
import { evaluateCapabilityAccess } from '../decision/capability-access-decision-backbone.mjs';
import { buildSessionGrantSnapshot } from '../decision/session-grant-snapshot-backbone.mjs';
import { buildAuditEventLedger } from '../governance/audit-event-ledger-backbone.mjs';
import { buildDownstreamOutcomeLinkage } from '../governance/downstream-outcome-linkage-backbone.mjs';
import { buildAccessContextEnvelope } from './access-context-envelope-backbone.mjs';
import { buildDecisionTraceView } from './decision-trace-view-backbone.mjs';

export function runAuthKernelAccessChain({
  rawIngressEvidence,
  requestedCapabilityId,
  requestedScopeRef = null,
  bindingBackbone = undefined,
  downstreamOutcome = null,
  now = new Date().toISOString(),
}) {
  const ingressEvidence = normalizeHostEvidence({
    ...rawIngressEvidence,
    requested_capability_id: requestedCapabilityId ?? rawIngressEvidence.requested_capability_id,
  });

  const actorResolutionResult = resolveActorFromIngress({ ingressEvidence });
  const bindingSnapshot = buildBindingSnapshot({
    ingressEvidence,
    actorResolutionResult,
    bindingBackbone: bindingBackbone ?? undefined,
    selectedScopeHint: rawIngressEvidence.target_scope_hint ?? requestedScopeRef,
    now,
  });
  const gate0Result = evaluateGate0({
    requestId: ingressEvidence.request_id,
    traceRef: ingressEvidence.trace_ref,
    ingressEvidence,
    actorResolutionResult,
    bindingSnapshot,
    now,
  });
  const capabilityAccess = evaluateCapabilityAccess({
    requestId: ingressEvidence.request_id,
    traceRef: ingressEvidence.trace_ref,
    gate0Result,
    bindingSnapshot,
    requestedCapabilityId: requestedCapabilityId ?? ingressEvidence.requested_capability_id,
    requestedScopeRef,
    now,
  });
  const sessionGrantSnapshot = buildSessionGrantSnapshot({
    requestId: ingressEvidence.request_id,
    traceRef: ingressEvidence.trace_ref,
    accessDecision: capabilityAccess.access_decision,
    bindingSnapshot: capabilityAccess.effective_binding_snapshot,
    grantedCapabilityIds: capabilityAccess.granted_capability_ids,
    now,
  });
  const accessContextEnvelope = buildAccessContextEnvelope({
    requestId: ingressEvidence.request_id,
    traceRef: ingressEvidence.trace_ref,
    accessDecision: capabilityAccess.access_decision,
    bindingSnapshot: capabilityAccess.effective_binding_snapshot,
    sessionGrantSnapshot,
    now,
  });
  const downstreamOutcomeLinkage = buildDownstreamOutcomeLinkage({
    downstreamOutcome,
    accessDecision: capabilityAccess.access_decision,
    sessionGrantSnapshot,
    now,
  });
  const auditEventLedger = buildAuditEventLedger({
    ingressEvidence,
    actorResolutionResult,
    bindingSnapshot: capabilityAccess.effective_binding_snapshot,
    gate0Result,
    accessDecision: capabilityAccess.access_decision,
    sessionGrantSnapshot,
    accessContextEnvelope,
    downstreamOutcomeLinkage,
    now,
  });
  const decisionTraceView = buildDecisionTraceView({
    ingressEvidence,
    actorResolutionResult,
    bindingSnapshot: capabilityAccess.effective_binding_snapshot,
    gate0Result,
    accessDecision: capabilityAccess.access_decision,
    sessionGrantSnapshot,
    accessContextEnvelope,
    auditEventLedger,
    downstreamOutcomeLinkage,
    now,
  });

  return {
    ingress_evidence: ingressEvidence,
    actor_resolution_result: actorResolutionResult,
    binding_snapshot: capabilityAccess.effective_binding_snapshot,
    gate0_result: gate0Result,
    access_decision: capabilityAccess.access_decision,
    session_grant_snapshot: sessionGrantSnapshot,
    access_context_envelope: accessContextEnvelope,
    downstream_outcome_linkage: downstreamOutcomeLinkage,
    audit_event_ledger: auditEventLedger,
    decision_trace_view: decisionTraceView,
  };
}

/**
 * @deprecated Use runAuthKernelAccessChain. This alias remains temporarily for
 * runtime/bridge callers that have not yet migrated.
 */
export function runMilestoneBAccessChain(options) {
  return runAuthKernelAccessChain(options);
}
