import { normalizeHostEvidence } from '../ingress-evidence/host-evidence-normalizer.mjs';
import { resolveActorFromIngress } from '../actor-registry/actor-resolution-backbone.mjs';
import { buildBindingSnapshot } from '../bindings/binding-backbone.mjs';
import { evaluateGate0 } from '../decision/gate0-backbone.mjs';
import { evaluateCapabilityAccess } from '../decision/capability-access-decision-backbone.mjs';
import { buildAccessContextEnvelope } from './access-context-envelope-backbone.mjs';

export function runMilestoneBAccessChain({ rawIngressEvidence, requestedCapabilityId, requestedScopeRef = null, now = new Date().toISOString() }) {
  const ingressEvidence = normalizeHostEvidence({
    ...rawIngressEvidence,
    requested_capability_id: requestedCapabilityId ?? rawIngressEvidence.requested_capability_id,
  });

  const actorResolutionResult = resolveActorFromIngress({ ingressEvidence });
  const bindingSnapshot = buildBindingSnapshot({
    ingressEvidence,
    actorResolutionResult,
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
  const accessContextEnvelope = buildAccessContextEnvelope({
    requestId: ingressEvidence.request_id,
    traceRef: ingressEvidence.trace_ref,
    accessDecision: capabilityAccess.access_decision,
    bindingSnapshot: capabilityAccess.effective_binding_snapshot,
    now,
  });

  return {
    ingress_evidence: ingressEvidence,
    actor_resolution_result: actorResolutionResult,
    binding_snapshot: capabilityAccess.effective_binding_snapshot,
    gate0_result: gate0Result,
    access_decision: capabilityAccess.access_decision,
    access_context_envelope: accessContextEnvelope,
  };
}
