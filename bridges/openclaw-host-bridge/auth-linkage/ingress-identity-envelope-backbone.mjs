import { ensureObject } from '../adapters/openclaw/bridge-shared-alignment.mjs';

export function assembleIngressIdentityEnvelope({ hostIngressEnvelope }) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);

  return {
    request_id: ingress.request_id,
    ingress_ref: ingress.ingress_ref,
    channel_kind: ingress.channel_kind,
    channel_account_ref: ingress.channel_account_ref,
    peer_identity_evidence: ingress.peer_identity_evidence.map(({ alias_namespace, alias_value }) => ({
      alias_namespace,
      alias_value,
    })),
    host_session_ref: ingress.host_session_ref,
    host_workspace_ref: ingress.host_workspace_ref,
    host_conversation_ref: ingress.host_conversation_ref,
    message_mode: ingress.message_mode,
    received_at: ingress.received_at,
    trace_ref: ingress.trace_ref,
    extensions: {
      host_message_ref: ingress.host_message_ref,
      host_event_kind: ingress.host_event_kind,
      host_trace_ref: ingress.host_trace_ref,
      requested_capability_id: ingress.requested_capability_id,
      requested_service_object_id: ingress.requested_service_object_id,
      target_scope_hint: ingress.target_scope_hint,
      target_business_date_hint: ingress.target_business_date_hint,
    },
  };
}
