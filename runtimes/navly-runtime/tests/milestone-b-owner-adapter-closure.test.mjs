import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runMilestoneBGuardedExecutionChain } from '../execution/runtime-chain-backbone.mjs';
import { createOwnerSideDataPlatformAdapter } from '../adapters/owner-side-data-platform-adapter.mjs';
import {
  getDefaultOwnerSideDependencyClientInitCountForTest,
  resetDefaultOwnerSideDependencyClientsForTest,
} from '../adapters/owner-side-dependency-clients.mjs';

const FIXED_NOW = '2026-04-06T08:00:00.000Z';
const EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';
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
const staffFixtureBundlePath = path.join(
  repoRoot,
  'platforms',
  'data-platform',
  'tests',
  'fixtures',
  'staff_board',
  'qinqin_staff_fixture_pages.bundle.json',
);
const financeFixtureBundlePath = path.join(
  repoRoot,
  'platforms',
  'data-platform',
  'tests',
  'fixtures',
  'finance_summary',
  'qinqin_fixture_pages.bundle.json',
);
const dailyOverviewFixtureBundlePaths = [
  fixtureBundlePath,
  staffFixtureBundlePath,
  financeFixtureBundlePath,
];

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
    granted_capability_ids: [
      'navly.store.member_insight',
      'navly.store.daily_overview',
      'navly.store.staff_board',
      'navly.store.finance_summary',
      'navly.system.capability_explanation',
    ],
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

function buildOwnerSurfaceResult({
  requestId = 'req-owner-adapter-001',
  traceRef = 'navly:trace:req-owner-adapter-001',
  targetScopeRef = 'navly:scope:store:sample-store-001',
  businessDate = '2026-03-23',
  readinessStatus = 'ready',
  serviceStatus = 'served',
} = {}) {
  return {
    readiness_response: {
      request_id: requestId,
      trace_ref: traceRef,
      capability_id: 'navly.store.member_insight',
      readiness_status: readinessStatus,
      evaluated_scope_ref: targetScopeRef,
      requested_business_date: businessDate,
      latest_usable_business_date: businessDate,
      reason_codes: readinessStatus === 'ready' ? [] : ['missing_dependency'],
      blocking_dependencies: readinessStatus === 'ready'
        ? []
        : [
          {
            dependency_kind: 'input_data',
            dependency_ref: 'qinqin.member.get_consume_bill_list.v1_2',
            blocking_reason_code: 'missing_dependency',
          },
        ],
      state_trace_refs: ['navly:state-trace:owner-surface:sample'],
      run_trace_refs: ['navly:run-trace:owner-surface:sample'],
      evaluated_at: FIXED_NOW,
      extensions: {
        owner_surface: 'member_insight',
      },
    },
    theme_service_response: {
      request_id: requestId,
      trace_ref: traceRef,
      capability_id: 'navly.store.member_insight',
      service_object_id: 'navly.service.store.member_insight',
      service_status: serviceStatus,
      service_object: serviceStatus === 'served'
        ? {
          capability_id: 'navly.store.member_insight',
          service_object_id: 'navly.service.store.member_insight',
          target_scope_ref: targetScopeRef,
          target_business_date: businessDate,
          customer_count: 1,
          customer_card_count: 1,
          consume_bill_count: 1,
          consume_bill_payment_count: 1,
          consume_bill_info_count: 1,
        }
        : {},
      data_window: {
        from: businessDate,
        to: businessDate,
      },
      explanation_object: serviceStatus === 'served'
        ? undefined
        : {
          capability_id: 'navly.store.member_insight',
          explanation_scope: 'service',
          reason_codes: ['missing_dependency'],
          state_trace_refs: ['navly:state-trace:owner-surface:sample'],
          run_trace_refs: ['navly:run-trace:owner-surface:sample'],
        },
      state_trace_refs: ['navly:state-trace:owner-surface:sample'],
      run_trace_refs: ['navly:run-trace:owner-surface:sample'],
      served_at: FIXED_NOW,
      extensions: {
        owner_surface: 'member_insight',
      },
    },
  };
}

