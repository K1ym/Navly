import {
  assertCapabilityId,
  assertMatchesSharedPattern,
  buildDeterministicId,
  sharedPatterns,
} from '../contracts/shared-contract-alignment.mjs';

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

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter((value) => value != null).map((value) => String(value)))];
}

function resolveEventPayload(downstreamOutcome) {
  if (downstreamOutcome.event_payload && typeof downstreamOutcome.event_payload === 'object') {
    return downstreamOutcome.event_payload;
  }

  if (downstreamOutcome.event && typeof downstreamOutcome.event === 'object') {
    return downstreamOutcome.event;
  }

  return {};
}

export function validateDownstreamOutcomeLinkageShape(downstreamOutcomeLinkage) {
  if (!downstreamOutcomeLinkage || typeof downstreamOutcomeLinkage !== 'object') {
    throw new Error('downstream_outcome_linkage must be an object');
  }

  if (
    typeof downstreamOutcomeLinkage.outcome_linkage_ref !== 'string' ||
    !downstreamOutcomeLinkage.outcome_linkage_ref.startsWith('navly:outcome-linkage:')
  ) {
    throw new Error('outcome_linkage_ref must be a navly:outcome-linkage:* ref');
  }

  assertMatchesSharedPattern('trace_ref', downstreamOutcomeLinkage.trace_ref, sharedPatterns.traceRef);
  assertMatchesSharedPattern('decision_ref', downstreamOutcomeLinkage.decision_ref, sharedPatterns.decisionRef);
  assertMatchesSharedPattern('actor_ref', downstreamOutcomeLinkage.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', downstreamOutcomeLinkage.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('conversation_ref', downstreamOutcomeLinkage.conversation_ref, sharedPatterns.conversationRef);
  assertMatchesSharedPattern('tenant_ref', downstreamOutcomeLinkage.tenant_ref, sharedPatterns.tenantRef);
  assertCapabilityId(downstreamOutcomeLinkage.target_capability_id);
  assertMatchesSharedPattern('target_scope_ref', downstreamOutcomeLinkage.target_scope_ref, sharedPatterns.scopeRef);
  assertNonEmptyString('downstream_system', downstreamOutcomeLinkage.downstream_system);
  assertNonEmptyString('event_kind', downstreamOutcomeLinkage.event_kind);
  assertNonEmptyString('downstream_event_ref', downstreamOutcomeLinkage.downstream_event_ref);
  assertNonEmptyString('downstream_result_status', downstreamOutcomeLinkage.downstream_result_status);
  assertDateTime('occurred_at', downstreamOutcomeLinkage.occurred_at);
  assertDateTime('linked_at', downstreamOutcomeLinkage.linked_at);

  if (
    typeof downstreamOutcomeLinkage.session_grant_snapshot_ref !== 'string' ||
    !downstreamOutcomeLinkage.session_grant_snapshot_ref.startsWith('navly:session-grant-snapshot:')
  ) {
    throw new Error('session_grant_snapshot_ref must be a navly:session-grant-snapshot:* ref');
  }

  if (!Array.isArray(downstreamOutcomeLinkage.downstream_reason_codes)) {
    throw new Error('downstream_reason_codes must be an array');
  }

  return downstreamOutcomeLinkage;
}

export function buildDownstreamOutcomeLinkage({
  downstreamOutcome,
  accessDecision,
  sessionGrantSnapshot,
  now = new Date().toISOString(),
}) {
  if (!downstreamOutcome) {
    return null;
  }

  if (!accessDecision?.decision_ref) {
    throw new Error('downstream outcome linkage requires accessDecision.decision_ref');
  }

  if (!sessionGrantSnapshot?.session_grant_snapshot_ref) {
    throw new Error('downstream outcome linkage requires sessionGrantSnapshot.session_grant_snapshot_ref');
  }

  if (sessionGrantSnapshot.grant_status !== 'issued') {
    throw new Error('downstream outcome linkage requires an issued session grant snapshot');
  }

  const eventPayload = resolveEventPayload(downstreamOutcome);
  const sessionGrantSnapshotRef =
    downstreamOutcome.session_grant_snapshot_ref ??
    downstreamOutcome.session_grant_ref ??
    eventPayload.session_grant_snapshot_ref ??
    eventPayload.session_grant_ref;

  if (!sessionGrantSnapshotRef) {
    throw new Error('downstream outcome linkage requires session_grant_snapshot_ref');
  }

  if (sessionGrantSnapshotRef !== sessionGrantSnapshot.session_grant_snapshot_ref) {
    throw new Error('downstream outcome linkage must point to the current session grant snapshot');
  }

  const requestId = assertNonEmptyString(
    'request_id',
    eventPayload.request_id ?? downstreamOutcome.request_id ?? sessionGrantSnapshot.request_id,
  );
  if (requestId !== sessionGrantSnapshot.request_id) {
    throw new Error('downstream outcome linkage request_id must match the current auth decision chain');
  }

  const traceRef = assertMatchesSharedPattern(
    'trace_ref',
    eventPayload.trace_ref ?? downstreamOutcome.trace_ref ?? accessDecision.trace_ref,
    sharedPatterns.traceRef,
  );
  if (traceRef !== accessDecision.trace_ref) {
    throw new Error('downstream outcome linkage trace_ref must match accessDecision.trace_ref');
  }

  const decisionRef = assertMatchesSharedPattern(
    'decision_ref',
    eventPayload.decision_ref ?? downstreamOutcome.decision_ref ?? accessDecision.decision_ref,
    sharedPatterns.decisionRef,
  );
  if (decisionRef !== accessDecision.decision_ref) {
    throw new Error('downstream outcome linkage decision_ref must match accessDecision.decision_ref');
  }

  const targetCapabilityId =
    eventPayload.selected_capability_id ??
    downstreamOutcome.target_capability_id ??
    sessionGrantSnapshot.target_capability_id;
  assertCapabilityId(targetCapabilityId);
  if (targetCapabilityId !== sessionGrantSnapshot.target_capability_id) {
    throw new Error('downstream outcome linkage capability must match the issued session grant');
  }

  const eventPayloadTargetScopeRef =
    eventPayload.target_scope_ref == null
      ? null
      : assertMatchesSharedPattern('event_payload.target_scope_ref', eventPayload.target_scope_ref, sharedPatterns.scopeRef);
  if (
    eventPayloadTargetScopeRef != null &&
    eventPayloadTargetScopeRef !== sessionGrantSnapshot.target_scope_ref
  ) {
    throw new Error('downstream outcome linkage event_payload.target_scope_ref must match the issued session grant scope');
  }

  const downstreamOutcomeTargetScopeRef =
    downstreamOutcome.target_scope_ref == null
      ? null
      : assertMatchesSharedPattern('target_scope_ref', downstreamOutcome.target_scope_ref, sharedPatterns.scopeRef);
  if (
    eventPayloadTargetScopeRef != null &&
    downstreamOutcomeTargetScopeRef != null &&
    downstreamOutcomeTargetScopeRef !== eventPayloadTargetScopeRef
  ) {
    throw new Error('downstream outcome linkage scope must not drift between event payload and envelope');
  }
  if (
    downstreamOutcomeTargetScopeRef != null &&
    downstreamOutcomeTargetScopeRef !== sessionGrantSnapshot.target_scope_ref
  ) {
    throw new Error('downstream outcome linkage scope must match the issued session grant');
  }
  const targetScopeRef =
    eventPayloadTargetScopeRef ??
    downstreamOutcomeTargetScopeRef ??
    sessionGrantSnapshot.target_scope_ref;

  const downstreamEventRef = assertNonEmptyString(
    'downstream_event_ref',
    eventPayload.event_id ?? downstreamOutcome.event_id ?? downstreamOutcome.external_outcome_ref,
  );
  const downstreamResultStatus = assertNonEmptyString(
    'downstream_result_status',
    eventPayload.result_status ?? downstreamOutcome.result_status,
  );
  const occurredAt = assertDateTime(
    'occurred_at',
    eventPayload.occurred_at ?? downstreamOutcome.occurred_at ?? now,
  );

  const downstreamOutcomeLinkage = {
    outcome_linkage_ref: `navly:outcome-linkage:${buildDeterministicId(
      'outcome',
      sessionGrantSnapshot.session_grant_snapshot_ref,
      downstreamEventRef,
      downstreamResultStatus,
    )}`,
    request_id: requestId,
    trace_ref: traceRef,
    decision_ref: decisionRef,
    session_grant_snapshot_ref: sessionGrantSnapshot.session_grant_snapshot_ref,
    actor_ref: sessionGrantSnapshot.actor_ref,
    session_ref: sessionGrantSnapshot.session_ref,
    conversation_ref: sessionGrantSnapshot.conversation_ref,
    tenant_ref: sessionGrantSnapshot.tenant_ref,
    target_capability_id: targetCapabilityId,
    target_scope_ref: targetScopeRef,
    downstream_system: assertNonEmptyString('downstream_system', downstreamOutcome.downstream_system),
    event_kind: assertNonEmptyString('event_kind', downstreamOutcome.event_kind),
    downstream_event_ref: downstreamEventRef,
    downstream_result_status: downstreamResultStatus,
    downstream_reason_codes: uniqueStrings([
      ...(eventPayload.reason_codes ?? []),
      ...(downstreamOutcome.reason_codes ?? []),
    ]),
    occurred_at: occurredAt,
    linked_at: assertDateTime('linked_at', now),
    extensions: {
      runtime_trace_ref: eventPayload.runtime_trace_ref ?? downstreamOutcome.runtime_trace_ref ?? null,
      selected_service_object_id: eventPayload.selected_service_object_id ?? downstreamOutcome.selected_service_object_id ?? null,
      external_outcome_ref: downstreamOutcome.external_outcome_ref ?? null,
      downstream_extensions: eventPayload.extensions ?? null,
    },
  };

  validateDownstreamOutcomeLinkageShape(downstreamOutcomeLinkage);
  return downstreamOutcomeLinkage;
}
