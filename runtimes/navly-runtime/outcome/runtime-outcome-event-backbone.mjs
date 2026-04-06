import { createHash } from 'node:crypto';

function buildEventId(requestId, runtimeTraceRef, resultStatus) {
  const digest = createHash('sha256').update(`${requestId}|${runtimeTraceRef}|${resultStatus}`).digest('hex').slice(0, 16);
  return `navly:runtime-outcome:${digest}`;
}

export function buildRuntimeOutcomeEvent({ runtimeIdentity, runtimeResultEnvelope, now = new Date().toISOString() }) {
  return {
    event_id: buildEventId(
      runtimeResultEnvelope.request_id,
      runtimeResultEnvelope.runtime_trace_ref,
      runtimeResultEnvelope.result_status,
    ),
    request_id: runtimeResultEnvelope.request_id,
    trace_ref: runtimeIdentity.trace_ref,
    runtime_trace_ref: runtimeResultEnvelope.runtime_trace_ref,
    decision_ref: runtimeIdentity.decision_ref,
    selected_capability_id: runtimeResultEnvelope.selected_capability_id,
    selected_service_object_id: runtimeResultEnvelope.selected_service_object_id,
    result_status: runtimeResultEnvelope.result_status,
    reason_codes: runtimeResultEnvelope.reason_codes,
    occurred_at: now,
    extensions: {
      route_result_status: runtimeResultEnvelope.result_status,
      trace_refs: runtimeResultEnvelope.trace_refs,
    },
  };
}