function writePersistedOwnerSurfaceSnapshot({
  rootDir,
  orgId = 'demo-org-001',
  businessDate = '2026-03-23',
  capabilityId = 'navly.store.member_insight',
  serviceObjectId = 'navly.service.store.member_insight',
  readinessStatus = 'ready',
  serviceStatus = 'served',
}) {
  const snapshot = {
    org_id: orgId,
    target_scope_ref: `navly:scope:store:${orgId}`,
    snapshot_business_date: businessDate,
    capability_id: capabilityId,
    service_object_id: serviceObjectId,
    ...buildOwnerSurfaceResult({
      requestId: `persisted-${businessDate}`,
      traceRef: `navly:trace:persisted-${businessDate}`,
      targetScopeRef: `navly:scope:store:${orgId}`,
      businessDate,
      readinessStatus,
      serviceStatus,
    }),
  };
  const orgRoot = path.join(rootDir, orgId, businessDate, 'owner-surfaces');
  fs.mkdirSync(orgRoot, { recursive: true });
  fs.writeFileSync(
    path.join(orgRoot, `${capabilityId}.json`),
    `${JSON.stringify(snapshot, null, 2)}\n`,
    'utf8',
  );
  fs.writeFileSync(
    path.join(rootDir, orgId, 'index.json'),
    `${JSON.stringify({
      snapshot_version: 'navly.phase1_owner_surface_snapshot.v1',
      org_id: orgId,
      capabilities: {
        [capabilityId]: {
          service_object_id: serviceObjectId,
          available_business_dates: [businessDate],
          latest_persisted_business_date: businessDate,
        },
      },
    }, null, 2)}\n`,
    'utf8',
  );
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

test('owner-side adapter closure serves staff_board without mocked clients', async () => {
  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildOwnerRuntimeRequestEnvelope({
      user_input_text: '帮我看下员工看板',
      requested_capability_id: 'navly.store.staff_board',
      requested_service_object_id: 'navly.service.store.staff_board',
    }),
    now: FIXED_NOW,
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultOrgId: 'demo-org-001',
        defaultAppSecret: 'test-secret',
        fixtureBundlePaths: [staffFixtureBundlePath],
      },
    },
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.staff_board');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.staff_board');
  assert.equal(result.runtime_dependency_outcome.theme_service_response.service_object.staff_count, 2);
});

test('owner-side adapter closure serves daily_overview without mocked clients', async () => {
  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildOwnerRuntimeRequestEnvelope({
      user_input_text: '给我今日门店日报',
      requested_capability_id: 'navly.store.daily_overview',
      requested_service_object_id: 'navly.service.store.daily_overview',
    }),
    now: FIXED_NOW,
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultOrgId: 'demo-org-001',
        defaultAppSecret: 'test-secret',
        fixtureBundlePaths: dailyOverviewFixtureBundlePaths,
      },
    },
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.daily_overview');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.daily_overview');
  assert.deepEqual(
    result.runtime_dependency_outcome.theme_service_response.service_object.published_service_object_ids,
    [
      'navly.service.store.member_insight',
      'navly.service.store.staff_board',
      'navly.service.store.finance_summary',
    ],
  );
});

