import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  createNavlyFirstPartyToolFactory,
  createNavlyFirstPartyTools,
} from '../extensions/navly-first-party-host/runtime.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');

function buildContext(overrides = {}) {
  return {
    agentId: 'main',
    messageChannel: 'wecom',
    agentAccountId: 'default',
    sessionKey: 'agent:main:wecom:direct:test-user',
    requesterSenderId: 'sample_manager_single_scope',
    deliveryContext: {
      channel: 'wecom',
      to: 'wecom-user:test-user',
    },
    ...overrides,
  };
}

test('navly first-party host plugin exposes main-agent tools from the publication manifest', () => {
  const tools = createNavlyFirstPartyTools({
    repoRoot,
    pluginConfig: {},
    context: buildContext(),
  });

  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      'navly_daily_overview',
      'navly_member_insight',
      'navly_finance_summary',
      'navly_staff_board',
      'navly_explain_unavailable',
    ],
  );
});

test('navly first-party host plugin exposes ops tools only inside the ops agent carrier', () => {
  const tools = createNavlyFirstPartyTools({
    repoRoot,
    pluginConfig: {},
    context: buildContext({
      agentId: 'ops',
      sessionKey: 'agent:ops:wecom:direct:test-user',
    }),
  });

  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      'navly_sync_status',
      'navly_backfill_status',
      'navly_rerun_sync',
      'navly_trigger_backfill',
      'navly_quality_report',
    ],
  );
});

test('navly first-party host plugin tool execution maps OpenClaw runtime context into Navly live handoff', async () => {
  let captured = null;
  const tools = createNavlyFirstPartyTools({
    repoRoot,
    pluginConfig: {
      defaultScopeRef: 'navly:scope:store:sample-store-001',
      defaultOrgId: '627149864218629',
      defaultAppSecret: 'test-secret',
    },
    context: buildContext(),
    nowFactory: () => new Date('2026-04-12T15:00:00.000Z'),
    liveHandoffRunner: async (payload) => {
      captured = payload;
      return {
        published_tool: {
          tool_name: payload.toolName,
          capability_id: 'navly.store.daily_overview',
          service_object_id: 'navly.service.store.daily_overview',
        },
        gate0_enforcement: {
          reason_codes: [],
        },
        runtime_pipeline: {
          runtime_result_envelope: {
            result_status: 'answered',
            selected_capability_id: 'navly.store.daily_overview',
            selected_service_object_id: 'navly.service.store.daily_overview',
            reason_codes: [],
          },
        },
        host_dispatch_result: {
          dispatch_status: 'ready_for_runtime_dispatch',
          reply_blocks: [
            {
              fragment_type: 'service_object',
              service_object: {
                capability_id: 'navly.store.daily_overview',
              },
            },
          ],
          trace_refs: ['navly:runtime-trace:test'],
        },
      };
    },
  });

  const result = await tools[0].execute('tool-call-1', {
    business_date: '2026-04-12',
  });

  assert.equal(captured.toolName, 'navly_daily_overview');
  assert.equal(captured.hostAgentSelection.agent_id, 'main');
  assert.equal(captured.rawHostIngress.channel_kind, 'wecom');
  assert.equal(captured.rawHostIngress.peer_identity_evidence[0].alias_namespace, 'wecom_user_id');
  assert.equal(captured.rawHostIngress.peer_identity_evidence[0].alias_value, 'sample_manager_single_scope');
  assert.equal(captured.runtimeDataContext.data_transport_kind, 'persisted');
  assert.equal(captured.runtimeDataContext.data_persisted_serving_root, '/var/lib/navly/data-platform/serving-store');
  assert.equal(captured.runtimeDataContext.data_org_id, '627149864218629');
  assert.equal(captured.runtimeDataContext.data_app_secret, 'test-secret');
  assert.equal(
    JSON.parse(result.content[0].text).selected_capability_id,
    'navly.store.daily_overview',
  );
});
