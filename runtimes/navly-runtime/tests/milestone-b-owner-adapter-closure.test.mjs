import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runMilestoneBGuardedExecutionChain } from '../execution/runtime-chain-backbone.mjs';
import { createOwnerSideDataPlatformAdapter } from '../adapters/owner-side-data-platform-adapter.mjs';
import {
  getDefaultOwnerSideDependencyClientInitCountForTest,
  resetDefaultOwnerSideDependencyClientsForTest,
} from '../adapters/owner-side-dependency-clients.mjs';

const FIXED_NOW = '2026-04-06T08:00:00.000Z';
const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const fixtureBundlePath = path.join(
  repoRoot,
  'platforms',
  'data-platform',
  'tests',
  'fixtures',
  'member_insight',
  'qinqin_fixture_pages.bundle.json',
);

function buildOwnerAccessContextEnvelope(overrides = {}) {
  return {
    request_id: 'req-owner-adapter-001',
    trace_ref: 'navly:trace:req-owner-adapter-001',
    decision_ref: 'navly:decision:gate0-owner-adapter-001',
    actor_ref: 'navly:actor:sample-store-manager-single',
    session_ref: 'navly:session:owner-adapter-session',
    conversation_ref: 'navly:conversation:owner-adapter-conversation',
    tenant_ref: 'navly:tenant:sample-retail',
    primary_scope_ref: 'navly:scope:store:sample-store-001',
    granted_scope_refs: ['navly:scope:store:sample-store-001'],
    granted_capability_ids: ['navly.store.member_insight', 'navly.system.capability_explanation'],
    issued_at: FIXED_NOW,
    expires_at: '2026-04-06T09:00:00.000Z',
    ...overrides,
  };
}

function buildOwnerRuntimeRequestEnvelope(overrides = {}) {
  return {
    request_id: 'req-owner-adapter-001',
    ingress_ref: 'ingress-wecom-owner-adapter',
    trace_ref: 'navly:trace:req-owner-adapter-001',
    channel_kind: 'wecom',
    message_mode: 'direct_message',
    user_input_text: '帮我看下会员洞察',
    structured_input_slots: {
      freshness_mode: 'latest_usable',
      data_org_id: 'demo-org-001',
      data_window_start_time: '2026-03-20 09:00:00',
      data_window_end_time: '2026-03-24 09:00:00',
      data_app_secret: 'test-secret',
    },
    requested_capability_id: 'navly.store.member_insight',
    requested_service_object_id: 'navly.service.store.member_insight',
    target_scope_hint: 'navly:scope:store:sample-store-001',
    target_business_date_hint: '2026-03-23',
    response_channel_capabilities: {
      rich_text: true,
    },
    access_context_envelope: buildOwnerAccessContextEnvelope(),
    decision_ref: 'navly:decision:gate0-owner-adapter-001',
    delivery_hint: {
      preferred_format: 'summary',
    },
    ...overrides,
  };
}

function buildDenyAuthClient() {
  return {
    async evaluateCapabilityAccess(request) {
      return {
        access_decision: {
          decision_ref: 'navly:decision:capability-deny-owner-adapter-001',
          request_id: request.request_id,
          trace_ref: request.trace_ref,
          decision_status: 'deny',
          actor_ref: 'navly:actor:sample-store-manager-single',
          session_ref: request.session_ref,
          target_capability_id: request.requested_capability_id,
          target_scope_ref: request.requested_scope_ref,
          reason_codes: ['capability_not_granted'],
          restriction_codes: [],
          obligation_codes: [],
          decided_at: FIXED_NOW,
          expires_at: '2026-04-06T09:00:00.000Z',
        },
      };
    },
  };
}

function buildReadinessQuery({
  requestId = 'req-cache-001',
  traceRef = 'navly:trace:req-cache-001',
  businessDate = '2026-03-23',
  orgId = 'demo-org-001',
  appSecret = 'test-secret',
} = {}) {
  return {
    request_id: requestId,
    trace_ref: traceRef,
    capability_id: 'navly.store.member_insight',
    access_context: buildOwnerAccessContextEnvelope({
      request_id: requestId,
      trace_ref: traceRef,
    }),
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: businessDate,
    freshness_mode: 'latest_usable',
    extensions: {
      runtime_trace_ref: 'navly:runtime-trace:cache-sample',
      selected_service_object_id: 'navly.service.store.member_insight',
      data_adapter_context: {
        org_id: orgId,
        app_secret: appSecret,
      },
    },
  };
}

