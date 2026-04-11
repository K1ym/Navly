import {
  buildHostLocalRef,
  ensureObject,
  uniqueStrings,
  validateRuntimeResultEnvelopeShape,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

function classifyRuntimeFailureDomain(runtimeResultEnvelope) {
  const reasonCodes = Array.isArray(runtimeResultEnvelope?.reason_codes) ? runtimeResultEnvelope.reason_codes : [];
  if (reasonCodes.some((code) => code.startsWith('runtime.dependency.auth') || code.startsWith('runtime.access'))) {
    return 'auth';
  }
  if (
    reasonCodes.some((code) => code.startsWith('runtime.dependency.readiness'))
    || reasonCodes.some((code) => code.startsWith('runtime.dependency.service'))
    || reasonCodes.some((code) => code.startsWith('runtime.readiness.'))
    || reasonCodes.some((code) => code.startsWith('runtime.service.'))
  ) {
    return 'data';
  }
  if (reasonCodes.some((code) => code.startsWith('runtime.route.'))) {
    return 'runtime';
  }
  if (runtimeResultEnvelope?.result_status === 'rejected' || runtimeResultEnvelope?.result_status === 'escalated') {
    return 'auth';
  }
  if (runtimeResultEnvelope?.result_status === 'runtime_error') {
    return 'runtime';
  }
  return null;
}

function buildGate0ReplyBlocks(gate0Enforcement) {
  switch (gate0Enforcement.enforcement_status) {
    case 'host_escalation':
      return [{
        kind: 'host_escalation',
        reason_codes: gate0Enforcement.reason_codes,
        obligation_codes: gate0Enforcement.obligation_codes,
      }];
    case 'host_scope_confirmation':
      return [{
        kind: 'host_scope_confirmation',
        reason_codes: gate0Enforcement.reason_codes,
        restriction_codes: gate0Enforcement.restriction_codes,
      }];
    default:
      return [{
        kind: 'host_rejection',
        reason_codes: gate0Enforcement.reason_codes,
      }];
  }
}

function buildRuntimeGuardReplyBlocks(reasonCode) {
  return [{
    kind: 'host_runtime_result_rejected',
    reason_codes: [reasonCode],
  }];
}

function buildRuntimeDispatchStatus(runtimeResultEnvelope) {
  switch (runtimeResultEnvelope.result_status) {
    case 'fallback':
      return 'ready_for_runtime_fallback_dispatch';
    case 'escalated':
      return 'ready_for_runtime_escalation_dispatch';
    case 'rejected':
      return 'ready_for_runtime_rejection_dispatch';
    case 'runtime_error':
      return 'ready_for_runtime_error_dispatch';
    default:
      return 'ready_for_runtime_dispatch';
  }
}

function resolveRuntimeResultMismatchReason({
  ingress,
  runtimeRequestEnvelope,
  runtimeResultEnvelope,
}) {
  if (runtimeResultEnvelope.request_id !== ingress.request_id) {
    return 'runtime_request_mismatch';
  }

  if (
    runtimeRequestEnvelope.requested_capability_id
    && runtimeResultEnvelope.selected_capability_id !== runtimeRequestEnvelope.requested_capability_id
  ) {
    return 'runtime_capability_mismatch';
  }

  if (
    runtimeRequestEnvelope.requested_service_object_id
    && runtimeResultEnvelope.selected_service_object_id !== runtimeRequestEnvelope.requested_service_object_id
  ) {
    return 'runtime_service_object_mismatch';
  }

  return null;
}

function buildDispatchMode({ runtimeResultEnvelope, hostIngressEnvelope }) {
  if (hostIngressEnvelope.host_event_kind === 'session_resume') {
    return 'session_resume';
  }
  if (hostIngressEnvelope.host_event_kind === 'tool_call') {
    return 'tool_call';
  }

  return runtimeResultEnvelope?.delivery_hints?.dispatch_mode
    ?? runtimeResultEnvelope?.delivery_hints?.host_delivery_context?.dispatch_mode
    ?? hostIngressEnvelope.host_delivery_context?.dispatch_mode
    ?? 'direct_reply';
}

function buildDispatchFlow(hostIngressEnvelope) {
  if (hostIngressEnvelope.host_event_kind === 'session_resume') {
    return 'session_resume';
  }
  if (hostIngressEnvelope.host_event_kind === 'tool_call') {
    return 'tool_call';
  }
  return hostIngressEnvelope.message_mode;
}

function buildRuntimeReplyBlocks(runtimeResultEnvelope) {
  if (Array.isArray(runtimeResultEnvelope.answer_fragments) && runtimeResultEnvelope.answer_fragments.length > 0) {
    return runtimeResultEnvelope.answer_fragments;
  }
  return runtimeResultEnvelope.explanation_fragments ?? [];
}

function resolveFailureDomain({
  gate0Enforcement,
  dispatchStatus,
  runtimeResultEnvelope,
}) {
  if (dispatchStatus === 'blocked_missing_runtime_request' || dispatchStatus === 'blocked_runtime_result_mismatch') {
    return 'host';
  }
  if (!gate0Enforcement.should_handoff_to_runtime) {
    return 'auth';
  }
  if (!runtimeResultEnvelope) {
    return 'host';
  }
  return classifyRuntimeFailureDomain(runtimeResultEnvelope);
}

export function buildHostDispatchResult({
  hostIngressEnvelope,
  gate0Enforcement,
  authorizedSessionLink = null,
  runtimeRequestEnvelope = null,
  runtimeResultEnvelope = null,
  runtimeOutcomeEvent = null,
  now = new Date().toISOString(),
}) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);
  const enforcement = ensureObject('gate0Enforcement', gate0Enforcement);

  let dispatchStatus = 'ready_for_gate0_rejection';
  let replyBlocks = buildGate0ReplyBlocks(enforcement);
  let traceRefs = uniqueStrings([ingress.trace_ref]);
  let runtimeTraceRef = null;
  let acceptedRuntimeResultEnvelope = null;

  if (runtimeResultEnvelope) {
    validateRuntimeResultEnvelopeShape(runtimeResultEnvelope);

    if (!enforcement.should_handoff_to_runtime) {
      if (enforcement.enforcement_status === 'host_escalation') {
        dispatchStatus = 'ready_for_gate0_escalation';
      } else if (enforcement.enforcement_status === 'host_scope_confirmation') {
        dispatchStatus = 'ready_for_scope_confirmation';
      }
    } else if (!runtimeRequestEnvelope) {
      dispatchStatus = 'blocked_missing_runtime_request';
      replyBlocks = buildRuntimeGuardReplyBlocks('missing_runtime_request');
    } else {
      const runtimeMismatchReason = resolveRuntimeResultMismatchReason({
        ingress,
        runtimeRequestEnvelope,
        runtimeResultEnvelope,
      });

      if (runtimeMismatchReason) {
        dispatchStatus = 'blocked_runtime_result_mismatch';
        replyBlocks = buildRuntimeGuardReplyBlocks(runtimeMismatchReason);
      } else {
        acceptedRuntimeResultEnvelope = runtimeResultEnvelope;
        dispatchStatus = buildRuntimeDispatchStatus(runtimeResultEnvelope);
        runtimeTraceRef = runtimeResultEnvelope.runtime_trace_ref;
        traceRefs = uniqueStrings([
          ...traceRefs,
          runtimeResultEnvelope.runtime_trace_ref,
          ...(runtimeResultEnvelope.trace_refs ?? []),
        ]);
        if (runtimeOutcomeEvent) {
          traceRefs = uniqueStrings([
            ...traceRefs,
            runtimeOutcomeEvent.trace_ref,
            runtimeOutcomeEvent.runtime_trace_ref,
            ...(runtimeOutcomeEvent.trace_refs ?? []),
          ]);
        }
        replyBlocks = buildRuntimeReplyBlocks(runtimeResultEnvelope);
      }
    }
  } else if (enforcement.enforcement_status === 'host_escalation') {
    dispatchStatus = 'ready_for_gate0_escalation';
  } else if (enforcement.enforcement_status === 'host_scope_confirmation') {
    dispatchStatus = 'ready_for_scope_confirmation';
  }

  const failureDomain = resolveFailureDomain({
    gate0Enforcement: enforcement,
    dispatchStatus,
    runtimeResultEnvelope: acceptedRuntimeResultEnvelope,
  });

  return {
    object_name: 'host_dispatch_result',
    object_scope: 'bridge_local',
    dispatch_ref: buildHostLocalRef('dispatch', ingress.request_id, enforcement.decision_ref ?? 'none', dispatchStatus),
    request_id: ingress.request_id,
    trace_ref: ingress.trace_ref,
    host_trace_ref: ingress.host_trace_ref,
    host_session_ref: ingress.host_session_ref,
    host_workspace_ref: ingress.host_workspace_ref,
    host_conversation_ref: ingress.host_conversation_ref,
    decision_ref: enforcement.decision_ref,
    session_ref: authorizedSessionLink?.session_ref ?? null,
    conversation_ref: authorizedSessionLink?.conversation_ref ?? null,
    runtime_trace_ref: acceptedRuntimeResultEnvelope ? runtimeTraceRef : null,
    dispatch_status: dispatchStatus,
    dispatch_mode: buildDispatchMode({ runtimeResultEnvelope: acceptedRuntimeResultEnvelope, hostIngressEnvelope: ingress }),
    dispatch_flow: buildDispatchFlow(ingress),
    failure_domain: failureDomain,
    reply_blocks: replyBlocks,
    delivery_target: runtimeRequestEnvelope?.delivery_hint?.host_delivery_context ?? ingress.host_delivery_context,
    trace_refs: traceRefs,
    outcome_event_refs: runtimeOutcomeEvent
      ? [runtimeOutcomeEvent.event_id]
      : [],
    prepared_at: now,
  };
}
