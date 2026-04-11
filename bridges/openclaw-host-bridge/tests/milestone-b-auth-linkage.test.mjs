import test from 'node:test';
import assert from 'node:assert/strict';

import { runMilestoneBAccessChain } from '../../../platforms/auth-kernel/serving/access-chain-backbone.mjs';
import { normalizeOpenClawHostIngress } from '../ingress/host-ingress-normalizer.mjs';
import { assembleIngressIdentityEnvelope } from '../auth-linkage/ingress-identity-envelope-backbone.mjs';
import { enforceGate0Result } from '../auth-linkage/gate0-enforcement-backbone.mjs';
import { buildAuthorizedSessionLink } from '../auth-linkage/authorized-session-link-backbone.mjs';
import { buildRuntimeRequestEnvelope } from '../runtime-handoff/runtime-request-envelope-backbone.mjs';
import { buildHostDispatchResult } from '../dispatch/host-dispatch-handoff-backbone.mjs';
import { createMilestoneBTraceBundle } from '../diagnostics/host-trace-backbone.mjs';
import { runOpenClawHostMilestoneBBackbone } from '../adapters/openclaw/openclaw-host-handoff-backbone.mjs';

function buildRawHostIngress(overrides = {}) {
  return {
    request_id: 'asp19-request-001',
    channel_kind: 'wecom',
    message_mode: 'direct_message',
    channel_account_ref: 'openclaw-host-bridge:channel-account:wecom-main',
    host_session_ref: 'openclaw:session:main:sample',
    host_workspace_ref: 'openclaw:workspace:main',
    host_conversation_ref: 'openclaw:conversation:direct:sample',
    host_message_ref: 'openclaw:message:001',
    peer_identity_evidence: [
      {
        alias_namespace: 'wecom_user_id',
        alias_value: 'sample_manager_single_scope',
      },
    ],
    message_text: '请给我今天的门店概览',
    requested_capability_id: 'navly.store.member_insight',
    target_business_date_hint: '2026-04-06',
    host_delivery_context: {
      dispatch_mode: 'direct_reply',
      target_ref: 'openclaw:session:main:sample',
    },
    response_channel_capabilities: {
      supports_text_reply: true,
      supports_private_reply: true,
      supports_thread_reply: false,
    },
    ...overrides,
  };
}

function buildRuntimeResultEnvelope(requestId, traceRef) {
  return {
    request_id: requestId,
    runtime_trace_ref: 'navly:runtime-trace:bridge-test-001',
    result_status: 'answered',
    selected_capability_id: 'navly.store.member_insight',
    selected_service_object_id: 'navly.service.store.member_insight',
    answer_fragments: [
      {
        kind: 'text',
        text: '今日门店概览已生成。',
      },
    ],
    explanation_fragments: [],
    reason_codes: [],
    trace_refs: [
      traceRef,
      'navly:state-trace:readiness:member-insight-ready',
      'navly:run-trace:ingestion:member-insight-run',
    ],
    delivery_hints: {
      dispatch_mode: 'direct_reply',
    },
  };
}

function buildRuntimeOutcomeEvent(requestId, traceRef, overrides = {}) {
  return {
    event_id: 'navly:runtime-outcome-event:bridge-test-001',
    request_id: requestId,
    trace_ref: traceRef,
    runtime_trace_ref: 'navly:runtime-trace:bridge-test-001',
    decision_ref: 'navly:decision:capability-allow-001',
    selected_capability_id: 'navly.store.member_insight',
    selected_service_object_id: 'navly.service.store.member_insight',
    result_status: 'answered',
    reason_codes: [],
    trace_refs: [
      traceRef,
      'navly:state-trace:readiness:member-insight-ready',
      'navly:run-trace:ingestion:member-insight-run',
    ],
    occurred_at: '2026-04-06T08:00:00.000Z',
    ...overrides,
  };
}

test('milestone B backbone assembles ingress identity, authorized session link, runtime request, and dispatch result', () => {
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress: buildRawHostIngress() });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(gate0Enforcement.enforcement_status, 'ready_for_runtime');
  assert.equal(gate0Enforcement.should_handoff_to_runtime, true);

  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(authorizedSessionLink.host_session_ref, hostIngressEnvelope.host_session_ref);
  assert.notEqual(authorizedSessionLink.session_ref, authorizedSessionLink.host_session_ref);

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(runtimeRequestEnvelope.decision_ref, accessChain.access_context_envelope.decision_ref);
  assert.equal(runtimeRequestEnvelope.access_context_envelope.decision_ref, accessChain.access_context_envelope.decision_ref);
  assert.equal(runtimeRequestEnvelope.delivery_hint.gate0_decision_ref, accessChain.gate0_result.decision_ref);
  assert.equal(runtimeRequestEnvelope.requested_capability_id, 'navly.store.member_insight');

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope(runtimeRequestEnvelope.request_id, runtimeRequestEnvelope.trace_ref),
  });

  assert.equal(hostDispatchResult.dispatch_status, 'ready_for_runtime_dispatch');
  assert.equal(hostDispatchResult.reply_blocks[0].text, '今日门店概览已生成。');
  assert.deepEqual(hostDispatchResult.trace_refs, [
    hostIngressEnvelope.trace_ref,
    'navly:runtime-trace:bridge-test-001',
    'navly:state-trace:readiness:member-insight-ready',
    'navly:run-trace:ingestion:member-insight-run',
  ]);

  const pipeline = runOpenClawHostMilestoneBBackbone({
    rawHostIngress: buildRawHostIngress(),
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
  });

  assert.ok(pipeline.runtime_request_envelope);
  assert.ok(pipeline.authorized_session_link);
  assert.ok(pipeline.host_trace_events.length >= 5);
});