test('owner-side adapter closure serves member_insight without mocked clients', async () => {
  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildOwnerRuntimeRequestEnvelope(),
    now: FIXED_NOW,
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultOrgId: 'demo-org-001',
        defaultAppSecret: 'test-secret',
        fixtureBundlePath,
      },
    },
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.member_insight');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.member_insight');
  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'served');
  assert.ok(result.runtime_dependency_outcome.capability_access_response?.access_decision);
  assert.ok(result.runtime_dependency_outcome.readiness_response);
  assert.ok(result.runtime_dependency_outcome.theme_service_response);
  assert.ok(result.runtime_result_envelope.trace_refs.every((ref) => !ref.startsWith('navly:decision:')));
});

test('owner-side data adapter fails closed when org context is unavailable', async () => {
  const runtimeRequestEnvelope = buildOwnerRuntimeRequestEnvelope({
    structured_input_slots: {
      freshness_mode: 'latest_usable',
      data_window_start_time: '2026-03-20 09:00:00',
      data_window_end_time: '2026-03-24 09:00:00',
      data_app_secret: 'test-secret',
    },
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    now: FIXED_NOW,
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultAppSecret: 'test-secret',
        fixtureBundlePath,
      },
    },
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'dependency_error');
  assert.equal(result.runtime_result_envelope.result_status, 'runtime_error');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.dependency.readiness_error'));
});

test('default owner-side dependency clients are initialized once across repeated runtime requests', async () => {
  resetDefaultOwnerSideDependencyClientsForTest();
  const authKernelClient = buildDenyAuthClient();
  const runtimeRequestEnvelope = buildOwnerRuntimeRequestEnvelope();

  await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    authKernelClient,
    now: FIXED_NOW,
  });
  await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    authKernelClient,
    now: FIXED_NOW,
  });

  assert.equal(getDefaultOwnerSideDependencyClientInitCountForTest(), 1);
});

test('owner-side data adapter cache is bounded by runCacheMaxEntries', async () => {
  let runCount = 0;
  const adapter = createOwnerSideDataPlatformAdapter({
    runCacheMaxEntries: 2,
    runCacheTtlMs: 0,
    runMemberInsightBackboneImpl: async ({ input }) => {
      runCount += 1;
      return {
        trace_ref: `navly:trace:cache-${runCount}`,
        capability_id: 'navly.store.member_insight',
        service_object_id: 'navly.service.store.member_insight',
        backbone_status: 'backbone_ready',
        latest_usable_business_date: input.requested_business_date,
        state_trace_ref: `navly:state-trace:cache:${input.requested_business_date}`,
        run_trace_ref: `navly:run-trace:cache:${runCount}`,
        updated_at: FIXED_NOW,
        service_object: {
          customer_count: 1,
          customer_card_count: 1,
          consume_bill_count: 1,
          consume_bill_payment_count: 1,
          consume_bill_info_count: 1,
        },
      };
    },
  });

  await adapter.queryCapabilityReadiness(buildReadinessQuery({ businessDate: '2026-03-21' }));
  await adapter.queryCapabilityReadiness(buildReadinessQuery({ businessDate: '2026-03-22' }));
  await adapter.queryCapabilityReadiness(buildReadinessQuery({ businessDate: '2026-03-23' }));
  await adapter.queryCapabilityReadiness(buildReadinessQuery({ businessDate: '2026-03-21' }));

  assert.equal(runCount, 4);
});

test('owner-side data adapter removes rejected promise entries so next attempt can retry', async () => {
  let runCount = 0;
  const adapter = createOwnerSideDataPlatformAdapter({
    runCacheMaxEntries: 4,
    runCacheTtlMs: 0,
    runMemberInsightBackboneImpl: async ({ input }) => {
      runCount += 1;
      if (runCount === 1) {
        throw new Error(`synthetic failure for ${input.requested_business_date}`);
      }

      return {
        trace_ref: `navly:trace:retry-${runCount}`,
        capability_id: 'navly.store.member_insight',
        service_object_id: 'navly.service.store.member_insight',
        backbone_status: 'backbone_ready',
        latest_usable_business_date: input.requested_business_date,
        state_trace_ref: `navly:state-trace:retry:${input.requested_business_date}`,
        run_trace_ref: `navly:run-trace:retry:${runCount}`,
        updated_at: FIXED_NOW,
        service_object: {
          customer_count: 1,
          customer_card_count: 1,
          consume_bill_count: 1,
          consume_bill_payment_count: 1,
          consume_bill_info_count: 1,
        },
      };
    },
  });

  const readinessQuery = buildReadinessQuery({ requestId: 'req-cache-retry-001', businessDate: '2026-03-24' });

  await assert.rejects(
    () => adapter.queryCapabilityReadiness(readinessQuery),
    /synthetic failure/,
  );

  const readinessResponse = await adapter.queryCapabilityReadiness(readinessQuery);
  assert.equal(readinessResponse.readiness_status, 'ready');
  assert.equal(runCount, 2);
});