test('owner-side adapter closure serves finance_summary capability_explanation without mocked clients', async () => {
  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildOwnerRuntimeRequestEnvelope({
      user_input_text: '解释财务汇总当前状态',
      requested_capability_id: 'navly.store.finance_summary',
      requested_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    }),
    now: FIXED_NOW,
    dependencyClientFactoryOptions: {
      authAdapterOptions: {
        nowFactory: () => FIXED_NOW,
      },
      dataAdapterOptions: {
        defaultOrgId: 'demo-org-001',
        defaultAppSecret: 'test-secret',
        fixtureBundlePaths: [financeFixtureBundlePath],
      },
    },
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.finance_summary');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
  assert.equal(result.runtime_dependency_outcome.theme_service_response.service_object.readiness_status, 'ready');
  assert.equal(result.runtime_dependency_outcome.theme_service_response.service_object.theme_service_status, 'served');
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

test('owner-side data adapter serves operator sync status through the operator surface path', async () => {
  let capturedInput = null;
  const adapter = createOwnerSideDataPlatformAdapter({
    runOperatorSurfaceImpl: async ({ input }) => {
      capturedInput = input;
      return {
        readiness_response: {
          request_id: input.request_id,
          trace_ref: input.trace_ref,
          capability_id: 'navly.ops.sync_status',
          readiness_status: 'ready',
          evaluated_scope_ref: input.target_scope_ref,
          requested_business_date: input.requested_business_date,
          latest_usable_business_date: input.requested_business_date,
          reason_codes: [],
          blocking_dependencies: [],
          state_trace_refs: ['navly:state-trace:operator-sync-status'],
          run_trace_refs: ['navly:run-trace:operator-sync-status'],
          evaluated_at: FIXED_NOW,
        },
        theme_service_response: {
          request_id: input.request_id,
          trace_ref: input.trace_ref,
          capability_id: 'navly.ops.sync_status',
          service_object_id: 'navly.service.ops.sync_status',
          service_status: 'served',
          service_object: {
            capability_id: 'navly.ops.sync_status',
            service_object_id: 'navly.service.ops.sync_status',
            org_id: input.org_id,
            state_snapshot: input.state_snapshot_path,
            report: {
              org_id: input.org_id,
              scheduler_runs: [],
              latest_sync_states: [],
              service_projection_count: 1,
            },
          },
          data_window: {
            from: input.requested_business_date,
            to: input.requested_business_date,
          },
          state_trace_refs: ['navly:state-trace:operator-sync-status'],
          run_trace_refs: ['navly:run-trace:operator-sync-status'],
          served_at: FIXED_NOW,
        },
      };
    },
  });

  const readiness = await adapter.queryCapabilityReadiness({
    request_id: 'req-ops-sync-status-001',
    trace_ref: 'navly:trace:req-ops-sync-status-001',
    capability_id: 'navly.ops.sync_status',
    access_context: buildOwnerAccessContextEnvelope(),
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-23',
    freshness_mode: 'latest_usable',
    extensions: {
      runtime_trace_ref: 'navly:runtime-trace:ops-sync-status-001',
      selected_service_object_id: 'navly.service.ops.sync_status',
      data_adapter_context: {
        org_id: 'demo-org-001',
        state_snapshot_path: '/tmp/navly-truth-store-snapshot.json',
      },
    },
  });
  const service = await adapter.queryThemeService({
    request_id: 'req-ops-sync-status-001',
    trace_ref: 'navly:trace:req-ops-sync-status-001',
    capability_id: 'navly.ops.sync_status',
    service_object_id: 'navly.service.ops.sync_status',
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-23',
    extensions: {
      data_adapter_context: {
        org_id: 'demo-org-001',
        state_snapshot_path: '/tmp/navly-truth-store-snapshot.json',
      },
    },
  });

  assert.equal(readiness.readiness_status, 'ready');
  assert.equal(service.service_status, 'served');
  assert.equal(service.service_object.report.service_projection_count, 1);
  assert.equal(capturedInput.state_snapshot_path, '/tmp/navly-truth-store-snapshot.json');
  assert.equal(capturedInput.org_id, 'demo-org-001');
});

test('owner-side data adapter passes backfill action inputs through the operator surface path', async () => {
  let capturedInput = null;
  const adapter = createOwnerSideDataPlatformAdapter({
    runOperatorSurfaceImpl: async ({ input }) => {
      capturedInput = input;
      return {
        readiness_response: {
          request_id: input.request_id,
          trace_ref: input.trace_ref,
          capability_id: 'navly.ops.sync_backfill',
          readiness_status: 'ready',
          evaluated_scope_ref: input.target_scope_ref,
          requested_business_date: input.requested_business_date,
          latest_usable_business_date: input.requested_business_date,
          reason_codes: [],
          blocking_dependencies: [],
          state_trace_refs: [],
          run_trace_refs: ['navly:run-trace:operator-backfill-action'],
          evaluated_at: FIXED_NOW,
        },
        theme_service_response: {
          request_id: input.request_id,
          trace_ref: input.trace_ref,
          capability_id: 'navly.ops.sync_backfill',
          service_object_id: 'navly.service.ops.sync_backfill',
          service_status: 'served',
          service_object: {
            capability_id: 'navly.ops.sync_backfill',
            service_object_id: 'navly.service.ops.sync_backfill',
            requested_window: {
              from: input.backfill_from,
              to: input.backfill_to,
            },
            state_snapshot: input.state_snapshot_path,
          },
          data_window: {
            from: input.backfill_from,
            to: input.backfill_to,
          },
          state_trace_refs: [],
          run_trace_refs: ['navly:run-trace:operator-backfill-action'],
          served_at: FIXED_NOW,
        },
      };
    },
  });

  const readiness = await adapter.queryCapabilityReadiness({
    request_id: 'req-ops-backfill-001',
    trace_ref: 'navly:trace:req-ops-backfill-001',
    capability_id: 'navly.ops.sync_backfill',
    access_context: buildOwnerAccessContextEnvelope(),
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-22',
    freshness_mode: 'latest_usable',
    extensions: {
      runtime_trace_ref: 'navly:runtime-trace:ops-backfill-001',
      selected_service_object_id: 'navly.service.ops.sync_backfill',
      data_adapter_context: {
        org_id: 'demo-org-001',
        app_secret: 'test-secret',
        state_snapshot_path: '/tmp/navly-truth-store-snapshot.json',
        fixture_bundle_path: fixtureBundlePath,
        transport_kind: 'fixture',
        backfill_from: '2026-03-21',
        backfill_to: '2026-03-22',
      },
    },
  });
  const service = await adapter.queryThemeService({
    request_id: 'req-ops-backfill-001',
    trace_ref: 'navly:trace:req-ops-backfill-001',
    capability_id: 'navly.ops.sync_backfill',
    service_object_id: 'navly.service.ops.sync_backfill',
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-22',
    extensions: {
      data_adapter_context: {
        org_id: 'demo-org-001',
        app_secret: 'test-secret',
        state_snapshot_path: '/tmp/navly-truth-store-snapshot.json',
        fixture_bundle_path: fixtureBundlePath,
        transport_kind: 'fixture',
        backfill_from: '2026-03-21',
        backfill_to: '2026-03-22',
      },
    },
  });

  assert.equal(readiness.readiness_status, 'ready');
  assert.equal(service.service_status, 'served');
  assert.deepEqual(service.service_object.requested_window, {
    from: '2026-03-21',
    to: '2026-03-22',
  });
  assert.equal(capturedInput.backfill_from, '2026-03-21');
  assert.equal(capturedInput.backfill_to, '2026-03-22');
});

test('owner-side data adapter fails closed for operator surfaces when state snapshot path is missing', async () => {
  const adapter = createOwnerSideDataPlatformAdapter();
  const readiness = await adapter.queryCapabilityReadiness({
    request_id: 'req-ops-quality-missing-001',
    trace_ref: 'navly:trace:req-ops-quality-missing-001',
    capability_id: 'navly.ops.quality_report',
    access_context: buildOwnerAccessContextEnvelope(),
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-23',
    freshness_mode: 'latest_usable',
    extensions: {
      runtime_trace_ref: 'navly:runtime-trace:ops-quality-missing-001',
      selected_service_object_id: 'navly.service.ops.quality_report',
      data_adapter_context: {
        org_id: 'demo-org-001',
      },
    },
  });
  const service = await adapter.queryThemeService({
    request_id: 'req-ops-quality-missing-001',
    trace_ref: 'navly:trace:req-ops-quality-missing-001',
    capability_id: 'navly.ops.quality_report',
    service_object_id: 'navly.service.ops.quality_report',
    target_scope_ref: 'navly:scope:store:sample-store-001',
    target_business_date: '2026-03-23',
    extensions: {
      data_adapter_context: {
        org_id: 'demo-org-001',
      },
    },
  });

  assert.equal(readiness.readiness_status, 'pending');
  assert.deepEqual(readiness.reason_codes, ['missing_persisted_state_path']);
  assert.equal(service.service_status, 'not_ready');
  assert.deepEqual(service.explanation_object.reason_codes, ['missing_persisted_state_path']);
});

test('owner-side data adapter cache is bounded by runCacheMaxEntries', async () => {
  let runCount = 0;
  const adapter = createOwnerSideDataPlatformAdapter({
    runCacheMaxEntries: 2,
    runCacheTtlMs: 0,
    runMemberInsightOwnerSurfaceImpl: async ({ input }) => {
      runCount += 1;
      return buildOwnerSurfaceResult({
        requestId: input.request_id,
        traceRef: input.trace_ref,
        targetScopeRef: input.target_scope_ref,
        businessDate: input.requested_business_date,
      });
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
    runMemberInsightOwnerSurfaceImpl: async ({ input }) => {
      runCount += 1;
      if (runCount === 1) {
        throw new Error(`synthetic failure for ${input.requested_business_date}`);
      }

      return buildOwnerSurfaceResult({
        requestId: input.request_id,
        traceRef: input.trace_ref,
        targetScopeRef: input.target_scope_ref,
        businessDate: input.requested_business_date,
      });
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

test('owner-side data adapter normalizes non-positive live timeout to the default value', async () => {
  let capturedInput = null;
  const adapter = createOwnerSideDataPlatformAdapter({
    liveTimeoutMs: 0,
    runMemberInsightOwnerSurfaceImpl: async ({ input }) => {
      capturedInput = input;
      return buildOwnerSurfaceResult({
        requestId: input.request_id,
        traceRef: input.trace_ref,
        targetScopeRef: input.target_scope_ref,
        businessDate: input.requested_business_date,
      });
    },
  });

  await adapter.queryCapabilityReadiness({
    ...buildReadinessQuery({ businessDate: '2026-03-25' }),
    extensions: {
      runtime_trace_ref: 'navly:runtime-trace:cache-sample',
      selected_service_object_id: 'navly.service.store.member_insight',
      data_adapter_context: {
        org_id: 'demo-org-001',
        app_secret: 'test-secret',
        transport_kind: 'live',
        live_base_url: 'http://127.0.0.1:8080',
        live_timeout_ms: 0,
      },
    },
  });

  assert.equal(capturedInput.live_timeout_ms, 15000);
});

test('owner-side data adapter prefers persisted snapshots for latest_usable manager queries', async () => {
  const persistedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'navly-persisted-owner-surface-'));
  try {
    writePersistedOwnerSurfaceSnapshot({
      rootDir: persistedRoot,
      businessDate: '2026-03-23',
    });
    const adapter = createOwnerSideDataPlatformAdapter({
      persistedServingRoot: persistedRoot,
      fixtureBundlePath: null,
      fixtureBundlePaths: null,
    });

    const readinessResponse = await adapter.queryCapabilityReadiness({
      ...buildReadinessQuery({ requestId: 'req-persisted-001', businessDate: '2026-03-24' }),
      extensions: {
        runtime_trace_ref: 'navly:runtime-trace:persisted-001',
        selected_service_object_id: 'navly.service.store.member_insight',
        data_adapter_context: {
          org_id: 'demo-org-001',
          transport_kind: 'persisted',
          persisted_serving_root: persistedRoot,
        },
      },
    });

    assert.equal(readinessResponse.readiness_status, 'ready');
    assert.equal(readinessResponse.latest_usable_business_date, '2026-03-23');
    assert.equal(readinessResponse.request_id, 'req-persisted-001');
    assert.equal(readinessResponse.extensions.data_source, 'persisted_owner_surface_snapshot');
  } finally {
    fs.rmSync(persistedRoot, { recursive: true, force: true });
  }
});

test('owner-side data adapter fail-closes when persisted snapshot is unavailable', async () => {
  const persistedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'navly-persisted-owner-surface-miss-'));
  try {
    const adapter = createOwnerSideDataPlatformAdapter({
      persistedServingRoot: persistedRoot,
      fixtureBundlePath: null,
      fixtureBundlePaths: null,
    });

    const readinessResponse = await adapter.queryCapabilityReadiness({
      ...buildReadinessQuery({ requestId: 'req-persisted-miss-001', businessDate: '2026-03-24' }),
      extensions: {
        runtime_trace_ref: 'navly:runtime-trace:persisted-miss-001',
        selected_service_object_id: 'navly.service.store.member_insight',
        data_adapter_context: {
          org_id: 'demo-org-001',
          transport_kind: 'persisted',
          persisted_serving_root: persistedRoot,
        },
      },
    });
    const serviceResponse = await adapter.queryThemeService({
      request_id: 'req-persisted-miss-001',
      trace_ref: 'navly:trace:req-persisted-miss-001',
      capability_id: 'navly.store.member_insight',
      service_object_id: 'navly.service.store.member_insight',
      target_scope_ref: 'navly:scope:store:demo-org-001',
      target_business_date: '2026-03-24',
      extensions: {
        data_adapter_context: {
          org_id: 'demo-org-001',
          transport_kind: 'persisted',
          persisted_serving_root: persistedRoot,
        },
      },
    });

    assert.equal(readinessResponse.readiness_status, 'pending');
    assert.deepEqual(readinessResponse.reason_codes, ['latest_state_not_published']);
    assert.equal(serviceResponse.service_status, 'not_ready');
    assert.deepEqual(serviceResponse.explanation_object.reason_codes, ['latest_state_not_published']);
  } finally {
    fs.rmSync(persistedRoot, { recursive: true, force: true });
  }
});