test('session_resume ingress keeps the authorized session link governed and resume-aware', () => {
  const rawHostIngress = buildRawHostIngress({
    request_id: 'asp39-session-resume-001',
    host_event_kind: 'session_resume',
    requested_capability_id: 'navly.store.daily_overview',
    host_delivery_context: {
      dispatch_mode: 'session_resume',
      target_ref: 'openclaw:session:main:sample',
    },
  });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });
  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(hostIngressEnvelope.host_delivery_context.dispatch_mode, 'session_resume');
  assert.equal(authorizedSessionLink.linkage_mode, 'session_resume');
  assert.equal(authorizedSessionLink.session_ref, accessChain.access_context_envelope.session_ref);
});

test('host dispatch formalizes runtime/data failure attribution and outcome linkage', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp39-runtime-error-001' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });
  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeResultEnvelope = {
    ...buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
    result_status: 'runtime_error',
    answer_fragments: [],
    explanation_fragments: [
      {
        kind: 'runtime_error',
        text: '数据侧 readiness 失败',
      },
    ],
    reason_codes: ['runtime.dependency.readiness_error'],
  };
  const runtimeOutcomeEvent = buildRuntimeOutcomeEvent(
    hostIngressEnvelope.request_id,
    hostIngressEnvelope.trace_ref,
    {
      result_status: 'runtime_error',
      reason_codes: ['runtime.dependency.readiness_error'],
    },
  );

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope,
    runtimeOutcomeEvent,
  });

  assert.equal(hostDispatchResult.dispatch_status, 'ready_for_runtime_error_dispatch');
  assert.equal(hostDispatchResult.failure_domain, 'data');
  assert.ok(hostDispatchResult.outcome_event_refs.includes(runtimeOutcomeEvent.event_id));
  assert.ok(hostDispatchResult.trace_refs.includes(runtimeOutcomeEvent.trace_ref));
});

test('host trace bundle links runtime_outcome_event and shared trace refs end to end', () => {
  const rawHostIngress = buildRawHostIngress({
    request_id: 'asp39-trace-link-001',
    host_event_kind: 'session_resume',
    host_delivery_context: {
      dispatch_mode: 'session_resume',
      target_ref: 'openclaw:session:main:sample',
    },
  });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });
  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeResultEnvelope = buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref);
  const runtimeOutcomeEvent = buildRuntimeOutcomeEvent(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref);
  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope,
    runtimeOutcomeEvent,
  });

  const traceEvents = createMilestoneBTraceBundle({
    hostIngressEnvelope,
    ingressIdentityEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    hostDispatchResult,
    runtimeResultEnvelope,
    runtimeOutcomeEvent,
  });

  assert.ok(traceEvents.some((event) => event.stage === 'session_resume_linked'));
  assert.ok(traceEvents.some((event) => event.stage === 'runtime_outcome_event_linked'));
  assert.equal(
    traceEvents.find((event) => event.stage === 'host_dispatch_handoff_prepared').details.failure_domain,
    null,
  );
});

