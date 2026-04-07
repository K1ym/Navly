import {
  assertCapabilityId,
  assertServiceObjectId,
  ensureObject,
  validateAccessContextEnvelopeShape,
  validateRuntimeRequestEnvelopeShape,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

function resolveCanonicalDecisionRef({ gate0Enforcement, authorizedSessionLink, accessContextEnvelope }) {
  if (!gate0Enforcement?.decision_ref) {
    return null;
  }

  if (!accessContextEnvelope?.decision_ref) {
    return null;
  }

  if (
    authorizedSessionLink?.access_context_decision_ref
    && authorizedSessionLink.access_context_decision_ref !== accessContextEnvelope.decision_ref
  ) {
    return null;
  }

  return accessContextEnvelope.decision_ref;
}

export function buildRuntimeRequestEnvelope({
  hostIngressEnvelope,
  gate0Enforcement,
  authorizedSessionLink,
  accessContextEnvelope,
}) {
  if (!gate0Enforcement?.should_handoff_to_runtime) {
    return null;
  }

  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);
  ensureObject('gate0Enforcement', gate0Enforcement);
  ensureObject('authorizedSessionLink', authorizedSessionLink);
  validateAccessContextEnvelopeShape(accessContextEnvelope);

  const canonicalDecisionRef = resolveCanonicalDecisionRef({
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope,
  });
  if (!canonicalDecisionRef) {
    return null;
  }

  if (ingress.requested_capability_id) {
    assertCapabilityId(ingress.requested_capability_id);
  }
  if (ingress.requested_service_object_id) {
    assertServiceObjectId(ingress.requested_service_object_id);
  }

  const runtimeRequestEnvelope = {
    request_id: ingress.request_id,
    ingress_ref: ingress.ingress_ref,
    trace_ref: ingress.trace_ref,
    channel_kind: ingress.channel_kind,
    message_mode: ingress.message_mode,
    user_input_text: ingress.message_text,
    structured_input_slots: ingress.structured_input_slots ?? {},
    response_channel_capabilities: ingress.response_channel_capabilities ?? {},
    access_context_envelope: accessContextEnvelope,
    decision_ref: canonicalDecisionRef,
    delivery_hint: {
      host_delivery_context: ingress.host_delivery_context,
      host_session_ref: authorizedSessionLink.host_session_ref,
      host_conversation_ref: authorizedSessionLink.host_conversation_ref,
      authorized_session_ref: authorizedSessionLink.session_ref,
      authorized_conversation_ref: authorizedSessionLink.conversation_ref,
      gate0_decision_ref: authorizedSessionLink.gate0_decision_ref,
      access_context_decision_ref: authorizedSessionLink.access_context_decision_ref,
    },
  };

  if (ingress.requested_capability_id) {
    runtimeRequestEnvelope.requested_capability_id = ingress.requested_capability_id;
  }
  if (ingress.requested_service_object_id) {
    runtimeRequestEnvelope.requested_service_object_id = ingress.requested_service_object_id;
  }
  if (ingress.target_scope_hint) {
    runtimeRequestEnvelope.target_scope_hint = ingress.target_scope_hint;
  }
  if (ingress.target_business_date_hint) {
    runtimeRequestEnvelope.target_business_date_hint = ingress.target_business_date_hint;
  }

  validateRuntimeRequestEnvelopeShape(runtimeRequestEnvelope);
  return runtimeRequestEnvelope;
}
