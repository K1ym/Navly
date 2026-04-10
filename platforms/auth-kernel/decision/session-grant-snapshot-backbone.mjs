import {
  assertCapabilityId,
  assertMatchesSharedPattern,
  buildDeterministicId,
  buildTenantRef,
  ensureArrayOfSharedPattern,
  sharedPatterns,
} from '../contracts/shared-contract-alignment.mjs';
import { assertCatalogCodes, loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';

const grantStatuses = new Set(['issued', 'withheld']);
const decisionChainStatuses = new Set([
  'access_allowed',
  'access_denied',
  'access_restricted',
  'access_escalated',
  'gate0_denied',
  'fail_closed',
]);

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter((value) => value != null).map((value) => String(value)))];
}

function assertSetMember(label, value, allowedValues) {
  if (!allowedValues.has(value)) {
    throw new Error(`${label} must be one of ${[...allowedValues].join(', ')}, received ${value}`);
  }
  return value;
}

function assertCapabilityIds(label, values) {
  if (!Array.isArray(values)) {
    throw new Error(`${label} must be an array`);
  }

  values.forEach((value) => assertCapabilityId(value));
  return values;
}

function buildSessionGrantSnapshotRef(requestId, traceRef, decisionRef, bindingSnapshotRef, decisionStatus) {
  return `navly:session-grant-snapshot:${buildDeterministicId(
    'session-grant',
    requestId,
    traceRef,
    decisionRef,
    bindingSnapshotRef,
    decisionStatus,
  )}`;
}

function deriveDecisionChainStatus(accessDecision, grantStatus) {
  const fallbackStatusByDecision = {
    allow: 'access_allowed',
    deny: 'access_denied',
    restricted: 'access_restricted',
    escalation: 'access_escalated',
  };

  if (grantStatus === 'withheld' && ['allow', 'restricted'].includes(accessDecision.decision_status)) {
    return 'fail_closed';
  }

  return accessDecision.decision_chain_status ?? fallbackStatusByDecision[accessDecision.decision_status] ?? 'fail_closed';
}

