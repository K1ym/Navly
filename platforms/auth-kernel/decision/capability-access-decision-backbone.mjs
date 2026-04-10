import {
  assertCapabilityId,
  buildDecisionRef,
  buildDeterministicId,
  validateAccessDecisionShape,
} from '../contracts/shared-contract-alignment.mjs';
import { applyScopeSelectionToBindingSnapshot } from '../bindings/binding-backbone.mjs';
import { assertCatalogCodes, loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';

function expiresAt(now, minutes = 30) {
  return new Date(Date.parse(now) + minutes * 60 * 1000).toISOString();
}

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter((value) => value != null).map((value) => String(value)))];
}

function collectGrantedCapabilities(roleIds, policyCatalog) {
  const capabilityIds = new Set();
  for (const roleId of roleIds) {
    for (const capabilityId of policyCatalog.grantProfileByRoleId.get(roleId) ?? []) {
      capabilityIds.add(capabilityId);
    }
  }
  return [...capabilityIds];
}

function finalizeAccessDecision(decision, policyCatalog) {
  validateAccessDecisionShape(decision);
  assertCatalogCodes('access.reason_codes', decision.reason_codes ?? [], policyCatalog.decisionReasonCodes);
  assertCatalogCodes('access.restriction_codes', decision.restriction_codes ?? [], policyCatalog.restrictionCodes);
  assertCatalogCodes('access.obligation_codes', decision.obligation_codes ?? [], policyCatalog.obligationCodes);
  return decision;
}

function buildDecisionShape({
  requestId,
  traceRef,
  actorRef,
  sessionRef,
  requestedCapabilityId,
  targetScopeRef,
  decisionStatus,
  reasonCodes,
  restrictionCodes,
  obligationCodes,
  bindingSnapshotRef,
  conversationRef,
  tenantRef,
  gate0DecisionRef,
  grantedCapabilityIds,
  grantedScopeRefs,
  decisionChainStatus,
  now,
}) {
  return {
    decision_ref: buildDecisionRef(
      buildDeterministicId('capability', requestId, traceRef, requestedCapabilityId, targetScopeRef, decisionStatus),
    ),
    request_id: requestId,
    trace_ref: traceRef,
    decision_status: decisionStatus,
    actor_ref: actorRef,
    session_ref: sessionRef,
    target_capability_id: requestedCapabilityId,
    target_scope_ref: targetScopeRef,
    reason_codes: reasonCodes,
    restriction_codes: restrictionCodes,
    obligation_codes: obligationCodes,
    binding_snapshot_ref: bindingSnapshotRef ?? null,
    conversation_ref: conversationRef ?? null,
    tenant_ref: tenantRef ?? null,
    gate0_decision_ref: gate0DecisionRef ?? null,
    granted_capability_ids: [...(grantedCapabilityIds ?? [])],
    granted_scope_refs: [...(grantedScopeRefs ?? [])],
    decision_chain_status: decisionChainStatus ?? 'fail_closed',
    decided_at: now,
    expires_at: expiresAt(now),
  };
}

function buildFailClosedDecision({
  requestId,
  traceRef,
  actorRef,
  sessionRef,
  requestedCapabilityId,
  targetScopeRef,
  reasonCodes,
  bindingSnapshotRef,
  conversationRef,
  tenantRef,
  gate0DecisionRef,
  grantedCapabilityIds,
  grantedScopeRefs,
  decisionChainStatus,
  now,
  policyCatalog,
}) {
  return finalizeAccessDecision(
    buildDecisionShape({
      requestId,
      traceRef,
      actorRef: actorRef ?? 'navly:actor:unknown',
      sessionRef: sessionRef ?? 'navly:session:unknown',
      requestedCapabilityId,
      targetScopeRef: targetScopeRef ?? 'navly:scope:tenant:unknown',
      decisionStatus: 'deny',
      reasonCodes,
      restrictionCodes: [],
      obligationCodes: [],
      bindingSnapshotRef,
      conversationRef,
      tenantRef,
      gate0DecisionRef,
      grantedCapabilityIds,
      grantedScopeRefs,
      decisionChainStatus,
      now,
    }),
    policyCatalog,
  );
}

