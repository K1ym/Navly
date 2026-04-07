import {
  assertCapabilityId,
  assertDecisionRef,
  assertEnum,
  assertPattern,
  assertScopeRef,
  assertServiceObjectId,
  assertTraceRef,
  buildRuntimeTraceRef,
  sharedEnums,
  todayIsoDate,
  validateAccessContextEnvelopeShape,
  sharedPatterns,
} from '../contracts/shared-contract-alignment.mjs';

function assertRequiredField(envelope, fieldName) {
  if (envelope[fieldName] === undefined || envelope[fieldName] === null || envelope[fieldName] === '') {
    throw new Error(`runtime_request_envelope missing required field: ${fieldName}`);
  }
}

function isIsoDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function normalizeFreshnessMode(slots) {
  const candidate = slots?.freshness_mode;
  if (!candidate) {
    return 'latest_usable';
  }
  return assertEnum('freshness_mode', candidate, sharedEnums.freshnessMode);
}

export function buildRuntimeInteractionContext({ runtimeRequestEnvelope, now = new Date().toISOString() }) {
  if (!runtimeRequestEnvelope || typeof runtimeRequestEnvelope !== 'object') {
    throw new Error('runtime_request_envelope must be an object');
  }

  const requiredFields = [
    'request_id',
    'ingress_ref',
    'trace_ref',
    'channel_kind',
    'message_mode',
    'user_input_text',
    'response_channel_capabilities',
    'access_context_envelope',
    'decision_ref',
  ];

  for (const fieldName of requiredFields) {
    assertRequiredField(runtimeRequestEnvelope, fieldName);
  }

  const accessContextEnvelope = validateAccessContextEnvelopeShape(runtimeRequestEnvelope.access_context_envelope);

  assertTraceRef(runtimeRequestEnvelope.trace_ref);
  assertDecisionRef(runtimeRequestEnvelope.decision_ref);

  if (runtimeRequestEnvelope.decision_ref !== accessContextEnvelope.decision_ref) {
    throw new Error('runtime_request_envelope.decision_ref does not match access_context_envelope.decision_ref');
  }

  if (runtimeRequestEnvelope.requested_capability_id) {
    assertCapabilityId(runtimeRequestEnvelope.requested_capability_id);
  }

  if (runtimeRequestEnvelope.requested_service_object_id) {
    assertServiceObjectId(runtimeRequestEnvelope.requested_service_object_id);
  }

  if (runtimeRequestEnvelope.target_scope_hint) {
    assertScopeRef(runtimeRequestEnvelope.target_scope_hint);
  }

  if (runtimeRequestEnvelope.target_business_date_hint && !isIsoDate(runtimeRequestEnvelope.target_business_date_hint)) {
    throw new Error('target_business_date_hint must use ISO date format YYYY-MM-DD');
  }

  const structuredInputSlots = runtimeRequestEnvelope.structured_input_slots ?? {};
  const freshnessMode = normalizeFreshnessMode(structuredInputSlots);

  const targetBusinessDateHint = runtimeRequestEnvelope.target_business_date_hint
    ?? (isIsoDate(structuredInputSlots.target_business_date) ? structuredInputSlots.target_business_date : null)
    ?? todayIsoDate(now);

  const targetScopeHint = runtimeRequestEnvelope.target_scope_hint
    ?? (typeof structuredInputSlots.target_scope_ref === 'string' ? structuredInputSlots.target_scope_ref : null)
    ?? accessContextEnvelope.primary_scope_ref;

  if (targetScopeHint) {
    assertPattern('target_scope_hint', targetScopeHint, sharedPatterns.scopeRef);
  }

  return {
    request_id: runtimeRequestEnvelope.request_id,
    ingress_ref: runtimeRequestEnvelope.ingress_ref,
    trace_ref: runtimeRequestEnvelope.trace_ref,
    runtime_trace_ref: buildRuntimeTraceRef(runtimeRequestEnvelope.request_id, runtimeRequestEnvelope.trace_ref),
    channel_kind: runtimeRequestEnvelope.channel_kind,
    message_mode: runtimeRequestEnvelope.message_mode,
    user_input_text: runtimeRequestEnvelope.user_input_text,
    structured_input_slots: structuredInputSlots,
    requested_capability_id: runtimeRequestEnvelope.requested_capability_id ?? null,
    requested_service_object_id: runtimeRequestEnvelope.requested_service_object_id ?? null,
    target_scope_hint: targetScopeHint,
    target_business_date_hint: targetBusinessDateHint,
    freshness_mode: freshnessMode,
    response_channel_capabilities: runtimeRequestEnvelope.response_channel_capabilities,
    access_context_envelope: accessContextEnvelope,
    decision_ref: runtimeRequestEnvelope.decision_ref,
    delivery_hint: runtimeRequestEnvelope.delivery_hint ?? {},
    received_at: now,
  };
}
