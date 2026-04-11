import {
  buildHostLocalRef,
  ensureObject,
  validateAccessContextEnvelopeShape,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

function resolveLinkageMode(hostIngressEnvelope) {
  if (hostIngressEnvelope.host_event_kind === 'session_resume') {
    return 'session_resume';
  }
  if (hostIngressEnvelope.host_event_kind === 'tool_call') {
    return 'tool_call';
  }
  return 'message_handoff';
}

export function buildAuthorizedSessionLink({
  hostIngressEnvelope,
  gate0Enforcement,
  accessContextEnvelope,
  now = new Date().toISOString(),
}) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);
  const enforcement = ensureObject('gate0Enforcement', gate0Enforcement);

  if (!enforcement.should_handoff_to_runtime) {
    return null;
  }

  validateAccessContextEnvelopeShape(accessContextEnvelope);

  return {
    object_name: 'authorized_session_link',
    object_scope: 'bridge_local',
    link_ref: buildHostLocalRef(
      'authorized-session-link',
      ingress.request_id,
      accessContextEnvelope.session_ref,
      accessContextEnvelope.conversation_ref,
    ),
    request_id: ingress.request_id,
    trace_ref: ingress.trace_ref,
    host_trace_ref: ingress.host_trace_ref,
    host_session_ref: ingress.host_session_ref,
    host_workspace_ref: ingress.host_workspace_ref,
    host_conversation_ref: ingress.host_conversation_ref,
    actor_ref: accessContextEnvelope.actor_ref,
    tenant_ref: accessContextEnvelope.tenant_ref,
    session_ref: accessContextEnvelope.session_ref,
    conversation_ref: accessContextEnvelope.conversation_ref,
    gate0_decision_ref: enforcement.decision_ref,
    access_context_decision_ref: accessContextEnvelope.decision_ref,
    binding_snapshot_ref: enforcement.binding_snapshot_ref ?? accessContextEnvelope.extensions?.binding_snapshot_ref ?? null,
    primary_scope_ref: accessContextEnvelope.primary_scope_ref,
    granted_scope_refs: accessContextEnvelope.granted_scope_refs,
    granted_capability_ids: accessContextEnvelope.granted_capability_ids,
    conversation_binding_status: accessContextEnvelope.extensions?.conversation_binding_status ?? null,
    linkage_mode: resolveLinkageMode(ingress),
    decision_status: enforcement.decision_status,
    restriction_codes: enforcement.restriction_codes,
    obligation_codes: enforcement.obligation_codes,
    linked_at: now,
  };
}