export function evaluateCapabilityAccess({
  requestId,
  traceRef,
  gate0Result,
  bindingSnapshot,
  requestedCapabilityId,
  requestedScopeRef = null,
  now = new Date().toISOString(),
  policyCatalog = loadPolicyCatalog(),
}) {
  assertCapabilityId(requestedCapabilityId);

  if (!gate0Result?.decision_ref) {
    return {
      access_decision: buildFailClosedDecision({
        requestId,
        traceRef,
        actorRef: bindingSnapshot.actor_ref,
        sessionRef: bindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef: requestedScopeRef,
        reasonCodes: ['missing_decision_ref'],
        bindingSnapshotRef: bindingSnapshot.binding_snapshot_ref,
        conversationRef: bindingSnapshot.conversation_ref,
        tenantRef: bindingSnapshot.tenant_ref,
        grantedCapabilityIds: [],
        grantedScopeRefs: [...(bindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'fail_closed',
        now,
        policyCatalog,
      }),
      effective_binding_snapshot: bindingSnapshot,
      granted_capability_ids: [],
    };
  }

  if (gate0Result.decision_status === 'deny') {
    return {
      access_decision: buildFailClosedDecision({
        requestId,
        traceRef,
        actorRef: bindingSnapshot.actor_ref,
        sessionRef: bindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef: requestedScopeRef ?? bindingSnapshot.primary_scope_ref,
        reasonCodes: [...(gate0Result.reason_codes ?? ['manual_review_needed'])],
        bindingSnapshotRef: bindingSnapshot.binding_snapshot_ref,
        conversationRef: bindingSnapshot.conversation_ref,
        tenantRef: bindingSnapshot.tenant_ref,
        gate0DecisionRef: gate0Result.decision_ref,
        grantedCapabilityIds: [],
        grantedScopeRefs: [...(bindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'gate0_denied',
        now,
        policyCatalog,
      }),
      effective_binding_snapshot: bindingSnapshot,
      granted_capability_ids: [],
    };
  }

  if (gate0Result.decision_status === 'escalation') {
    const escalationDecision = finalizeAccessDecision(
      buildDecisionShape({
        requestId,
        traceRef,
        actorRef: bindingSnapshot.actor_ref,
        sessionRef: bindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef: requestedScopeRef ?? bindingSnapshot.primary_scope_ref ?? 'navly:scope:tenant:unknown',
        decisionStatus: 'escalation',
        reasonCodes: [...(gate0Result.reason_codes ?? ['manual_review_needed'])],
        restrictionCodes: [...(gate0Result.restriction_codes ?? [])],
        obligationCodes: [...(gate0Result.obligation_codes ?? [])],
        bindingSnapshotRef: bindingSnapshot.binding_snapshot_ref,
        conversationRef: bindingSnapshot.conversation_ref,
        tenantRef: bindingSnapshot.tenant_ref,
        gate0DecisionRef: gate0Result.decision_ref,
        grantedCapabilityIds: [],
        grantedScopeRefs: [...(bindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'access_escalated',
        now,
      }),
      policyCatalog,
    );

    return {
      access_decision: escalationDecision,
      effective_binding_snapshot: bindingSnapshot,
      granted_capability_ids: [],
    };
  }

  let effectiveBindingSnapshot = bindingSnapshot;
  if (requestedScopeRef) {
    effectiveBindingSnapshot = applyScopeSelectionToBindingSnapshot({
      bindingSnapshot,
      requestedScopeRef,
      now,
    });
  }

  const grantedCapabilityIds = collectGrantedCapabilities(effectiveBindingSnapshot.role_ids, policyCatalog);
  const targetScopeRef = requestedScopeRef ?? effectiveBindingSnapshot.selected_scope_ref ?? effectiveBindingSnapshot.primary_scope_ref;

  if (!policyCatalog.capabilityById.has(requestedCapabilityId)) {
    return {
      access_decision: buildFailClosedDecision({
        requestId,
        traceRef,
        actorRef: effectiveBindingSnapshot.actor_ref,
        sessionRef: effectiveBindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef,
        reasonCodes: ['capability_not_granted'],
        bindingSnapshotRef: effectiveBindingSnapshot.binding_snapshot_ref,
        conversationRef: effectiveBindingSnapshot.conversation_ref,
        tenantRef: effectiveBindingSnapshot.tenant_ref,
        gate0DecisionRef: gate0Result.decision_ref,
        grantedCapabilityIds,
        grantedScopeRefs: [...(effectiveBindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'access_denied',
        now,
        policyCatalog,
      }),
      effective_binding_snapshot: effectiveBindingSnapshot,
      granted_capability_ids: grantedCapabilityIds,
    };
  }

  if (!targetScopeRef || !effectiveBindingSnapshot.granted_scope_refs.includes(targetScopeRef)) {
    return {
      access_decision: buildFailClosedDecision({
        requestId,
        traceRef,
        actorRef: effectiveBindingSnapshot.actor_ref,
        sessionRef: effectiveBindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef,
        reasonCodes: ['scope_unbound'],
        bindingSnapshotRef: effectiveBindingSnapshot.binding_snapshot_ref,
        conversationRef: effectiveBindingSnapshot.conversation_ref,
        tenantRef: effectiveBindingSnapshot.tenant_ref,
        gate0DecisionRef: gate0Result.decision_ref,
        grantedCapabilityIds,
        grantedScopeRefs: [...(effectiveBindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'access_denied',
        now,
        policyCatalog,
      }),
      effective_binding_snapshot: effectiveBindingSnapshot,
      granted_capability_ids: grantedCapabilityIds,
    };
  }

  if (!grantedCapabilityIds.includes(requestedCapabilityId)) {
    return {
      access_decision: buildFailClosedDecision({
        requestId,
        traceRef,
        actorRef: effectiveBindingSnapshot.actor_ref,
        sessionRef: effectiveBindingSnapshot.session_ref,
        requestedCapabilityId,
        targetScopeRef,
        reasonCodes: ['capability_not_granted'],
        bindingSnapshotRef: effectiveBindingSnapshot.binding_snapshot_ref,
        conversationRef: effectiveBindingSnapshot.conversation_ref,
        tenantRef: effectiveBindingSnapshot.tenant_ref,
        gate0DecisionRef: gate0Result.decision_ref,
        grantedCapabilityIds,
        grantedScopeRefs: [...(effectiveBindingSnapshot.granted_scope_refs ?? [])],
        decisionChainStatus: 'access_denied',
        now,
        policyCatalog,
      }),
      effective_binding_snapshot: effectiveBindingSnapshot,
      granted_capability_ids: grantedCapabilityIds,
    };
  }

  const decision = finalizeAccessDecision(
    buildDecisionShape({
      requestId,
      traceRef,
      actorRef: effectiveBindingSnapshot.actor_ref,
      sessionRef: effectiveBindingSnapshot.session_ref,
      requestedCapabilityId,
      targetScopeRef,
      decisionStatus: 'allow',
      reasonCodes: [],
      restrictionCodes: [],
      obligationCodes: uniqueStrings(['attach_decision_ref', 'emit_audit_event']),
      bindingSnapshotRef: effectiveBindingSnapshot.binding_snapshot_ref,
      conversationRef: effectiveBindingSnapshot.conversation_ref,
      tenantRef: effectiveBindingSnapshot.tenant_ref,
      gate0DecisionRef: gate0Result.decision_ref,
      grantedCapabilityIds,
      grantedScopeRefs: [...(effectiveBindingSnapshot.granted_scope_refs ?? [])],
      decisionChainStatus: 'access_allowed',
      now,
    }),
    policyCatalog,
  );

  return {
    access_decision: decision,
    effective_binding_snapshot: effectiveBindingSnapshot,
    granted_capability_ids: grantedCapabilityIds,
  };
}
