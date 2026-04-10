import {
  assertCapabilityId,
  assertMatchesSharedPattern,
  buildDeterministicId,
  sharedPatterns,
} from '../contracts/shared-contract-alignment.mjs';
import { assertCatalogCodes, loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';

const auditEventKinds = new Set([
  'actor_resolution',
  'binding_snapshot',
  'gate0_result',
  'access_decision',
  'session_grant_snapshot',
  'access_context_envelope',
  'downstream_outcome_linkage',
]);

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter((value) => value != null).map((value) => String(value)))];
}

function assertNonEmptyString(label, value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function assertDateTime(label, value) {
  const normalized = assertNonEmptyString(label, value);
  if (Number.isNaN(Date.parse(normalized))) {
    throw new Error(`${label} must be a valid date-time string`);
  }
  return normalized;
}

function validateOptionalSharedRef(label, value, pattern) {
  if (value == null) {
    return value;
  }
  return assertMatchesSharedPattern(label, value, pattern);
}

function validateOptionalCapability(value) {
  if (value == null) {
    return value;
  }
  return assertCapabilityId(value);
}

function validateEventShape(event) {
  if (!event || typeof event !== 'object') {
    throw new Error('audit event must be an object');
  }

  if (typeof event.audit_event_ref !== 'string' || !event.audit_event_ref.startsWith('navly:audit-event:')) {
    throw new Error('audit_event_ref must be a navly:audit-event:* ref');
  }

  if (!auditEventKinds.has(event.event_kind)) {
    throw new Error(`unsupported audit event kind ${event.event_kind}`);
  }

  assertNonEmptyString('event_status', event.event_status);
  assertNonEmptyString('request_id', event.request_id);
  assertMatchesSharedPattern('trace_ref', event.trace_ref, sharedPatterns.traceRef);
  validateOptionalSharedRef('actor_ref', event.actor_ref, sharedPatterns.actorRef);
  validateOptionalSharedRef('session_ref', event.session_ref, sharedPatterns.sessionRef);
  validateOptionalSharedRef('conversation_ref', event.conversation_ref, sharedPatterns.conversationRef);
  validateOptionalSharedRef('tenant_ref', event.tenant_ref, sharedPatterns.tenantRef);
  validateOptionalSharedRef('decision_ref', event.decision_ref, sharedPatterns.decisionRef);
  validateOptionalCapability(event.target_capability_id);
  validateOptionalSharedRef('target_scope_ref', event.target_scope_ref, sharedPatterns.scopeRef);
  assertDateTime('occurred_at', event.occurred_at);

  if (event.binding_snapshot_ref != null && !String(event.binding_snapshot_ref).startsWith('navly:binding-snapshot:')) {
    throw new Error('binding_snapshot_ref must be a navly:binding-snapshot:* ref when present');
  }

  if (
    event.session_grant_snapshot_ref != null &&
    !String(event.session_grant_snapshot_ref).startsWith('navly:session-grant-snapshot:')
  ) {
    throw new Error('session_grant_snapshot_ref must be a navly:session-grant-snapshot:* ref when present');
  }

  return event;
}

function buildAuditEvent({
  sequence,
  eventKind,
  eventStatus,
  requestId,
  traceRef,
  actorRef = null,
  sessionRef = null,
  conversationRef = null,
  tenantRef = null,
  bindingSnapshotRef = null,
  decisionRef = null,
  sessionGrantSnapshotRef = null,
  targetCapabilityId = null,
  targetScopeRef = null,
  reasonCodes = [],
  restrictionCodes = [],
  obligationCodes = [],
  occurredAt,
  extensions = {},
  policyCatalog,
}) {
  const normalizedReasonCodes = uniqueStrings(reasonCodes);
  const normalizedRestrictionCodes = uniqueStrings(restrictionCodes);
  const normalizedObligationCodes = uniqueStrings(obligationCodes);

  assertCatalogCodes(`audit.${eventKind}.reason_codes`, normalizedReasonCodes, policyCatalog.decisionReasonCodes);
  assertCatalogCodes(`audit.${eventKind}.restriction_codes`, normalizedRestrictionCodes, policyCatalog.restrictionCodes);
  assertCatalogCodes(`audit.${eventKind}.obligation_codes`, normalizedObligationCodes, policyCatalog.obligationCodes);

  const event = {
    audit_event_ref: `navly:audit-event:${buildDeterministicId(
      'audit',
      requestId,
      traceRef,
      eventKind,
      eventStatus,
      String(sequence),
    )}`,
    event_sequence: sequence,
    event_kind: eventKind,
    event_status: eventStatus,
    request_id: requestId,
    trace_ref: traceRef,
    actor_ref: actorRef,
    session_ref: sessionRef,
    conversation_ref: conversationRef,
    tenant_ref: tenantRef,
    binding_snapshot_ref: bindingSnapshotRef,
    decision_ref: decisionRef,
    session_grant_snapshot_ref: sessionGrantSnapshotRef,
    target_capability_id: targetCapabilityId,
    target_scope_ref: targetScopeRef,
    reason_codes: normalizedReasonCodes,
    restriction_codes: normalizedRestrictionCodes,
    obligation_codes: normalizedObligationCodes,
    occurred_at: occurredAt,
    extensions,
  };

  validateEventShape(event);
  return event;
}

export function validateAuditEventLedgerShape(auditEventLedger) {
  if (!auditEventLedger || typeof auditEventLedger !== 'object') {
    throw new Error('audit_event_ledger must be an object');
  }

  if (typeof auditEventLedger.ledger_ref !== 'string' || !auditEventLedger.ledger_ref.startsWith('navly:audit-ledger:')) {
    throw new Error('ledger_ref must be a navly:audit-ledger:* ref');
  }

  assertNonEmptyString('request_id', auditEventLedger.request_id);
  assertMatchesSharedPattern('trace_ref', auditEventLedger.trace_ref, sharedPatterns.traceRef);
  assertDateTime('created_at', auditEventLedger.created_at);

  if (!Array.isArray(auditEventLedger.events)) {
    throw new Error('audit_event_ledger.events must be an array');
  }

  auditEventLedger.events.forEach(validateEventShape);
  return auditEventLedger;
}

export function buildAuditEventLedger({
  ingressEvidence,
  actorResolutionResult,
  bindingSnapshot,
  gate0Result,
  accessDecision,
  sessionGrantSnapshot,
  accessContextEnvelope,
  downstreamOutcomeLinkage = null,
  now = new Date().toISOString(),
  policyCatalog = loadPolicyCatalog(),
}) {
  const events = [];
  const pushEvent = (event) => {
    events.push(
      buildAuditEvent({
        sequence: events.length + 1,
        requestId: ingressEvidence.request_id,
        traceRef: ingressEvidence.trace_ref,
        conversationRef: bindingSnapshot.conversation_ref,
        tenantRef: bindingSnapshot.tenant_ref,
        bindingSnapshotRef: bindingSnapshot.binding_snapshot_ref,
        sessionRef: accessDecision.session_ref,
        occurredAt: now,
        policyCatalog,
        ...event,
      }),
    );
  };

  pushEvent({
    eventKind: 'actor_resolution',
    eventStatus: actorResolutionResult.resolution_status,
    actorRef: actorResolutionResult.actor_ref ?? null,
    sessionRef: bindingSnapshot.session_ref ?? null,
    reasonCodes: actorResolutionResult.reason_codes ?? [],
    extensions: {
      actor_type: actorResolutionResult.actor_type ?? null,
      lifecycle_state: actorResolutionResult.lifecycle_state ?? null,
      matched_alias_count: Array.isArray(actorResolutionResult.matched_aliases) ? actorResolutionResult.matched_aliases.length : 0,
    },
  });

  pushEvent({
    eventKind: 'binding_snapshot',
    eventStatus: bindingSnapshot.conversation_binding_status,
    actorRef: bindingSnapshot.actor_ref ?? null,
    sessionRef: bindingSnapshot.session_ref ?? null,
    reasonCodes: bindingSnapshot.reason_codes ?? [],
    extensions: {
      role_ids: [...(bindingSnapshot.role_ids ?? [])],
      granted_scope_refs: [...(bindingSnapshot.granted_scope_refs ?? [])],
      selected_scope_ref: bindingSnapshot.selected_scope_ref ?? null,
      primary_scope_ref: bindingSnapshot.primary_scope_ref ?? null,
    },
  });

  pushEvent({
    eventKind: 'gate0_result',
    eventStatus: gate0Result.decision_status,
    actorRef: gate0Result.actor_ref ?? null,
    sessionRef: gate0Result.session_ref ?? null,
    decisionRef: gate0Result.decision_ref,
    reasonCodes: gate0Result.reason_codes ?? [],
    restrictionCodes: gate0Result.restriction_codes ?? [],
    obligationCodes: gate0Result.obligation_codes ?? [],
    occurredAt: gate0Result.issued_at,
  });

  pushEvent({
    eventKind: 'access_decision',
    eventStatus: accessDecision.decision_status,
    actorRef: accessDecision.actor_ref,
    tenantRef: accessDecision.tenant_ref ?? sessionGrantSnapshot.tenant_ref,
    decisionRef: accessDecision.decision_ref,
    targetCapabilityId: accessDecision.target_capability_id,
    targetScopeRef: accessDecision.target_scope_ref,
    reasonCodes: accessDecision.reason_codes ?? [],
    restrictionCodes: accessDecision.restriction_codes ?? [],
    obligationCodes: accessDecision.obligation_codes ?? [],
    occurredAt: accessDecision.decided_at,
    extensions: {
      gate0_decision_ref: accessDecision.gate0_decision_ref ?? null,
      decision_chain_status: accessDecision.decision_chain_status ?? 'fail_closed',
      granted_capability_ids: [...(accessDecision.granted_capability_ids ?? [])],
      granted_scope_refs: [...(accessDecision.granted_scope_refs ?? [])],
    },
  });

  pushEvent({
    eventKind: 'session_grant_snapshot',
    eventStatus: sessionGrantSnapshot.grant_status,
    actorRef: sessionGrantSnapshot.actor_ref,
    tenantRef: sessionGrantSnapshot.tenant_ref,
    decisionRef: sessionGrantSnapshot.decision_ref,
    sessionGrantSnapshotRef: sessionGrantSnapshot.session_grant_snapshot_ref,
    targetCapabilityId: sessionGrantSnapshot.target_capability_id,
    targetScopeRef: sessionGrantSnapshot.target_scope_ref,
    reasonCodes: sessionGrantSnapshot.reason_codes ?? [],
    restrictionCodes: sessionGrantSnapshot.restriction_codes ?? [],
    obligationCodes: sessionGrantSnapshot.obligation_codes ?? [],
    occurredAt: sessionGrantSnapshot.issued_at,
    extensions: {
      decision_status: sessionGrantSnapshot.decision_status,
      decision_chain_status: sessionGrantSnapshot.decision_chain_status,
      granted_capability_ids: [...(sessionGrantSnapshot.granted_capability_ids ?? [])],
      granted_scope_refs: [...(sessionGrantSnapshot.granted_scope_refs ?? [])],
    },
  });

  pushEvent({
    eventKind: 'access_context_envelope',
    eventStatus: accessContextEnvelope ? 'issued' : 'withheld',
    actorRef: sessionGrantSnapshot.actor_ref,
    tenantRef: sessionGrantSnapshot.tenant_ref,
    decisionRef: sessionGrantSnapshot.decision_ref,
    sessionGrantSnapshotRef: sessionGrantSnapshot.session_grant_snapshot_ref,
    targetCapabilityId: sessionGrantSnapshot.target_capability_id,
    targetScopeRef: sessionGrantSnapshot.target_scope_ref,
    reasonCodes: accessContextEnvelope ? [] : sessionGrantSnapshot.reason_codes ?? [],
    restrictionCodes: accessContextEnvelope ? [] : sessionGrantSnapshot.restriction_codes ?? [],
    obligationCodes: sessionGrantSnapshot.obligation_codes ?? [],
    occurredAt: accessContextEnvelope?.issued_at ?? now,
    extensions: {
      expires_at: accessContextEnvelope?.expires_at ?? null,
      decision_chain_status: sessionGrantSnapshot.decision_chain_status,
    },
  });

  if (downstreamOutcomeLinkage) {
    pushEvent({
      eventKind: 'downstream_outcome_linkage',
      eventStatus: downstreamOutcomeLinkage.downstream_result_status,
      actorRef: downstreamOutcomeLinkage.actor_ref,
      tenantRef: downstreamOutcomeLinkage.tenant_ref,
      decisionRef: downstreamOutcomeLinkage.decision_ref,
      sessionGrantSnapshotRef: downstreamOutcomeLinkage.session_grant_snapshot_ref,
      targetCapabilityId: downstreamOutcomeLinkage.target_capability_id,
      targetScopeRef: downstreamOutcomeLinkage.target_scope_ref,
      occurredAt: downstreamOutcomeLinkage.occurred_at,
      extensions: {
        downstream_system: downstreamOutcomeLinkage.downstream_system,
        event_kind: downstreamOutcomeLinkage.event_kind,
        downstream_event_ref: downstreamOutcomeLinkage.downstream_event_ref,
        downstream_reason_codes: [...(downstreamOutcomeLinkage.downstream_reason_codes ?? [])],
      },
    });
  }

  const auditEventLedger = {
    ledger_ref: `navly:audit-ledger:${buildDeterministicId(
      'ledger',
      ingressEvidence.request_id,
      ingressEvidence.trace_ref,
      accessDecision.decision_ref,
      sessionGrantSnapshot.session_grant_snapshot_ref,
      downstreamOutcomeLinkage?.outcome_linkage_ref ?? 'none',
    )}`,
    request_id: ingressEvidence.request_id,
    trace_ref: ingressEvidence.trace_ref,
    created_at: assertDateTime('created_at', now),
    event_count: events.length,
    gate0_decision_ref: gate0Result.decision_ref,
    access_decision_ref: accessDecision.decision_ref,
    binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
    session_grant_snapshot_ref: sessionGrantSnapshot.session_grant_snapshot_ref,
    events,
  };

  validateAuditEventLedgerShape(auditEventLedger);
  return auditEventLedger;
}