export function validateSessionGrantSnapshotShape(sessionGrantSnapshot) {
  if (!sessionGrantSnapshot || typeof sessionGrantSnapshot !== 'object') {
    throw new Error('session_grant_snapshot must be an object');
  }

  if (
    typeof sessionGrantSnapshot.session_grant_snapshot_ref !== 'string' ||
    !sessionGrantSnapshot.session_grant_snapshot_ref.startsWith('navly:session-grant-snapshot:')
  ) {
    throw new Error('session_grant_snapshot_ref must be a navly:session-grant-snapshot:* ref');
  }

  assertSetMember('grant_status', sessionGrantSnapshot.grant_status, grantStatuses);
  assertSetMember('decision_chain_status', sessionGrantSnapshot.decision_chain_status, decisionChainStatuses);
  assertMatchesSharedPattern('trace_ref', sessionGrantSnapshot.trace_ref, sharedPatterns.traceRef);
  assertMatchesSharedPattern('decision_ref', sessionGrantSnapshot.decision_ref, sharedPatterns.decisionRef);
  assertMatchesSharedPattern('actor_ref', sessionGrantSnapshot.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', sessionGrantSnapshot.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('conversation_ref', sessionGrantSnapshot.conversation_ref, sharedPatterns.conversationRef);
  assertMatchesSharedPattern('tenant_ref', sessionGrantSnapshot.tenant_ref, sharedPatterns.tenantRef);
  assertCapabilityId(sessionGrantSnapshot.target_capability_id);
  assertMatchesSharedPattern('target_scope_ref', sessionGrantSnapshot.target_scope_ref, sharedPatterns.scopeRef);
  ensureArrayOfSharedPattern('granted_scope_refs', sessionGrantSnapshot.granted_scope_refs, sharedPatterns.scopeRef);
  assertCapabilityIds('granted_capability_ids', sessionGrantSnapshot.granted_capability_ids);

  if (
    typeof sessionGrantSnapshot.binding_snapshot_ref !== 'string' ||
    !sessionGrantSnapshot.binding_snapshot_ref.startsWith('navly:binding-snapshot:')
  ) {
    throw new Error('binding_snapshot_ref must be a navly:binding-snapshot:* ref');
  }

  return sessionGrantSnapshot;
}

export function buildSessionGrantSnapshot({
  requestId,
  traceRef,
  accessDecision,
  bindingSnapshot,
  grantedCapabilityIds = [],
  now = new Date().toISOString(),
  policyCatalog = loadPolicyCatalog(),
}) {
  if (!accessDecision?.decision_ref) {
    throw new Error('session grant snapshot requires accessDecision.decision_ref');
  }

  if (!bindingSnapshot?.binding_snapshot_ref) {
    throw new Error('session grant snapshot requires bindingSnapshot.binding_snapshot_ref');
  }

  const grantedScopeRefs = [...(bindingSnapshot.granted_scope_refs ?? [])];
  const normalizedGrantedCapabilityIds = uniqueStrings(grantedCapabilityIds);
  const normalizedReasonCodes = uniqueStrings(accessDecision.reason_codes);
  const normalizedRestrictionCodes = uniqueStrings(accessDecision.restriction_codes);
  const normalizedObligationCodes = uniqueStrings(accessDecision.obligation_codes);
  const targetScopeRef =
    accessDecision.target_scope_ref ??
    bindingSnapshot.selected_scope_ref ??
    bindingSnapshot.primary_scope_ref ??
    'navly:scope:tenant:unknown';

  let grantStatus = 'withheld';
  if (
    ['allow', 'restricted'].includes(accessDecision.decision_status) &&
    bindingSnapshot.selected_scope_ref &&
    grantedScopeRefs.includes(targetScopeRef)
  ) {
    grantStatus = 'issued';
  }

  if (grantStatus === 'issued' && !normalizedObligationCodes.includes('emit_audit_event')) {
    normalizedObligationCodes.push('emit_audit_event');
  }

  if (grantStatus === 'withheld' && ['allow', 'restricted'].includes(accessDecision.decision_status)) {
    normalizedReasonCodes.push('scope_unbound');
  }

  const reasonCodes = uniqueStrings(normalizedReasonCodes);
  const restrictionCodes = uniqueStrings(normalizedRestrictionCodes);
  const obligationCodes = uniqueStrings(normalizedObligationCodes);

  assertCatalogCodes('sessionGrant.reason_codes', reasonCodes, policyCatalog.decisionReasonCodes);
  assertCatalogCodes('sessionGrant.restriction_codes', restrictionCodes, policyCatalog.restrictionCodes);
  assertCatalogCodes('sessionGrant.obligation_codes', obligationCodes, policyCatalog.obligationCodes);

  const sessionGrantSnapshot = {
    session_grant_snapshot_ref: buildSessionGrantSnapshotRef(
      requestId,
      traceRef,
      accessDecision.decision_ref,
      bindingSnapshot.binding_snapshot_ref,
      accessDecision.decision_status,
    ),
    request_id: requestId,
    trace_ref: traceRef,
    decision_ref: accessDecision.decision_ref,
    gate0_decision_ref: accessDecision.gate0_decision_ref ?? null,
    binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
    actor_ref: accessDecision.actor_ref,
    session_ref: accessDecision.session_ref,
    conversation_ref: bindingSnapshot.conversation_ref,
    tenant_ref: bindingSnapshot.tenant_ref ?? buildTenantRef('unknown'),
    target_capability_id: accessDecision.target_capability_id,
    target_scope_ref: targetScopeRef,
    granted_scope_refs: grantedScopeRefs,
    granted_capability_ids: normalizedGrantedCapabilityIds,
    grant_status: grantStatus,
    decision_status: accessDecision.decision_status,
    decision_chain_status: deriveDecisionChainStatus(accessDecision, grantStatus),
    reason_codes: reasonCodes,
    restriction_codes: restrictionCodes,
    obligation_codes: obligationCodes,
    issued_at: now,
    expires_at: accessDecision.expires_at,
  };

  validateSessionGrantSnapshotShape(sessionGrantSnapshot);
  return sessionGrantSnapshot;
}
