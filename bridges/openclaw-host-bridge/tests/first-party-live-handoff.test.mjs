import test from 'node:test';
import assert from 'node:assert/strict';
import { runFirstPartyLiveHostTool } from '../adapters/openclaw/first-party-live-handoff.mjs';

const FIXED_NOW = '2026-04-12T08:00:00.000Z';

function buildRawHostIngress(overrides = {}) {
  return {
    request_id: 'asp50-live-tool-001',
    trace_ref: 'navly:trace:asp50-live-tool-001',
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

function buildRuntimeExecutorOptions() {
  return {
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultOrgId: 'demo-org-001',
        defaultAppSecret: 'test-secret',
      },
    },
  };
}

test('first-party live handoff closes manager daily overview into runtime execution and host dispatch', async () => {
  const result = await runFirstPartyLiveHostTool({
    toolName: 'navly_daily_overview',
    rawHostIngress: buildRawHostIngress(),
    toolInput: {
      scope_ref: 'navly:scope:store:sample-store-001',
      business_date: '2026-03-23',
      freshness_mode: 'latest_usable',
      include_explanation: true,
    },
    hostAgentSelection: {
      agent_id: 'main',
      carrier_ref: 'openclaw:agent:main',
    },
    runtimeExecutorOptions: buildRuntimeExecutorOptions(),
    now: FIXED_NOW,
  });

  assert.equal(result.published_tool.capability_id, 'navly.store.daily_overview');
  assert.equal(result.host_agent_selection.agent_id, 'main');
  assert.equal(result.live_access_chain.access_decision.decision_status, 'allow');
  assert.equal(result.runtime_request_envelope.requested_capability_id, 'navly.store.daily_overview');
  assert.equal(result.runtime_pipeline.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_pipeline.runtime_result_envelope.selected_service_object_id, 'navly.service.store.daily_overview');
  assert.equal(result.host_dispatch_result.dispatch_status, 'ready_for_runtime_dispatch');
  assert.equal(result.host_dispatch_result.reply_blocks[0].fragment_type, 'service_object');
  assert.equal(result.host_dispatch_result.reply_blocks[0].service_object.capability_id, 'navly.store.daily_overview');
  assert.ok(result.host_dispatch_result.trace_refs.includes(result.runtime_pipeline.runtime_result_envelope.runtime_trace_ref));
});

test('first-party live handoff closes manager finance summary into runtime execution and host dispatch', async () => {
  const result = await runFirstPartyLiveHostTool({
    toolName: 'navly_finance_summary',
    rawHostIngress: buildRawHostIngress({
      request_id: 'asp53-live-tool-finance',
      trace_ref: 'navly:trace:asp53-live-tool-finance',
      host_message_ref: 'openclaw:message:finance-001',
      message_text: '看一下今天充值和流水',
    }),
    toolInput: {
      scope_ref: 'navly:scope:store:sample-store-001',
      business_date: '2026-03-23',
      freshness_mode: 'latest_usable',
      include_explanation: true,
    },
    hostAgentSelection: {
      agent_id: 'main',
      carrier_ref: 'openclaw:agent:main',
    },
    runtimeExecutorOptions: buildRuntimeExecutorOptions(),
    now: FIXED_NOW,
  });

  assert.equal(result.live_access_chain.access_decision.decision_status, 'allow');
  assert.equal(result.runtime_pipeline.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_pipeline.runtime_result_envelope.selected_service_object_id, 'navly.service.store.finance_summary');
  assert.equal(result.host_dispatch_result.dispatch_status, 'ready_for_runtime_dispatch');
  assert.equal(result.host_dispatch_result.reply_blocks[0].fragment_type, 'service_object');
  assert.equal(result.host_dispatch_result.reply_blocks[0].service_object.capability_id, 'navly.store.finance_summary');
});

test('agent selection remains host isolation only and cannot substitute for finance access truth', async () => {
  const result = await runFirstPartyLiveHostTool({
    toolName: 'navly_finance_summary',
    rawHostIngress: buildRawHostIngress({
      request_id: 'asp52-live-tool-agent-isolation',
      trace_ref: 'navly:trace:asp52-live-tool-agent-isolation',
      host_message_ref: 'openclaw:message:finance-002',
      peer_identity_evidence: [
        {
          alias_namespace: 'wecom_user_id',
          alias_value: 'sample_store_staff',
        },
      ],
      message_text: '帮我看下财务汇总',
    }),
    toolInput: {
      scope_ref: 'navly:scope:store:sample-store-001',
      business_date: '2026-03-23',
      freshness_mode: 'latest_usable',
      include_explanation: true,
    },
    hostAgentSelection: {
      agent_id: 'admin',
      carrier_ref: 'openclaw:agent:admin',
    },
    runtimeExecutorOptions: buildRuntimeExecutorOptions(),
    now: FIXED_NOW,
  });

  assert.equal(result.host_agent_selection.agent_id, 'admin');
  assert.equal(result.live_access_chain.gate0_result.decision_status, 'allow');
  assert.equal(result.live_access_chain.access_decision.decision_status, 'deny');
  assert.deepEqual(result.live_access_chain.access_decision.reason_codes, ['capability_not_granted']);
  assert.equal(result.runtime_request_envelope, null);
  assert.equal(result.runtime_pipeline, null);
  assert.equal(result.gate0_enforcement.enforcement_status, 'blocked_missing_access_context');
});
