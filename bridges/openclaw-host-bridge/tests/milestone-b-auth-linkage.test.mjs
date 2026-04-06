import test from 'node:test';
import assert from 'node:assert/strict';

import { runMilestoneBAccessChain } from '../../../platforms/auth-kernel/serving/access-chain-backbone.mjs';
import { normalizeOpenClawHostIngress } from '../ingress/host-ingress-normalizer.mjs';
import { assembleIngressIdentityEnvelope } from '../auth-linkage/ingress-identity-envelope-backbone.mjs';
import { enforceGate0Result } from '../auth-linkage/gate0-enforcement-backbone.mjs';
import { buildAuthorizedSessionLink } from '../auth-linkage/authorized-session-link-backbone.mjs';
import { buildRuntimeRequestEnvelope } from '../runtime-handoff/runtime-request-envelope-backbone.mjs';
import { buildHostDispatchResult } from '../dispatch/host-dispatch-handoff-backbone.mjs';
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
    requested_capability_id: 'navly.store.daily_overview',
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
    selected_capability_id: 'navly.store.daily_overview',
    selected_service_object_id: 'navly.service.store.daily_overview',
    answer_fragments: [
      {
        kind: 'text',
        text: '今日门店概览已生成。',
      },
    ],
    explanation_fragments: [],
    reason_codes: [],
    trace_refs: [traceRef],
    delivery_hints: {
      dispatch_mode: 'direct_reply',
    },
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

  assert.equal(runtimeRequestEnvelope.decision_ref, accessChain.gate0_result.decision_ref);
  assert.equal(runtimeRequestEnvelope.access_context_envelope.decision_ref, accessChain.access_context_envelope.decision_ref);
  assert.equal(runtimeRequestEnvelope.requested_capability_id, 'navly.store.daily_overview');

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope: buildRuntimeResultEnvelope(runtimeRequestEnvelope.request_id, runtimeRequestEnvelope.trace_ref),
  });

  assert.equal(hostDispatchResult.dispatch_status, 'ready_for_runtime_dispatch');
  assert.equal(hostDispatchResult.reply_blocks[0].text, '今日门店概览已生成。');

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