test('milestone B backbone fail-closes denied gate0 path into host rejection dispatch without runtime request', () => {
  const hostIngressEnvelope = normalizeOpenClawHostIngress({
    rawHostIngress: buildRawHostIngress({
      request_id: 'asp19-request-deny',
      peer_identity_evidence: [{ alias_namespace: 'wecom_user_id', alias_value: 'missing_user' }],
    }),
  });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const pipeline = runOpenClawHostMilestoneBBackbone({
    rawHostIngress: buildRawHostIngress({
      request_id: 'asp19-request-deny',
      peer_identity_evidence: [{ alias_namespace: 'wecom_user_id', alias_value: 'missing_user' }],
    }),
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(pipeline.gate0_enforcement.enforcement_status, 'host_rejected');
  assert.equal(pipeline.runtime_request_envelope, null);
  assert.equal(pipeline.host_dispatch_result.dispatch_status, 'ready_for_gate0_rejection');
  assert.equal(pipeline.host_dispatch_result.reply_blocks[0].kind, 'host_rejection');
});

test('milestone B backbone ignores runtime result when Gate 0 disallows runtime handoff', () => {
  const deniedIngress = buildRawHostIngress({
    request_id: 'asp19-request-deny-runtime',
    peer_identity_evidence: [{ alias_namespace: 'wecom_user_id', alias_value: 'missing_user' }],
  });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress: deniedIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const pipeline = runOpenClawHostMilestoneBBackbone({
    rawHostIngress: deniedIngress,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
  });

  assert.equal(pipeline.gate0_enforcement.enforcement_status, 'host_rejected');
  assert.equal(pipeline.runtime_request_envelope, null);
  assert.equal(pipeline.host_dispatch_result.dispatch_status, 'ready_for_gate0_rejection');
  assert.equal(pipeline.host_dispatch_result.reply_blocks[0].kind, 'host_rejection');
  assert.equal(pipeline.host_dispatch_result.runtime_trace_ref, null);
});

test('milestone B backbone keeps restricted multi-scope gate0 path on host-side scope confirmation', () => {
  const rawIngress = buildRawHostIngress({
    request_id: 'asp19-request-restricted',
    peer_identity_evidence: [{ alias_namespace: 'wecom_user_id', alias_value: 'sample_manager_multi_scope' }],
  });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress: rawIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const pipeline = runOpenClawHostMilestoneBBackbone({
    rawHostIngress: rawIngress,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(pipeline.gate0_enforcement.enforcement_status, 'host_scope_confirmation');
  assert.equal(pipeline.authorized_session_link, null);
  assert.equal(pipeline.runtime_request_envelope, null);
  assert.equal(pipeline.host_dispatch_result.dispatch_status, 'ready_for_scope_confirmation');
});

test('milestone B backbone rejects mismatched runtime result request ids', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp19-request-mismatch' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope('asp19-request-other', hostIngressEnvelope.trace_ref),
  });

  assert.equal(hostDispatchResult.dispatch_status, 'blocked_runtime_result_mismatch');
  assert.equal(hostDispatchResult.reply_blocks[0].kind, 'host_runtime_result_rejected');
  assert.deepEqual(hostDispatchResult.reply_blocks[0].reason_codes, ['runtime_request_mismatch']);
  assert.equal(hostDispatchResult.runtime_trace_ref, null);
  assert.deepEqual(hostDispatchResult.trace_refs, [hostIngressEnvelope.trace_ref]);
});

test('milestone B backbone rejects runtime result capability mismatch', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp24-request-capability-mismatch' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: {
      ...buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
      selected_capability_id: 'navly.store.daily_overview',
    },
  });

  assert.equal(hostDispatchResult.dispatch_status, 'blocked_runtime_result_mismatch');
  assert.equal(hostDispatchResult.reply_blocks[0].kind, 'host_runtime_result_rejected');
  assert.deepEqual(hostDispatchResult.reply_blocks[0].reason_codes, ['runtime_capability_mismatch']);
  assert.equal(hostDispatchResult.runtime_trace_ref, null);
});

test('milestone B backbone rejects runtime result missing selected service object when request pins one', () => {
  const rawHostIngress = buildRawHostIngress({
    request_id: 'asp24-request-service-object-missing',
    requested_service_object_id: 'navly.service.store.member_insight',
  });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: {
      ...buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
      selected_service_object_id: null,
    },
  });

  assert.equal(hostDispatchResult.dispatch_status, 'blocked_runtime_result_mismatch');
  assert.equal(hostDispatchResult.reply_blocks[0].kind, 'host_runtime_result_rejected');
  assert.deepEqual(hostDispatchResult.reply_blocks[0].reason_codes, ['runtime_service_object_mismatch']);
  assert.equal(hostDispatchResult.runtime_trace_ref, null);
});

test('milestone B backbone fail-closes runtime request assembly when bridge-local decision refs are inconsistent', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp25-request-decision-ref-mismatch' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink: {
      ...authorizedSessionLink,
      access_context_decision_ref: 'navly:decision:mismatched-local-ref',
    },
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(runtimeRequestEnvelope, null);

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope(hostIngressEnvelope.request_id, hostIngressEnvelope.trace_ref),
  });

  assert.equal(hostDispatchResult.dispatch_status, 'blocked_missing_runtime_request');
  assert.equal(hostDispatchResult.reply_blocks[0].kind, 'host_runtime_result_rejected');
  assert.deepEqual(hostDispatchResult.reply_blocks[0].reason_codes, ['missing_runtime_request']);
});

test('milestone B backbone fail-closes runtime request assembly when bridge-local access-context decision ref is missing', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp25-request-decision-ref-missing' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink: {
      ...authorizedSessionLink,
      access_context_decision_ref: null,
    },
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(runtimeRequestEnvelope, null);
});

test('milestone B backbone fail-closes runtime request assembly when bridge-local gate0 decision ref is inconsistent', () => {
  const rawHostIngress = buildRawHostIngress({ request_id: 'asp25-request-gate0-decision-ref-mismatch' });
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const accessChain = runMilestoneBAccessChain({
    rawIngressEvidence: ingressIdentityEnvelope,
    requestedCapabilityId: hostIngressEnvelope.requested_capability_id,
  });

  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: accessChain.gate0_result,
    accessContextEnvelope: accessChain.access_context_envelope,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink: {
      ...authorizedSessionLink,
      gate0_decision_ref: 'navly:decision:mismatched-gate0-ref',
    },
    accessContextEnvelope: accessChain.access_context_envelope,
  });

  assert.equal(runtimeRequestEnvelope, null);
});
