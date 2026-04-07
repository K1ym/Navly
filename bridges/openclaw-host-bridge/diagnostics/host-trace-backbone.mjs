import { buildHostLocalRef, ensureObject, uniqueStrings } from '../adapters/openclaw/bridge-shared-alignment.mjs';

export function createHostTraceEvent({
  hostIngressEnvelope,
  stage,
  status = 'recorded',
  linkedTraceRefs = [],
  details = {},
  now = new Date().toISOString(),
}) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);

  return {
    object_name: 'host_trace_event',
    object_scope: 'bridge_local',
    event_id: buildHostLocalRef('host-trace-event', ingress.request_id, stage, now),
    request_id: ingress.request_id,
    trace_ref: ingress.trace_ref,
    host_trace_ref: ingress.host_trace_ref,
    stage,
    status,
    linked_trace_refs: uniqueStrings(linkedTraceRefs),
    details,
    occurred_at: now,
  };
}

export function createMilestoneBTraceBundle({
  hostIngressEnvelope,
  ingressIdentityEnvelope,
  gate0Enforcement,
  authorizedSessionLink,
  runtimeRequestEnvelope,
  hostDispatchResult,
  runtimeResultEnvelope = null,
  now = new Date().toISOString(),
}) {
  const events = [
    createHostTraceEvent({
      hostIngressEnvelope,
      stage: 'host_ingress_normalized',
      linkedTraceRefs: [hostIngressEnvelope.trace_ref],
      details: {
        ingress_ref: hostIngressEnvelope.ingress_ref,
        host_event_kind: hostIngressEnvelope.host_event_kind,
      },
      now,
    }),
    createHostTraceEvent({
      hostIngressEnvelope,
      stage: 'ingress_identity_envelope_assembled',
      linkedTraceRefs: [ingressIdentityEnvelope.trace_ref],
      details: {
        ingress_ref: ingressIdentityEnvelope.ingress_ref,
        peer_identity_count: ingressIdentityEnvelope.peer_identity_evidence.length,
      },
      now,
    }),
    createHostTraceEvent({
      hostIngressEnvelope,
      stage: 'gate0_enforced',
      linkedTraceRefs: [hostIngressEnvelope.trace_ref, gate0Enforcement.decision_ref].filter(Boolean),
      details: {
        decision_status: gate0Enforcement.decision_status,
        enforcement_status: gate0Enforcement.enforcement_status,
      },
      now,
    }),
  ];

  if (authorizedSessionLink) {
    events.push(
      createHostTraceEvent({
        hostIngressEnvelope,
        stage: 'authorized_session_link_created',
        linkedTraceRefs: [authorizedSessionLink.trace_ref, authorizedSessionLink.gate0_decision_ref, authorizedSessionLink.access_context_decision_ref].filter(Boolean),
        details: {
          session_ref: authorizedSessionLink.session_ref,
          conversation_ref: authorizedSessionLink.conversation_ref,
        },
        now,
      }),
    );
  }

  if (runtimeRequestEnvelope) {
    events.push(
      createHostTraceEvent({
        hostIngressEnvelope,
        stage: 'runtime_request_envelope_assembled',
        linkedTraceRefs: [runtimeRequestEnvelope.trace_ref, runtimeRequestEnvelope.decision_ref],
        details: {
          requested_capability_id: runtimeRequestEnvelope.requested_capability_id ?? null,
          requested_service_object_id: runtimeRequestEnvelope.requested_service_object_id ?? null,
        },
        now,
      }),
    );
  }

  events.push(
    createHostTraceEvent({
      hostIngressEnvelope,
      stage: 'host_dispatch_handoff_prepared',
      linkedTraceRefs: uniqueStrings([
        ...(hostDispatchResult.trace_refs ?? []),
        runtimeResultEnvelope?.runtime_trace_ref ?? null,
      ]),
      details: {
        dispatch_status: hostDispatchResult.dispatch_status,
        dispatch_mode: hostDispatchResult.dispatch_mode,
      },
      now,
    }),
  );

  return events;
}
