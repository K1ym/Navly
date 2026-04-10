import test from 'node:test';
import assert from 'node:assert/strict';
import { runAuthKernelAccessChain } from '../serving/access-chain-backbone.mjs';
import {
  applyScopeSelectionToBindingSnapshot,
  buildBindingSnapshot,
  loadBindingBackbone,
} from '../bindings/binding-backbone.mjs';
import { evaluateCapabilityAccess } from '../decision/capability-access-decision-backbone.mjs';

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

test('single-scope manager closes actor -> binding -> Gate 0 -> access -> envelope', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.finance_summary',
  });

  assert.equal(result.actor_resolution_result.resolution_status, 'resolved');
  assert.equal(result.binding_snapshot.conversation_binding_status, 'bound');
  assert.equal(result.gate0_result.decision_status, 'allow');
  assert.equal(result.access_decision.decision_status, 'allow');
  assert.ok(result.access_context_envelope);
  assert.equal(result.access_context_envelope.primary_scope_ref, 'navly:scope:store:sample-store-001');
});

test('multi-scope manager without scope selection stays restricted at Gate 0 and does not issue envelope', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_multi_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
  });

  assert.equal(result.binding_snapshot.conversation_binding_status, 'pending_scope');
  assert.equal(result.gate0_result.decision_status, 'restricted');
  assert.deepEqual(result.gate0_result.obligation_codes, ['confirm_scope_before_continue', 'attach_decision_ref']);
  assert.equal(result.access_decision.decision_status, 'deny');
  assert.deepEqual(result.access_decision.reason_codes, ['scope_unbound']);
  assert.equal(result.access_context_envelope, null);
});

test('multi-scope manager can close capability access after explicit in-scope selection', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_multi_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    requestedScopeRef: 'navly:scope:store:sample-store-002',
  });

  assert.equal(result.binding_snapshot.selected_scope_ref, 'navly:scope:store:sample-store-002');
  assert.equal(result.binding_snapshot.conversation_binding_status, 'bound');
  assert.equal(result.gate0_result.decision_status, 'allow');
  assert.equal(result.access_decision.decision_status, 'allow');
  assert.ok(result.access_context_envelope);
  assert.equal(result.access_context_envelope.primary_scope_ref, 'navly:scope:store:sample-store-002');
});

test('inactive actor is denied at Gate 0', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_inactive_staff'),
    requestedCapabilityId: 'navly.store.daily_overview',
  });

  assert.equal(result.actor_resolution_result.resolution_status, 'inactive');
  assert.equal(result.gate0_result.decision_status, 'deny');
  assert.deepEqual(result.gate0_result.reason_codes, ['actor_inactive']);
});

test('unknown actor is denied at Gate 0 and cannot produce envelope', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('unknown_alias_value'),
    requestedCapabilityId: 'navly.store.daily_overview',
  });

  assert.equal(result.actor_resolution_result.resolution_status, 'unknown');
  assert.equal(result.gate0_result.decision_status, 'deny');
  assert.deepEqual(result.access_decision.reason_codes, ['actor_unresolved']);
  assert.equal(result.access_context_envelope, null);
});

test('Gate 0 deny cannot be reopened by capability stage even when requestedScopeRef becomes valid later', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_multi_scope', {
      target_scope_hint: 'navly:scope:store:not-granted',
    }),
    requestedCapabilityId: 'navly.store.daily_overview',
    requestedScopeRef: 'navly:scope:store:sample-store-002',
  });

  assert.equal(result.gate0_result.decision_status, 'deny');
  assert.deepEqual(result.gate0_result.reason_codes, ['invalid_scope_selection']);
  assert.equal(result.access_decision.decision_status, 'deny');
  assert.deepEqual(result.access_decision.reason_codes, ['invalid_scope_selection']);
  assert.equal(result.access_context_envelope, null);
});

