import test from 'node:test';
import assert from 'node:assert/strict';
import { runAuthKernelAccessChain } from '../serving/access-chain-backbone.mjs';
import { buildDownstreamOutcomeLinkage } from '../governance/downstream-outcome-linkage-backbone.mjs';

function sampleBaseIngress(peerAliasValue, extras = {}) {
  return {
    request_id: `req-${peerAliasValue}`,
    trace_ref: `navly:trace:${peerAliasValue}`,
    channel_kind: 'wecom',
    message_mode: 'direct_message',
    host_session_ref: `host-session-${peerAliasValue}`,
    host_workspace_ref: `host-workspace-${peerAliasValue}`,
    host_conversation_ref: `host-conversation-${peerAliasValue}`,
    peer_identity_evidence: [
      {
        alias_namespace: 'wecom_user_id',
        alias_value: peerAliasValue,
      },
    ],
    ...extras,
  };
}

function sampleRuntimeOutcome({ requestId, traceRef, decisionRef, capabilityId, sessionGrantSnapshotRef }) {
  return {
    downstream_system: 'runtime',
    event_kind: 'runtime_outcome_event',
    session_grant_snapshot_ref: sessionGrantSnapshotRef,
    event_payload: {
      event_id: `runtime-outcome-${requestId}`,
      request_id: requestId,
      trace_ref: traceRef,
      runtime_trace_ref: `navly:runtime-trace:${requestId}`,
      decision_ref: decisionRef,
      selected_capability_id: capabilityId,
      result_status: 'answered',
      occurred_at: '2026-04-10T10:00:00.000Z',
      extensions: {
        route_result_status: 'answered',
      },
    },
  };
}

test('allow path issues session grant, envelope, audit ledger, and trace view', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.finance_summary',
    now: '2026-04-10T09:00:00.000Z',
  });

  assert.equal(result.session_grant_snapshot.grant_status, 'issued');
  assert.equal(result.session_grant_snapshot.decision_chain_status, 'access_allowed');
  assert.deepEqual(result.access_decision.obligation_codes, ['attach_decision_ref', 'emit_audit_event']);
  assert.equal(
    result.access_context_envelope.extensions.session_grant_snapshot_ref,
    result.session_grant_snapshot.session_grant_snapshot_ref,
  );
  assert.equal(result.audit_event_ledger.event_count, 6);
  assert.equal(result.audit_event_ledger.events.at(-1).event_kind, 'access_context_envelope');
  assert.equal(result.audit_event_ledger.events.at(-1).event_status, 'issued');
  assert.equal(result.decision_trace_view.decision_chain_status, 'access_allowed');
  assert.equal(result.decision_trace_view.downstream_outcome_status, 'pending');
});

test('gate0 deny withholds session grant and keeps trace machine-readable', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('unknown_alias_value'),
    requestedCapabilityId: 'navly.store.daily_overview',
    now: '2026-04-10T09:05:00.000Z',
  });

  assert.equal(result.access_decision.decision_chain_status, 'gate0_denied');
  assert.equal(result.session_grant_snapshot.grant_status, 'withheld');
  assert.equal(result.session_grant_snapshot.decision_chain_status, 'gate0_denied');
  assert.equal(result.access_context_envelope, null);
  assert.equal(result.audit_event_ledger.event_count, 6);
  assert.equal(result.audit_event_ledger.events.at(-1).event_kind, 'access_context_envelope');
  assert.equal(result.audit_event_ledger.events.at(-1).event_status, 'withheld');
  assert.equal(result.decision_trace_view.decision_chain_status, 'gate0_denied');
});

test('downstream runtime outcome links back into governance chain when refs match', () => {
  const baseResult = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    now: '2026-04-10T09:10:00.000Z',
  });

  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    downstreamOutcome: sampleRuntimeOutcome({
      requestId: baseResult.ingress_evidence.request_id,
      traceRef: baseResult.ingress_evidence.trace_ref,
      decisionRef: baseResult.access_decision.decision_ref,
      capabilityId: baseResult.session_grant_snapshot.target_capability_id,
      sessionGrantSnapshotRef: baseResult.session_grant_snapshot.session_grant_snapshot_ref,
    }),
    now: '2026-04-10T09:10:00.000Z',
  });

  assert.ok(result.downstream_outcome_linkage);
  assert.equal(result.downstream_outcome_linkage.downstream_system, 'runtime');
  assert.equal(result.downstream_outcome_linkage.downstream_result_status, 'answered');
  assert.equal(result.audit_event_ledger.event_count, 7);
  assert.equal(result.audit_event_ledger.events.at(-1).event_kind, 'downstream_outcome_linkage');
  assert.equal(result.decision_trace_view.downstream_outcome_status, 'answered');
});

test('downstream outcome linkage fails closed when session grant ref is missing', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    now: '2026-04-10T09:15:00.000Z',
  });

  assert.throws(
    () =>
      buildDownstreamOutcomeLinkage({
        downstreamOutcome: {
          downstream_system: 'runtime',
          event_kind: 'runtime_outcome_event',
          event_payload: {
            event_id: 'runtime-outcome-missing-grant',
            request_id: result.ingress_evidence.request_id,
            trace_ref: result.ingress_evidence.trace_ref,
            runtime_trace_ref: `navly:runtime-trace:${result.ingress_evidence.request_id}`,
            decision_ref: result.access_decision.decision_ref,
            selected_capability_id: result.session_grant_snapshot.target_capability_id,
            result_status: 'answered',
            occurred_at: '2026-04-10T10:15:00.000Z',
          },
        },
        accessDecision: result.access_decision,
        sessionGrantSnapshot: result.session_grant_snapshot,
        now: '2026-04-10T10:15:00.000Z',
      }),
    /session_grant_snapshot_ref/,
  );
});

test('downstream outcome linkage fails closed when capability drifts from issued grant', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    now: '2026-04-10T09:20:00.000Z',
  });

  assert.throws(
    () =>
      buildDownstreamOutcomeLinkage({
        downstreamOutcome: sampleRuntimeOutcome({
          requestId: result.ingress_evidence.request_id,
          traceRef: result.ingress_evidence.trace_ref,
          decisionRef: result.access_decision.decision_ref,
          capabilityId: 'navly.store.finance_summary',
          sessionGrantSnapshotRef: result.session_grant_snapshot.session_grant_snapshot_ref,
        }),
        accessDecision: result.access_decision,
        sessionGrantSnapshot: result.session_grant_snapshot,
        now: '2026-04-10T10:20:00.000Z',
      }),
    /capability must match the issued session grant/,
  );
});