test('capability access fails closed without decision_ref', () => {
  const result = evaluateCapabilityAccess({
    requestId: 'req-fail-closed',
    traceRef: 'navly:trace:req-fail-closed',
    gate0Result: null,
    bindingSnapshot: {
      actor_ref: 'navly:actor:sample-store-manager-single',
      session_ref: 'navly:session:sample-session',
      role_ids: ['navly.role.store_manager'],
      granted_scope_refs: ['navly:scope:store:sample-store-001'],
      selected_scope_ref: 'navly:scope:store:sample-store-001',
      primary_scope_ref: 'navly:scope:store:sample-store-001',
      conversation_ref: 'navly:conversation:sample',
      tenant_ref: 'navly:tenant:sample-retail',
      binding_snapshot_ref: 'navly:binding-snapshot:sample',
      conversation_binding_status: 'bound',
    },
    requestedCapabilityId: 'navly.store.daily_overview',
    requestedScopeRef: 'navly:scope:store:sample-store-001',
  });

  assert.equal(result.access_decision.decision_status, 'deny');
  assert.deepEqual(result.access_decision.reason_codes, ['missing_decision_ref']);
});

test('store staff is denied when requesting capability outside grant profile', () => {
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_store_staff'),
    requestedCapabilityId: 'navly.store.finance_summary',
  });

  assert.equal(result.actor_resolution_result.resolution_status, 'resolved');
  assert.equal(result.gate0_result.decision_status, 'allow');
  assert.equal(result.access_decision.decision_status, 'deny');
  assert.deepEqual(result.access_decision.reason_codes, ['capability_not_granted']);
  assert.equal(result.access_context_envelope, null);
});

test('tenant mismatch bindings are excluded and fail closed before granted scopes are exposed', () => {
  const bindingBackbone = loadBindingBackbone();
  const result = buildBindingSnapshot({
    ingressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    actorResolutionResult: {
      resolution_status: 'resolved',
      actor_ref: 'navly:actor:sample-store-manager-single',
      tenant_ref: 'navly:tenant:sample-retail',
      reason_codes: [],
    },
    bindingBackbone: {
      ...bindingBackbone,
      scopeBindings: [
        ...bindingBackbone.scopeBindings,
        {
          actor_ref: 'navly:actor:sample-store-manager-single',
          tenant_ref: 'navly:tenant:foreign-tenant',
          scope_ref: 'navly:scope:store:foreign-store-999',
          is_primary: false,
        },
      ],
    },
  });

  assert.equal(result.conversation_binding_status, 'suspended');
  assert.deepEqual(result.reason_codes, ['tenant_mismatch']);
  assert.deepEqual(result.granted_scope_refs, []);
  assert.equal(result.primary_scope_ref, null);
});

test('Gate 0 preserves tenant_mismatch instead of collapsing it into binding_missing', () => {
  const bindingBackbone = loadBindingBackbone();
  const result = runAuthKernelAccessChain({
    rawIngressEvidence: sampleBaseIngress('sample_manager_single_scope'),
    requestedCapabilityId: 'navly.store.daily_overview',
    bindingBackbone: {
      ...bindingBackbone,
      scopeBindings: [
        ...bindingBackbone.scopeBindings,
        {
          actor_ref: 'navly:actor:sample-store-manager-single',
          tenant_ref: 'navly:tenant:foreign-tenant',
          scope_ref: 'navly:scope:store:foreign-store-999',
          is_primary: false,
        },
      ],
    },
  });

  assert.equal(result.gate0_result.decision_status, 'deny');
  assert.deepEqual(result.gate0_result.reason_codes, ['tenant_mismatch']);
});

test('scope selection recalculates binding_snapshot_ref when effective content changes', () => {
  const initialSnapshot = buildBindingSnapshot({
    ingressEvidence: sampleBaseIngress('sample_manager_multi_scope'),
    actorResolutionResult: {
      resolution_status: 'resolved',
      actor_ref: 'navly:actor:sample-store-manager-multi',
      tenant_ref: 'navly:tenant:sample-retail',
      reason_codes: [],
    },
  });

  const reboundSnapshot = applyScopeSelectionToBindingSnapshot({
    bindingSnapshot: initialSnapshot,
    requestedScopeRef: 'navly:scope:store:sample-store-002',
  });

  assert.notEqual(reboundSnapshot.binding_snapshot_ref, initialSnapshot.binding_snapshot_ref);
  assert.equal(reboundSnapshot.selected_scope_ref, 'navly:scope:store:sample-store-002');
  assert.equal(reboundSnapshot.conversation_binding_status, 'bound');
});
